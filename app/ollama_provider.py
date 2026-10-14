"""
Local Ollama and Cloud Model Provider Interface for Agno AgentOS.
Maintains full backward compatibility while delegating to unified model_provider.
"""
from __future__ import annotations

from .model_provider import (
    DEFAULT_OLLAMA_HOST,
    DEFAULT_OLLAMA_MODEL,
    create_active_model,
    create_gemini_model,
    create_ollama_model,
    get_active_provider_info,
    get_active_provider_name,
    get_available_ollama_models,
    is_gemini_available,
    is_ollama_available,
)

__all__ = [
    "DEFAULT_OLLAMA_HOST",
    "DEFAULT_OLLAMA_MODEL",
    "is_ollama_available",
    "get_available_ollama_models",
    "create_ollama_model",
    "is_gemini_available",
    "create_gemini_model",
    "get_active_provider_name",
    "create_active_model",
    "get_active_provider_info",
]
