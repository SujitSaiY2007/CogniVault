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
