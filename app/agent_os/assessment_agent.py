"""
CogniVault Assessment Agent for Agno AgentOS.
Manages deterministic question verification, adaptive question selection, and answer evaluation.
"""
from __future__ import annotations

import json
import os
from typing import Any, Optional

try:
    from agno.agent import Agent
except ImportError:
    Agent = None

from ..assessment import AssessmentEngine, DeterministicQuestionVerifier, compute_question_fingerprint
from ..models import AnswerEvaluation, Difficulty, LearnerSubmission, Question, QuestionOption, QuestionType, QuestionVerificationResult
from ..model_provider import create_active_model, create_ollama_model, is_ollama_available
from .tools import AssessmentTools


ASSESSMENT_SYSTEM_PROMPT = """
You are the CogniVault Assessment Agent, a pedagogical evaluation specialist.

Core Principles:
1. Grounded Questions: Every question must be directly supported by indexed course materials with physical locators.
2. Verified Answer Keys: Every question must pass deterministic structural and answer-key validation.
3. No Duplicates: Prevent question repetition by tracking question fingerprints.
4. Objective Scoring: Score student submissions strictly against verified keys, tolerances, or rubrics.
"""


class AssessmentAgent:
    """Bounded Agno Agent for educational assessment generation and verification."""

    def __init__(
        self,
        db,
        assessment_engine: Optional[AssessmentEngine] = None,
        verifier: Optional[DeterministicQuestionVerifier] = None,
        model_id: Optional[str] = None,
        host: Optional[str] = None,
    ):
        self.db = db
        self.verifier = verifier or DeterministicQuestionVerifier()
        self.engine = assessment_engine or AssessmentEngine(db, verifier=self.verifier)
        self.tools_handler = AssessmentTools(db, assessment_engine=self.engine, verifier=self.verifier)

        self.model_id = model_id or os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
        self.host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")

        self.agno_agent: Optional[Agent] = None
        if Agent is not None:
            model = create_active_model(self.model_id)

            self.agno_agent = Agent(
                name="CogniVault Assessment Agent",
                description="Pedagogical evaluation specialist ensuring verified answer keys and repetition control",
                instructions=ASSESSMENT_SYSTEM_PROMPT,
                tools=self.tools_handler.get_tool_list(),
                model=model,
                markdown=True,
            )

    def select_adaptive_question(
        self,
        topic_id: str,
        served_question_ids: Optional[list[str] | set[str]] = None,
        target_difficulty: Optional[Difficulty] = None,
        verified_only: bool = True,
    ) -> Optional[Question]:
        """Adaptively selects candidate question adhering to repetition suppression."""
        return self.engine.select_adaptive_question(
            topic_id=topic_id,
            served_question_ids=served_question_ids,
            target_difficulty=target_difficulty,
            verified_only=verified_only,
        )

    def verify_question(self, question: Question) -> QuestionVerificationResult:
        """Runs deterministic structural and answer-key verification."""
        return self.verifier.verify(question, db=self.db)

    def evaluate_submission(
        self,
        submission: LearnerSubmission,
        question: Question,
    ) -> AnswerEvaluation:
        """Scores submission and produces evidence-grounded feedback with source locators."""
        return self.engine.evaluate_submission(submission, question)

    def generate_and_verify_question(
        self,
        question_id: str,
        topic_id: str,
        prompt: str,
        expected_answer: str,
        evidence_ids: list[str],
        concept_id: Optional[str] = None,
        difficulty: Difficulty = Difficulty.medium,
        question_type: QuestionType = QuestionType.mcq,
        options: Optional[list[QuestionOption]] = None,
        tolerance: Optional[float] = None,
        solution: str = "",
        metadata: Optional[dict] = None,
    ) -> Question:
        """Creates and verifies a question, saving to database only if valid or rejected with reason."""
        return self.engine.build_and_verify_question(
            question_id=question_id,
            topic_id=topic_id,
            prompt=prompt,
            expected_answer=expected_answer,
            evidence_ids=evidence_ids,
            concept_id=concept_id,
            difficulty=difficulty,
            question_type=question_type,
            options=options,
            tolerance=tolerance,
            solution=solution,
            metadata=metadata,
        )
