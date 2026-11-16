from datetime import datetime, timedelta, timezone

import pytest

from app.learner import CHAT_CAP, LearnerModel, bkt_update, decayed
from app.models import PUBLIC_OWNER, Difficulty, Question, QuestionOption, QuestionType, TopicMasteryRecord
from app.questions import FormulaError, evaluate, grade, parse_expr, verify
from app.study import sm2, study_plan


# ---------------------------------------------------------------- formulas
def test_formula_parser_rejects_code():
    for bad in ["__import__('os')", "a.b", "open('x')", "4ac", "x if y else z"]:
        with pytest.raises(FormulaError):
            parse_expr(bad)
    assert evaluate(parse_expr("0.5 * m * v^2"), {"m": 4, "v": 3}) == 18


def test_generated_numerical_answers_are_correct(seeded):
    qs = [q for q in seeded.db.questions(PUBLIC_OWNER) if q.question_type == QuestionType.numerical]
    assert len(qs) >= 8 and any(q.metadata["generator"] == "formula-inverse" for q in qs)
    for q in qs:
        lhs, rhs = q.metadata["formula"].split("=", 1)
        if q.metadata["generator"] == "formula-forward":
            # recompute from the givens stated in the prompt
            import re

            env = {m.group(1): float(m.group(2)) for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*) = ([-\d.]+)", q.prompt.split("when", 1)[1])}
            assert abs(evaluate(parse_expr(rhs), env) - float(q.expected_answer)) <= q.tolerance


def test_bank_is_verified_linked_and_duplicate_free(seeded):
    qs = seeded.db.questions(PUBLIC_OWNER, verified_only=False)
    assert len(qs) >= 60
    ids = {u.evidence_id for u in seeded.db.evidence_for_owner(PUBLIC_OWNER)}
    assert all(q.verification_status == "verified" for q in qs)
    assert all(set(q.evidence_ids) <= ids for q in qs)
    assert len({q.fingerprint for q in qs}) == len(qs)
    for q in qs:
        if q.question_type == QuestionType.mcq:
            assert q.expected_answer in [o.key for o in q.options]
            assert len({o.text for o in q.options}) == len(q.options)


def test_public_view_hides_answer_key(seeded):
    q = seeded.db.questions(PUBLIC_OWNER)[0]
    pub = q.public()
    assert pub["expected_answer"] == "" and pub["solution"] == "" and "distractor_concepts" not in pub["metadata"]


def test_verifier_rejects_broken_items():
    q = Question(question_id="x", topic_id="t", evidence_ids=["e1"], prompt="Pick one of these options now", expected_answer="Z",
                 options=[QuestionOption(key="A", text="a"), QuestionOption(key="B", text="a")])
    fails = verify(q, {"e1"})
    assert "duplicate options" in fails and "answer key does not match an option" in fails and "fewer than 3 options" in fails
    assert "evidence link missing or unresolvable" in verify(q.model_copy(update={"evidence_ids": ["nope"]}), {"e1"})


# ----------------------------------------------------------------- grading
def _mcq():
    return Question(question_id="m", topic_id="t", prompt="Which is right here?", expected_answer="B", concept_id="Heat",
                    options=[QuestionOption(key="A", text="cold"), QuestionOption(key="B", text="warm"), QuestionOption(key="C", text="hot")],
                    metadata={"distractor_concepts": {"A": "Temperature", "C": "Entropy"}})


def test_grading_mcq_by_key_or_text_and_diagnoses_confusion():
    assert grade(_mcq(), "b").is_correct and grade(_mcq(), "warm").is_correct
    g = grade(_mcq(), "A")
    assert not g.is_correct and g.pattern == "confused_with:Temperature"


def test_grading_numerical_tolerance_and_error_patterns():
    q = Question(question_id="n", topic_id="t", prompt="Compute the value now", question_type=QuestionType.numerical, expected_answer="18", tolerance=0.18)
    assert grade(q, "18.1 J").is_correct and grade(q, "1.8e1").is_correct
    assert grade(q, "-18").pattern == "sign_error"
    assert grade(q, "180").pattern == "power_of_ten"
    assert grade(q, "18.6").status == "partially_correct"
    assert grade(q, "abc").pattern == "not_a_number"


def test_grading_cloze_accepts_minor_typos():
    q = Question(question_id="c", topic_id="t", prompt="Fill in the blank: ____", question_type=QuestionType.short_answer, expected_answer="mitochondria")
    assert grade(q, "Mitochondria").is_correct and grade(q, "mitochondira").is_correct
    assert not grade(q, "nucleus").is_correct


# --------------------------------------------------------------------- BKT
def test_bkt_matches_closed_form():
    p, g, s, t = 0.3, 0.25, 0.1, 0.15
    prior = p + (1 - p) * t
    expected = prior * (1 - s) / (prior * (1 - s) + (1 - prior) * g)
    assert bkt_update(p, 1.0, g, s, t) == pytest.approx(expected, abs=1e-6)


def test_mastery_rises_on_correct_and_falls_on_wrong(fresh):
    m = LearnerModel(fresh.db)
    q = fresh.db.questions(PUBLIC_OWNER)[0]
    before, rec = m.observe("u1", q, 1.0)
    assert rec.p_mastery > before
    before2, rec2 = m.observe("u1", q, 0.0)
    assert rec2.p_mastery < before2


def test_forgetting_decays_toward_floor_slower_with_practice():
    old = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    a = TopicMasteryRecord(learner_id="u", topic_id="t", p_mastery=0.9, correct=1, last_seen=old)
    b = a.model_copy(update={"correct": 6})
    assert 0.1 < decayed(a) < decayed(b) < 0.9


def test_chat_alone_cannot_create_mastery(fresh):
    m = LearnerModel(fresh.db)
    tid = fresh.db.topics(PUBLIC_OWNER)[0].topic_id
    for _ in range(50):
        rec = m.observe_instruction("u2", tid)
    assert rec.p_mastery <= CHAT_CAP


def test_misconception_needs_two_errors_and_clears_after_two_correct(fresh):
    m = LearnerModel(fresh.db)
    q = next(x for x in fresh.db.questions(PUBLIC_OWNER) if x.question_type == QuestionType.mcq and x.concept_id)
    assert m.record_error("u3", q, "wrong_option") is None
    sig = m.record_error("u3", q, "wrong_option")
    assert sig is not None and sig.error_count == 2 and sig.remediation_evidence_ids
    for _ in range(2):
        m.observe("u3", q, 1.0)
        m.record_success("u3", q)
    assert fresh.db.active_misconceptions("u3") == []


def test_recommendation_enforces_prerequisites(fresh):
    m = LearnerModel(fresh.db)
    topics = fresh.db.topics(PUBLIC_OWNER)
    target = next(t for t in topics if t.name == "Linear Momentum")
    rec = m.recommend("u4", topics, target.topic_id)
    assert rec.recommended_action == "foundational_review" and rec.topic_name == "Newton's Second Law"


def test_question_selection_avoids_repeats(fresh):
    tid = next(t.topic_id for t in fresh.db.topics(PUBLIC_OWNER) if len(fresh.db.questions(PUBLIC_OWNER, t.topic_id)) >= 4)
    seen = set()
    for _ in range(4):
        q = fresh.next_question("u5", tid)
        assert q.question_id not in seen
        seen.add(q.question_id)
        fresh.submit("u5", q.question_id, "A")


# ------------------------------------------------------------------- study
def test_sm2_schedule():
    e, i, r = sm2(2.5, 0, 0, 5)
    assert (i, r) == (1.0, 1)
    e, i, r = sm2(e, i, r, 4)
    assert i == 6.0
    e2, i2, r2 = sm2(e, i, r, 1)
    assert i2 == 1.0 and r2 == 0


def test_study_plan_warns_when_time_is_too_short(fresh):
    m = LearnerModel(fresh.db)
    plan = study_plan(m, "u6", fresh.db.topics(PUBLIC_OWNER), (datetime.now(timezone.utc).date() + timedelta(days=2)).isoformat(), 20)
    assert plan["warning"] and plan["blocks_needed"] > plan["blocks_available"]
    long = study_plan(m, "u6", fresh.db.topics(PUBLIC_OWNER), (datetime.now(timezone.utc).date() + timedelta(days=30)).isoformat(), 120)
    assert long["warning"] is None and long["plan"][-1]["blocks"][-1]["kind"] == "exam"


def test_short_plan_gives_every_topic_a_share(fresh):
    m = LearnerModel(fresh.db)
    topics = fresh.db.topics(PUBLIC_OWNER)
    plan = study_plan(m, "u7", topics, (datetime.now(timezone.utc).date() + timedelta(days=8)).isoformat(), 60)
    assert plan["warning"]
    covered = {b["topic_id"] for day in plan["plan"] for b in day["blocks"] if b["topic_id"]}
    assert len(covered) == len(topics) and plan["topics_covered"] == len(topics)
    assert sum(1 for day in plan["plan"] for b in day["blocks"] if b["kind"] == "practice") <= plan["blocks_available"]


def test_plan_for_empty_course_is_flagged_empty(fresh):
    m = LearnerModel(fresh.db)
    plan = study_plan(m, "u8", [], None, 60)
    assert plan["empty"] is True and plan["topics_covered"] == 0
