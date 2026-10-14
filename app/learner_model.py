from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from .db import EvidenceDB
from .models import BKTParams, TopicMasteryRecord

class BKTModel:
    """
    Standard Bayesian Knowledge Tracing (BKT) implementation.
    Computes exact posterior belief given observation, followed by learning transition.
    """
    def __init__(self, params: BKTParams | None = None):
        self.params = params or BKTParams()

    def update_posterior(self, p_prior: float, is_correct: bool) -> float:
        """
        Calculates P(L_t | observation).
        """
        p_prior = max(0.0001, min(0.9999, p_prior))
        p_s = self.params.p_slip
        p_g = self.params.p_guess

        if is_correct:
            numerator = p_prior * (1.0 - p_s)
            denominator = numerator + (1.0 - p_prior) * p_g
        else:
            numerator = p_prior * p_s
            denominator = numerator + (1.0 - p_prior) * (1.0 - p_g)

        if denominator <= 0.0:
            p_post = p_prior
        else:
            p_post = numerator / denominator

        return max(0.0001, min(0.9999, p_post))

    def apply_transition(self, p_posterior: float) -> float:
        """
        Calculates P(L_t) = P(L_t | obs) + (1 - P(L_t | obs)) * P(T).
        """
        p_t = self.params.p_transit
        p_next = p_posterior + (1.0 - p_posterior) * p_t
        return max(0.0001, min(0.9999, round(p_next, 6)))

    def step(self, p_prior: float, is_correct: bool) -> float:
        """
        Full BKT step: observation update + transition.
        """
        p_post = self.update_posterior(p_prior, is_correct)
        return self.apply_transition(p_post)

class LearnerStateManager:
    def __init__(self, db: EvidenceDB, bkt_model: BKTModel | None = None):
        self.db = db
        self.bkt = bkt_model or BKTModel()

    @property
    def params(self):
        return self.bkt.params

    def step(self, p_prior: float, is_correct: bool) -> float:
        return self.bkt.step(p_prior, is_correct)

    def update_posterior(self, p_prior: float, is_correct: bool) -> float:
        return self.bkt.update_posterior(p_prior, is_correct)

    def apply_transition(self, p_posterior: float) -> float:
        return self.bkt.apply_transition(p_posterior)

    def record_observation(
        self,
        learner_id: str,
        topic_id: str,
        is_correct: bool,
        timestamp: str | None = None
    ) -> TopicMasteryRecord:
        """Alias for record_response for API compatibility."""
        return self.record_response(learner_id, topic_id, is_correct, timestamp=timestamp)

    def get_or_create_mastery(self, learner_id: str, topic_id: str) -> TopicMasteryRecord:
        record = self.db.get_learner_mastery(learner_id, topic_id)
        if record is None:
            record = TopicMasteryRecord(
                learner_id=learner_id,
                topic_id=topic_id,
                p_mastery=self.bkt.params.p_init,
                attempts=0,
                correct=0,
                recent_correctness=[],
                last_seen=None,
                misconception_signals=[]
            )
            self.db.save_learner_mastery(record)
        return record

    def record_response(
        self,
        learner_id: str,
        topic_id: str,
        is_correct: bool,
        timestamp: str | None = None
    ) -> TopicMasteryRecord:
        current = self.get_or_create_mastery(learner_id, topic_id)
        new_p = self.bkt.step(current.p_mastery, is_correct)

        recent = list(current.recent_correctness)
        recent.append(is_correct)
        if len(recent) > 10:
            recent = recent[-10:]

        now_str = timestamp or datetime.now(timezone.utc).isoformat()
        updated = TopicMasteryRecord(
            learner_id=learner_id,
            topic_id=topic_id,
            p_mastery=new_p,
            attempts=current.attempts + 1,
            correct=current.correct + (1 if is_correct else 0),
            recent_correctness=recent,
            last_seen=now_str,
            misconception_signals=current.misconception_signals
        )
        self.db.save_learner_mastery(updated)
        return updated

    def get_learner_profile(self, learner_id: str) -> dict[str, Any]:
        records = self.db.get_all_learner_masteries(learner_id)
        interactions = self.db.get_interactions(learner_id)
        misconceptions = self.db.get_active_misconceptions(learner_id)

        mastery_map = {r.topic_id: r.p_mastery for r in records}
        return {
            "learner_id": learner_id,
            "topic_mastery": mastery_map,
            "total_attempts": sum(r.attempts for r in records),
            "total_correct": sum(r.correct for r in records),
            "interaction_count": len(interactions),
            "active_misconceptions": [m.suspected_misconception for m in misconceptions],
            "records": records
        }
