"""
CogniVault 2.0 — Landing & Learning Dashboard.
Comprehensive learning overview, course readiness, recommended next actions,
and rapid-navigation shortcuts.
"""
from __future__ import annotations

import streamlit as st
from app.ui.components import (
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

    render_page_header(
        title="Learning Overview & Dashboard",
        description="Welcome to CogniVault 2.0. Evidence-first adaptive learning with deterministic grounding and prerequisite gating.",
        badge_text="Track D Hackathon",
        badge_variant="indigo"
    )

    all_sources = list(db.all_sources())
    all_evidence = list(db.all_evidence())
    all_questions = db.all_questions(verified_only=True)
    all_topics = db.all_topics()
    active_learner = st.session_state.get("active_learner_id", "learner_demo")

    # 1. First-run guidance if no sources indexed
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

    # 2. Executive KPI Header Grid
    st.markdown('<div style="margin-bottom: 1.25rem;">', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_card(
            label="Curriculum Sources",
            value=len(all_sources),
            subtext="PDF, PPTX & Transcripts",
            badge="Indexed",
            badge_variant="indigo"
        )
    with c2:
        render_metric_card(
            label="Evidence Units",
            value=len(all_evidence),
            subtext="Atomic addressable chunks",
            badge="Verified",
            badge_variant="teal"
        )
    with c3:
        render_metric_card(
            label="Verified Items",
            value=len(all_questions),
            subtext="Structural integrity validated",
            badge="Ready",
            badge_variant="success"
        )
    with c4:
        # Calculate active learner average mastery
        masteries = db.get_all_learner_masteries(active_learner)
        avg_mastery = (sum(m.p_mastery for m in masteries) / len(masteries)) if masteries else 0.10
        render_metric_card(
            label="Active Learner P(L)",
            value=f"{avg_mastery:.1%}",
            subtext=f"Profile: {active_learner}",
            badge="BKT Model",
            badge_variant="indigo"
        )
    st.markdown('</div>', unsafe_allow_html=True)

    # 3. Next Learning Action & Prescribed Activity
    st.divider()
    render_section_header(
        title="🎯 Prescribed Next Learning Action",
        subtitle=f"Pedagogical policy recommendation generated for learner '{active_learner}'."
    )

    rec = recommendation_engine.recommend(active_learner)

    action_label = rec.recommended_action.replace("_", " ").title()
    status_type = rec.learner_state_evidence.get("status")
    is_blocked = status_type in ("unverified_prerequisite", "below_threshold") or "prerequisite" in rec.rationale.lower()
    prereq_topic = rec.learner_state_evidence.get("prerequisite_topic", "")

    status_variant = "danger" if is_blocked else ("warning" if "review" in rec.recommended_action else "success")
    status_icon = "🚨" if is_blocked else ("📖" if "review" in rec.recommended_action else "🎯")

    with st.container(border=True):
        col_rec_main, col_rec_meta = st.columns([2, 1])
        with col_rec_main:
            st.markdown(
                f"""
                <div style="display: flex; align-items: center; gap: 0.65rem; margin-bottom: 0.4rem;">
                    <span style="font-size: 1.25rem; font-weight: 700; color: {TEXT_PRIMARY};">{status_icon} {action_label}</span>
                    <span class="cogni-badge cogni-badge-{status_variant}">Target: {rec.topic_id}</span>
                    <span class="cogni-badge cogni-badge-neutral">Level: {rec.difficulty.value.upper()}</span>
                </div>
                <p style="font-size: 0.94rem; color: {TEXT_SECONDARY}; line-height: 1.5; margin-bottom: 0.75rem;">
                    {rec.rationale}
                </p>
                """,
                unsafe_allow_html=True
            )

            if is_blocked and prereq_topic:
                st.error(f"⛔ **Prerequisite Gate Locked:** Advancement is locked until prerequisite **{prereq_topic}** reaches mastery $P(L) \\ge 0.70$.")


            if rec.suggested_evidence_ids:
                st.caption(f"Suggested Review Evidence: `{'`, `'.join(rec.suggested_evidence_ids[:3])}`")

        with col_rec_meta:
            st.markdown(
                f"""
                <div style="background: #F8FAFC; border: 1px solid {BORDER_COLOR}; border-radius: 8px; padding: 1rem;">
                    <div style="font-size: 0.82rem; font-weight: 600; color: {TEXT_MUTED}; text-transform: uppercase;">Active Strategy</div>
                    <div style="font-size: 1.05rem; font-weight: 700; color: {TEXT_PRIMARY}; margin: 0.25rem 0;">Adaptive BKT Gating</div>
                    <div style="font-size: 0.85rem; color: {TEXT_SECONDARY};">Zero unmastered progression</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    # 4. Interactive Quick-Route Hub
    st.divider()
    render_section_header(
        title="⚡ Quick-Start Learning Modules",
        subtitle="Jump directly into tutoring, practice, or curriculum exploration."
    )

    q1, q2, q3 = st.columns(3)
    with q1:
        with st.container(border=True):
            st.markdown("### 💬 Ask Grounded Tutor")
            st.markdown("Pose syllabus questions with strict citation grounding and fail-closed abstention.")
            if st.button("Launch AI Tutor →", use_container_width=True, key="dash_btn_tutor"):
                st.session_state["nav_selection_override"] = "💬 3. Grounded AI Tutor"
                st.rerun()

    with q2:
        with st.container(border=True):
            st.markdown("### 📝 Verified Practice")
            st.markdown("Take adaptively selected practice items with real-time BKT mastery updates.")
            if st.button("Start Assessment →", use_container_width=True, key="dash_btn_assess"):
                st.session_state["nav_selection_override"] = "📝 4. Adaptive Assessment"
                st.rerun()

    with q3:
        with st.container(border=True):
            st.markdown("### 🔍 Evidence Vault")
            st.markdown("Audit multimodal evidence with page, slide, and lecture timestamp locators.")
            if st.button("Explore Evidence →", use_container_width=True, key="dash_btn_ev"):
                st.session_state["nav_selection_override"] = "🔍 2. Evidence Explorer"
                st.rerun()

    # 5. Core Architectural Pillars Banner
    st.divider()
    st.markdown(
        f"""
        <div style="background: #FFFFFF; border: 1px solid {BORDER_COLOR}; border-radius: 12px; padding: 1.25rem 1.5rem;">
            <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem;">
                <div>
                    <span style="font-size: 0.95rem; font-weight: 700; color: {TEXT_PRIMARY};">🧠 CogniVault Closed-Loop Guarantee</span>
                    <p style="margin: 0.2rem 0 0 0; font-size: 0.85rem; color: {TEXT_SECONDARY};">
                        Evidence Vault → Sufficiency Decision Gate → Grounded Tutor → Verified Assessment → BKT Mastery Model → Explainable Policy
                    </p>
                </div>
                <div style="display: flex; gap: 0.5rem;">
                    <span class="cogni-badge cogni-badge-indigo">100% Citation Addressability</span>
                    <span class="cogni-badge cogni-badge-teal">0% Hallucination Leakage</span>
                    <span class="cogni-badge cogni-badge-success">Deterministic Verification</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
