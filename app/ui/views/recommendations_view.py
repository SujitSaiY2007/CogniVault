"""
Adaptive Recommendations & Prerequisite Readiness View.
Demonstrates the deterministic pedagogical decision policy,
prerequisite gatekeeper, and misconception remediation routing.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd
from app.recommendation import AdaptiveRecommendationEngine
from app.ui.components import (
    _render_html_fragment,
    render_page_header,
    render_section_header,
    render_metric_card,
    render_callout,
    render_empty_state,
)


def render_recommendations_view(services: dict):
    db = services["db"]
    engine: AdaptiveRecommendationEngine = services["recommendations"]

    render_page_header(
        title="Adaptive Recommendations & Prerequisite Readiness",
        description="Explainable next-step pedagogical recommendations. CogniVault strictly enforces BKT mastery bands, active misconception routing, and prerequisite readiness gates (P >= 0.70).",
        badge_text="Module 6",
        badge_variant="indigo"
    )

    all_topics = [t.name for t in db.all_topics()]
    if not all_topics:
        render_empty_state(
            title="Curriculum Topics Not Found",
            description="No topics available in database. Please seed or index curriculum materials in Course Setup first.",
            icon="📂"
        )
        return

    # Configuration Card
    with st.container(border=True):
        col_learner, col_topic = st.columns([1, 1])
        with col_learner:
            active_learner_id = st.text_input("Active Learner ID", value=st.session_state.active_learner_id)
            st.session_state.active_learner_id = active_learner_id
        with col_topic:
            eval_topic = st.selectbox("Evaluate Recommendation For Topic", ["Auto (Global Weakest)"] + all_topics)

    target_topic_id = None if eval_topic == "Auto (Global Weakest)" else eval_topic

    # Generate Recommendation
    rec = engine.recommend(active_learner_id, active_topic_id=target_topic_id)

    # Main Prescribed Recommendation Card
    with st.container(border=True):
        header_cols = st.columns([2.5, 1, 1.2])
        with header_cols[0]:
            action_title = rec.recommended_action.replace("_", " ").upper()
            _render_html_fragment(f"""
                <div style="font-size: 0.82rem; font-weight: 600; color: #64748B; text-transform: uppercase; letter-spacing: 0.04em;">
                    Prescribed Learning Action
                </div>
                <div style="font-size: 1.35rem; font-weight: 700; color: #18233B; margin: 0.2rem 0;">
                    {action_title}
                </div>
                <div style="font-size: 0.95rem; color: #4F46E5; font-weight: 500;">
                    Target: <strong>{rec.topic_id}</strong> {f'({rec.concept_id})' if rec.concept_id else ''}
                </div>
                """)
        with header_cols[1]:
            _render_html_fragment(f"""
                <div style="font-size: 0.82rem; font-weight: 600; color: #64748B; text-transform: uppercase; letter-spacing: 0.04em;">
                    Recommended Level
                </div>
                <div style="margin-top: 0.4rem;">
                    <span class="cogni-badge cogni-badge-neutral">{rec.difficulty.value.upper()}</span>
                </div>
                """)
        with header_cols[2]:
            if rec.recommended_action == "remediate_misconception":
                badge_html = '<span class="cogni-badge cogni-badge-danger">🚨 Misconception Alert</span>'
            elif rec.recommended_action == "foundational_review":
                badge_html = '<span class="cogni-badge cogni-badge-warning">⚠️ Foundational Review</span>'
            elif rec.recommended_action == "advance_topic":
                badge_html = '<span class="cogni-badge cogni-badge-success">🌟 Mastery Achieved</span>'
            else:
                badge_html = '<span class="cogni-badge cogni-badge-indigo">🎯 Targeted Practice</span>'

            _render_html_fragment(f"""
                <div style="display: flex; justify-content: flex-end; align-items: center; height: 100%;">
                    {badge_html}
                </div>
                """)

        _render_html_fragment(f"""
            <div style="
                background: #F8FAFC;
                border-left: 3px solid #4F46E5;
                padding: 1rem 1.25rem;
                border-radius: 4px;
                margin: 1.25rem 0 1rem 0;
            ">
                <div style="font-size: 0.84rem; font-weight: 600; color: #4F46E5; margin-bottom: 0.35rem; text-transform: uppercase;">
                    Pedagogical Rationale
                </div>
                <div style="font-size: 0.96rem; color: #18233B; line-height: 1.6;">
                    {rec.rationale}
                </div>
            </div>
            """)

        if rec.learner_state_evidence:
            with st.expander("🔍 Learner State Evidence & Policy Telemetry", expanded=False):
                st.json(rec.learner_state_evidence)

        if rec.suggested_evidence_ids:
            render_section_header("📚 Suggested Review Evidence Units", subtitle="Curriculum units recommended for prerequisite revision before re-attempting practice.")
            for eid in rec.suggested_evidence_ids:
                ev = db.get_evidence(eid)
                if ev:
                    source = db.get_source(ev.source_id)
                    loc = ev.location
                    loc_str = f"Page {loc.get('page', '')}" if "page" in loc else (f"Slide {loc.get('slide', '')}" if "slide" in loc else "Section")
                    _render_html_fragment(f"""
                        <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 6px; padding: 0.65rem 0.95rem; margin-bottom: 0.5rem;">
                            <div style="display: flex; gap: 0.5rem; align-items: center; margin-bottom: 0.25rem;">
                                <span class="cogni-badge cogni-badge-neutral">{eid}</span>
                                <strong>{source.title if source else ev.source_id}</strong>
                                <span class="cogni-badge cogni-badge-neutral">{ev.modality.value.upper()} | {loc_str}</span>
                            </div>
                            <div style="font-size: 0.88rem; color: #475569; line-height: 1.4;">
                                {ev.text[:220]}...
                            </div>
                        </div>
                        """)

    _render_html_fragment("<div style='margin-bottom: 1.5rem;'></div>")

    # 2. Prerequisite Topology & Gatekeeper Audit
    render_section_header(
        "🌳 Prerequisite Topology & Gatekeeper Audit",
        subtitle="CogniVault enforces strict prerequisite gating: missing observations or P(L) < 0.70 blocks advancement."
    )

    prereq_rows = []
    for t in all_topics:
        prereqs = db.get_all_prerequisites(t)
        t_mastery = db.get_learner_mastery(active_learner_id, t)
        t_score = t_mastery.p_mastery if t_mastery else 0.10

        if not prereqs:
            prereq_rows.append({
                "Topic": t,
                "Current Mastery": round(t_score, 4),
                "Prerequisites": "None (Root Concept)",
                "Prerequisite Mastery": "N/A",
                "Gatekeeper Status": "✅ Ready",
            })
        else:
            for p in prereqs:
                p_mastery = db.get_learner_mastery(active_learner_id, p)
                if p_mastery is None:
                    status = "❌ Blocked (Unverified Prerequisite)"
                    p_score_str = "None (Unobserved)"
                elif p_mastery.p_mastery < 0.70:
                    status = f"❌ Blocked (Prerequisite P={p_mastery.p_mastery:.2f} < 0.70)"
                    p_score_str = f"{p_mastery.p_mastery:.4f}"
                else:
                    status = f"✅ Satisfied (Prerequisite P={p_mastery.p_mastery:.2f} >= 0.70)"
                    p_score_str = f"{p_mastery.p_mastery:.4f}"

                prereq_rows.append({
                    "Topic": t,
                    "Current Mastery": round(t_score, 4),
                    "Prerequisites": p,
                    "Prerequisite Mastery": p_score_str,
                    "Gatekeeper Status": status,
                })

    df_prereqs = pd.DataFrame(prereq_rows)
    st.dataframe(df_prereqs, use_container_width=True, hide_index=True)
