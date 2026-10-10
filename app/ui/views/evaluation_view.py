"""
Deterministic Benchmark & Evaluation View.
Executes and displays reproducible offline benchmark results,
detailed query-level traces, and simulated multi-turn learner trajectories.
"""
from __future__ import annotations

import json
from pathlib import Path
import streamlit as st
import pandas as pd

from evaluation.runner import EvaluationRunner
from evaluation.simulate_learners import run_all_simulations


def render_evaluation_view(services: dict):
    db = services["db"]
    st.header("🧪 Deterministic Evaluation & Benchmark Runner")
    st.markdown(
        """
        Evaluate CogniVault against reproducible, offline ground-truth benchmarks.
        All metrics are strictly calculated from deterministic checks and verifiable curriculum evidence.
        """
    )

    tab1, tab2, tab3 = st.tabs(["📊 Benchmark Suite", "🤖 Simulated Learner Trajectories", "📜 Metric Definitions & Protocols"])

    # -----------------------------------------------------------------------
    # TAB 1: Benchmark Suite
    # -----------------------------------------------------------------------
    with tab1:
        col_run, col_file = st.columns([1, 1])
        with col_run:
            run_btn = st.button("🚀 Run Full Benchmark Suite", type="primary", use_container_width=True)

        benchmark_file = Path("evaluation/benchmark_results.json")
        data = None

        if run_btn:
            with st.spinner("Executing deterministic benchmark runner over test dataset..."):
                runner = EvaluationRunner(db=db)
                runner.run_benchmark(output_path=benchmark_file)
                st.success(" Benchmark execution completed successfully!")

        if benchmark_file.exists():
            with open(benchmark_file, "r", encoding="utf-8") as f:
                data = json.load(f)

        if not data:
            st.info("No benchmark results found. Click **'Run Full Benchmark Suite'** to execute.")
        else:
            metrics = data.get("metrics", {})
            st.markdown(f"**Benchmark Version:** `{data.get('benchmark_version', '1.0.0')}` | **Evaluated Test Cases:** `{data.get('total_test_cases', 0)}` | **Timestamp:** `{data.get('benchmark_timestamp', '')}`")

            # Metric Cards Row 1: Retrieval & Sufficiency
            st.markdown("### 📊 Benchmark Metrics")
            r1_cols = st.columns(4)
            with r1_cols[0]:
                st.metric("Supported Answer Rate", f"{metrics.get('supported_answer_rate', 0.0):.2%}")
            with r1_cols[1]:
                st.metric("Abstention Rate", f"{metrics.get('unsupported_abstention_rate', 0.0):.2%}")
            with r1_cols[2]:
                st.metric("Retrieval Precision@3", f"{metrics.get('retrieval_precision_at_3', 0.0):.2%}")
            with r1_cols[3]:
                st.metric("Retrieval Recall@3", f"{metrics.get('retrieval_recall_at_3', 0.0):.2%}")

            # Metric Cards Row 2: Faithfulness, Citations, & Repetition
            r2_cols = st.columns(4)
            with r2_cols[0]:
                st.metric("Faithfulness Proxy", f"{metrics.get('grounded_faithfulness_proxy', 0.0):.2%}")
            with r2_cols[1]:
                st.metric("Citation Addressability", f"{metrics.get('citation_addressability_rate', 0.0):.2%}")
            with r2_cols[2]:
                st.metric("Locator Accuracy", f"{metrics.get('citation_locator_accuracy', 0.0):.2%}")
            with r2_cols[3]:
                st.metric("Leakage Rate", f"{metrics.get('unsupported_leakage_rate', 0.0):.2%}")

            # Metric Cards Row 3: Assessment, BKT, & Policy
            r3_cols = st.columns(4)
            with r3_cols[0]:
                st.metric("Question Verification", f"{metrics.get('question_verification_accuracy', 0.0):.2%}")
            with r3_cols[1]:
                st.metric("BKT Numerical Accuracy", f"{metrics.get('bkt_numerical_accuracy', 0.0):.2%}")
            with r3_cols[2]:
                st.metric("Policy Bracket Accuracy", f"{metrics.get('recommendation_policy_accuracy', 0.0):.2%}")
            with r3_cols[3]:
                st.metric("Repetition Control", " Passed" if metrics.get('repetition_control_pass') else "❌ Failed")

            st.divider()

            # Detailed Query-by-Query Results Table
            st.subheader("📋 Supported & Unsupported Q&A Test Details")
            details = data.get("details", {})
            supp_items = details.get("supported_qa_results", [])
            unsupp_items = details.get("unsupported_qa_results", [])

            qa_rows = []
            for item in supp_items:
                qa_rows.append({
                    "Query ID": item.get("id"),
                    "Type": "Supported (In-Corpus)",
                    "Query": item.get("query"),
                    "Pass / Correct": " " if item.get("pass") else "❌",
                    "Status": item.get("support_status"),
                    "Citations": len(item.get("citations", [])),
                })
            for item in unsupp_items:
                qa_rows.append({
                    "Query ID": item.get("id"),
                    "Type": "Unsupported (Off-Corpus)",
                    "Query": item.get("query"),
                    "Pass / Correct": " " if item.get("pass") else "❌",
                    "Status": item.get("support_status"),
                    "Citations": len(item.get("citations", [])),
                })

            if qa_rows:
                st.dataframe(pd.DataFrame(qa_rows), use_container_width=True, hide_index=True)

            with st.expander("📦 View Full Raw Benchmark Results JSON"):
                st.json(data)

    # -----------------------------------------------------------------------
    # TAB 2: Simulated Learner Trajectories
    # -----------------------------------------------------------------------
    with tab2:
        st.subheader("Multi-Turn Simulated Learner Evaluations")
        st.markdown(
            """
            Simulated learner models evaluate CogniVault's adaptive pedagogical loops across distinct learner personas
            and compare against a non-personalized baseline.
            """
        )

        sim_file = Path("evaluation/simulation_results.json")
        sim_data = None

        if st.button("🚀 Re-Run Multi-Turn Learner Simulations", use_container_width=True):
            with st.spinner("Running 6 simulated learner trajectories & baseline comparison..."):
                sim_res = run_all_simulations(db_path="data/cognivault.sqlite")
                st.success(" Simulations completed!")
                sim_data = sim_res

        if sim_data is None and sim_file.exists():
            with open(sim_file, "r", encoding="utf-8") as f:
                sim_data = json.load(f)

        if not sim_data:
            st.info("No simulation records found. Click **'Re-Run Multi-Turn Learner Simulations'** to execute.")
        else:
            scenarios = sim_data.get("scenarios", {})

            # Baseline Comparison Highlights
            st.markdown("### 📈 Adaptive Policy vs Fixed Non-Personalized Baseline")
            base_comp = sim_data.get("baseline_comparison", {})
            st.info(f"**Measurement Scope:** {base_comp.get('measurement_scope', 'Policy behavior contrast')}")

            b_cols = st.columns(2)
            with b_cols[0]:
                with st.container(border=True):
                    st.markdown("#### 🟢 CogniVault Adaptive Policy")
                    st.write("- **Advancing:** Dynamically escalates from Easy → Medium → Hard as $P(L) > 0.85$.")
                    st.write("- **Struggling:** Safely clamps to Easy Foundational Review ($P(L) < 0.40$).")
                    st.write("- **Misconceptions:** Instantly diverts to prerequisite remediation.")
                    st.write("- **Prerequisites:** Blocks advancement if prerequisite unverified or $<0.70$.")
            with b_cols[1]:
                with st.container(border=True):
                    st.markdown("#### ⚪ Non-Personalized Baseline")
                    st.write("- **Static Difficulty:** Always serves Medium difficulty regardless of performance.")
                    st.write("- **No Remediation:** Ignores repeated misconception errors.")
                    st.write("- **No Prerequisite Gating:** Attempts advanced topics without foundational readiness.")

            st.divider()

            # Detailed Scenario Viewers
            for name, scenario in scenarios.items():
                with st.expander(f"👤 Scenario: {name.replace('_', ' ').title()}", expanded=False):
                    if isinstance(scenario, list):
                        st.dataframe(pd.DataFrame(scenario), use_container_width=True, hide_index=True)
                    elif isinstance(scenario, dict):
                        st.json(scenario)


    # -----------------------------------------------------------------------
    # TAB 3: Metric Definitions & Protocol Disclosures
    # -----------------------------------------------------------------------
    with tab3:
        st.subheader("📜 Formal Metric Definitions & Mathematical Formulas")
        st.markdown(
            r"""
            1. **Retrieval Precision@K:**
               $$\text{Precision@K} = \frac{|\text{Retrieved Candidates} \cap \text{Expected Evidence}|}{\min(K, |\text{Retrieved Candidates}|)}$$
            2. **Retrieval Recall@K:**
               $$\text{Recall@K} = \frac{|\text{Retrieved Candidates} \cap \text{Expected Evidence}|}{|\text{Expected Evidence}|}$$
            3. **Sufficiency Gating Accuracy:**
               $$\text{Accuracy}_{\text{suff}} = \frac{\sum_{i=1}^N \mathbf{1}(\text{Predicted Sufficiency}_i = \text{Ground Truth Sufficiency}_i)}{N}$$
            4. **Unsupported Question Abstention Rate:**
               $$\text{Abstention Rate} = \frac{\sum_{q \in Q_{\text{unsupported}}} \mathbf{1}(\text{Status}(q) = \text{'unsupported'})}{|Q_{\text{unsupported}}|}$$
            5. **Unsupported Answer Leakage Rate:**
               $$\text{Leakage Rate} = \frac{\sum_{q \in Q_{\text{unsupported}}} \mathbf{1}(\text{Status}(q) \neq \text{'unsupported'})}{|Q_{\text{unsupported}}|}$$
            6. **Citation Validity & Addressability:**
               $$\text{Validity} = \frac{|\{c \in \text{Citations} \mid \text{Resolve}(c.\text{id}) \neq \text{None} \land c.\text{locator matches source}\}|}{|\text{Citations}|}$$
            7. **Bayesian Knowledge Tracing (BKT) Posterior Formula:**
               - *Correct observation ($O_t = 1$):*
                 $$P(L_t \mid O_t=1) = \frac{P(L_{t-1})(1 - P(S))}{P(L_{t-1})(1 - P(S)) + (1 - P(L_{t-1}))P(G)}$$
               - *Incorrect observation ($O_t = 0$):*
                 $$P(L_t \mid O_t=0) = \frac{P(L_{t-1})P(S)}{P(L_{t-1})P(S) + (1 - P(L_{t-1}))(1 - P(G))}$$
               - *Transition update:*
                 $$P(L_t) = P(L_t \mid O_t) + (1 - P(L_t \mid O_t))P(T)$$
            """
        )

        st.subheader("⚠️ Engineering & Scientific Disclosures")
        st.warning(
            """
            - **Structural Integrity vs Factual Ground Truth:** Question verification certifies strict single-key matching, valid tolerances, prompt length, and evidence links; it does not constitute external real-world factual proof without LLM/expert validation.
            - **Simulated Trajectories vs Real Learning Gains:** Simulated learner evaluations demonstrate mathematical and policy compliance; they do not measure real human student learning gains.
            - **Deterministic Proxy:** Deterministic test suites run locally and offline without external API latency or non-deterministic drift.
            """
        )
