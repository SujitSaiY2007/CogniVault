from app.db import EvidenceDB
from app.models import ConceptRecord, EvidenceUnit, Modality, SourceRecord, TopicRecord
import pytest

def test_evidence_id_roundtrip(tmp_path):
    db = EvidenceDB(tmp_path / "x.sqlite")
    db.add_source(SourceRecord(source_id="s1", path="x.pdf", modality=Modality.pdf, title="X", sha256="abc"))
    db.add_evidence(EvidenceUnit(evidence_id="s1:e00001", source_id="s1", modality=Modality.pdf, text="Concept evidence.", location={"page": 3}, concepts=["concept"]))
    e = db.get_evidence("s1:e00001")
    assert e.location["page"] == 3 and e.source_id == "s1"

def test_topic_concept_relational_representation(tmp_path):
    db = EvidenceDB(tmp_path / "relations.sqlite")
    db.add_topic("calculus", "Calculus", "Differentiation and Integration")
    db.add_concept("derivatives", "Derivatives", topic_id="calculus", description="Rate of change")
    db.add_concept("limits", "Limits", topic_id="calculus", description="Approaching a value")
    db.link_concept_prerequisite("derivatives", "limits")

    assert db.get_topic("calculus").name == "Calculus"
    assert db.get_concept("derivatives").topic == "calculus"
    assert "limits" in db.get_concept_prerequisites("derivatives")

    # Test one evidence unit -> multiple concepts
    db.add_source(SourceRecord(source_id="s1", path="calc.pdf", modality=Modality.pdf, title="Calculus Book", sha256="h1"))
    db.add_evidence(EvidenceUnit(
        evidence_id="s1:e00001",
        source_id="s1",
        modality=Modality.pdf,
        text="Definition of derivative as limit of difference quotient.",
        location={"page": 10},
        topics=["calculus"],
        concepts=["derivatives", "limits"],
        prerequisites=["limits"],
    ))

    # Test another evidence unit sharing a concept (one concept -> multiple evidence units)
    db.add_evidence(EvidenceUnit(
        evidence_id="s1:e00002",
        source_id="s1",
        modality=Modality.pdf,
        text="Epsilon-delta definition of a limit.",
        location={"page": 5},
        topics=["calculus"],
        concepts=["limits"],
    ))

    # Verify many-to-many relationships
    e1_concepts = [(c.name if hasattr(c, 'name') else str(c)).lower() for c in db.get_concepts_for_evidence("s1:e00001")]
    assert "derivatives" in e1_concepts and "limits" in e1_concepts

    limit_ids = [e.evidence_id for e in db.get_evidence_for_concept("limits")]
    assert "s1:e00001" in limit_ids and "s1:e00002" in limit_ids

    deriv_ids = [e.evidence_id for e in db.get_evidence_for_concept("derivatives")]
    assert "s1:e00001" in deriv_ids and "s1:e00002" not in deriv_ids

    topic_ids = [e.evidence_id for e in db.get_evidence_for_topic("calculus")]
    assert "s1:e00001" in topic_ids and "s1:e00002" in topic_ids

def test_prerequisite_transitive_closure(tmp_path):
    db = EvidenceDB(tmp_path / "prereqs.sqlite")
    # Linear chain: integrals -> derivatives -> limits -> algebra
    db.add_concept("integrals", "Integrals")
    db.add_concept("derivatives", "Derivatives")
    db.add_concept("limits", "Limits")
    db.add_concept("algebra", "Algebra")

    db.link_concept_prerequisite("integrals", "derivatives")
    db.link_concept_prerequisite("derivatives", "limits")
    db.link_concept_prerequisite("limits", "algebra")

    assert "derivatives" in db.get_concept_prerequisites("integrals")
    assert "limits" in db.get_concept_prerequisites("derivatives")
    assert "algebra" in db.get_concept_prerequisites("limits")

    all_prereqs = db.get_all_prerequisites("integrals")
    assert all_prereqs == ["derivatives", "limits", "algebra"]

    # Verify cycle tolerance
    db.link_concept_prerequisite("algebra", "integrals")
    closure_with_cycle = db.get_all_prerequisites("integrals")
    assert set(closure_with_cycle) == {"derivatives", "limits", "algebra"}

def test_source_record_persistence_and_retrieval(tmp_path):
    db = EvidenceDB(tmp_path / "sources.sqlite")
    s = SourceRecord(
        source_id="src_42",
        path="/path/to/physics.pdf",
        modality=Modality.pdf,
        title="Physics Principles",
        sha256="deadbeefcafe",
        metadata={"author": "Newton", "edition": 1},
    )
    db.add_source(s)

    retrieved = db.get_source("src_42")
    assert retrieved is not None
    assert retrieved.source_id == "src_42"
    assert retrieved.title == "Physics Principles"
    assert retrieved.sha256 == "deadbeefcafe"
    assert retrieved.metadata["author"] == "Newton"

    assert len(db.all_sources()) == 1
    assert db.get_source("nonexistent") is None

def test_embedding_dimension_validation(tmp_path):
    import numpy as np
    db = EvidenceDB(tmp_path / "embeddings.sqlite")
    assert not db.has_embeddings()

    v1 = np.array([0.1, 0.2, 0.3], dtype=np.float32)
    db.add_embedding("e1", v1, model_name="mini-3d")
    assert db.has_embeddings()

    meta = db.get_embedding_metadata()
    assert meta["dimension"] == 3
    assert meta["model_name"] == "mini-3d"

    # Valid matching dimension
    v2 = np.array([0.4, 0.5, 0.6], dtype=np.float32)
    db.add_embedding("e2", v2)

    # Invalid mismatched dimension should raise ValueError
    v_bad = np.array([0.1, 0.2], dtype=np.float32)
    with pytest.raises(ValueError, match="dimension mismatch"):
        db.add_embedding("e3", v_bad)
