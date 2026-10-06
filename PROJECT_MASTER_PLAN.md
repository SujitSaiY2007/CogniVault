# Cognivault — Project Master Plan

## 1. Locked Identity

**Project:** Cognivault  
**Track:** D — Personalized Tutoring & Adaptive Learning  
**Positioning:** Evidence-first adaptive learning system.

The hackathon project is separate from any academic research project.

## 2. Product Goal

Build a working course-grounded tutor that can ingest multimodal learning material, answer using source-linked evidence, generate and verify adaptive assessments, maintain interpretable per-topic learner state, detect likely learning misconceptions, and recommend the next learning action.

## 3. Locked Product Principles

- Evidence before generation.
- Abstain when evidence is insufficient.
- Every grounded claim must map to a real source location.
- Generated assessments must be verified before presentation.
- Personalization must be measurable rather than cosmetic.
- Evaluation results must come from executed tests.
- Established techniques must be attributed as prior art.
- Simplicity is preferred over unnecessary agents or infrastructure.
- No feature is complete until its acceptance test passes.

## 4. Locked MVP

### Must Have

1. PDF/textbook ingestion.
2. PPTX/slide ingestion.
3. Image/figure extraction within the implemented scope.
4. Lecture-video transcript/timestamp ingestion.
5. Source-linked evidence representation.
6. Hybrid lexical + semantic retrieval.
7. Evidence sufficiency gate.
8. Grounded tutor with exact source references.
9. Unsupported/off-material abstention.
10. Adaptive assessment.
11. Question and answer verification.
12. BKT-based per-topic mastery.
13. Evidence-based misconception signals.
14. Targeted next-action recommendations.
15. Reproducible evaluation benchmark.
16. Streamlit demo UI.
17. Secrets and quota controls.

### Stretch

Visual reasoning beyond extraction, rich video key-frame reasoning, English/Hindi interaction, audio tutoring, spaced repetition, and course-flow visualization.

Stretch features cannot delay the MVP.

## 5. Initial Domain

School-level Mathematics and Science.

English/Hindi is optional.

## 6. Architecture Lock

Python + Streamlit + SQLite/FTS5 + lightweight vector retrieval + one permitted LLM/multimodal provider + deterministic Python verification.

No microservices, Kubernetes, custom foundation-model training, or multi-agent orchestration unless a later measured requirement justifies it.

See docs/CHAT0_TECHNICAL_LOCK.md and ARCHITECTURE.md.

## 7. Execution Phases

### Chat 0 — Project Lock & Foundation
Complete. Lock requirements, architecture, corpus, evidence, tutoring, assessment, learner model, evaluation, security, prior art, tests, demo and repository governance.

### Chat 1 — Multimodal Knowledge Foundation
Implement source manifest, PDF/PPTX/video extraction, evidence objects, provenance, indexing and retrieval.

### Chat 2 — Intelligence Core
Implement grounded tutor, abstention, assessment generation/verification, BKT, misconception signals and recommendation policy.

### Chat 3 — Product & Evaluation
Implement polished UI, simulated learners, benchmark runner and measured evaluation.

### Chat 4 — Final Audit & Submission
Run clean setup, full tests, security audit, final evaluation, demo rehearsal and submission package.

## 8. Completion Rule

A phase is complete only when implementation, automated tests, acceptance tests, documentation, and Git state have been verified.

## 9. Prior-Art Rule

Cognivault uses established RAG, multimodal extraction, intelligent tutoring, knowledge tracing, adaptive assessment and LLM feedback techniques. It does not claim these as inventions.

Project-specific contribution claims must be phrased as integration or empirically measured improvement unless independent evidence supports a stronger claim.

## 10. Final Success Condition

Success is determined by executed acceptance tests, measured benchmark results, and a reproducible end-to-end demonstration—not by assumed results.
