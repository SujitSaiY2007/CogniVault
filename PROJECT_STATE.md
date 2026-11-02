# CogniVault — Project State

**Status date:** 2026-11-02  
**Repository:** [SujitSaiY2007/CogniVault](https://github.com/SujitSaiY2007/CogniVault)  
**Default branch:** `main`

## Current repository snapshot

The `main` tree contains the Python application, FastAPI/Agno API layer, Next.js frontend, preserved Streamlit UI, course fixtures, evaluation assets, tests, and project documentation. The repository is not just the early scaffold described in some older planning notes.

## Implemented areas represented in the source tree

- Source ingestion and provenance records for supported PDF, PPTX, and text inputs.
- Hybrid retrieval and evidence sufficiency checks.
- Source-grounded tutor path with citation resolution and abstention behavior.
- Assessment generation/selection and deterministic answer structure/numeric checks.
- Topic-level Bayesian Knowledge Tracing, misconception diagnostics, and recommendations.
- API and frontend workflows; legacy Streamlit interface retained.
- Evaluation runners, result artifacts, and test suites.

This inventory is a source-tree summary, not a fresh runtime acceptance test.

## Verification record

`docs/FINAL_VERIFICATION_AND_SUBMISSION_REPORT.md` records a 143-test pass (355.20 seconds in its shown Windows/Python 3.12 environment) and a successful frontend production build. README and submission documents contain other test counts and timings from different project checkpoints. **Do not treat those as interchangeable or as freshly rerun results.** For a new release or resume claim, rerun the suite and build on the exact commit being presented and update the report with commit and environment details.

Live deployment status and hosted persistence are not confirmed by this state file. Verify the endpoints and host storage behavior before describing production availability.

## Documentation cleanup status

A review-only portfolio cleanup is being prepared on `portfolio/readme-docs-cleanup-2026-11-02`. It does not change `main`, implementation code, evaluation data, historical branches, pull requests, or repository visibility. The user will decide what to do with the proposed changes.

## Preservation rules

- Keep historical evidence, source fixtures, tests, and decision records.
- Do not force-push, reset, delete/rename branches, change visibility, or merge without explicit approval.
- Treat phase plans and handoffs as historical context unless their status is explicitly current.
