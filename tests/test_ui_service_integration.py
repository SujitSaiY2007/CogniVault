"""
Tests for UI Service Container, Ingestion Bridges, and Multi-turn Simulations.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from app.db import EvidenceDB
from app.corpus import build_reproducible_corpus, seed_database_from_corpus, get_corpus_manifest
from app.ingest import ingest_file
from app.ui.state import get_services
from evaluation.simulate_learners import simulate_multi_turn_learners, run_all_simulations


@pytest.fixture
def temp_service_db(tmp_path):
    db_path = tmp_path / "ui_service_test.sqlite"
    db = EvidenceDB(db_path)
    seed_database_from_corpus(db)
    yield db, db_path
    db.close()


def test_ui_service_container_initialization(temp_service_db):
    """Validates that the UI service container initializes all required components."""
    db, db_path = temp_service_db
    services = get_services(str(db_path))

    assert "db" in services
    assert "retriever" in services
    assert "sufficiency_gate" in services
    assert "tutor" in services
    assert "verifier" in services
    assert "assessment_engine" in services
    assert "bkt" in services
    assert "misconceptions" in services
    assert "recommendations" in services


def test_ingest_file_dispatcher(tmp_path):
    """Validates that ingest_file dispatches correctly across file types."""
    db_path = tmp_path / "ingest_disp_test.sqlite"
    db = EvidenceDB(db_path)

    # Ingest TXT transcript
    transcript_path = tmp_path / "lecture.txt"
    transcript_path.write_text("[00:01:15] Photosynthesis converts sunlight into chemical energy.", encoding="utf-8")
    sid_txt = ingest_file(transcript_path, db)
    assert sid_txt is not None
    assert len(list(db.all_evidence())) == 1

    # Ingest unsupported format -> raises ValueError
    unsupported_path = tmp_path / "data.csv"
    unsupported_path.write_text("a,b,c", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported file format"):
        ingest_file(unsupported_path, db)

    db.close()


def test_simulation_runner_execution(temp_service_db, tmp_path):
    """Validates that simulated learner evaluations produce all scenarios and baseline comparison."""
    db, _ = temp_service_db
    out_path = tmp_path / "test_sim_results.json"

    res = simulate_multi_turn_learners(db=db, output_path=out_path)

    assert out_path.exists()
    assert "scenarios" in res
    assert "baseline_comparison" in res

    scenarios = res["scenarios"]
    assert "consistently_correct" in scenarios
    assert "consistently_incorrect" in scenarios
    assert "mixed_performance" in scenarios
    assert "misconception_remediation" in scenarios
    assert "prerequisite_gating" in scenarios
    assert "boundary_values" in scenarios

    base_comp = res["baseline_comparison"]
    assert "adaptive_difficulty_trajectory" in base_comp
    assert "static_difficulty_trajectory" in base_comp


def test_evidence_for_source_and_ui_bkt_integration(temp_service_db):
    """Validates get_evidence_for_source and UI state BKT observation workflow."""
    db, db_path = temp_service_db
    services = get_services(str(db_path))

    # 1. Test get_evidence_for_source for all seeded sources
    sources = list(db.all_sources())
    assert len(sources) > 0
    total_ev = 0
    for s in sources:
        ev_list = db.get_evidence_for_source(s.source_id)
        assert isinstance(ev_list, list)
        assert len(ev_list) > 0
        total_ev += len(ev_list)
    assert total_ev == len(list(db.all_evidence()))

    # 2. Test BKT observation / response recording via services container
    bkt = services["bkt"]
    assert hasattr(bkt, "record_observation")
    assert hasattr(bkt, "record_response")

    learner_id = "test_learner_ui_integration"
    topic_id = "Newtonian Mechanics"

    rec1 = bkt.record_observation(learner_id, topic_id, is_correct=True)
    assert rec1.attempts == 1
    assert rec1.correct == 1
    assert rec1.p_mastery > 0.10

    rec2 = bkt.record_observation(learner_id, topic_id, is_correct=False)
    assert rec2.attempts == 2
    assert rec2.correct == 1
    assert rec2.p_mastery < rec1.p_mastery


def test_all_seven_streamlit_views_render_without_exceptions():
    """Validates that all Streamlit navigation views render cleanly without unhandled exceptions."""
    from streamlit.testing.v1 import AppTest
    from pathlib import Path

    app_path = Path("app/ui/main.py").resolve()
    at = AppTest.from_file(str(app_path), default_timeout=15)
    at.run(timeout=15)
    assert len(at.exception) == 0, f"Initial run exceptions: {[e.message for e in at.exception]}"

    options = at.sidebar.radio[0].options
    assert len(options) == 9

    for opt in options:
        at.sidebar.radio[0].set_value(opt).run(timeout=15)
        assert len(at.exception) == 0, f"View '{opt}' raised exception: {[e.message for e in at.exception]}"




