from app.db import EvidenceDB
from app.models import Modality
from app.ingest import ingest_transcript

def test_video_timestamp_provenance(tmp_path):
    src = tmp_path / "demo.txt"
    src.write_text("[00:12] Photosynthesis converts light energy.\n[01:03] Chlorophyll absorbs light.", encoding="utf-8")
    db = EvidenceDB(tmp_path / "x.sqlite")
    ingest_transcript(src, db, "video1")
    rows = list(db.all_evidence())
    assert len(rows) == 2 and rows[0].modality is Modality.video and rows[0].location["timestamp"] == "00:12"

def test_transcript_multiple_timestamp_formats(tmp_path):
    transcript_content = (
        "[00:12] Standard bracketed minute:second.\n"
        "[01:23:45] Standard bracketed hour:minute:second.\n"
        "00:12 Unbracketed minute:second.\n"
        "00:01:23 Unbracketed hour:minute:second.\n"
        "02:15 - Hyphen-separated text.\n"
        "[03:45]: Colon-separated text.\n"
    )
    src = tmp_path / "lecture.txt"
    src.write_text(transcript_content, encoding="utf-8")
    db = EvidenceDB(tmp_path / "transcript.sqlite")
    sid = ingest_transcript(src, db, "lec01")

    rows = list(db.all_evidence())
    assert len(rows) == 6

    expected = [
        ("00:12", "Standard bracketed minute:second."),
        ("01:23:45", "Standard bracketed hour:minute:second."),
        ("00:12", "Unbracketed minute:second."),
        ("00:01:23", "Unbracketed hour:minute:second."),
        ("02:15", "Hyphen-separated text."),
        ("03:45", "Colon-separated text."),
    ]

    for idx, (expected_ts, expected_text) in enumerate(expected, 1):
        e = rows[idx - 1]
        assert e.source_id == "lec01"
        assert e.evidence_id == f"lec01:e{idx:05d}"
        assert e.modality == Modality.video
        assert e.location["timestamp"] == expected_ts
        assert e.text == expected_text
