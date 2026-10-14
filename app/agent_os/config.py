"""
Configuration settings for CogniVault Agno AgentOS.
"""
from __future__ import annotations

import os
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = REPO_ROOT / "cognivault.db"
DEFAULT_CHROMA_DIR = REPO_ROOT / "data" / "chroma"

# Environment configuration
DB_PATH = os.environ.get("COGNIVAULT_DB_PATH", str(DEFAULT_DB_PATH))
CHROMA_PERSIST_DIR = os.environ.get("CHROMA_PERSIST_DIR", str(DEFAULT_CHROMA_DIR))

# Model Provider configuration: 'auto', 'gemini', or 'ollama'
MODEL_PROVIDER = os.environ.get("MODEL_PROVIDER", "auto")

# Ollama settings (Local, zero-cost, private default)
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:latest")

# Cloud model provider settings (Google Gemini free tier)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

# AgentOS Server Settings
AGENTOS_HOST = os.environ.get("AGENTOS_HOST", "0.0.0.0")
# Respect PORT env var provided by platforms like Render
PORT_ENV = os.environ.get("PORT")
AGENTOS_PORT = int(PORT_ENV) if PORT_ENV else int(os.environ.get("AGENTOS_PORT", "8000"))
