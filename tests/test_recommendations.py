import pytest
from app.db import EvidenceDB
from app.models import Difficulty, MisconceptionSignal, TopicMasteryRecord
from app.recommendation import AdaptiveRecommendationEngine

def test_recommendation_mastery_brackets(tmp_path):
    db = EvidenceDB(tmp_path / "rec.sqlite")
    engine = AdaptiveRecommendationEngine(db)

    # 1. Low mastery (< 0.40) -> foundational_review, easy
    db.save_learner_mastery(TopicMasteryRecord(learner_id="u1", topic_id="Algebra", p_mastery=0.25, attempts=2, correct=0))
    rec1 = engine.recommend("u1", active_topic_id="Algebra")
    assert rec1.recommended_action == "foundational_review"
    assert rec1.difficulty == Difficulty.easy

    # 2. Medium mastery (0.40 <= p < 0.70) -> targeted_practice, medium
    db.save_learner_mastery(TopicMasteryRecord(learner_id="u2", topic_id="Geometry", p_mastery=0.55, attempts=5, correct=3))
    rec2 = engine.recommend("u2", active_topic_id="Geometry")
    assert rec2.recommended_action == "targeted_practice"
    assert rec2.difficulty == Difficulty.medium

    # 3. High mastery (0.70 <= p < 0.85) -> mixed_application, medium
    db.save_learner_mastery(TopicMasteryRecord(learner_id="u3", topic_id="Calculus", p_mastery=0.78, attempts=8, correct=6))
    rec3 = engine.recommend("u3", active_topic_id="Calculus")
    assert rec3.recommended_action == "mixed_application"
    assert rec3.difficulty == Difficulty.medium

    # 4. Mastered (p >= 0.85) -> advance_topic, hard
    db.save_learner_mastery(TopicMasteryRecord(learner_id="u4", topic_id="Physics", p_mastery=0.92, attempts=10, correct=9))
    rec4 = engine.recommend("u4", active_topic_id="Physics")
    assert rec4.recommended_action == "advance_topic"
    assert rec4.difficulty == Difficulty.hard

    # Exact boundary condition tests: 0.40, 0.70, 0.85
    # Boundary at 0.40 -> enters [0.40, 0.70) -> targeted_practice
    db.save_learner_mastery(TopicMasteryRecord(learner_id="b40", topic_id="Algebra", p_mastery=0.40, attempts=3, correct=1))
    rec_b40 = engine.recommend("b40", active_topic_id="Algebra")
    assert rec_b40.recommended_action == "targeted_practice"
    assert rec_b40.difficulty == Difficulty.medium

    # Boundary at 0.70 -> enters [0.70, 0.85) -> mixed_application
    db.save_learner_mastery(TopicMasteryRecord(learner_id="b70", topic_id="Geometry", p_mastery=0.70, attempts=6, correct=4))
    rec_b70 = engine.recommend("b70", active_topic_id="Geometry")
    assert rec_b70.recommended_action == "mixed_application"
    assert rec_b70.difficulty == Difficulty.medium

    # Boundary at 0.85 -> enters [0.85, 1.0] -> advance_topic
    db.save_learner_mastery(TopicMasteryRecord(learner_id="b85", topic_id="Calculus", p_mastery=0.85, attempts=9, correct=8))
    rec_b85 = engine.recommend("b85", active_topic_id="Calculus")
    assert rec_b85.recommended_action == "advance_topic"
    assert rec_b85.difficulty == Difficulty.hard


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
