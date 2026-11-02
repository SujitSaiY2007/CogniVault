"""
End-to-end verification of Supabase persistence, authentication, per-account isolation,
and security quotas for CogniVault.
"""
from __future__ import annotations

import io
import os
import re
import time
import json
import hashlib
import tempfile
from pathlib import Path
from typing import Any, Optional

import pytest
import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.testclient import TestClient

from app.agent_os.app import create_agent_os_app
from app.agent_os.service import AgentOSLearningService
from app.agent_os.supabase_store import SupabaseStore
from app.agent_os.supabase_accounts import SupabaseAuth, SupabaseUserMaterials
from app.db import EvidenceDB
from app.corpus import seed_corpus


def create_supabase_mock_app():
    """Mock Supabase server implementing PostgREST tables, RPCs, and Storage."""
    app = FastAPI(title="Supabase Mock")

    users: dict[str, dict] = {}  # username -> dict
    sessions: dict[str, dict] = {}  # token_hash -> dict
    sources: dict[str, dict] = {}  # source_id -> dict
    evidence: list[dict] = []  # list of evidence records
    snapshots: dict[str, dict] = {}  # owner_id -> dict
    storage: dict[str, bytes] = {}  # safe_path -> bytes

    def _verify_auth(request: Request):
        auth = request.headers.get("authorization", "")
        if not auth.startswith("Bearer test-service-key"):
            raise HTTPException(status_code=401, detail="Invalid API key")

    # REST: cognivault_users
    @app.post("/rest/v1/cognivault_users")
    async def post_user(request: Request):
        _verify_auth(request)
        body = await request.json()
        for u in body:
            username = u["username"]
            if username in users:
                raise HTTPException(status_code=409, detail="Duplicate key")
            users[username] = dict(u)
        return JSONResponse(content=body, status_code=201)

    @app.get("/rest/v1/cognivault_users")
    async def get_users(request: Request, username: Optional[str] = None):
        _verify_auth(request)
        res = list(users.values())
        if username and username.startswith("eq."):
            uname = username[3:]
            res = [u for u in res if u["username"] == uname]
        return JSONResponse(content=res)

    # REST: cognivault_sessions
    @app.post("/rest/v1/cognivault_sessions")
    async def post_session(request: Request):
        _verify_auth(request)
        body = await request.json()
        for s in body:
            sessions[s["token_hash"]] = dict(s)
        return JSONResponse(content=body, status_code=201)

    @app.get("/rest/v1/cognivault_sessions")
    async def get_sessions(request: Request, token_hash: Optional[str] = None, expires_at: Optional[str] = None):
        _verify_auth(request)
        res = []
        for s in sessions.values():
            if token_hash and token_hash.startswith("eq."):
                if s["token_hash"] != token_hash[3:]:
                    continue
            if expires_at and expires_at.startswith("gt."):
                if s["expires_at"] <= expires_at[3:]:
                    continue
            user_data = users.get(s["username"])
            item = dict(s)
            item["cognivault_users"] = {"learner_id": user_data["learner_id"]} if user_data else None
            res.append(item)
        return JSONResponse(content=res)

    @app.delete("/rest/v1/cognivault_sessions")
    async def delete_sessions(request: Request, expires_at: Optional[str] = None, token_hash: Optional[str] = None):
        _verify_auth(request)
        to_del = []
        for th, s in sessions.items():
            if expires_at and expires_at.startswith("lt."):
                if s["expires_at"] < expires_at[3:]:
                    to_del.append(th)
            if token_hash and token_hash.startswith("eq."):
                if th == token_hash[3:]:
                    to_del.append(th)
        for th in to_del:
            sessions.pop(th, None)
        return Response(status_code=204)

    # REST: user_sources
    @app.get("/rest/v1/user_sources")
    async def get_sources(request: Request, owner_id: Optional[str] = None, source_id: Optional[str] = None):
        _verify_auth(request)
        res = list(sources.values())
        if owner_id and owner_id.startswith("eq."):
            res = [s for s in res if s["owner_id"] == owner_id[3:]]
        if source_id and source_id.startswith("eq."):
            res = [s for s in res if s["source_id"] == source_id[3:]]
        return JSONResponse(content=res)

    @app.post("/rest/v1/user_sources")
    async def post_source(request: Request):
        _verify_auth(request)
        body = await request.json()
        for s in body:
            sid = s["source_id"]
            if sid in sources:
                raise HTTPException(status_code=409, detail="Duplicate source")
            sources[sid] = dict(s)
        return JSONResponse(content=body, status_code=201)

    @app.delete("/rest/v1/user_sources")
    async def delete_source(request: Request, owner_id: Optional[str] = None, source_id: Optional[str] = None):
        _verify_auth(request)
        oid = owner_id[3:] if owner_id and owner_id.startswith("eq.") else None
        sid = source_id[3:] if source_id and source_id.startswith("eq.") else None
        to_del = []
        for k, v in sources.items():
            if oid and v["owner_id"] != oid:
                continue
            if sid and v["source_id"] != sid:
                continue
            to_del.append(k)
        for k in to_del:
            sources.pop(k, None)
            evidence[:] = [e for e in evidence if e["source_id"] != k]
        return Response(status_code=204)

    # REST: user_evidence
    @app.get("/rest/v1/user_evidence")
    async def get_evidence(request: Request, owner_id: Optional[str] = None, source_id: Optional[str] = None, limit: Optional[str] = None, offset: Optional[str] = None):
        _verify_auth(request)
        res = evidence
        if owner_id and owner_id.startswith("eq."):
            res = [e for e in res if e["owner_id"] == owner_id[3:]]
        if source_id and source_id.startswith("eq."):
            res = [e for e in res if e["source_id"] == source_id[3:]]
        off = int(offset) if offset else 0
        lim = int(limit) if limit else len(res)
        return JSONResponse(content=res[off:off+lim])

    @app.post("/rest/v1/user_evidence")
    async def post_evidence(request: Request):
        _verify_auth(request)
        body = await request.json()
        for e in body:
            evidence.append(dict(e))
        return JSONResponse(content=body, status_code=201)

    # REST: learner_state_snapshots
    @app.get("/rest/v1/learner_state_snapshots")
    async def get_snapshots(request: Request, owner_id: Optional[str] = None):
        _verify_auth(request)
        res = list(snapshots.values())
        if owner_id and owner_id.startswith("eq."):
            res = [s for s in res if s["owner_id"] == owner_id[3:]]
        return JSONResponse(content=res)

    @app.post("/rest/v1/learner_state_snapshots")
    async def post_snapshot(request: Request):
        _verify_auth(request)
        body = await request.json()
        for s in body:
            snapshots[s["owner_id"]] = dict(s)
        return JSONResponse(content=body, status_code=201)

    # RPC: cognivault_global_storage_usage_bytes
    @app.post("/rest/v1/rpc/cognivault_global_storage_usage_bytes")
    async def rpc_storage_usage(request: Request):
        _verify_auth(request)
        total = sum(int(s.get("file_size_bytes", 0)) for s in sources.values())
        return JSONResponse(content=total)

    # RPC: cognivault_global_evidence_count
    @app.post("/rest/v1/rpc/cognivault_global_evidence_count")
    async def rpc_evidence_count(request: Request):
        _verify_auth(request)
        return JSONResponse(content=len(evidence))

    # Storage: user-materials
    @app.post("/storage/v1/object/user-materials/{path:path}")
    async def storage_upload(path: str, request: Request):
        _verify_auth(request)
        data = await request.body()
        storage[path] = data
        return JSONResponse(content={"Key": f"user-materials/{path}"})

    @app.get("/storage/v1/object/user-materials/{path:path}")
    async def storage_download(path: str, request: Request):
        _verify_auth(request)
        if path not in storage:
            raise HTTPException(status_code=404, detail="Object not found")
        return Response(content=storage[path], media_type="application/octet-stream")

    @app.delete("/storage/v1/object/user-materials")
    async def storage_delete(request: Request):
        _verify_auth(request)
        body = await request.json()
        for prefix in body.get("prefixes", []):
            keys = [k for k in storage if k.startswith(prefix)]
            for k in keys:
                storage.pop(k, None)
        return JSONResponse(content=[{"name": p} for p in body.get("prefixes", [])])

    return app, {
        "users": users,
        "sessions": sessions,
        "sources": sources,
        "evidence": evidence,
        "snapshots": snapshots,
        "storage": storage,
    }


@pytest.fixture(scope="module")
def supabase_test_env(tmp_path_factory):
    mock_app, state = create_supabase_mock_app()
    base_url = "http://supabase.test"
    mock_http_client = TestClient(mock_app, base_url=base_url)

    orig_httpx_request = httpx.request

    def patched_request(method, url, **kwargs):
        if str(url).startswith(base_url):
            # TestClient requires path or url relative to base_url
            path = str(url)[len(base_url):]
            if not path.startswith("/"):
                path = "/" + path
            return mock_http_client.request(method, path, **kwargs)
        return orig_httpx_request(method, url, **kwargs)

    httpx.request = patched_request

    os.environ["SUPABASE_URL"] = base_url
    os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "test-service-key"

    tmp_dir = tmp_path_factory.mktemp("supabase_vault")
    db_file = tmp_dir / "test.db"
    db = EvidenceDB(str(db_file))
    seed_corpus(db)
    db.close()

    service = AgentOSLearningService(db_path=str(db_file), in_memory_chroma=True)
    app = create_agent_os_app(service)
    client = TestClient(app)

    yield {
        "app": app,
        "client": client,
        "service": service,
        "db_file": str(db_file),
        "state": state,
    }

    httpx.request = orig_httpx_request
    mock_http_client.close()
    os.environ.pop("SUPABASE_URL", None)
    os.environ.pop("SUPABASE_SERVICE_ROLE_KEY", None)


# -----------------------------------------------------------------------------
# PHASE 3: AUTHENTICATION TESTS
# -----------------------------------------------------------------------------

def test_phase3_auth_full_lifecycle(supabase_test_env):
    client = supabase_test_env["client"]

    # 1. Registration
    reg_resp = client.post("/api/v1/auth/signup", json={"username": "user_alpha", "password": "Password123!"})
    assert reg_resp.status_code == 200
    data = reg_resp.json()
    assert data["username"] == "user_alpha"
    assert data["learner_id"] == "user_user_alpha"
    assert "access_token" in data
    assert "password_hash" not in data
    assert "password" not in data

    token_a = data["access_token"]

    # 2. Duplicate registration rejected
    dup_resp = client.post("/api/v1/auth/signup", json={"username": "user_alpha", "password": "AnotherPassword123!"})
    assert dup_resp.status_code == 409

    # 3. Password validation
    short_pw = client.post("/api/v1/auth/signup", json={"username": "new_user", "password": "123"})
    assert short_pw.status_code in (400, 422)

    invalid_username = client.post("/api/v1/auth/signup", json={"username": "a!@#$", "password": "Password123!"})
    assert invalid_username.status_code in (400, 422)

    # 4. Successful login
    login_resp = client.post("/api/v1/auth/login", json={"username": "user_alpha", "password": "Password123!"})
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "access_token" in login_data
    assert "password_hash" not in login_data
    token_a2 = login_data["access_token"]

    # 5. Invalid password rejection
    bad_login = client.post("/api/v1/auth/login", json={"username": "user_alpha", "password": "WrongPassword!"})
    assert bad_login.status_code == 401

    # 6. Non-existent username login rejection
    no_user = client.post("/api/v1/auth/login", json={"username": "non_existent_user", "password": "Password123!"})
    assert no_user.status_code == 401

    # 7. Session persistence & resolution via /api/v1/auth/me
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a2}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "user_alpha"
    assert me_resp.json()["learner_id"] == "user_user_alpha"
    assert "password_hash" not in me_resp.json()

    # 8. Protected endpoint access without token -> 401
    no_auth = client.get("/api/v1/auth/me")
    assert no_auth.status_code == 401

    # 9. Logout and session revocation
    logout_resp = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token_a2}"})
    assert logout_resp.status_code == 200
    assert logout_resp.json()["status"] == "signed_out"

    # Revoked token cannot access protected endpoints
    after_logout = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_a2}"})
    assert after_logout.status_code == 401


# -----------------------------------------------------------------------------
# PHASE 4: SUPABASE PERSISTENCE & PER-ACCOUNT ISOLATION
# -----------------------------------------------------------------------------

def test_phase4_per_account_isolation_and_persistence(supabase_test_env):
    client = supabase_test_env["client"]
    state = supabase_test_env["state"]

    # Register User A and User B
    client.post("/api/v1/auth/signup", json={"username": "tenant_a", "password": "Password123!"})
    login_a = client.post("/api/v1/auth/login", json={"username": "tenant_a", "password": "Password123!"}).json()
    token_a = login_a["access_token"]
    learner_a = login_a["learner_id"]
    headers_a = {"Authorization": f"Bearer {token_a}", "X-Learner-Id": learner_a}

    client.post("/api/v1/auth/signup", json={"username": "tenant_b", "password": "Password123!"})
    login_b = client.post("/api/v1/auth/login", json={"username": "tenant_b", "password": "Password123!"}).json()
    token_b = login_b["access_token"]
    learner_b = login_b["learner_id"]
    headers_b = {"Authorization": f"Bearer {token_b}", "X-Learner-Id": learner_b}

    # Upload document A for User A
    doc_a = b"[00:01:00] Quantum Physics: Wave-particle duality and Schrodinger wave function dynamics.\n"
    up_a = client.post(
        "/api/v1/ingest/upload",
        files={"file": ("quantum_notes.txt", io.BytesIO(doc_a), "text/plain")},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert up_a.status_code == 200
    data_a = up_a.json()
    src_id_a = data_a["source_id"]
    assert data_a["status"] == "private_ingested"

    # Upload document B for User B
    doc_b = b"[00:02:00] Organic Chemistry: Benzene resonance hybridization and aromatic electrophilic substitution.\n"
    up_b = client.post(
        "/api/v1/ingest/upload",
        files={"file": ("chemistry_lecture.txt", io.BytesIO(doc_b), "text/plain")},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert up_b.status_code == 200
    data_b = up_b.json()
    src_id_b = data_b["source_id"]

    # 1. Confirm each user only sees their own uploaded sources in list_sources
    sources_a = client.get("/api/v1/sources", headers={"Authorization": f"Bearer {token_a}"}).json()
    sources_b = client.get("/api/v1/sources", headers={"Authorization": f"Bearer {token_b}"}).json()
    src_ids_a = {s["source_id"] for s in sources_a}
    src_ids_b = {s["source_id"] for s in sources_b}

    assert src_id_a in src_ids_a
    assert src_id_b not in src_ids_a, "User A must not see User B's source in list_sources"

    assert src_id_b in src_ids_b
    assert src_id_a not in src_ids_b, "User B must not see User A's source in list_sources"

    # 2. Confirm evidence search is owner-scoped
    search_a = client.get("/api/v1/evidence/search?q=Schrodinger", headers={"Authorization": f"Bearer {token_a}"}).json()
    search_b = client.get("/api/v1/evidence/search?q=Schrodinger", headers={"Authorization": f"Bearer {token_b}"}).json()

    private_found_a = any(r.get("private") for r in search_a["results"])
    private_found_b = any(r.get("private") for r in search_b["results"])
    assert private_found_a is True, "User A should retrieve their private quantum evidence"
    assert private_found_b is False, "User B must NOT retrieve User A's private quantum evidence"

    # 3. Confirm User A cannot access User B's source ID directly
    get_b_by_a = client.get(f"/api/v1/sources/{src_id_b}", headers={"Authorization": f"Bearer {token_a}"})
    assert get_b_by_a.status_code == 404, "User A accessing User B's source must return 404"

    # 4. Confirm User A cannot get evidence for User B's source
    ev_b_by_a = client.get(f"/api/v1/sources/{src_id_b}/evidence", headers={"Authorization": f"Bearer {token_a}"})
    assert ev_b_by_a.status_code == 200
    assert len(ev_b_by_a.json()) == 0, "User A must get 0 evidence units for User B's source"

    # 5. Confirm User A cannot delete User B's source
    del_b_by_a = client.delete(f"/api/v1/sources/{src_id_b}", headers={"Authorization": f"Bearer {token_a}"})
    assert del_b_by_a.status_code == 404
    get_b_by_b = client.get(f"/api/v1/sources/{src_id_b}", headers={"Authorization": f"Bearer {token_b}"})
    assert get_b_by_b.status_code == 200

    # 6. Confirm tutor retrieval does not use another account's private material
    tutor_a = client.post(
        "/api/v1/tutor/query",
        json={"query": "Explain benzene resonance hybridization in detail"},
        headers={"Authorization": f"Bearer {token_a}"},
    ).json()
    citations_a = tutor_a.get("citations", [])
    for c in citations_a:
        assert c["source_id"] != src_id_b, "Tutor query for User A must not cite User B's source"

    # 7. Confirm unsupported tutor questions result in fail-closed abstention
    tutor_unsupported = client.post(
        "/api/v1/tutor/query",
        json={"query": "What were the primary agricultural practices of the Roman Republic?"},
        headers={"Authorization": f"Bearer {token_a}"},
    ).json()
    assert tutor_unsupported["support_status"] == "unsupported"
    assert tutor_unsupported["is_grounded"] is False
    assert len(tutor_unsupported["citations"]) == 0

    # 8. Confirm learner progress snapshot persistence across backend restart
    intake_resp = client.post(
        f"/api/v1/learner/{learner_a}/intake",
        json={
            "initial_topic_masteries": {"Classical Mechanics": 0.75},
            "diagnostic_responses": [{"topic_id": "Classical Mechanics", "is_correct": True}],
        },
        headers=headers_a,
    )
    assert intake_resp.status_code == 200
    assert learner_a in state["snapshots"], "Learner state snapshot must be persisted in Supabase"

    # Simulate backend restart: fresh SQLite DB and fresh app
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as fresh_db:
        fresh_db_path = fresh_db.name

    fresh_service = AgentOSLearningService(db_path=fresh_db_path, in_memory_chroma=True)
    fresh_app = create_agent_os_app(fresh_service)
    fresh_client = TestClient(fresh_app)

    profile_after = fresh_client.get(f"/api/v1/learner/{learner_a}/profile", headers=headers_a)
    assert profile_after.status_code == 200
    mastery_records = profile_after.json().get("topic_mastery", {})
    assert "Classical Mechanics" in mastery_records, "Learner mastery must survive backend restart via Supabase hydration"
    assert mastery_records["Classical Mechanics"] >= 0.7

    # 9. Confirm private sources remain available after restart
    sources_after = fresh_client.get("/api/v1/sources", headers={"Authorization": f"Bearer {token_a}"}).json()
    assert any(s["source_id"] == src_id_a for s in sources_after), "Private source must persist across backend restart"

    # 10. Confirm source deletion removes private object and associated records
    del_res = fresh_client.delete(f"/api/v1/sources/{src_id_a}", headers={"Authorization": f"Bearer {token_a}"})
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

    assert src_id_a not in state["sources"], "Source record must be deleted from Supabase"
    assert not any(e["source_id"] == src_id_a for e in state["evidence"]), "Evidence records must be cascade deleted"
    assert not any(src_id_a in k for k in state["storage"]), "Storage object blob must be deleted"

    fresh_service.close()
    Path(fresh_db_path).unlink(missing_ok=True)


# -----------------------------------------------------------------------------
# PHASE 6: SECURITY AND RESOURCE LIMITS
# -----------------------------------------------------------------------------

def test_phase6_security_and_resource_limits(supabase_test_env):
    client = supabase_test_env["client"]
    state = supabase_test_env["state"]

    client.post("/api/v1/auth/signup", json={"username": "sec_user", "password": "Password123!"})
    login = client.post("/api/v1/auth/login", json={"username": "sec_user", "password": "Password123!"}).json()
    token = login["access_token"]
    learner_id = login["learner_id"]
    headers = {"Authorization": f"Bearer {token}", "X-Learner-Id": learner_id}

    # 1. Unauthorized requests (no token) -> 401
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get(f"/api/v1/learner/{learner_id}/profile").status_code == 401
    assert client.post("/api/v1/ingest/upload", files={"file": ("f.txt", b"abc", "text/plain")}).status_code == 401

    # 2. Invalid session token -> 401
    bad_token = {"Authorization": "Bearer invalid_nonexistent_token_12345", "X-Learner-Id": learner_id}
    assert client.get("/api/v1/auth/me", headers=bad_token).status_code == 401
    assert client.get(f"/api/v1/learner/{learner_id}/profile", headers=bad_token).status_code == 401

    # 3. Cross-account access attempt -> 403
    mismatch_headers = {"Authorization": f"Bearer {token}", "X-Learner-Id": "user_another_person"}
    assert client.get("/api/v1/learner/user_another_person/profile", headers=headers).status_code == 403
    assert client.get(f"/api/v1/learner/{learner_id}/profile", headers=mismatch_headers).status_code == 403

    # 4. Unsupported file extension rejection -> 400
    bad_exts = [("script.py", b"print('bad')", "text/x-python"), ("malware.exe", b"MZ", "application/x-msdownload")]
    for fname, data, mime in bad_exts:
        r = client.post("/api/v1/ingest/upload", files={"file": (fname, io.BytesIO(data), mime)}, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 400
        assert "Unsupported format" in r.json()["detail"]

    # 5. Oversized file rejection (>25 MB) -> 413
    import sys
    app_module = sys.modules["app.agent_os.app"]
    orig_max = app_module.MAX_UPLOAD_SIZE
    try:
        app_module.MAX_UPLOAD_SIZE = 500
        oversized = b"X" * 1000
        r_over = client.post(
            "/api/v1/ingest/upload",
            files={"file": ("oversized.txt", io.BytesIO(oversized), "text/plain")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r_over.status_code == 413
        assert "Upload exceeds the 25 MB per-file" in r_over.json()["detail"]
    finally:
        app_module.MAX_UPLOAD_SIZE = orig_max

    # 6. Duplicate upload handling (same SHA-256) -> 409
    unique_content = b"[00:00:10] Physics Lecture: Friction coefficients in mechanical systems.\n"
    r1 = client.post("/api/v1/ingest/upload", files={"file": ("friction.txt", io.BytesIO(unique_content), "text/plain")}, headers={"Authorization": f"Bearer {token}"})
    assert r1.status_code == 200
    r2 = client.post("/api/v1/ingest/upload", files={"file": ("friction_copy.txt", io.BytesIO(unique_content), "text/plain")}, headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 409
    assert "already uploaded to your account" in r2.json()["detail"]

    # 7. Account 10-file quota check
    uploaded_sids = [r1.json()["source_id"]]
    for i in range(2, 11):
        content = f"[00:00:{i:02d}] Physics Lecture Part {i}: Dynamic equilibrium content.\n".encode()
        res = client.post("/api/v1/ingest/upload", files={"file": (f"note_{i}.txt", io.BytesIO(content), "text/plain")}, headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        uploaded_sids.append(res.json()["source_id"])

    # 11th file rejected with 413
    content_11 = b"[00:00:11] Too many files lecture note.\n"
    r_11 = client.post("/api/v1/ingest/upload", files={"file": ("note_11.txt", io.BytesIO(content_11), "text/plain")}, headers={"Authorization": f"Bearer {token}"})
    assert r_11.status_code == 413
    assert "Account upload limit reached (10 files)" in r_11.json()["detail"]

    # Clean up
    for sid in uploaded_sids:
        client.delete(f"/api/v1/sources/{sid}", headers={"Authorization": f"Bearer {token}"})
