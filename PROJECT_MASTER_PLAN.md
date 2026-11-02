# CogniVault — Project Overview & Plan

**Track:** D — Personalized Tutoring & Adaptive Learning  
**Purpose:** A course-grounded adaptive learning companion linking evidence retrieval, tutoring, assessment, and learner-state updates.

## Current repository direction

The codebase currently contains the Python application and API, a Next.js frontend, a retained Streamlit interface, evaluation assets, tests, and documentation. The earlier phase-by-phase overhaul notes below are retained as project history; they are not a reliable live task queue by themselves.

For current facts, see [PROJECT_STATE.md](PROJECT_STATE.md). For implementation structure, see [ARCHITECTURE.md](ARCHITECTURE.md). For recorded acceptance evidence, see [Final Verification Report](docs/FINAL_VERIFICATION_AND_SUBMISSION_REPORT.md).

## Core product loop

1. Ingest course sources and preserve evidence provenance/locators.
2. Retrieve relevant course evidence.
3. Answer only when the evidence gate permits; otherwise abstain.
4. Verify assessment items and learner responses within deterministic constraints.
5. Update topic mastery with BKT.
6. Use mastery and prerequisite context to recommend a next learning action.
7. Evaluate the system with reproducible datasets, metrics, and tests.

## Project records

- [Decision log](DECISION_LOG.md) — decisions and their recorded implementation status.
- [Documentation index](docs/README.md) — current useful project documents and preserved historical records.
- [Repository branch map](docs/REPOSITORY_BRANCH_MAP.md) — dated branch observations and preservation notes.
- [Submission plan](SUBMISSION_PLAN.md) — hackathon checklist; contains checkpoint-specific assertions that should be revalidated before reuse.
- [Archive](docs/archive/) — prior chat/phase reports retained for continuity.

## Governance

- Preserve project history, PRs, evidence, test fixtures, and uploaded reference PDFs.
- No force-push, reset, branch deletion/rename, visibility change, or merge without explicit user authorization.
- Do not describe tests, deployment, submissions, metrics, or features as freshly verified unless evidence is tied to the commit and verification run.
- This repository documentation refresh is presentation cleanup only; it is not a request to rebuild or redesign the product.
