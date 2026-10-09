import pytest
from app.db import EvidenceDB
from app.learner_model import BKTModel, LearnerStateManager
from app.models import BKTParams

def test_bkt_posterior_and_transition_math():
    # Parameters: p_init=0.10, p_transit=0.15, p_slip=0.10, p_guess=0.20
    params = BKTParams(p_init=0.10, p_transit=0.15, p_slip=0.10, p_guess=0.20)
    bkt = BKTModel(params)

    # 1. Correct observation
    # P(L_0 | correct) = (0.10 * 0.90) / (0.10 * 0.90 + 0.90 * 0.20) = 0.09 / (0.09 + 0.18) = 0.09 / 0.27 = 1/3 ~ 0.333333
    # P(L_1) = (1/3) + (1 - 1/3) * 0.15 = 0.333333 + 0.666667 * 0.15 = 0.333333 + 0.10 = 0.433333
    p_step1_corr = bkt.step(0.10, is_correct=True)
    assert abs(p_step1_corr - 0.433333) < 1e-4

    # 2. Incorrect observation
    # P(L_0 | incorrect) = (0.10 * 0.10) / (0.10 * 0.10 + 0.90 * 0.80) = 0.01 / (0.01 + 0.72) = 0.01 / 0.73 ~ 0.0136986
    # P(L_1) = 0.0136986 + (1 - 0.0136986) * 0.15 = 0.0136986 + 0.147945 ~ 0.161644
    p_step1_inc = bkt.step(0.10, is_correct=False)
    assert abs(p_step1_inc - 0.161644) < 1e-4

def test_bkt_repeated_updates_monotonicity():
    bkt = BKTModel()
    p = 0.10
    # Consecutive correct answers should strictly increase mastery
    for _ in range(5):
        p_next = bkt.step(p, is_correct=True)
        assert p_next > p
        p = p_next
    assert p > 0.80

def test_bkt_profile_divergence(tmp_path):
    db = EvidenceDB(tmp_path / "bkt_div.sqlite")
    manager = LearnerStateManager(db)

    # Learner A gets 4 correct answers in Algebra
    for _ in range(4):
        manager.record_response("learner_A", "Algebra", is_correct=True)

    # Learner B gets 4 incorrect answers in Algebra
    for _ in range(4):
        manager.record_response("learner_B", "Algebra", is_correct=False)

    prof_A = manager.get_or_create_mastery("learner_A", "Algebra")
    prof_B = manager.get_or_create_mastery("learner_B", "Algebra")

    assert prof_A.p_mastery > prof_B.p_mastery
    assert prof_A.p_mastery > 0.70
    assert prof_B.p_mastery < 0.40
    assert prof_A.correct == 4
    assert prof_B.correct == 0

def test_bkt_persistence(tmp_path):
    db_file = tmp_path / "bkt_persist.sqlite"
    db1 = EvidenceDB(db_file)
    mgr1 = LearnerStateManager(db1)
    mgr1.record_response("student_42", "Trigonometry", is_correct=True)
    rec1 = mgr1.get_or_create_mastery("student_42", "Trigonometry")

    # Reload from independent database instance
    db2 = EvidenceDB(db_file)
    mgr2 = LearnerStateManager(db2)
    rec2 = mgr2.get_or_create_mastery("student_42", "Trigonometry")

    assert rec2.learner_id == "student_42"
    assert rec2.topic_id == "Trigonometry"
    assert rec2.attempts == 1
    assert rec2.correct == 1
    assert abs(rec2.p_mastery - rec1.p_mastery) < 1e-6
