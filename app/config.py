"""Runtime settings read from environment variables.

All settings have safe defaults so the backend runs locally with no
configuration and no paid services.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    app_env: str = "development"
    data_dir: Path = ROOT / "data"
    db_path: Path = ROOT / "data" / "cognivault.sqlite"
    seed_demo_course: bool = True

    # Model providers. "auto" picks Gemini when a key is set, else Ollama
    # when reachable, else the deterministic extractive engine.
    model_provider: str = "auto"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    gemini_embed_model: str = "text-embedding-004"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:latest"

    # Embeddings: "hashing" (default, no download), "gemini", "sentence-transformers".
    embedding_provider: str = "hashing"

    # Persistence (optional). When both are set, accounts, uploads and
    # progress are stored in Supabase and survive container restarts.
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # Limits
    max_upload_mb: int = 25
    max_files_per_account: int = 20
    max_account_mb: int = 150
    cors_origins: tuple[str, ...] = field(default_factory=tuple)

    @property
    def supabase_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)


def load_settings() -> Settings:
    data_dir = Path(_env("CV_DATA_DIR", str(ROOT / "data")))
    db_path = Path(_env("CV_DB_PATH", str(data_dir / "cognivault.sqlite")))
    origins = tuple(o.strip() for o in _env("CORS_ORIGINS").split(",") if o.strip())
    return Settings(
        app_env=_env("APP_ENV", "development"),
        data_dir=data_dir,
        db_path=db_path,
        seed_demo_course=_env("SEED_DEMO_COURSE", "1") not in {"0", "false", "no"},
        model_provider=_env("MODEL_PROVIDER", "auto").lower(),
        gemini_api_key=_env("GEMINI_API_KEY"),
        gemini_model=_env("GEMINI_MODEL", "gemini-2.0-flash"),
        gemini_embed_model=_env("GEMINI_EMBED_MODEL", "text-embedding-004"),
        ollama_host=_env("OLLAMA_HOST", "http://localhost:11434").rstrip("/"),
        ollama_model=_env("OLLAMA_MODEL", "llama3.2:latest"),
        embedding_provider=_env("EMBEDDING_PROVIDER", "hashing").lower(),
        supabase_url=_env("SUPABASE_URL").rstrip("/"),
        supabase_service_role_key=_env("SUPABASE_SERVICE_ROLE_KEY"),
        max_upload_mb=_env_int("MAX_UPLOAD_MB", 25),
        max_files_per_account=_env_int("MAX_FILES_PER_ACCOUNT", 20),
        max_account_mb=_env_int("MAX_ACCOUNT_MB", 150),
        cors_origins=origins,
    )
