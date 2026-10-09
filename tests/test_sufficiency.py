import pytest
from app.db import EvidenceDB
from app.models import EvidenceUnit, Modality, RetrievalResult, RetrievalTrace, SourceRecord
from app.sufficiency import EvidenceSufficiencyGate, check_sufficiency

def test_sufficiency_empty_query(tmp_path):
    gate = EvidenceSufficiencyGate()
    res = gate.evaluate("", [])
    assert not res.is_sufficient
    assert res.reason == "empty query"
    assert res.confidence == 0.0

def test_sufficiency_unsupported_trace(tmp_path):
    gate = EvidenceSufficiencyGate()
    trace = RetrievalTrace(
        query="quantum black hole",
        mode="hybrid",
        unsupported=True,
        reason="no supported evidence matched"
    )
    res = gate.evaluate("quantum black hole", [], trace=trace)
    assert not res.is_sufficient
    assert "unsupported" in res.reason or "no supported evidence" in res.reason

def test_sufficiency_low_score_rejection(tmp_path):
    gate = EvidenceSufficiencyGate(min_score=0.30)
    results = [
        RetrievalResult(
            evidence_id="e1",
            score=0.10,
            lexical_score=0.10,
            semantic_score=0.10,
            source_id="s1",
            snippet="Irrelevant snippet",
            location={}
        )
    ]
    res = gate.evaluate("Newton law", results)
    assert not res.is_sufficient
    assert "below sufficiency threshold" in res.reason

def test_sufficiency_valid_evidence_passed(tmp_path):
    db = EvidenceDB(tmp_path / "suff.sqlite")
    db.add_source(SourceRecord(source_id="src1", path="book.pdf", modality=Modality.pdf, title="Physics", sha256="h1"))
    db.add_evidence(EvidenceUnit(evidence_id="src1:e00001", source_id="src1", modality=Modality.pdf, text="Newton second law relates force and acceleration F=ma.", location={"page": 10}))

    gate = EvidenceSufficiencyGate(min_score=0.15)
    results = [
        RetrievalResult(
            evidence_id="src1:e00001",
            score=0.85,
            lexical_score=0.80,
            semantic_score=0.90,
            source_id="src1",
            snippet="Newton second law relates force and acceleration F=ma.",
            location={"page": 10}
        )
    ]
    res = gate.evaluate("Newton second law force acceleration", results, db=db)
    assert res.is_sufficient
    assert res.reason is None
    assert "src1:e00001" in res.supporting_evidence_ids
    assert res.confidence == 0.85

def test_sufficiency_unaddressable_source_rejection(tmp_path):
    db = EvidenceDB(tmp_path / "suff2.sqlite")
    # Evidence ID not in DB
    gate = EvidenceSufficiencyGate(min_score=0.10, require_addressable_source=True)
    results = [
        RetrievalResult(
            evidence_id="phantom:e00001",
            score=0.90,
            lexical_score=0.90,
            semantic_score=0.90,
            source_id="phantom",
            snippet="Phantom text containing test query terms.",
            location={}
        )
    ]
    res = gate.evaluate("test query", results, db=db)
    assert not res.is_sufficient
    assert "could not be resolved" in res.reason

