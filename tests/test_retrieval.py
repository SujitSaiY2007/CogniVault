from app.db import EvidenceDB
from app.models import EvidenceUnit,Modality,SourceRecord
from app.retrieval import HybridRetriever
def test_lexical_retrieval(tmp_path):
    db=EvidenceDB(tmp_path/"x.sqlite")
    db.add_source(SourceRecord(source_id="s1",path="x.pdf",modality=Modality.pdf,title="X",sha256="abc"))
    db.add_evidence(EvidenceUnit(evidence_id="s1:e00001",source_id="s1",modality=Modality.pdf,text="Binary search uses sorted data.",concepts=["binary search"]))
    r,t=HybridRetriever(db).search("binary search",mode="lexical")
    assert r and r[0].evidence_id=="s1:e00001" and not t.unsupported
