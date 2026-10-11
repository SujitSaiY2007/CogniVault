# CogniVault — Current Project Reference

**Track:** D — Personalized Tutoring & Adaptive Learning  
**Reconciled:** 2026-10-10  
**Current phase:** Chat 05 screenshot-guided dashboard redesign; Antigravity response pending.

> **Repository truth:** `main` was at `0dd3acd0f973f7afcf8dada234f844ee5095b19a` before this documentation-only synchronization and contains the original scaffold/control files. Application implementation is on separate Chat 01–05 branches. This update does not merge implementation code into main.

## Product
CogniVault connects multimodal course-material ingestion and source-addressable evidence with grounded tutoring, explicit abstention, verified assessments, learner-state updates, recommendations and reproducible evaluation.

## Phase state
| Phase | Reported state | Current caveat |
|---|---|---|
| Chat 01 — Evidence foundation | Branch exists | PR #1 remains open/draft |
| Chat 02 — Intelligence core | Reported complete | Separate phase branch |
| Chat 03 — Product/evaluation | Reported complete | Separate phase branch |
| Chat 04 — Acceptance checkpoint | Reported 102 tests passed | Browser visual acceptance not established |
| Chat 05 — Initial UI overhaul | Reported pushed | Screenshots revealed significant UI defects |
| Chat 05 — Dashboard Stage 1 | AG task issued; response pending | Do not duplicate task |
| Browser acceptance | Pending | Playwright driver download failed in prior attempt |
| Demo recording/submission | Not confirmed | Still pending |
| Public free hosting/persistent storage/auth | Not verified | Separate future deployment work |

## Current UI decisions
- Preserve warm off-white, white, navy, indigo, teal and subtle-gray palette.
- Minimal unnumbered sidebar and screenshot-guided dashboard.
- Dashboard first; user approval required before redesigning other screens.
- Dashboard includes global tutor question field, account/guest and truthful usage state, welcome hero, Resume/Continue Learning, Recent History, Recommended Next Step, Quick Actions and onboarding.
- Fix raw HTML leakage, tiny text, one-letter heading wraps, excessive whitespace and technical clutter.
- Use real data and honest empty states. Never fabricate progress, history, quotas, or recommendations.
- Do not equate BKT probability with course completion.
- Guest history is session-only.

## Branch and file policy
Preserve main, PR #1 and all phase branches. No force-push, reset, deletion, rename or merge without explicit authorization. The four root PDFs supplied by the user are immutable references: do not edit, move, rename or delete them.

## Start here
Read `PROJECT_STATE.md`, `CURRENT_OBJECTIVE.md`, `CURRENT_HANDOFF.md`, `NEXT_CHAT_PROMPT.md`, `docs/continuity/CHAT_HISTORY.md`, `docs/continuity/FILE_OWNERSHIP.md`, and `docs/CHAT05_UI_OVERHAUL_REPORT.md`.

Reported test results are not independently rerun by this documentation commit. No demo recording or portal submission is marked complete without evidence.


---

## Final overhaul decision — 2026-10-11

The authoritative next-phase plan is now [`docs/FINAL_OVERHAUL_PLAN.md`](FINAL_OVERHAUL_PLAN.md). This section supersedes earlier forward-looking implementation instructions where they conflict; prior entries remain preserved as history.

**Current direction:** controlled Agno-first overhaul with v0-generated Next.js/TypeScript frontend, Python Agno AgentOS backend, Ollama/local model baseline, SQLite + FTS5 + local ChromaDB, local embeddings, deterministic evidence/assessment verification, and existing BKT logic. See the final plan for exact decisions, acceptance gates, branch rules, and the only three executor prompts.

**Execution model:** exactly three implementation chats: (1) Agno/evidence foundation, (2) frontend and adaptive learning loop, (3) evaluation, hardening and submission. Implementation must proceed on dedicated phase branches; preserve all legacy Streamlit code, source data, tests, PDFs, and Git history. Do not force-push, reset, delete/rename branches, close/merge PR #1, change visibility, or merge implementation to main without explicit approval.

**Truthfulness gate:** the plan is locked; implementation and acceptance are not yet proven. Organizer requirements are the acceptance baseline. Never claim a requirement, test, metric, deployment, video or submission is complete without reproducible evidence.
