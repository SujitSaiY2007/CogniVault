"""
CogniVault 2.0 Streamlit Application.
Evidence-First Adaptive Learning (Hackathon Track D).
"""
from __future__ import annotations

import streamlit as st

# Set page configuration as first Streamlit command
st.set_page_config(
    page_title="CogniVault 2.0 | Evidence-First Adaptive Learning",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

import sys
from pathlib import Path
_REPO_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from app.ui.theme import THEME_CSS, BORDER_COLOR, TEXT_PRIMARY, TEXT_SECONDARY
from app.ui.state import get_services, init_session_state
from app.ui.views.dashboard_view import render_dashboard_view
from app.ui.views.ingestion_view import render_ingestion_view
from app.ui.views.evidence_view import render_evidence_view
from app.ui.views.tutor_view import render_tutor_view
from app.ui.views.assessment_view import render_assessment_view
from app.ui.views.learner_view import render_learner_view
from app.ui.views.recommendations_view import render_recommendations_view
from app.ui.views.evaluation_view import render_evaluation_view


def main():
    # Inject CogniVault 2.0 Premium Light Design System
    st.markdown(THEME_CSS, unsafe_allow_html=True)
    init_session_state()
    services = get_services()
    db = services["db"]

    nav_options = [
        "🏠 Overview & Dashboard",
        "📥 1. Course Setup & Ingestion",
        "🔍 2. Evidence Explorer",
        "💬 3. Grounded AI Tutor",
        "📝 4. Adaptive Assessment",
        "📊 5. Learner Mastery Profile",
        "🎯 6. Recommendations & Prerequisites",
        "🧪 7. Benchmark & Evaluation",
    ]

    # Handle quick navigation override from dashboard shortcuts
    if "nav_selection_override" in st.session_state:
        override = st.session_state.pop("nav_selection_override")
        if override in nav_options:
            st.session_state["main_nav_radio"] = override

    # Sidebar Navigation & System Telemetry
    with st.sidebar:
        st.markdown(
            f"""
            <div style="padding-bottom: 0.75rem; border-bottom: 1px solid {BORDER_COLOR}; margin-bottom: 1rem;">
                <div style="display: flex; align-items: center; gap: 0.5rem;">
                    <span style="font-size: 1.6rem;">🧠</span>
                    <span style="font-size: 1.3rem; font-weight: 700; color: {TEXT_PRIMARY};">CogniVault 2.0</span>
                </div>
                <p style="margin: 0.25rem 0 0 0; font-size: 0.82rem; color: {TEXT_SECONDARY};">
                    Evidence-First Adaptive Learning
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )

        nav_choice = st.radio(
            "Navigation Modules",
            nav_options,
            key="main_nav_radio",
            label_visibility="collapsed"
        )

        st.divider()
        st.markdown(f"<div style='font-size: 0.82rem; font-weight: 600; color: {TEXT_SECONDARY}; text-transform: uppercase; margin-bottom: 0.5rem;'>📡 System Telemetry</div>", unsafe_allow_html=True)
        all_ev = list(db.all_evidence())
        all_sources = list(db.all_sources())
        all_q = db.all_questions(verified_only=True)

        st.markdown(f"- **Indexed Sources:** `{len(all_sources)}`")
        st.markdown(f"- **Evidence Units:** `{len(all_ev)}`")
        st.markdown(f"- **Verified Questions:** `{len(all_q)}`")
        st.markdown(f"- **Active Learner:** `{st.session_state.active_learner_id}`")
        st.markdown(f"- **Modalities:** `PDF | PPTX | Transcript`")

        st.divider()
        st.caption("CogniVault 2.0 • Track D Adaptive Learning")

    # Route Views
    if "Overview & Dashboard" in nav_choice:
        render_dashboard_view(services)
    elif "1. Course Setup" in nav_choice:
        render_ingestion_view(services)
    elif "2. Evidence Explorer" in nav_choice:
        render_evidence_view(services)
    elif "3. Grounded AI Tutor" in nav_choice:
        render_tutor_view(services)
    elif "4. Adaptive Assessment" in nav_choice:
        render_assessment_view(services)
    elif "5. Learner Mastery" in nav_choice:
        render_learner_view(services)
    elif "6. Recommendations" in nav_choice:
        render_recommendations_view(services)
    elif "7. Benchmark" in nav_choice:
        render_evaluation_view(services)


if __name__ == "__main__":
    main()
