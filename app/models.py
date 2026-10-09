from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field

class Modality(str, Enum):
    pdf = "pdf"
    pptx = "pptx"
    video = "video"
    image = "image"
    text = "text"

class TopicRecord(BaseModel):
    topic_id: str
    name: str
    description: str = ""

class ConceptRecord(BaseModel):
    concept_id: str
    name: str
    topic_id: str | None = None
    topic: str | None = None
    description: str = ""

    def model_post_init(self, __context):
        if self.topic is None and self.topic_id is not None:
            self.topic = self.topic_id
        elif self.topic_id is None and self.topic is not None:
            self.topic_id = self.topic

class PrerequisiteLink(BaseModel):
    concept_id: str
    prerequisite_concept_id: str

ConceptPrerequisite = PrerequisiteLink

class EvidenceUnit(BaseModel):
    evidence_id: str
    source_id: str
    modality: Modality
    text: str
    location: dict[str, str | int | float] = Field(default_factory=dict)
    evidence_type: str = "text"
    asset_id: str | None = None
    topics: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)

class SourceRecord(BaseModel):
    source_id: str
    path: str
    modality: Modality
    title: str
    sha256: str
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)

class RetrievalResult(BaseModel):
    evidence_id: str
    score: float
    lexical_score: float
    semantic_score: float
    source_id: str
    snippet: str
    location: dict[str, str | int | float] = Field(default_factory=dict)

class CandidateTrace(BaseModel):
    evidence_id: str
    source_id: str
    lexical_score: float
    semantic_score: float
    score: float
    rank: int

RetrievalScore = CandidateTrace

class RetrievalTrace(BaseModel):
    query: str
    mode: str
    result_ids: list[str] = Field(default_factory=list)
    unsupported: bool = False
    reason: str | None = None
    candidate_count: int = 0
    result_count: int = 0
    source_ids: list[str] = Field(default_factory=list)
    candidates: list[CandidateTrace] = Field(default_factory=list)
    scores: list[CandidateTrace] = Field(default_factory=list)
    ranking: list[str] = Field(default_factory=list)

# ---------------------------------------------------------------------------
# Chat 02 Intelligence Core Models
# ---------------------------------------------------------------------------

class SufficiencyResult(BaseModel):
    query: str
    is_sufficient: bool
    reason: str | None = None
    confidence: float = 0.0
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    evidence_count: int = 0

class Citation(BaseModel):
    evidence_id: str
    source_id: str
    modality: Modality
    location: dict[str, str | int | float] = Field(default_factory=dict)
    snippet: str = ""
    source_path: str | None = None
    source_title: str | None = None

class TutorResponse(BaseModel):
    query: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    is_grounded: bool = True
    is_synthesis: bool = False
    confidence: float = 1.0
    support_status: str = "supported"  # "supported" | "unsupported" | "error"
    reasoning_steps: list[str] = Field(default_factory=list)
    unsupported_reason: str | None = None
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)

class QuestionType(str, Enum):
    mcq = "mcq"
    numerical = "numerical"
    short_answer = "short_answer"

class Difficulty(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"

class QuestionOption(BaseModel):
    key: str
    text: str

class Question(BaseModel):
    question_id: str
    topic_id: str
    concept_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    difficulty: Difficulty = Difficulty.medium
    question_type: QuestionType = QuestionType.mcq
    prompt: str
    options: list[QuestionOption] = Field(default_factory=list)
    expected_answer: str
    tolerance: float | None = None
    solution: str = ""
    verification_status: str = "unverified"  # "verified" | "rejected" | "unverified"
    verification_reason: str | None = None
    fingerprint: str = ""
    repetition_count: int = 0
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)

class QuestionVerificationResult(BaseModel):
    question_id: str
    is_valid: bool
    verification_method: str = "deterministic"  # "deterministic" | "model_assisted"
    failure_reasons: list[str] = Field(default_factory=list)
    checks_passed: list[str] = Field(default_factory=list)

class LearnerSubmission(BaseModel):
    learner_id: str
    question_id: str
    topic_id: str
    answer: str
    timestamp: str | None = None

class AnswerEvaluation(BaseModel):
    learner_id: str
    question_id: str
    is_correct: bool
    status: str = "incorrect"  # "correct" | "partially_correct" | "incorrect"
    feedback: str
    citations: list[Citation] = Field(default_factory=list)
    remediation_action: str | None = None
    remediation_evidence_ids: list[str] = Field(default_factory=list)

class BKTParams(BaseModel):
    p_init: float = 0.10
    p_transit: float = 0.15
    p_slip: float = 0.10
    p_guess: float = 0.20

class TopicMasteryRecord(BaseModel):
    learner_id: str
    topic_id: str
    p_mastery: float = 0.10
    attempts: int = 0
    correct: int = 0
    recent_correctness: list[bool] = Field(default_factory=list)
    last_seen: str | None = None
    misconception_signals: list[str] = Field(default_factory=list)

class MisconceptionSignal(BaseModel):
    signal_id: str
    learner_id: str
    topic_id: str
    concept_id: str | None = None
    suspected_misconception: str
    error_count: int = 1
    confidence: float = 0.80
    remediation_concept_id: str | None = None
    remediation_evidence_ids: list[str] = Field(default_factory=list)
    remediation_note: str = ""
    created_at: str | None = None

class Recommendation(BaseModel):
    learner_id: str
    recommended_action: str  # "foundational_review" | "targeted_practice" | "mixed_application" | "advance_topic" | "remediate_misconception"
    topic_id: str
    concept_id: str | None = None
    difficulty: Difficulty = Difficulty.medium
    rationale: str
    learner_state_evidence: dict[str, str | int | float | bool] = Field(default_factory=dict)
    suggested_evidence_ids: list[str] = Field(default_factory=list)
    suggested_question_id: str | None = None

