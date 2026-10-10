"""
CogniVault 2.0 — Landing & Learning Dashboard.
Comprehensive learning overview, course readiness, recommended next actions,
and rapid-navigation shortcuts conforming to the approved SaaS dashboard layout.
"""
from __future__ import annotations

import textwrap
import streamlit as st
from app.ui.components import (
    _render_html_fragment,
    render_page_header, render_section_header,
    render_metric_card, render_callout, render_empty_state
)
from app.ui.theme import (
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    BORDER_COLOR, ACCENT_INDIGO, ACCENT_TEAL,
    SUCCESS_GREEN, WARNING_AMBER
)
from app.corpus import seed_database_from_corpus


def render_dashboard_view(services: dict) -> None:
    db = services["db"]
    recommendation_engine = services["recommendations"]

    all_sources = list(db.all_sources())
    all_evidence = list(db.all_evidence())
    all_questions = db.all_questions(verified_only=True)
    all_topics = db.all_topics()
    active_learner = st.session_state.get("active_learner_id", "learner_demo")

    # -------------------------------------------------------------------------
    # 1. Top Horizontal Header (Search, Help, Account Status, Login/Sign Up)
    # -------------------------------------------------------------------------
    # Use Streamlit's native layout containers; HTML wrappers cannot span widgets.

    hdr_left, hdr_right = st.columns([1.6, 1.4])
    with hdr_left:
        s_input_col, s_btn_col, s_help_col = st.columns([2.6, 1.0, 0.4])
        with s_input_col:
            search_query = st.text_input(
                "Search courses",
                placeholder="Ask any question across your courses...",
                label_visibility="collapsed",
                key="dash_global_search_input"
            )
        with s_btn_col:
            do_search = st.button("Ask Tutor", type="primary", use_container_width=True, key="dash_global_search_btn")
        with s_help_col:
            with st.popover("❓", help="CogniVault Principles"):
                st.markdown("### 🧠 How CogniVault Works")
                st.markdown(
                    "- **Evidence-First**: Answers are deterministically grounded in indexed textbooks, slides, and transcripts.\n"
                    "- **Zero Hallucination**: Fail-closed abstention when curriculum evidence is insufficient.\n"
                    "- **Adaptive BKT**: Bayesian Knowledge Tracing dynamically updates your topic mastery."
                )

    with hdr_right:
        u_col, p_col, log_col, sign_col = st.columns([1.1, 1.2, 0.8, 0.9])
        with u_col:
            _render_html_fragment('<div style="text-align: center; padding-top: 0.35rem;"><span class="cogni-badge cogni-badge-neutral">👤 Guest</span></div>')
        with p_col:
            _render_html_fragment('<div style="text-align: center; padding-top: 0.35rem;"><span class="cogni-badge cogni-badge-teal">Free Tier (Local)</span></div>')
        with log_col:
            with st.popover("Login"):
                st.markdown("**Demonstration Session**")
                st.info("Local demonstration session active. Multi-device sync will be available in future releases.")
        with sign_col:
            with st.popover("Sign Up"):
                st.markdown("**Create Account**")
                st.info("CogniVault local demo mode is active. All curriculum and adaptive learning tools are fully available.")

    if do_search and search_query.strip():
        st.session_state["tutor_prefill_query"] = search_query.strip()
        st.session_state["nav_selection_override"] = "💬 AI Tutor"
        st.rerun()

    # -------------------------------------------------------------------------
    # 2. First-Run Corpus Seeding if No Sources
    # -------------------------------------------------------------------------
    if not all_sources:
        render_callout(
            title="Course Materials Needed",
            message="No curriculum sources indexed yet. Click 'Initialize Benchmark Corpus' below to load verified STEM learning materials.",
            variant="warning",
            icon="⚠️"
        )
        col_seed, _ = st.columns([1, 2])
        with col_seed:
            if st.button("🌱 Initialize Benchmark Corpus (PDF, PPTX, Video)", type="primary", use_container_width=True):
                with st.spinner("Indexing standard STEM curriculum..."):
                    seed_database_from_corpus(db)
                    st.rerun()
        return

    # -------------------------------------------------------------------------
    # 3. Upper Section: Hero Card + Resume Learning Card
    # -------------------------------------------------------------------------
    col_hero, col_resume = st.columns([1.75, 1.25])

    with col_hero:
        # Large SaaS Welcome Hero Card
        hero_html = textwrap.dedent(f"""
            <div class="hero-card dashboard-hero" style="height:100%;display:flex;flex-direction:column;justify-content:center;text-align:center;">
                <div>
                    <div class="card-title" style="font-size: 1.55rem; margin-bottom: 0.45rem;">
                        Welcome to CogniVault
                    </div>
                    <div class="card-subtitle" style="font-size: 0.98rem; margin-bottom: 1.25rem;">
                        Learn with confidence. Ask questions, practice, and explore — all grounded in your course materials.
                    </div>
                </div>
                <div class="dashboard-hero-badges" style="display:flex;flex-wrap:wrap;justify-content:center;gap:0.5rem;margin-top:0.6rem;">
                    <span class="cogni-badge cogni-badge-indigo">🛡️ Evidence-backed answers</span>
                    <span class="cogni-badge cogni-badge-teal">🎯 Adaptive practice</span>
                    <span class="cogni-badge cogni-badge-success">📈 Track your progress</span>
                    <span class="cogni-badge cogni-badge-neutral">💡 Personalized recommendations</span>
                </div>
            </div>
        """).strip()
        st.markdown(hero_html, unsafe_allow_html=True)

    with col_resume:
        # Resume Learning Card (Based on real interactions & masteries)
        interactions = db.get_interactions(active_learner)
        masteries = db.get_all_learner_masteries(active_learner)

        with st.container(border=True):
            _render_html_fragment(textwrap.dedent(f"""
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem;">
                        <span class="resume-badge">Resume Learning</span>
                        <span style="font-size: 0.8rem; color: {TEXT_MUTED};">Active Session</span>
                    </div>
                """).strip())

            if interactions or masteries:
                # Find most recent topic
                if interactions:
                    res_topic = interactions[-1]["topic_id"]
                else:
                    res_topic = masteries[0].topic_id

                # Real topic metrics
                topic_qs = db.get_questions_for_topic(res_topic, verified_only=True)
                total_topic_qs = len(topic_qs)
                topic_interactions = [i for i in interactions if i["topic_id"] == res_topic]
                unique_answered = len({i["question_id"] for i in topic_interactions})
                completion_pct = int((unique_answered / max(1, total_topic_qs)) * 100) if total_topic_qs > 0 else 0

                rec_m = db.get_learner_mastery(active_learner, res_topic)
                mastery_p = rec_m.p_mastery if rec_m else 0.10

                st.markdown(f"### {res_topic}")
                _render_html_fragment(f"<div style='font-size: 0.85rem; color: {TEXT_SECONDARY}; margin-bottom: 0.6rem;'>STEM Curriculum • Verified Materials</div>")

                st.progress(min(1.0, max(0.05, completion_pct / 100.0)))
                st.caption(f"**Progress:** {unique_answered}/{total_topic_qs} items ({completion_pct}%) • **Mastery P(L):** `{mastery_p:.1%}`")

                col_btn_cont, col_btn_all = st.columns([1.3, 1.0])
                with col_btn_cont:
                    if st.button("Continue Learning →", type="primary", use_container_width=True, key="dash_resume_continue_btn"):
                        st.session_state["nav_selection_override"] = "📝 Practice & Assessment"
                        st.rerun()
                with col_btn_all:
                    if st.button("All Courses", use_container_width=True, key="dash_resume_all_courses_btn"):
                        st.session_state["nav_selection_override"] = "📚 Available Courses"
                        st.rerun()
            else:
                st.markdown("### Ready to Begin")
                _render_html_fragment(f"<div style='font-size: 0.88rem; color: {TEXT_SECONDARY}; margin-bottom: 1rem;'>You haven't started an active topic yet. Explore course materials or launch practice to begin.</div>")
                if st.button("Explore Available Courses →", type="primary", use_container_width=True, key="dash_resume_explore_empty_btn"):
                    st.session_state["nav_selection_override"] = "📚 Available Courses"
                    st.rerun()

    _render_html_fragment("<div style='margin-bottom: 1rem;'></div>")

    # -------------------------------------------------------------------------
    # 4. Compact recommendation panel and bottom quick actions.
    # The resume card above is the single source for continuing course work.
    # -------------------------------------------------------------------------
    rec = recommendation_engine.recommend(active_learner)
    action_label = rec.recommended_action.replace("_", " ").title()
    status_type = rec.learner_state_evidence.get("status")
    is_blocked = status_type in ("unverified_prerequisite", "below_threshold") or "prerequisite" in rec.rationale.lower()
    prereq_topic = rec.learner_state_evidence.get("prerequisite_topic", "")
    status_variant = "danger" if is_blocked else ("warning" if "review" in rec.recommended_action else "success")

    with st.container(border=True):
        render_section_header(title="🎯 Recommended Next Step", subtitle="Adaptive guidance calibrated to your mastery state.")
        _render_html_fragment(textwrap.dedent(f"""
            <div style="display:flex;align-items:center;gap:0.5rem;flex-wrap:wrap;margin-bottom:0.35rem;">
              <span style="font-size:1rem;font-weight:700;color:{TEXT_PRIMARY};">{action_label}</span>
              <span class="cogni-badge cogni-badge-{status_variant}">Target: {rec.topic_id}</span>
              <span class="cogni-badge cogni-badge-neutral">{rec.difficulty.value.upper()}</span>
            </div>
            <p style="font-size:0.85rem;color:{TEXT_SECONDARY};line-height:1.4;margin:0.25rem 0 0.5rem 0;">{rec.rationale}</p>
        """).strip())
        if is_blocked and prereq_topic:
            st.warning(f"Prerequisite gate: advancement is locked until {prereq_topic} reaches the required mastery threshold.")
        if st.button(f"Go to {action_label} →", type="primary", key="dash_rec_action_btn"):
            st.session_state["nav_selection_override"] = "💬 AI Tutor" if "tutor" in rec.recommended_action.lower() else "📝 Practice & Assessment"
            st.rerun()

    # Quick Actions are the final dashboard section and use compact equal-width cards.
    with st.container(border=True):
        render_section_header(title="⚡ Quick Actions", subtitle="Fast shortcuts to key learning capabilities.")
        qa_cols = st.columns(4)
        quick_actions = [
            ("💬", "Ask AI Tutor", "Launch Tutor", "💬 AI Tutor", "dash_qa_tutor"),
            ("📝", "Practice Test", "Start Practice", "📝 Practice & Assessment", "dash_qa_practice"),
            ("🔍", "Evidence Vault", "Explore Evidence", "📚 Available Courses", "dash_qa_evidence"),
            ("🎯", "Recommendations", "View Guidance", "🎯 Recommendations", "dash_qa_recommendations"),
        ]
        for col, (emoji, title, button_label, destination, key) in zip(qa_cols, quick_actions):
            with col:
                _render_html_fragment(f'<div class="quick-action-card dashboard-quick-action"><span style="font-size:1.1rem;">{emoji}</span><strong>{title}</strong></div>')
                if st.button(button_label, use_container_width=True, key=key):
                    st.session_state["nav_selection_override"] = destination
                    st.rerun()

    with st.expander("👋 Set up your learning profile", expanded=False):
        st.caption("Choose your standard/grade and interests for calibrated difficulty and personalized recommendations.")
        if st.button("Set Up Profile →", key="dash_onboarding_profile_btn"):
            st.session_state["nav_selection_override"] = "📊 My Progress"
            st.rerun()
