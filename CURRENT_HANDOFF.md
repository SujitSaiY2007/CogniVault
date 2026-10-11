# Current Handoff — Chat 06

**Reconciled:** 2026-10-10  
**AG response:** Pending; task may still be running.

## Immediate instruction
The user already sent AG a detailed prompt for Chat 05 Stage 1: implement only the screenshot-guided Home Dashboard on `chat05-ui-overhaul`, preserve backend/branches, test, capture screenshot and report. Do not issue a duplicate prompt while the response may still be in progress.

At the start of Chat 06, ask the user to paste AG's response/report and screenshot if available. Then verify current GitHub branch HEAD, diff, changed files and test evidence.

## Observed refs at handoff
- main before documentation-only sync: `0dd3acd0f973f7afcf8dada234f844ee5095b19a`.
- chat01: `cca915ca2edb209491f0766b0a224e65995b877c`.
- chat02: `fbdce9d824ea7384b3bf13ff3a79e217cee4a1bd`.
- chat03: `6dc575def670426166c4a7f8d271a8886e5fa288`.
- chat04: `a717132781f2957f5162786b3919f2ba32217d67`.
- chat05 before pending dashboard changes: `c213298a7ebe486ee9e793e54be2563431bf4d6c`.
- PR #1 is open/draft for Chat 01. Preserve it.
- User PDFs at root are immutable references.

## Why the UI task exists
Screenshots of the first overhaul show raw HTML fragments, headings wrapping one letter at a time, tiny text, excessive technical clutter and bad spacing. User rejected it and approved a screenshot-guided, one-screen-at-a-time process.

## Chat 06 workflow
1. Obtain pending AG response.
2. Verify branch/diff and confirm main/PR/PDFs untouched.
3. Inspect screenshot at normal zoom.
4. Fix only remaining dashboard defects if needed.
5. Run focused and full tests; distinguish AppTest from browser testing.
6. Ask for explicit user visual approval.
7. Only after approval, plan the next page.
8. Do not mark demo/portal submission complete without evidence.

## Unverified
Browser walkthrough, demo recording, portal submission, public hosting, durable cloud storage, actual authentication and server-enforced quotas.

## Roles
User = product owner/final visual approval. Antigravity = repository executor. ChatGPT = coordinator/reviewer/continuity.


---

## Final overhaul decision — 2026-10-11

The authoritative next-phase plan is now [`docs/FINAL_OVERHAUL_PLAN.md`](FINAL_OVERHAUL_PLAN.md). This section supersedes earlier forward-looking implementation instructions where they conflict; prior entries remain preserved as history.

**Current direction:** controlled Agno-first overhaul with v0-generated Next.js/TypeScript frontend, Python Agno AgentOS backend, Ollama/local model baseline, SQLite + FTS5 + local ChromaDB, local embeddings, deterministic evidence/assessment verification, and existing BKT logic. See the final plan for exact decisions, acceptance gates, branch rules, and the only three executor prompts.

**Execution model:** exactly three implementation chats: (1) Agno/evidence foundation, (2) frontend and adaptive learning loop, (3) evaluation, hardening and submission. Implementation must proceed on dedicated phase branches; preserve all legacy Streamlit code, source data, tests, PDFs, and Git history. Do not force-push, reset, delete/rename branches, close/merge PR #1, change visibility, or merge implementation to main without explicit approval.

**Truthfulness gate:** the plan is locked; implementation and acceptance are not yet proven. Organizer requirements are the acceptance baseline. Never claim a requirement, test, metric, deployment, video or submission is complete without reproducible evidence.
