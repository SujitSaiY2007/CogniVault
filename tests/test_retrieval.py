import numpy as np
import pytest
from app.db import EvidenceDB
from app.models import EvidenceUnit, Modality, SourceRecord
from app.retrieval import HybridRetriever

def _db(tmp_path):
    db = EvidenceDB(tmp_path / "x.sqlite")
    db.add_source(SourceRecord(source_id="s1", path="x.pdf", modality=Modality.pdf, title="X", sha256="abc"))
    db.add_evidence(EvidenceUnit(evidence_id="s1:e00001", source_id="s1", modality=Modality.pdf, text="Binary search uses sorted data.", concepts=["binary search"]))
    db.add_evidence(EvidenceUnit(evidence_id="s1:e00002", source_id="s1", modality=Modality.pdf, text="Stacks use last in first out.", concepts=["stack"]))
    return db

def test_lexical_retrieval_uses_fts5(tmp_path):
    db = _db(tmp_path)
    matches = db.fts_search("binary search")
    assert matches and matches[0][0] == "s1:e00001"
    r, t = HybridRetriever(db).search("binary search", mode="lexical")
    assert r and r[0].evidence_id == "s1:e00001" and not t.unsupported

def test_lexical_unsupported_query(tmp_path):
    db = _db(tmp_path)
    r, t = HybridRetriever(db).search("quantum entanglement", mode="lexical")
    assert r == [] and t.unsupported and t.reason == "no supported evidence matched"

def test_invalid_mode_is_explicitly_unsupported(tmp_path):
    db = _db(tmp_path)
    r, t = HybridRetriever(db).search("binary", mode="unknown")
    assert r == [] and t.unsupported and t.reason == "unsupported retrieval mode"

def test_semantic_retrieval_uses_persisted_embedding(tmp_path, monkeypatch):
    db = _db(tmp_path)
    db.add_embedding("s1:e00001", np.array([1.0, 0.0], dtype=np.float32))
    db.add_embedding("s1:e00002", np.array([0.0, 1.0], dtype=np.float32))
    retriever = HybridRetriever(db)
    class FakeModel:
        def encode(self, queries, normalize_embeddings=True):
            return np.array([[1.0, 0.0]], dtype=np.float32)
    monkeypatch.setattr(retriever, "_model", lambda: FakeModel())
    r, t = retriever.search("anything", mode="semantic")
    assert len(r) == 1
    assert r[0].evidence_id == "s1:e00001"
    assert r[0].semantic_score == 1.0
    assert t.result_ids == ["s1:e00001"]
    assert not t.unsupported

def test_ranking_tie_break_is_deterministic(tmp_path):
    db = _db(tmp_path)
    db.add_evidence(EvidenceUnit(evidence_id="s1:e00003", source_id="s1", modality=Modality.pdf, text="Binary search tree.", concepts=["binary search"]))
    r1, _ = HybridRetriever(db).search("binary search", mode="lexical")
    r2, _ = HybridRetriever(db).search("binary search", mode="lexical")
    assert [x.evidence_id for x in r1] == [x.evidence_id for x in r2]

def test_fts5_bm25_ranking_sensitivity(tmp_path):
    db = EvidenceDB(tmp_path / "fts_rank.sqlite")
    db.add_source(SourceRecord(source_id="s1", path="doc.pdf", modality=Modality.pdf, title="Doc", sha256="123"))
    # Doc A has multiple occurrences of "recursion"
    db.add_evidence(EvidenceUnit(
        evidence_id="s1:e00001", source_id="s1", modality=Modality.pdf,
        text="Recursion solves subproblems. In recursion, a base case stops infinite recursion.",
        concepts=["recursion"]
    ))
    # Doc B has a single occurrence
    db.add_evidence(EvidenceUnit(
        evidence_id="s1:e00002", source_id="s1", modality=Modality.pdf,
        text="An iterative loop can sometimes be rewritten using recursion.",
        concepts=["iteration"]
    ))
    matches = db.fts_search("recursion")
    assert len(matches) == 2
    # FTS5 bm25 rank is lower (more negative) for doc A
    assert matches[0][0] == "s1:e00001"

    r, t = HybridRetriever(db).search("recursion", mode="lexical")
    assert r[0].evidence_id == "s1:e00001"
    assert r[0].score >= r[1].score

def test_empty_and_whitespace_query_unsupported(tmp_path):
    db = _db(tmp_path)
    retriever = HybridRetriever(db)
    r1, t1 = retriever.search("", mode="hybrid")
    assert r1 == [] and t1.unsupported and t1.reason == "empty query"

    r2, t2 = retriever.search("    \n\t  ", mode="lexical")
    assert r2 == [] and t2.unsupported and t2.reason == "empty query"

def test_empty_database_unsupported(tmp_path):
    db = EvidenceDB(tmp_path / "empty.sqlite")
    r, t = HybridRetriever(db).search("anything", mode="hybrid")
    assert r == [] and t.unsupported and t.reason == "empty evidence index"

def test_semantic_missing_embeddings_unsupported(tmp_path):
    db = _db(tmp_path)
    retriever = HybridRetriever(db)
    r, t = retriever.search("binary search", mode="semantic")
    assert r == [] and t.unsupported and t.reason == "missing semantic embeddings"

def test_semantic_dimension_mismatch_raises(tmp_path, monkeypatch):
    db = _db(tmp_path)
    db.add_embedding("s1:e00001", np.array([1.0, 0.0], dtype=np.float32))
    retriever = HybridRetriever(db)
    class Fake3DModel:
        def encode(self, queries, normalize_embeddings=True):
            return np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
    monkeypatch.setattr(retriever, "_model", lambda: Fake3DModel())
    with pytest.raises(ValueError, match="dimension mismatch"):
        retriever.search("test", mode="semantic")

def test_hybrid_retrieval_weights_and_trace(tmp_path, monkeypatch):
    db = _db(tmp_path)
    db.add_embedding("s1:e00001", np.array([1.0, 0.0], dtype=np.float32))
    db.add_embedding("s1:e00002", np.array([0.0, 1.0], dtype=np.float32))
    retriever = HybridRetriever(db)
    class FakeModel:
        def encode(self, queries, normalize_embeddings=True):
            return np.array([[0.8, 0.2]], dtype=np.float32)
    monkeypatch.setattr(retriever, "_model", lambda: FakeModel())

    # Search with hybrid mode
    r, t = retriever.search("binary search", k=1, mode="hybrid")
    assert len(r) == 1
    assert r[0].evidence_id == "s1:e00001"
    # Hybrid score = 0.45 * lex + 0.55 * sem
    expected_score = round(0.45 * r[0].lexical_score + 0.55 * r[0].semantic_score, 6)
    assert abs(r[0].score - expected_score) < 1e-5

    # Check rich trace properties
    assert t.query == "binary search"
    assert t.mode == "hybrid"
    assert t.candidate_count == 2
    assert t.result_count == 1
    assert t.result_ids == ["s1:e00001"]
    assert t.source_ids == ["s1"]
    assert len(t.candidates) == 1
    assert t.candidates[0].evidence_id == "s1:e00001"
    assert t.ranking == ["s1:e00001"]
    assert not t.unsupported
    assert t.reason is None
