# Cognivault

**Evidence-First Adaptive Learning**

> A personalized tutoring system that grounds course answers in source evidence, adapts assessment to learner mastery, detects likely learning misconceptions, and evaluates its own reliability.

## Hackathon

**Track D — Personalized Tutoring & Adaptive Learning**

## Project Status

**Phase:** Chat 03 — Product & Evaluation  
**Status:** IMPLEMENTATION COMPLETE & VERIFIED (98/98 tests passing, benchmark suite operational, simulated learner evaluations verified, Streamlit demo active)  
**Repository:** SujitSaiY2007/CogniVault  
**Default branch:** main  
**Active branch:** chat03-product-evaluation  

GitHub is the canonical source of truth.

## Technical Lock

The authoritative technical specifications are:

- docs/CHAT0_TECHNICAL_LOCK.md
- docs/CHAT01_IMPLEMENTATION_STATUS.md
- docs/CHAT02_IMPLEMENTATION_STATUS.md
- docs/CHAT03_IMPLEMENTATION_STATUS.md
- docs/PRIOR_ART_AND_POSITIONING.md

These documents define the locked MVP, architecture, evidence model, tutor behavior, assessment verification, BKT learner model, misconception policy, evaluation methodology, security boundary, demo flow, and chat sequence.

## Core Product Loop

Course Materials → Multimodal Evidence Extraction → Source-Linked Knowledge Base → Evidence Retrieval → Sufficiency Gate → Grounded Tutor → Verified Adaptive Assessment → Learner Model (BKT) / Misconception Signals → Personalized Next Action → Updated Learner State

## Locked MVP

1. PDF/textbook ingestion.
2. PPTX/slide ingestion.
3. Figure/image extraction within the implemented scope.
4. Lecture-video transcript/timestamp ingestion.
5. Source-linked evidence with page, slide and timestamp metadata.
6. Hybrid lexical + semantic retrieval.
7. Evidence sufficiency gate.
8. Grounded tutor with real citations.
9. Unsupported/off-material abstention.
10. Adaptive assessment.
11. Question and answer verification.
12. Per-topic BKT mastery estimates.
13. Evidence-based misconception signals.
14. Targeted next-action recommendations.
15. Reproducible evaluation benchmark.
16. Streamlit demo interface.
17. Secrets and usage/quota controls.

Stretch features must not destabilize the MVP.

## Initial Learning Domain

School-level Mathematics and Science.

English/Hindi interaction is optional and is not a dependency of the core MVP.

## Grounding & Safety Principle

Cognivault cannot honestly promise that an LLM will never hallucinate. Instead, the system follows an evidence-first, fail-closed policy:

1. Retrieve evidence first.
2. Check whether the evidence is sufficient.
3. Require source mapping for grounded answers.
4. Abstain or clearly flag when the material does not support the answer.
5. Never fabricate citations or source locations.
6. Verify generated assessment questions and answer keys before showing them.
7. Prefer deterministic checking for numerical/objective answers where practical.
8. Fail closed when retrieval, verification, citation mapping or provider services fail.

## Architecture

Python + Streamlit + SQLite/FTS5 + lightweight vector retrieval + one permitted LLM/multimodal provider + deterministic verification.

No unnecessary microservices, Kubernetes, custom foundation-model training or multi-agent orchestration.

## Repository Map

- PROJECT_MASTER_PLAN.md — project identity, MVP and phase plan.
- PROJECT_STATE.md — verified project state.
- CURRENT_OBJECTIVE.md — active objective and exit status.
- CURRENT_HANDOFF.md — precise continuation state.
- DECISION_LOG.md — locked decisions and rationale (D-001 to D-043).
- REQUIREMENTS_TRACEABILITY.md — requirement → implementation → test mapping.
- ARCHITECTURE.md — system architecture.
- TEST_SPECIFICATION.md — acceptance tests (G1–G5, A1–A4, L1–L3, S1–S2).
- HALLUCINATION_CONTROL.md — grounding and abstention policy.
- SECURITY_AND_USAGE_POLICY.md — secrets, privacy and usage controls.
- EVALUATION_PROTOCOL.md — benchmark methodology and metric formulas.
- DEMO_PLAN.md — 7-module interactive demo sequence.
- SUBMISSION_PLAN.md — final audit and submission checklist.
- docs/CHAT0_TECHNICAL_LOCK.md — authoritative technical specification.
- docs/CHAT01_IMPLEMENTATION_STATUS.md — Chat 01 status report.
- docs/CHAT02_IMPLEMENTATION_STATUS.md — Chat 02 status report.
- docs/CHAT03_IMPLEMENTATION_STATUS.md — Chat 03 status report.
- docs/PRIOR_ART_AND_POSITIONING.md — prior-art and competitive-positioning record.
- app/ui/ — Streamlit user interface (main.py + 7 views).
- app/ — application code (ingestion, retrieval, tutor, sufficiency, assessment, BKT, misconceptions, recommendations).
- tests/ — automated unit and acceptance tests (98 tests passing).
- evaluation/ — benchmark dataset, runner, and simulation evaluation suite.
- data/ — reproducible school Mathematics & Science corpus and manifest.

## Secrets

Copy .env.example to a local .env file and supply credentials locally. Never commit .env.

## Prior Art

Cognivault uses established ideas including RAG, multimodal extraction, intelligent tutoring, Bayesian Knowledge Tracing, adaptive assessment and LLM-based feedback.

The project does not claim these techniques as inventions. Any stronger project-specific novelty claim must be supported by evidence.

## Developer Usage

### 1. Environment Setup & Installation
```powershell
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -e .
```

### 2. Launch Streamlit UI Demo
```powershell
streamlit run app/ui/main.py
```

### 3. Run Test Suite
Run the complete automated test suite (98 tests):
```powershell
pytest -v --durations=10
```

### 4. Run Deterministic Benchmark Evaluation
```powershell
python -m evaluation.runner
python -m evaluation.simulate_learners
```
