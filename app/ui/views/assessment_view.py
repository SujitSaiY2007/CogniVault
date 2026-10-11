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
from app.ui.components import (
    _render_html_fragment,
    render_page_header,
    render_section_header,
    render_metric_card,
    render_callout,
    render_empty_state,
)


def render_assessment_view(services: dict):
    db = services["db"]
    engine: AssessmentEngine = services["assessment_engine"]
    bkt: BKTModel = services["bkt"]
    misconceptions: MisconceptionDetector = services["misconceptions"]

    render_page_header(
        title="Practice & Assessment",
        description="Practise with verified questions, get feedback, and revisit topics that need more attention. Question selection can adapt to your learning history.",
        badge_text="Practice",
        badge_variant="indigo"
    )

    all_topics = [t.name for t in db.all_topics()]
    if not all_topics:
        render_empty_state(
            title="Curriculum Topics Not Found",
            description="No topics available in database. Please seed or ingest curriculum materials first in Course Setup.",
            icon="📂"
        )
        return

    # Learner and Topic Selection Header Card
    with st.container(border=True):
        col_learner, col_topic, col_diff = st.columns([1, 1, 1])
        with col_learner:
            learner_id = st.text_input("Active Learner ID", value=st.session_state.active_learner_id)
            st.session_state.active_learner_id = learner_id
        with col_topic:
            active_topic = st.selectbox("Curriculum Topic", all_topics, index=0)
            st.session_state.active_topic_id = active_topic
        with col_diff:
            diff_choice = st.selectbox("Difficulty Policy", ["Adaptive (Auto)", "Easy", "Medium", "Hard"])

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
    attempts_cnt = mastery_rec.attempts if mastery_rec else 0
    correct_cnt = mastery_rec.correct if mastery_rec else 0

    if p_mastery < 0.40:
        band_name = "Foundational Review (Easy)"
        badge_var = "danger"
    elif p_mastery < 0.70:
        band_name = "Targeted Practice (Medium)"
        badge_var = "warning"
    elif p_mastery <= 0.85:
        band_name = "Mixed Application (Medium)"
        badge_var = "indigo"
    else:
        band_name = "Advance Topic (Hard)"
        badge_var = "success"

    # Mastery KPI Bar
    col_k1, col_k2, col_k3, col_k4 = st.columns(4)
    with col_k1:
        render_metric_card("Mastery P(L)", f"{p_mastery:.4f}", subtext="Posterior belief", badge="BKT", badge_variant="indigo")
    with col_k2:
        render_metric_card("Active Policy Band", band_name.split(" ")[0], subtext=band_name, badge=diff_choice, badge_variant=badge_var)
    with col_k3:
        render_metric_card("Total Attempts", attempts_cnt, subtext=f"{correct_cnt} correct answers", badge="Practice", badge_variant="neutral")
    with col_k4:
        acc_pct = (correct_cnt / attempts_cnt * 100) if attempts_cnt > 0 else 0.0
        render_metric_card("Accuracy Rate", f"{acc_pct:.1f}%", subtext="Historical performance", badge="Score", badge_variant="teal")

    # Next Question Controls
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
                st.warning("No verified questions available for the selected topic and difficulty band.")

    with col_clear:
        if st.button("🔄 Reset Question History", use_container_width=True):
            st.session_state.served_question_ids = []
            st.info("Question repetition history cleared for this session.")

    # Render Current Question Card
    q = st.session_state.get("current_question")
    if not q:
        render_empty_state(
            title="No Active Question Loaded",
            description="Click 'Fetch Next Adaptive Question' above to load a verified item adapted to your current mastery state.",
            icon="📝"
        )
        return

    with st.container(border=True):
        header_cols = st.columns([2.5, 1, 1])
        with header_cols[0]:
            _render_html_fragment(f"""
                <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
                    <span class="cogni-badge cogni-badge-neutral">{q.question_id}</span>
                    <strong style="color: #18233B; font-size: 1.1rem;">{active_topic}</strong>
                </div>
                """)
            if q.concept_id:
                st.caption(f"Target Concept: **{q.concept_id}**")
        with header_cols[1]:
            _render_html_fragment(f"""
                <div style="display: flex; gap: 0.4rem; justify-content: flex-end;">
                    <span class="cogni-badge cogni-badge-neutral">{q.difficulty.value.upper()}</span>
                    <span class="cogni-badge cogni-badge-neutral">{q.question_type.value.upper()}</span>
                </div>
                """)
        with header_cols[2]:
            _render_html_fragment('<div style="text-align: right;"><span class="cogni-badge cogni-badge-success">✅ Verified Item</span></div>')

        _render_html_fragment(f"""
            <div style="
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                padding: 1.1rem 1.25rem;
                margin: 0.75rem 0 1.25rem 0;
                font-size: 1.05rem;
                font-weight: 500;
                color: #18233B;
                line-height: 1.5;
            ">
                {q.prompt}
            </div>
            """)

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

        if st.button("🚀 Submit Answer", type="primary", key=f"submit_{q.question_id}", use_container_width=True):
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
                bkt.record_observation(learner_id, q.topic_id, evaluation.is_correct)

                # 3. Check / update misconception tracking
                concept_id = q.concept_id or q.topic_id
                misconceptions.analyze_attempt(
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

        if eval_res.is_correct:
            render_callout(
                title="Correct Answer!",
                message=eval_res.feedback,
                variant="success",
                icon="🎉"
            )
        else:
            render_callout(
                title="Incorrect Attempt",
                message=eval_res.feedback,
                variant="danger",
                icon="❌"
            )

        # Show Solution and Citations Linked to Question
        if q.solution:
            with st.expander("💡 View Detailed Solution & Step-by-Step Explanation", expanded=True):
                st.write(q.solution)

        if eval_res.citations:
            render_section_header("📖 Evidence Provenance for This Question", subtitle="Verified source units certifying this question's answer.")
            for cite in eval_res.citations:
                loc = cite.location
                loc_str = f"Page {loc.get('page', '')}" if "page" in loc else (f"Slide {loc.get('slide', '')}" if "slide" in loc else "Locator")
                with st.expander(f"Evidence `{cite.evidence_id}` — {cite.source_title or cite.source_id} ({cite.modality.value.upper()}, {loc_str})"):
                    st.write(cite.snippet)

        # Show updated BKT Mastery Score
        updated_rec = db.get_learner_mastery(learner_id, q.topic_id)
        if updated_rec:
            st.success(f"📊 **Updated Topic Mastery $P(L)$:** `{updated_rec.p_mastery:.4f}` (Attempts: {updated_rec.attempts}, Correct: {updated_rec.correct})")
