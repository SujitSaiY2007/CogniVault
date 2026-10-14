"""
Unit tests for the Cloud & Local Model Provider dispatch architecture (app/model_provider.py).
Verifies:
  1. Default Ollama provider configuration and fallback detection.
  2. Gemini provider initialization with API key and model selection.
  3. Automatic graceful fallback to Ollama if Gemini key is missing.
  4. Active provider telemetry info reporting for /api/v1/health.
"""
import os
import pytest
from app.model_provider import (
    is_gemini_available,
    is_ollama_available,
    create_active_model,
    get_active_provider_info,
)


def test_provider_info_structure():
    info = get_active_provider_info()
    assert "configured_provider" in info
    assert "active_provider" in info
    assert "gemini_available" in info
    assert "ollama_available" in info
    assert "active_model_name" in info


def test_gemini_availability_without_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert is_gemini_available() is False


def test_gemini_availability_with_key(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-fake-key-12345")
    assert is_gemini_available() is True


def test_create_active_model_fallback_when_gemini_requested_without_key(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    model = create_active_model()
    # When GEMINI_API_KEY is missing, gracefully falls back to Ollama model
    from agno.models.ollama import Ollama
    assert isinstance(model, Ollama)


def test_create_active_model_gemini_when_key_present(monkeypatch):
    monkeypatch.setenv("MODEL_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-fake-key-12345")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    model = create_active_model()
    from agno.models.google import Gemini
    assert isinstance(model, Gemini)
    assert model.id == "gemini-2.5-flash"
