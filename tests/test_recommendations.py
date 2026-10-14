import pytest
from app.db import EvidenceDB
from app.models import Difficulty, MisconceptionSignal, TopicMasteryRecord
from app.recommendation import AdaptiveRecommendationEngine

def test_recommendation_mastery_brackets_and_boundaries(tmp_path):
    """
    Validates the 4 mastery policy brackets from CHAT0_TECHNICAL_LOCK §17:
      - p < 0.40: foundational_review (easy)
      - 0.40 <= p < 0.70: targeted_practice (medium)
      - 0.70 <= p <= 0.85: mixed_application (medium)
      - p > 0.85: advance_topic (hard)
    Tests exact boundary values (0.40, 0.70, 0.85) and immediate neighbors (0.39, 0.41, 0.69, 0.71, 0.84, 0.86).
    """
    db = EvidenceDB(tmp_path / "rec_brackets.sqlite")
    engine = AdaptiveRecommendationEngine(db)

    # 1. Below 0.40 bracket
    db.save_learner_mastery(TopicMasteryRecord(learner_id="u_low", topic_id="Algebra", p_mastery=0.25, attempts=2, correct=0))
    rec = engine.recommend("u_low", active_topic_id="Algebra")
    assert rec.recommended_action == "foundational_review"
    assert rec.difficulty == Difficulty.easy

    # Neighbor 0.39 (< 0.40) -> foundational_review
    db.save_learner_mastery(TopicMasteryRecord(learner_id="u_039", topic_id="Algebra", p_mastery=0.39, attempts=3, correct=1))
    rec = engine.recommend("u_039", active_topic_id="Algebra")
    assert rec.recommended_action == "foundational_review"
    assert rec.difficulty == Difficulty.easy

    # Exact boundary 0.40 (0.40 <= p < 0.70) -> targeted_practice
    db.save_learner_mastery(TopicMasteryRecord(learner_id="u_040", topic_id="Algebra", p_mastery=0.40, attempts=3, correct=1))
    rec = engine.recommend("u_040", active_topic_id="Algebra")
    assert rec.recommended_action == "targeted_practice"
    assert rec.difficulty == Difficulty.medium

    # Neighbor 0.41 (0.40 <= p < 0.70) -> targeted_practice
    db.save_learner_mastery(TopicMasteryRecord(learner_id="u_041", topic_id="Algebra", p_mastery=0.41, attempts=4, correct=2))
    rec = engine.recommend("u_041", active_topic_id="Algebra")
    assert rec.recommended_action == "targeted_practice"
    assert rec.difficulty == Difficulty.medium

    # Mid 0.55 (0.40 <= p < 0.70) -> targeted_practice
    db.save_learner_mastery(TopicMasteryRecord(learner_id="u_055", topic_id="Algebra", p_mastery=0.55, attempts=5, correct=3))
    rec = engine.recommend("u_055", active_topic_id="Algebra")
    assert rec.recommended_action == "targeted_practice"
    assert rec.difficulty == Difficulty.medium

    # Neighbor 0.69 (0.40 <= p < 0.70) -> targeted_practice
    db.save_learner_mastery(TopicMasteryRecord(learner_id="u_069", topic_id="Geometry", p_mastery=0.69, attempts=6, correct=4))
    rec = engine.recommend("u_069", active_topic_id="Geometry")
    assert rec.recommended_action == "targeted_practice"
    assert rec.difficulty == Difficulty.medium

    # Exact boundary 0.70 (0.70 <= p <= 0.85) -> mixed_application
    db.save_learner_mastery(TopicMasteryRecord(learner_id="u_070", topic_id="Geometry", p_mastery=0.70, attempts=7, correct=5))
    rec = engine.recommend("u_070", active_topic_id="Geometry")
    assert rec.recommended_action == "mixed_application"
    assert rec.difficulty == Difficulty.medium

    # Neighbor 0.71 (0.70 <= p <= 0.85) -> mixed_application
    db.save_learner_mastery(TopicMasteryRecord(learner_id="u_071", topic_id="Geometry", p_mastery=0.71, attempts=7, correct=5))
    rec = engine.recommend("u_071", active_topic_id="Geometry")
    assert rec.recommended_action == "mixed_application"
    assert rec.difficulty == Difficulty.medium

    # Mid 0.78 (0.70 <= p <= 0.85) -> mixed_application
    db.save_learner_mastery(TopicMasteryRecord(learner_id="u_078", topic_id="Calculus", p_mastery=0.78, attempts=8, correct=6))
    rec = engine.recommend("u_078", active_topic_id="Calculus")
    assert rec.recommended_action == "mixed_application"
    assert rec.difficulty == Difficulty.medium

    # Neighbor 0.84 (0.70 <= p <= 0.85) -> mixed_application
    db.save_learner_mastery(TopicMasteryRecord(learner_id="u_084", topic_id="Calculus", p_mastery=0.84, attempts=9, correct=7))
    rec = engine.recommend("u_084", active_topic_id="Calculus")
    assert rec.recommended_action == "mixed_application"
    assert rec.difficulty == Difficulty.medium

    # Exact boundary 0.85 (0.70 <= p <= 0.85) -> mixed_application (Authoritative Technical Lock §17)
    db.save_learner_mastery(TopicMasteryRecord(learner_id="u_085", topic_id="Calculus", p_mastery=0.85, attempts=10, correct=8))
    rec = engine.recommend("u_085", active_topic_id="Calculus")
    assert rec.recommended_action == "mixed_application"
    assert rec.difficulty == Difficulty.medium

    # Neighbor 0.86 (p > 0.85) -> advance_topic
    db.save_learner_mastery(TopicMasteryRecord(learner_id="u_086", topic_id="Calculus", p_mastery=0.86, attempts=10, correct=9))
    rec = engine.recommend("u_086", active_topic_id="Calculus")
    assert rec.recommended_action == "advance_topic"
    assert rec.difficulty == Difficulty.hard

    # High mastery 0.95 (p > 0.85) -> advance_topic
    db.save_learner_mastery(TopicMasteryRecord(learner_id="u_095", topic_id="Calculus", p_mastery=0.95, attempts=12, correct=11))
    rec = engine.recommend("u_095", active_topic_id="Calculus")
    assert rec.recommended_action == "advance_topic"
    assert rec.difficulty == Difficulty.hard

def test_recommendation_prerequisite_readiness(tmp_path):
    """
    Validates prerequisite readiness checks:
      - Missing prerequisite mastery (no record in DB) blocks advancement -> foundational_review on prerequisite
      - Prerequisite mastery below 0.70 blocks advancement -> foundational_review on prerequisite
      - Prerequisite mastery exactly 0.70 satisfies readiness
      - Prerequisite mastery above 0.70 satisfies readiness
      - High target topic mastery with unready/missing prerequisite does NOT falsely advance
    """
    db = EvidenceDB(tmp_path / "rec_prereq.sqlite")
    engine = AdaptiveRecommendationEngine(db)

    # Topic topology: Calculus requires Algebra
    db.add_concept("Algebra", "Algebra", topic_id="Algebra")
    db.add_concept("Calculus", "Calculus", topic_id="Calculus")
    db.link_concept_prerequisite("Calculus", "Algebra")

    # Case 1: Missing prerequisite mastery record
    # Learner has Calculus target topic, but NO Algebra record
    rec_missing = engine.recommend("learner_missing_prereq", active_topic_id="Calculus")
    assert rec_missing.recommended_action == "foundational_review"
    assert rec_missing.topic_id == "Algebra"
    assert rec_missing.difficulty == Difficulty.easy
    assert rec_missing.learner_state_evidence.get("prerequisite_recorded") is False
    assert rec_missing.learner_state_evidence.get("status") == "unverified_prerequisite"
    assert "no recorded mastery" in rec_missing.rationale

    # Case 2: Prerequisite mastery below 0.70 (e.g. 0.50)
    db.save_learner_mastery(TopicMasteryRecord(learner_id="learner_low_prereq", topic_id="Algebra", p_mastery=0.50, attempts=4, correct=2))
    db.save_learner_mastery(TopicMasteryRecord(learner_id="learner_low_prereq", topic_id="Calculus", p_mastery=0.60, attempts=3, correct=2))
    rec_low = engine.recommend("learner_low_prereq", active_topic_id="Calculus")
    assert rec_low.recommended_action == "foundational_review"
    assert rec_low.topic_id == "Algebra"
    assert rec_low.learner_state_evidence.get("prerequisite_recorded") is True
    assert rec_low.learner_state_evidence.get("prerequisite_mastery") == 0.50
    assert rec_low.learner_state_evidence.get("status") == "below_threshold"
    assert "requires reinforcement" in rec_low.rationale

    # Case 3: Prerequisite mastery exactly 0.70 (Prerequisite satisfied)
    db.save_learner_mastery(TopicMasteryRecord(learner_id="learner_exact_70", topic_id="Algebra", p_mastery=0.70, attempts=6, correct=4))
    db.save_learner_mastery(TopicMasteryRecord(learner_id="learner_exact_70", topic_id="Calculus", p_mastery=0.60, attempts=3, correct=2))
    rec_exact70 = engine.recommend("learner_exact_70", active_topic_id="Calculus")
    # Should proceed to recommend for Calculus (0.60 in [0.40, 0.70) -> targeted_practice)
    assert rec_exact70.topic_id == "Calculus"
    assert rec_exact70.recommended_action == "targeted_practice"
    assert rec_exact70.difficulty == Difficulty.medium

    # Case 4: Prerequisite mastery above 0.70 (e.g. 0.82)
    db.save_learner_mastery(TopicMasteryRecord(learner_id="learner_high_prereq", topic_id="Algebra", p_mastery=0.82, attempts=8, correct=7))
    db.save_learner_mastery(TopicMasteryRecord(learner_id="learner_high_prereq", topic_id="Calculus", p_mastery=0.75, attempts=6, correct=5))
    rec_high = engine.recommend("learner_high_prereq", active_topic_id="Calculus")
    # Should proceed to recommend for Calculus (0.75 in [0.70, 0.85] -> mixed_application)
    assert rec_high.topic_id == "Calculus"
    assert rec_high.recommended_action == "mixed_application"
    assert rec_high.difficulty == Difficulty.medium

    # Case 5: Target topic has high mastery (0.92), but prerequisite is NOT ready (0.45)
    # Must block advancement and recommend foundational review on Algebra
    db.save_learner_mastery(TopicMasteryRecord(learner_id="learner_inverted", topic_id="Algebra", p_mastery=0.45, attempts=4, correct=1))
    db.save_learner_mastery(TopicMasteryRecord(learner_id="learner_inverted", topic_id="Calculus", p_mastery=0.92, attempts=10, correct=9))
    rec_inv = engine.recommend("learner_inverted", active_topic_id="Calculus")
    assert rec_inv.recommended_action == "foundational_review"
    assert rec_inv.topic_id == "Algebra"
    assert rec_inv.difficulty == Difficulty.easy
    assert "requires reinforcement" in rec_inv.rationale
    assert rec_inv.learner_state_evidence.get("prerequisite_mastery") == 0.45

def test_recommendation_active_misconception_priority(tmp_path):
    db = EvidenceDB(tmp_path / "rec_misc.sqlite")
    engine = AdaptiveRecommendationEngine(db)

    # Set topic mastery to 0.60
    db.save_learner_mastery(TopicMasteryRecord(learner_id="u5", topic_id="Vectors", p_mastery=0.60, attempts=4, correct=2))

    # Add active misconception
    db.add_misconception(
        MisconceptionSignal(
            signal_id="sig_u5",
            learner_id="u5",
            topic_id="Vectors",
            concept_id="Dot Product",
            suspected_misconception="Confusing dot product with cross product",
            error_count=2,
            confidence=0.85,
            remediation_concept_id="Scalar Projection",
            remediation_evidence_ids=["ev_vec_01"]
        )
    )

    rec = engine.recommend("u5", active_topic_id="Vectors")
    assert rec.recommended_action == "remediate_misconception"
    assert rec.concept_id == "Scalar Projection"
    assert "Confusing dot product" in rec.rationale
    assert "ev_vec_01" in rec.suggested_evidence_ids
