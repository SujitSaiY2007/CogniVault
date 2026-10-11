# CogniVault — Evidence-First Adaptive Learning

**Hackathon:** Multimodal AI Hackathon 2026 · Track D — Personalized Tutoring & Adaptive Learning  
**Plan date:** 2026-10-11  
**Plan status:** Locked; implementation not yet verified.

## Start here

The authoritative final plan, architecture, acceptance gates and the only three executor prompts are in [docs/FINAL_OVERHAUL_PLAN.md](docs/FINAL_OVERHAUL_PLAN.md).

## Final planned stack

- Frontend: v0-generated Next.js + TypeScript + Tailwind CSS.
- Agent runtime: Python + Agno AgentOS with bounded workflows and three specialist responsibilities.
- Local model baseline: Ollama; any hosted free-tier provider is optional, quota-limited and not required.
- Data/retrieval: SQLite + FTS5 + local ChromaDB + local embeddings.
- Trust/adaptation: deterministic source/citation/assessment verification and preserved BKT learner model.
- Testing: pytest, API/integration checks, frontend checks and real browser walkthrough.

## Product goal

Deliver a source-grounded study companion that ingests learning materials, cites exact pages/slides/timestamps, abstains on unsupported questions, verifies assessments, tracks topic mastery and adapts the next learning action.

## Historical preservation

This is a continuation, not a replacement project. Preserve the Streamlit implementation, all useful code, tests, data, user-provided PDFs, reports, prior-art notes, commits, branches and PR #1. Streamlit remains a legacy path until the new system passes acceptance. Do not force-push, reset, delete/rename branches, close/merge PR #1, change visibility or merge implementation to main without explicit approval.

## Exactly three implementation chats

1. Agno evidence foundation and local API.
2. v0/Next.js frontend and complete adaptive learning loop.
3. Evaluation, hardening, demo and submission package.

## Truthful status

The organizer requirements informed the final plan. The new Agno/Next.js architecture has not yet passed its own tests or full browser walkthrough. Metrics, public deployment, video recording and portal submission are not claimed complete. Free frontend hosting does not automatically host the backend; Ollama is the baseline for avoiding paid API calls.

## Legacy launch

The existing Streamlit app remains available while preserved: python -m streamlit run app/ui/main.py.
