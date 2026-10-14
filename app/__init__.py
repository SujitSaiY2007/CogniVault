from __future__ import annotations

from .db import EvidenceDB
from .ingest import ingest_pdf, ingest_pptx, ingest_transcript
from .retrieval import HybridRetriever, build_embeddings
from .source_resolver import resolve
from .sufficiency import EvidenceSufficiencyGate, check_sufficiency
from .tutor import GroundedTutor, DeterministicTutorProvider
from .assessment import AssessmentEngine, DeterministicQuestionVerifier, compute_question_fingerprint
from .learner_model import BKTModel, LearnerStateManager
from .misconceptions import MisconceptionDetector
from .chroma_store import ChromaEvidenceStore
from .agent_os import AgentOSTutorService, EvidenceTutorAgent, create_agent_os_app
from .models import (
    AnswerEvaluation,
    BKTParams,
    CandidateTrace,
    Citation,
    ConceptRecord,
    Difficulty,
    EvidenceUnit,
    LearnerSubmission,
    LocatorType,
    MisconceptionSignal,
    Modality,
    PrerequisiteLink,
    Question,
    QuestionOption,
    QuestionType,
    QuestionVerificationResult,
    Recommendation,
    RetrievalResult,
    RetrievalTrace,
    SourceRecord,
    SufficiencyResult,
    TopicMasteryRecord,
    TopicRecord,
    TutorResponse,
)

__all__ = [
    "EvidenceDB",
    "ingest_pdf",
    "ingest_pptx",
    "ingest_transcript",
    "HybridRetriever",
    "build_embeddings",
    "resolve",
    "EvidenceSufficiencyGate",
    "check_sufficiency",
    "GroundedTutor",
    "DeterministicTutorProvider",
    "AssessmentEngine",
    "DeterministicQuestionVerifier",
    "compute_question_fingerprint",
    "BKTModel",
    "LearnerStateManager",
    "MisconceptionDetector",
    "AdaptiveRecommendationEngine",
    "ChromaEvidenceStore",
    "AgentOSTutorService",
    "EvidenceTutorAgent",
    "create_agent_os_app",
    "AnswerEvaluation",
    "BKTParams",
    "CandidateTrace",
    "Citation",
    "ConceptRecord",
    "Difficulty",
    "EvidenceUnit",
    "LearnerSubmission",
    "LocatorType",
    "MisconceptionSignal",
    "Modality",
    "PrerequisiteLink",
    "Question",
    "QuestionOption",
    "QuestionType",
    "QuestionVerificationResult",
    "Recommendation",
    "RetrievalResult",
    "RetrievalTrace",
    "SourceRecord",
    "SufficiencyResult",
    "TopicMasteryRecord",
    "TopicRecord",
    "TutorResponse",
]
