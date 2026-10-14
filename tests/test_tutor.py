import pytest
from app.db import EvidenceDB
from app.models import EvidenceUnit, Modality, SourceRecord
from app.retrieval import HybridRetriever
from app.tutor import BaseTutorProvider, GroundedTutor

def test_tutor_supported_direct_response(tmp_path):
    db = EvidenceDB(tmp_path / "tutor.sqlite")
    db.add_source(SourceRecord(source_id="math_book", path="math.pdf", modality=Modality.pdf, title="Mathematics", sha256="sha_m"))
    db.add_evidence(
        EvidenceUnit(
            evidence_id="math_book:e00001",
            source_id="math_book",
            modality=Modality.pdf,
            text="The Pythagorean theorem states that in a right-angled triangle, a^2 + b^2 = c^2.",
            location={"page": 42},
            topics=["Geometry", "Pythagoras"]
        )
    )

    tutor = GroundedTutor(db)
    resp = tutor.answer("Pythagorean theorem right triangle", mode="lexical")

    assert resp.is_grounded
    assert resp.support_status == "supported"
    assert "Pythagorean theorem" in resp.answer
    assert len(resp.citations) == 1
    assert resp.citations[0].evidence_id == "math_book:e00001"
    assert resp.citations[0].location["page"] == 42
    assert resp.citations[0].source_title == "Mathematics"

def test_tutor_unsupported_abstention(tmp_path):
    db = EvidenceDB(tmp_path / "tutor_unsupp.sqlite")
    db.add_source(SourceRecord(source_id="bio_book", path="bio.pdf", modality=Modality.pdf, title="Biology", sha256="sha_b"))
    db.add_evidence(
        EvidenceUnit(
            evidence_id="bio_book:e00001",
            source_id="bio_book",
            modality=Modality.pdf,
            text="Photosynthesis converts light energy into chemical energy.",
            location={"page": 1}
        )
    )

    tutor = GroundedTutor(db)
    resp = tutor.answer("quantum chromodynamics gluon interaction", mode="lexical")

    assert not resp.is_grounded
    assert resp.support_status == "unsupported"
    assert len(resp.citations) == 0
    assert "cannot answer" in resp.answer.lower() or "not contain sufficient" in resp.answer.lower()

def test_tutor_cross_source_synthesis(tmp_path):
    db = EvidenceDB(tmp_path / "tutor_synth.sqlite")
    db.add_source(SourceRecord(source_id="src_text", path="text.pdf", modality=Modality.pdf, title="Kinematics Text", sha256="s1"))
    db.add_source(SourceRecord(source_id="src_slides", path="slides.pptx", modality=Modality.pptx, title="Kinematics Slides", sha256="s2"))

    db.add_evidence(
        EvidenceUnit(
            evidence_id="src_text:e00001",
            source_id="src_text",
            modality=Modality.pdf,
            text="Velocity is the rate of change of displacement with respect to time.",
            location={"page": 12},
            topics=["Kinematics"]
        )
    )
    db.add_evidence(
        EvidenceUnit(
            evidence_id="src_slides:e00001",
            source_id="src_slides",
            modality=Modality.pptx,
            text="Acceleration is the rate of change of velocity over time.",
            location={"slide": 5},
            topics=["Kinematics"]
        )
    )

    tutor = GroundedTutor(db)
    resp = tutor.answer("velocity displacement acceleration rate", mode="lexical")

    assert resp.is_grounded
    assert resp.is_synthesis
    assert len(resp.citations) >= 2
    cited_eids = {c.evidence_id for c in resp.citations}
    assert "src_text:e00001" in cited_eids
    assert "src_slides:e00001" in cited_eids

def test_tutor_provider_failure_fails_closed(tmp_path):
    db = EvidenceDB(tmp_path / "tutor_err.sqlite")
    db.add_source(SourceRecord(source_id="src1", path="doc.pdf", modality=Modality.pdf, title="Doc", sha256="s1"))
    db.add_evidence(EvidenceUnit(evidence_id="src1:e00001", source_id="src1", modality=Modality.pdf, text="Newton first law of inertia.", location={"page": 1}))

    class FailingProvider:
        def generate(self, query, evidence_items):
            raise RuntimeError("LLM API rate limit / 503 Service Unavailable")

    tutor = GroundedTutor(db, provider=FailingProvider())
    resp = tutor.answer("Newton inertia", mode="lexical")

    assert not resp.is_grounded
    assert resp.support_status == "error"
    assert len(resp.citations) == 0
    assert "service error" in resp.answer.lower() or "withheld" in resp.answer.lower()
