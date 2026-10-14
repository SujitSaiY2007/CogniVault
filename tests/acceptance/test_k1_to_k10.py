import base64
import hashlib
import io
import numpy as np
import pytest
from pathlib import Path

import pymupdf
from pptx import Presentation

from app.db import EvidenceDB
from app.ingest import ingest_pdf, ingest_pptx, ingest_transcript
from app.models import EvidenceUnit, Modality, SourceRecord
from app.retrieval import HybridRetriever
from app.source_resolver import resolve

# Lightweight deterministic 1x1 PNG fixture
TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)

# ---------------------------------------------------------------------------
# K1 — Source Registration & Identity
# ---------------------------------------------------------------------------
def test_k1_source_registration_and_identity(tmp_path):
    """
    K1 Requirement: Sources must be registered with stable identifiers,
    SHA-256 source identity, path, title, modality, and structured metadata.
    """
    db = EvidenceDB(tmp_path / "k1.sqlite")
    sample_file = tmp_path / "source1.txt"
    content = b"Course material for CogniVault Track D."
    sample_file.write_bytes(content)
    expected_sha = hashlib.sha256(content).hexdigest()

    record = SourceRecord(
        source_id="src_k1_001",
        path=str(sample_file),
        modality=Modality.text,
        title="Source 1",
        sha256=expected_sha,
        metadata={"subject": "Computer Science", "grade": 12}
    )
    db.add_source(record)

    retrieved = db.get_source("src_k1_001")
    assert retrieved is not None
    assert retrieved.source_id == "src_k1_001"
    assert retrieved.sha256 == expected_sha
    assert retrieved.path == str(sample_file)
    assert retrieved.title == "Source 1"
    assert retrieved.modality == Modality.text
    assert retrieved.metadata["subject"] == "Computer Science"
    assert retrieved.metadata["grade"] == 12

    all_sources = db.all_sources()
    assert len(all_sources) == 1
    assert all_sources[0].source_id == "src_k1_001"

    # Edge case: nonexistent source returns None
    assert db.get_source("nonexistent") is None


# ---------------------------------------------------------------------------
# K2 — PDF Page Evidence & Deterministic Provenance
# ---------------------------------------------------------------------------
def test_k2_pdf_page_evidence(tmp_path):
    """
    K2 Requirement: PDF ingestion extracts text chunks with page-level provenance,
    deterministic IDs, source identity, and SHA-256 hash.
    """
    pdf_path = tmp_path / "textbook.pdf"
    doc = pymupdf.open()

    p1 = doc.new_page()
    p1.insert_text((72, 72), "Chapter 1: Principles of Algorithms and Asymptotic Growth.")

    p2 = doc.new_page()
    p2.insert_text((72, 72), "Chapter 2: Divide and Conquer paradigm in Sorting algorithms.")

    doc.save(pdf_path)
    doc.close()

    db = EvidenceDB(tmp_path / "k2.sqlite")
    sid = ingest_pdf(pdf_path, db, source_id="cs_book")
    assert sid == "cs_book"

    evidences = list(db.all_evidence())
    assert len(evidences) >= 2

    # Verify page 1 provenance
    e1 = next(e for e in evidences if e.location.get("page") == 1)
    assert e1.source_id == "cs_book"
    assert e1.evidence_id == "cs_book:e00001"
    assert e1.modality == Modality.pdf
    assert "Principles of Algorithms" in e1.text

    # Verify page 2 provenance
    e2 = next(e for e in evidences if e.location.get("page") == 2)
    assert e2.source_id == "cs_book"
    assert e2.evidence_id == "cs_book:e00002"
    assert e2.modality == Modality.pdf
    assert "Divide and Conquer" in e2.text


# ---------------------------------------------------------------------------
# K3 — PPTX Slide Evidence & Slide-Level Provenance
# ---------------------------------------------------------------------------
def test_k3_pptx_slide_evidence(tmp_path):
    """
    K3 Requirement: PPTX ingestion extracts slide text with slide-level provenance,
    deterministic IDs, and slide locators.
    """
    pptx_path = tmp_path / "lecture.pptx"
    prs = Presentation()

    slide1 = prs.slides.add_slide(prs.slide_layouts[1])
    slide1.shapes.title.text = "Lecture 1: Introduction to Data Structures"

    slide2 = prs.slides.add_slide(prs.slide_layouts[1])
    slide2.shapes.title.text = "Lecture 1: Stacks and Queues Overview"

    prs.save(pptx_path)

    db = EvidenceDB(tmp_path / "k3.sqlite")
    sid = ingest_pptx(pptx_path, db, source_id="lec_slides")
    assert sid == "lec_slides"

    evidences = list(db.all_evidence())
    assert len(evidences) >= 2

    s1_ev = next(e for e in evidences if e.location.get("slide") == 1)
    assert s1_ev.evidence_id == "lec_slides:e00001"
    assert s1_ev.modality == Modality.pptx
    assert "Introduction to Data Structures" in s1_ev.text

    s2_ev = next(e for e in evidences if e.location.get("slide") == 2)
    assert s2_ev.evidence_id == "lec_slides:e00002"
    assert s2_ev.modality == Modality.pptx
    assert "Stacks and Queues Overview" in s2_ev.text


# ---------------------------------------------------------------------------
# K4 — Transcript Timestamp Evidence Across Formats
# ---------------------------------------------------------------------------
def test_k4_transcript_timestamp_evidence(tmp_path):
    """
    K4 Requirement: Transcript ingestion parses diverse timestamp formats
    ([mm:ss], [hh:mm:ss], mm:ss, hh:mm:ss) and binds each to Modality.video.
    """
    transcript_path = tmp_path / "lecture_transcript.txt"
    lines = [
        "[00:12] Welcome to the machine learning lecture.",
        "[01:23:45] Gradient descent optimizes convex objective functions.",
        "02:30 Learning rate selection determines convergence speed.",
        "00:01:23 Backpropagation propagates error gradients backwards.",
        "03:15 - Stochastic gradient descent uses mini-batches.",
    ]
    transcript_path.write_text("\n".join(lines), encoding="utf-8")

    db = EvidenceDB(tmp_path / "k4.sqlite")
    sid = ingest_transcript(transcript_path, db, source_id="ml_video")
    assert sid == "ml_video"

    evidences = list(db.all_evidence())
    assert len(evidences) == 5

    expected_timestamps = ["00:12", "01:23:45", "02:30", "00:01:23", "03:15"]
    for idx, expected_ts in enumerate(expected_timestamps, 1):
        e = evidences[idx - 1]
        assert e.evidence_id == f"ml_video:e{idx:05d}"
        assert e.source_id == "ml_video"
        assert e.modality == Modality.video
        assert e.location["timestamp"] == expected_ts
        assert len(e.text) > 0


# ---------------------------------------------------------------------------
# K5 — Image / Figure Evidence as First-Class Evidence
# ---------------------------------------------------------------------------
def test_k5_embedded_figure_image_evidence(tmp_path):
    """
    K5 Requirement: Embedded figures and images are extracted as first-class,
    independently addressable evidence units with MIME type, SHA-256 hash,
    and asset storage.
    """
    pdf_path = tmp_path / "diagrams.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Figure 1 illustrates the neural network architecture.")
    page.insert_image(pymupdf.Rect(72, 100, 172, 200), stream=TINY_PNG)
    doc.save(pdf_path)
    doc.close()

    db = EvidenceDB(tmp_path / "k5.sqlite")
    ingest_pdf(pdf_path, db, source_id="nn_paper")

    images = [e for e in db.all_evidence() if e.evidence_type == "image"]
    assert len(images) == 1
    img_ev = images[0]

    assert img_ev.modality == Modality.image
    assert img_ev.location["page"] == 1
    assert img_ev.asset_id is not None
    assert img_ev.asset_id.startswith("asset:")

    # Verify asset storage
    asset_record = db.get_asset(img_ev.asset_id)
    assert asset_record is not None
    aid, eid, mime, digest, width, height, raw_data = asset_record
    assert aid == img_ev.asset_id
    assert eid == img_ev.evidence_id
    assert mime == "image/png"
    assert digest == hashlib.sha256(raw_data).hexdigest()
    assert raw_data.startswith(b"\x89PNG")


# ---------------------------------------------------------------------------
# K6 — Topic / Concept / Prerequisite Representation
# ---------------------------------------------------------------------------
def test_k6_topic_concept_prerequisite_representation(tmp_path):
    """
    K6 Requirement: Clean relational model supporting many-to-many
    evidence <-> concepts, topics, and directed prerequisite chains
    with transitive closure and cycle handling.
    """
    db = EvidenceDB(tmp_path / "k6.sqlite")

    db.add_topic("physics", "Physics", "Classical Mechanics")
    db.add_concept("vectors", "Vectors", topic_id="physics", description="Magnitude and direction")
    db.add_concept("velocity", "Velocity", topic_id="physics", description="Rate of displacement")
    db.add_concept("acceleration", "Acceleration", topic_id="physics", description="Rate of velocity change")

    # Prerequisite chain: acceleration -> velocity -> vectors
    db.link_concept_prerequisite("acceleration", "velocity")
    db.link_concept_prerequisite("velocity", "vectors")

    assert db.get_concept_prerequisites("acceleration") == ["velocity"]
    assert db.get_all_prerequisites("acceleration") == ["velocity", "vectors"]

    # Ingest evidence linking multiple concepts
    db.add_source(SourceRecord(source_id="phys_src", path="phys.pdf", modality=Modality.pdf, title="Physics", sha256="h0"))
    db.add_evidence(EvidenceUnit(
        evidence_id="phys_src:e00001",
        source_id="phys_src",
        modality=Modality.pdf,
        text="Acceleration is the derivative of the velocity vector.",
        location={"page": 12},
        topics=["physics"],
        concepts=["acceleration", "velocity", "vectors"]
    ))
    db.add_evidence(EvidenceUnit(
        evidence_id="phys_src:e00002",
        source_id="phys_src",
        modality=Modality.pdf,
        text="A vector has both magnitude and direction.",
        location={"page": 2},
        topics=["physics"],
        concepts=["vectors"]
    ))

    # Evidence -> Concepts
    e1_concepts = [c.name for c in db.get_concepts_for_evidence("phys_src:e00001")]
    assert set(e1_concepts) == {"Acceleration", "Velocity", "Vectors"}

    # Concept -> Evidence
    vec_evidence = [e.evidence_id for e in db.get_evidence_for_concept("vectors")]
    assert "phys_src:e00001" in vec_evidence and "phys_src:e00002" in vec_evidence

    acc_evidence = [e.evidence_id for e in db.get_evidence_for_concept("acceleration")]
    assert "phys_src:e00001" in acc_evidence and "phys_src:e00002" not in acc_evidence


# ---------------------------------------------------------------------------
# K7 — SQLite FTS5 Lexical Retrieval
# ---------------------------------------------------------------------------
def test_k7_lexical_fts5_retrieval(tmp_path):
    """
    K7 Requirement: Lexical retrieval backed by genuine SQLite FTS5 MATCH,
    BM25 ranking, and deterministic scores.
    """
    db = EvidenceDB(tmp_path / "k7.sqlite")
    db.add_source(SourceRecord(source_id="algo_src", path="algo.pdf", modality=Modality.pdf, title="Algorithms", sha256="h1"))

    db.add_evidence(EvidenceUnit(
        evidence_id="algo_src:e00001",
        source_id="algo_src",
        modality=Modality.pdf,
        text="Binary search requires a sorted array to achieve logarithmic time.",
        concepts=["binary search"]
    ))
    db.add_evidence(EvidenceUnit(
        evidence_id="algo_src:e00002",
        source_id="algo_src",
        modality=Modality.pdf,
        text="Quick sort is an in-place divide and conquer sorting algorithm.",
        concepts=["sorting"]
    ))

    # Direct FTS5 MATCH verification
    matches = db.fts_search("binary search")
    assert len(matches) == 1
    assert matches[0][0] == "algo_src:e00001"

    # Retriever lexical mode
    retriever = HybridRetriever(db)
    results, trace = retriever.search("binary search", mode="lexical")
    assert len(results) == 1
    assert results[0].evidence_id == "algo_src:e00001"
    assert results[0].lexical_score > 0.0
    assert not trace.unsupported
    assert trace.reason is None


# ---------------------------------------------------------------------------
# K8 — Semantic Retrieval & Persisted Embeddings
# ---------------------------------------------------------------------------
def test_k8_semantic_retrieval_persisted_embeddings(tmp_path, monkeypatch):
    """
    K8 Requirement: Embeddings can be persisted and reused without recomputation,
    recording dimension and model metadata, and catching dimension mismatch.
    """
    db = EvidenceDB(tmp_path / "k8.sqlite")
    db.add_source(SourceRecord(source_id="s1", path="doc.pdf", modality=Modality.pdf, title="Doc", sha256="h2"))
    db.add_evidence(EvidenceUnit(evidence_id="s1:e00001", source_id="s1", modality=Modality.pdf, text="Photosynthesis uses sunlight."))
    db.add_evidence(EvidenceUnit(evidence_id="s1:e00002", source_id="s1", modality=Modality.pdf, text="Cellular respiration produces ATP."))

    # Persist controlled 2D embeddings
    db.add_embedding("s1:e00001", np.array([1.0, 0.0], dtype=np.float32), model_name="test-sim-2d")
    db.add_embedding("s1:e00002", np.array([0.0, 1.0], dtype=np.float32), model_name="test-sim-2d")

    meta = db.get_embedding_metadata()
    assert meta["dimension"] == 2
    assert meta["model_name"] == "test-sim-2d"

    # Mock query model returning query aligned with evidence 1
    retriever = HybridRetriever(db)
    class ControlledModel:
        def encode(self, queries, normalize_embeddings=True):
            return np.array([[0.95, 0.05]], dtype=np.float32)

    monkeypatch.setattr(retriever, "_model", lambda: ControlledModel())

    results, trace = retriever.search("sunlight energy", mode="semantic")
    assert len(results) == 2
    assert results[0].evidence_id == "s1:e00001"
    assert results[0].semantic_score > results[1].semantic_score
    assert not trace.unsupported

    # Test dimension mismatch validation
    class Mismatched3DModel:
        def encode(self, queries, normalize_embeddings=True):
            return np.array([[1.0, 0.0, 0.0]], dtype=np.float32)

    monkeypatch.setattr(retriever, "_model", lambda: Mismatched3DModel())
    with pytest.raises(ValueError, match="dimension mismatch"):
        retriever.search("test", mode="semantic")


# ---------------------------------------------------------------------------
# K9 — Deterministic Hybrid Retrieval & Retrieval Trace
# ---------------------------------------------------------------------------
def test_k9_deterministic_hybrid_retrieval_and_trace(tmp_path, monkeypatch):
    """
    K9 Requirement: Deterministic linear combination of lexical + semantic scores
    (0.45 * lex + 0.55 * sem), stable tie-breaking, top-k support,
    and structured machine-readable trace.
    """
    db = EvidenceDB(tmp_path / "k9.sqlite")
    db.add_source(SourceRecord(source_id="src1", path="text.pdf", modality=Modality.pdf, title="Text", sha256="h3"))
    db.add_evidence(EvidenceUnit(evidence_id="src1:e00001", source_id="src1", modality=Modality.pdf, text="Dynamic programming memoization.", concepts=["dp"]))
    db.add_evidence(EvidenceUnit(evidence_id="src1:e00002", source_id="src1", modality=Modality.pdf, text="Greedy algorithm optimal choice.", concepts=["greedy"]))

    db.add_embedding("src1:e00001", np.array([0.9, 0.1], dtype=np.float32), model_name="mock")
    db.add_embedding("src1:e00002", np.array([0.1, 0.9], dtype=np.float32), model_name="mock")

    retriever = HybridRetriever(db)
    class ControlledModel:
        def encode(self, queries, normalize_embeddings=True):
            return np.array([[0.8, 0.2]], dtype=np.float32)

    monkeypatch.setattr(retriever, "_model", lambda: ControlledModel())

    results, trace = retriever.search("memoization dynamic", k=1, mode="hybrid")
    assert len(results) == 1
    assert results[0].evidence_id == "src1:e00001"

    # Verify score formula: 0.45 * lex + 0.55 * sem
    expected_score = round(0.45 * results[0].lexical_score + 0.55 * results[0].semantic_score, 6)
    assert abs(results[0].score - expected_score) < 1e-5

    # Verify trace schema
    assert trace.query == "memoization dynamic"
    assert trace.mode == "hybrid"
    assert trace.candidate_count == 2
    assert trace.result_count == 1
    assert trace.result_ids == ["src1:e00001"]
    assert trace.source_ids == ["src1"]
    assert len(trace.candidates) == 1
    assert trace.candidates[0].evidence_id == "src1:e00001"
    assert trace.candidates[0].score == results[0].score
    assert trace.ranking == ["src1:e00001"]
    assert not trace.unsupported

    # Tie-breaking determinism check
    r1, _ = retriever.search("dynamic", mode="hybrid")
    r2, _ = retriever.search("dynamic", mode="hybrid")
    assert [x.evidence_id for x in r1] == [x.evidence_id for x in r2]


# ---------------------------------------------------------------------------
# K10 — End-to-End Provenance Resolution & Unsupported Behavior
# ---------------------------------------------------------------------------
def test_k10_end_to_end_provenance_and_unsupported_behavior(tmp_path, monkeypatch):
    """
    K10 Requirement:
    1. Complete pipeline: Ingestion -> DB -> Retrieval -> RetrievalResult ->
       Source Resolver -> Exact Source Location (verified for PDF and Video).
    2. Explicit refusal / unsupported query handling without fabricating evidence.
    """
    # 1. Pipeline verification
    # Create PDF with 3 pages
    pdf_file = tmp_path / "course.pdf"
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Page one: Course syllabus.")
    doc.new_page().insert_text((72, 72), "Page two: Mathematical induction proofs.")
    doc.new_page().insert_text((72, 72), "Page three: Graph theory algorithms.")
    doc.save(pdf_file)
    doc.close()

    db = EvidenceDB(tmp_path / "k10.sqlite")
    pdf_sid = ingest_pdf(pdf_file, db, source_id="course_pdf")

    # Ingest Transcript
    tr_file = tmp_path / "course_video.txt"
    tr_file.write_text("[00:45] Induction requires a base case and an inductive step.", encoding="utf-8")
    vid_sid = ingest_transcript(tr_file, db, source_id="course_vid")

    retriever = HybridRetriever(db)

    # Search for induction proofs
    results, trace = retriever.search("induction proofs", mode="lexical")
    assert len(results) >= 1
    top_result = results[0]

    # Resolve evidence ID back to source location
    resolved = resolve(top_result.evidence_id, db)
    assert resolved is not None
    assert resolved["evidence_id"] == top_result.evidence_id
    assert resolved["source_id"] == pdf_sid
    assert resolved["source_path"] == str(pdf_file)
    assert resolved["modality"] == "pdf"
    assert resolved["location"]["page"] == 2
    assert "induction" in resolved["text"].lower()

    # Resolve video transcript
    video_ev = next(e for e in db.all_evidence() if e.modality == Modality.video)
    vid_resolved = resolve(video_ev.evidence_id, db)
    assert vid_resolved is not None
    assert vid_resolved["source_id"] == vid_sid
    assert vid_resolved["location"]["timestamp"] == "00:45"
    assert vid_resolved["modality"] == "video"

    # 2. Unsupported query behaviors (never fabricate answers)
    # Case A: Empty query
    r_empty, t_empty = retriever.search("", mode="hybrid")
    assert r_empty == [] and t_empty.unsupported and t_empty.reason == "empty query"

    # Case B: Whitespace query
    r_ws, t_ws = retriever.search("   \t  \n  ", mode="lexical")
    assert r_ws == [] and t_ws.unsupported and t_ws.reason == "empty query"

    # Case C: Off-corpus / unsupported query
    r_off, t_off = retriever.search("quantum teleportation black hole", mode="lexical")
    assert r_off == [] and t_off.unsupported and t_off.reason == "no supported evidence matched"

    # Case D: Missing embeddings in semantic mode
    r_noemb, t_noemb = retriever.search("induction", mode="semantic")
    assert r_noemb == [] and t_noemb.unsupported and t_noemb.reason == "missing semantic embeddings"

    # Case E: Unsupported retrieval mode
    r_mode, t_mode = retriever.search("induction", mode="invalid_mode")
    assert r_mode == [] and t_mode.unsupported and t_mode.reason == "unsupported retrieval mode"
