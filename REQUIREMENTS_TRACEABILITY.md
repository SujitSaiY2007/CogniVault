# Requirements Traceability — Current

Status terms: specified ≠ implemented; reported ≠ independently verified; AppTest ≠ browser acceptance; planned ≠ submitted.

| ID | Requirement | Evidence/state | Remaining acceptance |
|---|---|---|---|
| R01 | PDF/PPTX/transcript ingestion | Reported Chat 01/04/05 | Re-run end-to-end on final branch |
| R02 | Stable evidence IDs and locators | Reported Chat 01 | Resolve citations in browser |
| R03 | Hybrid retrieval | Reported Chat 01 | Confirm artifacts |
| R04 | Grounded tutor | Reported Chat 02/04 | Browser supported query + citation |
| R05 | Unsupported-query abstention | Reported Chat 02/04 | Browser off-corpus query |
| R06 | Verified assessment | Reported Chat 02/04 | Submission and regression test |
| R07 | BKT state updates | Reported Chat 02/04 | Verify persistence and metric semantics |
| R08 | Misconception signals | Reported Chat 02/04 | Verify signal behavior |
| R09 | Recommendations/prerequisite gating | Reported Chat 02/04 | Verify real state/policy |
| R10 | Deterministic benchmark | Reported Chat 03/04/05 | Re-run before release |
| R11 | UI workflows | Initial Chat 05 reported | Current dashboard redesign pending |
| R12 | Browser visual acceptance | Not complete | Required |
| R13 | Guest session-only history | Product requirement | Implementation not verified |
| R14 | Registered login/persistent history | Not verified | Future scope |
| R15 | Server-enforced free quotas | Not verified | Required before public multi-user release |
| R16 | Free public hosting/durable storage | Not verified | Separate deployment phase |
| R17 | Demo recording | Not confirmed | Pending |
| R18 | Official portal submission | Not confirmed | Pending |

Do not promote a row's status without an artifact, executed test, screenshot, browser observation, or submission receipt appropriate to the claim.


---

## Final overhaul decision — 2026-10-11

The authoritative next-phase plan is now [`docs/FINAL_OVERHAUL_PLAN.md`](FINAL_OVERHAUL_PLAN.md). This section supersedes earlier forward-looking implementation instructions where they conflict; prior entries remain preserved as history.

**Current direction:** controlled Agno-first overhaul with v0-generated Next.js/TypeScript frontend, Python Agno AgentOS backend, Ollama/local model baseline, SQLite + FTS5 + local ChromaDB, local embeddings, deterministic evidence/assessment verification, and existing BKT logic. See the final plan for exact decisions, acceptance gates, branch rules, and the only three executor prompts.

**Execution model:** exactly three implementation chats: (1) Agno/evidence foundation, (2) frontend and adaptive learning loop, (3) evaluation, hardening and submission. Implementation must proceed on dedicated phase branches; preserve all legacy Streamlit code, source data, tests, PDFs, and Git history. Do not force-push, reset, delete/rename branches, close/merge PR #1, change visibility, or merge implementation to main without explicit approval.

**Truthfulness gate:** the plan is locked; implementation and acceptance are not yet proven. Organizer requirements are the acceptance baseline. Never claim a requirement, test, metric, deployment, video or submission is complete without reproducible evidence.
