"""
FastAPI and Agno AgentOS application entry point for CogniVault.
Exposes REST endpoints for grounded tutoring, hybrid retrieval, and evidence synchronization.
"""
from __future__ import annotations

import os
from typing import Any, Optional
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

try:
    from agno.os import AgentOS
except ImportError:
    AgentOS = None

from .service import AgentOSTutorService


class TutorQueryRequest(BaseModel):
    query: str
    topic: Optional[str] = None


class TutorQueryResponse(BaseModel):
    answer: str
    supported: bool
    confidence: float
    evidence_count: int
    citations: list[dict[str, Any]]
    reasoning_steps: list[str]
    evidence_ids: list[str]


def create_agent_os_app(service: Optional[AgentOSTutorService] = None) -> FastAPI:
    """Factory creating the FastAPI / AgentOS application with all endpoints."""
    tutor_service = service or AgentOSTutorService()

    # Create base AgentOS app if agno.os is available and agent is present
    app: FastAPI
    if AgentOS is not None and tutor_service.tutor_agent.agno_agent is not None:
        agent_os = AgentOS(
            id="cognivault-agentos",
            name="CogniVault AgentOS",
            description="Evidence-first adaptive learning with exact locators and fail-closed abstention",
            agents=[tutor_service.tutor_agent.agno_agent],
        )
        app = agent_os.get_app()
    else:
        app = FastAPI(
            title="CogniVault AgentOS API",
            description="Evidence-first adaptive learning API with exact locators and fail-closed abstention",
            version="0.1.0",
        )

    # Attach tutor service to app state for lifecycle access
    app.state.tutor_service = tutor_service

    @app.get("/health", tags=["System"])
    @app.get("/api/v1/health", tags=["System"])
    def get_health() -> dict[str, Any]:
        """Health check probe verifying SQLite, ChromaDB, and local Ollama status."""
        return tutor_service.health_check()

    @app.post("/api/v1/tutor/query", tags=["Tutoring"])
    def tutor_query(req: TutorQueryRequest) -> dict[str, Any]:
        """
        Query the grounded tutor agent.
        Returns grounded answer with exact citations, or deterministically abstains if unsupported.
        """
        if not req.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty.")
        resp = tutor_service.ask_tutor(req.query, topic=req.topic)
        return resp.model_dump()

    @app.get("/api/v1/evidence/search", tags=["Evidence"])
    def search_evidence(
        q: str = Query(..., description="Search query string"),
        k: int = Query(5, description="Number of results to retrieve"),
        mode: str = Query("hybrid", description="Retrieval mode: hybrid, lexical, or semantic"),
    ) -> dict[str, Any]:
        """Hybrid search across indexed course materials with physical locators."""
        results, trace = tutor_service.search_evidence(q, k=k, mode=mode)
        return {
            "query": q,
            "mode": mode,
            "result_count": len(results),
            "unsupported": trace.unsupported,
            "reason": trace.reason,
            "results": [r.model_dump() for r in results],
        }

    @app.get("/api/v1/sources", tags=["Materials"])
    def list_sources() -> list[dict[str, Any]]:
        """List all indexed learning materials with SHA-256 provenance."""
        return tutor_service.list_sources()

    @app.post("/api/v1/evidence/sync-chroma", tags=["Evidence"])
    def sync_chroma() -> dict[str, Any]:
        """Synchronize evidence records and embeddings from SQLite into ChromaDB."""
        count = tutor_service.sync_chroma()
        return {"status": "success", "synced_units": count}

    return app


# Default application instance for uvicorn
app = create_agent_os_app()
