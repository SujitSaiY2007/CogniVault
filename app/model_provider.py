"""
CogniVault Unified Model Provider Adapter.

Supports:
1. Local Ollama (default, zero-cost, private offline baseline)
2. Google Gemini (free-tier cloud provider for hosted deployment)
3. Deterministic offline fallback (when credentials or daemons are unavailable)

Security & Governance Invariants:
- Server-side only; API keys are never returned in responses, client bundles, or logs.
- Fails clearly and safely when credentials are missing.
- Local Ollama remains the zero-cost local development default.
"""
from __future__ import annotations

import os
import json
import urllib.request
from typing import Any, Optional

# Attempt Agno model imports
try:
    from agno.models.ollama import Ollama
except ImportError:
    Ollama = None

try:
    from agno.models.google import Gemini
except ImportError:
    Gemini = None


# Default configuration
DEFAULT_OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
DEFAULT_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")


# ---------------------------------------------------------------------------
# Ollama Availability & Factory
# ---------------------------------------------------------------------------

def is_ollama_available(host: Optional[str] = None, timeout: float = 1.5) -> bool:
    """Check if the local Ollama daemon is reachable."""
    target_host = (host or os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)).rstrip("/")
    url = f"{target_host}/api/tags"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CogniVault/0.2"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status == 200
    except Exception:
        return False


def get_available_ollama_models(host: Optional[str] = None, timeout: float = 2.0) -> list[str]:
    """Retrieve list of locally installed Ollama model tags."""
    target_host = (host or os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST)).rstrip("/")
    url = f"{target_host}/api/tags"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CogniVault/0.2"})
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


# ---------------------------------------------------------------------------
# Google Gemini (Free Cloud Tier) Availability & Factory
# ---------------------------------------------------------------------------

def is_gemini_available() -> bool:
    """Check if Gemini credentials are configured and Gemini class is importable."""
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    return bool(api_key and Gemini is not None)


def create_gemini_model(model_id: Optional[str] = None) -> Optional[Any]:
    """Instantiate an Agno Gemini model wrapper if credentials are valid."""
    if not is_gemini_available():
        return None

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    target_model = model_id or os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)

    try:
        return Gemini(id=target_model, api_key=api_key)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Unified Provider Dispatcher
# ---------------------------------------------------------------------------

def get_active_provider_name() -> str:
    """
    Determines active provider name: 'gemini', 'ollama', or 'none'.
    Priority:
    1. Explicit MODEL_PROVIDER environment variable ('gemini' or 'ollama')
    2. Auto-detection: 'gemini' if GEMINI_API_KEY is present, else 'ollama'
    """
    configured = os.environ.get("MODEL_PROVIDER", "").strip().lower()

    if configured == "gemini":
        if is_gemini_available():
            return "gemini"
        return "ollama" if Ollama is not None else "none"

    if configured == "ollama":
        return "ollama" if Ollama is not None else "none"

    # Auto mode
    if is_gemini_available():
        return "gemini"
    if Ollama is not None:
        return "ollama"

    return "none"


def create_active_model(model_id: Optional[str] = None) -> Optional[Any]:
    """Instantiate the active model according to provider configuration."""
    provider = get_active_provider_name()
    if provider == "gemini":
        model = create_gemini_model(model_id=model_id)
        if model is not None:
            return model
    return create_ollama_model(model_id=model_id)


def get_active_provider_info() -> dict[str, Any]:
    """
    Returns public, safe telemetry for system status and health endpoints.
    Never exposes raw API keys or secret tokens.
    """
    configured = os.environ.get("MODEL_PROVIDER", "auto").strip().lower()
    provider = get_active_provider_name()
    ollama_ok = is_ollama_available()
    gemini_ok = is_gemini_available()

    active_model = None
    if provider == "gemini":
        active_model = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
    elif provider == "ollama":
        active_model = os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)

    info: dict[str, Any] = {
        "configured_provider": configured,
        "active_provider": provider,
        "active_model_name": active_model,
        "is_model_available": (gemini_ok if provider == "gemini" else (ollama_ok if provider == "ollama" else False)),
        "gemini_available": gemini_ok,
        "ollama_available": ollama_ok,
        "providers": {
            "gemini": {
                "configured": bool(os.environ.get("GEMINI_API_KEY")),
                "available": gemini_ok,
                "model": os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL),
                "tier": "free_cloud",
            },
            "ollama": {
                "host": os.environ.get("OLLAMA_HOST", DEFAULT_OLLAMA_HOST),
                "available": ollama_ok,
                "model": os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL),
                "tier": "local_private",
            },
        },
    }
    return info
