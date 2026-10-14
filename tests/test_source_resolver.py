from app.db import EvidenceDB
from app.models import EvidenceUnit, Modality, SourceRecord
from app.source_resolver import resolve

def test_source_resolver_preserves_location(tmp_path):
    db = EvidenceDB(tmp_path / "x.sqlite")
    db.add_source(SourceRecord(source_id="s1", path="x.pdf", modality=Modality.pdf, title="X", sha256="abc"))
    db.add_evidence(EvidenceUnit(evidence_id="s1:e00001", source_id="s1", modality=Modality.pdf, text="page evidence", location={"page": 7}))
    r = resolve("s1:e00001", db)
    assert r is not None
    assert r["source_id"] == "s1"
    assert r["location"]["page"] == 7
    assert r["source_path"] == "x.pdf"
    assert r["source_title"] == "X"
    assert r["source_sha256"] == "abc"

def test_source_resolver_multimodal_modalities(tmp_path):
    db = EvidenceDB(tmp_path / "multimodal.sqlite")
    # PPTX
    db.add_source(SourceRecord(source_id="ppt_src", path="/slides.pptx", modality=Modality.pptx, title="Slide Deck", sha256="ppthash"))
    db.add_evidence(EvidenceUnit(evidence_id="ppt_src:e00001", source_id="ppt_src", modality=Modality.pptx, text="Slide content", location={"slide": 4}))
    r_pptx = resolve("ppt_src:e00001", db)
    assert r_pptx["location"]["slide"] == 4
    assert r_pptx["modality"] == "pptx"

    # Video transcript
    db.add_source(SourceRecord(source_id="vid_src", path="/lecture.mp4", modality=Modality.video, title="Lecture Video", sha256="vidhash"))
    db.add_evidence(EvidenceUnit(evidence_id="vid_src:e00001", source_id="vid_src", modality=Modality.video, text="Transcript line", location={"timestamp": "01:23:45"}))
    r_vid = resolve("vid_src:e00001", db)
    assert r_vid["location"]["timestamp"] == "01:23:45"
    assert r_vid["modality"] == "video"

def test_source_resolver_edge_cases(tmp_path):
    db = EvidenceDB(tmp_path / "edge.sqlite")
    db.add_source(SourceRecord(source_id="s1", path="x.pdf", modality=Modality.pdf, title="X", sha256="abc"))
    db.add_evidence(EvidenceUnit(evidence_id="s1:e00001", source_id="s1", modality=Modality.pdf, text="text", location={"page": 1}))

    # Unknown evidence ID
    assert resolve("unknown:e99999", db) is None

    # Empty and None evidence ID
    assert resolve("", db) is None
    assert resolve(None, db) is None

    # Invalid type
    assert resolve(12345, db) is None

    # Evidence exists but source missing in sources table
    db.conn.execute("PRAGMA foreign_keys=OFF")
    db.conn.execute("DELETE FROM sources WHERE source_id='s1'")
    db.conn.commit()
    r = resolve("s1:e00001", db)
    assert r is not None
    assert r["evidence_id"] == "s1:e00001"
    assert r["source_path"] is None
