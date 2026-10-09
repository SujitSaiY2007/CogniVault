from __future__ import annotations
import re
from abc import ABC, abstractmethod
from typing import Any
from .db import EvidenceDB
from .models import Citation, Modality, RetrievalResult, RetrievalTrace, SufficiencyResult, TutorResponse
from .retrieval import HybridRetriever
from .source_resolver import resolve
from .sufficiency import EvidenceSufficiencyGate

class BaseTutorProvider(ABC):
    @abstractmethod
    def generate(self, query: str, evidence_items: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Generate a grounded answer dictionary given query and verified evidence items.
        Must return:
        {
            "answer": str,
            "cited_evidence_ids": list[str],
            "reasoning_steps": list[str] (optional)
        }
        """
        pass

class DeterministicTutorProvider(BaseTutorProvider):
    """
    Deterministic offline provider that constructs answers directly from verified evidence units.
    Ensures tests are fast, reproducible, and independent of external API keys.
    """
    def generate(self, query: str, evidence_items: list[dict[str, Any]]) -> dict[str, Any]:
        if not evidence_items:
            raise ValueError("No evidence provided to generator")

        # Collect distinct source IDs to identify cross-source synthesis
        source_ids = list(dict.fromkeys(item.get("source_id", "") for item in evidence_items))
        modalities = list(dict.fromkeys(item.get("modality", "") for item in evidence_items))
        is_synthesis = len(source_ids) > 1 or len(evidence_items) > 1

        texts = []
        cited_ids = []
        reasoning = []

        for idx, item in enumerate(evidence_items, 1):
            eid = item["evidence_id"]
            cited_ids.append(eid)
            raw_text = item.get("text", "").strip()
            loc = item.get("location", {})
            mod = item.get("modality", "text")

            loc_str = ""
            if "page" in loc:
                loc_str = f" [Page {loc['page']}]"
            elif "slide" in loc:
                loc_str = f" [Slide {loc['slide']}]"
            elif "timestamp" in loc:
                loc_str = f" [Timestamp {loc['timestamp']}]"

            if mod == "image":
                texts.append(f"According to visual evidence in {eid}{loc_str}: {raw_text}")
                reasoning.append(f"Referenced visual figure from {eid}{loc_str}")
            elif mod == "video":
                texts.append(f"At {loc.get('timestamp', 'video segment')}, the course video states: {raw_text}")
                reasoning.append(f"Extracted transcript claim from {eid} at {loc.get('timestamp', '')}")
            else:
                texts.append(f"{raw_text}")
                reasoning.append(f"Extracted conceptual statement from {eid}{loc_str}")

        if is_synthesis:
            intro = "Synthesizing information across course sources: "
            answer = intro + " ".join(texts)
        else:
            answer = " ".join(texts)

        return {
            "answer": answer,
            "cited_evidence_ids": cited_ids,
            "reasoning_steps": reasoning,
            "is_synthesis": is_synthesis,
        }

class GroundedTutor:
    def __init__(
        self,
        db: EvidenceDB,
        retriever: HybridRetriever | None = None,
        sufficiency_gate: EvidenceSufficiencyGate | None = None,
        provider: BaseTutorProvider | None = None,
    ):
        self.db = db
        self.retriever = retriever or HybridRetriever(db)
        self.sufficiency_gate = sufficiency_gate or EvidenceSufficiencyGate()
        self.provider = provider or DeterministicTutorProvider()

    def answer(
        self,
        query: str,
        k: int = 5,
        mode: str = "hybrid",
        forced_unsupported: bool = False
    ) -> TutorResponse:
        # Check fail-closed condition or empty query
        if forced_unsupported or not query or not query.strip():
            return TutorResponse(
                query=query,
                answer="I cannot answer this question because it is not supported by the supplied course material.",
                citations=[],
                is_grounded=False,
                is_synthesis=False,
                confidence=0.0,
                support_status="unsupported",
                reasoning_steps=[],
                unsupported_reason="empty query or forced unsupported state",
                metadata={"abstention": True}
            )

        # 1. Retrieval
        try:
            results, trace = self.retriever.search(query, k=k, mode=mode)
        except Exception as e:
            return TutorResponse(
                query=query,
                answer="Retrieval failed. Cannot generate a verified course-grounded answer.",
                citations=[],
                is_grounded=False,
                is_synthesis=False,
                confidence=0.0,
                support_status="error",
                reasoning_steps=[],
                unsupported_reason=f"retrieval error: {str(e)}",
                metadata={"error": True}
            )

        # 2. Sufficiency Gate
        suff = self.sufficiency_gate.evaluate(query, results, trace=trace, db=self.db)
        if not suff.is_sufficient:
            return TutorResponse(
                query=query,
                answer="I cannot answer this question because the supplied course material does not contain sufficient supporting evidence.",
                citations=[],
                is_grounded=False,
                is_synthesis=False,
                confidence=suff.confidence,
                support_status="unsupported",
                reasoning_steps=[],
                unsupported_reason=suff.reason or "insufficient evidence",
                metadata={"abstention": True}
            )

        # 3. Resolve Provenance for Supporting Evidence
        evidence_items: list[dict[str, Any]] = []
        citations: list[Citation] = []

        for eid in suff.supporting_evidence_ids:
            resolved = resolve(eid, self.db)
            if resolved:
                evidence_items.append(resolved)
                modality_val = resolved.get("modality", "text")
                try:
                    mod_enum = Modality(modality_val)
                except ValueError:
                    mod_enum = Modality.text

                citations.append(
                    Citation(
                        evidence_id=eid,
                        source_id=resolved.get("source_id", ""),
                        modality=mod_enum,
                        location=resolved.get("location", {}),
                        snippet=resolved.get("text", "")[:300],
                        source_path=resolved.get("source_path"),
                        source_title=resolved.get("source_title")
                    )
                )

        if not evidence_items:
            return TutorResponse(
                query=query,
                answer="Failed to resolve source citations for retrieved evidence.",
                citations=[],
                is_grounded=False,
                is_synthesis=False,
                confidence=0.0,
                support_status="error",
                unsupported_reason="citation resolution failure",
                metadata={"error": True}
            )

        # 4. Generation via Provider
        try:
            gen_out = self.provider.generate(query, evidence_items)
        except Exception as e:
            # Fail closed on provider error
            return TutorResponse(
                query=query,
                answer="Generation service error. Grounded answer withheld to prevent hallucination.",
                citations=[],
                is_grounded=False,
                is_synthesis=False,
                confidence=0.0,
                support_status="error",
                unsupported_reason=f"provider generation failure: {str(e)}",
                metadata={"error": True}
            )

        answer_text = gen_out.get("answer", "")
        cited_eids = set(gen_out.get("cited_evidence_ids", [c.evidence_id for c in citations]))
        filtered_citations = [c for c in citations if c.evidence_id in cited_eids]
        if not filtered_citations:
            filtered_citations = citations

        is_synthesis = gen_out.get("is_synthesis", len({c.source_id for c in filtered_citations}) > 1)
        reasoning = gen_out.get("reasoning_steps", [])

        return TutorResponse(
            query=query,
            answer=answer_text,
            citations=filtered_citations,
            is_grounded=True,
            is_synthesis=is_synthesis,
            confidence=suff.confidence,
            support_status="supported",
            reasoning_steps=reasoning,
            unsupported_reason=None,
            metadata={"evidence_count": len(filtered_citations)}
        )
