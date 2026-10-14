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
from app.ui.components import (
    _render_html_fragment,
    render_page_header,
    render_section_header,
    render_metric_card,
    render_callout,
    render_empty_state,
)


def render_evaluation_view(services: dict):
    db = services["db"]

    render_page_header(
        title="Evaluation Lab",
        description="Run reproducible checks on evidence retrieval, grounded answers, abstention, and adaptive learning behavior. This is an advanced evaluation area, not a student progress report.",
        badge_text="Advanced",
        badge_variant="indigo"
    )

    tab1, tab2, tab3 = st.tabs(["📊 Benchmark Suite", "🤖 Simulated Learner Trajectories", "📜 Metric Definitions & Disclosures"])

    # -----------------------------------------------------------------------
    # TAB 1: Benchmark Suite
    # -----------------------------------------------------------------------
    with tab1:
        col_run, col_info = st.columns([1, 2])
        with col_run:
            run_btn = st.button("🚀 Run Full Benchmark Suite", type="primary", use_container_width=True)

        benchmark_file = Path("evaluation/benchmark_results.json")
        data = None

        if run_btn:
            with st.spinner("Executing deterministic benchmark runner over test cases..."):
                runner = EvaluationRunner(db=db)
                runner.run_benchmark(output_path=benchmark_file)
                st.success("✅ Benchmark execution completed successfully!")

        if benchmark_file.exists():
            with open(benchmark_file, "r", encoding="utf-8") as f:
                data = json.load(f)

        if not data:
            render_empty_state(
                title="No Benchmark Results Found",
                description="Click 'Run Full Benchmark Suite' above to execute the deterministic evaluation over the benchmark test dataset.",
                icon="🧪"
            )
        else:
            metrics = data.get("metrics", {})
            total_cases = data.get("total_test_cases", 0)
            ver = data.get("benchmark_version", "1.0.0")
            ts = data.get("benchmark_timestamp", "")[:19].replace("T", " ")

            with col_info:
                _render_html_fragment(f"""
                    <div style="padding-top: 0.35rem; font-size: 0.88rem; color: #64748B;">
                        <strong>Version:</strong> <code>{ver}</code> &nbsp;|&nbsp;
                        <strong>Evaluated Cases:</strong> <code>{total_cases}</code> &nbsp;|&nbsp;
                        <strong>Timestamp:</strong> <code>{ts}</code>
                    </div>
                    """)

            # Metric Cards Row 1: Retrieval & Gating
            render_section_header("Retrieval & Sufficiency Gating", subtitle="Measures accuracy of candidate retrieval and precision of gatekeeping decisions.")
            r1_cols = st.columns(4)
            with r1_cols[0]:
                render_metric_card("Supported Answer Rate", f"{metrics.get('supported_answer_rate', 0.0):.1%}", subtext="In-corpus queries", badge="Tutor", badge_variant="indigo")
            with r1_cols[1]:
                render_metric_card("Abstention Rate", f"{metrics.get('unsupported_abstention_rate', 0.0):.1%}", subtext="Off-corpus queries", badge="Safety", badge_variant="warning")
            with r1_cols[2]:
                render_metric_card("Retrieval Precision@3", f"{metrics.get('retrieval_precision_at_3', 0.0):.1%}", subtext="Relevant / Retrieved", badge="Retrieval", badge_variant="teal")
            with r1_cols[3]:
                render_metric_card("Retrieval Recall@3", f"{metrics.get('retrieval_recall_at_3', 0.0):.1%}", subtext="Relevant / Expected", badge="Recall", badge_variant="teal")

            # Metric Cards Row 2: Faithfulness, Citations, & Zero-Leakage
            render_section_header("Citation Integrity & Leakage Prevention", subtitle="Verifies that all citations point to physical documents and no off-corpus information is fabricated.")
            r2_cols = st.columns(4)
            with r2_cols[0]:
                render_metric_card("Faithfulness Proxy", f"{metrics.get('grounded_faithfulness_proxy', 0.0):.1%}", subtext="Supported reasoning", badge="Factual", badge_variant="indigo")
            with r2_cols[1]:
                render_metric_card("Citation Addressability", f"{metrics.get('citation_addressability_rate', 0.0):.1%}", subtext="Valid IDs & sources", badge="Provenance", badge_variant="success")
            with r2_cols[2]:
                loc_acc = metrics.get('source_resolved_locator_accuracy', metrics.get('citation_locator_accuracy', 0.0))
                render_metric_card("Locator Accuracy", f"{loc_acc:.1%}", subtext="Page/slide/time match", badge="Locators", badge_variant="success")
            with r2_cols[3]:
                leak_val = metrics.get('unsupported_leakage_rate', 0.0)
                render_metric_card("Leakage Rate", f"{leak_val:.1%}", subtext="Hallucinations admitted", badge="Zero Target", badge_variant="success" if leak_val == 0 else "danger")

            # Metric Cards Row 3: Assessment, BKT, & Policy
            render_section_header("Assessment Engine & BKT Learner Modeling", subtitle="Structural verification of question items, BKT posterior calculation, and repetition gating.")
            r3_cols = st.columns(4)
            with r3_cols[0]:
                render_metric_card("Question Verification", f"{metrics.get('question_verification_accuracy', 0.0):.1%}", subtext="Structural integrity", badge="Assessment", badge_variant="indigo")
            with r3_cols[1]:
                render_metric_card("BKT Numerical Accuracy", f"{metrics.get('bkt_numerical_accuracy', 0.0):.1%}", subtext="Exact math transitions", badge="BKT", badge_variant="teal")
            with r3_cols[2]:
                render_metric_card("Policy Bracket Accuracy", f"{metrics.get('recommendation_policy_accuracy', 0.0):.1%}", subtext="Deterministic brackets", badge="Policy", badge_variant="indigo")
            with r3_cols[3]:
                passed_rep = metrics.get('repetition_control_pass')
                render_metric_card("Repetition Control", "Passed" if passed_rep else "Failed", subtext="Prevents duplicate items", badge="Anti-Repeat", badge_variant="success" if passed_rep else "danger")

            # Detailed Query-by-Query Results Table
            render_section_header("📋 Query-Level Grounding & Abstention Audit", subtitle="Individual test case traces confirming expected vs actual response statuses.")
            details = data.get("details", {})
            tutor_items = details.get("tutor_and_retrieval", [])

            qa_rows = []
            for item in tutor_items:
                is_supp = (item.get("expected_status") == "supported")
                qa_rows.append({
                    "Case ID": item.get("case_id"),
                    "Type": "Supported (In-Corpus)" if is_supp else "Unsupported (Off-Corpus)",
                    "Query": item.get("query"),
                    "Expected": item.get("expected_status"),
                    "Actual": item.get("actual_status"),
                    "Grounded": "✅" if item.get("is_grounded") else "❌",
                    "Citations": item.get("citations_count", 0),
                    "Precision@3": f"{item['precision_at_3']:.2%}" if isinstance(item.get("precision_at_3"), (int, float)) else "N/A",
                    "Recall@3": f"{item['recall_at_3']:.2%}" if isinstance(item.get("recall_at_3"), (int, float)) else "N/A",
                })

            if qa_rows:
                st.dataframe(pd.DataFrame(qa_rows), use_container_width=True, hide_index=True)

            with st.expander("📦 View Full Raw Benchmark Results JSON", expanded=False):
                st.json(data)

    # -----------------------------------------------------------------------
    # TAB 2: Simulated Learner Trajectories
    # -----------------------------------------------------------------------
    with tab2:
        render_section_header("Multi-Turn Simulated Learner Trajectories", subtitle="Evaluates adaptive pedagogical policy across 6 learner personas against a non-personalized baseline.")

        sim_file = Path("evaluation/simulation_results.json")
        sim_data = None

        if st.button("🚀 Re-Run Multi-Turn Learner Simulations", use_container_width=True):
            with st.spinner("Running 6 simulated learner trajectories & baseline comparison..."):
                sim_res = run_all_simulations(db_path="data/cognivault.sqlite")
                st.success("✅ Simulations completed!")
                sim_data = sim_res

        if sim_data is None and sim_file.exists():
            with open(sim_file, "r", encoding="utf-8") as f:
                sim_data = json.load(f)

        if not sim_data:
            render_empty_state(
                title="No Simulation Records Found",
                description="Click 'Re-Run Multi-Turn Learner Simulations' to execute and evaluate simulated learner personas.",
                icon="🤖"
            )
        else:
            scenarios = sim_data.get("scenarios", {})
            base_comp = sim_data.get("baseline_comparison", {})

            render_callout(
                title="Measurement Scope Disclosure",
                message=base_comp.get('measurement_scope', 'Policy behavior contrast between adaptive policy and static baseline.'),
                variant="indigo",
                icon="ℹ️"
            )

            b_cols = st.columns(2)
            with b_cols[0]:
                with st.container(border=True):
                    st.markdown("#### 🟢 CogniVault Adaptive Policy")
                    st.write("- **Advancing Learner:** Dynamically escalates from Easy → Medium → Hard as $P(L) > 0.85$.")
                    st.write("- **Struggling Learner:** Safely clamps to Easy Foundational Review when $P(L) < 0.40$.")
                    st.write("- **Misconception Routing:** Instantly diverts to prerequisite foundational remediation.")
                    st.write("- **Prerequisite Gatekeeper:** Strictly blocks advance topics if prerequisite $P(L) < 0.70$.")
            with b_cols[1]:
                with st.container(border=True):
                    st.markdown("#### ⚪ Non-Personalized Baseline")
                    st.write("- **Static Difficulty:** Always serves Medium difficulty regardless of performance.")
                    st.write("- **No Remediation:** Ignores repeated misconception error patterns.")
                    st.write("- **No Prerequisite Gating:** Attempts advanced topics without foundational readiness.")

            # Scenario Viewers
            for name, scenario in scenarios.items():
                with st.expander(f"👤 Persona: {name.replace('_', ' ').title()}", expanded=False):
                    if isinstance(scenario, list):
                        st.dataframe(pd.DataFrame(scenario), use_container_width=True, hide_index=True)
                    elif isinstance(scenario, dict):
                        st.json(scenario)

    # -----------------------------------------------------------------------
    # TAB 3: Metric Definitions & Protocol Disclosures
    # -----------------------------------------------------------------------
    with tab3:
        render_section_header("Formal Metric Definitions & Mathematical Formulas", subtitle="Rigorous mathematical formulas governing CogniVault's deterministic evaluation pipeline.")

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

        render_section_header("⚠️ Engineering & Scientific Disclosures", subtitle="Explicit boundaries and verification criteria.")
        render_callout(
            title="Structural Integrity vs Factual Ground Truth",
            message="Question verification certifies strict single-key matching, valid tolerances, prompt length, and evidence links; it does not constitute external real-world factual proof without LLM/expert validation.",
            variant="warning",
            icon="⚠️"
        )
        render_callout(
            title="Simulated Trajectories vs Real Learning Gains",
            message="Simulated learner evaluations demonstrate mathematical and policy compliance under controlled behavioral inputs; they do not measure real human student learning gains.",
            variant="neutral",
            icon="ℹ️"
        )
        render_callout(
            title="Deterministic Offline Execution",
            message="All test suites run locally and offline against fixed SQLite fixtures, ensuring zero external API latency, zero quota consumption, and zero non-deterministic drift.",
            variant="indigo",
            icon="🔒"
        )
