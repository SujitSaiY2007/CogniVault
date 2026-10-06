# Cognivault

**Evidence-First Adaptive Learning**

> A personalized tutoring system that grounds course answers in source evidence, adapts assessment to learner mastery, detects likely learning misconceptions, and evaluates its own reliability.

## Hackathon

**Track D — Personalized Tutoring & Adaptive Learning**

## Project Status

**Phase:** Chat 0 — Project Lock & Foundation  
**Status:** LOCKED — ready for Chat 1  
**Repository:** SujitSaiY2007/CogniVault  
**Default branch:** main

GitHub is the canonical source of truth.

## Chat 0 Technical Lock

The authoritative foundation specification is:

- docs/CHAT0_TECHNICAL_LOCK.md
- docs/PRIOR_ART_AND_POSITIONING.md

These documents define the locked MVP, architecture, evidence model, tutor behavior, assessment verification, BKT learner model, misconception policy, evaluation methodology, security boundary, demo flow, and chat sequence.

## Core Product Loop

Course Materials → Multimodal Evidence Extraction → Source-Linked Knowledge Base → Evidence Retrieval → Grounded Tutor → Verified Adaptive Assessment → Learner Model / Misconception Signals → Personalized Next Action → Updated Learner State

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
- DECISION_LOG.md — locked decisions and rationale.
- REQUIREMENTS_TRACEABILITY.md — requirement → implementation → test mapping.
- ARCHITECTURE.md — system architecture.
- TEST_SPECIFICATION.md — acceptance tests.
- HALLUCINATION_CONTROL.md — grounding and abstention policy.
- SECURITY_AND_USAGE_POLICY.md — secrets, privacy and usage controls.
- EVALUATION_PROTOCOL.md — benchmark methodology.
- DEMO_PLAN.md — demo sequence.
- SUBMISSION_PLAN.md — final audit and submission checklist.
- docs/CHAT0_TECHNICAL_LOCK.md — authoritative Chat 0 technical specification.
- docs/PRIOR_ART_AND_POSITIONING.md — prior-art and competitive-positioning record.
- docs/ — detailed documentation.
- app/ — application code; currently scaffold only.
- tests/ — automated/acceptance tests; currently scaffold only.
- evaluation/ — evaluation artifacts; currently scaffold only.
- data/ — corpus/evaluation data area; currently scaffold only.

## Development Rule

No phase is considered complete merely because code exists.

A phase is complete only when:

- implementation is present,
- automated tests pass,
- acceptance tests are executed,
- documentation is updated,
- no known blocker remains,
- Git history records the work,
- PROJECT_STATE and CURRENT_HANDOFF are updated.

## Secrets

Copy .env.example to a local .env file and supply credentials locally. Never commit .env.

## Prior Art

Cognivault uses established ideas including RAG, multimodal extraction, intelligent tutoring, Bayesian Knowledge Tracing, adaptive assessment and LLM-based feedback.

The project does not claim these techniques as inventions. Any stronger project-specific novelty claim must be supported by evidence.

## Chat 01 Developer Usage

### 1. Environment Setup & Installation
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -e .
```

### 2. Test Execution
Run all automated unit and acceptance tests (K1–K10):
```bash
pytest -v
```

### 3. Evidence Ingestion
Ingest textbooks, slide decks, and lecture transcripts into SQLite:
```python
from app.db import EvidenceDB
from app.ingest import ingest_pdf, ingest_pptx, ingest_transcript

db = EvidenceDB("cognivault.sqlite")

# Ingest PDF textbook (extracts text chunks and figures with page provenance)
pdf_source_id = ingest_pdf("textbook.pdf", db)

# Ingest PPTX slide deck (extracts slide text and embedded images with slide provenance)
pptx_source_id = ingest_pptx("lecture.pptx", db)

# Ingest lecture transcript (supports [mm:ss], [hh:mm:ss], mm:ss formats)
vid_source_id = ingest_transcript("transcript.txt", db)
```

### 4. Embedding Indexing
Generate and persist embeddings in SQLite:
```python
from app.retrieval import build_embeddings

# Persists normalized embeddings into SQLite without committed binaries
build_embeddings(db)
```

### 5. Deterministic Hybrid Retrieval
Query using SQLite FTS5 lexical search, semantic embeddings, or deterministic hybrid fusion:
```python
from app.retrieval import HybridRetriever

retriever = HybridRetriever(db)
results, trace = retriever.search("Newton second law", k=5, mode="hybrid")

for r in results:
    print(r.evidence_id, r.score, r.location, r.snippet[:100])

# Machine-readable retrieval trace
print("Unsupported:", trace.unsupported, "Reason:", trace.reason)
```

### 6. Exact Provenance Resolution
Resolve any retrieved evidence ID back to its original source location:
```python
from app.source_resolver import resolve

provenance = resolve(results[0].evidence_id, db)
print(provenance["source_path"], provenance["location"], provenance["text"])
```

## Next Phase

**Chat 2 — Intelligence Core**

Building on the verified Chat 01 evidence foundation, Chat 2 will implement:
- Grounded tutor response engine with evidence citation mapping.
- Evidence sufficiency gate and explicit abstention.
- Question generation and deterministic/model-assisted verification.
- Bayesian Knowledge Tracing (BKT) per-topic learner model.
- Misconception signal detection and targeted remediation recommendations.

