"""
Adaptive Assessment View.
Presents verified assessment items, evaluates learner responses,
updates Bayesian Knowledge Tracing (BKT) mastery in real-time,
and returns evidence-linked remediation feedback.
"""
from __future__ import annotations

import streamlit as st
from app.models import Difficulty, LearnerSubmission, QuestionType
from app.assessment import AssessmentEngine
from app.learner_model import BKTModel
from app.misconceptions import MisconceptionDetector


def render_assessment_view(services: dict):
    db = services["db"]
    engine: AssessmentEngine = services["assessment_engine"]
    bkt: BKTModel = services["bkt"]
    misconceptions: MisconceptionDetector = services["misconceptions"]

    st.header("📝 Adaptive Assessment & Verified Practice")
    st.markdown(
        """
        Practice curriculum topics through structurally verified questions.
        CogniVault adaptively serves items based on your current Bayesian Knowledge Tracing (BKT) mastery band
        and prevents unhelpful question repetition.
        """
    )

    # Learner and Topic Selection Header
    all_topics = [t.name for t in db.all_topics()]
    if not all_topics:
        st.warning("No topics available in database. Please seed or ingest curriculum material first.")
        return

    col_learner, col_topic, col_diff = st.columns([1, 1, 1])
    with col_learner:
        learner_id = st.text_input("Active Learner ID", value=st.session_state.active_learner_id)
        st.session_state.active_learner_id = learner_id
    with col_topic:
        active_topic = st.selectbox("Active Topic", all_topics, index=0)
        st.session_state.active_topic_id = active_topic
    with col_diff:
        diff_choice = st.selectbox("Target Difficulty", ["Adaptive (Auto)", "Easy", "Medium", "Hard"])

    target_diff = None
    if diff_choice == "Easy":
        target_diff = Difficulty.easy
    elif diff_choice == "Medium":
        target_diff = Difficulty.medium
    elif diff_choice == "Hard":
        target_diff = Difficulty.hard

    # Current Mastery Display for this topic
    mastery_rec = db.get_learner_mastery(learner_id, active_topic)
    p_mastery = mastery_rec.p_mastery if mastery_rec else 0.10

    if p_mastery < 0.40:
        band_name = "Foundational Review (Easy)"
        band_color = "red"
    elif p_mastery < 0.70:
        band_name = "Targeted Practice (Medium)"
        band_color = "orange"
    elif p_mastery <= 0.85:
        band_name = "Mixed Application (Medium)"
        band_color = "blue"
    else:
        band_name = "Advance Topic (Hard)"
        band_color = "green"

    st.markdown(
        f"**Learner:** `{learner_id}` | **Current Mastery $P(L)$:** `{p_mastery:.4f}` | "
        f"**Mastery Band:** :{band_color}[{band_name}]"
    )

    # Next Question Button
    col_fetch, col_clear = st.columns([2, 1])
    with col_fetch:
        if st.button("🎯 Fetch Next Adaptive Question", type="primary", use_container_width=True):
            served_ids = st.session_state.get("served_question_ids", [])
            q = engine.select_adaptive_question(
                active_topic,
                served_question_ids=served_ids,
                target_difficulty=target_diff,
                verified_only=True
            )
            if q:
                st.session_state.current_question = q
                st.session_state.last_evaluation = None
            else:
                st.warning("No verified questions available for the selected topic and difficulty.")

    with col_clear:
        if st.button("🔄 Reset Served Questions", use_container_width=True):
            st.session_state.served_question_ids = []
            st.info("Question repetition history cleared for this session.")

    st.divider()

    # Render Current Question Card
    q = st.session_state.get("current_question")
    if not q:
        st.info("Click **'Fetch Next Adaptive Question'** above to start your practice session.")
        return

    with st.container(border=True):
        header_cols = st.columns([3, 1, 1])
        with header_cols[0]:
            st.markdown(f"### Question `{q.question_id}`")
            if q.concept_id:
                st.caption(f"**Concept:** {q.concept_id}")
        with header_cols[1]:
            st.markdown(f"**Difficulty:** `{q.difficulty.value.upper()}`")
            st.markdown(f"**Type:** `{q.question_type.value.upper()}`")
        with header_cols[2]:
            st.success("✅ **Verified**\n(Structural Integrity)")

        st.markdown(f"#### {q.prompt}")

        # Form for answering
        user_answer = ""
        if q.question_type == QuestionType.mcq:
            opt_map = {f"{opt.key}: {opt.text}": opt.key for opt in q.options}
            selected_label = st.radio("Select your answer:", list(opt_map.keys()), key=f"radio_{q.question_id}")
            user_answer = opt_map.get(selected_label, "")
        elif q.question_type == QuestionType.numerical:
            user_answer = st.text_input("Enter numerical answer (e.g., 20.0 or 1.5e2):", key=f"num_{q.question_id}")
        else:
            user_answer = st.text_input("Enter your answer:", key=f"short_{q.question_id}")

        if st.button("Submit Answer", type="primary", key=f"submit_{q.question_id}"):
            if not user_answer.strip():
                st.error("Please enter or select an answer before submitting.")
            else:
                submission = LearnerSubmission(
                    learner_id=learner_id,
                    question_id=q.question_id,
                    topic_id=q.topic_id,
                    answer=user_answer.strip()
                )

                # 1. Evaluate submission
                evaluation = engine.evaluate_submission(submission, q)
                st.session_state.last_evaluation = evaluation

                # 2. Update BKT state
                bkt_res = bkt.record_observation(learner_id, q.topic_id, evaluation.is_correct)

                # 3. Check / update misconception tracking
                concept_id = q.concept_id or q.topic_id
                misc_signal = misconceptions.analyze_attempt(
                    learner_id,
                    q.topic_id,
                    concept_id,
                    is_correct=evaluation.is_correct,
                    error_pattern=user_answer.strip()
                )

                # 4. Mark question as served
                served = st.session_state.served_question_ids
                if q.question_id not in served:
                    served.append(q.question_id)
                st.session_state.served_question_ids = served

    # Display Feedback & Explanations if evaluated
    eval_res = st.session_state.get("last_evaluation")
    if eval_res and q and eval_res.question_id == q.question_id:
        st.divider()
        if eval_res.is_correct:
            st.success(f"### 🎉 {eval_res.feedback}")
        else:
            st.error(f"### ❌ {eval_res.feedback}")

        # Citations Linked to Question
        if eval_res.citations:
            st.subheader("📖 Evidence Provenance for This Question")
            for cite in eval_res.citations:
                loc = cite.location
                loc_str = f"Page {loc.get('page', '')}" if "page" in loc else (f"Slide {loc.get('slide', '')}" if "slide" in loc else "Locator")
                with st.expander(f"Evidence `{cite.evidence_id}` — {cite.source_title or cite.source_id} ({cite.modality.value.upper()}, {loc_str})"):
                    st.write(cite.snippet)

        # Show updated BKT Mastery Score
        updated_rec = db.get_learner_mastery(learner_id, q.topic_id)
        if updated_rec:
            st.info(f"📊 **Updated Topic Mastery $P(L)$:** `{updated_rec.p_mastery:.4f}` (Attempts: {updated_rec.attempts}, Correct: {updated_rec.correct})")
