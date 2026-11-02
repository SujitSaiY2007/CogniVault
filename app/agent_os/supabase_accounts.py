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
        self.store.delete("cognivault_sessions", params={"expires_at": f"lt.{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(now))}"})
        self.store.insert("cognivault_sessions", [{
            "token_hash": hashlib.sha256(token.encode()).hexdigest(),
            "username": username, "expires_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + ttl_seconds)),
        }])

    def resolve_token(self, token: str):
        digest = hashlib.sha256(token.encode()).hexdigest()
        rows = self.store.select("cognivault_sessions", params={
            "select": "username,expires_at,cognivault_users(learner_id)",
            "token_hash": _eq(digest), "expires_at": f"gt.{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}", "limit": "1",
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


def _paged_select(store: SupabaseStore, table: str, params: dict, page_size: int = 1000, max_rows: int = 5000):
    rows = []
    offset = 0
    while offset < max_rows:
        page = store.select(table, params={**params, "limit": str(page_size), "offset": str(offset)})
        if not page:
            break
        rows.extend(page)
        offset += len(page)
        if len(page) < page_size:
            break
    return rows[:max_rows]


class SupabaseUserMaterials:
    """Private source/evidence storage. Every method is scoped by validated owner_id."""
    def __init__(self, store: SupabaseStore):
        self.store = store

    def list_sources(self, owner_id: str):
        return self.store.select("user_sources", params={
            "select": "source_id,filename,title,modality,sha256,evidence_count,file_size_bytes,created_at",
            "owner_id": _eq(owner_id), "order": "created_at.desc",
        }) or []

    def get_source(self, owner_id: str, source_id: str):
        rows = self.store.select("user_sources", params={
            "select": "source_id,owner_id,filename,title,modality,sha256,storage_path,evidence_count,created_at",
            "owner_id": _eq(owner_id), "source_id": _eq(source_id), "limit": "1",
        })
        return rows[0] if rows else None

    def list_evidence(self, owner_id: str, source_id: str):
        rows = _paged_select(self.store, "user_evidence", {
            "select": "evidence_id,source_id,modality,evidence_text,location,evidence_type,metadata",
            "owner_id": _eq(owner_id), "source_id": _eq(source_id), "order": "evidence_id.asc",
        })
        result = []
        for row in rows:
            meta = row.get("metadata") or {}
            result.append({
                "evidence_id": row["evidence_id"], "source_id": row["source_id"],
                "modality": row["modality"], "text": row.get("evidence_text", ""),
                "location": row.get("location") or {}, "evidence_type": row.get("evidence_type", "text"),
                "asset_id": None, "topics": meta.get("topics", []), "concepts": meta.get("concepts", []),
                "prerequisites": meta.get("prerequisites", []), "metadata": meta,
            })
        return result

    def delete_source(self, owner_id: str, source_id: str):
        source = self.get_source(owner_id, source_id)
        if not source:
            return False
        self.store.delete("user_sources", params={
            "owner_id": _eq(owner_id), "source_id": _eq(source_id),
        })
        self.store.remove_private([source["storage_path"]])
        return True

    def get_global_storage_usage(self) -> int:
        rows = _paged_select(self.store, "user_sources", {"select": "file_size_bytes"}, max_rows=10000)
        return sum(int(row.get("file_size_bytes", 0)) for row in rows)

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
        return [row for _, row in scored[:max(1, min(limit, 10))]]

    def get_progress_snapshot(self, owner_id: str):
        rows = self.store.select("learner_state_snapshots", params={
            "select": "snapshot_json", "owner_id": _eq(owner_id), "limit": "1",
        })
        return rows[0].get("snapshot_json") if rows else {}

    def save_progress_snapshot(self, owner_id: str, snapshot: dict):
        self.store.insert("learner_state_snapshots", [{
            "owner_id": owner_id, "snapshot_json": snapshot,
        }], upsert=True)
