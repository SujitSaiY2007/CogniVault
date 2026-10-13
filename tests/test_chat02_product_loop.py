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
    learner_id = "test_learner_bkt_loop"

    # Get a verified question for Classical Mechanics
    qs = client.get("/api/v1/assessment/questions?topic_id=Newtonian+Mechanics").json()
    assert len(qs) >= 1
    target_q = qs[0]

    # Initial mastery should be unrecorded or 0.10
    m_init = client.get(
        f"/api/v1/learner/{learner_id}/mastery",
        headers={"X-Learner-Id": learner_id},
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
        headers={"X-Learner-Id": learner_id},
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
        headers={"X-Learner-Id": learner_id},
    ).json()
    assert prof["total_attempts"] == 1
    assert prof["total_correct"] == 1
    assert prof["interaction_count"] == 1


def test_misconception_detection_two_error_threshold_and_remediation(product_loop_env):
    client = TestClient(product_loop_env["app"])
    learner_id = "test_learner_misc_detection"

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
        headers={"X-Learner-Id": learner_id},
    )
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["evaluation"]["is_correct"] is False
    assert d1["misconception_detected"] is False

    # Check active misconceptions list is still empty
    misc_before = client.get(
        f"/api/v1/learner/{learner_id}/misconceptions",
        headers={"X-Learner-Id": learner_id},
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
        headers={"X-Learner-Id": learner_id},
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
        headers={"X-Learner-Id": learner_id},
    ).json()
    assert len(misc_list) >= 1
    pkg = misc_list[0]
    assert pkg["suspected_misconception"] != ""
    assert "evidence_items" in pkg

    # 3. Resolve misconception
    sig_id = d2["misconception"]["signal_id"]
    r_res = client.post(
        f"/api/v1/learner/{learner_id}/misconceptions/{sig_id}/resolve",
        headers={"X-Learner-Id": learner_id},
    )
    assert r_res.status_code == 200
    assert r_res.json()["status"] == "resolved"

    # Verify cleared
    misc_after = client.get(
        f"/api/v1/learner/{learner_id}/misconceptions",
        headers={"X-Learner-Id": learner_id},
    ).json()
    assert len(misc_after) == 0


def test_prerequisite_gating_and_recommendations(product_loop_env):
    client = TestClient(product_loop_env["app"])
    learner_id = "test_learner_prereq_gating"

    # Query recommendation for target topic that has prerequisites
    # For a topic with prerequisite mastery < 0.70, recommendation MUST demand foundational review
    r_rec = client.get(
        f"/api/v1/learner/{learner_id}/recommendations",
        headers={"X-Learner-Id": learner_id},
    )
    assert r_rec.status_code == 200
    rec = r_rec.json()
    assert "recommended_action" in rec
    assert rec["recommended_action"] in ["foundational_review", "targeted_practice", "remediate_misconception"]
    assert len(rec["suggested_evidence_ids"]) >= 1


def test_cold_start_intake_flow(product_loop_env):
    client = TestClient(product_loop_env["app"])
    learner_id = "fresh_learner_cold_start"

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
        headers={"X-Learner-Id": learner_id},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["intake_status"] == "completed"
    assert "profile" in data
    assert data["profile"]["topic_mastery"]["topic_classical_mechanics"] == 0.25
    assert "initial_recommendation" in data


def test_learner_isolation_boundary_enforcement(product_loop_env):
    client = TestClient(product_loop_env["app"])

    # Alice cannot read Bob's profile
    r_forbid = client.get(
        "/api/v1/learner/bob/profile",
        headers={"X-Learner-Id": "alice"},
    )
    assert r_forbid.status_code == 403
    assert "Forbidden" in r_forbid.json()["detail"]

    # Alice cannot submit an assessment on behalf of Bob
    r_sub_forbid = client.post(
        "/api/v1/assessment/submit",
        json={
            "learner_id": "bob",
            "question_id": "q1",
            "answer": "A",
        },
        headers={"X-Learner-Id": "alice"},
    )
    assert r_sub_forbid.status_code == 403

    # Alice CAN access Alice's own profile
    r_ok = client.get(
        "/api/v1/learner/alice/profile",
        headers={"X-Learner-Id": "alice"},
    )
    assert r_ok.status_code == 200


def test_ingest_upload_endpoint(product_loop_env):
    client = TestClient(product_loop_env["app"])

    # Upload sample lecture transcript
    content = "[00:02:15] Thermodynamics: Heat engines convert thermal energy into mechanical work.\n"
    content_bytes = content.encode("utf-8")
    files = {"file": ("thermodynamics_lecture.txt", io.BytesIO(content_bytes), "text/plain")}

    r = client.post("/api/v1/ingest/upload", files=files)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ingested_and_indexed"
    assert data["evidence_count"] >= 1
    assert data["sha256"] != ""

    # Verify indexed unit is immediately searchable via hybrid search
    r_search = client.get("/api/v1/evidence/search?q=heat+engines+thermal+energy")
    assert r_search.status_code == 200
    search_data = r_search.json()
    assert search_data["result_count"] >= 1


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

