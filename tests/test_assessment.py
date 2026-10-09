import pytest
from app.assessment import AssessmentEngine, DeterministicQuestionVerifier, compute_question_fingerprint
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

def test_repetition_suppression_and_adaptive_selection(tmp_path):
    db = EvidenceDB(tmp_path / "assess4.sqlite")
    db.add_source(SourceRecord(source_id="s1", path="p.pdf", modality=Modality.pdf, title="P", sha256="h"))
    db.add_evidence(EvidenceUnit(evidence_id="s1:e00001", source_id="s1", modality=Modality.pdf, text="Calculus limits and derivatives.", location={"page": 1}))

    engine = AssessmentEngine(db)

    # Add 3 questions for topic "Calculus"
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
