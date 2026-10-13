# CogniVault — Final Overhaul Plan and Three-Chat Execution Contract

**Date:** 2026-10-11  
**Project:** CogniVault — Evidence-First Adaptive Learning  
**Hackathon:** Multimodal AI Hackathon 2026, Track D — Personalized Tutoring & Adaptive Learning  
**Canonical repository:** https://github.com/SujitSaiY2007/CogniVault  
**Status:** Final plan locked; implementation not yet verified under this architecture.

## Executive decision

This is a continuation and controlled overhaul, not a new project. The objective is to complete the strongest reproducible submission in exactly three implementation chats after this plan. GitHub `main` is the canonical project plan and governance source. The three chats should use dedicated phase branches and must not merge implementation to `main` until final acceptance and explicit approval.

### Winning strategy

Prioritize the organizer's weighted rubric:
- Knowledge base and grounding — 20%
- Personalization effectiveness — 20%
- Assessment quality — 15%
- User experience and demo video — 15%
- System evaluation — 15%
- Technical implementation — 15%

A polished frontend is necessary but not sufficient. The judging story must show evidence traceability, correct abstention, verified assessment, measured adaptation over multiple simulated sessions, and reproducible evaluation.

## Organizer requirements retained as acceptance requirements

Based on the organizer Track D problem statement and submission guidance:
1. Ingest lecture videos, textbooks/PDFs, and slide decks with minimal manual preprocessing.
2. Organize content into topics, subtopics, concepts, and prerequisites.
3. Preserve exact provenance for each unit: PDF page, slide number, or video timestamp.
4. Extract and use relevant figures, diagrams, and images from documents/slides.
5. Answer using source-grounded excerpts with links that open the exact source location; decline or clearly label unsupported/off-material questions.
6. Support MCQ, short-answer, and numerical assessment, with topic, source locator, and difficulty; verify question/answer integrity and avoid repeats.
7. Update per-topic learner mastery after quizzes and tutoring interactions; support a new learner through diagnostic assessment or intake.
8. Evaluate faithfulness, answer relevancy, context precision, and context recall on a team-built set with known locators and unsupported queries.
9. Simulate multiple learner profiles across multiple sessions and report mastery gains and question repetition rate.
10. Deliver working ingestion, grounded tutor, adaptive assessment, dashboard, architecture/grounding/learner-model documentation, evaluation results, simulated-student results, and a 3–10 minute YouTube demonstration.

Do not claim that an organizer requirement is met unless a test, trace, reproducible artifact, or observable demo proves it.

## Final technology decisions

| Layer | Decision | Free-use approach |
|---|---|---|
| Frontend authoring | v0 by Vercel | Use limited free generation credits efficiently; export/sync code to GitHub. Do not make v0 a runtime dependency. |
| Frontend | Next.js + TypeScript + Tailwind CSS + accessible UI components | Local development; Vercel Hobby for eligible non-commercial demo use subject to current terms and limits. |
| Agent framework | Agno Python SDK | Use agents, tools, structured outputs, memory/session capabilities, workflows and guardrails where they improve the product. |
| Agent serving | Agno AgentOS / its FastAPI-based API surface | Local-first service; add custom routes only for product endpoints not covered by AgentOS. |
| LLM | Ollama local model as baseline; provider adapter permits an optional eligible free-tier hosted model | No paid API required for the reproducible baseline. Hosted free-tier quotas are optional and must not be assumed unlimited. |
| Persistence | SQLite | Local, portable, no hosted database bill. Preserve existing schema/data contracts where feasible. |
| Search | SQLite FTS5 + ChromaDB local vector index | Hybrid lexical/semantic retrieval; no paid vector service. |
| Embeddings | Local embedding model compatible with the selected vector index | Avoid paid embedding API dependency. |
| Ingestion | Python libraries for PDF, PPTX, text/transcript and video metadata/transcription | Add multimodal/OCR/diagram extraction only with explicit tests and source-locator preservation. |
| Learner model | Existing BKT/deterministic Python implementation | Keep numeric mastery updates deterministic and testable; agents may request tools but may not invent mastery. |
| Verification | Deterministic Python validators and source resolver | Validate source IDs/locators, answer schema, question structure, repeated-question policy, and allowed state mutations. |
| Evaluation | Existing benchmark harness plus RAGAS or an equivalent open evaluation method where compatible | Keep an offline deterministic benchmark runnable without paid APIs; label any LLM-judged metric and model dependency. |
| Tests | pytest, API/integration tests, frontend checks and recorded browser walkthrough | Local and reproducible. |
| Version control | Git + GitHub | GitHub remains canonical; preserve every phase branch and history. |

**Free means no mandatory paid subscription/API/hosting.** Free tiers are limited and can change. v0 credits are not unlimited. A locally running model is the only reliable no-per-token-cost baseline. Vercel frontend hosting does not by itself host the Agno backend. A public, always-on backend is not assumed to be free: prove an eligible free deployment or demonstrate the complete stack locally and record the demo. Do not expose API keys in the browser or commit secrets.

## Agno architecture: maximum practical use, not agent-for-everything

Use one Agno workflow as the orchestration boundary and three narrowly scoped specialists:
1. **Evidence Tutor Agent** — calls retrieval/source-resolution tools, uses only supplied evidence for grounded claims, and returns citations/abstention in a structured response.
2. **Assessment Agent** — drafts/selects MCQ, short-answer, and numerical questions; deterministic validators check schema, source/topic/difficulty, answer integrity, and duplicate policy before questions become usable.
3. **Learning Coach Agent** — reads verified learner-state tools and recommends a next action. BKT calculations and mastery persistence remain deterministic tools, not free-form model output.

Shared tools: hybrid retrieval, source locator resolver, question verifier, assessment scorer, BKT observation updater, misconception/prerequisite lookup, and recommendation candidate selector. Workflow order: request validation → retrieval → evidence sufficiency → response/assessment generation → deterministic verification → citation/source validation → permitted learner-state update → structured UI response.

Use Agno sessions/memory for conversational context, not as the source of truth for long-term mastery. Store durable learner state in SQLite. Use structured outputs, tool boundaries, input/output checks, tracing and evaluations. Start with a single workflow and direct agent calls; add a multi-agent team only if a measurable test proves it helps. No uncontrolled agent-to-agent loops.

## Historical preservation and Git rules

- Treat all existing code, data, tests, four user-provided PDFs, phase branches, commits, reports and prior-art notes as valuable history.
- Do not delete, rewrite, or mass-reformat existing implementation to make the new architecture appear clean.
- Do not force-push, reset, rename/delete branches, close or merge PR #1, or change repository visibility without explicit user approval.
- Keep the current Streamlit implementation as a preserved legacy/demo path while the Next.js/Agno path is built in dedicated new branches. Do not remove it until the new path passes acceptance and the user explicitly approves migration.
- Archive superseded plans by adding dated notes or copies under `docs/archive/`; do not erase original decision history or old status reports. Mark them historical and link to this final plan.
- Main receives the approved plan/governance documents only at this stage. Implementation proceeds on phase branches. Final merge to main is a separate acceptance decision.
- Never mark a requirement complete from source inspection alone; record the exact command, test result, commit, and evidence artifact.

## Exactly three implementation chats

### Chat 1 — Agno foundation and evidence contract
**Branch:** `overhaul/chat-01-agno-foundation` (create only if absent; base from the agreed latest preserved implementation branch after auditing all remote heads).  
**Goal:** prove a locally runnable Agno AgentOS backend can use existing evidence/retrieval contracts.  
**Tasks:** audit current branches and all project docs; map old modules to the new architecture; preserve old code; establish dependency lock/config and secrets policy; implement local model adapter; wire one Evidence Tutor Agent and retrieval/source-resolver tools; preserve exact page/slide/timestamp locators; add health/API checks; add unsupported-query abstention; document local run. Do not yet rebuild every frontend screen.  
**Exit gate:** clean install/run instructions; API-level supported and unsupported query tests pass; citations resolve to actual source locators; no paid API required; no legacy tests weakened; change report includes exact commands and outcomes.

### Chat 2 — v0/Next.js product and adaptive learning loop
**Branch:** `overhaul/chat-02-product-loop`, based on accepted Chat 1 head.  
**Goal:** connect a polished frontend to a working backend, not a static mockup.  
**Tasks:** generate/iterate UI using v0 and commit exported Next.js/TypeScript code; implement course/material ingestion UX, grounded tutor with clickable source locators, MCQ/short-answer/numerical practice, feedback, progress/mastery, recommendations and cold-start diagnostic/intake. Wire the Assessment Agent and Learning Coach through the workflow. Keep all mutations server-side; persist sessions/interactions/mastery in SQLite; retain BKT and deterministic verification. Provide a documented local dev command and environment example without secrets.  
**Exit gate:** a fresh learner can ingest supported materials, ask a grounded question, open a citation, answer a question, receive verified feedback, and see a persisted topic-level state/recommendation. Browser walkthrough at normal desktop and mobile widths; no fake dashboard data or unconnected controls.

### Chat 3 — evaluation, hardening, demo and submission package
**Branch:** `overhaul/chat-03-evaluation-submission`, based on accepted Chat 2 head.  
**Goal:** prove, package and demonstrate the system against organizer criteria.  
**Tasks:** run regression/unit/API/browser tests; repair critical defects; execute the known-locator/off-material evaluation set; report faithfulness, answer relevancy, context precision/recall using a named framework or documented equivalent; run multi-session simulated learners and report mastery gains/repetition rate; add error cases, security checks, setup instructions, architecture/grounding/BKT docs, evaluation outputs, demo script and 3–10 minute recording checklist. Confirm the frontend/backend hosting story honestly. Do not fabricate or manually inflate scores.  
**Exit gate:** reproducible test/evaluation artifacts, actual results and limitations, successful end-to-end walkthrough, documented demo link once user records/uploads it, and final submission checklist. External video upload and portal submission require user authorization/actions.

## Mandatory acceptance gates

- [ ] PDF/textbook and slide ingestion with page/slide provenance.
- [ ] Video/transcript path with timestamps, or a clearly disclosed limitation and tested supported route.
- [ ] Figure/diagram content is extracted or an explicit unsupported state is shown; never silently pretend OCR/vision worked.
- [ ] Citations open the exact source locator.
- [ ] Off-material query abstains or clearly separates outside knowledge.
- [ ] Assessment types: MCQ, short answer, numerical; validated answer key, source/topic/difficulty and duplicate checks.
- [ ] BKT/mastery updates after both assessments and tutoring interactions, with evidence that update is correct.
- [ ] Cold-start diagnostic/intake.
- [ ] RAG evaluation metrics and multi-session learner metrics are reproducible and honestly labelled.
- [ ] Responsive usable interface, no fake data, no dead controls, no secrets exposed.
- [ ] Fresh setup instructions, dependency lock, tests and a 3–10 minute demo plan.
- [ ] Git history and existing branches preserved; no implementation merge to main until explicit final acceptance.

## Automated workflow and tool choice

**Preferred local executor: Antigravity (AG)** for these three bounded prompts because it can edit the local repository and run the actual Windows test/browser workflow. Use Cursor instead only if AG cannot reliably execute commands or preserve repository state; do not split the same task across both agents concurrently. v0 is a UI code-generation tool, not the project orchestrator. ChatGPT maintains the plan, reviews evidence, and reconciles GitHub documentation.

At the start of each chat the executor must: fetch remote refs; inspect status/branch/HEAD; read all control docs and relevant source/tests; verify organizer requirements; create/switch only to the designated phase branch; protect dirty work; and produce a pre-change report. At the end: run tests and build checks, inspect diffs/secrets, commit and push only that phase branch, verify remote HEAD, update the phase report and continuity docs, and state any human-only action. If a gate fails, fix it within the same chat rather than silently proceeding. No waiting for approval at every minor step; pause only for destructive actions, credentials, external publication, or a genuine architecture blocker.

## The only three executor prompts

### PROMPT 1 — Agno foundation
You are the local implementation executor for the existing CogniVault repository. Read `docs/FINAL_OVERHAUL_PLAN.md` and all listed project control documents, `docs/CHAT0_TECHNICAL_LOCK.md`, `docs/PRIOR_ART_AND_POSITIONING.md`, the organizer Track D PDF/requirements available in the repository or supplied local files, and the existing app, tests, dependencies, evaluation and data. GitHub is canonical. Preserve all code, data, tests, documents, user PDFs, and branches. Do not touch main implementation, force-push, reset, delete/rename branches, or close/merge PR #1. Inspect every remote head before selecting the best preserved implementation baseline. Create/use only `overhaul/chat-01-agno-foundation` for changes. Implement the smallest complete Agno AgentOS + local Ollama + SQLite/FTS5/ChromaDB evidence-tutor path that reuses existing source/retrieval contracts, exact page/slide/timestamp locators, deterministic sufficiency/abstention and citation validation. Keep existing Streamlit code as a working historical path. Add dependency/config/run instructions and tests. No mandatory paid APIs, no secrets in source, no invented features. Run actual tests and API smoke tests; fix failures rather than weaken assertions. Commit/push this branch, verify remote SHA, update its implementation report and handoff. End with exact changed files, commands, test output, known gaps and Chat 2 starting SHA. Do not start Chat 2 in this run.

### PROMPT 2 — v0 frontend and learning loop
Continue the same CogniVault repository from the freshly verified accepted Chat 1 remote HEAD and read `docs/FINAL_OVERHAUL_PLAN.md`, `docs/CHAT01_AGNO_FOUNDATION_REPORT.md`, all current control documents and organizer requirements. The exact reconciled prompt is maintained at `docs/CHAT02_EXECUTION_PROMPT.md`. Preserve the existing Streamlit path, evidence contracts, prior code/tests/data, all branches and PR #1. Create/use only `overhaul/chat-02-product-loop` from accepted Chat 1 HEAD. **Chat 02 is one integrated phase combining both backend intelligence and frontend work; do not split these into separate chats.** Use v0 to generate/refine and commit real responsive Next.js + TypeScript + Tailwind frontend code, not a static mockup. Connect it to Agno AgentOS through typed API contracts. In the same phase expose assessment generation/selection, structural/source/answer-key verification, answer submission/scoring/feedback and duplicate prevention; expose deterministic BKT updates and durable SQLite learner state, misconception diagnosis/remediation, prerequisite-aware recommendations and cold-start diagnostic/intake using existing domain logic. Implement actual course/material ingestion, grounded tutor with clickable exact citations, MCQ/short-answer/numerical practice, progress/mastery and recommendations. Keep mutations server-side; no fake dashboard data or unconnected controls. Use Ollama/local embeddings by default and keep hosted free-tier providers optional. Provide safe env examples and reproducible Windows run commands. Run backend regression and targeted API tests, frontend lint/type/build, integration tests and actual desktop/mobile browser walkthrough; fix failures. Commit/push only this branch, verify remote SHA, update report/continuity docs and list remaining acceptance gaps. Do not start Chat 3.

### PROMPT 3 — prove, harden and package
Continue from the accepted Chat 2 remote SHA. Read `docs/FINAL_OVERHAUL_PLAN.md`, organizer requirements, all project governance docs, implementation reports and current code/tests. Preserve all history and branches; no force-push, reset, deletion, branch renames, PR #1 merge/closure, or unapproved repository visibility changes. Create/use only `overhaul/chat-03-evaluation-submission` from accepted Chat 2 HEAD. Run the complete regression suite, frontend checks, API/integration tests and end-to-end browser walkthrough. Build/execute a reproducible team test set with known page/slide/timestamp locators and off-material questions; report faithfulness, answer relevancy, context precision and context recall using RAGAS or a clearly documented equivalent. Run multi-session simulated learner profiles and report mastery gains and question repetition rate. Include failures, confidence/limitations and exact commands; never fabricate metrics or claim test success without output. Fix critical defects, verify citations and abstention, assessment correctness and BKT persistence, inspect secrets/dependencies/accessibility/responsiveness, and produce architecture, grounding, learner-model, setup, evaluation, demo script and 3–10 minute recording checklist. Verify branch and remote SHA, update all continuity docs, create final report and state precisely what is ready versus what still requires the user's video recording/portal submission. Do not merge to main or publish/change repository visibility without explicit approval.

## Human-only actions and honest limits

The executor must not claim to have recorded/uploaded a YouTube video or submitted the hackathon portal unless the user explicitly completes/authorizes that action and provides evidence. A private repository may fail an organizer's public-repository requirement; do not change visibility silently—flag it for explicit user approval in Chat 3. A free public always-on backend is not assumed. Do not include proprietary or user-sensitive content in public demo data.

## Final status

This document locks the plan, technology choices, history-preservation rules, acceptance gates, and the only three executor prompts. It does not assert that the overhaul is implemented or that the project is already submission-ready.

---

## Chat 02 completion and Chat 03 execution handoff (2026-10-13)

The Chat 02 implementation report is available at [`docs/CHAT02_PRODUCT_LOOP_REPORT.md` on `overhaul/chat-02-product-loop`](https://github.com/SujitSaiY2007/CogniVault/blob/overhaul/chat-02-product-loop/docs/CHAT02_PRODUCT_LOOP_REPORT.md). The reported Chat 02 commit is `4917668f0e93ed6851c50341768631ada7e943ce`; GitHub branch comparison confirmed the remote branch matched that commit at reconciliation time. The report records 127 Python tests passing and a successful Next.js build; these results were not rerun as part of this documentation handoff.

**The exact next executor prompt is [`docs/CHAT03_EXECUTION_PROMPT.md`](https://github.com/SujitSaiY2007/CogniVault/blob/main/docs/CHAT03_EXECUTION_PROMPT.md).** It requires Chat 03 to rerun the baseline suite and frontend build before edits, verify the live Chat 02 head, and work only on `overhaul/chat-03-evaluation-submission` branched from that head. It explicitly addresses the Chat 02 Playwright limitation: HTTP integration checks are not a browser walkthrough; Chat 03 must produce real automated browser evidence or a clearly labelled manual desktop/mobile walkthrough with screenshots.

Chat 03 is responsible for reproducible grounding/abstention/citation evaluation, multi-session learner simulations and repetition metrics, security/UX hardening, actual evidence artifacts, and the final demo/submission checklist. Do not merge implementation to `main`, alter repository visibility, or claim a video upload or portal submission without actual evidence. Preserve all historical code, data, PDFs, branches, PR #1, and commit history.
