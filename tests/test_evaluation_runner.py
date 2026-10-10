"""
Tests for Evaluation Benchmark Runner, Repetition Suppression, Citation Locators & Dataset Integrity.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from app.db import EvidenceDB
from app.corpus import seed_database_from_corpus, get_corpus_manifest
from app.assessment import AssessmentEngine, DeterministicQuestionVerifier
from evaluation.runner import (
    run_deterministic_benchmark,
    EvaluationRunner,
    verify_citation_locator_structural_integrity,
    compute_retrieval_precision_recall_at_k,
)


@pytest.fixture
def temp_eval_db(tmp_path):
    db_path = tmp_path / "eval_test.sqlite"
    db = EvidenceDB(db_path)
    seed_database_from_corpus(db)
    yield db
    db.close()


def test_benchmark_dataset_structure():
    """Validates that benchmark_dataset.json contains all required test sections with expected sources and locators."""
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

    # Verify that in-corpus cases have expected sources and locators
    for tc in data["retrieval_and_tutor_cases"]:
        if tc.get("expected_status") == "supported":
            assert "expected_source_ids" in tc or "expected_source_id" in tc
            assert "expected_evidence_ids" in tc
            assert "expected_locators" in tc


def test_deterministic_benchmark_execution(temp_eval_db, tmp_path):
    """
    Executes the deterministic benchmark suite and validates that
    all core metrics achieve expected ground-truth performance with explicit denominators.
    """
    output_path = tmp_path / "test_benchmark_results.json"
    results = run_deterministic_benchmark(
        db=temp_eval_db,
        output_path=output_path
    )

    assert output_path.exists()
    assert results["total_test_cases"] == 28

    metrics = results["metrics"]
    assert metrics["supported_answer_rate"] == 1.0
    assert metrics["unsupported_abstention_rate"] == 1.0
    assert metrics["unsupported_leakage_rate"] == 0.0
    assert metrics["retrieval_precision_at_3"] >= 0.35
    assert metrics["retrieval_recall_at_3"] == 1.0
    assert metrics["citation_addressability_rate"] == 1.0
    assert metrics["source_resolved_locator_accuracy"] == 1.0
    assert metrics["question_verification_accuracy"] == 1.0
    assert metrics["bkt_numerical_accuracy"] == 1.0
    assert metrics["recommendation_policy_accuracy"] == 1.0
    assert metrics["repetition_control_pass"] is True

    denominators = results["denominators"]
    assert denominators["supported_total"] == 8
    assert denominators["unsupported_total"] == 3
    assert denominators["retrieval_cases_evaluated"] == 8
    assert denominators["citations_total"] > 0
    assert denominators["citations_source_resolved"] == denominators["citations_total"]


def test_repetition_suppression_alternative_and_fallback(temp_eval_db):
    """
    Validates that:
    1. For a topic with multiple questions, previously served question is suppressed and an alternative is chosen.
    2. When all questions for a topic have been served, the selector gracefully falls back to the pool without crashing.
    """
    engine = AssessmentEngine(temp_eval_db)

    # 1. First selection from Newtonian Mechanics
    q1 = engine.select_adaptive_question("Newtonian Mechanics", served_question_ids=[])
    assert q1 is not None

    # 2. Second selection with q1 served -> alternative MUST be selected
    q2 = engine.select_adaptive_question("Newtonian Mechanics", served_question_ids=[q1.question_id])
    assert q2 is not None
    assert q2.question_id != q1.question_id
    assert q2.fingerprint != q1.fingerprint

    # 3. Third selection when BOTH questions are in served_question_ids -> graceful fallback
    q_fallback = engine.select_adaptive_question(
        "Newtonian Mechanics",
        served_question_ids=[q1.question_id, q2.question_id]
    )
    assert q_fallback is not None
    assert q_fallback.question_id in [q1.question_id, q2.question_id]


def test_source_resolved_citation_locator_verification():
    """
    Validates the structural integrity checker for citation locators.
    """
    # Valid PDF page match
    assert verify_citation_locator_structural_integrity({"page": 1}, {"page": 1}) is True

    # Valid PPTX slide match
    assert verify_citation_locator_structural_integrity({"slide": 2}, {"slide": 2}) is True

    # Valid transcript timestamp match
    assert verify_citation_locator_structural_integrity({"timestamp": "02:40"}, {"timestamp": "02:40"}) is True

    # Invalid mismatches
    assert verify_citation_locator_structural_integrity({"page": 1}, {"page": 2}) is False
    assert verify_citation_locator_structural_integrity({"page": -1}, {"page": -1}) is False
    assert verify_citation_locator_structural_integrity({"slide": 0}, {"slide": 0}) is False
    assert verify_citation_locator_structural_integrity({}, {"page": 1}) is False


def test_corpus_manifest_provenance_and_parser_metadata():
    """
    Validates that data/corpus_manifest.json contains complete provenance,
    licensing statements for synthetic test fixtures, and parser/extractor versions.
    """
    manifest = get_corpus_manifest()
    assert manifest["corpus_id"] == "cognivault-school-stem-benchmark-v1"
    assert manifest["provenance_type"] == "project_authored_synthetic"
    assert "Public Domain" in manifest["license"] or "MIT" in manifest["license"] or "CC0" in manifest["license"]
    assert "parser_and_extractor_metadata" in manifest

    meta = manifest["parser_and_extractor_metadata"]
    assert "pdf_extractor" in meta
    assert "pptx_extractor" in meta
    assert "transcript_extractor" in meta
    assert "chunker_version" in meta

    for s in manifest["sources"]:
        assert "extractor" in s
        assert "author" in s
        assert "license" in s
        assert "sha256" in s


def test_evaluation_runner_class_wrapper(temp_eval_db, tmp_path):
    """Validates the object-oriented EvaluationRunner interface."""
    runner = EvaluationRunner(db=temp_eval_db)
    output_path = tmp_path / "class_benchmark_results.json"
    res = runner.run_benchmark(output_path=output_path)

    assert output_path.exists()
    assert "metrics" in res
    assert res["metrics"]["supported_answer_rate"] == 1.0


def test_retrieval_partial_recall_and_fewer_results_precision():
    """
    Regression test validating that:
    1. When only one of two expected evidence items is retrieved in top 3,
       Recall@3 is exactly 0.50 (1 / 2).
    2. When fewer than three results are returned (e.g. 2, 1, or 0),
       the precision denominator correctly adjusts to min(3, len(retrieved)).
    3. Relevance is defined strictly based on exact expected evidence IDs.
    """
    exp_eids = ["doc_a:e00001", "doc_b:e00002"]

    # Scenario A: 2 expected evidence items, retrieved 3 items, only 1 matches
    retrieved_3 = ["doc_a:e00001", "unrelated:e00003", "unrelated:e00004"]
    prec_3, rec_3 = compute_retrieval_precision_recall_at_k(retrieved_3, exp_eids, k=3)
    assert prec_3 == pytest.approx(1 / 3, rel=1e-3)
    assert rec_3 == pytest.approx(1 / 2, rel=1e-3)

    # Scenario B: 2 expected evidence items, only 2 results returned, 1 matches
    # Precision denominator is min(3, 2) = 2 -> Precision = 1 / 2 = 0.50
    retrieved_2 = ["doc_a:e00001", "unrelated:e00003"]
    prec_2, rec_2 = compute_retrieval_precision_recall_at_k(retrieved_2, exp_eids, k=3)
    assert prec_2 == pytest.approx(0.50, rel=1e-3)
    assert rec_2 == pytest.approx(0.50, rel=1e-3)

    # Scenario C: 2 expected evidence items, only 1 result returned, 1 matches
    # Precision denominator is min(3, 1) = 1 -> Precision = 1 / 1 = 1.00
    retrieved_1 = ["doc_a:e00001"]
    prec_1, rec_1 = compute_retrieval_precision_recall_at_k(retrieved_1, exp_eids, k=3)
    assert prec_1 == pytest.approx(1.00, rel=1e-3)
    assert rec_1 == pytest.approx(0.50, rel=1e-3)

    # Scenario D: 2 expected evidence items, 0 results returned
    prec_0, rec_0 = compute_retrieval_precision_recall_at_k([], exp_eids, k=3)
    assert prec_0 == 0.0
    assert rec_0 == 0.0


def test_retrieval_duplicate_expected_evidence_safety():
    """
    Regression test validating that duplicate occurrences of an expected evidence ID
    in the retrieved list do NOT inflate precision or recall.
    """
    exp_eids = ["doc_a:e00001", "doc_b:e00002"]

    # Scenario 1: A list where doc_a:e00001 is duplicated 3 times
    # Without deduplication, recall would be 3/2 = 1.50 and precision 3/3 = 1.00
    # With duplicate-safety, unique retrieved is ["doc_a:e00001"], so:
    # - exactly 1 unique expected item is retrieved (doc_a:e00001)
    # - recall = 1 / 2 = 0.50
    # - precision = 1 / min(3, 1) = 1.00
    retrieved_dups = ["doc_a:e00001", "doc_a:e00001", "doc_a:e00001"]
    prec_dup, rec_dup = compute_retrieval_precision_recall_at_k(retrieved_dups, exp_eids, k=3)
    assert rec_dup == pytest.approx(0.50, rel=1e-3)
    assert prec_dup == pytest.approx(1.00, rel=1e-3)

    # Scenario 2: doc_a:e00001 duplicated with another unrelated document
    # Retrieved: ["doc_a:e00001", "doc_a:e00001", "unrelated:e00003"]
    # Unique retrieved: ["doc_a:e00001", "unrelated:e00003"] (len 2)
    # Expected: 2 items
    # - unique relevant retrieved = 1 (doc_a:e00001)
    # - recall = 1 / 2 = 0.50 (NOT 2/2 = 1.00!)
    # - precision = 1 / min(3, 2) = 1 / 2 = 0.50 (NOT 2/3 = 0.67!)
    retrieved_mixed = ["doc_a:e00001", "doc_a:e00001", "unrelated:e00003"]
    prec_mix, rec_mix = compute_retrieval_precision_recall_at_k(retrieved_mixed, exp_eids, k=3)
    assert rec_mix == pytest.approx(0.50, rel=1e-3)
    assert prec_mix == pytest.approx(0.50, rel=1e-3)


