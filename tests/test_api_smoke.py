"""
API Smoke Test Suite for CogniVault Agno AgentOS and Local Ollama Integration.
Verifies all endpoints, contracts, and graceful offline fallback behavior.
"""
import pytest
from starlette.testclient import TestClient

from app.agent_os.app import create_agent_os_app
from app.agent_os.service import AgentOSTutorService
from app.ollama_provider import is_ollama_available, get_available_ollama_models, DEFAULT_OLLAMA_HOST
from app.corpus import seed_corpus
from app.db import EvidenceDB
from app.retrieval import build_embeddings


@pytest.fixture(scope="module")
def smoke_app(tmp_path_factory):
    tmp_dir = tmp_path_factory.mktemp("smoke_vault")
    db_file = tmp_dir / "smoke.db"
    db = EvidenceDB(str(db_file))

    # Populate with reproducible seed STEM corpus (4 sources, 12 atomic units)
    seed_corpus(db)
    build_embeddings(db)
    db.close()

    service = AgentOSTutorService(
        db_path=str(db_file),
        in_memory_chroma=True,
    )
    service.sync_chroma()
    app = create_agent_os_app(service)

    yield app, service
    service.close()


def test_smoke_health_check(smoke_app):
    app, service = smoke_app
    client = TestClient(app)

    # AgentOS root health
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] in ["ok", "healthy"]

    # Component-level health
    resp_v1 = client.get("/api/v1/health")
    assert resp_v1.status_code == 200
    data = resp_v1.json()
    assert data["status"] == "healthy"
    assert data["sqlite_db"]["sources_count"] >= 4
    assert data["sqlite_db"]["evidence_count"] >= 12
    assert data["chroma_db"]["indexed_units"] >= 12
    assert "ollama" in data
    assert "available" in data["ollama"]


def test_smoke_sources_endpoint(smoke_app):
    app, service = smoke_app
    client = TestClient(app)

    resp = client.get("/api/v1/sources")
    assert resp.status_code == 200
    sources = resp.json()
    assert len(sources) >= 4

    # Verify primary Track D source modalities are represented in the seed corpus
    modalities = {s["modality"] for s in sources}
    assert {"pdf", "pptx", "video"}.issubset(modalities)


def test_smoke_evidence_search_hybrid(smoke_app):
    app, service = smoke_app
    client = TestClient(app)

    # Lexical + semantic query
    resp = client.get("/api/v1/evidence/search?q=acceleration&k=3&mode=hybrid")
    assert resp.status_code == 200
    data = resp.json()
    assert data["unsupported"] is False
    assert len(data["results"]) >= 1

    # Verify exact locator presence in results
    first_res = data["results"][0]
    assert "evidence_id" in first_res
    assert "location" in first_res
    assert isinstance(first_res["location"], dict)


def test_smoke_tutor_supported_query(smoke_app):
    app, service = smoke_app
    client = TestClient(app)

    # Core grounded query from STEM corpus
    payload = {"query": "What is Newton's second law?"}
    resp = client.post("/api/v1/tutor/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["is_grounded"] is True
    assert data["support_status"] == "supported"
    assert len(data["citations"]) >= 1

    # Verify citation physical locator
    top_citation = data["citations"][0]
    assert top_citation["source_id"] is not None
    assert top_citation["location"] is not None
    assert len(data["answer"]) > 20


def test_smoke_tutor_unsupported_query_abstention(smoke_app):
    app, service = smoke_app
    client = TestClient(app)

    # Canonical off-material question (French Revolution vs Science/Math corpus)
    payload = {"query": "What were the primary economic causes of the French Revolution in 1789?"}
    resp = client.post("/api/v1/tutor/query", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    # Must abstain fail-closed
    assert data["is_grounded"] is False
    assert data["support_status"] == "unsupported"
    assert len(data["citations"]) == 0
    assert "does not contain sufficient evidence" in data["answer"]


def test_smoke_chroma_sync(smoke_app):
    app, service = smoke_app
    client = TestClient(app)

    resp = client.post("/api/v1/evidence/sync-chroma")
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    assert resp.json()["synced_units"] >= 12


def test_smoke_ollama_connectivity_probe():
    """Validates local Ollama probe without failing if daemon is offline."""
    is_up = is_ollama_available(DEFAULT_OLLAMA_HOST, timeout=0.5)
    models = get_available_ollama_models(DEFAULT_OLLAMA_HOST, timeout=0.5)
    assert isinstance(is_up, bool)
    assert isinstance(models, list)



def test_username_password_authentication_and_learner_isolation(smoke_app):
    app, service = smoke_app
    client = TestClient(app)
    payload = {"username": "study_user_01", "password": "correct-horse-42"}

    signup = client.post("/api/v1/auth/signup", json=payload)
    assert signup.status_code == 200
    session = signup.json()
    assert session["username"] == payload["username"]
    assert session["learner_id"] == "user_study_user_01"
    assert session["access_token"]

    duplicate = client.post("/api/v1/auth/signup", json=payload)
    assert duplicate.status_code == 409

    bad_login = client.post("/api/v1/auth/login", json={"username": payload["username"], "password": "wrong-password"})
    assert bad_login.status_code == 401

    login = client.post("/api/v1/auth/login", json=payload)
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}", "X-Learner-Id": "user_study_user_01"}

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["learner_id"] == "user_study_user_01"

    own_profile = client.get("/api/v1/learner/user_study_user_01/profile", headers=headers)
    assert own_profile.status_code == 200
    other_profile = client.get("/api/v1/learner/learner_demo/profile", headers=headers)
    assert other_profile.status_code == 403

    logout = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout.status_code == 200
    expired = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert expired.status_code == 401


def test_signup_validates_username_and_password(smoke_app):
    app, service = smoke_app
    client = TestClient(app)
    assert client.post("/api/v1/auth/signup", json={"username": "ab", "password": "12345678"}).status_code == 400
    assert client.post("/api/v1/auth/signup", json={"username": "valid_user", "password": "short"}).status_code == 422
