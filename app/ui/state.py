"""
CogniVault UI State & Service Container.
Provides thread-safe, cached service instances for the Streamlit interface.
"""
from __future__ import annotations

import os
from pathlib import Path
import streamlit as st

from app.db import EvidenceDB
from app.retrieval import HybridRetriever
from app.sufficiency import EvidenceSufficiencyGate
from app.tutor import GroundedTutor, DeterministicTutorProvider
from app.assessment import AssessmentEngine, DeterministicQuestionVerifier
from app.learner_model import BKTModel, LearnerStateManager
from app.misconceptions import MisconceptionDetector
from app.recommendation import AdaptiveRecommendationEngine
from app.corpus import seed_database_from_corpus

DEFAULT_DB_PATH = "data/cognivault.sqlite"


@st.cache_resource
def get_db(db_path: str = DEFAULT_DB_PATH) -> EvidenceDB:
    """Initialize or connect to the persistent EvidenceDB instance."""
    os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
    db = EvidenceDB(db_path)
    # Check if empty; if so, automatically seed default Mathematics/Science corpus
    all_ev = list(db.all_evidence())
    if not all_ev:
        seed_database_from_corpus(db)
    return db


def get_services(db_path: str = DEFAULT_DB_PATH):
    """Return all core services bound to the database."""
    db = get_db(db_path)
    retriever = HybridRetriever(db)
    sufficiency_gate = EvidenceSufficiencyGate()
    tutor_provider = DeterministicTutorProvider()
    tutor = GroundedTutor(db, retriever=retriever, sufficiency_gate=sufficiency_gate, provider=tutor_provider)
    verifier = DeterministicQuestionVerifier()
    assessment_engine = AssessmentEngine(db, verifier=verifier)
    bkt = LearnerStateManager(db, bkt_model=BKTModel())
    misconceptions = MisconceptionDetector(db)
    recommendation_engine = AdaptiveRecommendationEngine(db)

    return {
        "db": db,
        "retriever": retriever,
        "sufficiency_gate": sufficiency_gate,
        "tutor": tutor,
        "verifier": verifier,
        "assessment_engine": assessment_engine,
        "bkt": bkt,
        "learner_state_manager": bkt,
        "misconceptions": misconceptions,
        "recommendations": recommendation_engine,
    }


def init_session_state():
    """Initialize standard session variables."""
    if "active_learner_id" not in st.session_state:
        st.session_state.active_learner_id = "learner_demo"
    if "active_topic_id" not in st.session_state:
        st.session_state.active_topic_id = "Newtonian Mechanics"
    if "served_question_ids" not in st.session_state:
        st.session_state.served_question_ids = []
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "current_question" not in st.session_state:
        st.session_state.current_question = None
    if "last_evaluation" not in st.session_state:
        st.session_state.last_evaluation = None
