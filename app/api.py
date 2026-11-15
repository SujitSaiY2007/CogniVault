"""HTTP API (FastAPI). Run with: uvicorn app.api:app

Every route except /health requires a bearer session. A user can only read
or change their own learner state and their own uploads; the demo course is
shared read-only.
"""
from __future__ import annotations

import logging
import re
import secrets
import threading
import time
import uuid
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from .config import Settings, load_settings
from .models import PUBLIC_OWNER, Difficulty, QuestionType
from .persistence import StorageError, check_password, hash_password
from .service import CogniVault, ServiceError

log = logging.getLogger("cognivault.api")
LEARNER_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
USER_RE = re.compile(r"^[a-z0-9_.-]{3,32}$")


# ------------------------------------------------------------------- schemas
class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=1, max_length=256)


class TutorRequest(BaseModel):
    query: str = Field(max_length=2000)
    topic: Optional[str] = None
    history: list[str] = Field(default_factory=list, max_length=10)
    source_ids: Optional[list[str]] = None
    allow_general_knowledge: bool = False


class SelectRequest(BaseModel):
    topic_id: str
    served_question_ids: list[str] = Field(default_factory=list)
    target_difficulty: Optional[Difficulty] = None
    question_type: Optional[QuestionType] = None


class SubmitRequest(BaseModel):
    learner_id: Optional[str] = None
    question_id: str
    answer: str = Field(max_length=1000)
    timestamp: Optional[str] = None


class QuizRequest(BaseModel):
    topic_ids: list[str] = Field(default_factory=list)
    count: int = Field(8, ge=1, le=40)
    types: list[str] = Field(default_factory=list)
    difficulty: Optional[str] = None
    mode: str = "practice"


class QuizAnswer(BaseModel):
    question_id: str
    answer: str = Field(max_length=1000)


class ObservationRequest(BaseModel):
    topic_id: str
    is_correct: bool
    timestamp: Optional[str] = None


class IntakeRequest(BaseModel):
    initial_topic_masteries: Optional[dict[str, float]] = None
    diagnostic_responses: Optional[list[dict[str, Any]]] = None


class ReviewRequest(BaseModel):
    grade: int = Field(ge=0, le=5)


class PlanRequest(BaseModel):
    exam_date: Optional[str] = None
    minutes_per_day: int = Field(60, ge=10, le=600)


# ------------------------------------------------------------- rate limiting
class RateLimiter:
    """Sliding-window limiter per key. In-memory: fine for one instance."""

    def __init__(self):
        self.hits: dict[str, deque] = defaultdict(deque)
        self.lock = threading.Lock()

    def check(self, key: str, limit: int, window: float) -> None:
        now = time.time()
        with self.lock:
            q = self.hits[key]
            while q and now - q[0] > window:
                q.popleft()
            if len(q) >= limit:
                raise HTTPException(429, "Too many requests. Please wait a moment and try again.")
            q.append(now)


# ----------------------------------------------------------------- factory
def create_app(service: Optional[CogniVault] = None, settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or (service.settings if service else load_settings())
    svc = service or CogniVault(settings)
    if settings.seed_demo_course:
        try:
            svc.seed_demo_course()
        except Exception:  # pragma: no cover - never block start-up
            log.exception("Demo course seeding failed")

    app = FastAPI(title="CogniVault API", version="2.0.0",
                  description="Evidence-first tutoring, assessment and learner modelling over your own course material.")
    origins = list(settings.cors_origins) or ["*"]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=origins != ["*"],
                       allow_methods=["*"], allow_headers=["*"])
    app.state.service = svc
    limiter = RateLimiter()

    @app.exception_handler(ServiceError)
    async def _svc_error(_: Request, exc: ServiceError):
        return JSONResponse(status_code=exc.status, content={"detail": str(exc)})

    @app.exception_handler(StorageError)
    async def _storage_error(_: Request, exc: StorageError):
        return JSONResponse(status_code=503, content={"detail": f"Storage is unavailable right now: {exc}"})

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        ref = uuid.uuid4().hex[:8]
        log.exception("Unhandled error %s", ref)
        return JSONResponse(status_code=500, content={"detail": f"Something went wrong on our side (ref {ref}). Please try again."})

    # ------------------------------------------------------------- auth
    def current_user(request: Request, authorization: Optional[str] = Header(None)) -> str:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(401, "Please sign in.")
        token = authorization.split(" ", 1)[1].strip()
        try:
            row = svc.backend.resolve_session(token)
        except StorageError as exc:
            raise HTTPException(503, "Sign-in service is unavailable. Please retry.") from exc
        if not row:
            raise HTTPException(401, "Your session expired. Please sign in again.")
        learner_id = row[1]
        limiter.check("req:" + learner_id, 120, 60)
        svc.hydrate(learner_id)
        request.state.username = row[0]
        return learner_id

    def same_learner(learner_id: str, me: str = Depends(current_user)) -> str:
        if not LEARNER_RE.match(learner_id or ""):
            raise HTTPException(400, "Invalid learner id.")
        if learner_id != me:
            raise HTTPException(403, "You can only access your own learner profile.")
        return me

    def issue(username: str, learner_id: str) -> dict[str, Any]:
        token = secrets.token_urlsafe(36)
        svc.backend.create_session(token, username)
        return {"access_token": token, "token_type": "bearer", "username": username, "learner_id": learner_id}

    @app.get("/health", tags=["System"])
    @app.get("/api/v1/health", tags=["System"])
    def health():
        return svc.health()

    @app.post("/api/v1/auth/signup", tags=["Auth"])
    def signup(body: Credentials, request: Request):
        limiter.check("signup:" + (request.client.host if request.client else "?"), 10, 3600)
        username = body.username.strip().lower()
        if not USER_RE.match(username):
            raise HTTPException(400, "Username must be 3-32 characters: letters, numbers, dot, dash or underscore.")
        if len(body.password) < 8:
            raise HTTPException(400, "Password must be at least 8 characters.")
        learner_id = "u_" + uuid.uuid4().hex[:20]
        try:
            svc.backend.create_user(username, hash_password(body.password), learner_id)
        except StorageError as exc:
            if "taken" in str(exc):
                raise HTTPException(409, "That username is already taken.") from exc
            raise
        return issue(username, learner_id)

    @app.post("/api/v1/auth/login", tags=["Auth"])
    def login(body: Credentials, request: Request):
        limiter.check("login:" + (request.client.host if request.client else "?") + body.username.lower(), 10, 300)
        user = svc.backend.get_user(body.username.strip().lower())
        if not user or not check_password(body.password, user["password_hash"]):
            raise HTTPException(401, "Incorrect username or password.")
        return issue(user["username"], user["learner_id"])

    @app.get("/api/v1/auth/me", tags=["Auth"])
    def me(request: Request, learner_id: str = Depends(current_user)):
        return {"username": request.state.username, "learner_id": learner_id}

    @app.post("/api/v1/auth/logout", tags=["Auth"])
    def logout(authorization: Optional[str] = Header(None)):
        if authorization and authorization.lower().startswith("bearer "):
            try:
                svc.backend.delete_session(authorization.split(" ", 1)[1].strip())
            except StorageError:
                pass
        return {"status": "signed_out"}

    # ------------------------------------------------------------ tutor
    @app.post("/api/v1/tutor/query", tags=["Tutor"])
    def tutor(body: TutorRequest, me: str = Depends(current_user)):
        limiter.check("tutor:" + me, 30, 60)
        with svc.owner_lock(me):
            return svc.ask(me, body.query, body.history, body.topic, body.source_ids, body.allow_general_knowledge).model_dump()

    @app.get("/api/v1/evidence/search", tags=["Evidence"])
    def search(q: str = Query(..., max_length=500), k: int = Query(5, ge=1, le=20), mode: str = "hybrid", me: str = Depends(current_user)):
        hits = svc.retriever.search(q, me, k=k)
        return {"query": q, "mode": "hybrid", "result_count": len(hits), "unsupported": not hits, "reason": None if hits else "No matching passages.",
                "results": [{"evidence_id": h.unit.evidence_id, "source_id": h.unit.source_id, "score": h.score, "coverage": h.coverage,
                             "snippet": h.unit.text[:500], "location": h.unit.location} for h in hits]}

    # ---------------------------------------------------------- materials
    def source_view(s, me: str) -> dict[str, Any]:
        d = s.model_dump()
        d["owner"] = "you" if s.owner_id == me else "demo"
        d["topics"] = [{"topic_id": t.topic_id, "name": t.name} for t in svc.db.topics(me) if t.source_id == s.source_id]
        d.pop("owner_id", None)
        return d

    def own_or_public_source(source_id: str, me: str):
        s = svc.db.get_source(source_id)
        if not s or s.owner_id not in {PUBLIC_OWNER, me}:
            raise HTTPException(404, "Source not found.")
        return s

    @app.get("/api/v1/sources", tags=["Materials"])
    def sources(me: str = Depends(current_user)):
        return [source_view(s, me) for s in svc.db.sources(me)]

    @app.get("/api/v1/sources/{source_id}", tags=["Materials"])
    def source(source_id: str, me: str = Depends(current_user)):
        return source_view(own_or_public_source(source_id, me), me)

    @app.get("/api/v1/sources/{source_id}/evidence", tags=["Materials"])
    def source_evidence(source_id: str, me: str = Depends(current_user)):
        own_or_public_source(source_id, me)
        return [u.model_dump(exclude={"owner_id"}) for u in svc.db.evidence_for_source(source_id)]

    @app.delete("/api/v1/sources/{source_id}", tags=["Materials"])
    def delete_source(source_id: str, me: str = Depends(current_user)):
        s = own_or_public_source(source_id, me)
        if s.owner_id != me:
            raise HTTPException(403, "Demo course material cannot be deleted.")
        with svc.owner_lock(me):
            svc.delete_source(me, source_id)
        return {"status": "deleted", "source_id": source_id}

    @app.get("/api/v1/assets/{asset_id}", tags=["Materials"])
    def asset(asset_id: str, me: str = Depends(current_user)):
        rows = svc.db._q("SELECT a.mime_type, a.data, e.owner_id FROM assets a JOIN evidence e ON e.evidence_id=a.evidence_id WHERE a.asset_id=?", (asset_id,))
        if not rows or rows[0]["owner_id"] not in {PUBLIC_OWNER, me}:
            raise HTTPException(404, "Image not found.")
        return Response(content=rows[0]["data"], media_type=rows[0]["mime_type"], headers={"Cache-Control": "private, max-age=86400"})

    @app.post("/api/v1/ingest/upload", tags=["Materials"])
    async def upload(file: UploadFile = File(...), title: Optional[str] = None, me: str = Depends(current_user)):
        limiter.check("upload:" + me, 15, 3600)
        name = Path((file.filename or "").replace("\\", "/")).name
        if not name:
            raise HTTPException(400, "The file needs a name.")
        limit = settings.max_upload_mb * 1024 * 1024
        data = await file.read(limit + 1)
        if len(data) > limit:
            raise HTTPException(413, f"Files are limited to {settings.max_upload_mb} MB.")
        mine = svc.db.sources(me, include_public=False)
        if len(mine) >= settings.max_files_per_account:
            raise HTTPException(413, f"Your library is limited to {settings.max_files_per_account} files. Delete one to upload another.")
        used = sum(int(s.metadata.get("file_size_bytes", 0)) for s in mine)
        if used + len(data) > settings.max_account_mb * 1024 * 1024:
            raise HTTPException(413, f"Your library is limited to {settings.max_account_mb} MB in total.")
        with svc.owner_lock(me):
            return svc.ingest(me, data, name, title=title)

    @app.post("/api/v1/evidence/sync-chroma", tags=["Materials"])
    def reindex(me: str = Depends(current_user)):
        n = svc.retriever.ensure_embeddings()
        return {"status": "ok", "synced_units": n}

    @app.post("/api/v1/corpus/seed", tags=["Materials"])
    def seed(me: str = Depends(current_user)):
        return {"status": "seeded", "stats": svc.seed_demo_course()}

    # --------------------------------------------------------- curriculum
    @app.get("/api/v1/topics", tags=["Curriculum"])
    def topics(me: str = Depends(current_user)):
        return svc.topics(me)

    @app.get("/api/v1/course-map", tags=["Curriculum"])
    def course_map(me: str = Depends(current_user)):
        return svc.map(me)

    # --------------------------------------------------------- assessment
    @app.get("/api/v1/assessment/questions", tags=["Assessment"])
    def questions(topic_id: Optional[str] = None, difficulty: Optional[Difficulty] = None,
                  question_type: Optional[QuestionType] = None, me: str = Depends(current_user)):
        qs = svc.db.questions(me, topic_id)
        qs = [q for q in qs if (not difficulty or q.difficulty == difficulty) and (not question_type or q.question_type == question_type)]
        return [q.public() for q in qs]

    @app.post("/api/v1/assessment/select", tags=["Assessment"])
    def select(body: SelectRequest, me: str = Depends(current_user)):
        q = svc.next_question(me, body.topic_id, body.target_difficulty, body.served_question_ids, body.question_type)
        if not q:
            raise HTTPException(404, "No verified questions for this topic yet.")
        return q.public()

    @app.post("/api/v1/assessment/submit", tags=["Assessment"])
    def submit(body: SubmitRequest, me: str = Depends(current_user)):
        if body.learner_id and body.learner_id != me:
            raise HTTPException(403, "You can only submit answers for yourself.")
        with svc.owner_lock(me):
            return svc.submit(me, body.question_id, body.answer)

    @app.post("/api/v1/quiz", tags=["Assessment"])
    def create_quiz(body: QuizRequest, me: str = Depends(current_user)):
        with svc.owner_lock(me):
            return svc.create_quiz(me, body.topic_ids, body.count, body.types, body.difficulty, body.mode)

    @app.get("/api/v1/quiz", tags=["Assessment"])
    def quiz_history(me: str = Depends(current_user)):
        return svc.quiz_history(me)

    @app.post("/api/v1/diagnostic", tags=["Assessment"])
    def diagnostic(me: str = Depends(current_user)):
        with svc.owner_lock(me):
            return svc.diagnostic(me)

    @app.get("/api/v1/quiz/{session_id}", tags=["Assessment"])
    def get_quiz(session_id: str, me: str = Depends(current_user)):
        quiz = svc.db.get_quiz(session_id)
        if not quiz or quiz["learner_id"] != me:
            raise HTTPException(404, "Quiz not found.")
        quiz.pop("learner_id", None)
        quiz["questions"] = [q.public() for q in (svc.db.get_question(i) for i in quiz["question_ids"]) if q]
        return quiz

    @app.post("/api/v1/quiz/{session_id}/answer", tags=["Assessment"])
    def quiz_answer(session_id: str, body: QuizAnswer, me: str = Depends(current_user)):
        with svc.owner_lock(me):
            return svc.quiz_answer(me, session_id, body.question_id, body.answer)

    @app.post("/api/v1/quiz/{session_id}/finish", tags=["Assessment"])
    def quiz_finish(session_id: str, me: str = Depends(current_user)):
        with svc.owner_lock(me):
            return svc.finish_quiz(me, session_id)

    # ------------------------------------------------------------ learner
    @app.get("/api/v1/learners", tags=["Learner"])
    def learners(me: str = Depends(current_user)):
        p = svc.profile(me)
        return [{"learner_id": me, "topics_tracked": len(p["records"]), "total_attempts": p["total_attempts"],
                 "total_correct": p["total_correct"], "active_misconceptions": len(p["active_misconceptions"])}]

    @app.get("/api/v1/learner/{learner_id}/profile", tags=["Learner"])
    def profile(me: str = Depends(same_learner)):
        return svc.profile(me)

    @app.get("/api/v1/learner/{learner_id}/mastery", tags=["Learner"])
    def mastery(me: str = Depends(same_learner)):
        return svc.profile(me)["records"]

    @app.post("/api/v1/learner/{learner_id}/observation", tags=["Learner"])
    def observation(body: ObservationRequest, me: str = Depends(same_learner)):
        if not svc.db.get_topic(body.topic_id):
            raise HTTPException(404, "Topic not found.")
        with svc.owner_lock(me):
            m = svc.learner.observe_binary(me, body.topic_id, body.is_correct, body.timestamp)
            svc.save_progress(me)
            return m.model_dump()

    @app.get("/api/v1/learner/{learner_id}/misconceptions", tags=["Learner"])
    def misconceptions(topic_id: Optional[str] = None, me: str = Depends(same_learner)):
        return svc.misconceptions(me, topic_id)

    @app.post("/api/v1/learner/{learner_id}/misconceptions/{signal_id}/resolve", tags=["Learner"])
    def resolve(signal_id: str, me: str = Depends(same_learner)):
        with svc.owner_lock(me):
            return svc.resolve_misconception(me, signal_id)

    @app.get("/api/v1/learner/{learner_id}/recommendations", tags=["Learner"])
    def recommendations(active_topic_id: Optional[str] = None, me: str = Depends(same_learner)):
        return svc.recommendation(me, active_topic_id)

    @app.post("/api/v1/learner/{learner_id}/intake", tags=["Learner"])
    def intake(body: IntakeRequest, me: str = Depends(same_learner)):
        with svc.owner_lock(me):
            return svc.intake(me, body.initial_topic_masteries, body.diagnostic_responses)

    # -------------------------------------------------------------- study
    @app.get("/api/v1/flashcards", tags=["Study"])
    def flashcards(topic_id: Optional[str] = None, limit: int = Query(20, ge=1, le=100), me: str = Depends(current_user)):
        return svc.flashcards(me, topic_id, limit)

    @app.post("/api/v1/flashcards/{card_id}/review", tags=["Study"])
    def review(card_id: str, body: ReviewRequest, me: str = Depends(current_user)):
        with svc.owner_lock(me):
            return svc.review_flashcard(me, card_id, body.grade)

    @app.get("/api/v1/study-plan", tags=["Study"])
    def get_plan(me: str = Depends(current_user)):
        return svc.plan(me, None, 0)

    @app.post("/api/v1/study-plan", tags=["Study"])
    def post_plan(body: PlanRequest, me: str = Depends(current_user)):
        with svc.owner_lock(me):
            return svc.plan(me, body.exam_date, body.minutes_per_day)

    return app


_app: Optional[FastAPI] = None
_lock = threading.Lock()


def __getattr__(name: str):
    """Build the default app on first access (``uvicorn app.api:app``), not at import."""
    global _app
    if name == "app":
        with _lock:
            if _app is None:
                logging.basicConfig(level=logging.INFO)
                _app = create_app()
        return _app
    raise AttributeError(name)
