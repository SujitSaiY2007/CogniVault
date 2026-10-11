"""Shared application shell for CogniVault's learner-first UI."""
from __future__ import annotations

import streamlit as st
from app.ui.components import _render_html_fragment


def render_sidebar(
    nav_options: list[str],
    db,
    *,
    nav_key: str = "main_nav_radio",
) -> str:
    """Render consistent navigation using native Streamlit widgets only."""
    with st.sidebar:
        _render_html_fragment(
            """
            <div class="cv-brand">
              <div class="cv-brand-mark">C</div>
              <div>
                <div class="cv-brand-name">CogniVault</div>
                <div class="cv-brand-caption">Your learning workspace</div>
              </div>
            </div>
            """
        )
        st.caption("WORKSPACE")
        choice = st.radio(
            "Main navigation",
            options=nav_options,
            key=nav_key,
            label_visibility="collapsed",
        )
        st.divider()
        st.caption("Study with confidence")
        st.markdown(
            "Answers are grounded in your indexed materials. When the evidence is insufficient, "
            "CogniVault should say so rather than invent an answer."
        )
        with st.expander("Advanced system details"):
            try:
                sources = len(list(db.all_sources()))
                evidence = len(list(db.all_evidence()))
                questions = len(db.all_questions(verified_only=True))
                st.caption(f"Sources indexed: {sources}")
                st.caption(f"Searchable evidence units: {evidence}")
                st.caption(f"Verified practice items: {questions}")
            except Exception:
                st.caption("System details are temporarily unavailable.")
        st.caption("Local demo · No cloud sync or account system is implied.")
    return choice


def render_page_intro(eyebrow: str, title: str, description: str) -> None:
    """Shared page introduction rendered with native Streamlit text elements."""
    st.caption(eyebrow.upper())
    st.title(title)
    st.markdown(description)
