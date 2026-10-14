"""
AgentOS Learning Service orchestrating database, ChromaDB store, retrieval,
and bounded Agno Agents (Evidence Tutor, Assessment, Learning Coach).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from ..assessment import AssessmentEngine, DeterministicQuestionVerifier
from ..chroma_store import ChromaEvidenceStore
from ..db import EvidenceDB
from ..ingest import ingest_file
from ..learner_model import LearnerStateManager
from ..misconceptions import MisconceptionDetector
from ..models import (
    AnswerEvaluation,
    Difficulty,
    LearnerSubmission,
    Question,
    QuestionType,
    QuestionVerificationResult,
    Recommendation,
    TopicMasteryRecord,
    TutorResponse,
)
from ..model_provider import get_active_provider_info
from ..ollama_provider import get_available_ollama_models, is_ollama_available
from ..recommendation import AdaptiveRecommendationEngine
from ..retrieval import HybridRetriever, build_embeddings
from ..source_resolver import SourceResolver
from ..sufficiency import EvidenceGate
from .assessment_agent import AssessmentAgent
from .config import CHROMA_PERSIST_DIR, DB_PATH, OLLAMA_HOST, OLLAMA_MODEL
from .learning_coach import LearningCoachAgent
from .tutor_agent import EvidenceTutorAgent
from .workflow import CogniVaultLearningWorkflow


class AgentOSLearningService:
    """Unified service coordinating Agno AgentOS, local evidence, assessment, and BKT modeling."""

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

        # Initialize Deterministic Assessment and Learner Modeling Engines
        self.verifier = DeterministicQuestionVerifier()
        self.assessment_engine = AssessmentEngine(self.db, verifier=self.verifier)
        self.state_manager = LearnerStateManager(self.db)
        self.misconception_detector = MisconceptionDetector(self.db)
        self.recommendation_engine = AdaptiveRecommendationEngine(self.db)

        # Initialize Three Bounded Agno Agents
        self.tutor_agent = EvidenceTutorAgent(
            db=self.db,
            retriever=self.retriever,
            gate=self.gate,
            resolver=self.resolver,
            model_id=OLLAMA_MODEL,
            host=OLLAMA_HOST,
        )
        self.assessment_agent = AssessmentAgent(
            db=self.db,
            assessment_engine=self.assessment_engine,
            verifier=self.verifier,
            model_id=OLLAMA_MODEL,
            host=OLLAMA_HOST,
        )
        self.coach_agent = LearningCoachAgent(
            db=self.db,
            state_manager=self.state_manager,
            misconception_detector=self.misconception_detector,
            recommendation_engine=self.recommendation_engine,
            model_id=OLLAMA_MODEL,
            host=OLLAMA_HOST,
        )

        # Initialize Unified Learning Workflow
        self.workflow = CogniVaultLearningWorkflow(
            tutor_agent=self.tutor_agent,
            assessment_agent=self.assessment_agent,
            coach_agent=self.coach_agent,
            db=self.db,
        )

    # -------------------------------------------------------------------------
    # Tutoring & Evidence Operations (Chat 01 Foundation Preserved)
    # -------------------------------------------------------------------------

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
                "evidence_count": len([e for e in self.db.all_evidence() if e.source_id == s.source_id]),
            }
            for s in sources
        ]

    def get_source_details(self, source_id: str) -> Optional[dict[str, Any]]:
        """Get single source metadata and associated evidence count."""
        source = self.db.get_source(source_id)
        if not source:
            return None
        evidence_list = [e for e in self.db.all_evidence() if e.source_id == source_id]
        return {
            "source_id": source.source_id,
            "title": source.title,
            "modality": source.modality.value if hasattr(source.modality, "value") else str(source.modality),
            "path": source.path,
            "sha256": source.sha256,
            "metadata": source.metadata,
            "evidence_count": len(evidence_list),
        }

    def get_source_evidence(self, source_id: str) -> list[dict[str, Any]]:
        """Get all extracted evidence units for a specific source."""
        units = [e for e in self.db.all_evidence() if e.source_id == source_id]
        return [u.model_dump() for u in units]

    def seed_default_corpus_if_empty(self):
        """Pre-populate the database with curriculum, topics, questions, and sources if missing."""
        from ..corpus import seed_database_from_corpus
        data_dir = Path(__file__).resolve().parent.parent.parent / "data"

        # Check if database lacks sources, topics, or verified questions
        has_sources = bool(self.db.all_sources())
        has_topics = bool(self.db.all_topics())
        has_questions = bool(self.db.all_questions())

        if not has_sources or not has_topics or not has_questions:
            try:
                import logging
                logging.getLogger("cognivault.service").info(
                    "Database needs baseline seeding (sources=%s, topics=%s, questions=%s). Seeding...",
                    has_sources, has_topics, has_questions
                )
                seed_database_from_corpus(self.db, data_dir)
            except Exception as e:
                import logging
                logging.getLogger("cognivault.service").warning(f"Startup corpus seeding failed: {e}")

    def build_and_sync_embeddings(self):
        """Build dense embeddings and sync to ChromaDB with graceful error handling."""
        try:
            build_embeddings(self.db)
            self.sync_chroma()
        except Exception as e:
            import logging
            logging.getLogger("cognivault.service").warning(f"Background embedding build: {e}")

    def ingest_document(
        self,
        file_path: str | Path,
        source_id: Optional[str] = None,
        title: Optional[str] = None,
        sync_embeddings: bool = True,
    ) -> dict[str, Any]:
        """
        Ingest a PDF, PPTX, or transcript file:
          1. Extracts text and figure units with exact page/slide/timestamp locators.
          2. Computes SHA-256 provenance hash.
          3. Indexes in SQLite FTS5.
          4. Optionally syncs dense embeddings and ChromaDB.
        """
        p = Path(file_path)
        sid = ingest_file(p, self.db, source_id=source_id, title=title)

        if sync_embeddings:
            self.build_and_sync_embeddings()

        source = self.db.get_source(sid)
        evidence_count = len([e for e in self.db.all_evidence() if e.source_id == sid])

        return {
            "source_id": sid,
            "title": source.title if source else p.stem,
            "modality": source.modality.value if source and hasattr(source.modality, "value") else "unknown",
            "sha256": source.sha256 if source else "",
            "evidence_count": evidence_count,
            "status": "ingested_and_indexed",
        }

    # -------------------------------------------------------------------------
    # Topic & Curriculum Knowledge Base Operations
    # -------------------------------------------------------------------------

    def list_topics(self) -> list[dict[str, Any]]:
        """List all topics, concepts, and prerequisite topological links."""
        topics = list(self.db.all_topics())
        if not topics:
            self.seed_default_corpus_if_empty()
            topics = list(self.db.all_topics())
        result = []
        for t in topics:
            concepts = list(self.db.get_concepts_for_topic(t.topic_id))
            prereqs = self.db.get_all_prerequisites(t.topic_id)
            result.append({
                "topic_id": t.topic_id,
                "name": t.name,
                "description": t.description,
                "concepts": [c.name for c in concepts],
                "prerequisites": prereqs,
            })
        return result

    # -------------------------------------------------------------------------
    # Assessment Operations (Chat 02 Intelligence Core)
    # -------------------------------------------------------------------------

    def list_questions(
        self,
        topic_id: Optional[str] = None,
        difficulty: Optional[Difficulty] = None,
        question_type: Optional[QuestionType] = None,
    ) -> list[dict[str, Any]]:
        """List questions matching topic or difficulty filters."""
        if not self.db.all_questions():
            self.seed_default_corpus_if_empty()

        if topic_id:
            qs = self.db.get_questions_for_topic(topic_id, verified_only=False)
        else:
            qs = list(self.db.all_questions())

        if difficulty:
            qs = [q for q in qs if q.difficulty == difficulty]
        if question_type:
            qs = [q for q in qs if q.question_type == question_type]

        return [q.model_dump() for q in qs]

    def get_question(self, question_id: str) -> Optional[dict[str, Any]]:
        """Retrieve question by ID."""
        q = self.db.get_question(question_id)
        return q.model_dump() if q else None

    def select_adaptive_question(
        self,
        topic_id: str,
        served_question_ids: Optional[list[str]] = None,
        target_difficulty: Optional[Difficulty] = None,
    ) -> Optional[dict[str, Any]]:
        """Select next adaptive practice question avoiding repeats."""
        if not self.db.all_questions():
            self.seed_default_corpus_if_empty()

        q = self.workflow.select_practice_question(
            topic_id=topic_id,
            served_question_ids=served_question_ids,
            target_difficulty=target_difficulty,
        )
        if not q:
            # Fallback 1: match topic case-insensitively
            all_qs = self.db.all_questions(verified_only=True)
            topic_match = [item for item in all_qs if item.topic_id.lower() == topic_id.lower()]
            if topic_match:
                q = topic_match[0]
            elif all_qs:
                # Fallback 2: return first verified question from any topic
                q = all_qs[0]

        return q.model_dump() if q else None

    def verify_question(self, question: Question) -> QuestionVerificationResult:
        """Deterministically verify question structure, answer key, and evidence linkage."""
        return self.assessment_agent.verify_question(question)

    def submit_assessment_answer(
        self,
        learner_id: str,
        question_id: str,
        answer: str,
        timestamp: Optional[str] = None,
    ) -> dict[str, Any]:
        """Submit answer, score deterministically, update BKT, and evaluate misconceptions."""
        return self.workflow.process_assessment_submission(
            learner_id=learner_id,
            question_id=question_id,
            answer=answer,
            timestamp=timestamp,
        )

    # -------------------------------------------------------------------------
    # Learner Model & BKT Tracking Operations (Chat 02)
    # -------------------------------------------------------------------------

    def list_learners(self) -> list[dict[str, Any]]:
        """List distinct registered learners with high-level stats."""
        # Query distinct learner_ids from learner_states and interactions
        cur = self.db.conn.cursor()
        cur.execute("SELECT DISTINCT learner_id FROM learner_states UNION SELECT DISTINCT learner_id FROM learner_interactions")
        rows = cur.fetchall()
        learner_ids = [r[0] for r in rows if r[0]]

        # Ensure demo learners exist if table is empty
        if not learner_ids:
            learner_ids = ["learner_demo"]

        result = []
        for lid in sorted(learner_ids):
            profile = self.state_manager.get_learner_profile(lid)
            result.append({
                "learner_id": lid,
                "topics_tracked": len(profile["topic_mastery"]),
                "total_attempts": profile["total_attempts"],
                "total_correct": profile["total_correct"],
                "active_misconceptions": len(profile["active_misconceptions"]),
            })
        return result

    def get_learner_profile(self, learner_id: str) -> dict[str, Any]:
        """Get complete learner profile including mastery map, stats, and active misconceptions."""
        return self.state_manager.get_learner_profile(learner_id)

    def get_learner_topic_mastery(self, learner_id: str) -> list[dict[str, Any]]:
        """Get list of topic mastery records for a learner."""
        records = self.db.get_all_learner_masteries(learner_id)
        return [r.model_dump() for r in records]

    def record_learning_observation(
        self,
        learner_id: str,
        topic_id: str,
        is_correct: bool,
        timestamp: Optional[str] = None,
    ) -> dict[str, Any]:
        """Direct observation recording (e.g. from validated tutor exchange or external task)."""
        updated = self.coach_agent.record_observation(
            learner_id=learner_id,
            topic_id=topic_id,
            is_correct=is_correct,
            timestamp=timestamp,
        )
        return updated.model_dump()

    def get_active_misconceptions(self, learner_id: str, topic_id: Optional[str] = None) -> list[dict[str, Any]]:
        """List active misconception signals and their remediation packages."""
        signals = self.db.get_active_misconceptions(learner_id, topic_id=topic_id)
        return [self.misconception_detector.get_remediation_package(s) for s in signals]

    def resolve_misconception(self, learner_id: str, topic_id: str, concept_id: Optional[str] = None) -> dict[str, Any]:
        """Clear active misconception signal and reset error counters."""
        self.coach_agent.resolve_misconception(learner_id, topic_id=topic_id, concept_id=concept_id)
        return {"status": "resolved", "learner_id": learner_id, "topic_id": topic_id}

    def get_recommendation(self, learner_id: str, active_topic_id: Optional[str] = None) -> dict[str, Any]:
        """Get prerequisite-aware next learning recommendation."""
        rec = self.coach_agent.get_recommendation(learner_id, active_topic_id=active_topic_id)
        return rec.model_dump()

    def cold_start_intake(
        self,
        learner_id: str,
        initial_topic_masteries: Optional[dict[str, float]] = None,
        diagnostic_responses: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Execute cold-start diagnostic intake for fresh learner."""
        return self.workflow.complete_intake(
            learner_id=learner_id,
            initial_masteries=initial_topic_masteries,
            responses=diagnostic_responses,
        )

    # -------------------------------------------------------------------------
    # Health Check Probe
    # -------------------------------------------------------------------------

    def health_check(self) -> dict[str, Any]:
        """Perform system health check across local components and agents."""
        ollama_ok = is_ollama_available(OLLAMA_HOST)
        models = get_available_ollama_models(OLLAMA_HOST) if ollama_ok else []
        return {
            "status": "healthy",
            "sqlite_db": {
                "path": self.db_path,
                "sources_count": len(list(self.db.all_sources())),
                "evidence_count": len(list(self.db.all_evidence())),
                "questions_count": len(list(self.db.all_questions())),
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
            "model_provider": get_active_provider_info(),
            "agno_agents": {
                "tutor": self.tutor_agent.agno_agent is not None,
                "assessment": self.assessment_agent.agno_agent is not None,
                "learning_coach": self.coach_agent.agno_agent is not None,
            },
        }

    def close(self):
        """Close database connections."""
        self.db.close()


# Backwards compatibility alias for Chat 01 code and tests
AgentOSTutorService = AgentOSLearningService
