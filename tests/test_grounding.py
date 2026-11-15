import pytest

from app.grounding import verify_generated
from app.llm import LLM, LLMError
from app.models import PUBLIC_OWNER

from .conftest import make_service

SUPPORTED = [
    ("What is Newton's second law?", "Page 1"),
    ("How is kinetic energy calculated?", "Page 3"),
    ("What is the powerhouse of the cell?", "00:02:50"),
    ("Explain Snell's law", "Slide 4"),
    ("What does the discriminant tell us?", "Page 1"),
    ("What is the chain rule?", "Page 2"),
]
UNSUPPORTED = [
    "What is Newton's fourth law?",
    "Who won the 1994 World Cup?",
    "What is the capital of France?",
    "Explain the economic causes of the French Revolution",
    "hello",
]


@pytest.mark.parametrize("q,locator", SUPPORTED)
def test_supported_questions_are_answered_with_correct_locator(seeded, q, locator):
    r = seeded.ask(PUBLIC_OWNER, q)
    assert r.support_status == "supported"
    assert r.citations and r.citations[0].locator_label == locator
    assert "[1]" in r.answer


@pytest.mark.parametrize("q", UNSUPPORTED)
def test_off_material_questions_abstain(seeded, q):
    r = seeded.ask(PUBLIC_OWNER, q)
    assert r.support_status == "unsupported" and not r.citations and r.confidence == 0


def test_every_citation_resolves_to_stored_evidence(seeded):
    for q, _ in SUPPORTED:
        for c in seeded.ask(PUBLIC_OWNER, q).citations:
            unit = seeded.db.get_evidence(c.evidence_id)
            assert unit is not None and unit.location == c.location


def test_answer_sentences_come_from_the_cited_passage(seeded):
    r = seeded.ask(PUBLIC_OWNER, "What is inertia?")
    cited = " ".join(c.snippet for c in r.citations)
    for sentence in r.answer.replace("[1]", "").split(". "):
        assert sentence.strip(" .") in cited


def test_follow_up_uses_previous_question(seeded):
    r = seeded.ask(PUBLIC_OWNER, "what are its units?", history=["How do I calculate kinetic energy?"])
    assert r.support_status == "supported" and "joules" in r.answer


def test_partial_coverage_is_flagged(seeded):
    r = seeded.ask(PUBLIC_OWNER, "How much kinetic energy does a cheetah have?")
    assert r.support_status in {"partial", "unsupported"}
    if r.support_status == "partial":
        assert "cheetah" in r.answer


class FakeLLM(LLM):
    name = "fake"

    def __init__(self, reply):
        self.reply = reply

    @property
    def available(self):
        return True

    def generate(self, prompt, system="", temperature=0.2, max_tokens=700):
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def test_generated_answer_keeps_only_supported_sentences(seeded):
    idx = seeded.retriever.index(PUBLIC_OWNER)
    hits = seeded.retriever.search("What is inertia?", PUBLIC_OWNER)
    ev = [h.unit for h in hits]
    good = "Inertia is the tendency of an object to resist changes in its state of motion [1]."
    bad = "Inertia was discovered by Galileo in 1638 using telescopes [1]."
    uncited = "Inertia is important."
    text, used, faith, n = verify_generated(f"{good} {bad} {uncited}", ev, idx)
    assert good.replace(" [1]", "")[:40] in text and "Galileo" not in text and "important" not in text
    assert faith == pytest.approx(1 / 3)


def test_model_answer_falls_back_when_verification_fails():
    svc = make_service(llm=FakeLLM("The Moon is made of cheese and was measured in 1969 [1]. Cats rule the world [2]."))
    r = svc.ask(PUBLIC_OWNER, "What is inertia?")
    assert r.generator == "extractive" and "cheese" not in r.answer
    assert any("failed verification" in s for s in r.reasoning_steps)


def test_model_answer_is_used_when_supported():
    reply = "Inertia is the tendency of an object to resist changes in its state of motion [1]. Objects with more mass have more inertia [1]."
    svc = make_service(llm=FakeLLM(reply))
    r = svc.ask(PUBLIC_OWNER, "What is inertia?")
    assert r.generator == "fake" and r.metadata["faithfulness"] == 1.0


def test_model_outage_degrades_to_extractive():
    svc = make_service(llm=FakeLLM(LLMError("down")))
    r = svc.ask(PUBLIC_OWNER, "What is inertia?")
    assert r.support_status == "supported" and r.generator == "extractive"


def test_general_knowledge_is_labelled_when_requested():
    svc = make_service(llm=FakeLLM("Paris is the capital of France."))
    r = svc.ask(PUBLIC_OWNER, "What is the capital of France?", allow_general=True)
    assert r.support_status == "unsupported" and "not verified" in r.answer and r.metadata.get("general_knowledge")
