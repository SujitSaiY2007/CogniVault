"""
Learner Mastery Profile View.
Visualizes per-topic Bayesian Knowledge Tracing (BKT) mastery states,
historical practice submissions, accuracy analytics, and detected misconception signals.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd


def render_learner_view(services: dict):
    db = services["db"]
    st.header("📊 Learner Mastery Profile & BKT Analytics")
    st.markdown(
        """
        Inspect the persisted learner state. CogniVault tracks topic mastery using a **Bayesian Knowledge Tracing (BKT)**
        hidden Markov model ($P(L_0)=0.10, P(T)=0.15, P(S)=0.10, P(G)=0.20$).
        """
    )

    # Preset / Custom Learner Switcher
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
        chosen_learner = st.selectbox("Select Profile", preset_learners, index=0)
    with col_custom:
        custom_id = st.text_input("Or Enter Custom Learner ID", value=chosen_learner)

    active_learner_id = custom_id.strip() if custom_id.strip() else chosen_learner
    st.session_state.active_learner_id = active_learner_id

    st.subheader(f"👤 Profile: `{active_learner_id}`")

    # 1. Topic Mastery Table & Progress
    masteries = db.get_all_learner_masteries(active_learner_id)
    all_topics = db.all_topics()
    all_topic_ids = [t.name for t in all_topics]

    if not masteries:
        st.info(f"No mastery observations recorded yet for learner `{active_learner_id}`. Start practice in the **Adaptive Assessment** tab or run simulated evaluations.")
    else:
        st.markdown("#### 🎯 Per-Topic Mastery States ($P(L)$)")
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
        for m in masteries:
            prog_col1, prog_col2 = st.columns([3, 1])
            with prog_col1:
                st.progress(min(1.0, max(0.0, m.p_mastery)), text=f"{m.topic_id}: {m.p_mastery:.4f}")
            with prog_col2:
                st.caption(f"Attempts: {m.attempts} | Correct: {m.correct}")

    st.divider()

    # 2. Active Misconception Signals
    st.subheader("⚠️ Active Misconception Signals")
    misc_signals = db.get_active_misconceptions(active_learner_id)
    if not misc_signals:
        st.success("No active misconception signals detected for this learner.")
    else:
        for ms in misc_signals:
            with st.container(border=True):
                st.markdown(f"**Topic:** `{ms.topic_id}` | **Concept:** `{ms.concept_id}` | **Signal ID:** `{ms.signal_id}`")
                st.error(f"🚨 **Suspected Misconception:** {ms.suspected_misconception}")
                st.markdown(f"**Repeated Error Count:** `{ms.error_count}` | **Confidence:** `{ms.confidence:.2f}`")
                if ms.remediation_concept_id:
                    st.info(f"💡 **Remediation Target:** Review foundational concept `{ms.remediation_concept_id}`")
                if ms.remediation_note:
                    st.caption(f"Remediation Note: {ms.remediation_note}")

    st.divider()

    # 3. Complete Interaction History Table
    st.subheader("📜 Practice Interaction History")
    interactions = db.get_interactions(active_learner_id)
    if not interactions:
        st.write("No submitted interactions recorded.")
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
