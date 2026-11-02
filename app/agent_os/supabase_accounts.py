"""Supabase-backed account/session and private material persistence."""
from __future__ import annotations
import hashlib
import time
from .supabase_store import SupabaseStore


def _eq(value: str) -> str:
    return f"eq.{value}"


class SupabaseAuth:
    def __init__(self, store: SupabaseStore):
        self.store = store

    def create_user(self, username: str, password_hash: str, learner_id: str) -> None:
        self.store.insert("cognivault_users", [{
            "username": username, "password_hash": password_hash, "learner_id": learner_id,
        }])

    def get_user(self, username: str):
        rows = self.store.select("cognivault_users", params={
            "select": "username,password_hash,learner_id",
            "username": _eq(username), "limit": "1",
        })
        return rows[0] if rows else None

    def issue_session(self, token: str, username: str, learner_id: str, ttl_seconds: int = 30 * 86400):
        now = int(time.time())
        self.store.delete("cognivault_sessions", params={"expires_at": f"lt.{now}"})
        self.store.insert("cognivault_sessions", [{
            "token_hash": hashlib.sha256(token.encode()).hexdigest(),
            "username": username, "expires_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + ttl_seconds)),
        }])

    def resolve_token(self, token: str):
        digest = hashlib.sha256(token.encode()).hexdigest()
        rows = self.store.select("cognivault_sessions", params={
            "select": "username,expires_at,cognivault_users(learner_id)",
            "token_hash": _eq(digest), "limit": "1",
        })
        if not rows:
            return None
        row = rows[0]
        # PostgREST relationship expansion can be object or singleton array depending on cardinality.
        user = row.get("cognivault_users")
        if isinstance(user, list):
            user = user[0] if user else None
        if not user:
            return None
        return row["username"], user["learner_id"]

    def revoke_token(self, token: str):
        self.store.delete("cognivault_sessions", params={
            "token_hash": _eq(hashlib.sha256(token.encode()).hexdigest()),
        })


class SupabaseUserMaterials:
    """Private source/evidence storage. Every method is scoped by validated owner_id."""
    def __init__(self, store: SupabaseStore):
        self.store = store

    def list_sources(self, owner_id: str):
        return self.store.select("user_sources", params={
            "select": "source_id,filename,title,modality,sha256,evidence_count,created_at",
            "owner_id": _eq(owner_id), "order": "created_at.desc",
        }) or []

    def get_source(self, owner_id: str, source_id: str):
        rows = self.store.select("user_sources", params={
            "select": "source_id,owner_id,filename,title,modality,sha256,storage_path,evidence_count,created_at",
            "owner_id": _eq(owner_id), "source_id": _eq(source_id), "limit": "1",
        })
        return rows[0] if rows else None

    def list_evidence(self, owner_id: str, source_id: str):
        return self.store.select("user_evidence", params={
            "select": "evidence_id,source_id,modality,evidence_text,location,evidence_type,metadata",
            "owner_id": _eq(owner_id), "source_id": _eq(source_id), "order": "evidence_id.asc",
        }) or []

    def delete_source(self, owner_id: str, source_id: str):
        source = self.get_source(owner_id, source_id)
        if not source:
            return False
        self.store.delete("user_sources", params={
            "owner_id": _eq(owner_id), "source_id": _eq(source_id),
        })
        self.store.remove_private([source["storage_path"]])
        return True

    def create_source(self, record: dict):
        self.store.insert("user_sources", [record])

    def create_evidence_batch(self, records: list[dict]):
        if records:
            self.store.insert("user_evidence", records)

    def search_evidence(self, owner_id: str, query: str, limit: int = 5):
        rows = self.store.select("user_evidence", params={
            "select": "evidence_id,source_id,modality,evidence_text,location,evidence_type,metadata",
            "owner_id": _eq(owner_id), "limit": "5000",
        }) or []
        terms = {term.lower() for term in query.split() if len(term) > 2}
        scored = []
        for row in rows:
            content = (row.get("evidence_text") or "").lower()
            score = sum(content.count(term) for term in terms)
            if score:
                scored.append((score, row))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [row for _, row in scored[:max(1, min(limit, 10))]

    def get_progress_snapshot(self, owner_id: str):
        rows = self.store.select("learner_state_snapshots", params={
            "select": "snapshot_json", "owner_id": _eq(owner_id), "limit": "1",
        })
        return rows[0].get("snapshot_json") if rows else {}

    def save_progress_snapshot(self, owner_id: str, snapshot: dict):
        self.store.insert("learner_state_snapshots", [{
            "owner_id": owner_id, "snapshot_json": snapshot,
        }], upsert=True)
