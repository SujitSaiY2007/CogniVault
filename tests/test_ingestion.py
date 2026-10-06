from app.db import EvidenceDB
from app.models import Modality
from app.ingest import ingest_transcript
def test_video_timestamp_provenance(tmp_path):
    src=tmp_path/"demo.txt"; src.write_text("[00:12] Photosynthesis converts light energy.\n[01:03] Chlorophyll absorbs light.",encoding="utf-8")
    db=EvidenceDB(tmp_path/"x.sqlite"); ingest_transcript(src,db,"video1"); rows=list(db.all_evidence())
    assert len(rows)==2 and rows[0].modality is Modality.video and rows[0].location["timestamp"]=="00:12"
