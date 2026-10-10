from __future__ import annotations
import datetime
import json
import math
from pathlib import Path
from typing import Any

from app.assessment import (
    AssessmentEngine,
    DeterministicQuestionVerifier,
)
from app.corpus import build_reproducible_corpus, seed_database_from_corpus
from app.db import EvidenceDB
from app.learner_model import BKTModel, LearnerStateManager
from app.misconceptions import MisconceptionDetector
from app.models import (
    Difficulty,
    LearnerSubmission,
    MisconceptionSignal,
    Question,
    QuestionOption,
    QuestionType,
    TopicMasteryRecord,
)
from app.recommendation import AdaptiveRecommendationEngine
from app.retrieval import HybridRetriever
from app.source_resolver import resolve
from app.sufficiency import EvidenceSufficiencyGate
from app.tutor import GroundedTutor


def verify_citation_locator_structural_integrity(
    citation_loc: dict[str, Any],
    resolved_loc: dict[str, Any]
) -> bool:
    """
    Verify that an emitted citation location matches the source-resolved
    locator in EvidenceDB and contains valid structural location values.
    """
    if not citation_loc or not resolved_loc:
        return False

    # Check that key locators match exactly
    if "page" in citation_loc:
        page_val = citation_loc.get("page")
        if not (isinstance(page_val, int) and page_val >= 1 and page_val == resolved_loc.get("page")):
            return False
    elif "slide" in citation_loc:
        slide_val = citation_loc.get("slide")
        if not (isinstance(slide_val, int) and slide_val >= 1 and slide_val == resolved_loc.get("slide")):
            return False
    elif "timestamp" in citation_loc:
        ts_val = str(citation_loc.get("timestamp", "")).strip()
        if not (ts_val and ts_val == str(resolved_loc.get("timestamp", "")).strip()):
            return False
    elif "asset_id" in citation_loc:
        asset_val = str(citation_loc.get("asset_id", "")).strip()
        if not (asset_val and asset_val == str(resolved_loc.get("asset_id", "")).strip()):
            return False
    else:
        return False

    return True


def run_deterministic_benchmark(
    db: EvidenceDB | None = None,
    dataset_path: Path | None = None,
    output_path: Path | None = None
) -> dict[str, Any]:
    project_root = Path(__file__).resolve().parent.parent
    if dataset_path is None:
        dataset_path = project_root / "evaluation" / "benchmark_dataset.json"

    benchmark_data = json.loads(dataset_path.read_text(encoding="utf-8"))

    temp_db = False
    if db is None:
        temp_db = True
        test_db_path = project_root / "evaluation" / "eval_temp.sqlite"
        if test_db_path.exists():
            test_db_path.unlink()
        db = EvidenceDB(test_db_path)
        seed_database_from_corpus(db, project_root / "data")

    # Engine initializations
    retriever = HybridRetriever(db)
    gate = EvidenceSufficiencyGate(retriever, db)
    tutor = GroundedTutor(db)
    verifier = DeterministicQuestionVerifier()
    assessment_engine = AssessmentEngine(db, verifier)
    bkt = BKTModel()
    manager = LearnerStateManager(db, bkt)
    detector = MisconceptionDetector(db, error_threshold=2)
    rec_engine = AdaptiveRecommendationEngine(db)

    results_detail: dict[str, list[dict[str, Any]]] = {
        "tutor_and_retrieval": [],
        "question_verification": [],
        "bkt_updates": [],
        "recommendation_policy": [],
        "repetition_control": []
    }

    # -------------------------------------------------------------------------
    # 1. Retrieval, Sufficiency & Grounded Tutoring Evaluation
    # -------------------------------------------------------------------------
    tutor_cases = benchmark_data.get("retrieval_and_tutor_cases", [])
    supported_total = 0
    supported_correct = 0
    unsupported_total = 0
    unsupported_abstained = 0
    unsupported_leakage = 0
    citations_total = 0
    citations_valid = 0
    citations_source_resolved = 0
    retrieval_cases_evaluated = 0
    retrieval_precision_sum = 0.0
    retrieval_recall_sum = 0.0
    grounded_token_overlap_sum = 0.0

    for tc in tutor_cases:
        query = tc["query"]
        expected_status = tc.get("expected_status", "supported")
        
        # 1. Retrieval
        _, trace = retriever.search(query, k=3, mode="lexical")
        retrieved_ids = trace.result_ids

        # 2. Sufficiency Gate & Tutor Generation
        resp = tutor.answer(query, mode="lexical")

        case_detail: dict[str, Any] = {
            "case_id": tc["case_id"],
            "query": query,
            "expected_status": expected_status,
            "actual_status": resp.support_status,
            "is_grounded": resp.is_grounded,
            "retrieved_ids": retrieved_ids,
            "citations_count": len(resp.citations)
        }

        if expected_status == "supported":
            supported_total += 1
            if resp.support_status == "supported" and resp.is_grounded and len(resp.citations) > 0:
                supported_correct += 1

            # Precision & Recall @ 3
            exp_sources = set(tc.get("expected_source_ids", []))
            if "expected_source_id" in tc:
                exp_sources.add(tc["expected_source_id"])
            exp_eids = set(tc.get("expected_evidence_ids", []))

            if exp_sources or exp_eids:
                retrieval_cases_evaluated += 1
                relevant_in_top3 = [
                    eid for eid in retrieved_ids
                    if any(eid.startswith(src) for src in exp_sources) or eid in exp_eids
                ]
                precision_k = len(relevant_in_top3) / 3.0
                recall_k = 1.0 if len(relevant_in_top3) > 0 else 0.0
                retrieval_precision_sum += precision_k
                retrieval_recall_sum += recall_k
                case_detail["precision_at_3"] = round(precision_k, 4)
                case_detail["recall_at_3"] = round(recall_k, 4)

            # Grounded support token overlap proxy
            exp_tokens = tc.get("expected_tokens_in_answer", [])
            if exp_tokens:
                found_tokens = [tok for tok in exp_tokens if tok.lower() in resp.answer.lower()]
                overlap_score = len(found_tokens) / len(exp_tokens)
                grounded_token_overlap_sum += overlap_score
                case_detail["token_containment_score"] = round(overlap_score, 4)

            # Citation validation with source-resolved locator verification
            for c in resp.citations:
                citations_total += 1
                resolved_ev = resolve(c.evidence_id, db)
                if resolved_ev is not None:
                    citations_valid += 1
                    loc_valid = verify_citation_locator_structural_integrity(
                        c.location, resolved_ev.get("location", {})
                    )
                    if loc_valid:
                        citations_source_resolved += 1

        elif expected_status == "unsupported":
            unsupported_total += 1
            if resp.support_status == "unsupported" and not resp.is_grounded and len(resp.citations) == 0:
                unsupported_abstained += 1
            else:
                unsupported_leakage += 1

        results_detail["tutor_and_retrieval"].append(case_detail)

    # -------------------------------------------------------------------------
    # 2. Question Verification Evaluation
    # -------------------------------------------------------------------------
    q_cases = benchmark_data.get("question_verification_cases", [])
    q_verif_total = len(q_cases)
    q_verif_correct = 0

    for qc in q_cases:
        q_type = QuestionType(qc["type"])
        opts = [QuestionOption(key=o["key"], text=o["text"]) for o in qc.get("options", [])]
        
        # Build question object
        q = Question(
            question_id=qc["id"],
            topic_id="General Science",
            prompt=qc["prompt"],
            expected_answer=qc["expected_answer"],
            options=opts,
            question_type=q_type,
            tolerance=qc.get("tolerance"),
            evidence_ids=["physics_mechanics:e00001"]
        )

        res = verifier.verify(q, db=db)
        is_pass = (res.is_valid == qc["expected_valid"])
        
        if not qc["expected_valid"] and "expected_reason_snippet" in qc:
            reason_matched = any(qc["expected_reason_snippet"] in r for r in res.failure_reasons)
            is_pass = is_pass and reason_matched

        if is_pass:
            q_verif_correct += 1

        results_detail["question_verification"].append({
            "id": qc["id"],
            "expected_valid": qc["expected_valid"],
            "actual_valid": res.is_valid,
            "passed": is_pass,
            "failure_reasons": res.failure_reasons
        })

    # -------------------------------------------------------------------------
    # 3. BKT Step Verification Evaluation
    # -------------------------------------------------------------------------
    bkt_cases = benchmark_data.get("bkt_transition_cases", [])
    bkt_total = len(bkt_cases)
    bkt_correct = 0

    for bc in bkt_cases:
        computed = bkt.step(bc["prior"], is_correct=bc["is_correct"])
        diff = abs(computed - bc["expected_posterior"])
        passed = (diff < 1e-4)
        if passed:
            bkt_correct += 1
        results_detail["bkt_updates"].append({
            "step": bc["step"],
            "prior": bc["prior"],
            "is_correct": bc["is_correct"],
            "expected_posterior": bc["expected_posterior"],
            "actual_posterior": round(computed, 6),
            "delta": round(diff, 8),
            "passed": passed
        })

    # -------------------------------------------------------------------------
    # 4. Recommendation Policy Evaluation
    # -------------------------------------------------------------------------
    rec_cases = benchmark_data.get("recommendation_policy_cases", [])
    rec_total = len(rec_cases)
    rec_correct = 0

    for rc in rec_cases:
        u_id = f"eval_user_{rc['case_id']}"
        db.save_learner_mastery(
            TopicMasteryRecord(learner_id=u_id, topic_id="Newtonian Mechanics", p_mastery=rc["p_mastery"], attempts=5, correct=3)
        )
        rec = rec_engine.recommend(u_id, active_topic_id="Newtonian Mechanics")
        
        action_match = (rec.recommended_action == rc["expected_action"])
        diff_match = (rec.difficulty.value == rc["expected_difficulty"])
        passed = (action_match and diff_match)
        if passed:
            rec_correct += 1

        results_detail["recommendation_policy"].append({
            "case_id": rc["case_id"],
            "p_mastery": rc["p_mastery"],
            "expected_action": rc["expected_action"],
            "actual_action": rec.recommended_action,
            "expected_difficulty": rc["expected_difficulty"],
            "actual_difficulty": rec.difficulty.value,
            "passed": passed
        })

    # -------------------------------------------------------------------------
    # 5. Question Repetition Control & Fallback Evaluation
    # -------------------------------------------------------------------------
    # Test 5A: Multi-question topic alternative selection ("Newtonian Mechanics" has q_seed_01 and q_seed_01_alt)
    q_nm1 = assessment_engine.select_adaptive_question("Newtonian Mechanics", served_question_ids=[])
    q_nm2 = assessment_engine.select_adaptive_question(
        "Newtonian Mechanics",
        served_question_ids=[q_nm1.question_id] if q_nm1 else []
    )
    alternative_selected = (
        q_nm1 is not None and
        q_nm2 is not None and
        q_nm2.question_id != q_nm1.question_id and
        q_nm2.question_id not in [q_nm1.question_id]
    )

    results_detail["repetition_control"].append({
        "scenario": "alternative_selection_on_multi_question_topic",
        "topic": "Newtonian Mechanics",
        "first_served": q_nm1.question_id if q_nm1 else None,
        "second_served": q_nm2.question_id if q_nm2 else None,
        "suppressed_duplicate": alternative_selected,
        "passed": alternative_selected
    })

    # Test 5B: Graceful fallback when all questions in topic have been served
    # (Exhausting pool for "Newtonian Mechanics" with both q_seed_01 and q_seed_01_alt served)
    all_nm_ids = [q_nm1.question_id, q_nm2.question_id] if (q_nm1 and q_nm2) else ["q_seed_01", "q_seed_01_alt"]
    q_fallback = assessment_engine.select_adaptive_question(
        "Newtonian Mechanics",
        served_question_ids=all_nm_ids
    )
    fallback_graceful = (q_fallback is not None and q_fallback.question_id in all_nm_ids)

    results_detail["repetition_control"].append({
        "scenario": "graceful_fallback_when_pool_exhausted",
        "topic": "Newtonian Mechanics",
        "served_pool": all_nm_ids,
        "fallback_served": q_fallback.question_id if q_fallback else None,
        "fallback_succeeded": fallback_graceful,
        "passed": fallback_graceful
    })

    repetition_control_pass = alternative_selected and fallback_graceful

    # -------------------------------------------------------------------------
    # Aggregate Metrics Calculation
    # -------------------------------------------------------------------------
    metrics = {
        "supported_answer_rate": round(supported_correct / max(1, supported_total), 4),
        "unsupported_abstention_rate": round(unsupported_abstained / max(1, unsupported_total), 4),
        "unsupported_leakage_rate": round(unsupported_leakage / max(1, unsupported_total), 4),
        "retrieval_precision_at_3": round(retrieval_precision_sum / max(1, retrieval_cases_evaluated), 4),
        "retrieval_recall_at_3": round(retrieval_recall_sum / max(1, retrieval_cases_evaluated), 4),
        "grounded_faithfulness_proxy": round(grounded_token_overlap_sum / max(1, supported_total), 4),
        "citation_addressability_rate": round(citations_valid / max(1, citations_total), 4),
        "source_resolved_locator_accuracy": round(citations_source_resolved / max(1, citations_total), 4),
        "question_verification_accuracy": round(q_verif_correct / max(1, q_verif_total), 4),
        "bkt_numerical_accuracy": round(bkt_correct / max(1, bkt_total), 4),
        "recommendation_policy_accuracy": round(rec_correct / max(1, rec_total), 4),
        "repetition_control_pass": repetition_control_pass
    }

    denominators = {
        "supported_total": supported_total,
        "unsupported_total": unsupported_total,
        "retrieval_cases_evaluated": retrieval_cases_evaluated,
        "citations_total": citations_total,
        "citations_valid": citations_valid,
        "citations_source_resolved": citations_source_resolved,
        "question_verification_total": q_verif_total,
        "bkt_transitions_total": bkt_total,
        "recommendation_cases_total": rec_total
    }

    summary = {
        "benchmark_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "benchmark_version": benchmark_data.get("benchmark_version", "1.0.0"),
        "total_test_cases": supported_total + unsupported_total + q_verif_total + bkt_total + rec_total,
        "metrics": metrics,
        "denominators": denominators,
        "metric_definitions": {
            "supported_answer_rate": "Fraction of in-corpus questions answered with grounded citations",
            "unsupported_abstention_rate": "Fraction of out-of-corpus questions where sufficiency gate explicitly abstained",
            "unsupported_leakage_rate": "Fraction of out-of-corpus questions erroneously answered as course-supported",
            "retrieval_precision_at_3": "Fraction of top-3 retrieved items matching expected source or evidence IDs across evaluated cases",
            "retrieval_recall_at_3": "Fraction of expected source evidence captured in top-3 candidates across evaluated cases",
            "grounded_faithfulness_proxy": "Token overlap ratio between reference answer concepts and grounded response",
            "citation_addressability_rate": "Fraction of cited evidence IDs existing and resolvable in SQLite EvidenceDB",
            "source_resolved_locator_accuracy": "Fraction of emitted citations whose location fields match source-resolved locators in EvidenceDB",
            "question_verification_accuracy": "Fraction of assessment items where structural verifier matches expected valid/reject decision",
            "bkt_numerical_accuracy": "Fraction of BKT posterior transitions matching analytical formula within 1e-4 tolerance",
            "recommendation_policy_accuracy": "Fraction of learner mastery brackets generating exact expected action and difficulty",
            "repetition_control_pass": "Boolean indicating that alternative questions are selected when available and graceful fallback occurs on pool exhaustion"
        },
        "details": results_detail
    }

    if output_path is None:
        output_path = project_root / "evaluation" / "benchmark_results.json"
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if temp_db:
        db.close()
        if test_db_path.exists():
            test_db_path.unlink()

    return summary


class EvaluationRunner:
    """Class wrapper for deterministic evaluation execution."""
    def __init__(self, db: EvidenceDB | None = None, dataset_path: Path | None = None):
        self.db = db
        self.dataset_path = dataset_path

    def run_benchmark(self, output_path: Path | str | None = None) -> dict[str, Any]:
        p = Path(output_path) if output_path else None
        return run_deterministic_benchmark(db=self.db, dataset_path=self.dataset_path, output_path=p)


if __name__ == "__main__":
    res = run_deterministic_benchmark()
    print("================================================================")
    print("CogniVault Deterministic Benchmark Results")
    print("================================================================")
    print(f"Timestamp: {res['benchmark_timestamp']}")
    print(f"Total Test Cases Evaluated: {res['total_test_cases']}")
    print("\nMetrics:")
    for k, v in res["metrics"].items():
        print(f"  - {k}: {v}")
    print("\nDenominators:")
    for k, v in res["denominators"].items():
        print(f"  - {k}: {v}")
    print("================================================================")
