# Cognivault

**Evidence-First Adaptive Learning**

> A personalized tutoring system that grounds course answers in source evidence, adapts assessment to learner mastery, detects likely learning misconceptions, and evaluates its own reliability.

## Hackathon

**Track D — Personalized Tutoring & Adaptive Learning**

## Project Status

**Phase:** Chat 02 — Intelligence Core  
**Status:** COMPLETE & VERIFIED — ready for Chat 03  
**Repository:** SujitSaiY2007/CogniVault  
**Default branch:** main  
**Active branch:** chat02-intelligence-core  

GitHub is the canonical source of truth.

## Technical Lock

The authoritative technical specifications are:

- docs/CHAT0_TECHNICAL_LOCK.md
- docs/CHAT01_IMPLEMENTATION_STATUS.md
- docs/CHAT02_IMPLEMENTATION_STATUS.md
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
- DECISION_LOG.md — locked decisions and rationale (D-001 to D-035).
- REQUIREMENTS_TRACEABILITY.md — requirement → implementation → test mapping.
- ARCHITECTURE.md — system architecture.
- TEST_SPECIFICATION.md — acceptance tests (G1–G5, A1–A4, L1–L3, S1–S2).
- HALLUCINATION_CONTROL.md — grounding and abstention policy.
- SECURITY_AND_USAGE_POLICY.md — secrets, privacy and usage controls.
- EVALUATION_PROTOCOL.md — benchmark methodology.
- DEMO_PLAN.md — demo sequence.
- SUBMISSION_PLAN.md — final audit and submission checklist.
- docs/CHAT0_TECHNICAL_LOCK.md — authoritative technical specification.
- docs/CHAT01_IMPLEMENTATION_STATUS.md — Chat 01 status report.
- docs/CHAT02_IMPLEMENTATION_STATUS.md — Chat 02 status report.
- docs/PRIOR_ART_AND_POSITIONING.md — prior-art and competitive-positioning record.
- app/ — application code (ingestion, retrieval, tutor, sufficiency, assessment, BKT, misconceptions, recommendations).
- tests/ — automated/acceptance tests (75 passing tests covering K1–K10 and G1–G5, A1–A4, L1–L3, S2).
- evaluation/ — evaluation artifacts area (benchmark runner in Chat 03).
- data/ — corpus/evaluation data area.

## Secrets

Copy .env.example to a local .env file and supply credentials locally. Never commit .env.

## Prior Art

Cognivault uses established ideas including RAG, multimodal extraction, intelligent tutoring, Bayesian Knowledge Tracing, adaptive assessment and LLM-based feedback.

The project does not claim these techniques as inventions. Any stronger project-specific novelty claim must be supported by evidence.

## Developer Usage

### 1. Environment Setup & Installation
```bash
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -e .
```

### 2. Test Execution
Run all 75 automated unit and acceptance tests (K1–K10, G1–G5, A1–A4, L1–L3, S2):
```bash
pytest -v
```

### 3. Ingestion & Retrieval (Knowledge Foundation)
```python
from app.db import EvidenceDB
from app.ingest import ingest_pdf, ingest_pptx, ingest_transcript
from app.retrieval import HybridRetriever, build_embeddings
from app.source_resolver import resolve

db = EvidenceDB("cognivault.sqlite")

# Ingest multimodal learning material
pdf_sid = ingest_pdf("textbook.pdf", db)
pptx_sid = ingest_pptx("lecture.pptx", db)
vid_sid = ingest_transcript("transcript.txt", db)

# Build embeddings and query
build_embeddings(db)
retriever = HybridRetriever(db)
results, trace = retriever.search("Newton second law", k=5, mode="hybrid")

# Resolve provenance
if results:
    prov = resolve(results[0].evidence_id, db)
    print(prov["source_title"], prov["location"], prov["text"])
```

### 4. Grounded Tutor & Sufficiency Gate
```python
from app.tutor import GroundedTutor
from app.sufficiency import check_sufficiency

tutor = GroundedTutor(db)

# Grounded query with citations
resp = tutor.answer("What is Newton's Second Law?")
print("Answer:", resp.answer)
for c in resp.citations:
    print(f"Citation: {c.evidence_id} ({c.modality}) -> {c.location}")

# Off-material query (abstains automatically)
off_resp = tutor.answer("Quantum teleportation black hole")
print("Unsupported?", off_resp.support_status == "unsupported")
```

### 5. Verified Assessment & Corrective Feedback
```python
from app.assessment import AssessmentEngine
from app.models import Difficulty, LearnerSubmission, QuestionOption

engine = AssessmentEngine(db)

# Create & verify question
q = engine.build_and_verify_question(
    question_id="q_math_01",
    topic_id="Algebra",
    prompt="What is the quadratic formula?",
    expected_answer="A",
    evidence_ids=[results[0].evidence_id],
    difficulty=Difficulty.medium,
    options=[
        QuestionOption(key="A", text="x = (-b +- sqrt(b^2 - 4ac)) / (2a)"),
        QuestionOption(key="B", text="x = -b / 2a")
    ],
    solution="The quadratic formula solves ax^2 + bx + c = 0."
)

# Adaptive question selection with repetition suppression
selected_q = engine.select_adaptive_question("Algebra", served_question_ids=["q_prev"])

# Evaluate submission
sub = LearnerSubmission(learner_id="student_1", question_id="q_math_01", topic_id="Algebra", answer="B")
eval_res = engine.evaluate_submission(sub, q)
print("Correct?", eval_res.is_correct)
print("Feedback:", eval_res.feedback)
```

### 6. BKT Learner Modeling, Misconceptions & Recommendations
```python
from app.learner_model import LearnerStateManager
from app.misconceptions import MisconceptionDetector
from app.recommendation import AdaptiveRecommendationEngine

# Update Bayesian Knowledge Tracing state
mgr = LearnerStateManager(db)
mastery = mgr.record_response("student_1", "Algebra", is_correct=False)
print(f"Topic Mastery: {mastery.p_mastery:.4f} (Attempts: {mastery.attempts})")

# Misconception tracking (triggers on repeated errors)
detector = MisconceptionDetector(db, error_threshold=2)
signal = detector.analyze_attempt("student_1", "Algebra", "Quadratic Roots", is_correct=False)
if signal:
    print("Misconception Detected:", signal.suspected_misconception)
    print("Remediation Concept:", signal.remediation_concept_id)

# Targeted next-action recommendation
rec_engine = AdaptiveRecommendationEngine(db)
rec = rec_engine.recommend("student_1", active_topic_id="Algebra")
print("Recommended Action:", rec.recommended_action)
print("Difficulty:", rec.difficulty)
print("Rationale:", rec.rationale)
```

## Next Phase

**Chat 3 — Product & Evaluation**

Building on the verified Intelligence Core, Chat 3 will implement:
- Multi-view Streamlit UI (`app/ui/`) for course setup, evidence explorer, grounded tutor, adaptive assessment, learner profile, and recommendations.
- Automated benchmark evaluation runner (`evaluation/runner.py`).
- Scripted simulated learner benchmarks and metric reports.
