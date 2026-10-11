from __future__ import annotations
from .db import EvidenceDB

def resolve(evidence_id: str, db: EvidenceDB) -> dict | None:
    if not evidence_id or not isinstance(evidence_id, str):
        return None
    e = db.get_evidence(evidence_id)
    if e is None:
        return None
    source = db.get_source(e.source_id)
    result = {
        "evidence_id": e.evidence_id,
        "source_id": e.source_id,
        "source_path": source.path if source else None,
        "source_title": source.title if source else None,
        "source_sha256": source.sha256 if source else None,
        "source_metadata": source.metadata if source else {},
        "modality": e.modality.value,
        "location": e.location,
        "text": e.text,
        "evidence_type": e.evidence_type,
        "asset_id": e.asset_id,
        "topics": e.topics,
        "concepts": e.concepts,
        "metadata": e.metadata,
    }
    if e.asset_id:
        asset = db.get_asset(e.asset_id)
        if asset:
            result["asset"] = {
                "asset_id": asset[0],
                "mime_type": asset[2],
                "sha256": asset[3],
                "width": asset[4],
                "height": asset[5],
                "size_bytes": len(asset[6]),
            }
    return result


class SourceResolver:
    """Object-oriented resolver providing physical source and locator resolution."""

    def __init__(self, db: EvidenceDB):
        self.db = db

    def resolve(self, evidence_id: str) -> dict | None:
        return resolve(evidence_id, self.db)

