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
import sqlite3
import secrets
import hashlib
import hmac
import time
from pathlib import Path
from typing import Any, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, File, Header, HTTPException, Query, UploadFile, Request
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




class CredentialsRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=8, max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    learner_id: str


class ColdStartIntakeRequest(BaseModel):
    initial_topic_masteries: Optional[dict[str, float]] = None
    diagnostic_responses: Optional[list[dict[str, Any]]] = None


# -----------------------------------------------------------------------------
# Learner Boundary & Security Dependencies
# -----------------------------------------------------------------------------

import re

LEARNER_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]{1,64}$")
MAX_UPLOAD_SIZE = 25 * 1024 * 1024  # 25 MB


def validate_learner_id_format(learner_id: str) -> None:
    """Validates that learner_id conforms to safe alphanumeric/dash syntax."""
    if not learner_id or not LEARNER_ID_PATTERN.match(learner_id.strip()):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid learner ID format. Must be alphanumeric with - or _, max 64 characters.",
        )




def _auth_connection(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=10)
    conn.execute("""CREATE TABLE IF NOT EXISTS auth_users (username TEXT PRIMARY KEY, password_hash TEXT NOT NULL, learner_id TEXT NOT NULL UNIQUE, created_at INTEGER NOT NULL)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS auth_sessions (token_hash TEXT PRIMARY KEY, username TEXT NOT NULL, expires_at INTEGER NOT NULL, created_at INTEGER NOT NULL, FOREIGN KEY(username) REFERENCES auth_users(username) ON DELETE CASCADE)""")
    conn.commit()
    return conn


def _normalize_username(value: str) -> str:
    username = value.strip().lower()
    if not re.fullmatch(r"[a-zA-Z0-9_.-]{3,32}", username):
        raise HTTPException(status_code=400, detail="Username must be 3–32 characters using letters, numbers, dot, dash, or underscore.")
    return username


def _password_hash(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310000)
    return salt.hex() + ":" + derived.hex()


def _password_matches(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split(":", 1)
        candidate = _password_hash(password, bytes.fromhex(salt_hex)).split(":", 1)[1]
        return hmac.compare_digest(candidate, digest_hex)
    except (ValueError, TypeError):
        return False


def _issue_session(conn: sqlite3.Connection, username: str, learner_id: str) -> AuthResponse:
    token = secrets.token_urlsafe(36)
    now = int(time.time())
    conn.execute("DELETE FROM auth_sessions WHERE expires_at < ?", (now,))
    conn.execute("INSERT INTO auth_sessions(token_hash,username,expires_at,created_at) VALUES(?,?,?,?)", (hashlib.sha256(token.encode()).hexdigest(), username, now + 60 * 60 * 24 * 30, now))
    conn.commit()
    return AuthResponse(access_token=token, username=username, learner_id=learner_id)


def verify_learner_boundary(learner_id: str, request: Request, x_learner_id: Optional[str] = Header(None, alias="X-Learner-Id"), authorization: Optional[str] = Header(None, alias="Authorization")) -> None:
    validate_learner_id_format(learner_id)
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sign in to access this learner profile.")
    token = authorization.split(" ", 1)[1].strip()
    conn = _auth_connection(request.app.state.auth_db_path)
    try:
        row = conn.execute("SELECT u.learner_id FROM auth_sessions s JOIN auth_users u ON u.username=s.username WHERE s.token_hash=? AND s.expires_at>?", (hashlib.sha256(token.encode()).hexdigest(), int(time.time()))).fetchone()
    finally:
        conn.close()
    if not row:
        raise HTTPException(status_code=401, detail="Your session expired. Please sign in again.")
    authenticated_learner_id = row[0]
    if authenticated_learner_id != learner_id.strip() or (x_learner_id and x_learner_id.strip() != authenticated_learner_id):
        raise HTTPException(status_code=403, detail="You cannot access another user's learner profile.")


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
    app.state.auth_db_path = learning_service.db_path
    auth_conn = _auth_connection(app.state.auth_db_path)
    auth_conn.close()
    app.state.service = learning_service
    app.state.tutor_service = learning_service

    # Auto-seed default course corpus if database is empty on fresh container
    try:
        learning_service.seed_default_corpus_if_empty()
    except Exception as e:
        import logging
        logging.getLogger("cognivault").warning(f"Startup corpus seeding failed: {e}")

    # =========================================================================
    # System Endpoints
    # =========================================================================

    @app.get("/health", tags=["System"])
    @app.get("/api/v1/health", tags=["System"])
    def get_health() -> dict[str, Any]:
        """Health check probe verifying SQLite, ChromaDB, and local Ollama status."""
        return learning_service.health_check()


    # Username/password authentication (no email required)
    @app.post("/api/v1/auth/signup", response_model=AuthResponse, tags=["Authentication"])
    def signup(req: CredentialsRequest) -> AuthResponse:
        username = _normalize_username(req.username)
        if len(req.password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")
        conn = _auth_connection(app.state.auth_db_path)
        try:
            learner_id = "user_" + username
            try:
                conn.execute("INSERT INTO auth_users(username,password_hash,learner_id,created_at) VALUES(?,?,?,?)", (username, _password_hash(req.password), learner_id, int(time.time())))
                conn.commit()
            except sqlite3.IntegrityError:
                raise HTTPException(status_code=409, detail="That username is already taken. Try signing in or choose another.")
            return _issue_session(conn, username, learner_id)
        finally:
            conn.close()

    @app.post("/api/v1/auth/login", response_model=AuthResponse, tags=["Authentication"])
    def login(req: CredentialsRequest) -> AuthResponse:
        username = _normalize_username(req.username)
        conn = _auth_connection(app.state.auth_db_path)
        try:
            row = conn.execute("SELECT password_hash, learner_id FROM auth_users WHERE username=?", (username,)).fetchone()
            if not row or not _password_matches(req.password, row[0]):
                raise HTTPException(status_code=401, detail="Username or password is incorrect.")
            return _issue_session(conn, username, row[1])
        finally:
            conn.close()

    @app.get("/api/v1/auth/me", tags=["Authentication"])
    def auth_me(authorization: Optional[str] = Header(None, alias="Authorization")) -> dict[str, str]:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="Sign in required.")
        token = authorization.split(" ", 1)[1].strip()
        conn = _auth_connection(app.state.auth_db_path)
        try:
            row = conn.execute("SELECT u.username,u.learner_id FROM auth_sessions s JOIN auth_users u ON u.username=s.username WHERE s.token_hash=? AND s.expires_at>?", (hashlib.sha256(token.encode()).hexdigest(), int(time.time()))).fetchone()
            if not row:
                raise HTTPException(status_code=401, detail="Session expired. Sign in again.")
            return {"username": row[0], "learner_id": row[1]}
        finally:
            conn.close()

    @app.post("/api/v1/auth/logout", tags=["Authentication"])
    def auth_logout(authorization: Optional[str] = Header(None, alias="Authorization")) -> dict[str, str]:
        if authorization and authorization.lower().startswith("bearer "):
            token = authorization.split(" ", 1)[1].strip()
            conn = _auth_connection(app.state.auth_db_path)
            try:
                conn.execute("DELETE FROM auth_sessions WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),))
                conn.commit()
            finally:
                conn.close()
        return {"status": "signed_out"}

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
    async def upload_material(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
    ) -> dict[str, Any]:
        """
        Upload course material (PDF, PPTX, or TXT transcript).
        Extracts evidence units with exact locators, computes SHA-256 hash,
        and indexes into SQLite and ChromaDB.
        """
        safe_filename = Path(file.filename or "").name
        if not safe_filename:
            raise HTTPException(status_code=400, detail="Filename cannot be empty.")

        suffix = Path(safe_filename).suffix.lower()
        if suffix not in {".pdf", ".pptx", ".txt", ".vtt", ".srt"}:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format '{suffix}'. Supported: .pdf, .pptx, .txt, .vtt, .srt",
            )

        # Write to temporary file for safe ingestion with size enforcement
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            bytes_read = 0
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                bytes_read += len(chunk)
                if bytes_read > MAX_UPLOAD_SIZE:
                    tmp.close()
                    Path(tmp.name).unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=413,
                        detail=f"Payload too large. File exceeds {MAX_UPLOAD_SIZE // (1024 * 1024)}MB maximum limit.",
                    )
                tmp.write(chunk)
            tmp_path = Path(tmp.name)

        try:
            result = learning_service.ingest_document(
                tmp_path,
                title=Path(safe_filename).stem,
                sync_embeddings=False,
            )
            background_tasks.add_task(learning_service.build_and_sync_embeddings)
            return result
        finally:
            if tmp_path.exists():
                try:
                    tmp_path.unlink()
                except Exception:
                    pass

    @app.post("/api/v1/corpus/seed", tags=["Ingestion"])
    def seed_corpus() -> dict[str, Any]:
        """
        Manually trigger or reset baseline curriculum seeding (topics, concepts, questions, and baseline sources).
        """
        from ..corpus import seed_database_from_corpus
        data_dir = Path(__file__).resolve().parent.parent.parent / "data"
        stats = seed_database_from_corpus(learning_service.db, data_dir)
        return {"status": "seeded", "stats": stats}

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
        validate_learner_id_format(req.learner_id)
        if x_learner_id:
            validate_learner_id_format(x_learner_id)
            if x_learner_id.strip() != req.learner_id.strip():
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
        if misc:
            if misc.learner_id != learner_id:
                raise HTTPException(status_code=403, detail="Forbidden: Learner boundary mismatch.")
            topic_id = misc.topic_id
            concept_id = misc.concept_id
        else:
            topic_id = signal_id.replace(f"misc_{learner_id}_", "")
            concept_id = None
        return learning_service.resolve_misconception(
            learner_id=learner_id,
            topic_id=topic_id,
            concept_id=concept_id,
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
