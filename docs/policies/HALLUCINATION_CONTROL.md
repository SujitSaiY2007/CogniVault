# Grounding, Citation Integrity, and Abstention

## Contract
In grounded mode, responses must be supported by retrieved, addressable course evidence. Insufficient/unresolvable evidence must lead to abstention or an explicit error.

## Sequence
Retrieve → assess relevance/sufficiency → resolve stored evidence IDs → generate within grounded contract → verify as implemented → display answer and citations distinctly.

## Fail-closed cases
No relevant evidence; insufficient support; missing citation mapping; unresolved conflict; verification failure; retrieval/provider failure.

## Citation rule
Page, slide, timestamp, figure and source IDs must come from stored metadata. Never invent locators or cite a source merely because it ranks highly.

## Honest claim
The project does not guarantee zero hallucinations. It implements or intends evidence-first controls designed to reject/flag unsupported responses; claims must match measured test scope.

## UI
Clearly distinguish grounded answers, citations, abstentions and service errors. The dashboard redesign must not change the backend grounding policy.


---

## Final overhaul decision — 2026-10-11

The authoritative next-phase plan is now [`docs/FINAL_OVERHAUL_PLAN.md`](FINAL_OVERHAUL_PLAN.md). This section supersedes earlier forward-looking implementation instructions where they conflict; prior entries remain preserved as history.

**Current direction:** controlled Agno-first overhaul with v0-generated Next.js/TypeScript frontend, Python Agno AgentOS backend, Ollama/local model baseline, SQLite + FTS5 + local ChromaDB, local embeddings, deterministic evidence/assessment verification, and existing BKT logic. See the final plan for exact decisions, acceptance gates, branch rules, and the only three executor prompts.

**Execution model:** exactly three implementation chats: (1) Agno/evidence foundation, (2) frontend and adaptive learning loop, (3) evaluation, hardening and submission. Implementation must proceed on dedicated phase branches; preserve all legacy Streamlit code, source data, tests, PDFs, and Git history. Do not force-push, reset, delete/rename branches, close/merge PR #1, change visibility, or merge implementation to main without explicit approval.

**Truthfulness gate:** the plan is locked; implementation and acceptance are not yet proven. Organizer requirements are the acceptance baseline. Never claim a requirement, test, metric, deployment, video or submission is complete without reproducible evidence.
