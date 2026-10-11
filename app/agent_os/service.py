"""
AgentOS Tutor Service orchestrating database, ChromaDB store, retrieval, and Agno Agent.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from ..chroma_store import ChromaEvidenceStore
from ..db import EvidenceDB
from ..models import TutorResponse
from ..retrieval import HybridRetriever
from ..source_resolver import SourceResolver
from ..sufficiency import EvidenceGate
from ..ollama_provider import is_ollama_available, get_available_ollama_models
from .config import DB_PATH, CHROMA_PERSIST_DIR, OLLAMA_HOST, OLLAMA_MODEL
from .tutor_agent import EvidenceTutorAgent


class AgentOSTutorService:
    """Unified service coordinating Agno AgentOS and local evidence components."""

    def __init__(
        self,
        db_path: Optional[str | Path] = None,
        chroma_dir: Optional[str | Path] = None,
        in_memory_chroma: bool = False,
    ):
        self.db_path = str(db_path or DB_PATH)
        self.db = EvidenceDB(self.db_path)

        # Initialize ChromaDB persistent vector store
        self.chroma_store = ChromaEvidenceStore(
            persist_directory=chroma_dir or CHROMA_PERSIST_DIR,
            in_memory=in_memory_chroma,
        )

        # Initialize HybridRetriever with ChromaDB support
        self.retriever = HybridRetriever(self.db, chroma_store=self.chroma_store)
        self.gate = EvidenceGate()
        self.resolver = SourceResolver(self.db)

        # Initialize Evidence Tutor Agent
        self.tutor_agent = EvidenceTutorAgent(
            db=self.db,
            retriever=self.retriever,
            gate=self.gate,
            resolver=self.resolver,
            model_id=OLLAMA_MODEL,
            host=OLLAMA_HOST,
        )

    def ask_tutor(self, query: str, topic: Optional[str] = None) -> TutorResponse:
        """Ask a question to the evidence tutor agent."""
        return self.tutor_agent.ask(query, topic=topic)

    def search_evidence(self, query: str, k: int = 5, mode: str = "hybrid"):
        """Search indexed learning material."""
        return self.retriever.search(query, k=k, mode=mode)

    def sync_chroma(self) -> int:
        """Synchronize evidence records and embeddings from SQLite into ChromaDB."""
        return self.chroma_store.sync_from_sqlite(self.db, embedder=self.retriever._model())

    def list_sources(self) -> list[dict[str, Any]]:
        """List all indexed sources with provenance metadata."""
        sources = list(self.db.all_sources())
        return [
            {
                "source_id": s.source_id,
                "title": s.title,
                "modality": s.modality.value if hasattr(s.modality, "value") else str(s.modality),
                "path": s.path,
                "sha256": s.sha256,
                "metadata": s.metadata,
            }
            for s in sources
        ]

    def health_check(self) -> dict[str, Any]:
        """Perform system health check across local components."""
        ollama_ok = is_ollama_available(OLLAMA_HOST)
        models = get_available_ollama_models(OLLAMA_HOST) if ollama_ok else []
        return {
            "status": "healthy",
            "sqlite_db": {
                "path": self.db_path,
                "sources_count": len(list(self.db.all_sources())),
                "evidence_count": len(list(self.db.all_evidence())),
            },
            "chroma_db": {
                "persist_directory": self.chroma_store.persist_directory,
                "indexed_units": self.chroma_store.count(),
            },
            "ollama": {
                "host": OLLAMA_HOST,
                "available": ollama_ok,
                "configured_model": OLLAMA_MODEL,
                "installed_models": models,
            },
            "agno_agent": {
                "initialized": self.tutor_agent.agno_agent is not None,
                "name": "CogniVault Evidence Tutor",
            },
        }

    def close(self):
        """Close database connections."""
        self.db.close()
