from __future__ import annotations
from typing import Any
from .db import EvidenceDB
from .models import Difficulty, Recommendation, TopicMasteryRecord

class AdaptiveRecommendationEngine:
    """
    Translates learner mastery state, prerequisite topology, and misconception signals
    into targeted, explainable next learning actions.
    """
    def __init__(self, db: EvidenceDB):
        self.db = db

    def recommend(
        self,
        learner_id: str,
        active_topic_id: str | None = None
    ) -> Recommendation:
        # Check active misconceptions first
        active_misc = self.db.get_active_misconceptions(learner_id, topic_id=active_topic_id)
        if active_misc:
            top_misc = active_misc[0]
            rationale = (
                f"Active misconception detected: '{top_misc.suspected_misconception}'. "
                f"Learner requires foundational remediation on prerequisite concept '{top_misc.remediation_concept_id}'."
            )
            return Recommendation(
                learner_id=learner_id,
                recommended_action="remediate_misconception",
                topic_id=top_misc.topic_id,
                concept_id=top_misc.remediation_concept_id,
                difficulty=Difficulty.easy,
                rationale=rationale,
                learner_state_evidence={
                    "misconception": top_misc.suspected_misconception,
                    "error_count": top_misc.error_count,
                    "confidence": top_misc.confidence,
                    "remediation_concept": top_misc.remediation_concept_id
                },
                suggested_evidence_ids=top_misc.remediation_evidence_ids
            )

        # Get all masteries or specific topic mastery
        masteries = self.db.get_all_learner_masteries(learner_id)
        mastery_map = {m.topic_id: m for m in masteries}

        target_topic = active_topic_id
        if not target_topic:
            if masteries:
                # Pick topic with lowest mastery among active attempts
                target_topic = min(masteries, key=lambda m: m.p_mastery).topic_id
            else:
                all_t = self.db.all_topics()
                target_topic = all_t[0].topic_id if all_t else "general"

        current_record = mastery_map.get(target_topic)
        p_mastery = current_record.p_mastery if current_record else 0.10
        attempts = current_record.attempts if current_record else 0

        # Check prerequisites for target topic
        prereqs = self.db.get_all_prerequisites(target_topic)
        for prereq in prereqs:
            prereq_mastery = mastery_map.get(prereq)
            if prereq_mastery and prereq_mastery.p_mastery < 0.70:
                # Prerequisite not met
                ev = self.db.get_evidence_for_concept(prereq) or self.db.get_evidence_for_topic(prereq)
                eids = [e.evidence_id for e in ev[:2]]
                return Recommendation(
                    learner_id=learner_id,
                    recommended_action="foundational_review",
                    topic_id=prereq,
                    concept_id=prereq,
                    difficulty=Difficulty.easy,
                    rationale=f"Prerequisite '{prereq}' for topic '{target_topic}' requires reinforcement (mastery: {prereq_mastery.p_mastery:.2f} < 0.70).",
                    learner_state_evidence={
                        "target_topic": target_topic,
                        "prerequisite_topic": prereq,
                        "prerequisite_mastery": prereq_mastery.p_mastery
                    },
                    suggested_evidence_ids=eids
                )

        # Retrieve evidence for suggested next practice
        ev_items = self.db.get_evidence_for_topic(target_topic)
        if not ev_items:
            ev_items = list(self.db.all_evidence())
        suggested_eids = [e.evidence_id for e in ev_items[:3]]

        # Mastery Policy Brackets (CHAT0_TECHNICAL_LOCK §17)
        if p_mastery < 0.40:
            action = "foundational_review"
            diff = Difficulty.easy
            rationale = f"Current topic mastery is low ({p_mastery:.2f} < 0.40). Recommend foundational concept review and easy practice."
        elif p_mastery < 0.70:
            action = "targeted_practice"
            diff = Difficulty.medium
            rationale = f"Current topic mastery is developing ({p_mastery:.2f} in [0.40, 0.70)). Recommend targeted medium-difficulty practice."
        elif p_mastery < 0.85:
            action = "mixed_application"
            diff = Difficulty.medium
            rationale = f"Current topic mastery is strong ({p_mastery:.2f} in [0.70, 0.85)). Recommend mixed application practice."
        else:
            action = "advance_topic"
            diff = Difficulty.hard
            # Check for dependent topics to advance into
            all_topics = [t.topic_id for t in self.db.all_topics()]
            next_topic = target_topic
            for t_id in all_topics:
                if t_id != target_topic and target_topic in self.db.get_all_prerequisites(t_id):
                    next_topic = t_id
                    break
            if next_topic != target_topic:
                target_topic = next_topic
                rationale = f"Mastery in previous topic exceeded 0.85 ({p_mastery:.2f}). Ready to advance to dependent topic '{target_topic}'."
            else:
                rationale = f"High topic mastery achieved ({p_mastery:.2f} >= 0.85). Recommend advanced challenges."

        return Recommendation(
            learner_id=learner_id,
            recommended_action=action,
            topic_id=target_topic,
            difficulty=diff,
            rationale=rationale,
            learner_state_evidence={
                "topic_id": target_topic,
                "p_mastery": p_mastery,
                "attempts": attempts,
                "policy_bracket": action
            },
            suggested_evidence_ids=suggested_eids
        )
