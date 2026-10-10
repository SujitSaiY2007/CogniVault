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
                _render_html_fragment("### 🧠 How CogniVault Works")
                st.markdown(
                    "- **Evidence-First**: Answers are deterministically grounded in indexed textbooks, slides, and transcripts.\n"
                    "- **Zero Hallucination**: Fail-closed abstention when curriculum evidence is insufficient.\n"
                    "- **Adaptive BKT**: Bayesian Knowledge Tracing dynamically updates your topic mastery."
                )

    with hdr_right:
        u_col, p_col, log_col, sign_col = st.columns([1.1, 1.2, 0.8, 0.9])
        with u_col:
            st.markdown(
                '<div style="text-align: center; padding-top: 0.35rem;"><span class="cogni-badge cogni-badge-neutral">👤 Guest</span></div>')
        with p_col:
            _render_html_fragment('<div style="text-align: center; padding-top: 0.35rem;"><span class="cogni-badge cogni-badge-teal">Free Tier (Local)</span></div>')
        with log_col:
            with st.popover("Login"):
                _render_html_fragment("**Demonstration Session**")
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
            <div class="hero-card" style="height: 100%; display: flex; flex-direction: column; justify-content: space-between;">
                <div>
                    <div class="card-title" style="font-size: 1.55rem; margin-bottom: 0.45rem;">
                        Welcome to CogniVault
                    </div>
                    <div class="card-subtitle" style="font-size: 0.98rem; margin-bottom: 1.25rem;">
                        Learn with confidence. Ask questions, practice, and explore — all grounded in your course materials.
                    </div>
                </div>
                <div style="display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: auto;">
                    <span class="cogni-badge cogni-badge-indigo">🛡️ Evidence-backed answers</span>
                    <span class="cogni-badge cogni-badge-teal">🎯 Adaptive practice</span>
                    <span class="cogni-badge cogni-badge-success">📈 Track your progress</span>
                    <span class="cogni-badge cogni-badge-neutral">💡 Personalized recommendations</span>
                </div>
            </div>
        """).strip()
        st.markdown(hero_html)

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

                _render_html_fragment(f"### {res_topic}")
                st.markdown(f"<div style='font-size: 0.85rem; color: {TEXT_SECONDARY}; margin-bottom: 0.6rem;'>STEM Curriculum • Verified Materials</div>")

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
                _render_html_fragment("### Ready to Begin")
                st.markdown(f"<div style='font-size: 0.88rem; color: {TEXT_SECONDARY}; margin-bottom: 1rem;'>You haven't started an active topic yet. Explore course materials or launch practice to begin.</div>")
                if st.button("Explore Available Courses →", type="primary", use_container_width=True, key="dash_resume_explore_empty_btn"):
                    st.session_state["nav_selection_override"] = "📚 Available Courses"
                    st.rerun()

    _render_html_fragment("<div style='margin-bottom: 1rem;'></div>")

    # -------------------------------------------------------------------------
    # 4. Main Dashboard Grid: Left (Continue Learning + History), Right (Recs + Quick Actions)
    # -------------------------------------------------------------------------
    col_main, col_side = st.columns([1.75, 1.25])

    with col_main:
        # A. Continue Learning Section
        with st.container(border=True):
            render_section_header(
                title="📖 Continue Learning",
                subtitle="Your active course curriculum and progress."
            )

            if interactions or masteries:
                active_topic_name = interactions[-1]["topic_id"] if interactions else masteries[0].topic_id
                t_qs = db.get_questions_for_topic(active_topic_name, verified_only=True)
                t_inter = [i for i in interactions if i["topic_id"] == active_topic_name]
                t_ans = len({i["question_id"] for i in t_inter})
                t_pct = int((t_ans / max(1, len(t_qs))) * 100) if t_qs else 0
                t_mast = (db.get_learner_mastery(active_learner, active_topic_name).p_mastery if db.get_learner_mastery(active_learner, active_topic_name) else 0.10)

                _render_html_fragment(textwrap.dedent(f"""
                        <div style="background: #F8FAFC; border: 1px solid {BORDER_COLOR}; border-radius: 8px; padding: 1rem; margin-bottom: 0.85rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
                                <span style="font-size: 1.05rem; font-weight: 700; color: {TEXT_PRIMARY};">{active_topic_name}</span>
                                <span class="cogni-badge cogni-badge-indigo">Mastery: {t_mast:.1%}</span>
                            </div>
                            <div style="font-size: 0.86rem; color: {TEXT_SECONDARY}; margin-bottom: 0.5rem;">
                                Comprehensive topic coverage with deterministic grounding and multi-modal evidence.
                            </div>
                            <div style="font-size: 0.82rem; color: {TEXT_MUTED};">
                                Completed: <strong>{t_ans} of {len(t_qs)} items</strong> ({t_pct}%)
                            </div>
                        </div>
                    """).strip())
                if st.button("Open Course Practice →", type="primary", key="dash_open_course_practice_btn"):
                    st.session_state["nav_selection_override"] = "📝 Practice & Assessment"
                    st.rerun()
            else:
                # Default curriculum source
                primary_source = all_sources[0] if all_sources else None
                s_title = primary_source.title if primary_source else "STEM Benchmark Curriculum"
                s_mod = primary_source.modality.upper() if primary_source else "PDF"

                _render_html_fragment(textwrap.dedent(f"""
                        <div style="background: #F8FAFC; border: 1px solid {BORDER_COLOR}; border-radius: 8px; padding: 1rem; margin-bottom: 0.85rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
                                <span style="font-size: 1.05rem; font-weight: 700; color: {TEXT_PRIMARY};">{s_title}</span>
                                <span class="cogni-badge cogni-badge-teal">{s_mod}</span>
                            </div>
                            <div style="font-size: 0.86rem; color: {TEXT_SECONDARY};">
                                Verified foundational course material ready for exploration and practice.
                            </div>
                        </div>
                    """).strip())
                if st.button("Start Course →", type="primary", key="dash_start_primary_course_btn"):
                    st.session_state["nav_selection_override"] = "📚 Available Courses"
                    st.rerun()

        # B. Recent History Section (Real interaction records, session-only for guests)
        with st.container(border=True):
            render_section_header(
                title="⏱️ Recent History",
                subtitle="Recent practice attempts and tutor inquiries during this session."
            )

            if interactions:
                recent_list = interactions[-5:][::-1]
                for item in recent_list:
                    status_badge = '<span class="cogni-badge cogni-badge-success">✅ Correct</span>' if item["is_correct"] else '<span class="cogni-badge cogni-badge-warning">❌ Needs Review</span>'
                    ts_str = item["timestamp"][:16].replace("T", " ") if "T" in item["timestamp"] else item["timestamp"]
                    _render_html_fragment(textwrap.dedent(f"""
                            <div class="history-row">
                                <div>
                                    <span style="font-weight: 600; color: {TEXT_PRIMARY};">{item['topic_id']}</span>
                                    <div style="font-size: 0.78rem; color: {TEXT_MUTED}; margin-top: 0.15rem;">Score: {item['score']:.0%} • {ts_str}</div>
                                </div>
                                <div>{status_badge}</div>
                            </div>
                        """).strip())
            else:
                render_empty_state(
                    title="No Recent Activity",
                    message="Your practice attempts, evidence explorations, and tutor queries will appear here.",
                    icon="⏱️"
                )

    with col_side:
        # C. Recommended Next Step Card
        with st.container(border=True):
            render_section_header(
                title="🎯 Recommended Next Step",
                subtitle="Adaptive guidance calibrated to your mastery state."
            )

            rec = recommendation_engine.recommend(active_learner)
            action_label = rec.recommended_action.replace("_", " ").title()
            status_type = rec.learner_state_evidence.get("status")
            is_blocked = status_type in ("unverified_prerequisite", "below_threshold") or "prerequisite" in rec.rationale.lower()
            prereq_topic = rec.learner_state_evidence.get("prerequisite_topic", "")

            status_variant = "danger" if is_blocked else ("warning" if "review" in rec.recommended_action else "success")

            _render_html_fragment(textwrap.dedent(f"""
                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.4rem; flex-wrap: wrap;">
                        <span style="font-size: 1.05rem; font-weight: 700; color: {TEXT_PRIMARY};">{action_label}</span>
                        <span class="cogni-badge cogni-badge-{status_variant}">Target: {rec.topic_id}</span>
                        <span class="cogni-badge cogni-badge-neutral">{rec.difficulty.value.upper()}</span>
                    </div>
                    <p style="font-size: 0.88rem; color: {TEXT_SECONDARY}; line-height: 1.5; margin-bottom: 0.75rem;">
                        {rec.rationale}
                    </p>
                """).strip())

            if is_blocked and prereq_topic:
                st.error(f"⛔ **Prerequisite Gate:** Advancement locked until **{prereq_topic}** reaches $P(L) \\ge 0.70$.")

            if st.button(f"Go to {action_label} →", type="primary", use_container_width=True, key="dash_rec_action_btn"):
                if "tutor" in rec.recommended_action.lower():
                    st.session_state["nav_selection_override"] = "💬 AI Tutor"
                else:
                    st.session_state["nav_selection_override"] = "📝 Practice & Assessment"
                st.rerun()

        # D. Quick Actions Grid (2x2)
        with st.container(border=True):
            render_section_header(
                title="⚡ Quick Actions",
                subtitle="Fast shortcuts to key learning capabilities."
            )

            qa_col1, qa_col2 = st.columns(2)
            with qa_col1:
                _render_html_fragment(textwrap.dedent(f"""
                        <div class="quick-action-card">
                            <div style="font-size: 1.2rem; margin-bottom: 0.25rem;">💬</div>
                            <div style="font-weight: 700; color: {TEXT_PRIMARY}; font-size: 0.95rem;">Ask AI Tutor</div>
                            <div style="font-size: 0.82rem; color: {TEXT_SECONDARY}; margin-top: 0.2rem;">Strict citation grounding</div>
                        </div>
                    """).strip())
                if st.button("Launch Tutor", use_container_width=True, key="dash_qa_tutor"):
                    st.session_state["nav_selection_override"] = "💬 AI Tutor"
                    st.rerun()

                _render_html_fragment("<div style='margin-top: 0.5rem;'></div>")

                _render_html_fragment(textwrap.dedent(f"""
                        <div class="quick-action-card">
                            <div style="font-size: 1.2rem; margin-bottom: 0.25rem;">🔍</div>
                            <div style="font-weight: 700; color: {TEXT_PRIMARY}; font-size: 0.95rem;">Evidence Vault</div>
                            <div style="font-size: 0.82rem; color: {TEXT_SECONDARY}; margin-top: 0.2rem;">Explore slides & locators</div>
                        </div>
                    """).strip())
                if st.button("Explore Evidence", use_container_width=True, key="dash_qa_evidence"):
                    st.session_state["nav_selection_override"] = "📚 Available Courses"
                    st.rerun()

            with qa_col2:
                _render_html_fragment(textwrap.dedent(f"""
                        <div class="quick-action-card">
                            <div style="font-size: 1.2rem; margin-bottom: 0.25rem;">📝</div>
                            <div style="font-weight: 700; color: {TEXT_PRIMARY}; font-size: 0.95rem;">Practice Test</div>
                            <div style="font-size: 0.82rem; color: {TEXT_SECONDARY}; margin-top: 0.2rem;">Adaptive BKT assessment</div>
                        </div>
                    """).strip())
                if st.button("Start Practice", use_container_width=True, key="dash_qa_practice"):
                    st.session_state["nav_selection_override"] = "📝 Practice & Assessment"
                    st.rerun()

                _render_html_fragment("<div style='margin-top: 0.5rem;'></div>")

                _render_html_fragment(textwrap.dedent(f"""
                        <div class="quick-action-card">
                            <div style="font-size: 1.2rem; margin-bottom: 0.25rem;">🎯</div>
                            <div style="font-weight: 700; color: {TEXT_PRIMARY}; font-size: 0.95rem;">Recommendations</div>
                            <div style="font-size: 0.82rem; color: {TEXT_SECONDARY}; margin-top: 0.2rem;">View prerequisite trees</div>
                        </div>
                    """).strip())
                if st.button("View Guidance", use_container_width=True, key="dash_qa_recs"):
                    st.session_state["nav_selection_override"] = "🎯 Recommendations"
                    st.rerun()

    # -------------------------------------------------------------------------
    # 5. Bottom Onboarding / Profile Setup Banner
    # -------------------------------------------------------------------------
    _render_html_fragment(textwrap.dedent(f"""
            <div class="onboarding-banner">
                <div>
                    <span style="font-size: 1.05rem; font-weight: 700; color: {TEXT_PRIMARY};">
                        👋 New to CogniVault? Set up your learning profile
                    </span>
                    <p style="margin: 0.25rem 0 0 0; font-size: 0.88rem; color: {TEXT_SECONDARY};">
                        Select your standard/grade and interests to receive calibrated difficulty and personalized course recommendations.
                    </p>
                </div>
            </div>
        """).strip())
    col_ob1, _ = st.columns([1.5, 3])
    with col_ob1:
        if st.button("Set Up Profile →", type="primary", use_container_width=True, key="dash_onboarding_profile_btn"):
            st.session_state["nav_selection_override"] = "📊 My Progress"
            st.rerun()
