# Cognivault

**Evidence-First Adaptive Learning**

> A personalized tutoring system that grounds course answers in source evidence, adapts assessment to learner mastery, detects likely learning misconceptions, and evaluates its own reliability.

## Hackathon

**Track D — Personalized Tutoring & Adaptive Learning**

## Project Status

**Phase:** Chat 01 — Multimodal Knowledge Foundation  
**Status:** COMPLETE & VERIFIED — ready for Chat 02  
**Repository:** SujitSaiY2007/CogniVault  
**Default branch:** main  
**Verified development branch:** `chat01-evidence-foundation`  
**Verified ending commit:** `424ad5617e3d8461e468ddd59d5771decde5e9fe`

GitHub is the canonical source of truth.

## Chat 0 Technical Lock

The authoritative foundation specification is:

- docs/CHAT0_TECHNICAL_LOCK.md
- docs/PRIOR_ART_AND_POSITIONING.md

These documents define the locked MVP, architecture, evidence model, tutor behavior, assessment verification, BKT learner model, misconception policy, evaluation methodology, security boundary, demo flow, and chat sequence.

## Core Product Loop

Course Materials → Multimodal Evidence Extraction → Source-Linked Knowledge Base → Evidence Retrieval → Grounded Tutor → Verified Adaptive Assessment → Learner Model / Misconception Signals → Personalized Next Action → Updated Learner State

## Chat 01 Verified Foundation

Chat 01 is complete and locally verified with **40/40 tests passing in 8.69s**, including the K1–K10 acceptance harness.

Implemented foundation:
- PDF page-level evidence
- PPTX slide-level evidence
- timestamped video transcript evidence
- first-class embedded image/figure evidence
- topic/concept/prerequisite relations
- SQLite FTS5 BM25 retrieval
- persisted semantic embeddings
- deterministic hybrid retrieval
- machine-readable retrieval traces
- exact source/provenance resolution
- fail-closed unsupported-query behavior

See `docs/CHAT01_IMPLEMENTATION_STATUS.md` for the detailed verification record.

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

## Development Rule

No phase is considered complete merely because code exists. A phase is complete only when implementation, automated tests, acceptance tests, documentation, and Git history are verified, with no known blocker.

## Chat 02 — Intelligence Core

Building on the verified Chat 01 foundation, Chat 02 will implement:
- evidence sufficiency gate
- citation-grounded tutor response engine
- question generation and verification
- Bayesian Knowledge Tracing (BKT)
- misconception signals and targeted remediation

Chat 02 must preserve all Chat 01 tests and must add executable acceptance tests for every new requirement.

## Developer Usage

### Environment Setup
```bash
python -m venv .venv
# Windows:
.venv\\Scripts\\activate
# Linux/macOS:
source .venv/bin/activate

pip install -e .
```

### Test Execution
```bash
pytest -v
```

### Core APIs
The existing `app/` modules expose ingestion, retrieval, and provenance APIs. Chat 02 must build on these contracts rather than replacing them.

## Secrets

Never commit `.env` or credentials.

## Prior Art

CogniVault uses established ideas including RAG, multimodal extraction, intelligent tutoring, Bayesian Knowledge Tracing, adaptive assessment and LLM-based feedback. The project does not claim these techniques as inventions. Any stronger novelty claim must be supported by evidence.
