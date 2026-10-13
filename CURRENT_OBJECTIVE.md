# Current Objective — Chat 03: Evaluation, Hardening & Submission Package

**Status:** Chat 02 branch verified; Chat 03 not yet implemented.  
**Canonical plan:** [docs/FINAL_OVERHAUL_PLAN.md](docs/FINAL_OVERHAUL_PLAN.md)  
**Exact executor prompt:** [docs/CHAT03_EXECUTION_PROMPT.md](docs/CHAT03_EXECUTION_PROMPT.md)

## Verified starting point
- Branch: `overhaul/chat-02-product-loop`
- Reported SHA: `4917668f0e93ed6851c50341768631ada7e943ce`
- Live GitHub compare confirmed this SHA matches the remote branch head at reconciliation time. Re-fetch and re-verify before branching.
- Chat 02 report records 127 Python tests passing in 232.91s and a successful frontend build; this documentation step did not rerun those commands.
- Important known gap: Playwright browser binary download failed with HTTP 404, so a full automated browser walkthrough was not established.

## Chat 03 goals
1. Run the full Python suite and frontend build before changes; inspect the local checkout and preserve dirty work.
2. Create/use `overhaul/chat-03-evaluation-submission` from the verified latest Chat 02 remote HEAD, never from `main`.
3. Run reproducible evidence-grounding, citation-locator, supported/unsupported abstention and retrieval benchmarks with transparent definitions, denominators and limitations.
4. Run multi-session synthetic learner profiles and report BKT mastery trajectories, misconception/prerequisite behavior, persistence and question repetition rate.
5. Close the browser evidence gap with real automated browser checks if possible; otherwise perform a documented manual desktop/mobile walkthrough with screenshots. Never label HTTP checks as browser testing.
6. Perform security, robustness, accessibility and responsive UI checks; fix confirmed defects with regression tests.
7. Produce evidence-backed evaluation/hardening reports, architecture and grounding docs, a 3–10 minute demo script, requirement-to-evidence matrix and submission checklist.

## Exit gate
All commands, exit codes, actual test outputs, metrics, screenshots/logs, limitations and changed files are recorded. No fabricated metrics, browser success, deployment, video upload or portal submission claims. Push only the Chat 03 branch and verify remote SHA. Do not merge implementation to `main`.

## Preservation
Keep all historical code/data/tests/user PDFs/reports/branches/commit history and PR #1. No force-push/reset, branch deletion/rename, PR #1 close/merge, repository visibility change or unapproved main merge. Video recording/upload and portal submission remain human tasks.
