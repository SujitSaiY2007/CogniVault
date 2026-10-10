"""
Grounded AI Tutor View.
Conversational interface that enforces strict evidence retrieval, sufficiency gating,
resolvable citations, and transparent grounding audit traces.
"""
from __future__ import annotations

import streamlit as st
from app.tutor import GroundedTutor
from app.sufficiency import EvidenceSufficiencyGate


def render_tutor_view(services: dict):
    tutor: GroundedTutor = services["tutor"]
    st.header("💬 Grounded AI Tutor")
    st.markdown(
        """
        Ask questions grounded strictly in the verified course material.
        If a question cannot be supported with sufficient evidence from the curriculum, CogniVault **abstains**
        rather than hallucinating.
        """
    )

    # Preset Sample Questions for Quick Testing
    st.markdown("**💡 Quick Test Prompts:**")
    prompt_cols = st.columns(4)
    preset_query = None
    with prompt_cols[0]:
        if st.button("Direct: Newton's Law", use_container_width=True):
            preset_query = "What is Newton's second law of motion and its mathematical formula?"
    with prompt_cols[1]:
        if st.button("Synthesis: Optics & Waves", use_container_width=True):
            preset_query = "How is Snell's law of refraction related to wave reflection in optics?"
    with prompt_cols[2]:
        if st.button("Math: Power Rule", use_container_width=True):
            preset_query = "What is the derivative power rule for x^n in calculus?"
    with prompt_cols[3]:
        if st.button("Off-Corpus: French Rev", use_container_width=True):
            preset_query = "What were the major economic causes of the French Revolution in 1789?"

    # Input form
    user_query = st.text_input(
        "Enter your question for the tutor:",
        value=preset_query if preset_query else "",
        placeholder="Ask any question on Physics, Optics, Calculus, or Biology..."
    )

    col_btn, col_mode, col_k = st.columns([1, 1, 1])
    with col_btn:
        ask_btn = st.button("Ask Tutor", type="primary", use_container_width=True)
    with col_mode:
        retrieval_mode = st.selectbox("Retrieval Mode", ["hybrid", "lexical", "semantic"], index=0)
    with col_k:
        top_k = st.slider("Max Evidence Candidates (k)", min_value=1, max_value=10, value=5)

    if ask_btn and user_query.strip():
        with st.spinner("Retrieving evidence, evaluating sufficiency, and formulating grounded answer..."):
            # Execute Grounded Tutor Pipeline
            response = tutor.answer(user_query.strip(), k=top_k, mode=retrieval_mode)

            # Retrieve audit trace details
            results, trace = tutor.retriever.search(user_query.strip(), k=top_k, mode=retrieval_mode)
            suff_eval = tutor.sufficiency_gate.evaluate(user_query.strip(), results, trace=trace, db=services["db"])

        st.divider()

        # Render Response Status
        if response.support_status == "supported":
            status_col1, status_col2 = st.columns([3, 1])
            with status_col1:
                st.success("🟢 **Grounded in Course Evidence** — Answer verified against curriculum materials.")
            with status_col2:
                if response.is_synthesis:
                    st.info("🔄 **Cross-Source Synthesis**")
                else:
                    st.caption(f"Confidence: {response.confidence:.2f}")

            # Tutor Answer
            st.markdown(f"### Tutor Response\n{response.answer}")

            # Citations Display
            st.subheader("📚 Verified Source Citations")
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

                    with st.expander(f"[{idx}] Evidence `{cite.evidence_id}` — {cite.source_title or cite.source_id} ({cite.modality.value.upper()}, {loc_str})", expanded=True):
                        st.markdown(f"**Exact Source Locator:** `{loc_str}`")
                        st.markdown(f"**Supporting Excerpt:**\n> {cite.snippet}")
                        if cite.source_path:
                            st.caption(f"Source file: `{cite.source_path}`")
            else:
                st.write("No explicit citations resolved.")

        elif response.support_status == "unsupported":
            st.warning("⚠️ **Abstention Policy Triggered** — Question is unsupported by the ingested course materials.")
            st.markdown(f"### Tutor Response\n{response.answer}")
            st.info(f"**Reason for Abstention:** `{response.unsupported_reason}`")

        else:
            st.error(f"❌ **System Error:** {response.unsupported_reason}")
            st.markdown(f"### Tutor Response\n{response.answer}")

        # Audit Trace Expander
        with st.expander("🛠️ Inspect Grounding & Sufficiency Audit Trace", expanded=False):
            st.markdown("#### 1. Sufficiency Decision Gate")
            st.json({
                "query": suff_eval.query,
                "is_sufficient": suff_eval.is_sufficient,
                "confidence_score": suff_eval.confidence,
                "threshold": 0.35,
                "reason": suff_eval.reason,
                "supporting_evidence_ids": suff_eval.supporting_evidence_ids,
            })

            st.markdown("#### 2. Retrieved Candidates & Scoring Matrix")
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
                st.table(cand_data)
            else:
                st.write("No candidate units retrieved.")

            if response.reasoning_steps:
                st.markdown("#### 3. Generation Reasoning Steps")
                for step in response.reasoning_steps:
                    st.markdown(f"- {step}")
