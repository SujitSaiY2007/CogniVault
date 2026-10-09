# NEXT CHAT PROMPT — CHAT 03: PRODUCT & EVALUATION

You are continuing the existing repository **SujitSaiY2007/CogniVault**, project **CogniVault — Evidence-First Adaptive Learning**, Hackathon Track D — Personalized Tutoring & Adaptive Learning.

## Mission

Complete **Chat 03 — Product & Evaluation** end to end: deliver a usable Streamlit demo, a small real and reproducible school-level Mathematics/Science corpus, a deterministic evaluation runner, and simulated multi-turn learner evaluations with measured results. Begin by validating the current Chat 02 closure state; do not spend the chat re-planning the project or asking the user to restate known requirements.

## Step 0 — Sync, verify, and establish the branch boundary (mandatory)

1. Treat GitHub as the canonical source of truth. Fetch the latest remote refs and inspect `README.md`, `PROJECT_MASTER_PLAN.md`, `PROJECT_STATE.md`, `CURRENT_OBJECTIVE.md`, `CURRENT_HANDOFF.md`, `DECISION_LOG.md`, `REQUIREMENTS_TRACEABILITY.md`, `ARCHITECTURE.md`, `TEST_SPECIFICATION.md`, `HALLUCINATION_CONTROL.md`, `SECURITY_AND_USAGE_POLICY.md`, `EVALUATION_PROTOCOL.md`, `DEMO_PLAN.md`, `SUBMISSION_PLAN.md`, `docs/CHAT0_TECHNICAL_LOCK.md`, `docs/CHAT01_IMPLEMENTATION_STATUS.md`, and `docs/CHAT02_IMPLEMENTATION_STATUS.md`, plus the relevant application code and tests.
2. Confirm the current remote HEAD of `chat02-intelligence-core`; do not assume an old commit hash. The Chat 02 closure documentation records a prior 80-test pass, but the final malformed-grouped-decimal assertions were added after that reported run. The **first executable task** is to sync the local Chat 02 branch to remote HEAD and run the full test suite using the repository's documented Windows virtual-environment command:
   ```powershell
   & .\.venv\Scripts\python.exe -m pytest -v --durations=10
   ```
3. If the suite fails, diagnose the actual failure. Fix only defects needed to restore correctness of the Chat 02 branch, including the strict comma-grouping regression cases if relevant. Do not silently skip tests or weaken assertions. Run the complete suite again until green. Commit and push any Chat 02 repair **only to `chat02-intelligence-core`**, update the closure records with actual output, then re-sync.
4. Once Chat 02 is green, create/switch to `chat03-product-evaluation` from the **verified current remote HEAD of `chat02-intelligence-core`**. Confirm clean working tree and record both base SHA and new branch SHA. Never branch from `main`.
5. Do not modify or merge to `main`; do not merge or close PR #1; do not delete, rename, or rewrite any existing branch. Preserve all unrelated user changes. If the working tree has unexpected changes, inspect and preserve them rather than resetting or discarding them.

## Locked product and technical boundaries

- Initial learning domain: **school-level Mathematics and Science**.
- Evidence first: retrieval → sufficiency decision → grounded answer → citation verification → response. Abstain or clearly flag unsupported questions.
- Grounded claims must cite real, resolvable evidence IDs and exact source locators. Never fabricate citations, answers, evaluation scores, or benchmark outcomes.
- The deterministic question verifier proves **structural integrity**, not external factual truth. Do not describe its result as proof that the answer is factually correct.
- Mastery policy from `docs/CHAT0_TECHNICAL_LOCK.md` §17 is authoritative:
  - `p < 0.40`: foundational review, easy.
  - `0.40 <= p < 0.70`: targeted practice, medium.
  - `0.70 <= p <= 0.85`: mixed application, medium.
  - `p > 0.85`: advance topic, hard.
  - Exactly `0.85` remains mixed application; advancement is strictly greater than `0.85`.
- Missing prerequisite mastery is **unverified**, not assumed mastered. A missing record or prerequisite mastery below `0.70` blocks advancement and directs foundational review to the prerequisite; exactly `0.70` satisfies readiness.
- Misconception diagnosis requires repeated/strong evidence per the technical lock; an isolated wrong answer is not automatically a misconception.
- Keep the architecture lightweight: Python, Streamlit, SQLite/FTS5, existing retrieval stack, and at most the already permitted provider configuration. No unnecessary agents, microservices, Kubernetes, custom model training, or new architectural framework.
- Do not claim zero hallucinations, learning improvement, novelty, or superiority without a defined measurement and actual evidence. Established RAG, BKT, adaptive assessment, and tutoring methods are prior art.

## Deliverable 1 — Functional Streamlit demo (`app/ui/`)

Implement a cohesive, working UI using the existing application services rather than duplicating business logic. Include these practical views/workflows:

1. **Course setup and ingestion:** upload/ingest supported PDF, PPTX, and supported transcript material; show clear validation/errors and ingestion results.
2. **Evidence explorer:** browse source records/evidence, source locators, and relevant metadata; show citations that can be resolved back to evidence.
3. **Grounded tutor:** accept a learner question, show answer and exact citations, surface abstention/sufficiency reasons for unsupported questions, and expose enough trace detail to audit grounding.
4. **Adaptive assessment:** present only verified questions, accept responses, show evidence-linked feedback, and avoid repeating already-served questions when valid alternatives exist.
5. **Learner profile:** show persisted per-topic BKT mastery and relevant interaction history without inventing learner data.
6. **Recommendations:** show the recommended next action, difficulty, rationale, prerequisite readiness, and misconception signals based on actual persisted state.
7. **Evaluation/admin:** run the reproducible benchmark and display actual results, run metadata, and limitations.

Use clear navigation, useful empty states, loading/error handling, safe input validation, and readable layouts. The UI must be demonstrable on a clean local setup. Do not imply unsupported visual reasoning if the pipeline only extracts text/OCR/captions.

## Deliverable 2 — Real, reproducible Mathematics/Science corpus

Create a small, legally usable and reproducible corpus sufficient to exercise:

- definitions and conceptual explanations;
- equations and numerical problems;
- figures/diagrams within actual supported extraction scope;
- prerequisite relationships;
- direct evidence questions, cross-source questions, and unsupported/off-corpus questions.

Add a source manifest with source ID, title, subject/level, provenance/license note, checksum, acquisition instructions or URL where appropriate, parser/extractor version, and status. Prefer open-license/public educational sources or user-provided content. Do not commit large source files or private materials. Use small fixtures where useful. Validate ingestion, evidence addressability, exact locators, duplicates, and citation resolution. Clearly mark any source that could not be obtained or verified; never invent its license or contents.

## Deliverable 3 — Reproducible benchmark runner (`evaluation/runner.py`)

Build a deterministic runner with a fixed benchmark dataset, explicit reference answers, expected supporting evidence IDs/locations, and defined supported versus unsupported questions. Keep evaluation inputs/versioning and results reproducible. At minimum, define and measure:

- retrieval precision@K and recall@K, with the relevance rule and K stated;
- grounded-answer support/faithfulness, or a clearly named and documented deterministic proxy if semantic judging is unavailable;
- supported-answer rate;
- unsupported-question abstention rate and unsupported-answer leakage rate;
- citation validity/addressability and locator correctness;
- question structural-verification pass/reject behavior;
- question repetition rate;
- BKT state-update correctness on scripted observations;
- recommendation-policy correctness, including mastery boundaries and missing/under-mastered prerequisites.

Specify metric formulas and denominators before reporting scores. Separate deterministic checks from any subjective/model-assisted judgments. Save machine-readable results (for example JSON/CSV) with benchmark version, timestamp, configuration, and sample counts. Never fabricate missing scores or label a proxy as ground-truth faithfulness.

## Deliverable 4 — Simulated multi-turn learner evaluation

Add reproducible learner scenarios covering at least:

- consistently correct answers;
- consistently incorrect answers;
- mixed performance;
- repeated errors on the same concept;
- remediation followed by improvement;
- missing prerequisite mastery;
- prerequisite mastery below, exactly at, and above `0.70`;
- target mastery at `0.39`, `0.40`, `0.69`, `0.70`, `0.85`, and just above `0.85`;
- question repetition suppression when alternatives exist and fallback when they do not;
- supported and unsupported tutor queries.

Compare against an explicitly defined baseline where appropriate (for example, non-personalized fixed-difficulty selection). Report what the comparison actually measures. A changed recommendation is not evidence of improved learning; do not claim learning gains from simulated trajectories unless a valid learning-outcome measure exists.

## Deliverable 5 — Integration and regression tests

- Preserve and run all existing K1–K10, G1–G5, A1–A4, L1–L3, S2 and unit tests.
- Add end-to-end tests for ingestion → evidence retrieval → sufficiency → grounded tutor → resolvable citation/abstention.
- Add assessment → submission → persisted interaction → BKT update → misconception signal → prerequisite-aware recommendation tests.
- Test UI-facing service integration and evaluation runner outputs without requiring network access during ordinary unit tests.
- Test malformed/empty inputs, missing evidence, provider/retrieval failures, invalid configuration, and repeatability.
- Prefer deterministic tests; isolate any live provider calls and never make the full test suite depend on credentials or network availability.
- Run the full suite and record the exact command, Python/platform details, collected/passed/failed counts, and duration from actual output.

## Documentation and evidence discipline

After implementation and tests, reconcile these files so they describe the **actual** current state and agree with one another:

- `README.md`
- `PROJECT_STATE.md`
- `CURRENT_OBJECTIVE.md`
- `CURRENT_HANDOFF.md`
- `REQUIREMENTS_TRACEABILITY.md`
- `DECISION_LOG.md`
- `EVALUATION_PROTOCOL.md`
- `DEMO_PLAN.md`
- `SUBMISSION_PLAN.md`
- `docs/CHAT03_IMPLEMENTATION_STATUS.md` (create this report)

Keep historical Chat 01/02 status reports historically accurate; do not rewrite them to pretend Chat 03 work existed in those phases. Mark each requirement as implemented, partially implemented, planned, or blocked based on code and tests. Record actual benchmark outputs and limitations. Add a decision-log entry for any meaningful policy/architecture change before relying on it.

## Completion and Git protocol

Chat 03 is complete only when all of the following are true:

1. The UI runs locally from documented clean setup instructions.
2. The small source corpus and manifest are reproducible and legal/provenance notes are present.
3. The evaluation runner produces reproducible machine-readable results and metrics with explicit definitions.
4. Simulated learner scenarios run and produce interpretable, evidence-backed outputs.
5. All tests pass, including the existing baseline and new integration tests.
6. Documentation and traceability agree with implementation and observed test/benchmark evidence.
7. Changes are committed and pushed to **`chat03-product-evaluation` only**; working tree is clean; remote HEAD matches the final commit.
8. `main`, PR #1, and unrelated branches remain untouched.

At completion, provide a concise but complete report with: starting Chat 02 SHA, verified Chat 02 SHA, Chat 03 base SHA, final Chat 03 SHA, files changed, exact test command/output summary, benchmark metrics and formulas, demo run instructions, limitations, unresolved issues, and remote/worktree state. Explicitly distinguish tests actually run from prior reported results. Do not ask the user to approve routine implementation steps; make the best bounded decision consistent with these rules and record it. Ask a question only if a true blocker cannot be resolved safely from the repository.
