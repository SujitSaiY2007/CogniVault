# Cognivault — Project Master Plan

## 1. Locked Identity

**Project:** Cognivault  
**Track:** D — Personalized Tutoring & Adaptive Learning  
**Positioning:** Evidence-first adaptive learning system.

The hackathon project is separate from any academic research project. No academic project title is to be substituted for this identity.

## 2. Product Goal

Build a working tutoring system that can ingest multimodal learning material, answer questions using source-linked evidence, generate and verify adaptive assessments, maintain a per-topic learner model, detect likely misconceptions, and recommend the next learning action.

## 3. Product Principles

- Evidence before generation.
- Abstain when evidence is insufficient.
- Every grounded claim must map to a real source location.
- Generated assessments must be verified before presentation.
- Personalization must be measurable rather than cosmetic.
- Evaluation results must come from executed tests.
- Prior art and established techniques must be distinguished from project-specific engineering contributions.
- Simplicity is preferred over unnecessary agent or infrastructure complexity.

## 4. MVP Scope

### Must Have
1. Course-material ingestion.
2. Source-linked evidence representation.
3. Retrieval.
4. Grounded tutor.
5. Unsupported/off-material handling.
6. Adaptive assessment.
7. Question/answer verification.
8. Learner mastery state.
9. Misconception signals.
10. Personalized recommendations.
11. Evaluation benchmark.
12. Polished demo UI.
13. Secure local configuration and usage controls.
14. Complete README and demo instructions.

### Conditional / Stretch
- Video timestamp grounding.
- Visual/diagram question answering.
- Mixed-language interaction.
- Course flow visualization.
- Audio tutoring.
- Spaced-repetition scheduling.

Stretch features must never destabilize the MVP.

## 5. Initial Domain

School-level Mathematics and Science.

English/Hindi is an optional interaction enhancement, not a core corpus requirement.

## 6. Execution Phases

### Chat 0 — Project Lock & Foundation
Lock requirements, architecture, corpus strategy, testing, evaluation, security, prior-art positioning, repository governance, and acceptance criteria.

### Chat 1 — Multimodal Knowledge Foundation
Implement ingestion, extraction, evidence units, metadata, indexing, and retrieval.

### Chat 2 — Intelligence Core
Implement grounded tutoring, assessment generation/verification, learner model, misconception signals, and adaptive recommendations.

### Chat 3 — Product & Evaluation
Implement polished UI, dashboards, simulated learner sessions, benchmark runners, and measured evaluation.

### Chat 4 — Final Audit & Submission
Run full audit, fix defects, finalize README, demo, evaluation report, and submission package.

### Emergency Buffer
Reserved only for integration, dependency, API, evaluation, or demo failures.

## 7. Completion Rule

A phase is complete only when:
- implementation is present,
- automated tests pass,
- acceptance tests are executed,
- documentation is updated,
- no known blocker remains,
- Git history records the work,
- PROJECT_STATE and CURRENT_HANDOFF are updated.

## 8. Prior-Art Rule

Cognivault will use established ideas where useful, including RAG, multimodal extraction, adaptive assessment, knowledge tracing, and LLM tutoring. The repository must not claim these techniques as inventions. Any project-specific contribution must be described as engineering/product integration unless independently verified as novel.

## 9. Final Success Condition

Success is determined by the actual benchmark and end-to-end demonstration, not by an assumed result. Claims in the final submission must be traceable to repository evidence.
