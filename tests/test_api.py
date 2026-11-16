from app.corpus import build_all

from .conftest import NOTES, MemoryBackend, client_for, make_service, signup


def test_health_needs_no_auth_and_everything_else_does(seeded):
    c = client_for(seeded)
    assert c.get("/health").json()["status"] == "healthy"
    for path in ["/api/v1/topics", "/api/v1/sources", "/api/v1/flashcards", "/api/v1/course-map"]:
        assert c.get(path).status_code == 401
    assert c.post("/api/v1/tutor/query", json={"query": "x"}).status_code == 401


def test_signup_login_logout_and_validation(fresh):
    c = client_for(fresh)
    assert c.post("/api/v1/auth/signup", json={"username": "ab", "password": "longenough"}).status_code == 422
    assert c.post("/api/v1/auth/signup", json={"username": "Bad Name!", "password": "longenough"}).status_code == 400
    assert c.post("/api/v1/auth/signup", json={"username": "carol", "password": "short"}).status_code == 400
    h, lid = signup(c, "carol")
    assert c.post("/api/v1/auth/signup", json={"username": "carol", "password": "correct-horse-1"}).status_code == 409
    assert c.post("/api/v1/auth/login", json={"username": "carol", "password": "wrong-pass"}).status_code == 401
    tok = c.post("/api/v1/auth/login", json={"username": "CAROL", "password": "correct-horse-1"}).json()["access_token"]
    assert c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tok}"}).json()["learner_id"] == lid
    c.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {tok}"})
    assert c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_upload_then_tutor_quiz_and_report(fresh):
    c = client_for(fresh)
    h, lid = signup(c, "dana")
    r = c.post("/api/v1/ingest/upload", headers=h, files={"file": ("thermo.md", NOTES, "text/markdown")})
    assert r.status_code == 200, r.text
    up = r.json()
    assert {t["name"] for t in up["topics"]} == {"Thermodynamics", "Entropy"} and up["question_count"] >= 8
    assert c.post("/api/v1/ingest/upload", headers=h, files={"file": ("again.md", NOTES, "text/markdown")}).status_code == 409

    ans = c.post("/api/v1/tutor/query", headers=h, json={"query": "What is entropy?"}).json()
    assert ans["support_status"] == "supported" and ans["citations"][0]["source_id"] == up["source_id"]

    mine = [t["topic_id"] for t in c.get("/api/v1/topics", headers=h).json() if t["owner"] == "you"]
    quiz = c.post("/api/v1/quiz", headers=h, json={"topic_ids": mine, "count": 6}).json()
    assert len(quiz["questions"]) == 6 and all(q["expected_answer"] == "" for q in quiz["questions"])
    for q in quiz["questions"]:
        res = c.post(f"/api/v1/quiz/{quiz['session_id']}/answer", headers=h, json={"question_id": q["question_id"], "answer": "A"})
        assert res.status_code == 200
    assert c.post(f"/api/v1/quiz/{quiz['session_id']}/answer", headers=h, json={"question_id": quiz["questions"][0]["question_id"], "answer": "B"}).status_code == 409
    rep = c.post(f"/api/v1/quiz/{quiz['session_id']}/finish", headers=h).json()
    assert rep["total"] == 6 and rep["answered"] == 6 and {t["topic_name"] for t in rep["topics"]} <= {"Thermodynamics", "Entropy"}
    assert all(t["mastery_after"] is not None for t in rep["topics"]) and rep["next_recommendation"]["topic_id"]

    prof = c.get(f"/api/v1/learner/{lid}/profile", headers=h).json()
    assert prof["total_attempts"] == 6
    plan = c.post("/api/v1/study-plan", headers=h, json={"exam_date": "2030-01-01", "minutes_per_day": 60}).json()
    assert plan["days"] == 60
    cards = c.get("/api/v1/flashcards", headers=h).json()
    assert cards and c.post(f"/api/v1/flashcards/{cards[0]['card_id']}/review", headers=h, json={"grade": 4}).status_code == 200


def test_users_cannot_see_each_others_data(fresh):
    c = client_for(fresh)
    ha, la = signup(c, "erin")
    hb, lb = signup(c, "frank")
    src = c.post("/api/v1/ingest/upload", headers=ha, files={"file": ("thermo.md", NOTES, "text/markdown")}).json()["source_id"]
    assert len(c.get("/api/v1/sources", headers=hb).json()) == 4  # demo only
    assert c.get(f"/api/v1/sources/{src}", headers=hb).status_code == 404
    assert c.delete(f"/api/v1/sources/{src}", headers=hb).status_code == 404
    assert c.post("/api/v1/tutor/query", headers=hb, json={"query": "What is entropy?"}).json()["support_status"] == "unsupported"
    assert c.get(f"/api/v1/learner/{la}/profile", headers=hb).status_code == 403
    assert c.post("/api/v1/assessment/submit", headers=hb, json={"learner_id": la, "question_id": "x", "answer": "A"}).status_code == 403
    demo = next(s["source_id"] for s in c.get("/api/v1/sources", headers=hb).json())
    assert c.delete(f"/api/v1/sources/{demo}", headers=hb).status_code == 403


def test_select_never_leaks_answers_and_submit_returns_them(seeded):
    c = client_for(seeded)
    h, _ = signup(c, "gina")
    tid = c.get("/api/v1/topics", headers=h).json()[0]["topic_id"]
    q = c.post("/api/v1/assessment/select", headers=h, json={"topic_id": tid}).json()
    assert q["expected_answer"] == "" and q["solution"] == ""
    r = c.post("/api/v1/assessment/submit", headers=h, json={"question_id": q["question_id"], "answer": "A"}).json()
    assert r["evaluation"]["expected_answer"] and "p_before" in r


def test_progress_and_uploads_survive_a_restart():
    backend = MemoryBackend()
    svc1 = make_service(backend=backend)
    c1 = client_for(svc1)
    h, lid = signup(c1, "hana")
    c1.post("/api/v1/ingest/upload", headers=h, files={"file": ("waves.pptx", build_all()["waves_optics.pptx"], "application/octet-stream")})
    tid = next(t["topic_id"] for t in c1.get("/api/v1/topics", headers=h).json() if t["owner"] == "you")
    q = c1.post("/api/v1/assessment/select", headers=h, json={"topic_id": tid}).json()
    c1.post("/api/v1/assessment/submit", headers=h, json={"question_id": q["question_id"], "answer": "A"})
    before = c1.get(f"/api/v1/learner/{lid}/profile", headers=h).json()

    svc2 = make_service(backend=backend)  # new process, empty local DB
    c2 = client_for(svc2)
    after = c2.get(f"/api/v1/learner/{lid}/profile", headers=h).json()
    assert after["total_attempts"] == before["total_attempts"] == 1
    assert after["topic_mastery"] == before["topic_mastery"]
    assert any(s["owner"] == "you" for s in c2.get("/api/v1/sources", headers=h).json())
    assert c2.post("/api/v1/tutor/query", headers=h, json={"query": "What is refraction?"}).json()["citations"]


def test_storage_outage_rolls_back_upload():
    backend = MemoryBackend()
    svc = make_service(backend=backend)
    c = client_for(svc)
    h, _ = signup(c, "ivan")
    backend.fail_saves = True
    r = c.post("/api/v1/ingest/upload", headers=h, files={"file": ("thermo.md", NOTES, "text/markdown")})
    assert r.status_code == 503
    assert not any(s["owner"] == "you" for s in c.get("/api/v1/sources", headers=h).json())


def test_unsupported_and_oversized_uploads_are_rejected(fresh):
    c = client_for(fresh)
    h, _ = signup(c, "jade")
    assert c.post("/api/v1/ingest/upload", headers=h, files={"file": ("x.exe", b"MZ", "application/octet-stream")}).status_code == 422
    big = b"a" * (25 * 1024 * 1024 + 1)
    assert c.post("/api/v1/ingest/upload", headers=h, files={"file": ("big.txt", big, "text/plain")}).status_code == 413


def test_storage_diagnostics_local(fresh):
    r = client_for(fresh).get("/api/v1/diagnostics/storage")
    assert r.status_code == 200
    assert r.json()["all_ok"] is True


def test_supabase_diagnose_reports_connection_failure():
    from app.persistence import SupabaseBackend
    b = SupabaseBackend("http://127.0.0.1:9", "sb_secret_testkey")
    d = b.diagnose()
    assert d["key_kind"] == "sb_secret" and d["all_ok"] is False
    assert all(p["ok"] is False and p["error"] for p in d["probes"].values())
    assert "sb_secret_testkey" not in str(d)
