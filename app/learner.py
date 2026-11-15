"""Learner model: Bayesian Knowledge Tracing with item-aware parameters,
partial credit, forgetting, misconception diagnosis and recommendations.

BKT update for one observation with score s in [0, 1]:
    prior            = P(L) + (1 - P(L)) * T     (learning since the last attempt; T = 0 on the first)
    P(L | correct)   = prior(1-S) / [prior(1-S) + (1-prior)G]
    P(L | incorrect) = prior S    / [prior S    + (1-prior)(1-G)]
    stored mastery   = s * P(L | correct) + (1-s) * P(L | incorrect)
Stored mastery is the posterior "probability the topic is known given the
answers so far", so it always falls after a wrong answer and rises after a
right one.
Guess G depends on the item: 1/(number of options) for MCQ, 0.05 for
numerical, 0.10 for short answer. Slip S grows with difficulty
(0.05 / 0.10 / 0.15).

Forgetting: between sessions mastery decays toward a floor,
    p(t) = floor + (p0 - floor) * exp(-dt / tau),  tau = 4 days * (1 + correct answers)
so well-practised topics are forgotten more slowly (a spacing effect).

A grounded tutor explanation counts as instruction, not evidence of
knowledge: it applies half a learning transition, and chat alone can never
raise mastery above 0.60.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from .db import Database, now_iso
from .models import Difficulty, MisconceptionSignal, Question, QuestionType, Recommendation, TopicMasteryRecord, TopicRecord

P_INIT = 0.15
P_TRANSIT = 0.15
P_FLOOR = 0.10
TAU_DAYS = 4.0
SLIP = {Difficulty.easy: 0.05, Difficulty.medium: 0.10, Difficulty.hard: 0.15}
CHAT_CAP = 0.60
MASTERED = 0.85
READY = 0.70


def guess_for(q: Optional[Question]) -> float:
    if q is None:
        return 0.2
    if q.question_type == QuestionType.mcq:
        return 1.0 / max(2, len(q.options))
    if q.question_type == QuestionType.numerical:
        return 0.05
    return 0.10


def bkt_update(p: float, score: float, guess: float, slip: float, transit: float = P_TRANSIT) -> float:
    """Learning transition on the prior, then the Bayes update on the answer."""
    p = min(max(p, 1e-4), 1 - 1e-4)
    p = p + (1 - p) * transit
    pc = p * (1 - slip) / (p * (1 - slip) + (1 - p) * guess)
    pi = p * slip / (p * slip + (1 - p) * (1 - guess))
    post = score * pc + (1 - score) * pi
    return round(min(max(post, 1e-4), 0.9999), 6)


def _days_since(ts: Optional[str], now: Optional[datetime] = None) -> float:
    if not ts:
        return 0.0
    try:
        t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    now = now or datetime.now(timezone.utc)
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return max(0.0, (now - t).total_seconds() / 86400)


def decayed(m: TopicMasteryRecord, now: Optional[datetime] = None) -> float:
    dt = _days_since(m.last_seen, now)
    if dt <= 0 or m.p_mastery <= P_FLOOR:
        return m.p_mastery
    tau = TAU_DAYS * (1 + m.correct)
    return round(P_FLOOR + (m.p_mastery - P_FLOOR) * math.exp(-dt / tau), 6)


def predicted_correct(p: float, q: Optional[Question]) -> float:
    g = guess_for(q)
    s = SLIP[q.difficulty] if q else 0.1
    return p * (1 - s) + (1 - p) * g


@dataclass
class MisconceptionRule:
    text: str
    threshold: int


def describe_pattern(pattern: str, concept: str, formula: str = "") -> str:
    if pattern.startswith("confused_with:"):
        other = pattern.split(":", 1)[1]
        return f"Mixing up {concept} with {other}"
    return {
        "sign_error": f"Sign errors when applying {formula or concept}",
        "power_of_ten": "Unit or power-of-ten conversion slips",
        "formula_misapplied": f"Misapplying the formula for {concept}",
        "rounding": "Rounding or precision errors",
        "wrong_value": f"Difficulty applying {formula or concept} to numbers",
        "wrong_term": f"Not yet recalling the term {concept}",
        "incomplete_term": f"Partial recall of {concept}",
        "wrong_option": f"Unsure about {concept}",
    }.get(pattern, f"Repeated difficulty with {concept}")


class LearnerModel:
    def __init__(self, db: Database):
        self.db = db

    # ---------------------------------------------------------------- mastery
    def mastery(self, learner_id: str, topic_id: str) -> TopicMasteryRecord:
        m = self.db.get_mastery(learner_id, topic_id)
        if m is None:
            m = TopicMasteryRecord(learner_id=learner_id, topic_id=topic_id, p_mastery=P_INIT)
        return m

    def current(self, learner_id: str, topic_id: str) -> float:
        m = self.db.get_mastery(learner_id, topic_id)
        return decayed(m) if m else P_INIT

    def observe(self, learner_id: str, q: Question, score: float, timestamp: Optional[str] = None) -> tuple[float, TopicMasteryRecord]:
        m = self.mastery(learner_id, q.topic_id)
        before = decayed(m)
        after = bkt_update(before, score, guess_for(q), SLIP[q.difficulty], transit=self.transit(m))
        ok = score >= 0.75
        m.p_mastery = after
        m.attempts += 1
        m.correct += 1 if ok else 0
        m.recent_correctness = (m.recent_correctness + [ok])[-10:]
        m.last_seen = timestamp or now_iso()
        self.db.put_mastery(m)
        return before, m

    @staticmethod
    def transit(m: TopicMasteryRecord) -> float:
        """Learning happens between practice opportunities, so it is applied to the
        prior of every observation after the first. Stored mastery is therefore the
        posterior P(known | answers so far), which falls after a wrong answer."""
        return P_TRANSIT if m.attempts > 0 else 0.0

    def observe_binary(self, learner_id: str, topic_id: str, correct: bool, timestamp: Optional[str] = None) -> TopicMasteryRecord:
        m = self.mastery(learner_id, topic_id)
        m.p_mastery = bkt_update(decayed(m), 1.0 if correct else 0.0, 0.2, 0.1, transit=self.transit(m))
        m.attempts += 1
        m.correct += int(correct)
        m.recent_correctness = (m.recent_correctness + [correct])[-10:]
        m.last_seen = timestamp or now_iso()
        self.db.put_mastery(m)
        return m

    def observe_instruction(self, learner_id: str, topic_id: str) -> TopicMasteryRecord:
        m = self.mastery(learner_id, topic_id)
        p = decayed(m)
        if p < CHAT_CAP:
            p = min(CHAT_CAP, p + (1 - p) * P_TRANSIT * 0.5)
        m.p_mastery = round(p, 6)
        m.last_seen = now_iso()
        self.db.put_mastery(m)
        return m

    def set_prior(self, learner_id: str, topic_id: str, self_rating: float) -> TopicMasteryRecord:
        """Self-reported level is weak evidence: map [0,1] to [0.10, 0.60]."""
        m = self.mastery(learner_id, topic_id)
        m.p_mastery = round(0.10 + 0.50 * min(1.0, max(0.0, self_rating)), 6)
        m.last_seen = now_iso()
        self.db.put_mastery(m)
        return m

    # --------------------------------------------------------- misconceptions
    def record_error(self, learner_id: str, q: Question, pattern: str) -> Optional[MisconceptionSignal]:
        concept = q.concept_id or q.topic_id
        total = self.db.bump_error(learner_id, q.topic_id, concept, pattern or "wrong")
        patterns = self.db.error_patterns(learner_id, q.topic_id, concept)
        top_pattern, top_count = max(patterns.items(), key=lambda kv: kv[1])
        # One wrong answer is a slip. Two on the same concept is a pattern.
        if total < 2:
            return None
        conf = min(0.95, 1 - 0.5 ** total + (0.1 if top_count >= 2 else 0.0))
        topic = self.db.get_topic(q.topic_id)
        remediation_topic = topic.prerequisites[0] if topic and topic.prerequisites and self.current(learner_id, topic.prerequisites[0]) < READY else q.topic_id
        ev = list(dict.fromkeys(q.evidence_ids + [e.evidence_id for e in self.db.evidence_for_topic(remediation_topic)[:2]]))
        sig = MisconceptionSignal(
            signal_id=f"misc:{learner_id}:{q.topic_id}:{concept}"[:180],
            learner_id=learner_id, topic_id=q.topic_id, concept_id=concept,
            suspected_misconception=describe_pattern(top_pattern, concept, q.metadata.get("formula", "")),
            error_count=total, confidence=round(conf, 3), remediation_concept_id=remediation_topic,
            remediation_evidence_ids=ev[:4],
            remediation_note=(
                f"Re-read the cited passages on {concept}" + (" and its prerequisite topic" if remediation_topic != q.topic_id else "")
                + ", then try two easier questions."
            ),
            created_at=now_iso(),
        )
        self.db.put_misconception(sig, active=True)
        m = self.mastery(learner_id, q.topic_id)
        if sig.suspected_misconception not in m.misconception_signals:
            m.misconception_signals = (m.misconception_signals + [sig.suspected_misconception])[-5:]
            self.db.put_mastery(m)
        return sig

    def record_success(self, learner_id: str, q: Question) -> None:
        concept = q.concept_id or q.topic_id
        m = self.mastery(learner_id, q.topic_id)
        # Two correct answers in a row on the topic clear the concept's signal.
        if len(m.recent_correctness) >= 2 and all(m.recent_correctness[-2:]):
            self.resolve(learner_id, q.topic_id, concept)

    def resolve(self, learner_id: str, topic_id: str, concept_id: Optional[str] = None) -> None:
        self.db.clear_errors(learner_id, topic_id, concept_id)
        self.db.deactivate_misconceptions(learner_id, topic_id, concept_id)
        m = self.db.get_mastery(learner_id, topic_id)
        if m:
            active = {s.suspected_misconception for s in self.db.active_misconceptions(learner_id, topic_id)}
            m.misconception_signals = [s for s in m.misconception_signals if s in active]
            self.db.put_mastery(m)

    # ---------------------------------------------------------- recommendation
    def recommend(self, learner_id: str, topics: list[TopicRecord], active_topic: Optional[str] = None) -> Recommendation:
        if not topics:
            return Recommendation(learner_id=learner_id, recommended_action="upload_material", topic_id="", difficulty=Difficulty.easy,
                                  rationale="Upload course material to get personalised recommendations.")
        by_id = {t.topic_id: t for t in topics}
        p = {t.topic_id: self.current(learner_id, t.topic_id) for t in topics}
        seen = {m.topic_id: m for m in self.db.all_mastery(learner_id)}

        def unmet(tid: str) -> list[str]:
            return [x for x in by_id[tid].prerequisites if x in by_id and p[x] < READY]

        # Interleave and avoid dead ends (from intelligent-tutoring practice):
        #  * after 3 questions in a row on one topic, prefer a different one;
        #  * skip topics whose question bank this learner has used up;
        #  * "wheel-spinning": 8+ attempts with mastery still < 0.4 means more of the
        #    same is not working, so step away (to a prerequisite or another topic).
        history = self.db.interactions(learner_id)
        recent = [h["topic_id"] for h in history[-3:]]
        streak_topic = recent[0] if len(recent) == 3 and len(set(recent)) == 1 else None
        answered = {}
        for h in history:
            answered.setdefault(h["topic_id"], set()).add(h["question_id"])
        bank_size = {t.topic_id: len(self.db.questions(learner_id, t.topic_id)) for t in topics}

        def fresh(tid: str) -> bool:
            return bank_size.get(tid, 0) > len(answered.get(tid, ()))

        def spinning(tid: str) -> bool:
            return tid in seen and seen[tid].attempts >= 8 and p[tid] < 0.4

        def usable(ts: list[TopicRecord]) -> list[TopicRecord]:
            good = [t for t in ts if t.topic_id != streak_topic and fresh(t.topic_id) and not spinning(t.topic_id)]
            return good or [t for t in ts if fresh(t.topic_id)] or ts

        misc = self.db.active_misconceptions(learner_id, active_topic) or self.db.active_misconceptions(learner_id)
        misc = [m for m in misc if m.topic_id in by_id]
        # Remediation is skipped while it would only repeat used-up or stalled practice.
        misc = [m for m in misc if (m.remediation_concept_id if m.remediation_concept_id in by_id else m.topic_id) != streak_topic
                and fresh(m.remediation_concept_id if m.remediation_concept_id in by_id else m.topic_id)]
        if misc:
            top = misc[0]
            tid = top.remediation_concept_id if top.remediation_concept_id in by_id else top.topic_id
            return Recommendation(
                learner_id=learner_id, recommended_action="remediate_misconception", topic_id=tid, topic_name=by_id[tid].name,
                concept_id=top.concept_id, difficulty=Difficulty.easy,
                rationale=f"{top.suspected_misconception} ({top.error_count} errors). Review the cited passages, then practise easy questions.",
                learner_state_evidence={"misconception": top.suspected_misconception, "error_count": top.error_count,
                                        "confidence": top.confidence, "p_mastery": p[tid]},
                suggested_evidence_ids=top.remediation_evidence_ids,
            )

        def pack(tid: str, action: str, why: str, extra: Optional[dict] = None) -> Recommendation:
            diff = Difficulty.easy if p[tid] < 0.4 else Difficulty.medium if p[tid] < READY else Difficulty.hard
            ev = [e.evidence_id for e in self.db.evidence_for_topic(tid)[:3]]
            return Recommendation(
                learner_id=learner_id, recommended_action=action, topic_id=tid, topic_name=by_id[tid].name, difficulty=diff,
                rationale=why, learner_state_evidence={"p_mastery": round(p[tid], 3), "attempts": seen[tid].attempts if tid in seen else 0, **(extra or {})},
                suggested_evidence_ids=ev,
            )

        if active_topic and active_topic in by_id:
            blockers = unmet(active_topic)
            if blockers:
                b = min(blockers, key=lambda x: p[x])
                return pack(b, "foundational_review",
                            f"'{by_id[active_topic].name}' builds on '{by_id[b].name}', where your mastery is {p[b]:.2f} (< {READY}). Strengthen it first.",
                            {"blocked_topic": active_topic})

        ordered = sorted(topics, key=lambda t: (t.owner_id == "public", t.source_id or "", t.position))
        ready = [t for t in ordered if not unmet(t.topic_id)]

        started_weak = usable([t for t in ready if t.topic_id in seen and p[t.topic_id] < READY]) if any(
            t.topic_id in seen and p[t.topic_id] < READY for t in ready) else []
        new_ready = [t for t in ready if t.topic_id not in seen]
        if started_weak and new_ready and all(t.topic_id == streak_topic or not fresh(t.topic_id) or spinning(t.topic_id) for t in started_weak):
            t = new_ready[0]
            return pack(t.topic_id, "advance_topic", f"You have practised your current topic a lot in a row. Mixing in '{t.name}' helps both stick.")
        if started_weak:
            t = min(started_weak, key=lambda x: p[x.topic_id])
            act = "foundational_review" if p[t.topic_id] < 0.4 else "targeted_practice"
            return pack(t.topic_id, act, f"Mastery of '{t.name}' is {p[t.topic_id]:.2f}. Practice here gives the largest expected gain.")
        faded = [t for t in ready if t.topic_id in seen and seen[t.topic_id].p_mastery - p[t.topic_id] > 0.15]
        if faded:
            t = max(faded, key=lambda x: seen[x.topic_id].p_mastery - p[x.topic_id])
            return pack(t.topic_id, "spaced_review",
                        f"'{t.name}' has faded from {seen[t.topic_id].p_mastery:.2f} to about {p[t.topic_id]:.2f} since you last practised. A short review now is efficient.")
        mid = usable([t for t in ready if t.topic_id in seen and p[t.topic_id] < MASTERED]) if any(
            t.topic_id in seen and p[t.topic_id] < MASTERED for t in ready) else []
        if mid:
            t = min(mid, key=lambda x: p[x.topic_id])
            return pack(t.topic_id, "mixed_application", f"'{t.name}' is at {p[t.topic_id]:.2f}. Harder, mixed questions will consolidate it.")
        new = [t for t in ready if t.topic_id not in seen]
        if new:
            t = new[0]
            return pack(t.topic_id, "advance_topic", f"Prerequisites are met. Start '{t.name}' next.")
        blocked = [t for t in ordered if unmet(t.topic_id)]
        if blocked:
            b = min((x for t in blocked for x in unmet(t.topic_id)), key=lambda x: p[x])
            return pack(b, "foundational_review", f"Remaining topics depend on '{by_id[b].name}'.")
        t = min(ordered, key=lambda x: p[x.topic_id])
        return pack(t.topic_id, "mixed_application", "All topics are mastered. Mixed practice keeps them fresh.")

    def target_difficulty(self, learner_id: str, topic_id: str) -> Difficulty:
        p = self.current(learner_id, topic_id)
        return Difficulty.easy if p < 0.4 else Difficulty.medium if p < READY else Difficulty.hard

    def select_question(self, learner_id: str, bank: list[Question], difficulty: Optional[Difficulty] = None,
                        exclude: Optional[set[str]] = None) -> Optional[Question]:
        """Unseen first, then matching difficulty, then least-recently answered."""
        if not bank:
            return None
        exclude = exclude or set()
        history = self.db.interactions(learner_id)
        last_seen: dict[str, str] = {}
        for h in history:
            last_seen[h["question_id"]] = h["timestamp"]
        fps_seen = {q.fingerprint for q in bank if q.question_id in last_seen}
        target = difficulty or (self.target_difficulty(learner_id, bank[0].topic_id))
        rank = {Difficulty.easy: 0, Difficulty.medium: 1, Difficulty.hard: 2}

        def key(q: Question):
            unseen = q.question_id not in last_seen and q.fingerprint not in fps_seen
            return (q.question_id in exclude, not unseen, abs(rank[q.difficulty] - rank[target]), last_seen.get(q.question_id, ""), q.question_id)

        return sorted(bank, key=key)[0]
