import pytest
from app.db import EvidenceDB
from app.misconceptions import MisconceptionDetector
from app.models import EvidenceUnit, Modality, SourceRecord

def test_misconception_single_error_suppressed(tmp_path):
    db = EvidenceDB(tmp_path / "misc1.sqlite")
    detector = MisconceptionDetector(db, error_threshold=2)

    # 1st error: isolated slip -> should NOT diagnose misconception
    res = detector.analyze_attempt("learner_1", "Fractions", "Denominator Addition", is_correct=False)
    assert res is None
    assert len(db.get_active_misconceptions("learner_1")) == 0

def test_misconception_repeated_error_threshold_and_remediation(tmp_path):
    db = EvidenceDB(tmp_path / "misc2.sqlite")
    db.add_source(SourceRecord(source_id="src_math", path="math.pdf", modality=Modality.pdf, title="Math Book", sha256="s1"))
    db.add_concept("Common Denominators", "Common Denominators", description="Finding LCM for adding fractions")
    db.add_concept("Denominator Addition", "Denominator Addition", description="Adding numerators over common denominator")
    db.link_concept_prerequisite("Denominator Addition", "Common Denominators")

    db.add_evidence(
        EvidenceUnit(
            evidence_id="src_math:e00001",
            source_id="src_math",
            modality=Modality.pdf,
            text="Before adding fractions, find a common denominator using the LCM.",
            concepts=["Common Denominators"],
            topics=["Fractions"]
        )
    )

    detector = MisconceptionDetector(db, error_threshold=2)

    # 1st attempt: incorrect
    detector.analyze_attempt("learner_2", "Fractions", "Denominator Addition", is_correct=False)

    # 2nd attempt: incorrect -> threshold met
    signal = detector.analyze_attempt("learner_2", "Fractions", "Denominator Addition", is_correct=False)

    assert signal is not None
    assert signal.learner_id == "learner_2"
    assert signal.error_count == 2
    assert "Common Denominators" in signal.remediation_concept_id
    assert "src_math:e00001" in signal.remediation_evidence_ids

    # Package check
    pkg = detector.get_remediation_package(signal)
    assert len(pkg["evidence_items"]) >= 1
    assert "Common Denominators" in pkg["remediation_concept_id"]
