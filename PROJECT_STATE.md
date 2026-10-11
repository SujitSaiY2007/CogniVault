# CogniVault — Authoritative Project State

**Reconciled:** 2026-10-11  
**Current phase:** Final Agno-first overhaul plan locked; implementation acceptance pending.  
**Authority:** docs/FINAL_OVERHAUL_PLAN.md

## Current decision

Use v0-generated Next.js/TypeScript, Python Agno AgentOS, Ollama local-model baseline, SQLite + FTS5 + local ChromaDB, local embeddings, deterministic verification and the existing BKT learner model. Exactly three implementation chats are planned.

## Done

- Organizer Track D and problem-statement requirements were retrieved from the project library and used as acceptance criteria.
- Final stack, preservation rules, acceptance gates and three executor prompts were committed to main.
- Existing Streamlit code, prior reports, tests, data, user PDFs, branches and PR #1 remain historical assets.

## Not yet verified

- Agno runtime integration with current evidence contracts.
- Next.js UI connected to a working backend.
- End-to-end ingestion, cited tutoring, assessment, BKT and recommendation loop.
- New-stack tests, frontend build and browser walkthrough.
- Final architecture evaluation, simulated learner results, public deployment, demo video and portal submission.

## Next action

Start Chat 1 using Prompt 1 in docs/FINAL_OVERHAUL_PLAN.md. Inspect remote heads and local working tree first, then select the safest preserved implementation baseline. Implement only on the dedicated Chat 1 branch.

## Preservation

No destructive cleanup, force-push/reset, branch deletion/rename, PR #1 merge/closure, repository visibility change, or implementation merge to main without explicit approval. Historical test results do not prove new commits.
