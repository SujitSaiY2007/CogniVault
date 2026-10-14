"""
Tests for ChromaEvidenceStore and hybrid ChromaDB retrieval integration.
"""
import pytest
import numpy as np

from app.db import EvidenceDB
from app.models import EvidenceUnit, Modality, SourceRecord
from app.chroma_store import ChromaEvidenceStore
from app.retrieval import HybridRetriever, build_embeddings


import uuid

@pytest.fixture
def memory_chroma():
    return ChromaEvidenceStore(
        in_memory=True,
        collection_name=f"test_mem_{uuid.uuid4().hex[:8]}"
    )


@pytest.fixture
def populated_db_and_chroma(tmp_path):
    db_file = tmp_path / "test_chroma.db"
    db = EvidenceDB(str(db_file))

    # Add source
    source = SourceRecord(
        source_id="src_kinematics",
        path="data/corpus/kinematics.pdf",
        modality=Modality.pdf,
        title="Physics Kinematics",
        sha256="abc123sha",
        metadata={"subject": "Physics"},
    )
    db.add_source(source)

    # Add 3 evidence units
    unit1 = EvidenceUnit(
        evidence_id="ev_001",
        source_id="src_kinematics",
        modality=Modality.pdf,
        text="Velocity is defined as the rate of change of displacement with respect to time.",
        location={"page": 2, "locator": "Page 2"},
        topics=["Kinematics"],
        concepts=["Velocity"],
    )
    unit2 = EvidenceUnit(
        evidence_id="ev_002",
        source_id="src_kinematics",
        modality=Modality.pdf,
        text="Acceleration is the first derivative of velocity with respect to time.",
        location={"page": 4, "locator": "Page 4"},
        topics=["Kinematics"],
        concepts=["Acceleration"],
    )
    unit3 = EvidenceUnit(
        evidence_id="ev_003",
        source_id="src_kinematics",
        modality=Modality.pdf,
        text="Newton's second law states that force is mass times acceleration: F = ma.",
        location={"page": 7, "locator": "Page 7"},
        topics=["Dynamics"],
        concepts=["Second Law"],
    )
    for u in [unit1, unit2, unit3]:
        db.add_evidence(u)

    chroma = ChromaEvidenceStore(
        in_memory=True,
        collection_name=f"test_pop_{uuid.uuid4().hex[:8]}"
    )
    yield db, chroma, [unit1, unit2, unit3]
    db.close()


def test_chroma_add_and_query_basic(memory_chroma):
    unit = EvidenceUnit(
        evidence_id="e_test_1",
        source_id="src_1",
        modality=Modality.pdf,
        text="Quantum mechanics governs micro-scale physics.",
        location={"page": 10, "locator": "Page 10"},
        topics=["Quantum"],
        concepts=["Wavefunction"],
    )
    emb = [0.1] * 384
    memory_chroma.add_evidence(unit, emb)

    assert memory_chroma.count() == 1
    stored = memory_chroma.get_by_id("e_test_1")
    assert stored is not None
    assert stored["metadata"]["topic"] == "Quantum"
    assert stored["metadata"]["locator_value"] == "10"

    # Query with exact vector
    results = memory_chroma.query(emb, top_k=1)
    assert len(results) == 1
    assert results[0]["evidence_id"] == "e_test_1"
    assert results[0]["similarity"] > 0.99


def test_chroma_filters_and_deletion(memory_chroma):
    unit_a = EvidenceUnit(
        evidence_id="e_a",
        source_id="src_1",
        modality=Modality.pdf,
        text="Topic A text content",
        location={"page": 1, "locator": "Page 1"},
        topics=["TopicA"],
    )
    unit_b = EvidenceUnit(
        evidence_id="e_b",
        source_id="src_2",
        modality=Modality.pptx,
        text="Topic B text content",
        location={"slide": 3, "locator": "Slide 3"},
        topics=["TopicB"],
    )
    emb_a = [0.2] * 384
    emb_b = [-0.2] * 384
    memory_chroma.batch_add_evidence([unit_a, unit_b], [emb_a, emb_b])

    assert memory_chroma.count() == 2

    # Filter by topic
    res_a = memory_chroma.query(emb_a, top_k=5, topic_filter="TopicA")
    assert len(res_a) == 1
    assert res_a[0]["evidence_id"] == "e_a"

    # Delete
    memory_chroma.delete_evidence("e_a")
    assert memory_chroma.count() == 1
    assert memory_chroma.get_by_id("e_a") is None


def test_chroma_sync_from_sqlite(populated_db_and_chroma):
    db, chroma, units = populated_db_and_chroma

    # Add embeddings into SQLite EvidenceDB
    dim = 384
    for i, u in enumerate(units):
        vec = np.zeros(dim, dtype=np.float32)
        vec[i] = 1.0  # orthogonal vectors
        db.add_embedding(u.evidence_id, vec, model_name="test_model")

    # Sync into ChromaDB
    synced = chroma.sync_from_sqlite(db)
    assert synced == 3
    assert chroma.count() == 3

    # Verify query
    query_vec = np.zeros(dim, dtype=np.float32)
    query_vec[0] = 1.0
    results = chroma.query(query_vec, top_k=1)
    assert results[0]["evidence_id"] == "ev_001"
    assert results[0]["metadata"]["concept"] == "Velocity"


def test_hybrid_retriever_with_chroma_store(populated_db_and_chroma):
    db, chroma, units = populated_db_and_chroma

    dim = 384
    for i, u in enumerate(units):
        vec = np.zeros(dim, dtype=np.float32)
        vec[i] = 1.0
        db.add_embedding(u.evidence_id, vec, model_name="test_model")

    chroma.sync_from_sqlite(db)

    # Mock embedder that returns vector matching unit 2
    class MockEmbedder:
        def encode(self, texts, **kwargs):
            arr = np.zeros((len(texts), dim), dtype=np.float32)
            arr[:, 1] = 1.0
            return arr

    retriever = HybridRetriever(db, model=MockEmbedder(), chroma_store=chroma)

    results, trace = retriever.search("acceleration", k=2, mode="hybrid")
    assert len(results) > 0
    assert results[0].evidence_id == "ev_002"
    assert results[0].semantic_score > 0.0
    assert not trace.unsupported
