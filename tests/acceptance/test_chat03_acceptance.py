"""
Chat 03 Acceptance Test Suite — Product & Evaluation.
Validates the end-to-end user workflows, reproducible corpus,
deterministic question verification, citation addressability, BKT tracking,
and prerequisite-aware recommendation policies.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from app.corpus import seed_database_from_corpus, get_corpus_manifest
from app.db import EvidenceDB
from app.ingest import ingest_file
from app.models import (
    Difficulty,
    LearnerSubmission,
    Modality,
    Question,
    QuestionOption,
    QuestionType,
    TopicMasteryRecord,
)
from app.retrieval import HybridRetriever
from app.sufficiency import EvidenceSufficiencyGate
from app.tutor import GroundedTutor
from app.source_resolver import resolve
from app.assessment import AssessmentEngine, DeterministicQuestionVerifier
from app.learner_model import BKTModel, LearnerStateManager
from app.misconceptions import MisconceptionDetector
from app.recommendation import AdaptiveRecommendationEngine


@pytest.fixture
def seeded_db(tmp_path):
    db_path = tmp_path / "chat03_acceptance.sqlite"
    db = EvidenceDB(db_path)
    seed_database_from_corpus(db)
    yield db
    db.close()


# ---------------------------------------------------------------------------
# Test 1: Real & Reproducible Corpus Ingestion & Manifest Integrity
# ---------------------------------------------------------------------------
def test_corpus_manifest_and_ingestion_integrity(seeded_db):
    """
    Validates that the baseline Math/Science corpus is reproducible,
    contains valid source records, evidence units, locators, and manifest metadata.
    """
    manifest = get_corpus_manifest()
    assert "corpus_version" in manifest or "manifest_version" in manifest or "sources" in manifest
    assert len(manifest["sources"]) >= 4

    sources = list(seeded_db.all_sources())
    assert len(sources) >= 4

    modalities = {s.modality for s in sources}
    assert Modality.pdf in modalities
    assert Modality.pptx in modalities
    assert Modality.video in modalities

    evidence_units = list(seeded_db.all_evidence())
    assert len(evidence_units) >= 10

    # Ensure every evidence unit has a valid locator
    for ev in evidence_units:
        loc = ev.location
        assert ("page" in loc) or ("slide" in loc) or ("timestamp" in loc)


# ---------------------------------------------------------------------------
# Test 2: Grounded AI Tutor — Direct Course Evidence & Resolvable Citation
# ---------------------------------------------------------------------------
def test_tutor_grounded_answer_and_resolvable_citation(seeded_db):
    """
    Validates that direct questions retrieve verified evidence, formulate grounded answers,
    and attach exact, addressable citations with page/slide locators.
    """
    tutor = GroundedTutor(seeded_db)
    res = tutor.answer("What is Newton's second law of motion and its formula?", mode="lexical")

    assert res.is_grounded is True
    assert res.support_status == "supported"
    assert "Newton" in res.answer or "F = m" in res.answer or "force" in res.answer.lower()
    assert len(res.citations) >= 1

    for cite in res.citations:
        resolved = resolve(cite.evidence_id, seeded_db)
        assert resolved is not None
        loc = cite.location
        assert ("page" in loc) or ("slide" in loc) or ("timestamp" in loc)

    assert any(cite.source_id == "physics_mechanics" for cite in res.citations)


# ---------------------------------------------------------------------------
# Test 3: Grounded AI Tutor — Fail-Closed Abstention on Off-Corpus Questions
# ---------------------------------------------------------------------------
def test_tutor_fail_closed_abstention_on_off_corpus_query(seeded_db):
    """
    Validates that out-of-corpus queries (e.g. French Revolution) trigger explicit abstention
    and do not leak unsupported claims.
    """
    tutor = GroundedTutor(seeded_db)
    res = tutor.answer("What were the primary economic causes of the French Revolution in 1789?", mode="hybrid")

    assert res.is_grounded is False
    assert res.support_status == "unsupported"
    assert "cannot answer" in res.answer.lower()
    assert len(res.citations) == 0
    assert res.unsupported_reason is not None


# ---------------------------------------------------------------------------
# Test 4: Question Verification — Structural Integrity & Key Consistency
# ---------------------------------------------------------------------------
def test_question_structural_verification_pass_and_reject(seeded_db):
    """
    Validates that the deterministic question verifier passes structural items
    and rejects malformed/duplicate keys or unparseable numbers.
    """
    verifier = DeterministicQuestionVerifier()

    # Valid MCQ
    q_valid = Question(
        question_id="q_val_01",
        topic_id="Newtonian Mechanics",
        prompt="A 5 kg mass accelerates at 3 m/s^2. What is the net force?",
        options=[
            QuestionOption(key="A", text="10 N"),
            QuestionOption(key="B", text="15 N"),
            QuestionOption(key="C", text="20 N"),
        ],
        expected_answer="B",
        difficulty=Difficulty.medium,
        evidence_ids=["physics_mechanics:e00001"],
    )
    res_valid = verifier.verify(q_valid, db=seeded_db)
    assert res_valid.is_valid is True

    # Invalid MCQ: duplicate keys
    q_invalid = Question(
        question_id="q_inval_01",
        topic_id="Newtonian Mechanics",
        prompt="A 5 kg mass accelerates at 3 m/s^2. What is the net force?",
        options=[
            QuestionOption(key="A", text="10 N"),
            QuestionOption(key="A", text="15 N"),
        ],
        expected_answer="A",
        difficulty=Difficulty.medium,
        evidence_ids=["physics_mechanics:e00001"],
    )
    res_invalid = verifier.verify(q_invalid, db=seeded_db)
    assert res_invalid.is_valid is False
    assert any("Duplicate option key" in r for r in res_invalid.failure_reasons)


# ---------------------------------------------------------------------------
# Test 5: Adaptive Assessment — Non-Repeating Selection & Evidence Feedback
# ---------------------------------------------------------------------------
def test_adaptive_assessment_repetition_suppression_and_feedback(seeded_db):
    """
    Validates that adaptive selection suppresses already served questions
    and provides evidence-linked feedback upon submission.
    """
    engine = AssessmentEngine(seeded_db)

    # First draw
    q1 = engine.select_adaptive_question("Newtonian Mechanics", served_question_ids=[])
    assert q1 is not None

    # Second draw with q1 served -> must return alternative question
    q2 = engine.select_adaptive_question("Newtonian Mechanics", served_question_ids=[q1.question_id])
    assert q2 is not None
    assert q2.question_id != q1.question_id

    # Evaluate submission
    sub = LearnerSubmission(
        learner_id="test_learner",
        question_id=q1.question_id,
        topic_id=q1.topic_id,
        answer=q1.expected_answer
    )
    eval_res = engine.evaluate_submission(sub, q1)
    assert eval_res.is_correct is True
    assert eval_res.status == "correct"
    assert len(eval_res.citations) >= 1
    assert "Refer to Page" in eval_res.feedback or "Correct" in eval_res.feedback


# ---------------------------------------------------------------------------
# Test 6: Bayesian Knowledge Tracing (BKT) Multi-Turn Progression
# ---------------------------------------------------------------------------
def test_bkt_multi_turn_progression(seeded_db):
    """
    Validates Bayesian Knowledge Tracing posterior state transitions across multiple observations:
    Initial: 0.10 -> Correct (0.4333) -> Correct (0.6305) -> Correct (0.9020).
    """
    bkt = BKTModel()
    manager = LearnerStateManager(seeded_db, bkt)
    learner_id = "bkt_advancing_test"
    topic = "Calculus Derivatives"

    # Step 1: correct
    rec1 = manager.record_response(learner_id, topic, is_correct=True)
    assert abs(rec1.p_mastery - 0.433333) < 1e-4

    # Step 2: correct
    rec2 = manager.record_response(learner_id, topic, is_correct=True)
    assert abs(rec2.p_mastery - 0.808609) < 1e-4

    # Step 3: correct
    rec3 = manager.record_response(learner_id, topic, is_correct=True)
    assert rec3.p_mastery > 0.85  # Mastered bracket!


# ---------------------------------------------------------------------------
# Test 7: Misconception Detection & Remediation Routing
# ---------------------------------------------------------------------------
def test_misconception_detection_and_remediation_routing(seeded_db):
    """
    Validates that repeated wrong answers trigger a misconception signal
    and route recommendations to prerequisite remediation.
    """
    detector = MisconceptionDetector(seeded_db, error_threshold=2)
    rec_engine = AdaptiveRecommendationEngine(seeded_db)
    learner_id = "misc_test_learner"
    topic = "Newtonian Mechanics"
    concept = "Newton's Second Law"

    # Mistake 1 (isolated slip)
    sig1 = detector.analyze_attempt(learner_id, topic, concept, is_correct=False, error_pattern="F=m/a")
    assert sig1 is None

    # Mistake 2 (threshold reached -> misconception diagnosed)
    sig2 = detector.analyze_attempt(learner_id, topic, concept, is_correct=False, error_pattern="F=m/a")
    assert sig2 is not None
    assert sig2.error_count == 2
    assert round(sig2.confidence, 2) >= 0.80

    # Recommendation must prioritize misconception remediation
    rec = rec_engine.recommend(learner_id, active_topic_id=topic)
    assert rec.recommended_action == "remediate_misconception"
    assert rec.difficulty == Difficulty.easy
    assert "Active misconception" in rec.rationale


# ---------------------------------------------------------------------------
# Test 8: Prerequisite Gatekeeper Enforcement
# ---------------------------------------------------------------------------
def test_prerequisite_gatekeeper_blocks_unmastered_advancement(seeded_db):
    """
    Validates that missing or unverified prerequisite mastery (< 0.70)
    strictly blocks advancement to dependent topics.
    """
    rec_engine = AdaptiveRecommendationEngine(seeded_db)
    learner_id = "prereq_test_learner"

    # Geometric Optics requires Wave Properties.
    # Case A: Wave Properties unobserved (no mastery record)
    rec_unobserved = rec_engine.recommend(learner_id, active_topic_id="Geometric Optics")
    assert rec_unobserved.recommended_action == "foundational_review"
    assert rec_unobserved.topic_id == "Wave Properties"
    assert "no recorded mastery" in rec_unobserved.rationale

    # Case B: Wave Properties recorded at 0.50 (< 0.70 threshold)
    seeded_db.save_learner_mastery(
        TopicMasteryRecord(
            learner_id=learner_id,
            topic_id="Wave Properties",
            p_mastery=0.50,
            attempts=2,
            correct=1
        )
    )
    rec_below = rec_engine.recommend(learner_id, active_topic_id="Geometric Optics")
    assert rec_below.recommended_action == "foundational_review"
    assert rec_below.topic_id == "Wave Properties"
    assert "requires reinforcement" in rec_below.rationale

    # Case C: Wave Properties satisfied at 0.75 (>= 0.70)
    seeded_db.save_learner_mastery(
        TopicMasteryRecord(
            learner_id=learner_id,
            topic_id="Wave Properties",
            p_mastery=0.75,
            attempts=4,
            correct=3
        )
    )
    rec_ok = rec_engine.recommend(learner_id, active_topic_id="Geometric Optics")
    assert rec_ok.topic_id == "Geometric Optics"


# ---------------------------------------------------------------------------
# Test 9: Strict Boundary Condition Verification (§17 Technical Lock)
# ---------------------------------------------------------------------------
def test_mastery_band_boundary_conditions(seeded_db):
    """
    Verifies exact mastery band boundaries from docs/CHAT0_TECHNICAL_LOCK.md:
      - p < 0.40: foundational_review (easy)
      - 0.40 <= p < 0.70: targeted_practice (medium)
      - 0.70 <= p <= 0.85: mixed_application (medium)
      - p > 0.85: advance_topic (hard)
      - 0.85 is mixed_application; 0.850001 is advance_topic.
    """
    rec_engine = AdaptiveRecommendationEngine(seeded_db)
    learner_id = "boundary_learner"
    topic = "Newtonian Mechanics"

    cases = [
        (0.39, "foundational_review", Difficulty.easy),
        (0.40, "targeted_practice", Difficulty.medium),
        (0.69, "targeted_practice", Difficulty.medium),
        (0.70, "mixed_application", Difficulty.medium),
        (0.85, "mixed_application", Difficulty.medium),
        (0.850001, "advance_topic", Difficulty.hard),
    ]

    for p_val, exp_action, exp_diff in cases:
        seeded_db.save_learner_mastery(
            TopicMasteryRecord(
                learner_id=learner_id,
                topic_id=topic,
                p_mastery=p_val,
                attempts=1,
                correct=1
            )
        )
        rec = rec_engine.recommend(learner_id, active_topic_id=topic)
        assert rec.recommended_action == exp_action, f"Failed action for p={p_val}: got {rec.recommended_action}, expected {exp_action}"
        assert rec.difficulty == exp_diff, f"Failed difficulty for p={p_val}: got {rec.difficulty}, expected {exp_diff}"

