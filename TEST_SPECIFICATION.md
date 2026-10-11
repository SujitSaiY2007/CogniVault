# Test Specification — Release Candidate

## Reported baseline
Chat 04/05 reports state 102 tests passed in 39.30 seconds and AppTest 8/8 navigation targets. This docs update did not rerun the suite.

## Regression groups
- Ingestion/source manifest and provenance.
- Stable evidence IDs, retrieval traces and citation resolution.
- Supported tutor query and unsupported abstention.
- Fail-closed citation/provider errors.
- Assessment selection, answer validation and BKT state update.
- Persistence across expected reruns/restarts where claimed.
- Recommendation rationale and prerequisite gate.
- Evaluation formulas, denominators and displayed values.
- Dashboard normal-zoom layout, no raw HTML leakage, no one-character wrapping, working routes, global tutor submission, continue/history actions, empty states and narrow viewport behavior.

## Command
Run on the actual implementation branch and configured environment, not assumed runnable from scaffold-only main:
```powershell
& .\.venv\Scripts\python.exe -m pytest -v --durations=10
```

If unavailable, report the exact blocker. Never claim tests passed without output.

## Browser disclosure
Prior Playwright attempt failed downloading its driver. AppTest does not replace browser acceptance. Label each check as AppTest, real-browser, or pending.


---

## Final overhaul decision — 2026-10-11

The authoritative next-phase plan is now [`docs/FINAL_OVERHAUL_PLAN.md`](FINAL_OVERHAUL_PLAN.md). This section supersedes earlier forward-looking implementation instructions where they conflict; prior entries remain preserved as history.

**Current direction:** controlled Agno-first overhaul with v0-generated Next.js/TypeScript frontend, Python Agno AgentOS backend, Ollama/local model baseline, SQLite + FTS5 + local ChromaDB, local embeddings, deterministic evidence/assessment verification, and existing BKT logic. See the final plan for exact decisions, acceptance gates, branch rules, and the only three executor prompts.

**Execution model:** exactly three implementation chats: (1) Agno/evidence foundation, (2) frontend and adaptive learning loop, (3) evaluation, hardening and submission. Implementation must proceed on dedicated phase branches; preserve all legacy Streamlit code, source data, tests, PDFs, and Git history. Do not force-push, reset, delete/rename branches, close/merge PR #1, change visibility, or merge implementation to main without explicit approval.

**Truthfulness gate:** the plan is locked; implementation and acceptance are not yet proven. Organizer requirements are the acceptance baseline. Never claim a requirement, test, metric, deployment, video or submission is complete without reproducible evidence.
