"""
FastAPI and Agno AgentOS application entry point for CogniVault.
Exposes complete typed REST endpoints for the product loop:
  - Source ingestion with exact locators and SHA-256 provenance
  - Grounded Evidence Tutoring with citations or fail-closed abstention
  - Adaptive Assessments (MCQ, short-answer, numerical) with verified answer keys
  - Bayesian Knowledge Tracing (BKT) learner state persistence
  - Misconception diagnostics and prerequisite-aware recommendations
  - Cold-start diagnostic intake and learner isolation
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from agno.os import AgentOS
except ImportError:
    AgentOS = None

from ..models import Difficulty, Question, QuestionOption, QuestionType
from .service import AgentOSLearningService, AgentOSTutorService


# -----------------------------------------------------------------------------
# Typed Request & Response Schemas
# -----------------------------------------------------------------------------

class TutorQueryRequest(BaseModel):
    query: str
    topic: Optional[str] = None


class QuestionSelectRequest(BaseModel):
    topic_id: str
    served_question_ids: list[str] = Field(default_factory=list)
    target_difficulty: Optional[Difficulty] = None


class QuestionOptionInput(BaseModel):
    key: str
    text: str


class QuestionVerifyRequest(BaseModel):
    question_id: str = "temp_q"
    topic_id: str
    concept_id: Optional[str] = None
    prompt: str
    expected_answer: str
    evidence_ids: list[str]
    question_type: QuestionType = QuestionType.mcq
    difficulty: Difficulty = Difficulty.medium
    options: list[QuestionOptionInput] = Field(default_factory=list)
    tolerance: Optional[float] = None
    solution: str = ""


class QuestionGenerateRequest(BaseModel):
    question_id: str
    topic_id: str
    concept_id: Optional[str] = None
    prompt: str
    expected_answer: str
    evidence_ids: list[str]
    difficulty: Difficulty = Difficulty.medium
    question_type: QuestionType = QuestionType.mcq
    options: list[QuestionOptionInput] = Field(default_factory=list)
    tolerance: Optional[float] = None
    solution: str = ""
    metadata: Optional[dict[str, Any]] = None


class AssessmentSubmissionRequest(BaseModel):
    learner_id: str
    question_id: str
    answer: str
    timestamp: Optional[str] = None


class ObservationRequest(BaseModel):
    topic_id: str
    is_correct: bool
    timestamp: Optional[str] = None


class LearnerCreateRequest(BaseModel):
    learner_id: str
    name: Optional[str] = None


class ColdStartIntakeRequest(BaseModel):
    initial_topic_masteries: Optional[dict[str, float]] = None
    diagnostic_responses: Optional[list[dict[str, Any]]] = None


# -----------------------------------------------------------------------------
# Learner Boundary / Authorization Dependency
# -----------------------------------------------------------------------------

def verify_learner_boundary(
    learner_id: str,
    x_learner_id: Optional[str] = Header(None, alias="X-Learner-Id"),
) -> None:
    """
    Enforces authorization boundary:
    If client presents an X-Learner-Id header, it must match the path's learner_id.
    Prevents learner A from reading or mutating learner B's state.
    """
    if x_learner_id and x_learner_id.strip() != learner_id.strip():
        raise HTTPException(
            status_code=403,
            detail=f"Forbidden: Learner boundary mismatch. Header '{x_learner_id}' cannot mutate or read learner '{learner_id}'.",
        )


# -----------------------------------------------------------------------------
# Application Factory
# -----------------------------------------------------------------------------

def create_agent_os_app(service: Optional[AgentOSLearningService] = None) -> FastAPI:
    """Factory creating the FastAPI / AgentOS application with all endpoints."""
    learning_service = service or AgentOSLearningService()

    app: FastAPI
    agents_list = []
    if learning_service.tutor_agent.agno_agent is not None:
        agents_list.append(learning_service.tutor_agent.agno_agent)
    if learning_service.assessment_agent.agno_agent is not None:
        agents_list.append(learning_service.assessment_agent.agno_agent)
    if learning_service.coach_agent.agno_agent is not None:
        agents_list.append(learning_service.coach_agent.agno_agent)

    if AgentOS is not None and agents_list:
        agent_os = AgentOS(
            id="cognivault-agentos",
            name="CogniVault AgentOS",
            description="Evidence-first adaptive learning with exact locators and fail-closed abstention",
            agents=agents_list,
        )
        app = agent_os.get_app()
    else:
        app = FastAPI(
            title="CogniVault AgentOS API",
            description="Evidence-first adaptive learning API with exact locators, verified assessments, and BKT modeling",
            version="0.2.0",
        )

    # Enable CORS for local Next.js frontend and external tools
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Attach service to app state for lifecycle access
    app.state.service = learning_service
    app.state.tutor_service = learning_service

    # =========================================================================
    # System Endpoints
    # =========================================================================

    @app.get("/health", tags=["System"])
    @app.get("/api/v1/health", tags=["System"])
    def get_health() -> dict[str, Any]:
        """Health check probe verifying SQLite, ChromaDB, and local Ollama status."""
        return learning_service.health_check()

    # =========================================================================
    # Tutoring Endpoints (Role 1: Evidence Tutor)
    # =========================================================================

    @app.post("/api/v1/tutor/query", tags=["Tutoring"])
    def tutor_query(req: TutorQueryRequest) -> dict[str, Any]:
        """
        Query the grounded tutor agent.
        Returns grounded answer with exact citations, or deterministically abstains if unsupported.
        """
        if not req.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty.")
        resp = learning_service.ask_tutor(req.query, topic=req.topic)
        return resp.model_dump()

    # =========================================================================
    # Evidence & Materials Endpoints
    # =========================================================================

    @app.get("/api/v1/evidence/search", tags=["Evidence"])
    def search_evidence(
        q: str = Query(..., description="Search query string"),
        k: int = Query(5, description="Number of results to retrieve"),
        mode: str = Query("hybrid", description="Retrieval mode: hybrid, lexical, or semantic"),
    ) -> dict[str, Any]:
        """Hybrid search across indexed course materials with physical locators."""
        results, trace = learning_service.search_evidence(q, k=k, mode=mode)
        return {
            "query": q,
            "mode": mode,
            "result_count": len(results),
            "unsupported": trace.unsupported,
            "reason": trace.reason,
            "results": [r.model_dump() for r in results],
        }

    @app.post("/api/v1/evidence/sync-chroma", tags=["Evidence"])
    def sync_chroma() -> dict[str, Any]:
        """Synchronize evidence records and embeddings from SQLite into ChromaDB."""
        count = learning_service.sync_chroma()
        return {"status": "success", "synced_units": count}

    @app.get("/api/v1/sources", tags=["Materials"])
    def list_sources() -> list[dict[str, Any]]:
        """List all indexed learning materials with SHA-256 provenance."""
        return learning_service.list_sources()

    @app.get("/api/v1/sources/{source_id}", tags=["Materials"])
    def get_source(source_id: str) -> dict[str, Any]:
        """Get source metadata and evidence summary."""
        src = learning_service.get_source_details(source_id)
        if not src:
            raise HTTPException(status_code=404, detail=f"Source '{source_id}' not found.")
        return src

    @app.get("/api/v1/sources/{source_id}/evidence", tags=["Materials"])
    def get_source_evidence(source_id: str) -> list[dict[str, Any]]:
        """List all extracted evidence units for a specific source."""
        return learning_service.get_source_evidence(source_id)

    @app.post("/api/v1/ingest/upload", tags=["Materials"])
    async def upload_material(file: UploadFile = File(...)) -> dict[str, Any]:
        """
        Upload course material (PDF, PPTX, or TXT transcript).
        Extracts evidence units with exact locators, computes SHA-256 hash,
        and indexes into SQLite and ChromaDB.
        """
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in {".pdf", ".pptx", ".txt", ".vtt", ".srt"}:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format '{suffix}'. Supported: .pdf, .pptx, .txt",
            )

        # Write to temporary file for safe ingestion
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = Path(tmp.name)

        try:
            result = learning_service.ingest_document(tmp_path)
            return result
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass

    @app.get("/api/v1/topics", tags=["Curriculum"])
    def list_topics() -> list[dict[str, Any]]:
        """List curriculum topics, concepts, and prerequisite topology."""
        return learning_service.list_topics()

    # =========================================================================
    # Assessment Endpoints (Role 2: Assessment)
    # =========================================================================

    @app.get("/api/v1/assessment/questions", tags=["Assessment"])
    def list_questions(
        topic_id: Optional[str] = Query(None, description="Filter by topic"),
        difficulty: Optional[Difficulty] = Query(None, description="Filter by difficulty"),
        question_type: Optional[QuestionType] = Query(None, description="Filter by question type"),
    ) -> list[dict[str, Any]]:
        """List questions matching optional topic/difficulty/type filters."""
        return learning_service.list_questions(
            topic_id=topic_id,
            difficulty=difficulty,
            question_type=question_type,
        )

    @app.get("/api/v1/assessment/question/{question_id}", tags=["Assessment"])
    def get_question(question_id: str) -> dict[str, Any]:
        """Get single question by ID."""
        q = learning_service.get_question(question_id)
        if not q:
            raise HTTPException(status_code=404, detail=f"Question '{question_id}' not found.")
        return q

    @app.post("/api/v1/assessment/select", tags=["Assessment"])
    def select_adaptive_question(req: QuestionSelectRequest) -> dict[str, Any]:
        """
        Adaptively select candidate practice question for a topic.
        Applies repetition suppression using served question IDs and fingerprints.
        """
        q = learning_service.select_adaptive_question(
            topic_id=req.topic_id,
            served_question_ids=req.served_question_ids,
            target_difficulty=req.target_difficulty,
        )
        if not q:
            raise HTTPException(
                status_code=404,
                detail=f"No available verified questions found for topic '{req.topic_id}'.",
            )
        return q

    @app.post("/api/v1/assessment/verify", tags=["Assessment"])
    def verify_question(req: QuestionVerifyRequest) -> dict[str, Any]:
        """
        Deterministically verifies question prompt, options, answer key, and evidence linkage.
        """
        q = Question(
            question_id=req.question_id,
            topic_id=req.topic_id,
            concept_id=req.concept_id,
            evidence_ids=req.evidence_ids,
            difficulty=req.difficulty,
            question_type=req.question_type,
            prompt=req.prompt,
            options=[QuestionOption(key=o.key, text=o.text) for o in req.options],
            expected_answer=req.expected_answer,
            tolerance=req.tolerance,
            solution=req.solution,
        )
        result = learning_service.verify_question(q)
        return result.model_dump()

    @app.post("/api/v1/assessment/generate", tags=["Assessment"])
    def generate_question(req: QuestionGenerateRequest) -> dict[str, Any]:
        """
        Create, verify, and store question from course evidence.
        """
        q = learning_service.assessment_agent.generate_and_verify_question(
            question_id=req.question_id,
            topic_id=req.topic_id,
            prompt=req.prompt,
            expected_answer=req.expected_answer,
            evidence_ids=req.evidence_ids,
            concept_id=req.concept_id,
            difficulty=req.difficulty,
            question_type=req.question_type,
            options=[QuestionOption(key=o.key, text=o.text) for o in req.options],
            tolerance=req.tolerance,
            solution=req.solution,
            metadata=req.metadata,
        )
        return q.model_dump()

    @app.post("/api/v1/assessment/submit", tags=["Assessment"])
    def submit_assessment(
        req: AssessmentSubmissionRequest,
        x_learner_id: Optional[str] = Header(None, alias="X-Learner-Id"),
    ) -> dict[str, Any]:
        """
        Submit learner answer for evaluation:
          1. Scores submission against verified key with exact physical citations.
          2. Updates BKT topic mastery P(L_t) in SQLite.
          3. Checks for misconception accumulation.
          4. Returns prerequisite-aware next recommendation.
        """
        if x_learner_id and x_learner_id.strip() != req.learner_id.strip():
            raise HTTPException(
                status_code=403,
                detail=f"Forbidden: Learner boundary mismatch. Header '{x_learner_id}' cannot mutate or read learner '{req.learner_id}'.",
            )
        try:
            return learning_service.submit_assessment_answer(
                learner_id=req.learner_id,
                question_id=req.question_id,
                answer=req.answer,
                timestamp=req.timestamp,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # =========================================================================
    # Learner Model & BKT Tracking (Role 3: Learning Coach)
    # =========================================================================

    @app.get("/api/v1/learners", tags=["Learner"])
    def list_learners() -> list[dict[str, Any]]:
        """List distinct active learners with summary metrics."""
        return learning_service.list_learners()

    @app.get(
        "/api/v1/learner/{learner_id}/profile",
        tags=["Learner"],
        dependencies=[Depends(verify_learner_boundary)],
    )
    def get_learner_profile(learner_id: str) -> dict[str, Any]:
        """Get complete learner profile, mastery map, and interaction history."""
        profile = learning_service.get_learner_profile(learner_id)
        # Convert records to JSON serializable dictionaries
        profile_json = dict(profile)
        if "records" in profile_json:
            profile_json["records"] = [
                r.model_dump() if hasattr(r, "model_dump") else r
                for r in profile_json["records"]
            ]
        return profile_json

    @app.get(
        "/api/v1/learner/{learner_id}/mastery",
        tags=["Learner"],
        dependencies=[Depends(verify_learner_boundary)],
    )
    def get_learner_mastery(learner_id: str) -> list[dict[str, Any]]:
        """Get BKT topic mastery records for learner."""
        return learning_service.get_learner_topic_mastery(learner_id)

    @app.post(
        "/api/v1/learner/{learner_id}/observation",
        tags=["Learner"],
        dependencies=[Depends(verify_learner_boundary)],
    )
    def record_learner_observation(
        learner_id: str,
        req: ObservationRequest,
    ) -> dict[str, Any]:
        """
        Record a verified learning observation (from assessment or defined tutor exchange).
        Updates BKT mastery P(L_t) and persists to SQLite.
        """
        return learning_service.record_learning_observation(
            learner_id=learner_id,
            topic_id=req.topic_id,
            is_correct=req.is_correct,
            timestamp=req.timestamp,
        )

    @app.get(
        "/api/v1/learner/{learner_id}/misconceptions",
        tags=["Learner"],
        dependencies=[Depends(verify_learner_boundary)],
    )
    def get_misconceptions(
        learner_id: str,
        topic_id: Optional[str] = Query(None, description="Optional topic filter"),
    ) -> list[dict[str, Any]]:
        """List active diagnosed student misconceptions and remediation recommendations."""
        return learning_service.get_active_misconceptions(learner_id, topic_id=topic_id)

    @app.post(
        "/api/v1/learner/{learner_id}/misconceptions/{signal_id}/resolve",
        tags=["Learner"],
        dependencies=[Depends(verify_learner_boundary)],
    )
    def resolve_misconception(learner_id: str, signal_id: str) -> dict[str, Any]:
        """Mark misconception resolved after successful foundational remediation."""
        misc = learning_service.db.get_misconception(signal_id)
        if not misc or misc.learner_id != learner_id:
            raise HTTPException(status_code=404, detail="Misconception signal not found.")
        return learning_service.resolve_misconception(
            learner_id=learner_id,
            topic_id=misc.topic_id,
            concept_id=misc.concept_id,
        )

    @app.get(
        "/api/v1/learner/{learner_id}/recommendations",
        tags=["Learner"],
        dependencies=[Depends(verify_learner_boundary)],
    )
    def get_recommendations(
        learner_id: str,
        active_topic_id: Optional[str] = Query(None, description="Optional active topic context"),
    ) -> dict[str, Any]:
        """Get prerequisite-aware next learning action recommendation."""
        return learning_service.get_recommendation(learner_id, active_topic_id=active_topic_id)

    @app.post(
        "/api/v1/learner/{learner_id}/intake",
        tags=["Learner"],
        dependencies=[Depends(verify_learner_boundary)],
    )
    def cold_start_intake(
        learner_id: str,
        req: ColdStartIntakeRequest,
    ) -> dict[str, Any]:
        """
        Perform cold-start diagnostic intake for fresh learner.
        Initializes baseline topic masteries in SQLite without fabricating numbers.
        """
        return learning_service.cold_start_intake(
            learner_id=learner_id,
            initial_topic_masteries=req.initial_topic_masteries,
            diagnostic_responses=req.diagnostic_responses,
        )

    return app


# Default app instance
app = create_agent_os_app()
