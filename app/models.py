from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field
class Modality(str, Enum):
    pdf="pdf"; pptx="pptx"; video="video"; image="image"; text="text"
class EvidenceUnit(BaseModel):
    evidence_id: str
    source_id: str
    modality: Modality
    text: str
    location: dict[str, str|int|float] = Field(default_factory=dict)
    evidence_type: str = "text"
    asset_id: str|None = None
    topics: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)
    metadata: dict[str, str|int|float|bool] = Field(default_factory=dict)
class SourceRecord(BaseModel):
    source_id: str
    path: str
    modality: Modality
    title: str
    sha256: str
    metadata: dict[str, str|int|float|bool] = Field(default_factory=dict)
class RetrievalResult(BaseModel):
    evidence_id: str
    score: float
    lexical_score: float
    semantic_score: float
    source_id: str
    snippet: str
    location: dict[str, str|int|float] = Field(default_factory=dict)
class RetrievalTrace(BaseModel):
    query: str
    mode: str
    result_ids: list[str]
    unsupported: bool
    reason: str|None = None
