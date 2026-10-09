import base64
import hashlib
import numpy as np
import pytest
from pathlib import Path

import pymupdf
from pptx import Presentation

from app.assessment import AssessmentEngine, DeterministicQuestionVerifier
from app.db import EvidenceDB
from app.ingest import ingest_pdf, ingest_pptx, ingest_transcript
from app.learner_model import BKTModel, LearnerStateManager
from app.misconceptions import MisconceptionDetector
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
from app.recommendation import AdaptiveRecommendationEngine
from app.retrieval import HybridRetriever
from app.source_resolver import resolve
from app.sufficiency import EvidenceSufficiencyGate
from app.tutor import GroundedTutor

TINY_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)

# ---------------------------------------------------------------------------
# G1 — Grounding: Directly Supported Course Query
# ---------------------------------------------------------------------------
def test_g1_directly_supported_grounding(tmp_path):
    """
    G1: Question explicitly answered by course material.
    Pass: correct answer with valid citation resolving to supporting evidence.
    """
    pdf_path = tmp_path / "math_book.pdf"
    doc = pymupdf.open()
    p = doc.new_page()
    p.insert_text((72, 72), "The Quadratic Formula for ax^2 + bx + c = 0 is x = (-b +- sqrt(b^2 - 4ac)) / (2a).")
    doc.save(pdf_path)
    doc.close()

    db = EvidenceDB(tmp_path / "g1.sqlite")
    sid = ingest_pdf(pdf_path, db, source_id="quad_text")

    tutor = GroundedTutor(db)
    response = tutor.answer("Quadratic Formula solution equation", mode="lexical")

    assert response.is_grounded
    assert response.support_status == "supported"
    assert "Quadratic Formula" in response.answer
    assert len(response.citations) >= 1

    top_cite = response.citations[0]
    assert top_cite.source_id == sid
    assert top_cite.location.get("page") == 1

    # Verify citation resolves to stored evidence
    resolved = resolve(top_cite.evidence_id, db)
    assert resolved is not None
    assert "Quadratic Formula" in resolved["text"]


# ---------------------------------------------------------------------------
# G2 — Grounding: Visual / Diagram Evidence
# ---------------------------------------------------------------------------
def test_g2_visual_diagram_grounding(tmp_path):
    """
    G2: Question requiring implemented figure/visual evidence.
    Pass: referenced visual evidence actually supports the answer.
    """
    pdf_path = tmp_path / "science_fig.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Figure 1.1: Schematic diagram of a plant cell chloroplast.")
    page.insert_image(pymupdf.Rect(72, 100, 200, 200), stream=TINY_PNG)
    doc.save(pdf_path)
    doc.close()

    db = EvidenceDB(tmp_path / "g2.sqlite")
    sid = ingest_pdf(pdf_path, db, source_id="cell_biology")

    # Verify image evidence was stored with Modality.image
    img_ev = next((e for e in db.all_evidence() if e.modality == Modality.image), None)
    assert img_ev is not None

    tutor = GroundedTutor(db)
    response = tutor.answer("plant cell chloroplast diagram", mode="lexical")

    assert response.is_grounded
    assert len(response.citations) >= 1
    # Check that image citation or parent page citation is present
    has_page_or_img = any(c.location.get("page") == 1 for c in response.citations)
    assert has_page_or_img


# ---------------------------------------------------------------------------
# G3 — Grounding: Video Transcript Timestamp
# ---------------------------------------------------------------------------
def test_g3_video_timestamp_grounding(tmp_path):
    """
    G3: Question whose evidence occurs in an ingested lecture segment.
    Pass: answer contains resolvable timestamp citation.
    """
    transcript_path = tmp_path / "lecture_physics.txt"
    transcript_path.write_text(
        "[01:45] Centripetal force acts towards the center of curvature: F_c = m*v^2/r.\n"
        "[03:20] Angular momentum is conserved when net torque is zero.\n",
        encoding="utf-8"
    )

    db = EvidenceDB(tmp_path / "g3.sqlite")
    sid = ingest_transcript(transcript_path, db, source_id="phys_lec_01")

    tutor = GroundedTutor(db)
    response = tutor.answer("centripetal force formula center curvature", mode="lexical")

    assert response.is_grounded
    assert response.support_status == "supported"
    assert len(response.citations) >= 1
    assert response.citations[0].location.get("timestamp") == "01:45"

    resolved = resolve(response.citations[0].evidence_id, db)
    assert resolved is not None
    assert resolved["location"]["timestamp"] == "01:45"


# ---------------------------------------------------------------------------
# G4 — Grounding: Cross-Source Synthesis
# ---------------------------------------------------------------------------
def test_g4_cross_source_synthesis_grounding(tmp_path):
    """
    G4: Question requiring two course sources (e.g. textbook + slide deck).
    Pass: synthesis answer with both supporting references.
    """
    # Source A: PDF
    pdf_path = tmp_path / "waves_book.pdf"
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Wave frequency f is the number of wave cycles passing a point per second.")
    doc.save(pdf_path)
    doc.close()

    # Source B: PPTX
    pptx_path = tmp_path / "waves_slides.pptx"
    prs = Presentation()
    slide = prs.slides.add_slide(prs.slide_layouts[1])
    slide.shapes.title.text = "Wave speed equation: v = f * lambda relates speed, frequency, and wavelength."
    prs.save(pptx_path)

    db = EvidenceDB(tmp_path / "g4.sqlite")
    pdf_sid = ingest_pdf(pdf_path, db, source_id="book_waves")
    pptx_sid = ingest_pptx(pptx_path, db, source_id="slides_waves")

    tutor = GroundedTutor(db)
    response = tutor.answer("wave frequency speed wavelength cycles", mode="lexical")

    assert response.is_grounded
    assert response.is_synthesis
    assert len(response.citations) >= 2

    source_ids = {c.source_id for c in response.citations}
    assert pdf_sid in source_ids
    assert pptx_sid in source_ids


# ---------------------------------------------------------------------------
# G5 — Grounding: Unsupported / Off-Material Abstention
# ---------------------------------------------------------------------------
def test_g5_unsupported_abstention(tmp_path):
    """
    G5: Question outside supplied course material.
    Pass: explicit abstention / unsupported state; no unsupported answer presented as course-grounded.
    """
    db = EvidenceDB(tmp_path / "g5.sqlite")
    db.add_source(SourceRecord(source_id="elem_math", path="math.txt", modality=Modality.text, title="Math", sha256="h1"))
    db.add_evidence(EvidenceUnit(evidence_id="elem_math:e00001", source_id="elem_math", modality=Modality.text, text="Basic arithmetic addition and subtraction of integers.", location={"page": 1}))

    tutor = GroundedTutor(db)
    # Off-material query
    response = tutor.answer("Superstring theory 11 dimensional Calabi-Yau manifolds", mode="lexical")

    assert not response.is_grounded
    assert response.support_status == "unsupported"
    assert len(response.citations) == 0
    assert "cannot answer" in response.answer.lower() or "not contain sufficient" in response.answer.lower()


# ---------------------------------------------------------------------------
# A1 — Assessment: Tagged Question Validity
# ---------------------------------------------------------------------------
def test_a1_tagged_question_metadata(tmp_path):
    """
    A1: Question has valid topic, difficulty, source evidence, and verification status.
    Pass: all required fields validate.
    """
    db = EvidenceDB(tmp_path / "a1.sqlite")
    db.add_source(SourceRecord(source_id="src1", path="bio.pdf", modality=Modality.pdf, title="Bio", sha256="h1"))
    db.add_evidence(EvidenceUnit(evidence_id="src1:e00001", source_id="src1", modality=Modality.pdf, text="DNA structure is a double helix discovered by Watson, Crick, and Franklin.", location={"page": 20}))

    engine = AssessmentEngine(db)
    q = engine.build_and_verify_question(
        question_id="q_bio_01",
        topic_id="Genetics",
        concept_id="DNA Structure",
        prompt="What geometric shape describes the structure of double-stranded DNA?",
        expected_answer="A",
        evidence_ids=["src1:e00001"],
        difficulty=Difficulty.easy,
        question_type=QuestionType.mcq,
        options=[
            QuestionOption(key="A", text="Double Helix"),
            QuestionOption(key="B", text="Triple Helix"),
            QuestionOption(key="C", text="Planar Ring"),
            QuestionOption(key="D", text="Beta Sheet")
        ],
        solution="DNA is structured as a double helix."
    )

    assert q.question_id == "q_bio_01"
    assert q.topic_id == "Genetics"
    assert q.concept_id == "DNA Structure"
    assert q.difficulty == Difficulty.easy
    assert q.evidence_ids == ["src1:e00001"]
    assert q.verification_status == "verified"
    assert len(q.options) == 4
    assert q.fingerprint != ""


# ---------------------------------------------------------------------------
# A2 — Assessment: Correctness Verification & Flawed Key Rejection
# ---------------------------------------------------------------------------
def test_a2_incorrect_answer_key_rejected(tmp_path):
    """
    A2: Present an intentionally incorrect answer key or unsupported question.
    Pass: verifier rejects it before presentation.
    """
    db = EvidenceDB(tmp_path / "a2.sqlite")
    db.add_source(SourceRecord(source_id="src1", path="doc.pdf", modality=Modality.pdf, title="Doc", sha256="h1"))
    db.add_evidence(EvidenceUnit(evidence_id="src1:e00001", source_id="src1", modality=Modality.pdf, text="Chemical reactions obey the law of conservation of mass.", location={"page": 5}))

    engine = AssessmentEngine(db)

    # Flawed MCQ: expected answer "E" is not among options A, B, C, D
    q_flawed = engine.build_and_verify_question(
        question_id="q_flawed_01",
        topic_id="Chemistry",
        prompt="What law states mass is neither created nor destroyed in a reaction?",
        expected_answer="E",  # Invalid key
        evidence_ids=["src1:e00001"],
        options=[
            QuestionOption(key="A", text="Conservation of Mass"),
            QuestionOption(key="B", text="Conservation of Energy"),
            QuestionOption(key="C", text="Law of Definite Proportions"),
            QuestionOption(key="D", text="Boyle's Law")
        ]
    )

    assert q_flawed.verification_status == "rejected"
    assert q_flawed.verification_reason is not None
    assert "does not match any valid option key" in q_flawed.verification_reason

    # Verify that adaptive selection filters out rejected questions
    selected = engine.select_adaptive_question("Chemistry", verified_only=True)
    assert selected is None


# ---------------------------------------------------------------------------
# A3 — Assessment: Repetition Control
# ---------------------------------------------------------------------------
def test_a3_repetition_suppression(tmp_path):
    """
    A3: Run repeated sessions with multiple valid candidate questions.
    Pass: identical/near-duplicate question is suppressed when alternatives exist.
    """
    db = EvidenceDB(tmp_path / "a3.sqlite")
    db.add_source(SourceRecord(source_id="s1", path="math.pdf", modality=Modality.pdf, title="Math", sha256="h1"))
    db.add_evidence(EvidenceUnit(evidence_id="s1:e00001", source_id="s1", modality=Modality.pdf, text="Arithmetic progressions and series.", location={"page": 1}))

    engine = AssessmentEngine(db)

    # Build 3 valid questions
    q1 = engine.build_and_verify_question(
        question_id="q_ap_01", topic_id="AP", prompt="Find common difference of 2, 5, 8, 11...",
        expected_answer="3", evidence_ids=["s1:e00001"], question_type=QuestionType.numerical
    )
    q2 = engine.build_and_verify_question(
        question_id="q_ap_02", topic_id="AP", prompt="Find the 10th term of 1, 3, 5, 7...",
        expected_answer="19", evidence_ids=["s1:e00001"], question_type=QuestionType.numerical
    )

    # Session 1: chooses q1
    s1 = engine.select_adaptive_question("AP", served_question_ids=[])
    assert s1.question_id == "q_ap_01"

    # Session 2: q1 is served -> must suppress q1 and return q2
    s2 = engine.select_adaptive_question("AP", served_question_ids=["q_ap_01"])
    assert s2.question_id == "q_ap_02"


# ---------------------------------------------------------------------------
# A4 — Assessment: Evidence-Grounded Corrective Feedback
# ---------------------------------------------------------------------------
def test_a4_corrective_feedback_cites_evidence(tmp_path):
    """
    A4: Submit a wrong answer.
    Pass: feedback is tied to relevant evidence and identifies the learner's next action.
    """
    db = EvidenceDB(tmp_path / "a4.sqlite")
    db.add_source(SourceRecord(source_id="src_optics", path="optics.pdf", modality=Modality.pdf, title="Optics", sha256="h1"))
    db.add_evidence(
        EvidenceUnit(
            evidence_id="src_optics:e00001",
            source_id="src_optics",
            modality=Modality.pdf,
            text="Snell's law of refraction: n1 * sin(theta1) = n2 * sin(theta2).",
            location={"page": 33},
            topics=["Optics", "Refraction"]
        )
    )

    engine = AssessmentEngine(db)
    q = engine.build_and_verify_question(
        question_id="q_snell_01",
        topic_id="Refraction",
        prompt="State Snell's law of refraction relating refractive indices and angles.",
        expected_answer="A",
        evidence_ids=["src_optics:e00001"],
        options=[
            QuestionOption(key="A", text="n1 * sin(theta1) = n2 * sin(theta2)"),
            QuestionOption(key="B", text="n1 * cos(theta1) = n2 * cos(theta2)")
        ],
        solution="Snell's law uses sine of the incident and refracted angles."
    )

    # Learner submits incorrect choice "B"
    sub = LearnerSubmission(learner_id="student_99", question_id="q_snell_01", topic_id="Refraction", answer="B")
    eval_res = engine.evaluate_submission(sub, q)

    assert not eval_res.is_correct
    assert eval_res.status == "incorrect"
    assert "Page 33" in eval_res.feedback
    assert len(eval_res.citations) == 1
    assert eval_res.citations[0].evidence_id == "src_optics:e00001"
    assert "Recommended next action" in eval_res.feedback


# ---------------------------------------------------------------------------
# L1 — Learner Model: Profile Divergence
# ---------------------------------------------------------------------------
def test_l1_learner_profile_divergence(tmp_path):
    """
    L1: Run two simulated learners with materially different answer histories.
    Pass: mastery states and recommendations differ in the expected direction.
    """
    db = EvidenceDB(tmp_path / "l1.sqlite")
    db.add_source(SourceRecord(source_id="s1", path="math.pdf", modality=Modality.pdf, title="Math", sha256="h1"))
    db.add_evidence(EvidenceUnit(evidence_id="s1:e00001", source_id="s1", modality=Modality.pdf, text="Quadratic equations factoring and roots.", location={"page": 1}))

    manager = LearnerStateManager(db)
    rec_engine = AdaptiveRecommendationEngine(db)

    # Learner High gets 5 consecutive correct answers
    for _ in range(5):
        manager.record_response("learner_high", "Quadratics", is_correct=True)

    # Learner Low gets 5 consecutive incorrect answers
    for _ in range(5):
        manager.record_response("learner_low", "Quadratics", is_correct=False)

    rec_high = rec_engine.recommend("learner_high", active_topic_id="Quadratics")
    rec_low = rec_engine.recommend("learner_low", active_topic_id="Quadratics")

    m_high = db.get_learner_mastery("learner_high", "Quadratics").p_mastery
    m_low = db.get_learner_mastery("learner_low", "Quadratics").p_mastery

    # Verify divergence
    assert m_high > m_low
    assert m_high >= 0.85
    assert m_low <= 0.30
    assert rec_high.recommended_action == "advance_topic"
    assert rec_low.recommended_action == "foundational_review"


# ---------------------------------------------------------------------------
# L2 — Learner Model: Session BKT State Updates
# ---------------------------------------------------------------------------
def test_l2_bkt_session_deterministic_update(tmp_path):
    """
    L2: Run verified responses.
    Pass: BKT state changes deterministically according to configured parameters.
    """
    db = EvidenceDB(tmp_path / "l2.sqlite")
    manager = LearnerStateManager(db)

    # Initial state
    m0 = manager.get_or_create_mastery("student_01", "Thermodynamics")
    assert m0.p_mastery == 0.10

    # Step 1: Correct response -> expected p_mastery ~ 0.433333
    m1 = manager.record_response("student_01", "Thermodynamics", is_correct=True)
    assert abs(m1.p_mastery - 0.433333) < 1e-4
    assert m1.attempts == 1
    assert m1.correct == 1

    # Step 2: Incorrect response from p=0.433333
    # P(L_1 | incorrect) = (0.433333 * 0.10) / (0.433333 * 0.10 + 0.566667 * 0.80) = 0.043333 / (0.043333 + 0.453333) = 0.043333 / 0.496666 ~ 0.087248
    # P(L_2) = 0.087248 + (1 - 0.087248) * 0.15 = 0.087248 + 0.136913 ~ 0.224161
    m2 = manager.record_response("student_01", "Thermodynamics", is_correct=False)
    assert abs(m2.p_mastery - 0.224161) < 1e-4
    assert m2.attempts == 2
    assert m2.correct == 1


# ---------------------------------------------------------------------------
# L3 — Learner Model: Targeted Intervention & Misconception Remediation
# ---------------------------------------------------------------------------
def test_l3_targeted_intervention_misconception(tmp_path):
    """
    L3: Give a learner repeated errors on one topic/concept.
    Pass: recommendation targets that topic/prerequisite and cites remediation evidence.
    """
    db = EvidenceDB(tmp_path / "l3.sqlite")
    db.add_source(SourceRecord(source_id="src_trig", path="trig.pdf", modality=Modality.pdf, title="Trig", sha256="h1"))
    db.add_concept("Unit Circle", "Unit Circle", description="Angles on unit circle")
    db.add_concept("Trig Signs", "Trig Signs", description="Signs in quadrants ASTC")
    db.link_concept_prerequisite("Trig Signs", "Unit Circle")

    db.add_evidence(
        EvidenceUnit(
            evidence_id="src_trig:e00001",
            source_id="src_trig",
            modality=Modality.pdf,
            text="In the unit circle, x = cos(theta) and y = sin(theta). All ratios positive in quadrant 1.",
            concepts=["Unit Circle"],
            topics=["Trigonometry"]
        )
    )

    detector = MisconceptionDetector(db, error_threshold=2)
    rec_engine = AdaptiveRecommendationEngine(db)

    # 2 consecutive errors on "Trig Signs"
    detector.analyze_attempt("student_error", "Trigonometry", "Trig Signs", is_correct=False)
    signal = detector.analyze_attempt("student_error", "Trigonometry", "Trig Signs", is_correct=False)
    assert signal is not None

    # Get recommendation
    rec = rec_engine.recommend("student_error", active_topic_id="Trigonometry")

    assert rec.recommended_action == "remediate_misconception"
    assert rec.concept_id == "Unit Circle"
    assert "src_trig:e00001" in rec.suggested_evidence_ids
    assert "Active misconception detected" in rec.rationale


# ---------------------------------------------------------------------------
# S2 — Security & Failure Closure: Provider / Verification Failure
# ---------------------------------------------------------------------------
def test_s2_failure_closure(tmp_path):
    """
    S2: Force retrieval / provider / verification failure.
    Pass: system shows explicit failure/abstention state rather than fabricated output.
    """
    db = EvidenceDB(tmp_path / "s2.sqlite")
    db.add_source(SourceRecord(source_id="s1", path="p.pdf", modality=Modality.pdf, title="P", sha256="h1"))
    db.add_evidence(EvidenceUnit(evidence_id="s1:e00001", source_id="s1", modality=Modality.pdf, text="Course concept.", location={"page": 1}))

    # 1. Tutor Provider Crash
    class CrashProvider:
        def generate(self, query, evidence_items):
            raise ConnectionError("Upstream AI Provider 504 Gateway Timeout")

    tutor = GroundedTutor(db, provider=CrashProvider())
    resp = tutor.answer("Course concept", mode="lexical")

    assert not resp.is_grounded
    assert resp.support_status == "error"
    assert "service error" in resp.answer.lower() or "withheld" in resp.answer.lower()
    assert len(resp.citations) == 0

    # 2. Retrieval Failure Closed
    tutor_retrieval_fail = GroundedTutor(db)
    resp_empty = tutor_retrieval_fail.answer("", mode="lexical")
    assert not resp_empty.is_grounded
    assert resp_empty.support_status == "unsupported"
