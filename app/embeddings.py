"""Dense text embeddings with a no-download default.

``HashingEmbedder`` is the default. It maps stemmed words, word bigrams and
character 4-grams into a fixed 512-dim space with signed feature hashing and
sublinear term frequency. Character n-grams give it tolerance to plurals,
typos and morphology ("refraction" ~ "refracted"). It needs no model files,
so it works on free hosting and offline.

Optional providers (set EMBEDDING_PROVIDER): ``gemini`` (text-embedding-004)
and ``sentence-transformers`` (all-MiniLM-L6-v2). If an optional provider
fails at start-up the hashing embedder is used instead.
"""
from __future__ import annotations

import logging
import math
import zlib
from typing import Protocol

import numpy as np

from .nlp import STOPWORDS, stem, tokens

log = logging.getLogger("cognivault.embeddings")


class Embedder(Protocol):
    name: str

    def embed(self, texts: list[str]) -> np.ndarray: ...


class HashingEmbedder:
    def __init__(self, dim: int = 512):
        self.dim = dim
        self.name = f"hashing-v1-{dim}"

    def _features(self, text: str) -> dict[int, float]:
        feats: dict[int, float] = {}
        words = [stem(t) for t in tokens(text) if t not in STOPWORDS]

        def add(key: str, w: float):
            h = zlib.crc32(key.encode("utf-8"))
            idx = h % self.dim
            sign = 1.0 if (h >> 31) & 1 else -1.0
            feats[idx] = feats.get(idx, 0.0) + sign * w

        counts: dict[str, int] = {}
        for w in words:
            counts[w] = counts.get(w, 0) + 1
        for w, c in counts.items():
            tf = 1.0 + math.log(c)
            add("w:" + w, tf)
            padded = f"<{w}>"
            if len(padded) > 5:
                for i in range(len(padded) - 3):
                    add("c:" + padded[i : i + 4], 0.35 * tf)
        for a, b in zip(words, words[1:]):
            add(f"b:{a}_{b}", 0.7)
        return feats

    def embed(self, texts: list[str]) -> np.ndarray:
        mat = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, t in enumerate(texts):
            for idx, v in self._features(t).items():
                mat[i, idx] = v
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return mat / norms


class GeminiEmbedder:
    def __init__(self, api_key: str, model: str = "text-embedding-004"):
        from google import genai  # type: ignore

        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.name = f"gemini-{model}"
        self.embed(["warm up"])  # fail fast at start-up

    def embed(self, texts: list[str]) -> np.ndarray:
        out = []
        for i in range(0, len(texts), 64):
            res = self.client.models.embed_content(model=self.model, contents=texts[i : i + 64])
            out.extend(e.values for e in res.embeddings)
        mat = np.asarray(out, dtype=np.float32)
        mat /= np.maximum(np.linalg.norm(mat, axis=1, keepdims=True), 1e-9)
        return mat


class SentenceTransformerEmbedder:
    def __init__(self, model: str = "sentence-transformers/all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer  # type: ignore

        self.model = SentenceTransformer(model)
        self.name = "st-" + model.split("/")[-1]

    def embed(self, texts: list[str]) -> np.ndarray:
        return np.asarray(self.model.encode(texts, normalize_embeddings=True), dtype=np.float32)


def make_embedder(provider: str, gemini_api_key: str = "", gemini_model: str = "text-embedding-004") -> Embedder:
    try:
        if provider == "gemini" and gemini_api_key:
            return GeminiEmbedder(gemini_api_key, gemini_model)
        if provider in {"sentence-transformers", "st"}:
            return SentenceTransformerEmbedder()
    except Exception as exc:  # pragma: no cover - depends on network/packages
        log.warning("Embedding provider '%s' unavailable (%s); using hashing embedder.", provider, exc)
    return HashingEmbedder()
