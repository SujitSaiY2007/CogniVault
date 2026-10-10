"""
Tests for Evaluation Benchmark Runner & Dataset Integrity.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from app.db import EvidenceDB
from app.corpus import seed_database_from_corpus
from evaluation.runner import run_deterministic_benchmark, EvaluationRunner


@pytest.fixture
def temp_eval_db(tmp_path):
    db_path = tmp_path / "eval_test.sqlite"
    db = EvidenceDB(db_path)
    seed_database_from_corpus(db)
    yield db
    db.close()


def test_benchmark_dataset_structure():
    """Validates that benchmark_dataset.json contains all required test sections."""
    dataset_path = Path("evaluation/benchmark_dataset.json")
    assert dataset_path.exists(), "benchmark_dataset.json must exist"

    data = json.loads(dataset_path.read_text(encoding="utf-8"))
    assert "benchmark_version" in data
    assert "retrieval_and_tutor_cases" in data
    assert "question_verification_cases" in data
    assert "bkt_transition_cases" in data
    assert "recommendation_policy_cases" in data

    assert len(data["retrieval_and_tutor_cases"]) >= 8
    assert len(data["question_verification_cases"]) >= 4
    assert len(data["bkt_transition_cases"]) >= 4
    assert len(data["recommendation_policy_cases"]) >= 6



def test_deterministic_benchmark_execution(temp_eval_db, tmp_path):
    """
    Executes the deterministic benchmark suite and validates that
    all core metrics achieve expected ground-truth performance.
    """
    output_path = tmp_path / "test_benchmark_results.json"
    results = run_deterministic_benchmark(
        db=temp_eval_db,
        output_path=output_path
    )

    assert output_path.exists()
    assert results["total_test_cases"] >= 20

    metrics = results["metrics"]
    assert metrics["supported_answer_rate"] == 1.0
    assert metrics["unsupported_abstention_rate"] == 1.0
    assert metrics["unsupported_leakage_rate"] == 0.0
    assert metrics["citation_addressability_rate"] == 1.0
    assert metrics["citation_locator_accuracy"] == 1.0
    assert metrics["question_verification_accuracy"] == 1.0
    assert metrics["bkt_numerical_accuracy"] == 1.0
    assert metrics["recommendation_policy_accuracy"] == 1.0
    assert metrics["repetition_control_pass"] is True


def test_evaluation_runner_class_wrapper(temp_eval_db, tmp_path):
    """Validates the object-oriented EvaluationRunner interface."""
    runner = EvaluationRunner(db=temp_eval_db)
    output_path = tmp_path / "class_benchmark_results.json"
    res = runner.run_benchmark(output_path=output_path)

    assert output_path.exists()
    assert "metrics" in res
    assert res["metrics"]["supported_answer_rate"] == 1.0
