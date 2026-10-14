from __future__ import annotations
import datetime
import json
from pathlib import Path
from typing import Any

from app.assessment import AssessmentEngine, DeterministicQuestionVerifier
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
from app.tutor import GroundedTutor

def simulate_multi_turn_learners(
    db: EvidenceDB | None = None,
    output_path: Path | None = None
) -> dict[str, Any]:
    project_root = Path(__file__).resolve().parent.parent

    temp_db = False
    if db is None:
        temp_db = True
        test_db_path = project_root / "evaluation" / "sim_temp.sqlite"
        if test_db_path.exists():
            test_db_path.unlink()
        db = EvidenceDB(test_db_path)
        seed_database_from_corpus(db, project_root / "data")

    bkt = BKTModel()
    manager = LearnerStateManager(db, bkt)
    detector = MisconceptionDetector(db, error_threshold=2)
    rec_engine = AdaptiveRecommendationEngine(db)
    assessment = AssessmentEngine(db)
    tutor = GroundedTutor(db)

    simulation_results: dict[str, Any] = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "scenarios": {},
        "baseline_comparison": {}
    }

    # =========================================================================
    # Scenario 1: Consistently Correct Learner (Rapid Mastery & Advancement)
    # =========================================================================
    learner_correct = "sim_learner_advancing"
    s1_history: list[dict[str, Any]] = []
    
    # Initial state
    rec0 = rec_engine.recommend(learner_correct, active_topic_id="Newtonian Mechanics")
    s1_history.append({"turn": 0, "action": rec0.recommended_action, "difficulty": rec0.difficulty.value, "p_mastery": 0.10})

    for turn in range(1, 5):
        m = manager.record_response(learner_correct, "Newtonian Mechanics", is_correct=True)
        rec = rec_engine.recommend(learner_correct, active_topic_id="Newtonian Mechanics")
        s1_history.append({
            "turn": turn,
            "response": "correct",
            "p_mastery": round(m.p_mastery, 4),
            "recommended_action": rec.recommended_action,
            "difficulty": rec.difficulty.value,
            "rationale": rec.rationale
        })

    simulation_results["scenarios"]["consistently_correct"] = {
        "learner_id": learner_correct,
        "turns": s1_history,
        "final_p_mastery": s1_history[-1]["p_mastery"],
        "final_action": s1_history[-1]["recommended_action"],
        "advanced_to_dependent_topic": ("Work and Energy" in s1_history[-1]["rationale"] or s1_history[-1]["recommended_action"] == "advance_topic")
    }

    # =========================================================================
    # Scenario 2: Consistently Incorrect Learner (Foundational Remediation)
    # =========================================================================
    learner_struggling = "sim_learner_struggling"
    s2_history: list[dict[str, Any]] = []

    for turn in range(1, 4):
        m = manager.record_response(learner_struggling, "Algebra", is_correct=False)
        rec = rec_engine.recommend(learner_struggling, active_topic_id="Algebra")
        s2_history.append({
            "turn": turn,
            "response": "incorrect",
            "p_mastery": round(m.p_mastery, 4),
            "recommended_action": rec.recommended_action,
            "difficulty": rec.difficulty.value
        })

    simulation_results["scenarios"]["consistently_incorrect"] = {
        "learner_id": learner_struggling,
        "turns": s2_history,
        "final_p_mastery": s2_history[-1]["p_mastery"],
        "final_action": s2_history[-1]["recommended_action"]
    }

    # =========================================================================
    # Scenario 3: Mixed Performance Learner (Adaptive Difficulty Progression)
    # =========================================================================
    learner_mixed = "sim_learner_mixed"
    s3_history: list[dict[str, Any]] = []
    # Prerequisite Wave Properties is already mastered (0.80) to evaluate Geometric Optics progression
    db.save_learner_mastery(TopicMasteryRecord(learner_id=learner_mixed, topic_id="Wave Properties", p_mastery=0.80, attempts=5, correct=4))
    # Pattern: C, I, C, C
    answers = [True, False, True, True]

    for turn, is_corr in enumerate(answers, start=1):
        m = manager.record_response(learner_mixed, "Geometric Optics", is_correct=is_corr)
        rec = rec_engine.recommend(learner_mixed, active_topic_id="Geometric Optics")
        s3_history.append({
            "turn": turn,
            "is_correct": is_corr,
            "p_mastery": round(m.p_mastery, 4),
            "recommended_action": rec.recommended_action,
            "difficulty": rec.difficulty.value
        })

    simulation_results["scenarios"]["mixed_performance"] = {
        "learner_id": learner_mixed,
        "turns": s3_history,
        "final_p_mastery": s3_history[-1]["p_mastery"],
        "final_action": s3_history[-1]["recommended_action"]
    }

    # =========================================================================
    # Scenario 4: Misconception Triggering and Remediation Recovery
    # =========================================================================
    learner_misc = "sim_learner_misconception"
    # 2 consecutive errors on Second Law
    sig1 = detector.analyze_attempt(learner_misc, "Newtonian Mechanics", "Second Law", is_correct=False)
    sig2 = detector.analyze_attempt(learner_misc, "Newtonian Mechanics", "Second Law", is_correct=False)
    rec_misc = rec_engine.recommend(learner_misc, active_topic_id="Newtonian Mechanics")

    # Learner completes remediation successfully
    m_remed = manager.record_response(learner_misc, "Newtonian Mechanics", is_correct=True)
    detector.resolve_misconception(learner_misc, "Newtonian Mechanics", "Second Law")
    rec_recovered = rec_engine.recommend(learner_misc, active_topic_id="Newtonian Mechanics")

    simulation_results["scenarios"]["misconception_remediation"] = {
        "learner_id": learner_misc,
        "error_threshold_enforced": (sig1 is None and sig2 is not None),
        "misconception_diagnosed": sig2.suspected_misconception if sig2 else None,
        "remediation_action_triggered": rec_misc.recommended_action,
        "remediation_concept": rec_misc.concept_id,
        "post_remediation_action": rec_recovered.recommended_action
    }

    # =========================================================================
    # Scenario 5: Prerequisite Readiness Gating
    # =========================================================================
    # Unverified prerequisite
    rec_unverified = rec_engine.recommend("sim_u_unverified", active_topic_id="Differential Calculus")
    # Low prerequisite (0.50)
    db.save_learner_mastery(TopicMasteryRecord(learner_id="sim_u_low_prereq", topic_id="Algebra", p_mastery=0.50, attempts=3, correct=1))
    db.save_learner_mastery(TopicMasteryRecord(learner_id="sim_u_low_prereq", topic_id="Differential Calculus", p_mastery=0.90, attempts=5, correct=5))
    rec_low_prereq = rec_engine.recommend("sim_u_low_prereq", active_topic_id="Differential Calculus")

    # Verified prerequisite (0.75)
    db.save_learner_mastery(TopicMasteryRecord(learner_id="sim_u_ready", topic_id="Algebra", p_mastery=0.75, attempts=6, correct=5))
    db.save_learner_mastery(TopicMasteryRecord(learner_id="sim_u_ready", topic_id="Differential Calculus", p_mastery=0.90, attempts=5, correct=5))
    rec_ready = rec_engine.recommend("sim_u_ready", active_topic_id="Differential Calculus")

    simulation_results["scenarios"]["prerequisite_gating"] = {
        "missing_prerequisite_blocked": (rec_unverified.recommended_action == "foundational_review" and rec_unverified.topic_id == "Algebra"),
        "low_prerequisite_blocked": (rec_low_prereq.recommended_action == "foundational_review" and rec_low_prereq.topic_id == "Algebra"),
        "ready_prerequisite_advanced": (rec_ready.recommended_action == "advance_topic")
    }

    # =========================================================================
    # Scenario 6: Boundary Values Check (0.39, 0.40, 0.69, 0.70, 0.85, 0.86)
    # =========================================================================
    boundaries = [0.39, 0.40, 0.69, 0.70, 0.85, 0.86]
    boundary_results: dict[str, str] = {}
    for b_val in boundaries:
        u_b = f"sim_u_b_{str(b_val).replace('.', '_')}"
        db.save_learner_mastery(TopicMasteryRecord(learner_id=u_b, topic_id="Cell Biology", p_mastery=b_val, attempts=5, correct=3))
        rec_b = rec_engine.recommend(u_b, active_topic_id="Cell Biology")
        boundary_results[str(b_val)] = f"{rec_b.recommended_action} ({rec_b.difficulty.value})"

    simulation_results["scenarios"]["boundary_values"] = boundary_results

    # =========================================================================
    # Comparative Baseline Analysis (Adaptive vs Static Non-Personalized Selection)
    # =========================================================================
    # Measure difficulty alignment across simulated trajectory
    # Adaptive assigns: easy (<0.40), medium (0.40-0.85), hard (>0.85)
    # Static Baseline assigns fixed medium difficulty to all learners regardless of mastery
    adaptive_actions = [s["difficulty"] for s in s1_history]
    static_actions = ["medium"] * len(s1_history)

    simulation_results["baseline_comparison"] = {
        "baseline_description": "Static Non-Personalized Assignment (Fixed Medium Difficulty)",
        "adaptive_description": "CogniVault BKT-Gated Adaptive Mastery Assignment",
        "comparison_metric": "Dynamic Difficulty Shift Rate",
        "adaptive_difficulty_trajectory": adaptive_actions,
        "static_difficulty_trajectory": static_actions,
        "measurement_scope": "Measures differentiation of assigned difficulty according to verified learner mastery state. Does not claim unproven longitudinal learning gains."
    }

    if output_path is None:
        output_path = project_root / "evaluation" / "simulation_results.json"
    output_path.write_text(json.dumps(simulation_results, indent=2), encoding="utf-8")

    if temp_db:
        db.close()
        if test_db_path.exists():
            test_db_path.unlink()

    return simulation_results


run_all_simulations = simulate_multi_turn_learners

if __name__ == "__main__":
    sim = simulate_multi_turn_learners()
    print("================================================================")
    print("CogniVault Multi-Turn Simulated Learner Results")
    print("================================================================")
    print(f"Timestamp: {sim['timestamp']}")
    for k, v in sim["scenarios"].items():
        print(f"\nScenario [{k}]:")
        print(json.dumps(v, indent=2))
    print("\nBaseline Comparison:")
    print(json.dumps(sim["baseline_comparison"], indent=2))
    print("================================================================")
