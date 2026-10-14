from __future__ import annotations
import re
from .db import EvidenceDB
from .models import RetrievalResult, RetrievalTrace, SufficiencyResult

STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "when", "at",
    "by", "for", "with", "about", "against", "between", "into", "through", "during",
    "before", "after", "above", "below", "to", "from", "up", "down", "in", "out",
    "on", "off", "over", "under", "again", "further", "then", "once", "here", "there",
    "all", "any", "both", "each", "few", "more", "most", "other", "some", "such",
    "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very",
    "s", "t", "can", "will", "just", "don", "should", "now", "what", "which",
    "who", "whom", "this", "that", "these", "those", "am", "is", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "having", "do", "does",
    "did", "doing", "how", "why", "where", "explain", "describe", "define", "give", "tell"
}

def _extract_keywords(text: str) -> set[str]:
    tokens = re.findall(r"[A-Za-z0-9_]+", text.lower())
    return {t for t in tokens if len(t) > 1 and t not in STOP_WORDS}

class EvidenceSufficiencyGate:
    def __init__(
        self,
        min_score: float = 0.15,
        min_term_coverage: float = 0.25,
        require_addressable_source: bool = True
    ):
        self.min_score = min_score
        self.min_term_coverage = min_term_coverage
        self.require_addressable_source = require_addressable_source

    def evaluate(
        self,
        query: str,
        results: list[RetrievalResult],
        trace: RetrievalTrace | None = None,
        db: EvidenceDB | None = None
    ) -> SufficiencyResult:
        if not query or not query.strip():
            return SufficiencyResult(
                query=query,
                is_sufficient=False,
                reason="empty query",
                confidence=0.0,
                supporting_evidence_ids=[],
                evidence_count=0
            )

        if trace is not None and trace.unsupported:
            return SufficiencyResult(
                query=query,
                is_sufficient=False,
                reason=trace.reason or "retrieval trace marked as unsupported",
                confidence=0.0,
                supporting_evidence_ids=[],
                evidence_count=0
            )

        if not results:
            return SufficiencyResult(
                query=query,
                is_sufficient=False,
                reason="no matching evidence found in course material",
                confidence=0.0,
                supporting_evidence_ids=[],
                evidence_count=0
            )

        # Filter by minimum relevance score
        passing = [r for r in results if r.score >= self.min_score]
        if not passing:
            return SufficiencyResult(
                query=query,
                is_sufficient=False,
                reason="retrieved evidence confidence below sufficiency threshold",
                confidence=round(results[0].score, 4) if results else 0.0,
                supporting_evidence_ids=[],
                evidence_count=len(results)
            )

        # Keyword coverage check
        q_keywords = _extract_keywords(query)
        if q_keywords:
            combined_text = " ".join(r.snippet.lower() for r in passing)
            ev_tokens = set(re.findall(r"[A-Za-z0-9_]+", combined_text))
            covered = q_keywords & ev_tokens
            coverage = len(covered) / len(q_keywords)
            if coverage < self.min_term_coverage:
                return SufficiencyResult(
                    query=query,
                    is_sufficient=False,
                    reason=f"insufficient topic coverage in retrieved evidence ({len(covered)}/{len(q_keywords)} key terms found)",
                    confidence=round(coverage, 4),
                    supporting_evidence_ids=[],
                    evidence_count=len(passing)
                )

        # Addressability check with DB if provided
        verified_ids: list[str] = []
        if db is not None and self.require_addressable_source:
            for r in passing:
                ev = db.get_evidence(r.evidence_id)
                if ev is not None:
                    src = db.get_source(ev.source_id)
                    if src is not None:
                        verified_ids.append(r.evidence_id)
            if not verified_ids:
                return SufficiencyResult(
                    query=query,
                    is_sufficient=False,
                    reason="retrieved evidence could not be resolved to valid source records",
                    confidence=0.0,
                    supporting_evidence_ids=[],
                    evidence_count=0
                )
        else:
            verified_ids = [r.evidence_id for r in passing]

        top_confidence = round(max(r.score for r in passing), 4) if passing else 1.0

        return SufficiencyResult(
            query=query,
            is_sufficient=True,
            reason=None,
            confidence=top_confidence,
            supporting_evidence_ids=verified_ids,
            evidence_count=len(verified_ids)
        )

def check_sufficiency(
    query: str,
    results: list[RetrievalResult],
    trace: RetrievalTrace | None = None,
    db: EvidenceDB | None = None,
    min_score: float = 0.15,
    min_term_coverage: float = 0.25
) -> SufficiencyResult:
    gate = EvidenceSufficiencyGate(min_score=min_score, min_term_coverage=min_term_coverage)
    return gate.evaluate(query, results, trace=trace, db=db)


EvidenceGate = EvidenceSufficiencyGate

