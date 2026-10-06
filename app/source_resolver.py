from __future__ import annotations
from .db import EvidenceDB
def resolve(evidence_id,db:EvidenceDB):
    e=db.get_evidence(evidence_id)
    if e is None:return None
    return {"evidence_id":e.evidence_id,"source_id":e.source_id,"modality":e.modality.value,"location":e.location,"text":e.text}
