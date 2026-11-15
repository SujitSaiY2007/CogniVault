"""Hybrid retrieval over one user's scope (shared course + their uploads).

Pipeline
  1. Lexical: SQLite FTS5 BM25 (Porter stemming) over chunk text and section titles.
  2. Dense: cosine similarity of embeddings.
  3. Fusion: Reciprocal Rank Fusion, RRF(d) = sum_r 1 / (60 + rank_r(d)).
     RRF is robust to the two scores living on different scales.
  4. Re-rank the fused top 30 with IDF-weighted query-term coverage, which is
     what the grounding gate also checks, so ranking and gating agree, plus
     coverage of the chunk's section heading.
  5. Maximal Marginal Relevance picks the final k (lambda = 0.75) so the
     citations are not near-duplicates.
"""
from __future__ import annotations

import math
import re
import threading
from dataclasses import dataclass
from typing import Optional

import numpy as np

from .db import Database
from .embeddings import Embedder
from .models import EvidenceUnit
from .nlp import STOPWORDS, content_terms, term_set, tokens

RRF_K = 60


@dataclass
class Hit:
    unit: EvidenceUnit
    score: float
    lexical: float
    dense: float
    coverage: float
    rank: int = 0


class CorpusIndex:
    """In-memory view of one scope: units, term sets, document frequencies, vectors."""

    def __init__(self, units: list[EvidenceUnit], ids: list[str], matrix: np.ndarray):
        self.units = {u.evidence_id: u for u in units}
        self.order = [u.evidence_id for u in units]
        self.terms = {u.evidence_id: term_set(u.text + " " + u.section) for u in units}
        self.section_terms = {u.evidence_id: term_set(u.section) for u in units}
        self.df: dict[str, int] = {}
        for ts in self.terms.values():
            for t in ts:
                self.df[t] = self.df.get(t, 0) + 1
        self.n = max(1, len(units))
        keep = [i for i, eid in enumerate(ids) if eid in self.units]
        self.vec_ids = [ids[i] for i in keep]
        self.matrix = matrix[keep] if len(keep) else np.zeros((0, matrix.shape[1] if matrix.ndim == 2 else 1), dtype=np.float32)
        self.vec_pos = {eid: i for i, eid in enumerate(self.vec_ids)}

    def idf(self, term: str) -> float:
        # Unseen terms get the maximum weight: a question about something the
        # course never mentions should not look "covered".
        return math.log(1 + self.n / (1 + self.df.get(term, 0)))

    def coverage(self, q_terms: set[str], doc_terms: set[str]) -> float:
        if not q_terms:
            return 0.0
        total = sum(self.idf(t) for t in q_terms)
        got = sum(self.idf(t) for t in q_terms if t in doc_terms)
        return got / total if total else 0.0


def fts_query(text: str) -> str:
    toks = [t for t in tokens(text) if t not in STOPWORDS and len(t) > 1]
    toks = list(dict.fromkeys(re.sub(r"[^a-z0-9]", "", t) for t in toks))
    toks = [t for t in toks if t]
    return " OR ".join(f'"{t}"' for t in toks[:24])


class Retriever:
    def __init__(self, db: Database, embedder: Embedder):
        self.db = db
        self.embedder = embedder
        self._cache: dict[str, tuple[int, CorpusIndex]] = {}
        self._versions: dict[str, int] = {}
        self._lock = threading.Lock()

    def invalidate(self, owner_id: Optional[str] = None) -> None:
        with self._lock:
            if owner_id is None or owner_id == "public":
                self._cache.clear()
            else:
                self._cache.pop(owner_id, None)

    def index(self, owner_id: str) -> CorpusIndex:
        with self._lock:
            cached = self._cache.get(owner_id)
            if cached:
                return cached[1]
        units = self.db.evidence_for_owner(owner_id)
        ids, mat = self.db.embeddings_for_owner(owner_id, self.embedder.name)
        idx = CorpusIndex(units, ids, mat)
        with self._lock:
            self._cache[owner_id] = (0, idx)
        return idx

    def ensure_embeddings(self) -> int:
        missing = self.db.missing_embeddings(self.embedder.name)
        if not missing:
            return 0
        for i in range(0, len(missing), 128):
            batch = missing[i : i + 128]
            vecs = self.embedder.embed([u.section + ". " + u.text for u in batch])
            self.db.put_embeddings([(u.evidence_id, u.owner_id, self.embedder.name, v) for u, v in zip(batch, vecs)])
        self.invalidate()
        return len(missing)

    def search(self, query: str, owner_id: str, k: int = 5, source_ids: Optional[set[str]] = None,
               topic_id: Optional[str] = None) -> list[Hit]:
        idx = self.index(owner_id)
        if not idx.units or not query.strip():
            return []
        q_terms = term_set(query)

        def allowed(eid: str) -> bool:
            u = idx.units.get(eid)
            if u is None:
                return False
            if source_ids is not None and u.source_id not in source_ids:
                return False
            if topic_id and topic_id not in u.topics:
                return False
            return True

        # 1. lexical
        lex_raw = [(eid, s) for eid, s in self.db.fts_search(fts_query(query), owner_id, limit=80) if allowed(eid)]
        lex_max = max((s for _, s in lex_raw), default=0.0) or 1.0
        lex = {eid: s / lex_max for eid, s in lex_raw}
        lex_rank = {eid: r for r, (eid, _) in enumerate(lex_raw, 1)}

        # 2. dense
        dense: dict[str, float] = {}
        dense_rank: dict[str, int] = {}
        qv = None
        if idx.matrix.shape[0]:
            try:
                qv = self.embedder.embed([query])[0]
                sims = idx.matrix @ qv
                order = np.argsort(-sims)[:80]
                r = 0
                for i in order:
                    eid = idx.vec_ids[int(i)]
                    if not allowed(eid) or sims[i] <= 0:
                        continue
                    r += 1
                    dense[eid] = float(sims[i])
                    dense_rank[eid] = r
            except Exception:
                qv = None

        # 3. RRF fusion
        cand = set(lex_rank) | set(dense_rank)
        if not cand:
            return []
        rrf = {eid: (1 / (RRF_K + lex_rank[eid]) if eid in lex_rank else 0.0)
               + (1 / (RRF_K + dense_rank[eid]) if eid in dense_rank else 0.0) for eid in cand}
        top = sorted(cand, key=lambda e: -rrf[e])[:30]
        rrf_max = max(rrf[e] for e in top) or 1.0

        # 4. coverage-aware re-rank
        hits: list[Hit] = []
        for eid in top:
            cov = idx.coverage(q_terms, idx.terms[eid])
            sec = idx.coverage(q_terms, idx.section_terms[eid])
            d = dense.get(eid, 0.0)
            # The section heading is a strong topical anchor ("Newton's Second Law").
            score = 0.35 * cov + 0.25 * (rrf[eid] / rrf_max) + 0.15 * d + 0.10 * lex.get(eid, 0.0) + 0.15 * sec
            if idx.units[eid].evidence_type == "figure" and cov < 0.5:
                score *= 0.8  # captions are short; avoid them crowding out text
            hits.append(Hit(idx.units[eid], round(score, 6), round(lex.get(eid, 0.0), 6), round(d, 6), round(cov, 6)))
        hits.sort(key=lambda h: (-h.score, h.unit.evidence_id))

        # 5. MMR diversity
        chosen = self._mmr(hits, idx, k, lam=0.75)
        for i, h in enumerate(chosen, 1):
            h.rank = i
        return chosen

    @staticmethod
    def _mmr(hits: list[Hit], idx: CorpusIndex, k: int, lam: float) -> list[Hit]:
        if len(hits) <= 1:
            return hits[:k]
        chosen: list[Hit] = [hits[0]]
        pool = hits[1:]

        def sim(a: Hit, b: Hit) -> float:
            pa, pb = idx.vec_pos.get(a.unit.evidence_id), idx.vec_pos.get(b.unit.evidence_id)
            if pa is not None and pb is not None:
                return float(idx.matrix[pa] @ idx.matrix[pb])
            ta, tb = idx.terms[a.unit.evidence_id], idx.terms[b.unit.evidence_id]
            return len(ta & tb) / max(1, len(ta | tb))

        while pool and len(chosen) < k:
            best = max(pool, key=lambda h: lam * h.score - (1 - lam) * max(sim(h, c) for c in chosen))
            chosen.append(best)
            pool.remove(best)
        return chosen


def expand_followup(query: str, history: list[str]) -> str:
    """Resolve short follow-ups ("what are its units?") using the last question."""
    if not history:
        return query
    q_terms = content_terms(query)
    pronoun = re.search(r"\b(it|its|this|that|they|them|those|these|he|she|his|her)\b", query.lower())
    if len(q_terms) <= 3 and (pronoun or len(q_terms) <= 1):
        prev = history[-1]
        return f"{query} {prev}"
    return query
