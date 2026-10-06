from __future__ import annotations
from .db import EvidenceDB
def resolve(evidence_id,db:EvidenceDB):
    e=db.get_evidence(evidence_id)
    if e is None:return None
    result={"evidence_id":e.evidence_id,"source_id":e.source_id,"modality":e.modality.value,"location":e.location,"text":e.text,"evidence_type":e.evidence_type,"asset_id":e.asset_id}
    if e.asset_id:
        asset=db.get_asset(e.asset_id)
        if asset:
            result["asset"]={"asset_id":asset[0],"mime_type":asset[2],"sha256":asset[3],"width":asset[4],"height":asset[5],"size_bytes":len(asset[6])}
    return result
