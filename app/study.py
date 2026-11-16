"""Study tools built on the learner model: flashcards, a study plan, and the course map.

Flashcards use SM-2 scheduling. Grade 0-5 after each review:
    ease     <- max(1.3, ease + 0.1 - (5 - g)(0.08 + 0.02(5 - g)))
    interval <- 1, 6, then interval * ease;  reset to 1 if g < 3

The study plan spreads practice blocks over the days before an exam.
Each 20-minute practice block is expected to raise mastery by about 0.12.
Topics are scheduled in prerequisite order, weakest first. Mastered topics
get review blocks on the day their forgetting curve predicts they will
fall below 0.75. The last day is a mixed mock exam.
"""
from __future__ import annotations

import hashlib
import math
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from .db import Database
from .knowledge import Definition
from .learner import MASTERED, P_FLOOR, READY, TAU_DAYS, LearnerModel
from .models import TopicRecord

BLOCK_MIN = 20
BLOCK_GAIN = 0.12


def card_id(topic_id: str, front: str) -> str:
    return "card:" + hashlib.sha256(f"{topic_id}|{front}".encode()).hexdigest()[:16]


def build_cards(topics: list[TopicRecord], defs: dict[str, list[Definition]], formulas: dict[str, list[tuple[str, str]]]) -> list[dict[str, Any]]:
    cards = []
    for t in topics:
        for d in defs.get(t.topic_id, []):
            cards.append({"card_id": card_id(t.topic_id, d.term), "topic_id": t.topic_id, "topic_name": t.name,
                          "front": d.term, "back": d.sentence, "evidence_id": d.evidence_id, "kind": "definition"})
        for text, eid in formulas.get(t.topic_id, []):
            cards.append({"card_id": card_id(t.topic_id, text), "topic_id": t.topic_id, "topic_name": t.name,
                          "front": f"Formula: {text.split('=')[0].strip()} = ?", "back": text, "evidence_id": eid, "kind": "formula"})
    return cards


def sm2(ease: float, interval: float, reps: int, grade: int) -> tuple[float, float, int]:
    g = max(0, min(5, int(grade)))
    if g < 3:
        return max(1.3, ease - 0.2), 1.0, 0
    ease = max(1.3, ease + 0.1 - (5 - g) * (0.08 + 0.02 * (5 - g)))
    reps += 1
    interval = 1.0 if reps == 1 else 6.0 if reps == 2 else round(interval * ease, 2)
    return round(ease, 3), interval, reps


def due_cards(db: Database, model: LearnerModel, learner_id: str, cards: list[dict[str, Any]], limit: int = 20) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    state = db.cards(learner_id)
    out = []
    for c in cards:
        s = state.get(c["card_id"])
        due = datetime.fromisoformat(s["due"]) if s else now
        p = model.current(learner_id, c["topic_id"])
        overdue_days = (now - due).total_seconds() / 86400
        if s is None or overdue_days >= 0:
            out.append({**c, "due": due.isoformat(), "reps": s["reps"] if s else 0, "priority": round((1 - p) + 0.1 * max(0, overdue_days), 4)})
    out.sort(key=lambda c: (-c["priority"], c["card_id"]))
    return out[:limit]


def review_card(db: Database, learner_id: str, cid: str, grade: int) -> dict[str, Any]:
    s = db.get_card(learner_id, cid) or {"ease": 2.5, "interval_days": 0.0, "reps": 0}
    ease, interval, reps = sm2(s["ease"], s["interval_days"], s["reps"], grade)
    due = (datetime.now(timezone.utc) + timedelta(days=interval)).isoformat()
    db.put_card(learner_id, cid, ease, interval, reps, due)
    return {"card_id": cid, "ease": ease, "interval_days": interval, "reps": reps, "due": due}


def topo_order(topics: list[TopicRecord]) -> list[TopicRecord]:
    by = {t.topic_id: t for t in topics}
    out, seen = [], set()

    def visit(t: TopicRecord, stack: set[str]):
        if t.topic_id in seen or t.topic_id in stack:
            return
        stack.add(t.topic_id)
        for p in t.prerequisites:
            if p in by:
                visit(by[p], stack)
        seen.add(t.topic_id)
        out.append(t)

    for t in sorted(topics, key=lambda x: (x.owner_id == "public", x.source_id or "", x.position)):
        visit(t, set())
    return out


def study_plan(model: LearnerModel, learner_id: str, topics: list[TopicRecord], exam_date: Optional[str],
               minutes_per_day: int = 60, today: Optional[date] = None) -> dict[str, Any]:
    today = today or datetime.now(timezone.utc).date()
    try:
        exam = date.fromisoformat(exam_date) if exam_date else today + timedelta(days=14)
    except ValueError:
        exam = today + timedelta(days=14)
    days = max(1, min(60, (exam - today).days))
    per_day = max(1, min(8, minutes_per_day // BLOCK_MIN))
    ordered = topo_order(topics)
    mastery = {m.topic_id: m for m in model.db.all_mastery(learner_id)}
    need: dict[str, int] = {}
    for t in ordered:
        p = model.current(learner_id, t.topic_id)
        need[t.topic_id] = max(0, math.ceil((MASTERED - p) / BLOCK_GAIN)) if p < MASTERED else 0

    plan: list[dict[str, Any]] = [{"date": (today + timedelta(days=i)).isoformat(), "blocks": []} for i in range(days)]
    study_days = days - 1 if days > 2 else days
    total_capacity = study_days * per_day
    total_need = sum(need.values())
    wanted = total_need
    if total_need > total_capacity > 0:
        # Not enough time for everything: give every topic a fair share (at least one block)
        # instead of filling early topics and leaving the last ones with nothing.
        scale = total_capacity / total_need
        need = {tid: (max(1, int(n * scale)) if n else 0) for tid, n in need.items()}
        while sum(need.values()) > total_capacity:
            biggest = max(need, key=lambda k: need[k])
            if need[biggest] <= 1:
                break
            need[biggest] -= 1
    queue = [t for t in ordered if need[t.topic_id] > 0]
    max_topics_per_day = per_day if wanted > total_capacity else 2
    d = 0
    for t in queue:
        n = need[t.topic_id]
        while n > 0 and d < study_days:
            day = plan[d]
            if len(day["blocks"]) >= per_day or len({b["topic_id"] for b in day["blocks"]}) >= max_topics_per_day and t.topic_id not in {b["topic_id"] for b in day["blocks"]}:
                d += 1
                continue
            p = model.current(learner_id, t.topic_id)
            act = "Read cited passages, then easy questions" if p < 0.4 else "Targeted practice questions" if p < READY else "Mixed harder questions"
            day["blocks"].append({"topic_id": t.topic_id, "topic_name": t.name, "activity": act, "minutes": BLOCK_MIN, "kind": "practice"})
            n -= 1
    # Reviews for topics that are strong now but will fade before the exam.
    for t in ordered:
        m = mastery.get(t.topic_id)
        if not m or need[t.topic_id] > 0:
            continue
        tau = TAU_DAYS * (1 + m.correct)
        p_now = model.current(learner_id, t.topic_id)
        if p_now <= 0.75:
            continue
        t_drop = -tau * math.log((0.75 - P_FLOOR) / max(1e-6, p_now - P_FLOOR))
        day_i = min(study_days - 1, max(0, int(t_drop)))
        if day_i < days:
            target = plan[day_i]
            if len(target["blocks"]) < per_day + 1:
                target["blocks"].append({"topic_id": t.topic_id, "topic_name": t.name, "activity": "Spaced review: flashcards + 3 questions",
                                         "minutes": 10, "kind": "review"})
    if days > 2:
        plan[-1]["blocks"].append({"topic_id": "", "topic_name": "All topics", "activity": "Mock exam (mixed, timed)", "minutes": min(60, minutes_per_day), "kind": "exam"})
    warning = None
    if wanted > total_capacity:
        warning = (f"Full mastery of every topic needs about {wanted * BLOCK_MIN // 60} h {wanted * BLOCK_MIN % 60} min, "
                   f"but you have about {total_capacity * BLOCK_MIN // 60} h {total_capacity * BLOCK_MIN % 60} min before the exam. "
                   "The plan gives every topic a share of your time. Add daily time or move the exam date for more depth.")
    scheduled = [b for day in plan for b in day["blocks"]]
    return {"exam_date": exam.isoformat(), "days": days, "minutes_per_day": minutes_per_day, "plan": plan,
            "blocks_needed": wanted, "blocks_available": total_capacity, "warning": warning,
            "total_minutes": sum(b["minutes"] for b in scheduled),
            "topics_covered": len({b["topic_id"] for b in scheduled if b["topic_id"]}),
            "topics_total": len(ordered), "empty": not ordered}


def course_map(model: LearnerModel, learner_id: str, topics: list[TopicRecord]) -> dict[str, Any]:
    by = {t.topic_id: t for t in topics}
    depth: dict[str, int] = {}

    def dep(tid: str, stack=()) -> int:
        if tid in depth:
            return depth[tid]
        if tid in stack:
            return 0
        t = by[tid]
        d = 1 + max((dep(p, stack + (tid,)) for p in t.prerequisites if p in by), default=-1)
        depth[tid] = d
        return d

    nodes = []
    for t in topics:
        p = model.current(learner_id, t.topic_id)
        unmet = [x for x in t.prerequisites if x in by and model.current(learner_id, x) < READY]
        status = "mastered" if p >= MASTERED else "in_progress" if model.db.get_mastery(learner_id, t.topic_id) else ("locked" if unmet else "ready")
        nodes.append({"topic_id": t.topic_id, "name": t.name, "source_id": t.source_id, "depth": dep(t.topic_id),
                      "p_mastery": round(p, 3), "status": status, "concepts": t.concepts[:5]})
    edges = [{"from": p, "to": t.topic_id} for t in topics for p in t.prerequisites if p in by]
    return {"nodes": nodes, "edges": edges}
