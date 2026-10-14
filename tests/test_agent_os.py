"""
Comprehensive test suite for Agno AgentOS, local Ollama provider, and FastAPI endpoints.
Validates fail-closed abstention, exact locator citations, and service contracts.
"""
import json
import pytest
from starlette.testclient import TestClient

from app.db import EvidenceDB
from app.models import EvidenceUnit, Modality, SourceRecord
from app.retrieval import HybridRetriever, build_embeddings
from app.sufficiency import EvidenceGate
from app.source_resolver import SourceResolver
from app.chroma_store import ChromaEvidenceStore
from app.agent_os.tools import AgentTools
from app.agent_os.tutor_agent import EvidenceTutorAgent
from app.agent_os.service import AgentOSTutorService
from app.agent_os.app import create_agent_os_app


@pytest.fixture
def test_env(tmp_path):
    db_file = tmp_path / "agentos_test.db"
    db = EvidenceDB(str(db_file))

    # Add 2 sources
    s1 = SourceRecord(
        source_id="src_physics_textbook",
        path="data/corpus/physics.pdf",
        modality=Modality.pdf,
        title="College Physics",
        sha256="sha256_mock_1",
        metadata={"subject": "Physics", "grade": "11"},
    )
    s2 = SourceRecord(
        source_id="src_slides",
        path="data/corpus/slides.pptx",
        modality=Modality.pptx,
        title="Newtonian Mechanics",
        sha256="sha256_mock_2",
        metadata={"subject": "Physics"},
    )
    db.add_source(s1)
    db.add_source(s2)

    # Add evidence units
    u1 = EvidenceUnit(
        evidence_id="ev_kinematics_1",
        source_id="src_physics_textbook",
        modality=Modality.pdf,
        text="Displacement is the vector difference between the final and initial positions of an object.",
        location={"page": 12, "locator": "Page 12"},
        topics=["Kinematics"],
        concepts=["Displacement"],
    )
    u2 = EvidenceUnit(
        evidence_id="ev_dynamics_1",
        source_id="src_slides",
        modality=Modality.pptx,
        text="Newton's second law: The acceleration of an object is directly proportional to the net force acting upon it (F = ma).",
        location={"slide": 5, "locator": "Slide 5"},
        topics=["Dynamics"],
        concepts=["Second Law"],
    )
    for u in [u1, u2]:
        db.add_evidence(u)

    # Build embeddings in SQLite
    build_embeddings(db)

    chroma = ChromaEvidenceStore(in_memory=True, collection_name=f"test_aos_{tmp_path.name}")
    chroma.sync_from_sqlite(db)

    retriever = HybridRetriever(db, chroma_store=chroma)
    gate = EvidenceGate()
    resolver = SourceResolver(db)

    yield {
        "db": db,
        "chroma": chroma,
        "retriever": retriever,
        "gate": gate,
        "resolver": resolver,
        "db_path": str(db_file),
    }
    db.close()


def test_agent_tools_functionality(test_env):
    tools = AgentTools(
        db=test_env["db"],
        retriever=test_env["retriever"],
        gate=test_env["gate"],
        resolver=test_env["resolver"],
    )

    # 1. Search course materials
    res_search = json.loads(tools.search_course_materials("Newton second law", k=2))
    assert res_search["status"] == "success"
    assert res_search["count"] >= 1
    assert any(e["evidence_id"] == "ev_dynamics_1" for e in res_search["evidence"])

    # 2. Sufficiency evaluation (Supported)
    res_suff_yes = json.loads(tools.evaluate_evidence_sufficiency("What is displacement in kinematics?"))
    assert res_suff_yes["supported"] is True
    assert "ev_kinematics_1" in res_suff_yes["evidence_ids"]

    # 3. Sufficiency evaluation (Unsupported / off-topic)
    res_suff_no = json.loads(tools.evaluate_evidence_sufficiency("What is cellular mitosis in human biology?"))
    assert res_suff_no["supported"] is False

    # 4. Locator resolution
    res_loc = json.loads(tools.resolve_locator_details("ev_dynamics_1"))
    assert res_loc["evidence_id"] == "ev_dynamics_1"
    assert res_loc["source_id"] == "src_slides"
    assert res_loc["location"]["slide"] == 5

    # 5. Citation validation
    res_cit_valid = json.loads(tools.validate_citation_support("acceleration is net force", "ev_dynamics_1"))
    assert res_cit_valid["valid"] is True


def test_evidence_tutor_agent_abstention_on_off_topic(test_env):
    agent = EvidenceTutorAgent(
        db=test_env["db"],
        retriever=test_env["retriever"],
        gate=test_env["gate"],
        resolver=test_env["resolver"],
    )

    # Query completely outside the corpus
    resp = agent.ask("Explain chlorophyll absorption during photosynthesis in plant cells.")

    assert resp.is_grounded is False
    assert resp.support_status == "unsupported"
    assert len(resp.citations) == 0
    assert "does not contain sufficient evidence" in resp.answer
    assert any("INSUFFICIENT" in step for step in resp.reasoning_steps)


def test_evidence_tutor_agent_grounded_answer(test_env):
    agent = EvidenceTutorAgent(
        db=test_env["db"],
        retriever=test_env["retriever"],
        gate=test_env["gate"],
        resolver=test_env["resolver"],
    )

    resp = agent.ask("What is Newton's second law of motion?")

    assert resp.is_grounded is True
    assert resp.support_status == "supported"
    assert resp.confidence > 0.0
    assert len(resp.citations) >= 1
    top_cit = resp.citations[0]
    assert top_cit.evidence_id == "ev_dynamics_1"
    assert top_cit.source_id == "src_slides"
    assert top_cit.location["slide"] == 5
    assert "Slide 5" in resp.answer or "Slide" in str(top_cit.location)


def test_agent_os_service_and_health(test_env):
    service = AgentOSTutorService(
        db_path=test_env["db_path"],
        in_memory_chroma=True,
    )
    # Sync
    count = service.sync_chroma()
    assert count >= 2

    # Health check
    health = service.health_check()
    assert health["status"] == "healthy"
    assert health["sqlite_db"]["sources_count"] == 2
    assert health["chroma_db"]["indexed_units"] >= 2
    assert "ollama" in health

    # Source listing
    sources = service.list_sources()
    assert len(sources) == 2
    assert any(s["source_id"] == "src_physics_textbook" for s in sources)

    service.close()


def test_agent_os_fastapi_endpoints(test_env):
    service = AgentOSTutorService(
        db_path=test_env["db_path"],
        in_memory_chroma=True,
    )
    service.sync_chroma()

    app = create_agent_os_app(service)
    client = TestClient(app)

    # 1. GET /health and /api/v1/health
    r_health = client.get("/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] in ["ok", "healthy"]

    r_api_health = client.get("/api/v1/health")
    assert r_api_health.status_code == 200
    assert r_api_health.json()["status"] == "healthy"

    # 2. GET /api/v1/sources
    r_sources = client.get("/api/v1/sources")
    assert r_sources.status_code == 200
    assert len(r_sources.json()) == 2

    # 3. GET /api/v1/evidence/search
    r_search = client.get("/api/v1/evidence/search?q=displacement")
    assert r_search.status_code == 200
    search_data = r_search.json()
    assert search_data["result_count"] >= 1
    assert search_data["results"][0]["evidence_id"] == "ev_kinematics_1"

    # 4. POST /api/v1/tutor/query (Supported)
    r_query_sup = client.post(
        "/api/v1/tutor/query",
        json={"query": "What is displacement in physics?"},
    )
    assert r_query_sup.status_code == 200
    data_sup = r_query_sup.json()
    assert data_sup["is_grounded"] is True
    assert data_sup["support_status"] == "supported"
    assert len(data_sup["citations"]) >= 1

    # 5. POST /api/v1/tutor/query (Unsupported / off-topic)
    r_query_unsup = client.post(
        "/api/v1/tutor/query",
        json={"query": "How do mitochondria generate ATP in eukaryotic cells?"},
    )
    assert r_query_unsup.status_code == 200
    data_unsup = r_query_unsup.json()
    assert data_unsup["is_grounded"] is False
    assert data_unsup["support_status"] == "unsupported"
    assert len(data_unsup["citations"]) == 0

    # 6. POST /api/v1/tutor/query (Empty query -> 400)
    r_empty = client.post("/api/v1/tutor/query", json={"query": "   "})
    assert r_empty.status_code == 400

    # 7. POST /api/v1/evidence/sync-chroma
    r_sync = client.post("/api/v1/evidence/sync-chroma")
    assert r_sync.status_code == 200
    assert r_sync.json()["status"] == "success"

    service.close()
