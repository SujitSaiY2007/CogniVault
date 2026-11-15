"""Data contracts shared by the backend and the Next.js client."""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

PUBLIC_OWNER = "public"  # owner id of the shared demo course


class Modality(str, Enum):
    pdf = "pdf"
    pptx = "pptx"
    video = "video"
    image = "image"
    text = "text"


class Difficulty(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class QuestionType(str, Enum):
    mcq = "mcq"
    numerical = "numerical"
    short_answer = "short_answer"


class SourceRecord(BaseModel):
    source_id: str
    owner_id: str = PUBLIC_OWNER
    title: str
    modality: Modality
    path: str = ""
    sha256: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    evidence_count: int = 0
    created_at: Optional[str] = None


class EvidenceUnit(BaseModel):
    evidence_id: str
    source_id: str
    owner_id: str = PUBLIC_OWNER
    modality: Modality
    text: str
    location: dict[str, Any] = Field(default_factory=dict)
    evidence_type: str = "text"  # text | figure | slide | transcript | notes
    section: str = ""
    topics: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TopicRecord(BaseModel):
    topic_id: str
    owner_id: str = PUBLIC_OWNER
    name: str
    description: str = ""
    source_id: Optional[str] = None
    position: int = 0
    concepts: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)


class Citation(BaseModel):
    evidence_id: str
    source_id: str
    modality: Modality
    location: dict[str, Any] = Field(default_factory=dict)
    snippet: str
    source_path: Optional[str] = None
    source_title: Optional[str] = None
    locator_label: str = ""
    asset_id: Optional[str] = None


class TutorResponse(BaseModel):
    query: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    is_grounded: bool
    is_synthesis: bool = False
    confidence: float = 0.0
    support_status: str  # supported | unsupported | error
    reasoning_steps: list[str] = Field(default_factory=list)
    unsupported_reason: Optional[str] = None
    topics: list[str] = Field(default_factory=list)
    generator: str = "extractive"
    metadata: dict[str, Any] = Field(default_factory=dict)


class QuestionOption(BaseModel):
    key: str
    text: str


class Question(BaseModel):
    question_id: str
    owner_id: str = PUBLIC_OWNER
    topic_id: str
    concept_id: Optional[str] = None
    evidence_ids: list[str] = Field(default_factory=list)
    difficulty: Difficulty = Difficulty.medium
    question_type: QuestionType = QuestionType.mcq
    prompt: str
    options: list[QuestionOption] = Field(default_factory=list)
    expected_answer: str
    tolerance: Optional[float] = None
    solution: str = ""
    verification_status: str = "unverified"  # verified | rejected | unverified
    verification_reason: Optional[str] = None
    fingerprint: str = ""
    repetition_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)

    def public(self) -> dict[str, Any]:
        """Client-safe view: never reveal the answer key before submission."""
        data = self.model_dump()
        data["expected_answer"] = ""
        data["solution"] = ""
        meta = dict(data.get("metadata") or {})
        meta.pop("distractor_concepts", None)
        meta.pop("formula", None)
        data["metadata"] = meta
        return data


class AnswerEvaluation(BaseModel):
    learner_id: str
    question_id: str
    is_correct: bool
    status: str  # correct | partially_correct | incorrect
    score: float = 0.0
    feedback: str
    expected_answer: str = ""
    solution: str = ""
    citations: list[Citation] = Field(default_factory=list)
    remediation_action: Optional[str] = None
    remediation_evidence_ids: list[str] = Field(default_factory=list)


class TopicMasteryRecord(BaseModel):
    learner_id: str
    topic_id: str
    p_mastery: float
    attempts: int = 0
    correct: int = 0
    recent_correctness: list[bool] = Field(default_factory=list)
    last_seen: Optional[str] = None
    misconception_signals: list[str] = Field(default_factory=list)
    topic_name: str = ""


class MisconceptionSignal(BaseModel):
    signal_id: str
    learner_id: str
    topic_id: str
    concept_id: Optional[str] = None
    suspected_misconception: str
    error_count: int
    confidence: float
    remediation_concept_id: Optional[str] = None
    remediation_evidence_ids: list[str] = Field(default_factory=list)
    remediation_note: str = ""
    created_at: Optional[str] = None


class Recommendation(BaseModel):
    learner_id: str
    recommended_action: str
    topic_id: str
    topic_name: str = ""
    concept_id: Optional[str] = None
    difficulty: Difficulty
    rationale: str
    learner_state_evidence: dict[str, Any] = Field(default_factory=dict)
    suggested_evidence_ids: list[str] = Field(default_factory=list)
    suggested_question_id: Optional[str] = None
