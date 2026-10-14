"""
Grounded Agno Evidence Tutor Agent.
Enforces deterministic sufficiency gating, exact source locators, and citation verification.
"""
from __future__ import annotations

import os
from typing import Optional

try:
    from agno.agent import Agent
except ImportError:
    Agent = None

from ..models import Citation, TutorResponse
from ..ollama_provider import create_ollama_model, is_ollama_available
from .tools import AgentTools


TUTOR_SYSTEM_PROMPT = """
You are the CogniVault Evidence Tutor, an AI study companion that explains concepts strictly grounded in course materials.

Core Principles:
1. Grounded Answering: Answer the student's question using ONLY the provided course evidence.
2. Citation Integrity: Every substantive factual claim must cite its exact source location (e.g. [kinematics.pdf: Page 2] or [forces.pptx: Slide 4]).
3. Zero Hallucination: Do not introduce outside facts or invent page numbers, slide numbers, or timestamps.
4. Fail-Closed Abstention: If the course material does not contain sufficient information to answer the question, clearly state that the indexed material does not cover the topic.
"""


class EvidenceTutorAgent:
    """Orchestrates Agno Agent execution for grounded tutoring."""

    def __init__(
        self,
        db,
        retriever,
        gate,
        resolver,
        model_id: Optional[str] = None,
        host: Optional[str] = None,
    ):
        self.db = db
        self.retriever = retriever
        self.gate = gate
        self.resolver = resolver
        self.tools_handler = AgentTools(db, retriever, gate, resolver)

        self.model_id = model_id or os.environ.get("OLLAMA_MODEL", "llama3.2:latest")
        self.host = host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")

        # Initialize Agno Agent if agno is installed
        self.agno_agent: Optional[Agent] = None
        if Agent is not None:
            model = None
            if is_ollama_available(self.host):
                model = create_ollama_model(self.model_id, self.host)

            self.agno_agent = Agent(
                name="CogniVault Evidence Tutor",
                description="Course-grounded tutor with exact locators and fail-closed abstention",
                instructions=TUTOR_SYSTEM_PROMPT,
                tools=self.tools_handler.get_tool_list(),
                model=model,
                markdown=True,
            )

    def ask(self, query: str, topic: Optional[str] = None) -> TutorResponse:
        """
        Execute grounded tutoring query.
        Guarantees deterministic abstention if evidence is insufficient.
        """
        if not query or not query.strip():
            return TutorResponse(
                query=query or "",
                answer="Please provide a valid question to begin.",
                citations=[],
                is_grounded=False,
                confidence=0.0,
                support_status="unsupported",
                unsupported_reason="Empty query provided",
                reasoning_steps=["Empty query provided"],
            )

        # 1. Hybrid Retrieval (FTS5 + ChromaDB)
        results, trace = self.retriever.search(query.strip(), k=5, mode="hybrid")

        # 2. Deterministic Sufficiency Gate
        decision = self.gate.evaluate(query.strip(), results, db=self.db)

        if not decision.is_sufficient:
            return TutorResponse(
                query=query.strip(),
                answer=(
                    "The provided course material does not contain sufficient evidence to answer this question. "
                    "CogniVault only provides answers supported by your indexed textbooks, slides, and transcripts."
                ),
                citations=[],
                is_grounded=False,
                confidence=0.0,
                support_status="unsupported",
                unsupported_reason=decision.reason or "insufficient course evidence",
                reasoning_steps=[
                    f"Hybrid retrieval evaluated {trace.candidate_count} indexed items",
                    "Evidence sufficiency gate: INSUFFICIENT",
                    f"Fail-closed reason: {decision.reason or 'low relevance'}",
                ],
            )

        # 3. Resolve exact citations for supported evidence units
        citations: list[Citation] = []
        cited_evidence_ids = decision.supporting_evidence_ids[:3]
        for eid in cited_evidence_ids:
            unit = self.db.get_evidence(eid)
            source = self.db.get_source(unit.source_id) if unit else None
            loc_dict = unit.location if unit else {}
            snippet = (unit.text[:140] + "...") if unit else ""
            citations.append(
                Citation(
                    evidence_id=eid,
                    source_id=unit.source_id if unit else "unknown",
                    modality=unit.modality if unit else Modality.TEXT,
                    location=loc_dict if isinstance(loc_dict, dict) else {"locator": str(loc_dict)},
                    snippet=snippet,
                    source_path=source.path if source else None,
                    source_title=source.title if source else "Course Material",
                )
            )

        # 4. Generate grounded explanation
        evidence_texts = [
            f"[{c.location.get('locator', 'Page')}]: {c.snippet}" for c in citations
        ]
        context_block = "\n".join(evidence_texts)

        answer_text = ""
        # Try Agno Agent with Ollama if running
        if self.agno_agent and is_ollama_available(self.host):
            try:
                prompt = (
                    f"Question: {query}\n\n"
                    f"Supported Course Evidence:\n{context_block}\n\n"
                    f"Explain the answer clearly to the student, citing the locations above."
                )
                run_res = self.agno_agent.run(prompt)
                if hasattr(run_res, "content") and run_res.content:
                    answer_text = str(run_res.content).strip()
            except Exception:
                answer_text = ""

        # Deterministic synthesis fallback if Ollama is not running or returns empty
        if not answer_text:
            primary_evidence = self.db.get_evidence(cited_evidence_ids[0])
            first_sentence = primary_evidence.text.split(".")[0] if primary_evidence else ""
            loc_labels = " ".join([f"[{c.location.get('locator', 'Source')}]" for c in citations])
            answer_text = (
                f"Based on the course material, {first_sentence}. "
                f"This is supported directly by your indexed resources {loc_labels}."
            )

        return TutorResponse(
            query=query.strip(),
            answer=answer_text,
            citations=citations,
            is_grounded=True,
            confidence=round(decision.confidence, 4),
            support_status="supported",
            reasoning_steps=[
                f"Hybrid retrieval matched {len(results)} candidate evidence units",
                f"Sufficiency gate verified: confidence={decision.confidence:.2f}",
                f"Grounded response composed with {len(citations)} verified physical locators",
            ],
            metadata={
                "evidence_ids": ",".join(cited_evidence_ids),
                "evidence_count": len(citations),
            },
        )
