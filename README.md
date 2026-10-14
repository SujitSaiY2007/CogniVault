# CogniVault — Evidence-First Adaptive Learning

**Hackathon:** Multimodal AI Hackathon 2026 · Track D — Personalized Tutoring & Adaptive Learning  
**Plan date:** 2026-10-11  
**Current status:** Chat 01–03 implementation is reported complete on its phase branch. Final integration into `main` and live ingestion/browser acceptance remain outstanding. See [Current Handoff](CURRENT_HANDOFF.md).

## Start here

The authoritative plan is [docs/FINAL_OVERHAUL_PLAN.md](docs/FINAL_OVERHAUL_PLAN.md). The final integration and verification prompt is [docs/CHAT04_FINAL_VERIFICATION_PROMPT.md](docs/CHAT04_FINAL_VERIFICATION_PROMPT.md).

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

The Chat 03 report records 138/138 Python tests, a successful Next.js build, benchmark metrics, learner simulations, security tests and 13 Playwright screenshots. Treat these as reported until the final chat reruns them. The user's local homepage rendered, but a live ingestion attempt remained at “Ingesting…” with zero sources; the upload request outcome is not yet known. Do not claim final acceptance, video recording or portal submission complete. Free frontend hosting does not automatically host the backend; Ollama is the baseline for avoiding paid API calls.

## Legacy launch

The existing Streamlit app remains available while preserved: python -m streamlit run app/ui/main.py.


## Current integration status

The implementation branch is [`overhaul/chat-03-evaluation-submission`](https://github.com/SujitSaiY2007/CogniVault/tree/overhaul/chat-03-evaluation-submission). Integration PR [#2](https://github.com/SujitSaiY2007/CogniVault/pull/2) was opened, but GitHub initially reported it not mergeable because `main` and the implementation branch diverged. Do not assume this default branch already contains the final application. The final chat must inspect conflicts and integrate safely before calling `main` presentation-ready.

## Next steps

1. Run [the final verification prompt](docs/CHAT04_FINAL_VERIFICATION_PROMPT.md) in the next ChatGPT chat with Antigravity executing local work.
2. Safely integrate the phase implementation and resolve the real ingestion stall.
3. Rerun tests/build and conduct the full live walkthrough.
4. Record the 3–5 minute demo, upload it to YouTube (Unlisted) or Google Drive, and submit the repository/video links to the hackathon portal.
