"""
Local Ollama model provider and health probe for Agno AgentOS.
Requires zero paid APIs, zero cloud credentials, and operates locally.
"""
from __future__ import annotations

import os
from typing import Any, Optional
import urllib.request
import json

try:
    from agno.models.ollama import Ollama
except ImportError:
    Ollama = None


DEFAULT_OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:latest")


def is_ollama_available(host: Optional[str] = None, timeout: float = 1.5) -> bool:
    """Check if the local Ollama daemon is reachable."""
    target_host = host or os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)
    # Strip trailing slash if present
    target_host = target_host.rstrip("/")
    url = f"{target_host}/api/tags"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CogniVault/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status == 200
    except Exception:
        return False


def get_available_ollama_models(host: Optional[str] = None, timeout: float = 2.0) -> list[str]:
    """Retrieve list of locally installed Ollama model tags."""
    target_host = (host or os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)).rstrip("/")
    url = f"{target_host}/api/tags"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CogniVault/0.1"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    except Exception:
        pass
    return []


def create_ollama_model(
    model_id: Optional[str] = None,
    host: Optional[str] = None,
) -> Optional[Any]:
    """Instantiate an Agno Ollama model wrapper if Ollama is available."""
    if Ollama is None:
        return None

    target_model = model_id or os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
    target_host = host or os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)

    try:
        return Ollama(id=target_model, host=target_host)
    except Exception:
        return None
