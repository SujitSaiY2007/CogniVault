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

# Ollama settings (Local, zero-cost, private)
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:latest")

# AgentOS Server Settings
AGENTOS_HOST = os.environ.get("AGENTOS_HOST", "0.0.0.0")
AGENTOS_PORT = int(os.environ.get("AGENTOS_PORT", "8000"))
