from app.db import EvidenceDB
from app.models import EvidenceUnit,Modality,SourceRecord
from app.source_resolver import resolve
def test_source_resolver_preserves_location(tmp_path):
    db=EvidenceDB(tmp_path/"x.sqlite")
    db.add_source(SourceRecord(source_id="s1",path="x.pdf",modality=Modality.pdf,title="X",sha256="abc"))
    db.add_evidence(EvidenceUnit(evidence_id="s1:e00001",source_id="s1",modality=Modality.pdf,text="page evidence",location={"page":7}))
    r=resolve("s1:e00001",db)
    assert r["source_id"]=="s1" and r["location"]["page"]==7
