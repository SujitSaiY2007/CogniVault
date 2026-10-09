from __future__ import annotations
import hashlib
import json
import math
import re
from typing import Any
from .db import EvidenceDB
from .models import (
    AnswerEvaluation,
    Citation,
    Difficulty,
    LearnerSubmission,
    Modality,
    Question,
    QuestionOption,
    QuestionType,
    QuestionVerificationResult,
)
from .source_resolver import resolve

def compute_question_fingerprint(prompt: str, topic_id: str = "", concept_id: str | None = None) -> str:
    tokens = re.findall(r"[a-z0-9]+", prompt.lower())
    core_text = " ".join(sorted(tokens))
    key = f"{topic_id}:{concept_id or ''}:{core_text}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]

def parse_numerical_value(val: Any) -> float | None:
    """
    Parse a numerical input (str, int, float) into a finite float.
    Correctly handles:
      - Integers and floating point numbers: '42', '3.14', '-0.5'
      - Explicit positive and negative signs: '+12', '-4.5'
      - Scientific notation: '1.5e2', '-2.3e-4', '+1E6'
      - Comma thousand separators: '1,000.5' -> 1000.5
      - Whitespace stripping: '  42.0  '
    Rejects:
      - Non-numeric strings: 'abc', '12.3.4', '1.2e', '42 meters'
      - Non-finite values: 'NaN', 'inf', '-infinity'
      - Empty strings and None
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val) if math.isfinite(val) else None
    if not isinstance(val, str):
        return None

    cleaned = val.strip()
    if not cleaned:
        return None

    # Reject literal non-finite representations
    lower = cleaned.lower()
    if lower in {"nan", "+nan", "-nan", "inf", "+inf", "-inf", "infinity", "+infinity", "-infinity"}:
        return None

    # Remove standard thousands-separator commas if present
    if "," in cleaned:
        cleaned = cleaned.replace(",", "")

    try:
        parsed = float(cleaned)
        if math.isfinite(parsed):
            return parsed
        return None
    except (ValueError, TypeError):
        return None

class DeterministicQuestionVerifier:
    """
    Deterministic structural & key-integrity verifier for educational questions.

    Verification Scope & Guarantee:
      - STRUCTURAL VALIDITY: Validates prompt length, topic presence, and evidence addressability.
      - KEY-OPTION INTEGRITY: Establishes that MCQ options are unique, distinct, and that the
        expected answer unambiguously resolves to exactly one valid option key or option text.
      - NUMERICAL INTEGRITY: Validates parseability of numeric answers and non-negative tolerances.
      - SCOPE BOUNDARY: This verifier certifies structural and mapping integrity; it does NOT
        prove external factual domain truth of the prompt/answer against real-world knowledge
        without external ground-truth evidence alignment or LLM validation.
    """
    def verify(self, question: Question, db: EvidenceDB | None = None) -> QuestionVerificationResult:
        failures: list[str] = []
        passes: list[str] = []

        # 1. Prompt validity
        if not question.prompt or len(question.prompt.strip()) < 10:
            failures.append("Prompt is empty or too short (minimum 10 characters required)")
        else:
            passes.append("Prompt length valid")

        # 2. Topic validity
        if not question.topic_id or not question.topic_id.strip():
            failures.append("Missing topic_id")
        else:
            passes.append("Topic ID present")

        # 3. Source Evidence linkage
        if not question.evidence_ids:
            failures.append("Missing source evidence linkage (at least one evidence_id required)")
        else:
            passes.append(f"Linked to {len(question.evidence_ids)} evidence IDs")

        # 4. Database addressability check if DB is supplied
        if db is not None and question.evidence_ids:
            missing = [eid for eid in question.evidence_ids if db.get_evidence(eid) is None]
            if missing:
                failures.append(f"Referenced evidence IDs do not exist in database: {missing}")
            else:
                passes.append("All evidence IDs verified in database")

        # 5. Type-specific checks
        if question.question_type == QuestionType.mcq:
            if len(question.options) < 2:
                failures.append("MCQ must have at least 2 options")
            else:
                passes.append(f"MCQ option count ({len(question.options)}) valid")

            # Check unique option keys
            keys = [opt.key.strip().upper() for opt in question.options]
            if len(keys) != len(set(keys)):
                failures.append(f"Duplicate option keys in MCQ: {keys}")
            else:
                passes.append("Option keys unique")

            # Check unique option texts
            texts = [opt.text.strip().lower() for opt in question.options]
            if len(texts) != len(set(texts)):
                failures.append("Duplicate option texts found in MCQ options")
            else:
                passes.append("Option texts distinct")

            # Single unambiguous expected answer match
            exp_raw = question.expected_answer.strip()
            exp_upper = exp_raw.upper()
            exp_lower = exp_raw.lower()

            matching_keys = [k for k in keys if k == exp_upper]
            matching_texts = [t for t in texts if t == exp_lower]

            if not matching_keys and not matching_texts:
                failures.append(
                    f"Expected answer '{question.expected_answer}' does not match any valid option key {list(set(keys))} or option text"
                )
            elif matching_keys and matching_texts:
                # Check if the matched key belongs to the matched text option
                matched_key_for_text = [
                    opt.key.strip().upper() for opt in question.options if opt.text.strip().lower() == exp_lower
                ]
                if matched_key_for_text != matching_keys:
                    failures.append(
                        f"Expected answer '{question.expected_answer}' is ambiguous across multiple distinct options"
                    )
                else:
                    passes.append("Expected answer unambiguously matches exactly one MCQ option (structural verification)")
            else:
                passes.append("Expected answer unambiguously matches exactly one MCQ option (structural verification)")

        elif question.question_type == QuestionType.numerical:
            val = parse_numerical_value(question.expected_answer)
            if val is None:
                failures.append(f"Expected answer '{question.expected_answer}' is not a valid parseable finite number")
            else:
                passes.append(f"Expected numerical value parseable ({val})")

            if question.tolerance is not None:
                if not isinstance(question.tolerance, (int, float)) or not math.isfinite(question.tolerance) or question.tolerance < 0.0:
                    failures.append(f"Numerical tolerance cannot be negative or non-finite: {question.tolerance}")
                else:
                    passes.append(f"Tolerance valid ({question.tolerance})")

        elif question.question_type == QuestionType.short_answer:
            if not question.expected_answer or len(question.expected_answer.strip()) < 1:
                failures.append("Short answer requires non-empty expected answer or rubric")
            else:
                passes.append("Short answer expected answer present")

        is_valid = (len(failures) == 0)
        return QuestionVerificationResult(
            question_id=question.question_id,
            is_valid=is_valid,
            verification_method="deterministic",
            failure_reasons=failures,
            checks_passed=passes,
            scope="structural_integrity"
        )


class AssessmentEngine:
    def __init__(self, db: EvidenceDB, verifier: DeterministicQuestionVerifier | None = None):
        self.db = db
        self.verifier = verifier or DeterministicQuestionVerifier()

    def build_and_verify_question(
        self,
        question_id: str,
        topic_id: str,
        prompt: str,
        expected_answer: str,
        evidence_ids: list[str],
        concept_id: str | None = None,
        difficulty: Difficulty = Difficulty.medium,
        question_type: QuestionType = QuestionType.mcq,
        options: list[QuestionOption] | None = None,
        tolerance: float | None = None,
        solution: str = "",
        metadata: dict | None = None
    ) -> Question:
        fp = compute_question_fingerprint(prompt, topic_id=topic_id, concept_id=concept_id)
        q = Question(
            question_id=question_id,
            topic_id=topic_id,
            concept_id=concept_id,
            evidence_ids=evidence_ids,
            difficulty=difficulty,
            question_type=question_type,
            prompt=prompt,
            options=options or [],
            expected_answer=expected_answer,
            tolerance=tolerance,
            solution=solution,
            verification_status="unverified",
            fingerprint=fp,
            metadata=metadata or {}
        )

        res = self.verifier.verify(q, db=self.db)
        if res.is_valid:
            q.verification_status = "verified"
            q.verification_reason = None
        else:
            q.verification_status = "rejected"
            q.verification_reason = "; ".join(res.failure_reasons)

        self.db.add_question(q)
        return q

    def select_adaptive_question(
        self,
        topic_id: str,
        served_question_ids: set[str] | list[str] | None = None,
        target_difficulty: Difficulty | None = None,
        verified_only: bool = True
    ) -> Question | None:
        all_q = self.db.get_questions_for_topic(topic_id, verified_only=verified_only)
        if not all_q:
            return None

        served_ids = set(served_question_ids or [])
        served_fps = {q.fingerprint for q in all_q if q.question_id in served_ids}

        # Repetition Control (A3):
        # Filter out questions that have been seen or share the same fingerprint
        unseen_candidates = [
            q for q in all_q
            if q.question_id not in served_ids and q.fingerprint not in served_fps
        ]

        # If unseen alternatives exist, choose among them
        pool = unseen_candidates if unseen_candidates else all_q

        if target_difficulty is not None:
            diff_matched = [q for q in pool if q.difficulty == target_difficulty]
            if diff_matched:
                pool = diff_matched

        # Return stable deterministic first choice
        pool.sort(key=lambda q: (q.repetition_count, q.question_id))
        return pool[0]

    def evaluate_submission(
        self,
        submission: LearnerSubmission,
        question: Question
    ) -> AnswerEvaluation:
        user_ans = submission.answer.strip()
        is_correct = False

        if question.question_type == QuestionType.mcq:
            user_clean = user_ans.upper()
            exp_clean = question.expected_answer.strip().upper()

            # Check if user passed the option key (e.g. "A") or the full option text
            if user_clean == exp_clean:
                is_correct = True
            else:
                # Match against option text
                for opt in question.options:
                    if opt.key.upper() == exp_clean and opt.text.strip().lower() == user_ans.lower():
                        is_correct = True
                        break
                    if opt.key.upper() == user_clean and opt.text.strip().lower() == question.expected_answer.strip().lower():
                        is_correct = True
                        break

        elif question.question_type == QuestionType.numerical:
            user_val = parse_numerical_value(user_ans)
            exp_val = parse_numerical_value(question.expected_answer)
            if user_val is None or exp_val is None:
                is_correct = False
            else:
                tol = (
                    question.tolerance
                    if (question.tolerance is not None and isinstance(question.tolerance, (int, float)) and math.isfinite(question.tolerance) and question.tolerance >= 0.0)
                    else 1e-5
                )
                is_correct = abs(user_val - exp_val) <= tol

        elif question.question_type == QuestionType.short_answer:
            # Rubric / keyword matching
            exp_tokens = set(re.findall(r"\w+", question.expected_answer.lower()))
            user_tokens = set(re.findall(r"\w+", user_ans.lower()))
            overlap = len(exp_tokens & user_tokens) / max(1, len(exp_tokens))
            is_correct = (overlap >= 0.70)

        # Resolve citations for evidence-grounded feedback (A4)
        citations: list[Citation] = []
        loc_strings = []
        for eid in question.evidence_ids:
            resolved = resolve(eid, self.db)
            if resolved:
                mod_str = resolved.get("modality", "text")
                try:
                    mod_enum = Modality(mod_str)
                except ValueError:
                    mod_enum = Modality.text
                loc = resolved.get("location", {})
                if "page" in loc:
                    loc_strings.append(f"Page {loc['page']}")
                elif "slide" in loc:
                    loc_strings.append(f"Slide {loc['slide']}")
                elif "timestamp" in loc:
                    loc_strings.append(f"Timestamp {loc['timestamp']}")

                citations.append(
                    Citation(
                        evidence_id=eid,
                        source_id=resolved.get("source_id", ""),
                        modality=mod_enum,
                        location=loc,
                        snippet=resolved.get("text", "")[:300],
                        source_path=resolved.get("source_path"),
                        source_title=resolved.get("source_title")
                    )
                )

        loc_cite = f" (Refer to {', '.join(loc_strings)})" if loc_strings else ""

        if is_correct:
            status = "correct"
            feedback = f"Correct! Well done.{loc_cite} {question.solution}".strip()
            remediation = None
            remediation_eids = []
        else:
            status = "incorrect"
            sol_note = f" Solution explanation: {question.solution}" if question.solution else ""
            feedback = (
                f"Incorrect. Your answer was '{user_ans}', but the expected answer is '{question.expected_answer}'.{sol_note}{loc_cite} "
                f"Recommended next action: Review {question.topic_id} concepts in the referenced source material."
            )
            remediation = f"review_topic:{question.topic_id}"
            remediation_eids = question.evidence_ids

        # Record interaction in database
        self.db.record_interaction(
            interaction_id=f"int_{submission.learner_id}_{question.question_id}_{hashlib.sha256(user_ans.encode()).hexdigest()[:8]}",
            learner_id=submission.learner_id,
            question_id=question.question_id,
            topic_id=question.topic_id,
            user_answer=user_ans,
            is_correct=is_correct,
            score=1.0 if is_correct else 0.0,
            feedback=feedback,
            timestamp=submission.timestamp
        )

        return AnswerEvaluation(
            learner_id=submission.learner_id,
            question_id=question.question_id,
            is_correct=is_correct,
            status=status,
            feedback=feedback,
            citations=citations,
            remediation_action=remediation,
            remediation_evidence_ids=remediation_eids
        )
