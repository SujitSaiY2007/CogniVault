"""Simulated students: does adaptive practice help, and is the learner model calibrated?

Each simulated student has a hidden true state per topic (known / not known).
  * Answer model: P(correct) = 1 - slip if known, else guess. True slip by difficulty
    0.05/0.10/0.20; guess 1/options for MCQ, 0.02 numerical, 0.05 short answer.
    These differ from the BKT parameters CogniVault assumes, on purpose.
  * Learning: after each practice item on an unknown topic the student learns it
    with probability 0.25 if all its prerequisites are known, else 0.08.
  * Profiles: novice / intermediate / advanced start with each topic known with
    probability 0.10 / 0.45 / 0.80.

Three policies get the same 6 sessions x 10 questions, with the same students (paired seeds):
  adaptive  CogniVault recommendation picks topic and difficulty; selection avoids repeats
  syllabus  fixed topic order (3 questions per topic, cycling); selection avoids repeats
  random    random topic, random question (repeats allowed), like a plain question bank

Metrics
  true_mastery     share of topics the student truly knows after each session (ground truth)
  repetition_rate  share of served questions the student had already seen
  auc / brier      how well BKT's predicted P(correct) before each answer matches outcomes
  estimate_mae     |BKT mastery - true state| per topic at the end, over practised topics

Run: python -m evaluation.simulate
"""
from __future__ import annotations

import json
import random
import time
from pathlib import Path

import numpy as np

from app.learner import predicted_correct
from app.models import PUBLIC_OWNER, Difficulty, QuestionType

from .run_eval import service

PROFILES = {"novice": 0.10, "intermediate": 0.45, "advanced": 0.80}
SLIP = {Difficulty.easy: 0.05, Difficulty.medium: 0.10, Difficulty.hard: 0.20}
SESSIONS, PER_SESSION, STUDENTS = 6, 10, 30


def guess(q):
    if q.question_type == QuestionType.mcq:
        return 1 / max(2, len(q.options))
    return 0.02 if q.question_type == QuestionType.numerical else 0.05


def auc(scores, labels):
    pos = [s for s, l in zip(scores, labels) if l]
    neg = [s for s, l in zip(scores, labels) if not l]
    if not pos or not neg:
        return float("nan")
    wins = 0.0
    for p in pos:
        for n in neg:
            wins += 1.0 if p > n else 0.5 if p == n else 0.0
    return wins / (len(pos) * len(neg))


def run():
    svc = service()
    topics = svc.db.topics(PUBLIC_OWNER)
    topics = [t for t in topics if svc.db.questions(PUBLIC_OWNER, t.topic_id)]
    tids = [t.topic_id for t in topics]
    prereq = {t.topic_id: [p for p in t.prerequisites if p in tids] for t in topics}
    bank = {t: svc.db.questions(PUBLIC_OWNER, t) for t in tids}
    t0 = time.time()
    results: dict = {}
    for policy in ["adaptive", "syllabus", "random"]:
        results[policy] = {}
        for profile, p0 in PROFILES.items():
            curves, reps, preds, outs, maes = [], [], [], [], []
            for s in range(STUDENTS):
                rng = random.Random(f"{profile}-{s}")          # same student across policies
                act = random.Random(f"{policy}-{profile}-{s}")  # policy's own randomness
                known = {t: rng.random() < p0 for t in tids}
                sid = f"sim-{policy}-{profile}-{s}"
                seen: set[str] = set()
                served = repeated = 0
                curve = [sum(known.values()) / len(tids)]
                cursor = 0
                for _session in range(SESSIONS):
                    for _ in range(PER_SESSION):
                        if policy == "adaptive":
                            rec = svc.learner.recommend(sid, topics)
                            tid = rec.topic_id
                            q = svc.learner.select_question(sid, bank[tid], rec.difficulty)
                        elif policy == "syllabus":
                            tid = tids[(cursor // 3) % len(tids)]
                            cursor += 1
                            q = svc.learner.select_question(sid, bank[tid])
                        else:
                            tid = act.choice(tids)
                            q = act.choice(bank[tid])
                        served += 1
                        repeated += q.question_id in seen
                        seen.add(q.question_id)
                        preds.append(predicted_correct(svc.learner.current(sid, tid), q))
                        correct = rng.random() < ((1 - SLIP[q.difficulty]) if known[tid] else guess(q))
                        outs.append(correct)
                        if q.question_type == QuestionType.mcq:
                            ans = q.expected_answer if correct else next(o.key for o in q.options if o.key != q.expected_answer)
                        elif q.question_type == QuestionType.numerical:
                            ans = q.expected_answer if correct else str(float(q.expected_answer) * 3 + 7)
                        else:
                            ans = q.expected_answer if correct else "no idea"
                        svc.submit(sid, q.question_id, ans)
                        if not known[tid]:
                            rate = 0.25 if all(known[p] for p in prereq[tid]) else 0.08
                            known[tid] = rng.random() < rate
                    curve.append(sum(known.values()) / len(tids))
                curves.append(curve)
                reps.append(repeated / served)
                practised = {m.topic_id for m in svc.db.all_mastery(sid)}
                maes.extend(abs(svc.learner.current(sid, t) - (1.0 if known[t] else 0.0)) for t in practised)
            c = np.array(curves)
            results[policy][profile] = {
                "true_mastery_by_session": [round(float(x), 4) for x in c.mean(axis=0)],
                "gain": round(float((c[:, -1] - c[:, 0]).mean()), 4),
                "repetition_rate": round(float(np.mean(reps)), 4),
                "auc": round(auc(preds, outs), 4),
                "brier": round(float(np.mean([(p - o) ** 2 for p, o in zip(preds, outs)])), 4),
                "estimate_mae": round(float(np.mean(maes)), 4),
                "_final": [float(x) for x in c[:, -1]],
            }
    # Paired comparison: same students under adaptive vs each baseline.
    results["adaptive_vs_baselines"] = {}
    for base in ["syllabus", "random"]:
        for profile in PROFILES:
            d = np.array(results["adaptive"][profile]["_final"]) - np.array(results[base][profile]["_final"])
            half = 1.96 * d.std(ddof=1) / np.sqrt(len(d))
            results["adaptive_vs_baselines"][f"{profile}_vs_{base}"] = {
                "mean_diff": round(float(d.mean()), 4), "ci95": [round(float(d.mean() - half), 4), round(float(d.mean() + half), 4)]}
    for policy in ["adaptive", "syllabus", "random"]:
        for profile in PROFILES:
            results[policy][profile].pop("_final")
    results["settings"] = {"students_per_profile": STUDENTS, "sessions": SESSIONS, "questions_per_session": PER_SESSION,
                           "topics": len(tids), "runtime_seconds": round(time.time() - t0, 1)}
    out = Path(__file__).resolve().parent / "results"
    out.mkdir(exist_ok=True)
    (out / "simulation.json").write_text(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
