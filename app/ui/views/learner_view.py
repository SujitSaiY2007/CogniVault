"""
Learner Mastery Profile View.
Visualizes per-topic Bayesian Knowledge Tracing (BKT) mastery states,
historical practice submissions, accuracy analytics, and detected misconception signals.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd
from app.ui.components import (
    render_page_header,
    render_section_header,
    render_metric_card,
    render_callout,
    render_empty_state,
)


def render_learner_view(services: dict):
    db = services["db"]

    render_page_header(
        title="Learner Mastery Profile & BKT Analytics",
        description="Inspect persisted learner states tracked via Bayesian Knowledge Tracing (BKT). Posterior belief estimates reflect probabilistic mastery across curriculum topics.",
        badge_text="Module 5",
        badge_variant="indigo"
    )

    # Preset / Custom Learner Switcher Card
    with st.container(border=True):
        preset_learners = [
            "learner_demo",
            "sim_advancing",
            "sim_struggling",
            "sim_mixed",
            "sim_misconception",
            "sim_prereq_gated",
        ]

        col_sel, col_custom = st.columns([1, 1])
        with col_sel:
            chosen_learner = st.selectbox("Select Benchmark / Demo Profile", preset_learners, index=0)
        with col_custom:
            custom_id = st.text_input("Or Enter Custom Learner ID", value=chosen_learner)

    active_learner_id = custom_id.strip() if custom_id.strip() else chosen_learner
    st.session_state.active_learner_id = active_learner_id

    # Retrieve State
    masteries = db.get_all_learner_masteries(active_learner_id)
    misc_signals = db.get_active_misconceptions(active_learner_id)
    interactions = db.get_interactions(active_learner_id)

    # Top-level summary KPIs
    if masteries:
        tot_attempts = sum(m.attempts for m in masteries)
        tot_correct = sum(m.correct for m in masteries)
        overall_acc = (tot_correct / tot_attempts * 100) if tot_attempts > 0 else 0.0
        avg_mastery = sum(m.p_mastery for m in masteries) / len(masteries)

        col_k1, col_k2, col_k3, col_k4 = st.columns(4)
        with col_k1:
            render_metric_card("Observed Topics", len(masteries), subtext="Evaluated curriculum units", badge="Coverage", badge_variant="indigo")
        with col_k2:
            render_metric_card("Average Mastery", f"{avg_mastery:.4f}", subtext="Mean BKT posterior", badge="P(L)", badge_variant="teal")
        with col_k3:
            render_metric_card("Overall Accuracy", f"{overall_acc:.1f}%", subtext=f"{tot_correct}/{tot_attempts} submissions", badge="Historical", badge_variant="success")
        with col_k4:
            render_metric_card("Active Misconceptions", len(misc_signals), subtext="Requires remediation", badge="Alerts", badge_variant="danger" if misc_signals else "neutral")

        st.markdown("<div style='margin-bottom: 1.25rem;'></div>", unsafe_allow_html=True)

    # 1. Topic Mastery Table & Visual Progress Bars
    render_section_header("🎯 Per-Topic Mastery States (BKT)", subtitle="Probabilistic estimates based on hidden Markov model parameters P(L0)=0.10, P(T)=0.15, P(S)=0.10, P(G)=0.20.")

    if not masteries:
        render_empty_state(
            title=f"No Mastery Observations for '{active_learner_id}'",
            description="This profile has no recorded practice interactions yet. Start a session in the Adaptive Assessment tab to build mastery history.",
            icon="📊"
        )
    else:
        mastery_rows = []
        for m in masteries:
            p = m.p_mastery
            if p < 0.40:
                band = "Foundational Review (Easy)"
                bracket = "p < 0.40"
            elif p < 0.70:
                band = "Targeted Practice (Medium)"
                bracket = "0.40 <= p < 0.70"
            elif p <= 0.85:
                band = "Mixed Application (Medium)"
                bracket = "0.70 <= p <= 0.85"
            else:
                band = "Advance Topic (Hard)"
                bracket = "p > 0.85"

            acc = (m.correct / m.attempts * 100) if m.attempts > 0 else 0.0
            mastery_rows.append({
                "Topic": m.topic_id,
                "Mastery P(L)": round(p, 4),
                "Policy Bracket": band,
                "Range Rule": bracket,
                "Attempts": m.attempts,
                "Correct": m.correct,
                "Accuracy (%)": f"{acc:.1f}%",
                "Last Seen": m.last_seen or "—",
            })

        df_mastery = pd.DataFrame(mastery_rows)
        st.dataframe(df_mastery, use_container_width=True, hide_index=True)

        # Progress Visualizers
        st.markdown("<div style='margin-bottom: 0.5rem;'></div>", unsafe_allow_html=True)
        for m in masteries:
            with st.container(border=True):
                p_val = min(1.0, max(0.0, m.p_mastery))
                col_name, col_stat = st.columns([2.5, 1])
                with col_name:
                    st.markdown(f"**{m.topic_id}** — Mastery $P(L) = {m.p_mastery:.4f}$")
                with col_stat:
                    st.caption(f"Attempts: {m.attempts} | Correct: {m.correct}")
                st.progress(p_val)

    st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)

    # 2. Active Misconception Signals
    render_section_header("⚠️ Active Misconception Diagnostics", subtitle="Automated detection of repeated bug library errors and systematic misconceptions.")

    if not misc_signals:
        render_callout(
            title="Clean Diagnostic Profile",
            message="No repeated misconception signals or bug patterns detected for this learner profile.",
            variant="success",
            icon="✅"
        )
    else:
        for ms in misc_signals:
            with st.container(border=True):
                st.markdown(
                    f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <span class="cogni-badge cogni-badge-danger">🚨 Suspected Misconception</span>
                        <span class="cogni-badge cogni-badge-neutral">Error Count: {ms.error_count} (Confidence: {ms.confidence:.2f})</span>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                st.markdown(f"**Topic:** `{ms.topic_id}` | **Concept:** `{ms.concept_id}`")
                st.error(f"**Diagnostic Finding:** {ms.suspected_misconception}")
                if ms.remediation_concept_id:
                    st.info(f"💡 **Remediation Action:** Review foundational prerequisite `{ms.remediation_concept_id}`")
                if ms.remediation_note:
                    st.caption(f"Clinical Note: {ms.remediation_note}")

    st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)

    # 3. Complete Interaction History Table
    render_section_header("📜 Practice Interaction History", subtitle="Audit log of all questions attempted by this learner profile.")

    if not interactions:
        st.caption("No historical practice submissions recorded.")
    else:
        hist_rows = []
        for i in reversed(interactions):
            hist_rows.append({
                "Timestamp": i["timestamp"],
                "Question ID": i["question_id"],
                "Topic": i["topic_id"],
                "Learner Answer": i["user_answer"],
                "Result": "✅ Correct" if i["is_correct"] else "❌ Incorrect",
                "Feedback": i["feedback"][:120] + ("..." if len(i["feedback"]) > 120 else ""),
            })
        df_hist = pd.DataFrame(hist_rows)
        st.dataframe(df_hist, use_container_width=True, hide_index=True)
