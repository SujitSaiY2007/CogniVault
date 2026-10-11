# Current Objective — Chat 05 Dashboard Stage 1

**State:** Antigravity implementation request already issued; response pending.  
**Next chat:** Chat 06 — Reconcile AG response and finish dashboard acceptance.

## Objective
Implement a clean, professional Home Dashboard matching the user's screenshot supplied on 2026-10-10. The screenshot, not the rejected first overhaul, is the primary visual reference.

## Requirements
- Preserve warm off-white/white/navy/indigo/teal palette.
- Minimal unnumbered left sidebar.
- Header with global tutor question field, help, guest/registered status, truthful usage indicator, Login and Sign Up.
- Welcome hero, Resume Learning, Continue Learning, Recent History, Recommended Next Step, Quick Actions, profile/onboarding banner.
- Remove raw HTML leakage, one-letter-wrapped headings, tiny text, poor proportions, excess whitespace and unnecessary technical KPI cards.
- Use real data and truthful empty states.
- Do not present BKT posterior probability as course completion.
- Guest history remains session-only.
- Preserve all backend contracts, persistence, assessment, retrieval, citations, learner model, recommendation and evaluation logic.

## Do not do in this stage
Do not redesign other pages, rewrite backend, add authentication, change schemas, implement cloud hosting/billing/quotas, or create fake data.

## First action in Chat 06
Ask for the pending AG response and screenshot if not already received. Verify actual branch/diff before issuing any new prompt.

## Exit criteria
Dashboard rendered at normal browser zoom, no raw HTML leakage or layout defects, relevant/full tests reported accurately, browser status disclosed, screenshot presented, and user explicitly approves it before the next page begins.


---

## Final overhaul decision — 2026-10-11

The authoritative next-phase plan is now [`docs/FINAL_OVERHAUL_PLAN.md`](FINAL_OVERHAUL_PLAN.md). This section supersedes earlier forward-looking implementation instructions where they conflict; prior entries remain preserved as history.

**Current direction:** controlled Agno-first overhaul with v0-generated Next.js/TypeScript frontend, Python Agno AgentOS backend, Ollama/local model baseline, SQLite + FTS5 + local ChromaDB, local embeddings, deterministic evidence/assessment verification, and existing BKT logic. See the final plan for exact decisions, acceptance gates, branch rules, and the only three executor prompts.

**Execution model:** exactly three implementation chats: (1) Agno/evidence foundation, (2) frontend and adaptive learning loop, (3) evaluation, hardening and submission. Implementation must proceed on dedicated phase branches; preserve all legacy Streamlit code, source data, tests, PDFs, and Git history. Do not force-push, reset, delete/rename branches, close/merge PR #1, change visibility, or merge implementation to main without explicit approval.

**Truthfulness gate:** the plan is locked; implementation and acceptance are not yet proven. Organizer requirements are the acceptance baseline. Never claim a requirement, test, metric, deployment, video or submission is complete without reproducible evidence.
