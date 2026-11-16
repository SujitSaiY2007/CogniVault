"""Accounts, sessions and durable storage.

Two interchangeable backends:
  * LocalBackend  - SQLite on local disk (development, single server).
  * SupabaseBackend - Postgres tables + private Storage bucket via the REST
    API, so accounts, uploads and progress survive restarts of free hosts.

Uploaded files are kept as the original bytes. After a restart the server
downloads and re-parses them (parsing is deterministic, so evidence ids are
identical), then restores the learner snapshot.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import time
from typing import Any, Optional
from urllib.parse import quote

import httpx

from .db import Database

SESSION_TTL = 30 * 86400
log = logging.getLogger("cognivault.storage")


class StorageError(RuntimeError):
    """Persistent storage failed. Message is safe to show users."""


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    salt = salt or secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return salt.hex() + ":" + dk.hex()


def check_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest = stored.split(":", 1)
        return hmac.compare_digest(hash_password(password, bytes.fromhex(salt_hex)).split(":", 1)[1], digest)
    except (ValueError, TypeError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class Backend:
    durable = False
    name = "local"

    # accounts
    def create_user(self, username: str, password_hash: str, learner_id: str) -> None: ...
    def get_user(self, username: str) -> Optional[dict[str, Any]]: ...
    def create_session(self, token: str, username: str) -> None: ...
    def resolve_session(self, token: str) -> Optional[tuple[str, str]]: ...
    def delete_session(self, token: str) -> None: ...
    # materials
    def save_file(self, owner_id: str, source: dict[str, Any], data: bytes, mime: str, evidence_rows: list[dict[str, Any]]) -> None: ...
    def list_files(self, owner_id: str) -> list[dict[str, Any]]: return []
    def load_file(self, owner_id: str, source_id: str) -> Optional[bytes]: return None
    def delete_file(self, owner_id: str, source_id: str) -> None: ...
    # progress
    def load_snapshot(self, owner_id: str) -> dict[str, Any]: return {}
    def save_snapshot(self, owner_id: str, snapshot: dict[str, Any]) -> None: ...


class LocalBackend(Backend):
    """Accounts in the app SQLite DB. Files live in the same DB, so nothing to save."""

    def __init__(self, db: Database):
        self.db = db

    def create_user(self, username, password_hash, learner_id):
        if self.get_user(username):
            raise StorageError("That username is already taken.")
        self.db._x("INSERT INTO auth_users VALUES(?,?,?,?)", (username, password_hash, learner_id, int(time.time())))

    def get_user(self, username):
        rows = self.db._q("SELECT * FROM auth_users WHERE username=?", (username,))
        return dict(rows[0]) if rows else None

    def create_session(self, token, username):
        now = int(time.time())
        self.db._x("DELETE FROM auth_sessions WHERE expires_at<?", (now,))
        self.db._x("INSERT INTO auth_sessions VALUES(?,?,?,?)", (token_hash(token), username, now + SESSION_TTL, now))

    def resolve_session(self, token):
        rows = self.db._q(
            "SELECT u.username, u.learner_id FROM auth_sessions s JOIN auth_users u ON u.username=s.username "
            "WHERE s.token_hash=? AND s.expires_at>?", (token_hash(token), int(time.time())))
        return (rows[0]["username"], rows[0]["learner_id"]) if rows else None

    def delete_session(self, token):
        self.db._x("DELETE FROM auth_sessions WHERE token_hash=?", (token_hash(token),))


def _eq(v: str) -> str:
    return f"eq.{v}"


def _iso(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


class SupabaseBackend(Backend):
    durable = True
    name = "supabase"
    BUCKET = "user-materials"

    def __init__(self, url: str, key: str):
        self.url = url.rstrip("/")
        self.headers = {"apikey": key, "Content-Type": "application/json"}
        if key.startswith("eyJ"):  # legacy JWT service-role key
            self.headers["Authorization"] = f"Bearer {key}"
        self.timeout = httpx.Timeout(20.0, connect=5.0)
        self.client = httpx.Client(timeout=self.timeout)

    def _req(self, method: str, path: str, *, params=None, json=None, headers=None, content=None, retries: int = 2):
        last: Optional[Exception] = None
        for attempt in range(retries + 1):
            try:
                r = self.client.request(method, f"{self.url}{path}", params=params, json=json,
                                        headers={**self.headers, **(headers or {})}, content=content)
            except httpx.HTTPError as exc:
                last = exc
                log.warning("Supabase %s %s failed (attempt %d): %s: %s", method, path.split("?")[0],
                            attempt + 1, type(exc).__name__, str(exc)[:200])
                time.sleep(0.4 * (attempt + 1))
                continue
            if r.status_code == 409:
                raise StorageError("That item already exists.")
            if r.status_code >= 500 and attempt < retries:
                time.sleep(0.4 * (attempt + 1))
                continue
            if r.status_code >= 400:
                log.warning("Supabase %s %s returned %s: %s", method, path.split("?")[0], r.status_code, r.text[:200])
                raise StorageError(f"Storage request failed ({r.status_code}).")
            if r.status_code == 204 or not r.content:
                return None
            ctype = r.headers.get("content-type", "")
            return r.json() if "json" in ctype else r.content
        raise StorageError("Storage is temporarily unreachable.") from last

    def diagnose(self) -> dict:
        """Probe Supabase and report what fails. Never returns secrets."""
        key = self.headers.get("apikey", "")
        info = {
            "url_host": self.url.split("//", 1)[-1].split("/", 1)[0],
            "url_has_scheme": self.url.startswith(("http://", "https://")),
            "url_has_whitespace": any(c.isspace() for c in self.url),
            "key_kind": "sb_secret" if key.startswith("sb_secret_") else "jwt" if key.startswith("eyJ")
                        else "sb_publishable" if key.startswith("sb_publishable_") else "unknown",
            "key_length": len(key),
            "key_has_whitespace": any(c.isspace() for c in key),
            "key_is_ascii": key.isascii(),
        }
        probes = {}
        for name, path in (("rest_users_table", "/rest/v1/cognivault_users?select=username&limit=1"),
                           ("rest_sources_table", "/rest/v1/user_sources?select=source_id&limit=1"),
                           ("storage_bucket", f"/storage/v1/bucket/{self.BUCKET}")):
            try:
                r = self.client.get(f"{self.url}{path}", headers=self.headers)
                probes[name] = {"ok": r.status_code < 400, "status": r.status_code,
                                "note": "" if r.status_code < 400 else r.text[:160]}
            except Exception as exc:  # report the exact failure class
                probes[name] = {"ok": False, "error": type(exc).__name__, "note": str(exc)[:160]}
        info["probes"] = probes
        info["all_ok"] = all(p["ok"] for p in probes.values())
        return info

    def _select(self, table, params):
        return self._req("GET", f"/rest/v1/{table}", params=params) or []

    def _insert(self, table, rows, upsert=False):
        prefer = "return=minimal" + (",resolution=merge-duplicates" if upsert else "")
        return self._req("POST", f"/rest/v1/{table}", json=rows, headers={"Prefer": prefer})

    def _delete(self, table, params):
        return self._req("DELETE", f"/rest/v1/{table}", params=params, headers={"Prefer": "return=minimal"})

    # accounts
    def create_user(self, username, password_hash, learner_id):
        try:
            self._insert("cognivault_users", [{"username": username, "password_hash": password_hash, "learner_id": learner_id}])
        except StorageError as exc:
            if "already exists" in str(exc):
                raise StorageError("That username is already taken.") from exc
            raise

    def get_user(self, username):
        rows = self._select("cognivault_users", {"select": "username,password_hash,learner_id", "username": _eq(username), "limit": "1"})
        return rows[0] if rows else None

    def create_session(self, token, username):
        now = time.time()
        try:
            self._delete("cognivault_sessions", {"expires_at": f"lt.{_iso(now)}"})
        except StorageError:
            pass
        self._insert("cognivault_sessions", [{"token_hash": token_hash(token), "username": username, "expires_at": _iso(now + SESSION_TTL)}])

    def resolve_session(self, token):
        rows = self._select("cognivault_sessions", {
            "select": "username,cognivault_users(learner_id)", "token_hash": _eq(token_hash(token)),
            "expires_at": f"gt.{_iso(time.time())}", "limit": "1"})
        if not rows:
            return None
        user = rows[0].get("cognivault_users")
        if isinstance(user, list):
            user = user[0] if user else None
        return (rows[0]["username"], user["learner_id"]) if user else None

    def delete_session(self, token):
        self._delete("cognivault_sessions", {"token_hash": _eq(token_hash(token))})

    # materials
    def save_file(self, owner_id, source, data, mime, evidence_rows):
        path = f"{owner_id}/{source['source_id']}/{source['filename']}"
        self._req("POST", f"/storage/v1/object/{self.BUCKET}/{quote(path, safe='/')}",
                  headers={"Content-Type": mime, "x-upsert": "true"}, content=data)
        try:
            self._insert("user_sources", [{**source, "owner_id": owner_id, "storage_path": path}], upsert=True)
            for i in range(0, len(evidence_rows), 200):
                self._insert("user_evidence", evidence_rows[i : i + 200], upsert=True)
        except StorageError:
            self._req("DELETE", f"/storage/v1/object/{self.BUCKET}", json={"prefixes": [path]})
            raise

    def list_files(self, owner_id):
        return self._select("user_sources", {
            "select": "source_id,filename,title,modality,sha256,storage_path,evidence_count,file_size_bytes,created_at",
            "owner_id": _eq(owner_id), "order": "created_at.asc"})

    def load_file(self, owner_id, source_id):
        rows = self._select("user_sources", {"select": "storage_path", "owner_id": _eq(owner_id), "source_id": _eq(source_id), "limit": "1"})
        if not rows:
            return None
        data = self._req("GET", f"/storage/v1/object/{self.BUCKET}/{quote(rows[0]['storage_path'], safe='/')}")
        return data if isinstance(data, bytes) else None

    def delete_file(self, owner_id, source_id):
        rows = self._select("user_sources", {"select": "storage_path", "owner_id": _eq(owner_id), "source_id": _eq(source_id), "limit": "1"})
        if rows:
            self._req("DELETE", f"/storage/v1/object/{self.BUCKET}", json={"prefixes": [rows[0]["storage_path"]]})
        self._delete("user_sources", {"owner_id": _eq(owner_id), "source_id": _eq(source_id)})

    # progress
    def load_snapshot(self, owner_id):
        rows = self._select("learner_state_snapshots", {"select": "snapshot_json", "owner_id": _eq(owner_id), "limit": "1"})
        return (rows[0].get("snapshot_json") or {}) if rows else {}

    def save_snapshot(self, owner_id, snapshot):
        self._insert("learner_state_snapshots", [{"owner_id": owner_id, "snapshot_json": snapshot}], upsert=True)
