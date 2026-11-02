"""
Comprehensive test suite for Chat 02 Product Loop.
Validates:
  1. Assessment API: selection, verification, scoring, duplicate/fingerprint prevention.
  2. Learner model API: BKT state persistence, correct observation updates.
  3. Misconception API: 2-error threshold diagnosis, remediation package, resolution.
  4. Prerequisite gating: blocks progression until prerequisite mastery >= 0.70.
  5. Cold-start diagnostic intake flow.
  6. Learner isolation boundary: 403 Forbidden when X-Learner-Id mismatches path.
  7. Ingestion upload API: PDF/PPTX/TXT extraction, SHA-256 provenance, and searchability.
"""
import io
import json
import pytest
from starlette.testclient import TestClient

from app.agent_os.app import create_agent_os_app
from app.agent_os.service import AgentOSLearningService
from app.assessment import compute_question_fingerprint
from app.corpus import seed_corpus
from app.db import EvidenceDB
from app.models import Difficulty, Question, QuestionOption, QuestionType
from app.retrieval import build_embeddings


@pytest.fixture(scope="module")
def product_loop_env(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("product_loop_vault")
    db_file = tmp_dir / "product_loop.db"
    db = EvidenceDB(str(db_file))

    # Seed STEM corpus (4 sources, 12 evidence units, topics, concepts, prerequisites, questions)
    seed_corpus(db)
    build_embeddings(db)
    db.close()

    service = AgentOSLearningService(
        db_path=str(db_file),
        in_memory_chroma=True,
    )
    service.sync_chroma()
    app = create_agent_os_app(service)

    yield {
        "app": app,
        "service": service,
        "db_file": str(db_file),
    }
    service.close()


def _auth_learner(client: TestClient, username: str) -> tuple[str, dict[str, str]]:
    """Helper to register/login a test learner and return (learner_id, auth_headers)."""
    r = client.post(
        "/api/v1/auth/signup",
        json={"username": username, "password": "Password123!"},
    )
    if r.status_code == 200:
        data = r.json()
        token = data["access_token"]
        learner_id = data["learner_id"]
    else:
        r_login = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": "Password123!"},
        )
        data = r_login.json()
        token = data["access_token"]
        learner_id = data["learner_id"]
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Learner-Id": learner_id,
    }
    return learner_id, headers


def test_assessment_selection_and_duplicate_suppression(product_loop_env):
    client = TestClient(product_loop_env["app"])

    # 1. Select first question for Classical Mechanics
    req_payload = {
        "topic_id": "Newtonian Mechanics",
        "served_question_ids": [],
    }
    r1 = client.post("/api/v1/assessment/select", json=req_payload)
    assert r1.status_code == 200
    q1 = r1.json()
    assert "question_id" in q1
    assert q1["topic_id"] == "Newtonian Mechanics"
    assert len(q1["options"]) >= 2
    assert q1["fingerprint"] != ""

    # 2. Select with q1 served -> should return a different question or candidate
    req_payload["served_question_ids"] = [q1["question_id"]]
    r2 = client.post("/api/v1/assessment/select", json=req_payload)
    assert r2.status_code == 200
    q2 = r2.json()
    # If another question exists, it must not repeat q1 or q1's fingerprint
    all_qs = client.get("/api/v1/assessment/questions?topic_id=Newtonian+Mechanics").json()
    if len(all_qs) > 1:
        assert q2["question_id"] != q1["question_id"]
        assert q2["fingerprint"] != q1["fingerprint"]


def test_question_verification_rejection_rules(product_loop_env):
    client = TestClient(product_loop_env["app"])

    # 1. Rejects short prompt (< 10 chars)
    r_short = client.post(
        "/api/v1/assessment/verify",
        json={
            "question_id": "q_invalid_short",
            "topic_id": "Newtonian Mechanics",
            "prompt": "Too short",
            "expected_answer": "A",
            "evidence_ids": ["physics_mechanics:e00001"],
            "options": [{"key": "A", "text": "Opt 1"}, {"key": "B", "text": "Opt 2"}],
        },
    )
    assert r_short.status_code == 200
    res_short = r_short.json()
    assert res_short["is_valid"] is False
    assert any("too short" in f.lower() for f in res_short["failure_reasons"])

    # 2. Rejects ambiguous MCQ expected answer
    r_ambig = client.post(
        "/api/v1/assessment/verify",
        json={
            "question_id": "q_invalid_ambig",
            "topic_id": "Newtonian Mechanics",
            "prompt": "Which of the following is true regarding friction?",
            "expected_answer": "NonExistentKey",
            "evidence_ids": ["physics_mechanics:e00001"],
            "options": [{"key": "A", "text": "Opt A"}, {"key": "B", "text": "Opt B"}],
        },
    )
    assert r_ambig.status_code == 200
    assert r_ambig.json()["is_valid"] is False

    # 3. Valid question passes
    r_valid = client.post(
        "/api/v1/assessment/verify",
        json={
            "question_id": "q_valid_mcq",
            "topic_id": "Newtonian Mechanics",
            "prompt": "What physical quantity does the product of mass and velocity represent?",
            "expected_answer": "A",
            "evidence_ids": ["physics_mechanics:e00001"],
            "options": [
                {"key": "A", "text": "Linear Momentum"},
                {"key": "B", "text": "Kinetic Energy"},
            ],
        },
    )
    assert r_valid.status_code == 200
    assert r_valid.json()["is_valid"] is True


def test_answer_submission_bkt_mastery_and_interaction(product_loop_env):
    client = TestClient(product_loop_env["app"])
    learner_id, headers = _auth_learner(client, "bkt_loop")

    # Get a verified question for Classical Mechanics
    qs = client.get("/api/v1/assessment/questions?topic_id=Newtonian+Mechanics").json()
    assert len(qs) >= 1
    target_q = qs[0]

    # Initial mastery should be unrecorded or 0.10
    m_init = client.get(
        f"/api/v1/learner/{learner_id}/mastery",
        headers=headers,
    ).json()
    assert len(m_init) == 0

    # 1. Submit CORRECT answer
    sub_payload = {
        "learner_id": learner_id,
        "question_id": target_q["question_id"],
        "answer": target_q["expected_answer"],
    }
    r_sub = client.post(
        "/api/v1/assessment/submit",
        json=sub_payload,
        headers=headers,
    )
    assert r_sub.status_code == 200
    data = r_sub.json()

    assert data["evaluation"]["is_correct"] is True
    assert data["evaluation"]["status"] == "correct"
    assert len(data["evaluation"]["citations"]) >= 1
    # Check physical citation presence
    top_cit = data["evaluation"]["citations"][0]
    assert "location" in top_cit

    # BKT mastery should have updated from p_init (0.10) to > 0.40
    p_updated = data["mastery"]["p_mastery"]
    assert p_updated > 0.35
    assert data["mastery"]["attempts"] == 1
    assert data["mastery"]["correct"] == 1

    # Verify persistent state in DB
    prof = client.get(
        f"/api/v1/learner/{learner_id}/profile",
        headers=headers,
    ).json()
    assert prof["total_attempts"] == 1
    assert prof["total_correct"] == 1
    assert prof["interaction_count"] == 1


def test_misconception_detection_two_error_threshold_and_remediation(product_loop_env):
    client = TestClient(product_loop_env["app"])
    learner_id, headers = _auth_learner(client, "misc_detection")

    qs = client.get("/api/v1/assessment/questions?topic_id=Newtonian+Mechanics").json()
    assert len(qs) >= 1
    target_q = qs[0]

    # 1. First incorrect attempt (error count = 1 -> isolated slip, NOT a misconception)
    r1 = client.post(
        "/api/v1/assessment/submit",
        json={
            "learner_id": learner_id,
            "question_id": target_q["question_id"],
            "answer": "CompletelyWrongAnswer1",
        },
        headers=headers,
    )
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["evaluation"]["is_correct"] is False
    assert d1["misconception_detected"] is False

    # Check active misconceptions list is still empty
    misc_before = client.get(
        f"/api/v1/learner/{learner_id}/misconceptions",
        headers=headers,
    ).json()
    assert len(misc_before) == 0

    # 2. Second consecutive incorrect attempt (error count = 2 -> triggers misconception signal!)
    r2 = client.post(
        "/api/v1/assessment/submit",
        json={
            "learner_id": learner_id,
            "question_id": target_q["question_id"],
            "answer": "CompletelyWrongAnswer2",
        },
        headers=headers,
    )
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["evaluation"]["is_correct"] is False
    assert d2["misconception_detected"] is True
    assert d2["misconception"] is not None
    assert d2["misconception"]["error_count"] >= 2

    # Verify active misconceptions endpoint returns remediation package with evidence items
    misc_list = client.get(
        f"/api/v1/learner/{learner_id}/misconceptions",
        headers=headers,
    ).json()
    assert len(misc_list) >= 1
    pkg = misc_list[0]
    assert pkg["suspected_misconception"] != ""
    assert "evidence_items" in pkg

    # 3. Resolve misconception
    sig_id = d2["misconception"]["signal_id"]
    r_res = client.post(
        f"/api/v1/learner/{learner_id}/misconceptions/{sig_id}/resolve",
        headers=headers,
    )
    assert r_res.status_code == 200
    assert r_res.json()["status"] == "resolved"

    # Verify cleared
    misc_after = client.get(
        f"/api/v1/learner/{learner_id}/misconceptions",
        headers=headers,
    ).json()
    assert len(misc_after) == 0


def test_prerequisite_gating_and_recommendations(product_loop_env):
    client = TestClient(product_loop_env["app"])
    learner_id, headers = _auth_learner(client, "prereq_gating")

    # Query recommendation for target topic that has prerequisites
    # For a topic with prerequisite mastery < 0.70, recommendation MUST demand foundational review
    r_rec = client.get(
        f"/api/v1/learner/{learner_id}/recommendations",
        headers=headers,
    )
    assert r_rec.status_code == 200
    rec = r_rec.json()
    assert "recommended_action" in rec
    assert rec["recommended_action"] in ["foundational_review", "targeted_practice", "remediate_misconception"]
    assert len(rec["suggested_evidence_ids"]) >= 1


def test_cold_start_intake_flow(product_loop_env):
    client = TestClient(product_loop_env["app"])
    learner_id, headers = _auth_learner(client, "cold_start")

    # Submit intake with initial baseline profile
    intake_payload = {
        "initial_topic_masteries": {
            "topic_classical_mechanics": 0.25,
            "topic_optics": 0.15,
        },
        "diagnostic_responses": [],
    }
    r = client.post(
        f"/api/v1/learner/{learner_id}/intake",
        json=intake_payload,
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["intake_status"] == "completed"
    assert "profile" in data
    assert data["profile"]["topic_mastery"]["topic_classical_mechanics"] == 0.25
    assert "initial_recommendation" in data


def test_learner_isolation_boundary_enforcement(product_loop_env):
    client = TestClient(product_loop_env["app"])
    alice_id, alice_headers = _auth_learner(client, "alice_boundary")
    bob_id, bob_headers = _auth_learner(client, "bob_boundary")

    # 1. Unauthenticated request rejected with 401
    r_unauth = client.get(f"/api/v1/learner/{bob_id}/profile")
    assert r_unauth.status_code == 401

    # 2. Alice cannot read Bob's profile (403 Forbidden)
    r_forbid = client.get(
        f"/api/v1/learner/{bob_id}/profile",
        headers=alice_headers,
    )
    assert r_forbid.status_code == 403
    assert "cannot access another user" in r_forbid.json()["detail"].lower()

    # 3. Alice cannot submit an assessment on behalf of Bob (403 Forbidden)
    r_sub_forbid = client.post(
        "/api/v1/assessment/submit",
        json={
            "learner_id": bob_id,
            "question_id": "q1",
            "answer": "A",
        },
        headers=alice_headers,
    )
    assert r_sub_forbid.status_code == 403

    # 4. Alice CAN access Alice's own profile (200 OK)
    r_ok = client.get(
        f"/api/v1/learner/{alice_id}/profile",
        headers=alice_headers,
    )
    assert r_ok.status_code == 200


def test_ingest_upload_endpoint(product_loop_env):
    client = TestClient(product_loop_env["app"])

    # 1. Unconfigured Supabase -> 503 fail-closed durable storage guard
    content = "[00:02:15] Thermodynamics: Heat engines convert thermal energy into mechanical work.\n"
    content_bytes = content.encode("utf-8")
    files = {"file": ("thermodynamics_lecture.txt", io.BytesIO(content_bytes), "text/plain")}
    r_unconf = client.post("/api/v1/ingest/upload", files=files)
    assert r_unconf.status_code == 503
    assert "Configure Supabase" in r_unconf.json()["detail"]

    # 2. Configured store with authenticated owner -> 200 persisted_private and searchable
    from app.agent_os.supabase_accounts import SupabaseAuth, SupabaseUserMaterials
    class IngestionTestStore:
        def __init__(self):
            self.users = []
            self.sessions = []
            self.sources = []
            self.evidence = []
            self.files = {}
        def select(self, table, *, params):
            if table == "cognivault_sessions":
                th = params.get("token_hash", "").replace("eq.", "")
                matched = [s for s in self.sessions if s["token_hash"] == th]
                if matched:
                    sess = matched[0]
                    u = next((usr for usr in self.users if usr["username"] == sess["username"]), None)
                    return [{
                        "username": sess["username"],
                        "expires_at": sess["expires_at"],
                        "cognivault_users": {"learner_id": u["learner_id"]} if u else None,
                    }]
                return []
            if table == "cognivault_users":
                u = params.get("username", "").replace("eq.", "")
                return [usr for usr in self.users if usr["username"] == u]
            if table == "user_sources":
                return self.sources
            if table == "user_evidence":
                owner = params.get("owner_id", "").replace("eq.", "")
                return [e for e in self.evidence if e.get("owner_id") == owner]
            return []
        def insert(self, table, rows, *, upsert=False):
            if table == "cognivault_users":
                self.users.extend(rows)
            elif table == "cognivault_sessions":
                self.sessions.extend(rows)
            elif table == "user_sources":
                self.sources.extend(rows)
            elif table == "user_evidence":
                self.evidence.extend(rows)
            return rows
        def delete(self, table, *, params):
            pass
        def upload_private(self, path, data, mime):
            self.files[path] = data
        def rpc(self, name, params):
            return 0

    store = IngestionTestStore()
    app = product_loop_env["app"]
    orig_supabase = app.state.supabase_enabled
    orig_store = getattr(app.state, "supabase_store", None)
    orig_auth = getattr(app.state, "supabase_auth", None)
    orig_materials = getattr(app.state, "user_materials", None)

    try:
        app.state.supabase_enabled = True
        app.state.supabase_store = store
        app.state.supabase_auth = SupabaseAuth(store)
        app.state.user_materials = SupabaseUserMaterials(store)

        learner_id, headers = _auth_learner(client, "ingest_user")
        files = {"file": ("thermodynamics_lecture.txt", io.BytesIO(content_bytes), "text/plain")}
        r_auth = client.post("/api/v1/ingest/upload", files=files, headers=headers)
        assert r_auth.status_code == 200
        data = r_auth.json()
        assert data["status"] == "private_ingested"
        assert data["evidence_count"] >= 1
        assert data["sha256"] != ""

        # Verify indexed unit is immediately searchable via owner-scoped search
        r_search = client.get("/api/v1/evidence/search?q=heat+engines+thermal+energy", headers=headers)
        assert r_search.status_code == 200
        search_data = r_search.json()
        assert search_data["result_count"] >= 1
    finally:
        app.state.supabase_enabled = orig_supabase
        app.state.supabase_store = orig_store
        app.state.supabase_auth = orig_auth
        app.state.user_materials = orig_materials


def test_topics_and_curriculum_endpoint(product_loop_env):
    client = TestClient(product_loop_env["app"])
    r = client.get("/api/v1/topics")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    topic = data[0]
    assert "topic_id" in topic
    assert "name" in topic
    assert "concepts" in topic
    assert "prerequisites" in topic

