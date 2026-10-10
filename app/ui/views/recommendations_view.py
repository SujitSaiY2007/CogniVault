r"""
Adaptive Recommendations & Prerequisite Readiness View.
Demonstrates the deterministic pedagogical decision policy,
prerequisite gatekeeper, and misconception remediation routing.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd
from app.recommendation import AdaptiveRecommendationEngine


def render_recommendations_view(services: dict):
    db = services["db"]
    engine: AdaptiveRecommendationEngine = services["recommendations"]
    st.header("🎯 Adaptive Recommendations & Prerequisite Readiness")
    st.markdown(
        r"""
        Inspect the explainable next-step pedagogical policy.
        Recommendations strictly enforce BKT mastery bands ($<0.40, [0.40, 0.70), [0.70, 0.85], >0.85$),
        active misconception remediation, and prerequisite readiness gates ($\ge 0.70$).
        """
    )

    all_topics = [t.name for t in db.all_topics()]
    if not all_topics:
        st.warning("No curriculum topics found. Please index course materials first.")
        return

    # Controls
    col_learner, col_topic = st.columns([1, 1])
    with col_learner:
        active_learner_id = st.text_input("Active Learner ID", value=st.session_state.active_learner_id)
        st.session_state.active_learner_id = active_learner_id
    with col_topic:
        eval_topic = st.selectbox("Evaluate Recommendation For Topic", ["Auto (Global Weakest)"] + all_topics)

    target_topic_id = None if eval_topic == "Auto (Global Weakest)" else eval_topic

    # Generate Recommendation
    rec = engine.recommend(active_learner_id, active_topic_id=target_topic_id)

    # 1. Main Recommendation Banner
    with st.container(border=True):
        header_cols = st.columns([2, 1, 1])
        with header_cols[0]:
            st.markdown(f"### Recommended Action: `{rec.recommended_action.upper()}`")
            st.markdown(f"**Target Topic:** `{rec.topic_id}`")
            if rec.concept_id:
                st.caption(f"Target Concept: `{rec.concept_id}`")
        with header_cols[1]:
            st.markdown(f"**Recommended Difficulty:** `{rec.difficulty.value.upper()}`")
        with header_cols[2]:
            if rec.recommended_action == "remediate_misconception":
                st.error("🚨 Misconception Alert")
            elif rec.recommended_action == "foundational_review":
                st.warning("⚠️ Foundational Review")
            elif rec.recommended_action == "advance_topic":
                st.success("🌟 Mastery Achieved")
            else:
                st.info("🎯 Practice Mode")

        st.divider()
        st.markdown(f"#### 📖 Pedagogical Rationale\n{rec.rationale}")

        if rec.learner_state_evidence:
            with st.expander("🔍 Learner State Evidence Breakdown", expanded=True):
                st.json(rec.learner_state_evidence)

        if rec.suggested_evidence_ids:
            st.subheader("📚 Suggested Review Evidence Units")
            for eid in rec.suggested_evidence_ids:
                ev = db.get_evidence(eid)
                if ev:
                    source = db.get_source(ev.source_id)
                    loc = ev.location
                    loc_str = f"Page {loc.get('page', '')}" if "page" in loc else (f"Slide {loc.get('slide', '')}" if "slide" in loc else "Section")
                    st.markdown(f"- **`{eid}`** — *{source.title if source else ev.source_id}* ({ev.modality.value.upper()}, {loc_str}): {ev.text[:180]}...")

    st.divider()

    # 2. Prerequisite Topology & Readiness Matrix
    st.subheader("🌳 Prerequisite Topology & Gatekeeper Audit")
    st.markdown("CogniVault enforces: *A missing mastery record or $P(L) < 0.70$ on a prerequisite blocks advancement to dependent topics.*")

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
                "Gatekeeper Status": " Ready",
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
                    status = f" Satisfied (Prerequisite P={p_mastery.p_mastery:.2f} >= 0.70)"
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
