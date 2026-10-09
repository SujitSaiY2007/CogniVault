import math
import pytest
from app.assessment import (
    AssessmentEngine,
    DeterministicQuestionVerifier,
    compute_question_fingerprint,
    parse_numerical_value,
)
from app.db import EvidenceDB
from app.models import (
    Difficulty,
    EvidenceUnit,
    LearnerSubmission,
    Modality,
    Question,
    QuestionOption,
    QuestionType,
    SourceRecord,
)

def test_parse_numerical_value():
    # Valid numeric representations
    assert parse_numerical_value("42") == 42.0
    assert parse_numerical_value("3.14159") == 3.14159
    assert parse_numerical_value("-15.5") == -15.5
    assert parse_numerical_value("+12.0") == 12.0
    assert parse_numerical_value("1.5e3") == 1500.0
    assert parse_numerical_value("-2.5e-2") == -0.025
    assert parse_numerical_value("  100.25  ") == 100.25
    assert parse_numerical_value("1,000.5") == 1000.5
    assert parse_numerical_value("1,234,567.89") == 1234567.89
    assert parse_numerical_value(42) == 42.0
    assert parse_numerical_value(-7.8) == -7.8

    # Malformed & invalid inputs
    assert parse_numerical_value("abc") is None
    assert parse_numerical_value("12.3.4") is None
    assert parse_numerical_value("1.2e") is None
    assert parse_numerical_value("42 meters") is None
    assert parse_numerical_value("--5") is None
    assert parse_numerical_value("") is None
    assert parse_numerical_value("   ") is None
    assert parse_numerical_value(None) is None
    assert parse_numerical_value("nan") is None
    assert parse_numerical_value("NaN") is None
    assert parse_numerical_value("inf") is None
    assert parse_numerical_value("-inf") is None
    assert parse_numerical_value("infinity") is None

def test_question_verifier_valid_mcq(tmp_path):
    db = EvidenceDB(tmp_path / "assess.sqlite")
    db.add_source(SourceRecord(source_id="s1", path="p.pdf", modality=Modality.pdf, title="P", sha256="h"))
    db.add_evidence(EvidenceUnit(evidence_id="s1:e00001", source_id="s1", modality=Modality.pdf, text="F=ma is Newton second law.", location={"page": 1}))

    verifier = DeterministicQuestionVerifier()
    q = Question(
        question_id="q1",
        topic_id="Newtonian Mechanics",
        concept_id="Second Law",
        evidence_ids=["s1:e00001"],
        difficulty=Difficulty.medium,
        question_type=QuestionType.mcq,
        prompt="What equation represents Newton's Second Law of Motion?",
        options=[
            QuestionOption(key="A", text="F = m * a"),
            QuestionOption(key="B", text="E = m * c^2"),
            QuestionOption(key="C", text="v = u + a * t"),
            QuestionOption(key="D", text="p = m * v")
        ],
        expected_answer="A",
        solution="Newton's second law is defined by Force = mass * acceleration."
    )

    res = verifier.verify(q, db=db)
    assert res.is_valid
    assert len(res.failure_reasons) == 0
    assert res.scope == "structural_integrity"

def test_question_verifier_rejects_invalid_answer_key(tmp_path):
    db = EvidenceDB(tmp_path / "assess2.sqlite")
    db.add_source(SourceRecord(source_id="s1", path="p.pdf", modality=Modality.pdf, title="P", sha256="h"))
    db.add_evidence(EvidenceUnit(evidence_id="s1:e00001", source_id="s1", modality=Modality.pdf, text="Sample text", location={"page": 1}))

    verifier = DeterministicQuestionVerifier()
    # Intentionally invalid expected answer "Z" not in options
    q = Question(
        question_id="q_invalid",
        topic_id="Mechanics",
        evidence_ids=["s1:e00001"],
        question_type=QuestionType.mcq,
        prompt="What is the unit of force in SI units?",
        options=[
            QuestionOption(key="A", text="Newton"),
            QuestionOption(key="B", text="Joule")
        ],
        expected_answer="Z"  # Nonexistent option
    )

    res = verifier.verify(q, db=db)
    assert not res.is_valid
    assert any("does not match any valid option key" in r for r in res.failure_reasons)

def test_question_verifier_rejects_duplicate_mcq_options(tmp_path):
    db = EvidenceDB(tmp_path / "assess_dup.sqlite")
    db.add_source(SourceRecord(source_id="s1", path="p.pdf", modality=Modality.pdf, title="P", sha256="h"))
    db.add_evidence(EvidenceUnit(evidence_id="s1:e00001", source_id="s1", modality=Modality.pdf, text="Sample text", location={"page": 1}))

    verifier = DeterministicQuestionVerifier()
    # Duplicate option keys
    q_dup_key = Question(
        question_id="q_dup_key",
        topic_id="Physics",
        evidence_ids=["s1:e00001"],
        question_type=QuestionType.mcq,
        prompt="Sample question with duplicate option keys?",
        options=[
            QuestionOption(key="A", text="First choice"),
            QuestionOption(key="A", text="Second choice")
        ],
        expected_answer="A"
    )
    res1 = verifier.verify(q_dup_key, db=db)
    assert not res1.is_valid
    assert any("Duplicate option keys" in r for r in res1.failure_reasons)

    # Duplicate option texts
    q_dup_text = Question(
        question_id="q_dup_text",
        topic_id="Physics",
        evidence_ids=["s1:e00001"],
        question_type=QuestionType.mcq,
        prompt="Sample question with duplicate option text?",
        options=[
            QuestionOption(key="A", text="Identical Text"),
            QuestionOption(key="B", text="Identical Text")
        ],
        expected_answer="A"
    )
    res2 = verifier.verify(q_dup_text, db=db)
    assert not res2.is_valid
    assert any("Duplicate option texts" in r for r in res2.failure_reasons)

def test_question_verifier_rejects_missing_evidence(tmp_path):
    db = EvidenceDB(tmp_path / "assess3.sqlite")
    verifier = DeterministicQuestionVerifier()
    q = Question(
        question_id="q_no_ev",
        topic_id="Math",
        evidence_ids=["phantom_evidence_id"],
        question_type=QuestionType.numerical,
        prompt="Calculate the derivative of x^2 at x=3.",
        expected_answer="6.0"
    )
    res = verifier.verify(q, db=db)
    assert not res.is_valid
    assert any("do not exist in database" in r for r in res.failure_reasons)

def test_numerical_question_verification_and_tolerance(tmp_path):
    db = EvidenceDB(tmp_path / "assess_num.sqlite")
    db.add_source(SourceRecord(source_id="s1", path="p.pdf", modality=Modality.pdf, title="P", sha256="h"))
    db.add_evidence(EvidenceUnit(evidence_id="s1:e00001", source_id="s1", modality=Modality.pdf, text="Speed of sound is 343 m/s.", location={"page": 1}))

    verifier = DeterministicQuestionVerifier()

    # 1. Valid numerical question with scientific notation and positive tolerance
    q_valid = Question(
        question_id="q_valid_num",
        topic_id="Physics",
        evidence_ids=["s1:e00001"],
        question_type=QuestionType.numerical,
        prompt="What is the speed of light in vacuum in m/s (scientific notation)?",
        expected_answer="3.0e8",
        tolerance=1.0e6
    )
    res_valid = verifier.verify(q_valid, db=db)
    assert res_valid.is_valid

    # 2. Negative tolerance rejection
    q_neg_tol = Question(
        question_id="q_neg_tol",
        topic_id="Physics",
        evidence_ids=["s1:e00001"],
        question_type=QuestionType.numerical,
        prompt="What is the acceleration due to gravity on Earth in m/s^2?",
        expected_answer="9.81",
        tolerance=-0.1
    )
    res_neg_tol = verifier.verify(q_neg_tol, db=db)
    assert not res_neg_tol.is_valid
    assert any("tolerance cannot be negative" in r for r in res_neg_tol.failure_reasons)

    # 3. Malformed expected answer rejection
    q_malformed = Question(
        question_id="q_malformed",
        topic_id="Physics",
        evidence_ids=["s1:e00001"],
        question_type=QuestionType.numerical,
        prompt="What is the value of pi?",
        expected_answer="3.14.15abc"
    )
    res_malformed = verifier.verify(q_malformed, db=db)
    assert not res_malformed.is_valid
    assert any("not a valid parseable finite number" in r for r in res_malformed.failure_reasons)

def test_numerical_submission_evaluation(tmp_path):
    db = EvidenceDB(tmp_path / "assess_eval.sqlite")
    db.add_source(SourceRecord(source_id="s1", path="p.pdf", modality=Modality.pdf, title="P", sha256="h"))
    db.add_evidence(EvidenceUnit(evidence_id="s1:e00001", source_id="s1", modality=Modality.pdf, text="Gravitational acceleration is 9.81 m/s^2.", location={"page": 1}))

    engine = AssessmentEngine(db)
    q = engine.build_and_verify_question(
        question_id="q_num_eval",
        topic_id="Physics",
        prompt="What is the standard acceleration due to gravity on Earth in m/s^2?",
        expected_answer="9.81",
        evidence_ids=["s1:e00001"],
        question_type=QuestionType.numerical,
        tolerance=0.05
    )

    # Correct within tolerance
    sub1 = LearnerSubmission(learner_id="u1", question_id="q_num_eval", topic_id="Physics", answer="9.83")
    eval1 = engine.evaluate_submission(sub1, q)
    assert eval1.is_correct
    assert eval1.status == "correct"

    # Scientific notation answer
    sub2 = LearnerSubmission(learner_id="u2", question_id="q_num_eval", topic_id="Physics", answer="9.81e0")
    eval2 = engine.evaluate_submission(sub2, q)
    assert eval2.is_correct

    # Outside tolerance
    sub3 = LearnerSubmission(learner_id="u3", question_id="q_num_eval", topic_id="Physics", answer="9.90")
    eval3 = engine.evaluate_submission(sub3, q)
    assert not eval3.is_correct
    assert eval3.status == "incorrect"

    # Malformed submission input (should fail cleanly without exception)
    sub4 = LearnerSubmission(learner_id="u4", question_id="q_num_eval", topic_id="Physics", answer="nine point eight")
    eval4 = engine.evaluate_submission(sub4, q)
    assert not eval4.is_correct
    assert eval4.status == "incorrect"

def test_repetition_suppression_and_adaptive_selection(tmp_path):
    db = EvidenceDB(tmp_path / "assess4.sqlite")
    db.add_source(SourceRecord(source_id="s1", path="p.pdf", modality=Modality.pdf, title="P", sha256="h"))
    db.add_evidence(EvidenceUnit(evidence_id="s1:e00001", source_id="s1", modality=Modality.pdf, text="Calculus limits and derivatives.", location={"page": 1}))

    engine = AssessmentEngine(db)

    # Add 2 questions for topic "Calculus"
    q1 = engine.build_and_verify_question(
        question_id="q_calc_01",
        topic_id="Calculus",
        prompt="What is the derivative of sin(x)?",
        expected_answer="A",
        evidence_ids=["s1:e00001"],
        difficulty=Difficulty.easy,
        options=[QuestionOption(key="A", text="cos(x)"), QuestionOption(key="B", text="-cos(x)")]
    )
    q2 = engine.build_and_verify_question(
        question_id="q_calc_02",
        topic_id="Calculus",
        prompt="What is the integral of 1/x dx?",
        expected_answer="A",
        evidence_ids=["s1:e00001"],
        difficulty=Difficulty.medium,
        options=[QuestionOption(key="A", text="ln|x| + C"), QuestionOption(key="B", text="e^x + C")]
    )

    assert q1.verification_status == "verified"
    assert q2.verification_status == "verified"

    # Select first question:
    selected1 = engine.select_adaptive_question("Calculus", served_question_ids=[])
    assert selected1 is not None
    assert selected1.question_id == "q_calc_01"

    # Next session with q_calc_01 already served: should suppress q_calc_01 and select q_calc_02
    selected2 = engine.select_adaptive_question("Calculus", served_question_ids=["q_calc_01"])
    assert selected2 is not None
    assert selected2.question_id == "q_calc_02"

def test_corrective_feedback_with_citations(tmp_path):
    db = EvidenceDB(tmp_path / "assess5.sqlite")
    db.add_source(SourceRecord(source_id="phy_book", path="phy.pdf", modality=Modality.pdf, title="Physics Book", sha256="h1"))
    db.add_evidence(
        EvidenceUnit(
            evidence_id="phy_book:e00001",
            source_id="phy_book",
            modality=Modality.pdf,
            text="Work is defined as Force multiplied by displacement in the direction of force: W = F * d.",
            location={"page": 15},
            topics=["Physics", "Work and Energy"]
        )
    )

    engine = AssessmentEngine(db)
    q = engine.build_and_verify_question(
        question_id="q_work_01",
        topic_id="Work and Energy",
        prompt="What is the formula for mechanical work?",
        expected_answer="A",
        evidence_ids=["phy_book:e00001"],
        options=[
            QuestionOption(key="A", text="W = F * d"),
            QuestionOption(key="B", text="W = m * g")
        ],
        solution="Work equals force times displacement (W = F * d)."
    )

    # Submit wrong answer "B"
    sub = LearnerSubmission(learner_id="learner_001", question_id="q_work_01", topic_id="Work and Energy", answer="B")
    eval_res = engine.evaluate_submission(sub, q)

    assert not eval_res.is_correct
    assert eval_res.status == "incorrect"
    assert "Page 15" in eval_res.feedback
    assert len(eval_res.citations) == 1
    assert eval_res.citations[0].evidence_id == "phy_book:e00001"
    assert eval_res.remediation_action == "review_topic:Work and Energy"
