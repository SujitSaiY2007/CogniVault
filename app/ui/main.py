"""
CogniVault application entry point and route dispatcher.
UI shell and view composition are deliberately separated from domain services.
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="CogniVault | Evidence-first learning",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

_REPO_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from app.ui.theme import THEME_CSS
from app.ui.shell import render_sidebar
from app.ui.state import get_services, init_session_state
from app.ui.views.dashboard_view import render_dashboard_view
from app.ui.views.ingestion_view import render_ingestion_view
from app.ui.views.evidence_view import render_evidence_view
from app.ui.views.courses_view import render_courses_view
from app.ui.views.tutor_view import render_tutor_view
from app.ui.views.assessment_view import render_assessment_view
from app.ui.views.learner_view import render_learner_view
from app.ui.views.recommendations_view import render_recommendations_view
from app.ui.views.evaluation_view import render_evaluation_view

NAV_HOME = "🏠 Home"
NAV_COURSES = "📚 Courses"
NAV_EVIDENCE = "🔎 Evidence Explorer"
NAV_NEW_COURSE = "➕ Add Materials"
NAV_TUTOR = "💬 AI Tutor"
NAV_ASSESSMENT = "📝 Practice"
NAV_PROGRESS = "📈 My Progress"
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
    NAV_EVIDENCE,
    NAV_EVALUATION,
]

ROUTE_ALIASES = {
    "Overview & Dashboard": NAV_HOME,
    "Home": NAV_HOME,
    "1. Course Setup": NAV_NEW_COURSE,
    "Course Setup": NAV_NEW_COURSE,
    "New Course": NAV_NEW_COURSE,
    "Add Materials": NAV_NEW_COURSE,
    "2. Evidence Explorer": NAV_EVIDENCE,
    "Evidence Explorer": NAV_EVIDENCE,
    "Available Courses": NAV_COURSES,
    "3. Grounded AI Tutor": NAV_TUTOR,
    "Grounded AI Tutor": NAV_TUTOR,
    "AI Tutor": NAV_TUTOR,
    "4. Adaptive Assessment": NAV_ASSESSMENT,
    "Adaptive Assessment": NAV_ASSESSMENT,
    "Practice & Assessment": NAV_ASSESSMENT,
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
        if alias_key.casefold() in raw_target.casefold():
            return mapped_nav
    return NAV_HOME


def main() -> None:
    st.markdown(THEME_CSS, unsafe_allow_html=True)
    init_session_state()
    services = get_services()
    db = services["db"]

    # Dashboard shortcuts and cross-page actions use the same route contract.
    if "nav_selection_override" in st.session_state:
        override = st.session_state.pop("nav_selection_override")
        st.session_state["main_nav_radio"] = _resolve_nav_choice(str(override))

    nav_choice = render_sidebar(NAV_OPTIONS, db)

    if nav_choice == NAV_HOME:
        render_dashboard_view(services)
    elif nav_choice == NAV_COURSES:
        render_courses_view(services)
    elif nav_choice == NAV_EVIDENCE:
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
