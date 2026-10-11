# Decision Log — Reconciled 2026-10-10

Historical decisions are retained as history. Current decisions supersede obsolete workflow instructions; do not erase the audit trail.

| ID | Decision | Status |
|---|---|---|
| D-001 | Product name CogniVault | Locked |
| D-002 | Track D — Personalized Tutoring & Adaptive Learning | Locked |
| D-003 | Evidence-first grounded behavior with abstention | Locked |
| D-004 | Mathematics/Science starter corpus | Locked |
| D-005 | Streamlit-first architecture | Locked |
| D-006 | Lightweight services; avoid unnecessary agents/microservices | Locked |
| D-007 | No secrets in Git | Locked |
| D-008 | Evaluation claims require executed evidence | Locked |
| D-009 | Hybrid retrieval and source provenance | Reported on Chat 01 branch |
| D-010 | Sufficiency gate and abstention | Reported on Chat 02 branch |
| D-011 | BKT and explainable recommendation policy | Reported on Chat 02 branch |
| D-012 | Benchmark and simulated learner evaluation | Reported on Chat 03 branch |
| D-013 | Chat 04 acceptance checkpoint retained | `a717132781f2957f5162786b3919f2ba32217d67` |
| D-014 | Initial Chat 05 overhaul isolated on its branch | `c213298a7ebe486ee9e793e54be2563431bf4d6c` |
| D-015 | Preserve main, PR #1, and all phase branches | Locked |
| D-016 | Screenshot/browser acceptance is required | Current |
| D-017 | Redesign one screen at a time, dashboard first | Current |
| D-018 | User screenshot is primary dashboard reference | Current |
| D-019 | Remove raw HTML leakage, tiny text and technical clutter | Current |
| D-020 | Use real data and honest empty states | Current |
| D-021 | Do not equate BKT probability with course completion | Current |
| D-022 | Guest history is session-only | Current |
| D-023 | Free hosting/auth/durable storage/quotas are future work until verified | Current |
| D-024 | Main gets documentation synchronization only; implementation remains on phase branches | Current |
| D-025 | Reconcile pending AG response before issuing duplicate task | Current |

Chat 0's instruction that Chat 1 is the next phase is historical and superseded by Chats 01–05.


---

## Final overhaul decision — 2026-10-11

The authoritative next-phase plan is now [`docs/FINAL_OVERHAUL_PLAN.md`](FINAL_OVERHAUL_PLAN.md). This section supersedes earlier forward-looking implementation instructions where they conflict; prior entries remain preserved as history.

**Current direction:** controlled Agno-first overhaul with v0-generated Next.js/TypeScript frontend, Python Agno AgentOS backend, Ollama/local model baseline, SQLite + FTS5 + local ChromaDB, local embeddings, deterministic evidence/assessment verification, and existing BKT logic. See the final plan for exact decisions, acceptance gates, branch rules, and the only three executor prompts.

**Execution model:** exactly three implementation chats: (1) Agno/evidence foundation, (2) frontend and adaptive learning loop, (3) evaluation, hardening and submission. Implementation must proceed on dedicated phase branches; preserve all legacy Streamlit code, source data, tests, PDFs, and Git history. Do not force-push, reset, delete/rename branches, close/merge PR #1, change visibility, or merge implementation to main without explicit approval.

**Truthfulness gate:** the plan is locked; implementation and acceptance are not yet proven. Organizer requirements are the acceptance baseline. Never claim a requirement, test, metric, deployment, video or submission is complete without reproducible evidence.
