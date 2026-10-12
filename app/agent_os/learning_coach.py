"""
CogniVault Learning Coach Agent for Agno AgentOS.
Manages Bayesian Knowledge Tracing (BKT) state transitions, persistent misconception diagnosis,
and prerequisite-aware adaptive recommendations.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

try:
    from agno.agent import Agent
except ImportError:
    Agent = None

from ..db import EvidenceDB
from ..learner_model import BKTModel, LearnerStateManager
from ..misconceptions import MisconceptionDetector
from ..models import MisconceptionSignal, Recommendation, TopicMasteryRecord
from ..ollama_provider import create_ollama_model, is_ollama_available
from ..recommendation import AdaptiveRecommendationEngine
from .tools import LearningCoachTools


COACH_SYSTEM_PROMPT = """
You are the CogniVault Learning Coach, an adaptive educational navigator.

Core Principles:
1. Deterministic Mastery: Mastery numbers P(L_t) are computed strictly via Bayesian Knowledge Tracing (BKT). Never invent mastery probabilities.
2. Verified Updates: Updates occur exclusively from verified assessment outcomes or grounded tutoring observations.
3. Prerequisite Gatekeeping: Prerequisite concepts must achieve mastery >= 0.70 before advancing to dependent topics.
4. Persistent Misconceptions: Two or more consecutive incorrect signals trigger targeted foundational remediation.
"""


class LearningCoachAgent:
    """Bounded Agno Agent for learner modeling, BKT tracking, and recommendations."""

    def __init__(
        self,
        db: EvidenceDB,
        state_manager: Optional[LearnerStateManager] = None,
        misconception_detector: Optional[MisconceptionDetector] = None,
        recommendation_engine: Optional[AdaptiveRecommendationEngine] = None,
        model_id: Optional[str] = None,
        host: Optional[str] = None,
    ):
        self.db = db
        self.state_manager = state_manager or LearnerStateManager(db)
        self.detector = misconception_detector or MisconceptionDetector(db)
        self.recommender = recommendation_engine or AdaptiveRecommendationEngine(db)
        self.tools_handler = LearningCoachTools(
            db,
            state_manager=self.state_manager,
            misconception_detector=self.detector,
            recommendation_engine=self.recommender,
        )

        self.model_id = model_id or os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
        self.host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")

        self.agno_agent: Optional[Agent] = None
        if Agent is not None:
            model = None
            if is_ollama_available(self.host):
                model = create_ollama_model(self.model_id, self.host)

            self.agno_agent = Agent(
                name="CogniVault Learning Coach",
                description="Adaptive educational coach enforcing BKT mastery tracking and prerequisite gating",
                instructions=COACH_SYSTEM_PROMPT,
                tools=self.tools_handler.get_tool_list(),
                model=model,
                markdown=True,
            )

    def get_topic_mastery(self, learner_id: str, topic_id: str) -> TopicMasteryRecord:
        """Retrieves or initializes latent topic mastery P(L_t) for learner."""
        return self.state_manager.get_or_create_mastery(learner_id, topic_id)

    def record_observation(
        self,
        learner_id: str,
        topic_id: str,
        is_correct: bool,
        timestamp: Optional[str] = None,
    ) -> TopicMasteryRecord:
        """Applies deterministic BKT update: posterior + transition, persisting to SQLite."""
        return self.state_manager.record_observation(
            learner_id=learner_id,
            topic_id=topic_id,
            is_correct=is_correct,
            timestamp=timestamp,
        )

    def analyze_attempt(
        self,
        learner_id: str,
        topic_id: str,
        concept_id: Optional[str],
        is_correct: bool,
        error_pattern: str = "wrong_answer",
    ) -> Optional[MisconceptionSignal]:
        """Analyzes attempt for persistent misconception signals (threshold >= 2)."""
        return self.detector.analyze_attempt(
            learner_id=learner_id,
            topic_id=topic_id,
            concept_id=concept_id,
            is_correct=is_correct,
            error_pattern=error_pattern,
        )

    def resolve_misconception(self, learner_id: str, topic_id: str, concept_id: Optional[str] = None) -> None:
        """Clears active misconception signals and resets error counters."""
        self.detector.resolve_misconception(learner_id, topic_id, concept_id)

    def get_recommendation(self, learner_id: str, active_topic_id: Optional[str] = None) -> Recommendation:
        """Computes next learning recommendation with prerequisite gating and policy brackets."""
        return self.recommender.recommend(learner_id, active_topic_id=active_topic_id)

    def cold_start_intake(
        self,
        learner_id: str,
        initial_topic_masteries: Optional[dict[str, float]] = None,
        diagnostic_responses: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """
        Initializes a fresh learner profile via cold-start diagnostic intake.
        Takes optional baseline masteries or evaluates diagnostic responses.
        """
        now_str = datetime.now(timezone.utc).isoformat()
        records: list[TopicMasteryRecord] = []

        # If baseline masteries provided
        if initial_topic_masteries:
            for t_id, p_val in initial_topic_masteries.items():
                p_clamped = max(0.0001, min(0.9999, float(p_val)))
                rec = TopicMasteryRecord(
                    learner_id=learner_id,
                    topic_id=t_id,
                    p_mastery=p_clamped,
                    attempts=1,
                    correct=1 if p_clamped >= 0.50 else 0,
                    recent_correctness=[p_clamped >= 0.50],
                    last_seen=now_str,
                    misconception_signals=[],
                )
                self.db.save_learner_mastery(rec)
                records.append(rec)

        # If diagnostic question responses provided
        if diagnostic_responses:
            for resp in diagnostic_responses:
                t_id = resp.get("topic_id", "general")
                is_corr = bool(resp.get("is_correct", False))
                rec = self.record_observation(learner_id, t_id, is_corr, timestamp=now_str)
                records.append(rec)

        # If neither provided, initialize all known topics with default p_init (0.10)
        if not records:
            all_topics = self.db.all_topics()
            for t in all_topics:
                rec = self.state_manager.get_or_create_mastery(learner_id, t.topic_id)
                records.append(rec)

        profile = self.state_manager.get_learner_profile(learner_id)
        next_rec = self.get_recommendation(learner_id)
        return {
            "learner_id": learner_id,
            "intake_status": "completed",
            "timestamp": now_str,
            "profile": profile,
            "initial_recommendation": next_rec.model_dump(),
        }
