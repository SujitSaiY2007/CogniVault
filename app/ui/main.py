"""
CogniVault Streamlit Demo Application.
Evidence-First Adaptive Learning (Hackathon Track D).
"""
from __future__ import annotations

import streamlit as st

# Set page configuration as first Streamlit command
st.set_page_config(
    page_title="CogniVault | Evidence-First Adaptive Learning",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

import sys
from pathlib import Path
_REPO_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from app.ui.state import get_services, init_session_state
from app.ui.views.ingestion_view import render_ingestion_view
from app.ui.views.evidence_view import render_evidence_view
from app.ui.views.tutor_view import render_tutor_view
from app.ui.views.assessment_view import render_assessment_view
from app.ui.views.learner_view import render_learner_view
from app.ui.views.recommendations_view import render_recommendations_view
from app.ui.views.evaluation_view import render_evaluation_view

# Custom Styling for WOW Aesthetics & Modern Design System
CUSTOM_CSS = """
<style>
    /* Main Theme Overrides */
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
    }

    /* Headers */
    h1, h2, h3, h4 {
        color: #58a6ff !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        font-weight: 600;
    }

    /* Card Containers */
    [data-testid="stVerticalBlock"] > div[data-testid="stContainer"] {
        border-radius: 8px;
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 1.25rem;
        margin-bottom: 1rem;
    }

    /* Metric Cards */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #7ee787 !important;
    }

    /* Buttons */
    .stButton > button[kind="primary"] {
        background-color: #238636 !important;
        border-color: #2ea043 !important;
        color: #ffffff !important;
        font-weight: 600;
        border-radius: 6px;
        transition: all 0.2s ease-in-out;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #2ea043 !important;
        transform: translateY(-1px);
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }

    /* Badge Tags */
    .badge-grounded {
        background-color: #238636;
        color: #ffffff;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .badge-abstain {
        background-color: #da3633;
        color: #ffffff;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
    }
</style>
"""


def main():
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    init_session_state()
    services = get_services()
    db = services["db"]

    # Sidebar Navigation & System Telemetry
    with st.sidebar:
        st.markdown("## 🧠 **CogniVault**")
        st.caption("Evidence-First Adaptive Learning (Track D)")
        st.divider()

        nav_choice = st.radio(
            "Navigate Modules",
            [
                "📥 1. Course Setup & Ingestion",
                "🔍 2. Evidence Explorer",
                "💬 3. Grounded AI Tutor",
                "📝 4. Adaptive Assessment",
                "📊 5. Learner Mastery Profile",
                "🎯 6. Recommendations & Prerequisites",
                "🧪 7. Benchmark & Evaluation",
            ],
            index=0
        )

        st.divider()
        st.markdown("### 📡 System Telemetry")
        all_ev = list(db.all_evidence())
        all_sources = list(db.all_sources())
        all_q = db.all_questions(verified_only=True)

        st.markdown(f"- **Indexed Sources:** `{len(all_sources)}`")
        st.markdown(f"- **Evidence Units:** `{len(all_ev)}`")
        st.markdown(f"- **Verified Questions:** `{len(all_q)}`")
        st.markdown(f"- **Active Learner:** `{st.session_state.active_learner_id}`")
        st.markdown(f"- **Database:** `data/cognivault.sqlite`")

        st.divider()
        st.caption("CogniVault v0.3.0 | Track D Hackathon Demo")

    # Route Views
    if "1. Course Setup" in nav_choice:
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
