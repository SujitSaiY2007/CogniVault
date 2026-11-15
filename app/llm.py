"""Optional language-model providers (Gemini, Ollama).

The app never depends on a model being available. Every caller has a
deterministic fallback, and a short circuit breaker stops repeated slow
failures from blocking requests.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from typing import Any, Optional

import httpx

log = logging.getLogger("cognivault.llm")


class LLMError(RuntimeError):
    pass


class LLM:
    name = "none"

    def generate(self, prompt: str, system: str = "", temperature: float = 0.2, max_tokens: int = 700) -> str:
        raise LLMError("No language model configured")

    def generate_json(self, prompt: str, system: str = "", temperature: float = 0.2, max_tokens: int = 1200) -> Any:
        text = self.generate(prompt + "\n\nReturn only valid JSON.", system, temperature, max_tokens)
        return parse_json_block(text)

    @property
    def available(self) -> bool:
        return False


def parse_json_block(text: str) -> Any:
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1).strip()
    start = min([i for i in (text.find("{"), text.find("[")) if i >= 0], default=-1)
    if start > 0:
        text = text[start:]
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMError(f"Model did not return valid JSON: {exc}") from exc


class _Breaker:
    def __init__(self, cooldown: float = 90.0):
        self.cooldown = cooldown
        self.until = 0.0
        self.lock = threading.Lock()

    def open(self) -> bool:
        return time.time() < self.until

    def trip(self) -> None:
        with self.lock:
            self.until = time.time() + self.cooldown


class GeminiLLM(LLM):
    def __init__(self, api_key: str, model: str):
        from google import genai  # type: ignore

        self.client = genai.Client(api_key=api_key)
        self.model = model
        self.name = f"gemini:{model}"
        self.breaker = _Breaker()

    @property
    def available(self) -> bool:
        return not self.breaker.open()

    def generate(self, prompt: str, system: str = "", temperature: float = 0.2, max_tokens: int = 700) -> str:
        if self.breaker.open():
            raise LLMError("Gemini temporarily disabled after a failure")
        from google.genai import types  # type: ignore

        try:
            res = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system or None, temperature=temperature, max_output_tokens=max_tokens
                ),
            )
            text = (res.text or "").strip()
            if not text:
                raise LLMError("Empty response")
            return text
        except LLMError:
            raise
        except Exception as exc:
            self.breaker.trip()
            log.warning("Gemini call failed: %s", type(exc).__name__)
            raise LLMError(str(exc)) from exc

    def describe_image(self, data: bytes, mime: str, context: str) -> str:
        from google.genai import types  # type: ignore

        if self.breaker.open():
            raise LLMError("Gemini temporarily disabled")
        try:
            res = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Part.from_bytes(data=data, mime_type=mime),
                    "Describe this figure from course material in 2-4 factual sentences for a student. "
                    "Transcribe any labels, axes, equations or numbers you can read. Do not guess beyond what is visible. "
                    f"Context: {context[:300]}",
                ],
                config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=300),
            )
            return (res.text or "").strip()
        except Exception as exc:
            self.breaker.trip()
            raise LLMError(str(exc)) from exc


class OllamaLLM(LLM):
    def __init__(self, host: str, model: str):
        self.host = host.rstrip("/")
        self.model = model
        self.name = f"ollama:{model}"
        self.breaker = _Breaker(60)

    @property
    def available(self) -> bool:
        return not self.breaker.open()

    def generate(self, prompt: str, system: str = "", temperature: float = 0.2, max_tokens: int = 700) -> str:
        if self.breaker.open():
            raise LLMError("Ollama temporarily disabled after a failure")
        try:
            r = httpx.post(
                f"{self.host}/api/generate",
                json={"model": self.model, "prompt": prompt, "system": system, "stream": False,
                      "options": {"temperature": temperature, "num_predict": max_tokens}},
                timeout=httpx.Timeout(60.0, connect=2.0),
            )
            r.raise_for_status()
            text = (r.json().get("response") or "").strip()
            if not text:
                raise LLMError("Empty response")
            return text
        except LLMError:
            raise
        except Exception as exc:
            self.breaker.trip()
            raise LLMError(str(exc)) from exc


def ollama_reachable(host: str) -> bool:
    try:
        return httpx.get(f"{host.rstrip('/')}/api/tags", timeout=1.5).status_code == 200
    except Exception:
        return False


def make_llm(provider: str, gemini_api_key: str, gemini_model: str, ollama_host: str, ollama_model: str) -> LLM:
    try:
        if provider in {"auto", "gemini"} and gemini_api_key:
            return GeminiLLM(gemini_api_key, gemini_model)
        if provider in {"auto", "ollama"} and ollama_reachable(ollama_host):
            return OllamaLLM(ollama_host, ollama_model)
    except Exception as exc:  # pragma: no cover
        log.warning("Model provider unavailable: %s", exc)
    return LLM()
