"""Compatibility entry point. Prefer ``uvicorn app.api:app``."""
from __future__ import annotations


def __getattr__(name: str):
    if name == "app":
        from app import api

        return api.app
    raise AttributeError(name)
