from __future__ import annotations
import re
from .models import RetrievalResult, RetrievalTrace

class HybridRetriever:
    def __init__(self,db,model_name="sentence-transformers/all-MiniLM-L6-v2"):
        self.db=db; self.model_name=model_name; self.model=None

    def _model(self):
        if self.model is None:
            from sentence_transformers import SentenceTransformer
            self.model=SentenceTransformer(self.model_name)
        return self.model

    @staticmethod
    def _lex(q,t):
        a=set(re.findall(r"\w+",q.lower())); b=set(re.findall(r"\w+",t.lower()))
        return len(a&b)/max(1,len(a))

    def _lexical_scores(self,query,rows):
        matched={evidence_id: rank for evidence_id,rank in self.db.fts_search(query)}
        return [self._lex(query,e.text+" "+" ".join(e.concepts+e.topics)) if e.evidence_id in matched else 0.0 for e in rows]

    def search(self,query,k=5,mode="hybrid"):
        if not query.strip():
            return [],RetrievalTrace(query=query,mode=mode,result_ids=[],unsupported=True,reason="empty query")
        if mode not in {"lexical","semantic","hybrid"}:
            return [],RetrievalTrace(query=query,mode=mode,result_ids=[],unsupported=True,reason="unsupported retrieval mode")
        rows=list(self.db.all_evidence())
        if not rows:
            return [],RetrievalTrace(query=query,mode=mode,result_ids=[],unsupported=True,reason="empty evidence index")

        lex=self._lexical_scores(query,rows); sem=[0.0]*len(rows)
        if mode in ("semantic","hybrid"):
            import numpy as np
            qv=self._model().encode([query],normalize_embeddings=True)[0]
            for i,e in enumerate(rows):
                v=self.db.get_embedding(e.evidence_id)
                if v is not None:
                    sem[i]=float(np.dot(qv,v))

        scores=lex if mode=="lexical" else sem if mode=="semantic" else [0.45*a+0.55*b for a,b in zip(lex,sem)]
        ranked=sorted(range(len(rows)),key=lambda i:(-scores[i],rows[i].evidence_id))
        out=[
            RetrievalResult(evidence_id=rows[i].evidence_id,score=float(scores[i]),
                lexical_score=float(lex[i]),semantic_score=float(sem[i]),
                source_id=rows[i].source_id,snippet=rows[i].text[:500],location=rows[i].location)
            for i in ranked[:max(0,k)] if scores[i]>0
        ]
        return out,RetrievalTrace(query=query,mode=mode,result_ids=[x.evidence_id for x in out],
            unsupported=not bool(out),reason=None if out else "no supported evidence matched")

def build_embeddings(db,model_name="sentence-transformers/all-MiniLM-L6-v2"):
    from sentence_transformers import SentenceTransformer
    m=SentenceTransformer(model_name)
    for e in db.all_evidence():
        db.add_embedding(e.evidence_id,m.encode(e.text,normalize_embeddings=True))
