from __future__ import annotations
import hashlib
from datetime import datetime, timezone
from typing import Any
from .db import EvidenceDB
from .models import MisconceptionSignal

class MisconceptionDetector:
    def __init__(self, db: EvidenceDB, error_threshold: int = 2):
        self.db = db
        self.error_threshold = error_threshold

    def analyze_attempt(
        self,
        learner_id: str,
        topic_id: str,
        concept_id: str | None,
        is_correct: bool,
        error_pattern: str = "wrong_answer"
    ) -> MisconceptionSignal | None:
        eff_concept = concept_id or topic_id

        if is_correct:
            # Clear or decrease error signal on success
            self.db.reset_error_signal(learner_id, topic_id, eff_concept)
            return None

        # Record and increment error signal count
        count = self.db.record_error_signal(learner_id, topic_id, eff_concept, error_pattern)

        # Decision D-016: A single error is an isolated slip, not a misconception
        if count < self.error_threshold:
            return None

        # Threshold reached: diagnose misconception and find prerequisite remediation
        suspected = f"Persistent difficulty with {eff_concept} ({error_pattern})"

        # Find prerequisite concepts for foundational remediation
        prereqs = self.db.get_all_prerequisites(eff_concept)
        remediation_concept = prereqs[0] if prereqs else eff_concept

        # Find supporting evidence units for remediation
        remedial_ev = self.db.get_evidence_for_concept(remediation_concept)
        if not remedial_ev:
            remedial_ev = self.db.get_evidence_for_topic(topic_id)
        if not remedial_ev:
            remedial_ev = list(self.db.all_evidence())[:2]

        remedial_eids = [e.evidence_id for e in remedial_ev[:3]]

        sig_id = f"misc_{learner_id}_{eff_concept}_{hashlib.sha256(error_pattern.encode()).hexdigest()[:8]}"
        signal = MisconceptionSignal(
            signal_id=sig_id,
            learner_id=learner_id,
            topic_id=topic_id,
            concept_id=eff_concept,
            suspected_misconception=suspected,
            error_count=count,
            confidence=min(0.95, 0.70 + 0.10 * (count - 1)),
            remediation_concept_id=remediation_concept,
            remediation_evidence_ids=remedial_eids,
            remediation_note=f"Review prerequisite/core material for '{remediation_concept}' before attempting further assessments.",
            created_at=datetime.now(timezone.utc).isoformat()
        )

        self.db.add_misconception(signal)

        # Update topic mastery record misconception list
        mastery = self.db.get_learner_mastery(learner_id, topic_id)
        if mastery:
            if suspected not in mastery.misconception_signals:
                mastery.misconception_signals.append(suspected)
                self.db.save_learner_mastery(mastery)

        return signal

    def resolve_misconception(self, learner_id: str, topic_id: str, concept_id: str | None = None):
        """
        Clears active misconception signals and resets error counters after successful remediation.
        """
        eff_concept = concept_id or topic_id
        self.db.reset_error_signal(learner_id, topic_id, eff_concept)
        self.db.clear_misconceptions(learner_id, topic_id=topic_id)

    def get_remediation_package(self, signal: MisconceptionSignal) -> dict[str, Any]:
        evidence_items = []
        for eid in signal.remediation_evidence_ids:
            ev = self.db.get_evidence(eid)
            if ev:
                evidence_items.append({
                    "evidence_id": ev.evidence_id,
                    "text": ev.text,
                    "location": ev.location,
                    "modality": ev.modality.value
                })

        return {
            "signal_id": signal.signal_id,
            "learner_id": signal.learner_id,
            "topic_id": signal.topic_id,
            "concept_id": signal.concept_id,
            "suspected_misconception": signal.suspected_misconception,
            "confidence": signal.confidence,
            "remediation_concept_id": signal.remediation_concept_id,
            "remediation_note": signal.remediation_note,
            "evidence_items": evidence_items
        }
