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

from app.ui.components import _render_html_fragment
from app.ui.theme import THEME_CSS, BORDER_COLOR, TEXT_PRIMARY, TEXT_SECONDARY
from app.ui.state import get_services, init_session_state
from app.ui.views.dashboard_view import render_dashboard_view
from app.ui.views.ingestion_view import render_ingestion_view
from app.ui.views.evidence_view import render_evidence_view
from app.ui.views.tutor_view import render_tutor_view
from app.ui.views.assessment_view import render_assessment_view
import textwrap
from app.ui.views.learner_view import render_learner_view
from app.ui.views.recommendations_view import render_recommendations_view
from app.ui.views.evaluation_view import render_evaluation_view

# Unnumbered Navigation Hierarchy (CogniVault 2.0)
NAV_HOME = "🏠 Home"
NAV_COURSES = "📚 Available Courses"
NAV_NEW_COURSE = "➕ New Course"
NAV_TUTOR = "💬 AI Tutor"
NAV_ASSESSMENT = "📝 Practice & Assessment"
NAV_PROGRESS = "📊 My Progress"
NAV_RECOMMENDATIONS = "🎯 Recommendations"
NAV_EVALUATION = "🧪 Evaluation"

NAV_OPTIONS = [
    NAV_HOME,
    NAV_COURSES,
    NAV_NEW_COURSE,
    NAV_TUTOR,
    NAV_ASSESSMENT,
    NAV_PROGRESS,
    NAV_RECOMMENDATIONS,
    NAV_EVALUATION,
]

ROUTE_ALIASES = {
    "Overview & Dashboard": NAV_HOME,
    "Home": NAV_HOME,
    "1. Course Setup": NAV_NEW_COURSE,
    "Course Setup": NAV_NEW_COURSE,
    "New Course": NAV_NEW_COURSE,
    "2. Evidence Explorer": NAV_COURSES,
    "Evidence Explorer": NAV_COURSES,
    "Available Courses": NAV_COURSES,
    "3. Grounded AI Tutor": NAV_TUTOR,
    "Grounded AI Tutor": NAV_TUTOR,
    "AI Tutor": NAV_TUTOR,
    "4. Adaptive Assessment": NAV_ASSESSMENT,
    "Adaptive Assessment": NAV_ASSESSMENT,
    "Practice": NAV_ASSESSMENT,
    "5. Learner Mastery": NAV_PROGRESS,
    "Learner Mastery Profile": NAV_PROGRESS,
    "My Progress": NAV_PROGRESS,
    "6. Recommendations": NAV_RECOMMENDATIONS,
    "Recommendations & Prerequisites": NAV_RECOMMENDATIONS,
    "Recommendations": NAV_RECOMMENDATIONS,
    "7. Benchmark": NAV_EVALUATION,
    "Benchmark & Evaluation": NAV_EVALUATION,
    "Evaluation": NAV_EVALUATION,
}


def _resolve_nav_choice(raw_target: str) -> str:
    if raw_target in NAV_OPTIONS:
        return raw_target
    for alias_key, mapped_nav in ROUTE_ALIASES.items():
        if alias_key.lower() in raw_target.lower():
            return mapped_nav
    return NAV_HOME


def main():
    # Inject CogniVault 2.0 Premium Light Design System
    st.markdown(THEME_CSS, unsafe_allow_html=True)
    init_session_state()
    services = get_services()
    db = services["db"]

    # Handle quick navigation override from dashboard shortcuts
    if "nav_selection_override" in st.session_state:
        override = st.session_state.pop("nav_selection_override")
        resolved = _resolve_nav_choice(override)
        st.session_state["main_nav_radio"] = resolved

    # Sidebar Navigation — Minimal & Uncluttered
    with st.sidebar:
        _render_html_fragment(textwrap.dedent(f"""
                <div style="padding-bottom: 0.75rem; border-bottom: 1px solid {BORDER_COLOR}; margin-bottom: 1rem;">
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <span style="font-size: 1.6rem;">🧠</span>
                        <span style="font-size: 1.3rem; font-weight: 700; color: {TEXT_PRIMARY};">CogniVault</span>
                    </div>
                    <p style="margin: 0.25rem 0 0 0; font-size: 0.82rem; color: {TEXT_SECONDARY};">
                        Evidence-First Adaptive Learning
                    </p>
                </div>
            """).strip())

        nav_choice = st.radio(
            "Navigation Modules",
            NAV_OPTIONS,
            key="main_nav_radio",
            label_visibility="collapsed"
        )

        _render_html_fragment("<div style='margin-top: 1.5rem;'></div>")

        # Minimal collapsible telemetry in sidebar footer
        with st.expander("ℹ️ System Status", expanded=False):
            all_ev = list(db.all_evidence())
            all_sources = list(db.all_sources())
            all_q = db.all_questions(verified_only=True)

            st.caption(f"**Sources:** `{len(all_sources)}` | **Evidence Units:** `{len(all_ev)}`")
            st.caption(f"**Verified Items:** `{len(all_q)}`")
            st.caption(f"**Active Learner:** `{st.session_state.active_learner_id}`")
            st.caption(f"**Corpus Modalities:** `PDF | PPTX | Transcript`")

        st.caption("CogniVault 2.0 • Track D Adaptive Learning")

    # Route Views
    if nav_choice == NAV_HOME:
        render_dashboard_view(services)
    elif nav_choice == NAV_COURSES:
        render_evidence_view(services)
    elif nav_choice == NAV_NEW_COURSE:
        render_ingestion_view(services)
    elif nav_choice == NAV_TUTOR:
        render_tutor_view(services)
    elif nav_choice == NAV_ASSESSMENT:
        render_assessment_view(services)
    elif nav_choice == NAV_PROGRESS:
        render_learner_view(services)
    elif nav_choice == NAV_RECOMMENDATIONS:
        render_recommendations_view(services)
    elif nav_choice == NAV_EVALUATION:
        render_evaluation_view(services)


if __name__ == "__main__":
    main()

