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
