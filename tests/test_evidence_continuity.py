import base64
import pytest
from app.db import EvidenceDB
from app.ingest import ingest_pdf, ingest_pptx, ingest_transcript
from app.retrieval import HybridRetriever
from app.source_resolver import resolve

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")

def test_pdf_evidence_id_continuity_e2e(tmp_path):
    import pymupdf
    pdf_path = tmp_path / "textbook.pdf"
    doc = pymupdf.open()
    p1 = doc.new_page()
    p1.insert_text((72, 72), "Chapter 1: Introductory Mathematics and Basic Arithmetic.")
    p2 = doc.new_page()
    p2.insert_text((72, 72), "Chapter 2: Foundations of Euclidean Geometry and Axioms.")
    p3 = doc.new_page()
    p3.insert_text((72, 72), "Pythagorean theorem states that for a right triangle a squared plus b squared equals c squared.")
    doc.save(pdf_path)
    doc.close()

    db = EvidenceDB(tmp_path / "continuity_pdf.sqlite")
    sid = ingest_pdf(pdf_path, db, source_id="math_book")

    retriever = HybridRetriever(db)
    results, trace = retriever.search("Pythagorean theorem right triangle", mode="lexical")

    assert len(results) > 0, "Retrieval should return matching evidence"
    top_result = results[0]

    # Verify evidence_id in retrieval result matches trace
    assert top_result.evidence_id == trace.result_ids[0]
    assert top_result.source_id == "math_book"

    # Resolve through source resolver
    resolved = resolve(top_result.evidence_id, db)
    assert resolved is not None
    assert resolved["evidence_id"] == top_result.evidence_id
    assert resolved["source_id"] == "math_book"
    assert resolved["modality"] == "pdf"
    assert resolved["source_path"] == str(pdf_path)
    assert resolved["location"]["page"] == 3
    assert "Pythagorean theorem" in resolved["text"]

def test_pptx_evidence_id_continuity_e2e(tmp_path):
    from pptx import Presentation
    prs = Presentation()
    s1 = prs.slides.add_slide(prs.slide_layouts[1])
    s1.shapes.title.text = "Physics Overview Slide Deck"
    s2 = prs.slides.add_slide(prs.slide_layouts[1])
    s2.shapes.title.text = "Newton second law states that net force equals mass times acceleration."
    pptx_path = tmp_path / "lecture.pptx"
    prs.save(pptx_path)

    db = EvidenceDB(tmp_path / "continuity_pptx.sqlite")
    sid = ingest_pptx(pptx_path, db, source_id="phys_slides")

    retriever = HybridRetriever(db)
    results, trace = retriever.search("Newton second law force mass", mode="lexical")

    assert len(results) > 0
    top = results[0]
    assert top.evidence_id == trace.result_ids[0]

    resolved = resolve(top.evidence_id, db)
    assert resolved is not None
    assert resolved["evidence_id"] == top.evidence_id
    assert resolved["source_id"] == "phys_slides"
    assert resolved["modality"] == "pptx"
    assert resolved["location"]["slide"] == 2
    assert "Newton second law" in resolved["text"]

def test_transcript_evidence_id_continuity_e2e(tmp_path):
    transcript_file = tmp_path / "lecture.txt"
    transcript_file.write_text(
        "[00:05] Welcome to general biology class.\n"
        "[04:32] Mitochondria are the powerhouses of the cell generating ATP.\n"
        "[10:15] Ribosomes are responsible for protein synthesis.\n",
        encoding="utf-8"
    )

    db = EvidenceDB(tmp_path / "continuity_transcript.sqlite")
    sid = ingest_transcript(transcript_file, db, source_id="bio_lec")

    retriever = HybridRetriever(db)
    results, trace = retriever.search("Mitochondria powerhouses ATP", mode="lexical")

    assert len(results) > 0
    top = results[0]
    assert top.evidence_id == trace.result_ids[0]

    resolved = resolve(top.evidence_id, db)
    assert resolved is not None
    assert resolved["evidence_id"] == top.evidence_id
    assert resolved["source_id"] == "bio_lec"
    assert resolved["modality"] == "video"
    assert resolved["location"]["timestamp"] == "04:32"
    assert "Mitochondria" in resolved["text"]

def test_embedded_image_evidence_id_continuity_e2e(tmp_path):
    import pymupdf
    pdf_path = tmp_path / "diagrams.pdf"
    doc = pymupdf.open()
    p1 = doc.new_page()
    p1.insert_text((72, 72), "Introduction to cellular diagrams.")
    p2 = doc.new_page()
    p2.insert_text((72, 72), "Diagram caption for cellular organelle.")
    p2.insert_image(pymupdf.Rect(72, 100, 172, 200), stream=PNG)
    doc.save(pdf_path)
    doc.close()

    db = EvidenceDB(tmp_path / "continuity_img.sqlite")
    sid = ingest_pdf(pdf_path, db, source_id="diagram_doc")

    # Find the image evidence unit
    image_units = [e for e in db.all_evidence() if e.evidence_type == "image"]
    assert len(image_units) == 1
    img = image_units[0]

    # Resolve through source resolver
    resolved = resolve(img.evidence_id, db)
    assert resolved is not None
    assert resolved["evidence_id"] == img.evidence_id
    assert resolved["source_id"] == "diagram_doc"
    assert resolved["evidence_type"] == "image"
    assert resolved["location"]["page"] == 2
    assert resolved["asset_id"] == img.asset_id
    assert resolved["asset"]["mime_type"] == "image/png"
    assert resolved["asset"]["size_bytes"] > 0
