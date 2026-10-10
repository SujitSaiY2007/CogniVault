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
