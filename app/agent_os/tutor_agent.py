"""
Grounded Agno Evidence Tutor Agent.
Enforces deterministic sufficiency gating, exact source locators, and citation verification.
"""
from __future__ import annotations

import os
import re
import unicodedata
from typing import Optional

try:
    from agno.agent import Agent
except ImportError:
    Agent = None

from ..models import Citation, Modality, TutorResponse
from ..model_provider import (
    create_active_model,
    create_ollama_model,
    get_active_provider_name,
    is_gemini_available,
    is_ollama_available,
)
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

        # Initialize Agno Agent if agno is installed and model provider is reachable
        self.agno_agent: Optional[Agent] = None
        if Agent is not None:
            # Only connect model agent if a live provider is detected
            if is_gemini_available() or is_ollama_available(self.host):
                model = create_active_model(self.model_id)
                if model is not None:
                    self.agno_agent = Agent(
                        name="CogniVault Evidence Tutor",
                        description="Course-grounded tutor with exact locators and fail-closed abstention",
                        instructions=TUTOR_SYSTEM_PROMPT,
                        tools=self.tools_handler.get_tool_list(),
                        model=model,
                        markdown=True,
                    )

    def _synthesize_grounded_answer(
        self,
        query: str,
        citations: list[Citation],
        cited_evidence_ids: list[str],
    ) -> str:
        """
        Synthesizes a clean, plain-language, direct answer grounded in the cited course evidence.
        Extracts the most relevant definitions, explanations, formulas, and bullet points.
        """
        if not citations:
            return "Based on your course materials, no direct evidence was located."

        # Tokenize query for relevance scoring
        stop_words = {
            "what", "is", "the", "of", "in", "and", "to", "a", "an", "for", "are", "by",
            "that", "with", "on", "at", "from", "as", "it", "be", "this", "how", "explain",
            "tell", "me", "about", "define", "does", "do", "can", "could", "would", "which",
            "why", "when", "where", "who", "all", "any", "state", "give"
        }
        query_words = [
            w.lower()
            for w in re.findall(r"\w+", query)
            if w.lower() not in stop_words and len(w) > 2
        ]

        scored_candidates = []

        for citation in citations:
            unit = self.db.get_evidence(citation.evidence_id)
            if not unit or not unit.text:
                continue

            loc_name = citation.location.get("locator") or (
                f"Page {citation.location.get('page')}"
                if citation.location.get("page")
                else "Course Material"
            )
            title = citation.source_title or "Course Material"

            # Normalize text to remove unicode ligature anomalies
            norm_text = unicodedata.normalize("NFKD", unit.text)
            raw_lines = [line.strip() for line in norm_text.split("\n") if line.strip()]

            # Group lines into semantic blocks (split on numbered items, bullet points, or section titles)
            blocks = []
            curr_block = []
            for line in raw_lines:
                if re.match(r"^(\d+[\.\)]|[A-Z][a-zA-Z\s]{2,}:|\-\s|\*\s)", line) and curr_block:
                    blocks.append(curr_block)
                    curr_block = [line]
                else:
                    curr_block.append(line)
            if curr_block:
                blocks.append(curr_block)

            for block in blocks:
                block_text = "\n".join(block)
                block_lower = block_text.lower()

                # Relevance score based on query keywords
                matched_tokens = [w for w in set(query_words) if w in block_lower]
                score = len(matched_tokens) * 3

                # Boost if header contains query terms
                first_line = block[0].lower()
                if any(w in first_line for w in query_words):
                    score += 5

                # Boost for definitional phrases
                if any(p in block_lower for p in ["states that", "defined as", "given by", "formula", "law", "equation", "where"]):
                    score += 1

                scored_candidates.append({
                    "score": score,
                    "matched_count": len(matched_tokens),
                    "title": title,
                    "loc": loc_name,
                    "block": block,
                    "citation": citation,
                })

        # Sort candidate blocks by score descending
        scored_candidates.sort(key=lambda x: (x["score"], x["matched_count"]), reverse=True)

        # If we have a strong match (at least 1 matching keyword)
        if scored_candidates and scored_candidates[0]["score"] > 0:
            best = scored_candidates[0]
            lines = best["block"]

            # Format the primary answer clearly
            formatted_lines = []
            for i, line in enumerate(lines):
                if i == 0:
                    clean_header = re.sub(r"^\d+[\.\)]\s*", "", line).rstrip(":")
                    formatted_lines.append(f"**{clean_header}:**")
                elif line.lower().startswith("where "):
                    formatted_lines.append(f"\n{line}")
                elif line.startswith("-") or line.startswith("*"):
                    formatted_lines.append(f"• {line.lstrip('-*').strip()}")
                else:
                    formatted_lines.append(line)

            primary_body = "\n".join(formatted_lines)
            answer = f"According to your course material in **{best['title']} ({best['loc']})**:\n\n{primary_body}"

            # Check if there's a complementary secondary point matching substantial query tokens
            secondary = None
            for cand in scored_candidates[1:]:
                if (
                    cand["score"] >= 6
                    and cand["matched_count"] >= 2
                    and cand["title"] != best["title"]
                    and cand["matched_count"] >= max(2, int(best["matched_count"] * 0.6))
                ):
                    secondary = cand
                    break

            if secondary:
                sec_header = re.sub(r"^\d+[\.\)]\s*", "", secondary["block"][0]).rstrip(":")
                sec_body = "\n".join(secondary["block"][1:] if len(secondary["block"]) > 1 else secondary["block"])
                answer += f"\n\n**Additional Context from {secondary['title']} ({secondary['loc']}):**\n{sec_header}\n{sec_body}"

            return answer

        # Fallback if no specific keyword scored high: clean excerpt from primary citation
        first_citation = citations[0]
        first_unit = self.db.get_evidence(first_citation.evidence_id)
        loc_name = first_citation.location.get("locator") or (
            f"Page {first_citation.location.get('page')}"
            if first_citation.location.get("page")
            else "Course Material"
        )
        first_text = first_unit.text.strip() if first_unit else "Refer to the verified course citations."
        return f"Based on your course materials in **{first_citation.source_title} ({loc_name})**:\n\n{first_text}"

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
        # Try Agno Agent if model is available
        if self.agno_agent and getattr(self.agno_agent, "model", None) is not None:
            try:
                prompt = (
                    f"Question: {query}\n\n"
                    f"Supported Course Evidence:\n{context_block}\n\n"
                    f"Explain the answer clearly to the student in simple plain language, citing the locations above."
                )
                run_res = self.agno_agent.run(prompt)
                if hasattr(run_res, "content") and run_res.content:
                    raw_content = str(run_res.content).strip()
                    # Filter out model provider connection error messages
                    err_keywords = [
                        "failed to connect to ollama",
                        "check that ollama is downloaded",
                        "connection refused",
                        "cannot connect",
                        "error communicating",
                        "httperror",
                        "rate limit",
                    ]
                    if not any(k in raw_content.lower() for k in err_keywords):
                        answer_text = raw_content
            except Exception:
                answer_text = ""

        # Grounded explanation synthesis from retrieved course evidence
        if not answer_text:
            answer_text = self._synthesize_grounded_answer(query, citations, cited_evidence_ids)

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
