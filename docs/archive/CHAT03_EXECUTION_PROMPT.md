# Chat 03 Execution Prompt — Evaluation, Hardening & Submission Package

**Canonical roadmap:** `docs/FINAL_OVERHAUL_PLAN.md` on `main`  
**Chat 02 report:** `docs/CHAT02_PRODUCT_LOOP_REPORT.md` on `overhaul/chat-02-product-loop`  
**Implementation branch:** `overhaul/chat-03-evaluation-submission`  
**Reported Chat 02 commit:** `4917668f0e93ed6851c50341768631ada7e943ce`  
**Important:** re-fetch and verify the live remote branch head before creating the branch. Do not blindly trust this recorded SHA if the remote advanced.

You are the local implementation executor for the existing CogniVault repository. This is the final implementation phase in the locked three-chat plan. ChatGPT maintains governance/reviews evidence; Antigravity executes local code, tests, and browser work.

## 0. Preflight — must happen before edits
1. Open the existing local repository `C:\Users\sujit\CogniVault`; inspect `git status --short --branch`, current branch, HEAD, and remotes. Preserve dirty/untracked work; do not stash, discard, or overwrite it without explicit permission.
2. Fetch remote refs and verify `origin/overhaul/chat-02-product-loop` live HEAD. Compare it with reported Chat 02 SHA `4917668f0e93ed6851c50341768631ada7e943ce`; record any divergence and inspect commits/diffs before proceeding.
3. Run the full existing Python suite from the verified Chat 02 state before adding Chat 03 changes:
   `& .\.venv\Scripts\python.exe -m pytest tests/ -v --durations=10`
   Run the frontend build too:
   `npm --prefix frontend run build`
   Record actual console output and exit codes. If the local checkout is behind or differs from the remote, safely fast-forward only if clean and ancestry proves it is safe; never reset or force. If dirty or divergent, preserve and diagnose before branching.
4. Read `docs/FINAL_OVERHAUL_PLAN.md`, `docs/CHAT02_PRODUCT_LOOP_REPORT.md`, all current control documents, the existing benchmark/evaluation runner, learner simulation code, security policy, source resolver, ingestion and citation logic, frontend/API code, and organizer Track D requirements.
5. Only after preflight is recorded, create/use `overhaul/chat-03-evaluation-submission` from the verified live Chat 02 remote HEAD. Do not branch from `main`.

## Git and preservation invariants
- Preserve all source, tests, data, four user reference PDFs, reports, commit history, every existing branch, PR #1, and the legacy Streamlit path.
- Never force-push, reset, rebase published history, delete/rename branches, close/merge PR #1, change repository visibility, or merge implementation to `main`.
- Commit/push only to `overhaul/chat-03-evaluation-submission`.
- Do not weaken/delete tests to obtain a green suite. Do not invent metrics, screenshots, browser success, deployment, or submission status.
- If a defect is found, fix it in the Chat 03 branch and add a regression test. Record baseline and post-fix results.

## 1. Grounding and abstention evaluation
Build or extend a reproducible evaluation set using the actual bundled/seed corpus and known physical locators. Include:
- supported questions with expected source IDs and page/slide/timestamp;
- unsupported/off-material questions;
- ambiguous or insufficient-evidence questions;
- citation integrity and exact-locator resolution;
- source ingestion/provenance and retrieval checks;
- assessment answer-key/source verification where relevant.

Run the existing benchmark runner first; preserve baseline outputs. Report faithfulness, answer relevancy, context precision and context recall using RAGAS or a documented equivalent that is actually executable. For every metric, document its definition, numerator/denominator or scoring procedure, test set size, model/judge dependency, and limitations. Prefer deterministic offline checks where possible; distinguish exact deterministic metrics from LLM-judged estimates. Do not relabel simple keyword overlap as a validated semantic metric.

Report abstention precision/recall or a transparent confusion matrix for supported vs unsupported queries, citation addressability, locator accuracy, retrieval precision/recall, and any failed cases. Include raw machine-readable results and a human-readable report with exact commands and environment details.

## 2. Multi-session learner evaluation
Execute and/or extend `evaluation/simulate_learners.py` with several distinct synthetic learner profiles across multiple sessions (e.g., progressing, struggling, mixed, misconception-prone, prerequisite-blocked, and cold-start). Measure:
- topic mastery trajectory over sessions using persisted BKT values;
- improvement relative to a stated baseline, with formulas and denominators;
- misconception detection/remediation behavior;
- prerequisite gate compliance;
- question repetition rate and duplicate suppression;
- persistence across restart/session boundaries.

Do not guarantee mastery gains: report what the simulations actually show, including regressions and limitations. Save reproducible JSON/CSV outputs and add tests for the metric calculations.

## 3. Browser/UI end-to-end proof — mandatory gap closure
Chat 02 reported a successful Next.js build and live HTTP acceptance sequence, but the internal Playwright browser runner failed downloading browser binaries (HTTP 404). Do not describe HTTP requests as a full browser walkthrough. Resolve this gap:
- inspect installed browsers and Playwright dependencies;
- use a locally available compatible browser/runtime or install a compatible pinned package only through an available, working source; do not repeatedly rely on the failed CDN URL;
- if browser automation genuinely cannot be run, execute and document a manual visual walkthrough with screenshots at desktop and mobile widths, clearly labelling it manual. Do not claim automated browser tests passed.
- Exercise all major views and interactions: learner intake/switching, PDF/PPTX/TXT ingestion, source list, grounded tutor and citation drawer, off-material abstention, MCQ/short-answer/numerical submission, verified feedback, BKT persistence, misconception remediation, recommendations/prerequisite gates, backend offline/error/empty states, and responsive layout.
- Check console/network errors, dead buttons, overflow, loading/error states, keyboard/focus/accessibility basics, and ensure displayed metrics derive from real API data rather than placeholders.
- Save screenshots/logs and exact reproducible steps under a dedicated Chat 03 evidence directory.

## 4. Security, robustness and dependency checks
Inspect:
- learner isolation and authorization on all read/write endpoints;
- file upload size/type limits, parsing failures, path traversal, unsafe file handling and resource limits;
- citation/source-ID validation, prompt injection from uploaded content, model output schema validation and fail-closed behavior;
- CORS/environment configuration and no secrets in source or frontend bundle;
- SQLite transaction/persistence behavior, concurrent submissions, duplicate submissions, malformed payloads and unavailable Ollama/Chroma paths;
- frontend accessibility/responsiveness, empty/loading/error states and API error handling;
- dependency lockfiles and known security advisories where local tooling can check them.

Add targeted tests for confirmed defects. Avoid speculative rewrites; make minimal justified fixes and document residual risk.

## 5. Final documentation and submission assets
Create/update:
- `docs/CHAT03_EVALUATION_REPORT.md`: methods, dataset/test cases, commands, raw metric references, actual results, failures, limitations and reproducibility instructions.
- `docs/CHAT03_HARDENING_REPORT.md`: issues found, fixes, tests, security/UX audit and residual risks.
- architecture, evidence-grounding/citation contract, learner/BKT model and local setup documentation as needed.
- final demo script for a 3–10 minute video, click-by-click recording checklist, submission description and final requirement-to-evidence matrix. Do not claim the video was recorded or uploaded.
- update `CURRENT_HANDOFF.md`, `CURRENT_OBJECTIVE.md`, `PROJECT_STATE.md`, `DEMO_PLAN.md`, `EVALUATION_PROTOCOL.md`, `SUBMISSION_PLAN.md`, README and requirement traceability to match evidence actually produced. Remove contradictory current-status claims only by preserving historical records and clearly marking them historical; do not erase project history.

## 6. Final verification and exit gate
Run and record:
- complete Python regression suite;
- targeted evaluation/simulation/security tests;
- frontend lint/typecheck/build;
- backend API smoke/integration tests;
- browser walkthrough or honestly labelled manual visual walkthrough;
- secrets/diff review and clean status.
Fix failures where feasible; do not suppress or weaken tests. Confirm the branch includes only intended Chat 03 work and compare it with its verified Chat 02 parent. Push only the Chat 03 branch and verify the exact remote HEAD.

## Required final report
State:
1. verified starting and ending SHAs;
2. exact commands and actual exit codes/output summaries;
3. tests passed/failed/skipped and why;
4. evaluation formulas, sample counts, measured results and limitations;
5. learner simulation results and question repetition rate;
6. browser evidence type (automated or manual), screenshots/log locations and any gaps;
7. security fixes and residual risks;
8. all changed files and documentation links;
9. what is demonstrably ready vs still incomplete;
10. human-only tasks: final video recording/upload and hackathon portal submission.

Do not merge to `main`, change visibility, close/merge PR #1, or start another implementation phase. This is Chat 03 of the three-chat plan; finish with an evidence-backed closure report, not an unverified “submission ready” claim.
