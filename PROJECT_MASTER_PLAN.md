# CogniVault — Project Master Plan (Current)

**Track:** D — Personalized Tutoring & Adaptive Learning  
**Current phase:** Chat 05 dashboard redesign; AG response pending.

## Product goal
Deliver a demonstrable course-grounded learning loop: multimodal source ingestion → addressable evidence → grounded tutor/abstention → verified assessment → learner-state update → explainable next action → reproducible evaluation.

## Phase history
| Chat | Scope | Recorded state |
|---|---|---|
| Chat 0 | Requirements and technical lock | Historical specification; old next-step wording superseded |
| Chat 01 | Evidence foundation/provenance/retrieval | Phase branch exists; PR #1 open/draft |
| Chat 02 | Tutor grounding, abstention, assessment, BKT, misconception and recommendation | Reported complete on branch |
| Chat 03 | Product workflows and evaluation | Reported complete on branch |
| Chat 04 | Final acceptance checkpoint | Reported 102 tests passing |
| Chat 05 | Initial UI overhaul and controlled redesign | Initial UI rejected; dashboard Stage 1 task pending AG response |
| Chat 06 | Reconcile pending AG output and accept dashboard | Next chat |

## Current UI sequence
1. Implement screenshot-guided Home Dashboard only.
2. Review at normal browser zoom and fix defects.
3. Obtain user approval.
4. Redesign remaining pages one at a time using the accepted system.
5. Run full regression and browser walkthrough.
6. Record demo and submit only after acceptance.

## Deployment is a separate phase
Investigate free hosting only after the UI is accepted. Verify provider quotas, sleeping, bandwidth, durable storage, auth, data isolation, retention, and actual cost. No public deployment is currently verified.

## Governance
Preserve all branches and PR #1. No force-push/reset/delete/rename/merge without explicit user authorization. Main is the documentation/control baseline and remains scaffold code; this documentation update does not merge implementation branches. Do not alter the user's uploaded PDFs.


---

## Final overhaul decision — 2026-10-11

The authoritative next-phase plan is now [`docs/FINAL_OVERHAUL_PLAN.md`](FINAL_OVERHAUL_PLAN.md). This section supersedes earlier forward-looking implementation instructions where they conflict; prior entries remain preserved as history.

**Current direction:** controlled Agno-first overhaul with v0-generated Next.js/TypeScript frontend, Python Agno AgentOS backend, Ollama/local model baseline, SQLite + FTS5 + local ChromaDB, local embeddings, deterministic evidence/assessment verification, and existing BKT logic. See the final plan for exact decisions, acceptance gates, branch rules, and the only three executor prompts.

**Execution model:** exactly three implementation chats: (1) Agno/evidence foundation, (2) frontend and adaptive learning loop, (3) evaluation, hardening and submission. Implementation must proceed on dedicated phase branches; preserve all legacy Streamlit code, source data, tests, PDFs, and Git history. Do not force-push, reset, delete/rename branches, close/merge PR #1, change visibility, or merge implementation to main without explicit approval.

**Truthfulness gate:** the plan is locked; implementation and acceptance are not yet proven. Organizer requirements are the acceptance baseline. Never claim a requirement, test, metric, deployment, video or submission is complete without reproducible evidence.
