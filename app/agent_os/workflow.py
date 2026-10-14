"""
CogniVault Learning Loop Workflow for Agno AgentOS.
Coordinates three bounded roles:
  1. Evidence Tutor: Grounded answering with exact source citations or fail-closed abstention.
  2. Assessment: Verified question generation/selection, answer-key integrity, and objective scoring.
  3. Learning Coach: Deterministic BKT mastery updates, persistent misconception diagnosis, and prerequisite gating.
"""
from __future__ import annotations

from typing import Any, Optional

from ..db import EvidenceDB
from ..models import AnswerEvaluation, Difficulty, LearnerSubmission, Question, Recommendation, TopicMasteryRecord, TutorResponse
from .assessment_agent import AssessmentAgent
from .learning_coach import LearningCoachAgent
from .tutor_agent import EvidenceTutorAgent


class CogniVaultLearningWorkflow:
    """Controlled multi-agent workflow uniting Evidence Tutor, Assessment, and Learning Coach."""

    def __init__(
        self,
        tutor_agent: EvidenceTutorAgent,
        assessment_agent: AssessmentAgent,
        coach_agent: LearningCoachAgent,
        db: EvidenceDB,
    ):
        self.tutor = tutor_agent
        self.assessment = assessment_agent
        self.coach = coach_agent
        self.db = db

    def ask_grounded_tutor(self, query: str, topic: Optional[str] = None) -> TutorResponse:
        """Role 1: Queries the Evidence Tutor Agent with deterministic abstention."""
        return self.tutor.ask(query, topic=topic)

    def select_practice_question(
        self,
        topic_id: str,
        served_question_ids: Optional[list[str]] = None,
        target_difficulty: Optional[Difficulty] = None,
    ) -> Optional[Question]:
        """Role 2: Selects next verified practice question avoiding repeats."""
        return self.assessment.select_adaptive_question(
            topic_id=topic_id,
            served_question_ids=served_question_ids,
            target_difficulty=target_difficulty,
            verified_only=True,
        )

    def process_assessment_submission(
        self,
        learner_id: str,
        question_id: str,
        answer: str,
        timestamp: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Executes complete feedback loop:
          1. Role 2: Evaluates submission against verified key & resolves source locators.
          2. Role 3: Computes exact BKT step P(L_t) and updates database.
          3. Role 3: Checks for misconception accumulation (>= 2 errors).
          4. Role 3: Formulates prerequisite-aware next-step recommendation.
        """
        question = self.db.get_question(question_id)
        if not question:
            raise ValueError(f"Question '{question_id}' not found.")

        submission = LearnerSubmission(
            learner_id=learner_id,
            question_id=question_id,
            topic_id=question.topic_id,
            answer=answer,
            timestamp=timestamp,
        )

        # 1. Evaluate answer and get citation-backed feedback
        evaluation: AnswerEvaluation = self.assessment.evaluate_submission(submission, question)

        # 2. Update BKT latent mastery
        updated_mastery: TopicMasteryRecord = self.coach.record_observation(
            learner_id=learner_id,
            topic_id=question.topic_id,
            is_correct=evaluation.is_correct,
            timestamp=timestamp,
        )

        # 3. Analyze misconception
        misconception_signal = None
        if not evaluation.is_correct:
            misconception_signal = self.coach.analyze_attempt(
                learner_id=learner_id,
                topic_id=question.topic_id,
                concept_id=question.concept_id,
                is_correct=False,
                error_pattern="incorrect_assessment_answer",
            )
        else:
            # Clear or decrease error signals on correct answer
            self.coach.resolve_misconception(
                learner_id=learner_id,
                topic_id=question.topic_id,
                concept_id=question.concept_id,
            )

        # 4. Generate next recommendation
        recommendation: Recommendation = self.coach.get_recommendation(
            learner_id=learner_id,
            active_topic_id=question.topic_id,
        )

        return {
            "evaluation": evaluation.model_dump(),
            "mastery": updated_mastery.model_dump(),
            "misconception_detected": misconception_signal is not None,
            "misconception": misconception_signal.model_dump() if misconception_signal else None,
            "next_recommendation": recommendation.model_dump(),
        }

    def complete_intake(
        self,
        learner_id: str,
        initial_masteries: Optional[dict[str, float]] = None,
        responses: Optional[list[dict[str, Any]]] = None,
    ) -> dict[str, Any]:
        """Role 3: Cold-start diagnostic intake initializing baseline mastery."""
        return self.coach.cold_start_intake(
            learner_id=learner_id,
            initial_topic_masteries=initial_masteries,
            diagnostic_responses=responses,
        )
