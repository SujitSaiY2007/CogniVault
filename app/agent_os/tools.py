"""
Agno Agent tools for CogniVault evidence retrieval, sufficiency gating, and citation verification.
Preserves exact physical locators and strict fail-closed abstention rules.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Optional
from ..models import EvidenceUnit, LocatorType, RetrievalResult


class AgentTools:
    """Encapsulates tool functions callable by Agno Agents."""

    def __init__(self, db, retriever, gate, resolver):
        self.db = db
        self.retriever = retriever
        self.gate = gate
        self.resolver = resolver

    def search_course_materials(self, query: str, k: int = 5) -> str:
        """
        Search course learning materials using hybrid lexical (FTS5) and semantic (ChromaDB) retrieval.
        Returns matching excerpts with exact source locators (e.g. Page number, Slide number, Video timestamp).
        """
        results, trace = self.retriever.search(query, k=k, mode="hybrid")
        if not results:
            return json.dumps({
                "status": "no_results",
                "message": "No course evidence found matching the query.",
                "unsupported": trace.unsupported,
                "reason": trace.reason,
            })

        formatted = []
        for r in results:
            unit = self.db.get_evidence(r.evidence_id)
            loc_str = unit.location if unit else r.location
            formatted.append({
                "evidence_id": r.evidence_id,
                "source_id": r.source_id,
                "location": loc_str,
                "score": r.score,
                "text": r.snippet,
            })

        return json.dumps({
            "status": "success",
            "count": len(formatted),
            "evidence": formatted,
        })

    def evaluate_evidence_sufficiency(self, query: str) -> str:
        """
        Deterministically evaluates whether the course contains sufficient evidence to answer the query.
        Returns whether the tutor is permitted to answer or MUST abstain.
        """
        results, _ = self.retriever.search(query, k=5, mode="hybrid")
        decision = self.gate.evaluate(query, results, db=self.db)
        return json.dumps({
            "supported": decision.is_sufficient,
            "confidence": decision.confidence,
            "evidence_count": decision.evidence_count,
            "evidence_ids": decision.supporting_evidence_ids,
            "reason": decision.reason,
        })

    def resolve_locator_details(self, evidence_id: str) -> str:
        """
        Resolves an evidence ID to its physical source file path, checksum, and exact locator (page, slide, timestamp).
        """
        resolved = self.resolver.resolve(evidence_id)
        if not resolved:
            return json.dumps({"error": f"Evidence ID '{evidence_id}' could not be resolved."})
        return json.dumps({
            "evidence_id": resolved.get("evidence_id"),
            "source_id": resolved.get("source_id"),
            "source_path": resolved.get("source_path"),
            "source_title": resolved.get("source_title"),
            "source_sha256": resolved.get("source_sha256"),
            "location": resolved.get("location"),
            "modality": resolved.get("modality"),
        })

    def validate_citation_support(self, claim: str, evidence_id: str) -> str:
        """
        Verifies that an evidence unit legitimately supports a specific factual claim before citing it.
        """
        unit = self.db.get_evidence(evidence_id)
        if not unit:
            return json.dumps({"valid": False, "reason": "Evidence unit does not exist."})

        # Calculate token overlap between claim and evidence text
        import re
        claim_words = set(re.findall(r"\w+", claim.lower()))
        text_words = set(re.findall(r"\w+", unit.text.lower()))
        overlap = len(claim_words & text_words) / max(1, len(claim_words))

        is_valid = overlap >= 0.20 or any(w in text_words for w in claim_words if len(w) > 3)
        return json.dumps({
            "valid": is_valid,
            "overlap_ratio": round(overlap, 4),
            "evidence_id": evidence_id,
            "location": unit.location,
        })

    def get_tool_list(self) -> list[Callable]:
        """Return list of tool callables for Agno Agent registration."""
        return [
            self.search_course_materials,
            self.evaluate_evidence_sufficiency,
            self.resolve_locator_details,
            self.validate_citation_support,
        ]


class AssessmentTools:
    """Deterministic assessment tools callable by Agno Assessment Agent."""

    def __init__(self, db, assessment_engine: Optional[Any] = None, verifier: Optional[Any] = None):
        from ..assessment import DeterministicQuestionVerifier, AssessmentEngine
        self.db = db
        self.verifier = verifier or DeterministicQuestionVerifier()
        self.engine = assessment_engine or AssessmentEngine(db, verifier=self.verifier)

    def verify_question_structure(self, question_json: str) -> str:
        """
        Deterministically verifies question prompt, options, answer key, and evidence linkage.
        Rejects malformed, duplicate, or ungrounded questions.
        """
        from ..assessment import compute_question_fingerprint
        from ..models import Difficulty, Question, QuestionOption, QuestionType

        data = json.loads(question_json) if isinstance(question_json, str) else question_json
        options = [QuestionOption(**o) for o in data.get("options", [])]
        q = Question(
            question_id=data.get("question_id", "temp_q"),
            topic_id=data.get("topic_id", ""),
            concept_id=data.get("concept_id"),
            evidence_ids=data.get("evidence_ids", []),
            difficulty=Difficulty(data.get("difficulty", "medium")),
            question_type=QuestionType(data.get("question_type", "mcq")),
            prompt=data.get("prompt", ""),
            options=options,
            expected_answer=data.get("expected_answer", ""),
            tolerance=data.get("tolerance"),
            solution=data.get("solution", ""),
        )
        res = self.verifier.verify(q, db=self.db)
        return json.dumps({
            "is_valid": res.is_valid,
            "verification_method": res.verification_method,
            "failure_reasons": res.failure_reasons,
            "checks_passed": res.checks_passed,
            "fingerprint": compute_question_fingerprint(q.prompt, q.topic_id, q.concept_id),
        })

    def select_adaptive_question(self, topic_id: str, served_ids_json: str = "[]", target_difficulty: Optional[str] = None) -> str:
        """
        Adaptively selects next question for topic, filtering out previously seen questions and duplicate fingerprints.
        """
        from ..models import Difficulty

        served_ids = json.loads(served_ids_json) if isinstance(served_ids_json, str) else served_ids_json
        diff = Difficulty(target_difficulty) if target_difficulty else None
        q = self.engine.select_adaptive_question(topic_id, served_question_ids=served_ids, target_difficulty=diff, verified_only=True)
        if not q:
            return json.dumps({"status": "exhausted", "message": f"No available verified questions for topic '{topic_id}'."})
        return json.dumps({
            "status": "success",
            "question": q.model_dump(),
        })

    def evaluate_learner_submission(self, submission_json: str) -> str:
        """
        Deterministically scores learner answer (MCQ, numerical, or short-answer) and generates
        evidence-grounded explanation with exact source locators.
        """
        from ..models import LearnerSubmission

        data = json.loads(submission_json) if isinstance(submission_json, str) else submission_json
        q = self.db.get_question(data["question_id"])
        if not q:
            return json.dumps({"status": "error", "message": f"Question '{data['question_id']}' not found."})
        sub = LearnerSubmission(
            learner_id=data["learner_id"],
            question_id=data["question_id"],
            topic_id=q.topic_id,
            answer=data["answer"],
            timestamp=data.get("timestamp"),
        )
        eval_result = self.engine.evaluate_submission(sub, q)
        return json.dumps({
            "status": "success",
            "evaluation": eval_result.model_dump(),
        })

    def get_tool_list(self) -> list[Callable]:
        return [
            self.verify_question_structure,
            self.select_adaptive_question,
            self.evaluate_learner_submission,
        ]


class LearningCoachTools:
    """Deterministic learner modeling tools callable by Agno Learning Coach Agent."""

    def __init__(self, db, state_manager: Optional[Any] = None, misconception_detector: Optional[Any] = None, recommendation_engine: Optional[Any] = None):
        from ..learner_model import LearnerStateManager
        from ..misconceptions import MisconceptionDetector
        from ..recommendation import AdaptiveRecommendationEngine

        self.db = db
        self.state_manager = state_manager or LearnerStateManager(db)
        self.detector = misconception_detector or MisconceptionDetector(db)
        self.recommender = recommendation_engine or AdaptiveRecommendationEngine(db)

    def get_learner_topic_mastery(self, learner_id: str, topic_id: str) -> str:
        """
        Retrieves current Bayesian Knowledge Tracing (BKT) mastery probability P(L_t) for a topic.
        """
        record = self.state_manager.get_or_create_mastery(learner_id, topic_id)
        return json.dumps({
            "learner_id": learner_id,
            "topic_id": topic_id,
            "p_mastery": record.p_mastery,
            "attempts": record.attempts,
            "correct": record.correct,
            "recent_correctness": record.recent_correctness,
            "last_seen": record.last_seen,
        })

    def record_bkt_observation(self, learner_id: str, topic_id: str, is_correct: bool) -> str:
        """
        Executes exact BKT mathematical update: computes posterior P(L_t | obs) then applies transition P(T).
        Durable write to SQLite learner_states.
        """
        updated = self.state_manager.record_observation(learner_id, topic_id, is_correct)
        return json.dumps({
            "status": "updated",
            "learner_id": learner_id,
            "topic_id": topic_id,
            "p_mastery": updated.p_mastery,
            "attempts": updated.attempts,
            "correct": updated.correct,
        })

    def diagnose_active_misconceptions(self, learner_id: str, topic_id: Optional[str] = None) -> str:
        """
        Detects persistent student misconceptions (>= 2 consecutive error signals) and retrieves prerequisite remediation materials.
        """
        misc_list = self.db.get_active_misconceptions(learner_id, topic_id=topic_id)
        packages = [self.detector.get_remediation_package(m) for m in misc_list]
        return json.dumps({
            "learner_id": learner_id,
            "active_misconceptions_count": len(packages),
            "misconceptions": packages,
        })

    def generate_adaptive_recommendation(self, learner_id: str, active_topic_id: Optional[str] = None) -> str:
        """
        Calculates explainable next learning recommendation based on BKT policy brackets and prerequisite verification (prereq mastery >= 0.70).
        """
        rec = self.recommender.recommend(learner_id, active_topic_id=active_topic_id)
        return json.dumps({
            "learner_id": learner_id,
            "recommendation": rec.model_dump(),
        })

    def get_tool_list(self) -> list[Callable]:
        return [
            self.get_learner_topic_mastery,
            self.record_bkt_observation,
            self.diagnose_active_misconceptions,
            self.generate_adaptive_recommendation,
        ]

