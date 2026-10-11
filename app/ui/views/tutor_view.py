"""
Grounded AI Tutor View.
Conversational interface that enforces strict evidence retrieval, sufficiency gating,
resolvable citations, and transparent grounding audit traces.
"""
from __future__ import annotations

import streamlit as st
import pandas as pd
from app.tutor import GroundedTutor
from app.ui.components import (
    _render_html_fragment,
    render_page_header,
    render_section_header,
    render_callout,
    render_citation_card,
)


def render_tutor_view(services: dict):
    tutor: GroundedTutor = services["tutor"]

    render_page_header(
        title="AI Tutor",
        description="Ask questions about your course materials. Answers show supporting sources; when the material does not support an answer, CogniVault will tell you.",
        badge_text="Source-backed",
        badge_variant="indigo"
    )

    # Preset Quick Test Prompts
    render_section_header("💡 Suggested Curriculum Questions", subtitle="Select a preset prompt to test grounded synthesis or fail-closed abstention.")

    prompt_cols = st.columns(4)
    preset_query = None
    with prompt_cols[0]:
        if st.button("Direct: Newton's Law", use_container_width=True, help="Tests single-source Physics retrieval"):
            preset_query = "What is Newton's second law of motion and its mathematical formula?"
    with prompt_cols[1]:
        if st.button("Synthesis: Optics & Waves", use_container_width=True, help="Tests multi-source cross-synthesis"):
            preset_query = "How is Snell's law of refraction related to wave reflection in optics?"
    with prompt_cols[2]:
        if st.button("Math: Power Rule", use_container_width=True, help="Tests Calculus differentiation"):
            preset_query = "What is the derivative power rule for x^n in calculus?"
    with prompt_cols[3]:
        if st.button("Off-Corpus: French Rev", use_container_width=True, help="Tests fail-closed abstention gate"):
            preset_query = "What were the major economic causes of the French Revolution in 1789?"

    _render_html_fragment("<div style='margin-bottom: 0.75rem;'></div>")

    # Question Composer Container
    prefill_query = st.session_state.pop("tutor_prefill_query", "")
    active_default = preset_query if preset_query else prefill_query
    auto_trigger = bool(prefill_query and not preset_query)

    with st.container(border=True):
        user_query = st.text_input(
            "Ask a curriculum question:",
            value=active_default,
            placeholder="e.g., What is Newton's second law? How does cellular respiration work? What is the power rule?",
            help="Formulate any academic question grounded in the course materials."
        )

        col_btn, col_mode, col_k = st.columns([1.5, 1, 1])
        with col_btn:
            ask_btn = st.button("🚀 Ask Tutor", type="primary", use_container_width=True)
        with col_mode:
            retrieval_mode = st.selectbox("Retrieval Strategy", ["hybrid", "lexical", "semantic"], index=0)
        with col_k:
            top_k = st.slider("Max Evidence Candidates (k)", min_value=1, max_value=10, value=5)

    if (ask_btn or auto_trigger) and user_query.strip():
        with st.spinner("Retrieving evidence, evaluating sufficiency gate, and formulating grounded response..."):
            response = tutor.answer(user_query.strip(), k=top_k, mode=retrieval_mode)
            results, trace = tutor.retriever.search(user_query.strip(), k=top_k, mode=retrieval_mode)
            suff_eval = tutor.sufficiency_gate.evaluate(user_query.strip(), results, trace=trace, db=services["db"])

        _render_html_fragment("<div style='margin-bottom: 1.5rem;'></div>")

        # -------------------------------------------------------------
        # STATE 1: Grounded & Supported Answer
        # -------------------------------------------------------------
        if response.support_status == "supported":
            status_col1, status_col2 = st.columns([3, 1])
            with status_col1:
                _render_html_fragment("""
                    <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                        <span class="cogni-badge cogni-badge-success">🟢 Grounded in Curriculum Evidence</span>
                        <span style="font-size: 0.88rem; color: #16A34A; font-weight: 500;">Verified against indexed course units</span>
                    </div>
                    """)
            with status_col2:
                if response.is_synthesis:
                    _render_html_fragment('<div style="text-align: right;"><span class="cogni-badge cogni-badge-indigo">🔄 Cross-Source Synthesis</span></div>')
                else:
                    _render_html_fragment(f'<div style="text-align: right;"><span class="cogni-badge cogni-badge-neutral">Confidence: {response.confidence:.2f}</span></div>')

            # Tutor Answer Card
            _render_html_fragment(f"""
                <div style="
                    background: #FFFFFF;
                    border: 1px solid #E2E8F0;
                    border-left: 4px solid #4F46E5;
                    border-radius: 10px;
                    padding: 1.25rem 1.5rem;
                    margin-bottom: 1.5rem;
                    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.03);
                ">
                    <div style="font-size: 0.82rem; font-weight: 600; color: #4F46E5; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.5rem;">
                        Tutor Response
                    </div>
                    <div style="font-size: 1.02rem; color: #18233B; line-height: 1.65;">
                        {response.answer}
                    </div>
                </div>
                """)

            # Verified Source Citations
            render_section_header("📚 Verified Source Citations", subtitle="Every factual assertion in the response maps directly to these addressable units.")

            if response.citations:
                for idx, cite in enumerate(response.citations, 1):
                    loc = cite.location
                    if "page" in loc:
                        loc_str = f"Page {loc['page']}"
                    elif "slide" in loc:
                        loc_str = f"Slide {loc['slide']}"
                    elif "timestamp" in loc:
                        loc_str = f"Timestamp {loc['timestamp']}"
                    else:
                        loc_str = "Section"

                    render_citation_card(
                        index=idx,
                        evidence_id=cite.evidence_id,
                        source_title=cite.source_title or cite.source_id,
                        modality=cite.modality.value.upper(),
                        locator_str=loc_str,
                        snippet=cite.snippet,
                        source_path=cite.source_path
                    )
            else:
                st.caption("No explicit citations resolved.")

        # -------------------------------------------------------------
        # STATE 2: Fail-Closed Abstention (Off-Corpus / Insufficient)
        # -------------------------------------------------------------
        elif response.support_status == "unsupported":
            render_callout(
                title="Fail-Closed Abstention Enforced",
                message=f"CogniVault deterministically declined to answer. {response.unsupported_reason}",
                variant="warning",
                icon="⚠️"
            )

            _render_html_fragment(f"""
                <div style="
                    background: #FFFBEB;
                    border: 1px solid #FDE68A;
                    border-left: 4px solid #D97706;
                    border-radius: 10px;
                    padding: 1.25rem 1.5rem;
                    margin-bottom: 1.5rem;
                ">
                    <div style="font-size: 0.82rem; font-weight: 600; color: #D97706; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.5rem;">
                        Abstention Statement
                    </div>
                    <div style="font-size: 0.98rem; color: #18233B; line-height: 1.6;">
                        {response.answer}
                    </div>
                </div>
                """)

        # -------------------------------------------------------------
        # STATE 3: System Error
        # -------------------------------------------------------------
        else:
            render_callout(
                title="System Pipeline Error",
                message=f"{response.unsupported_reason}",
                variant="danger",
                icon="❌"
            )
            st.write(response.answer)

        # Grounding & Sufficiency Audit Trace Accordion
        with st.expander("🛠️ Inspect Grounding & Sufficiency Audit Trace", expanded=False):
            st.markdown("#### 1. Sufficiency Decision Gate Telemetry")
            st.json({
                "query": suff_eval.query,
                "is_sufficient": suff_eval.is_sufficient,
                "confidence_score": suff_eval.confidence,
                "decision_threshold": 0.35,
                "reason": suff_eval.reason,
                "supporting_evidence_ids": suff_eval.supporting_evidence_ids,
            })

            st.markdown("#### 2. Candidate Retrieval Scoring Matrix")
            cand_data = []
            for c in trace.candidates:
                cand_data.append({
                    "Rank": c.rank,
                    "Evidence ID": c.evidence_id,
                    "Source ID": c.source_id,
                    "Hybrid Score": round(c.score, 4),
                    "Lexical Score": round(c.lexical_score, 4),
                    "Semantic Score": round(c.semantic_score, 4),
                })
            if cand_data:
                st.dataframe(pd.DataFrame(cand_data), use_container_width=True, hide_index=True)
            else:
                st.caption("No candidate units retrieved.")

            if response.reasoning_steps:
                st.markdown("#### 3. Chain-of-Grounding Steps")
                for step in response.reasoning_steps:
                    st.markdown(f"- {step}")
