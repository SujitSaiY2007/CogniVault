from app.db import EvidenceDB
from app.models import EvidenceUnit,Modality,SourceRecord
def test_evidence_id_roundtrip(tmp_path):
    db=EvidenceDB(tmp_path/"x.sqlite")
    db.add_source(SourceRecord(source_id="s1",path="x.pdf",modality=Modality.pdf,title="X",sha256="abc"))
    db.add_evidence(EvidenceUnit(evidence_id="s1:e00001",source_id="s1",modality=Modality.pdf,text="Concept evidence.",location={"page":3},concepts=["concept"]))
    e=db.get_evidence("s1:e00001")
    assert e.location["page"]==3 and e.source_id=="s1"
