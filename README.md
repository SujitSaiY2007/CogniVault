# Cognivault

Evidence-First Adaptive Learning

> A personalized tutoring system that grounds course answers in source evidence, adapts assessment to learner mastery, detects likely misconceptions, and evaluates its own reliability.

## Hackathon Track
Track D — Personalized Tutoring & Adaptive Learning

## Project Status
Phase: Chat 0 — Project Lock & Foundation
Repository: SujitSaiY2007/CogniVault
Default branch: main

This repository is the single source of truth for the project. Implementation decisions, requirements, tests, evaluation results, and demo/submission artifacts are version-controlled here.

## Core Product Loop
Course Materials → Multimodal Evidence Extraction → Source-Linked Knowledge Base → Evidence Retrieval → Grounded Tutor → Verified Adaptive Assessment → Learner Model / Misconception Signals → Personalized Next Action → updated learner state

## Planned MVP
1. Multimodal ingestion for textbooks/slide decks and selected lecture-video content.
2. Source-linked evidence with page, slide, figure, and timestamp metadata where applicable.
3. Evidence-first tutor with explicit citations and safe abstention for unsupported questions.
4. Adaptive assessments tagged by topic, source, and difficulty.
5. Verification of generated questions and answers before presentation.
6. Per-topic learner mastery estimates.
7. Misconception signals and targeted revision recommendations.
8. Evaluation benchmark covering grounding, faithfulness, relevancy, personalization, and question repetition.
9. Polished Streamlit demo interface.
10. Lightweight usage controls with secrets kept outside the repository.

## Initial Learning Domain
The current product direction is school-level Mathematics and Science because these subjects provide strong opportunities to demonstrate equations and numerical reasoning, diagrams and figures, prerequisite relationships, conceptual and quantitative assessment, multimodal source grounding, and measurable mastery changes.

English/Hindi interaction may be added as an optional capability if time permits; it is not a dependency of the core MVP.

## Non-Goals
- Claiming that the underlying techniques are unprecedented.
- Training a custom foundation model.
- Adding multi-agent complexity without a measurable benefit.
- Presenting unsupported model knowledge as course-grounded fact.
- Committing API keys, passwords, or personal credentials.
- Fabricating evaluation results.

## Grounding & Safety Principle
Cognivault cannot honestly promise that an LLM will never hallucinate. Instead, the system is designed around an evidence-first, zero-unsupported-answer policy for course-grounded responses:
1. Retrieve evidence first.
2. Check whether the evidence is sufficient.
3. Require source mapping for grounded answers.
4. Abstain or clearly flag when the material does not support the answer.
5. Never fabricate citations or source locations.
6. Verify generated assessment questions and answer keys before showing them.
7. Prefer deterministic checking for numerical answers where practical.
8. Fail closed when retrieval, verification, or citation mapping fails.

## Repository Map
- PROJECT_MASTER_PLAN.md — locked project plan and phase structure.
- PROJECT_STATE.md — current implementation state and verified status.
- CURRENT_OBJECTIVE.md — exact objective for the active phase.
- CURRENT_HANDOFF.md — continuation state for the next chat/agent session.
- DECISION_LOG.md — important decisions and rationale.
- REQUIREMENTS_TRACEABILITY.md — hackathon requirement → implementation → test mapping.
- TEST_SPECIFICATION.md — acceptance tests defined before completion claims.
- ARCHITECTURE.md — system architecture and data flow.
- HALLUCINATION_CONTROL.md — evidence, abstention, and verification policy.
- SECURITY_AND_USAGE_POLICY.md — secrets, accounts, quotas, and usage controls.
- EVALUATION_PROTOCOL.md — benchmark methodology and metrics.
- DEMO_PLAN.md — final 3–10 minute demo sequence.
- SUBMISSION_PLAN.md — final submission checklist.
- docs/ — detailed project documentation.
- app/ — application code.
- tests/ — automated and acceptance tests.
- evaluation/ — evaluation datasets, runners, and reports.

## Development Rule
No phase is considered complete merely because code exists. A phase is complete only when its acceptance criteria, tests, documentation, and Git state have been verified and recorded.

## Secrets
Copy .env.example to a local .env file and supply credentials locally. Never commit .env.

## License
License will be selected before public release/submission according to hackathon requirements and project ownership.