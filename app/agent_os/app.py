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
import threading
from pathlib import Path
from typing import Any, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, File, Header, HTTPException, Query, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from agno.os import AgentOS
except ImportError:
    AgentOS = None

from ..models import Citation, Difficulty, Modality, Question, QuestionOption, QuestionType, TutorResponse
from ..db import EvidenceDB
from ..ingest import ingest_file
from .service import AgentOSLearningService, AgentOSTutorService
from .supabase_store import SupabaseStore
from .supabase_accounts import SupabaseAuth, SupabaseUserMaterials


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


def _restore_user_progress(request: Request, owner_id: str) -> None:
    """Hydrate only this account's progress rows from its durable Supabase snapshot."""
    if not request.app.state.supabase_enabled:
        return
    snapshot = request.app.state.user_materials.get_progress_snapshot(owner_id) or {}
    db = request.app.state.service.db
    conn = db.conn
    for table in ("learner_states", "learner_interactions", "misconceptions", "error_signals"):
        columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if "learner_id" not in columns:
            continue
        conn.execute(f"DELETE FROM {table} WHERE learner_id=?", (owner_id,))
        rows = snapshot.get(table, [])
        for item in rows:
            selected = [column for column in columns if column in item]
            if not selected:
                continue
            placeholders = ",".join("?" for _ in selected)
            conn.execute(f"INSERT OR REPLACE INTO {table} ({','.join(selected)}) VALUES ({placeholders})", [item[column] for column in selected])
    conn.commit()


def _persist_user_progress(request: Request, owner_id: str) -> None:
    """Save just the learner-owned progress rows; shared curriculum data is excluded."""
    if not request.app.state.supabase_enabled:
        return
    db = request.app.state.service.db
    snapshot = {}
    for table in ("learner_states", "learner_interactions", "misconceptions", "error_signals"):
        columns = [row[1] for row in db.conn.execute(f"PRAGMA table_info({table})").fetchall()]
        if "learner_id" not in columns:
            snapshot[table] = []
            continue
        rows = db.conn.execute(f"SELECT * FROM {table} WHERE learner_id=?", (owner_id,)).fetchall()
        snapshot[table] = [dict(zip(columns, row)) for row in rows]
    request.app.state.user_materials.save_progress_snapshot(owner_id, snapshot)


def _bearer_token(authorization: Optional[str]) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sign in to access your private learning data.")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Sign in to access your private learning data.")
    return token


def _resolve_owner(request: Request, token: str) -> str:
    if request.app.state.supabase_enabled:
        resolved = request.app.state.supabase_auth.resolve_token(token)
        if not resolved:
            raise HTTPException(status_code=401, detail="Session expired. Sign in again.")
        return resolved[1]
    raise HTTPException(status_code=503, detail="Private Supabase storage is not configured.")


def verify_learner_boundary(learner_id: str, request: Request, x_learner_id: Optional[str] = Header(None, alias="X-Learner-Id"), authorization: Optional[str] = Header(None, alias="Authorization")) -> None:
    validate_learner_id_format(learner_id)
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sign in to access this learner profile.")
    token = authorization.split(" ", 1)[1].strip()
    if request.app.state.supabase_enabled:
        row = request.app.state.supabase_auth.resolve_token(token)
        if not row:
            raise HTTPException(status_code=401, detail="Your session expired. Please sign in again.")
        authenticated_learner_id = row[1]
    else:
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
    app.state.progress_lock = threading.RLock()

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
        learner_id = "user_" + username
        if app.state.supabase_enabled:
            app.state.supabase_auth.create_user(username, _password_hash(req.password), learner_id)
            token = secrets.token_urlsafe(36)
            app.state.supabase_auth.issue_session(token, username, learner_id)
            return AuthResponse(access_token=token, username=username, learner_id=learner_id)
        conn = _auth_connection(app.state.auth_db_path)
        try:
            conn.execute("INSERT INTO auth_users(username,password_hash,learner_id,created_at) VALUES(?,?,?,?)", (username, _password_hash(req.password), learner_id, int(time.time())))
            conn.commit()
            return _issue_session(conn, username, learner_id)
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="That username is already taken. Try signing in or choose another.")
        finally:
            conn.close()

    @app.post("/api/v1/auth/login", response_model=AuthResponse, tags=["Authentication"])
    def login(req: CredentialsRequest) -> AuthResponse:
        username = _normalize_username(req.username)
        if app.state.supabase_enabled:
            row = app.state.supabase_auth.get_user(username)
            if not row or not _password_matches(req.password, row["password_hash"]):
                raise HTTPException(status_code=401, detail="Username or password is incorrect.")
            token = secrets.token_urlsafe(36)
            app.state.supabase_auth.issue_session(token, username, row["learner_id"])
            return AuthResponse(access_token=token, username=username, learner_id=row["learner_id"])
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
        if app.state.supabase_enabled:
            row = app.state.supabase_auth.resolve_token(token)
            if not row:
                raise HTTPException(status_code=401, detail="Session expired. Sign in again.")
            return {"username": row[0], "learner_id": row[1]}
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
            if app.state.supabase_enabled:
                app.state.supabase_auth.revoke_token(token)
            else:
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
    def tutor_query(
        req: TutorQueryRequest, request: Request,
        authorization: Optional[str] = Header(None, alias="Authorization"),
    ) -> dict[str, Any]:
        """Answer using baseline material or the authenticated user's private course uploads."""
        if not req.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty.")
        if request.app.state.supabase_enabled:
            owner_id = _resolve_owner(request, _bearer_token(authorization))
            matches = request.app.state.user_materials.search_evidence(owner_id, req.query, limit=3)
            if not matches and request.app.state.user_materials.list_sources(owner_id):
                return TutorResponse(
                    query=req.query.strip(),
                    answer="I could not locate relevant evidence in your uploaded course materials, so I am abstaining rather than answering from unrelated material.",
                    citations=[], is_grounded=False, confidence=0.0,
                    support_status="unsupported",
                    unsupported_reason="No matching evidence was retrieved from this account's private uploads.",
                    reasoning_steps=["Searched only this account's private indexed evidence.", "No sufficiently relevant excerpt was located."],
                    metadata={"scope": "private_account_materials"},
                ).model_dump()
            if matches:
                citations = []
                for item in matches:
                    meta = item.get("metadata") or {}
                    citations.append(Citation(
                        evidence_id=item["evidence_id"], source_id=item["source_id"],
                        modality=Modality(item["modality"]), location=item.get("location") or {},
                        snippet=(item.get("evidence_text") or "")[:350],
                        source_title=meta.get("source_title") or "Your uploaded course material",
                    ))
                excerpts = []
                for citation in citations:
                    location = citation.location
                    locator = f"Page {location['page']}" if location.get("page") else (f"Slide {location['slide']}" if location.get("slide") else (f"Timestamp {location['timestamp']}" if location.get("timestamp") else "Course material"))
                    excerpts.append(f"{citation.source_title} — {locator}: {citation.snippet}")
                answer = "I found these relevant passages in your uploaded course materials. The excerpts below are source-grounded; I am not adding unsupported explanation.\n\n" + "\n\n".join(excerpts)
                return TutorResponse(query=req.query.strip(), answer=answer, citations=citations,
                    is_grounded=True, confidence=0.65, support_status="supported",
                    reasoning_steps=["Retrieved evidence from this account's private course material store.",
                                    "Returned excerpts with the original page, slide, or timestamp locators."],
                    metadata={"scope": "private_account_materials"}).model_dump()
        resp = learning_service.ask_tutor(req.query, topic=req.topic)
        return resp.model_dump()

    # =========================================================================
    # Evidence & Materials Endpoints
    # =========================================================================

    @app.get("/api/v1/evidence/search", tags=["Evidence"])
    def search_evidence(
        request: Request,
        q: str = Query(..., description="Search query string"),
        k: int = Query(5, ge=1, le=10, description="Number of results to retrieve"),
        mode: str = Query("hybrid", description="Retrieval mode: hybrid, lexical, or semantic"),
        authorization: Optional[str] = Header(None, alias="Authorization"),
    ) -> dict[str, Any]:
        """Search baseline course evidence plus owner-scoped private evidence."""
        public_results, trace = learning_service.search_evidence(q, k=k, mode=mode)
        results = [r.model_dump() for r in public_results]
        if request.app.state.supabase_enabled:
            owner_id = _resolve_owner(request, _bearer_token(authorization))
            private_results = request.app.state.user_materials.search_evidence(owner_id, q, limit=k)
            results = [{
                "evidence_id": item["evidence_id"], "source_id": item["source_id"],
                "score": float(item.get("score", 1)), "snippet": item["evidence_text"][:500],
                "location": item.get("location") or {}, "source_title": item.get("metadata", {}).get("source_title", "Your uploaded material"),
                "private": True,
            } for item in private_results] + results[:max(0, k-len(private_results))]
        return {
            "query": q, "mode": mode, "result_count": len(results),
            "unsupported": trace.unsupported and not (request.app.state.supabase_enabled and results),
            "reason": None if request.app.state.supabase_enabled and results else trace.reason,
            "results": results[:k],
        }

    @app.post("/api/v1/evidence/sync-chroma", tags=["Evidence"])
    def sync_chroma() -> dict[str, Any]:
        """Synchronize evidence records and embeddings from SQLite into ChromaDB."""
        count = learning_service.sync_chroma()
        return {"status": "success", "synced_units": count}

    @app.get("/api/v1/sources", tags=["Materials"])
    def list_sources(
        request: Request,
        authorization: Optional[str] = Header(None, alias="Authorization"),
    ) -> list[dict[str, Any]]:
        """List baseline curriculum sources plus only the signed-in account's private uploads."""
        public_sources = learning_service.list_sources()
        if request.app.state.supabase_enabled:
            token = _bearer_token(authorization)
            owner_id = _resolve_owner(request, token)
            private_sources = request.app.state.user_materials.list_sources(owner_id)
            private_sources = [{
                "source_id": item["source_id"], "title": item["title"], "modality": item["modality"],
                "path": item["filename"], "sha256": item["sha256"], "evidence_count": item["evidence_count"],
                "metadata": {"private": True, "file_size_bytes": item.get("file_size_bytes", 0)},
            } for item in private_sources]
            return public_sources + private_sources
        return public_sources

    @app.get("/api/v1/sources/{source_id}", tags=["Materials"])
    def get_source(
        source_id: str,
        request: Request,
        authorization: Optional[str] = Header(None, alias="Authorization"),
    ) -> dict[str, Any]:
        """Resolve a baseline source or the signed-in user's private source."""
        if request.app.state.supabase_enabled:
            owner_id = _resolve_owner(request, _bearer_token(authorization))
            private = request.app.state.user_materials.get_source(owner_id, source_id)
            if private:
                return {
                    "source_id": private["source_id"], "title": private["title"],
                    "modality": private["modality"], "path": private["filename"],
                    "sha256": private["sha256"], "evidence_count": private["evidence_count"],
                    "metadata": {"private": True, "file_size_bytes": private.get("file_size_bytes", 0)},
                }
        src = learning_service.get_source_details(source_id)
        if not src:
            raise HTTPException(status_code=404, detail=f"Source '{source_id}' not found.")
        return src

    @app.get("/api/v1/sources/{source_id}/evidence", tags=["Materials"])
    def get_source_evidence(
        source_id: str,
        request: Request,
        authorization: Optional[str] = Header(None, alias="Authorization"),
    ) -> list[dict[str, Any]]:
        """Return evidence only for public baseline material or owner-matched private sources."""
        if request.app.state.supabase_enabled:
            owner_id = _resolve_owner(request, _bearer_token(authorization))
            if request.app.state.user_materials.get_source(owner_id, source_id):
                return request.app.state.user_materials.list_evidence(owner_id, source_id)
        return learning_service.get_source_evidence(source_id)

    @app.delete("/api/v1/sources/{source_id}", tags=["Materials"])
    def delete_private_source(
        source_id: str, request: Request,
        authorization: Optional[str] = Header(None, alias="Authorization"),
    ) -> dict[str, Any]:
        """Delete only a source owned by the authenticated account, including its private blob."""
        if not request.app.state.supabase_enabled:
            raise HTTPException(status_code=503, detail="Configure Supabase to manage private uploads.")
        owner_id = _resolve_owner(request, _bearer_token(authorization))
        if not request.app.state.user_materials.delete_source(owner_id, source_id):
            raise HTTPException(status_code=404, detail="Private source not found.")
        return {"status": "deleted", "source_id": source_id}

    @app.post("/api/v1/ingest/upload", tags=["Materials"])
    async def upload_material(
        request: Request,
        file: UploadFile = File(...),
        authorization: Optional[str] = Header(None, alias="Authorization"),
    ) -> dict[str, Any]:
        """Persist a private upload in Supabase Storage and tenant-owned evidence rows."""
        if not request.app.state.supabase_enabled:
            raise HTTPException(status_code=503, detail="Configure Supabase to enable durable private uploads.")
        owner_id = _resolve_owner(request, _bearer_token(authorization))
        safe_filename = Path((file.filename or "").replace("\\", "/")).name
        if not safe_filename:
            raise HTTPException(status_code=400, detail="Filename cannot be empty.")
        suffix = Path(safe_filename).suffix.lower()
        if suffix not in {".pdf", ".pptx", ".txt", ".vtt", ".srt"}:
            raise HTTPException(status_code=400, detail=f"Unsupported format '{suffix}'.")
        existing = request.app.state.user_materials.list_sources(owner_id)
        if len(existing) >= 10:
            raise HTTPException(status_code=413, detail="Account upload limit reached (10 files).")
        used_bytes = sum(int(item.get("file_size_bytes", 0)) for item in existing)
        account_quota = 100 * 1024 * 1024
        global_used_bytes = request.app.state.user_materials.get_global_storage_usage()
        global_quota = 800 * 1024 * 1024  # leave headroom under Supabase Free 1 GB object-storage limit
        if global_used_bytes >= global_quota:
            raise HTTPException(status_code=413, detail="Shared project upload capacity reached. Try again after storage cleanup.")
        if used_bytes >= account_quota:
            raise HTTPException(status_code=413, detail="Account storage quota reached (100 MB).")

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as upload_tmp:
            bytes_read = 0
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                bytes_read += len(chunk)
                if bytes_read > MAX_UPLOAD_SIZE or used_bytes + bytes_read > account_quota or global_used_bytes + bytes_read > global_quota:
                    upload_tmp.close()
                    Path(upload_tmp.name).unlink(missing_ok=True)
                    raise HTTPException(status_code=413, detail="Upload exceeds the 25 MB per-file or 100 MB per-account limit.")
                upload_tmp.write(chunk)
            upload_path = Path(upload_tmp.name)

        temp_db_path = None
        storage_path = None
        source_id = None
        private_db = None
        try:
            # Run the existing evidence extractor against a disposable DB; never mix tenant records into the shared corpus.
            with tempfile.NamedTemporaryFile(delete=False, suffix=".sqlite") as db_tmp:
                temp_db_path = db_tmp.name
            private_db = EvidenceDB(temp_db_path)
            file_sha = hashlib.sha256(upload_path.read_bytes()).hexdigest()
            if any(item.get("sha256") == file_sha for item in existing):
                raise HTTPException(status_code=409, detail="This file is already uploaded to your account.")
            source_id = "src_" + hashlib.sha256(f"{owner_id}:{file_sha}".encode()).hexdigest()[:28]
            ingest_file(upload_path, private_db, source_id=source_id, title=Path(safe_filename).stem)
            source = private_db.get_source(source_id)
            evidence_units = [unit for unit in private_db.all_evidence() if unit.source_id == source_id]
            if len(evidence_units) > 2000 or sum(int(item.get("evidence_count", 0)) for item in existing) + len(evidence_units) > 10000:
                raise HTTPException(status_code=413, detail="Evidence indexing quota reached (2,000 chunks/file; 10,000/account).")
            storage_path = f"{owner_id}/{source_id}/{safe_filename}"
            mime_type = {".pdf": "application/pdf", ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation", ".txt": "text/plain", ".vtt": "text/vtt", ".srt": "application/x-subrip"}[suffix]
            request.app.state.supabase_store.upload_private(storage_path, upload_path.read_bytes(), mime_type)
            request.app.state.user_materials.create_source({
                "source_id": source_id, "owner_id": owner_id, "filename": safe_filename,
                "title": source.title if source else Path(safe_filename).stem,
                "modality": source.modality.value if source else suffix.lstrip("."),
                "sha256": file_sha, "storage_path": storage_path,
                "evidence_count": len(evidence_units), "file_size_bytes": bytes_read,
            })
            # Chunk REST inserts to bound request payload and prevent large bulk calls.
            batch = []
            for unit in evidence_units:
                batch.append({
                    "evidence_id": unit.evidence_id, "owner_id": owner_id, "source_id": source_id,
                    "modality": unit.modality.value, "evidence_text": unit.text,
                    "location": unit.location, "evidence_type": unit.evidence_type,
                    "metadata": {**(unit.metadata or {}), "source_title": source.title if source else Path(safe_filename).stem, "topics": unit.topics, "concepts": unit.concepts, "prerequisites": unit.prerequisites},
                })
                if len(batch) >= 100:
                    request.app.state.user_materials.create_evidence_batch(batch)
                    batch = []
            if batch:
                request.app.state.user_materials.create_evidence_batch(batch)
            return {"source_id": source_id, "title": source.title if source else Path(safe_filename).stem,
                    "modality": source.modality.value if source else suffix.lstrip("."),
                    "sha256": file_sha, "evidence_count": len(evidence_units), "status": "private_ingested"}
        except Exception:
            if source_id:
                request.app.state.user_materials.delete_source(owner_id, source_id)
            if storage_path:
                request.app.state.supabase_store.remove_private([storage_path])
            raise
        finally:
            if private_db is not None:
                private_db.close()
            if upload_path.exists():
                upload_path.unlink(missing_ok=True)
            if temp_db_path and Path(temp_db_path).exists():
                Path(temp_db_path).unlink(missing_ok=True)

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
        request: Request,
        x_learner_id: Optional[str] = Header(None, alias="X-Learner-Id"),
        authorization: Optional[str] = Header(None, alias="Authorization"),
    ) -> dict[str, Any]:
        """
        Submit learner answer for evaluation:
          1. Scores submission against verified key with exact physical citations.
          2. Updates BKT topic mastery P(L_t) in SQLite.
          3. Checks for misconception accumulation.
          4. Returns prerequisite-aware next recommendation.
        """
        verify_learner_boundary(req.learner_id, request, x_learner_id, authorization)
        _restore_user_progress(request, req.learner_id)
        try:
            result = learning_service.submit_assessment_answer(
                learner_id=req.learner_id, question_id=req.question_id,
                answer=req.answer, timestamp=req.timestamp,
            )
            _persist_user_progress(request, req.learner_id)
            return result
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # =========================================================================
    # Learner Model & BKT Tracking (Role 3: Learning Coach)
    # =========================================================================

    @app.get("/api/v1/learners", tags=["Learner"])
    def list_learners(
        request: Request,
        authorization: Optional[str] = Header(None, alias="Authorization"),
    ) -> list[dict[str, Any]]:
        """Return only the authenticated account's learner summary."""
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail="Sign in required.")
        token = authorization.split(" ", 1)[1].strip()
        if app.state.supabase_enabled:
            row = app.state.supabase_auth.resolve_token(token)
            if not row:
                raise HTTPException(status_code=401, detail="Session expired. Sign in again.")
            own_learner_id = row[1]
        else:
            conn = _auth_connection(app.state.auth_db_path)
            try:
                row = conn.execute("SELECT u.learner_id FROM auth_sessions s JOIN auth_users u ON u.username=s.username WHERE s.token_hash=? AND s.expires_at>?", (hashlib.sha256(token.encode()).hexdigest(), int(time.time()))).fetchone()
                if not row:
                    raise HTTPException(status_code=401, detail="Session expired. Sign in again.")
                own_learner_id = row[0]
            finally:
                conn.close()
        _restore_user_progress(request, own_learner_id)
        return [learner for learner in learning_service.list_learners() if learner.get("learner_id") == own_learner_id]

    @app.get(
        "/api/v1/learner/{learner_id}/profile",
        tags=["Learner"],
        dependencies=[Depends(verify_learner_boundary)],
    )
    def get_learner_profile(learner_id: str, request: Request) -> dict[str, Any]:
        """Get complete learner profile, mastery map, and interaction history."""
        _restore_user_progress(request, learner_id)
        profile = learning_service.get_learner_profile(learner_id)
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
    def get_learner_mastery(learner_id: str, request: Request) -> list[dict[str, Any]]:
        """Get durable BKT topic mastery records for the authenticated learner."""
        _restore_user_progress(request, learner_id)
        return learning_service.get_learner_topic_mastery(learner_id)

    @app.post(
        "/api/v1/learner/{learner_id}/observation",
        tags=["Learner"],
        dependencies=[Depends(verify_learner_boundary)],
    )
    def record_learner_observation(
        learner_id: str, req: ObservationRequest, request: Request,
    ) -> dict[str, Any]:
        """Record an observation and persist the resulting BKT learner snapshot."""
        _restore_user_progress(request, learner_id)
        result = learning_service.record_learning_observation(
            learner_id=learner_id, topic_id=req.topic_id,
            is_correct=req.is_correct, timestamp=req.timestamp,
        )
        _persist_user_progress(request, learner_id)
        return result

    @app.get(
        "/api/v1/learner/{learner_id}/misconceptions",
        tags=["Learner"],
        dependencies=[Depends(verify_learner_boundary)],
    )
    def get_misconceptions(
        learner_id: str, request: Request,
        topic_id: Optional[str] = Query(None, description="Optional topic filter"),
    ) -> list[dict[str, Any]]:
        """List active diagnosed misconceptions for the authenticated learner."""
        _restore_user_progress(request, learner_id)
        return learning_service.get_active_misconceptions(learner_id, topic_id=topic_id)

    @app.post(
        "/api/v1/learner/{learner_id}/misconceptions/{signal_id}/resolve",
        tags=["Learner"],
        dependencies=[Depends(verify_learner_boundary)],
    )
    def resolve_misconception(learner_id: str, signal_id: str, request: Request) -> dict[str, Any]:
        """Resolve a misconception and persist the updated learner snapshot."""
        _restore_user_progress(request, learner_id)
        misc = learning_service.db.get_misconception(signal_id)
        if misc:
            if misc.learner_id != learner_id:
                raise HTTPException(status_code=403, detail="Forbidden: Learner boundary mismatch.")
            topic_id = misc.topic_id
            concept_id = misc.concept_id
        else:
            topic_id = signal_id.replace(f"misc_{learner_id}_", "")
            concept_id = None
        result = learning_service.resolve_misconception(
            learner_id=learner_id, topic_id=topic_id, concept_id=concept_id,
        )
        _persist_user_progress(request, learner_id)
        return result

    @app.get(
        "/api/v1/learner/{learner_id}/recommendations",
        tags=["Learner"],
        dependencies=[Depends(verify_learner_boundary)],
    )
    def get_recommendations(
        learner_id: str, request: Request,
        active_topic_id: Optional[str] = Query(None, description="Optional active topic context"),
    ) -> dict[str, Any]:
        """Get prerequisite-aware recommendation from durable learner state."""
        _restore_user_progress(request, learner_id)
        return learning_service.get_recommendation(learner_id, active_topic_id=active_topic_id)

    @app.post(
        "/api/v1/learner/{learner_id}/intake",
        tags=["Learner"],
        dependencies=[Depends(verify_learner_boundary)],
    )
    def cold_start_intake(
        learner_id: str, req: ColdStartIntakeRequest, request: Request,
    ) -> dict[str, Any]:
        """Initialize the learner intake and persist the resulting mastery snapshot."""
        _restore_user_progress(request, learner_id)
        result = learning_service.cold_start_intake(
            learner_id=learner_id, initial_topic_masteries=req.initial_topic_masteries,
            diagnostic_responses=req.diagnostic_responses,
        )
        _persist_user_progress(request, learner_id)
        return result

    return app


# Default app instance
app = create_agent_os_app()
