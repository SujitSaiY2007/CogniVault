import numpy as np
from app.db import EvidenceDB
from app.models import EvidenceUnit,Modality,SourceRecord
from app.retrieval import HybridRetriever

def _db(tmp_path):
    db=EvidenceDB(tmp_path/"x.sqlite")
    db.add_source(SourceRecord(source_id="s1",path="x.pdf",modality=Modality.pdf,title="X",sha256="abc"))
    db.add_evidence(EvidenceUnit(evidence_id="s1:e00001",source_id="s1",modality=Modality.pdf,text="Binary search uses sorted data.",concepts=["binary search"]))
    db.add_evidence(EvidenceUnit(evidence_id="s1:e00002",source_id="s1",modality=Modality.pdf,text="Stacks use last in first out.",concepts=["stack"]))
    return db

def test_lexical_retrieval_uses_fts5(tmp_path):
    db=_db(tmp_path)
    matches=db.fts_search("binary search")
    assert matches and matches[0][0]=="s1:e00001"
    r,t=HybridRetriever(db).search("binary search",mode="lexical")
    assert r and r[0].evidence_id=="s1:e00001" and not t.unsupported

def test_lexical_unsupported_query(tmp_path):
    db=_db(tmp_path)
    r,t=HybridRetriever(db).search("quantum entanglement",mode="lexical")
    assert r==[] and t.unsupported and t.reason=="no supported evidence matched"

def test_invalid_mode_is_explicitly_unsupported(tmp_path):
    db=_db(tmp_path)
    r,t=HybridRetriever(db).search("binary",mode="unknown")
    assert r==[] and t.unsupported and t.reason=="unsupported retrieval mode"

def test_semantic_retrieval_uses_persisted_embedding(tmp_path,monkeypatch):
    db=_db(tmp_path)
    db.add_embedding("s1:e00001",np.array([1.0,0.0],dtype=np.float32))
    db.add_embedding("s1:e00002",np.array([0.0,1.0],dtype=np.float32))
    retriever=HybridRetriever(db)
    class FakeModel:
        def encode(self,queries,normalize_embeddings=True):
            return np.array([[1.0,0.0]],dtype=np.float32)
    monkeypatch.setattr(retriever,"_model",lambda:FakeModel())
    r,t=retriever.search("anything",mode="semantic")
    assert r[0].evidence_id=="s1:e00001"
    assert r[0].semantic_score>r[1].semantic_score
    assert t.result_ids==["s1:e00001","s1:e00002"]

def test_ranking_tie_break_is_deterministic(tmp_path):
    db=_db(tmp_path)
    db.add_evidence(EvidenceUnit(evidence_id="s1:e00003",source_id="s1",modality=Modality.pdf,text="Binary search tree.",concepts=["binary search"]))
    r1,_=HybridRetriever(db).search("binary search",mode="lexical")
    r2,_=HybridRetriever(db).search("binary search",mode="lexical")
    assert [x.evidence_id for x in r1]==[x.evidence_id for x in r2]
