# Cognivault Architecture

## Target Architecture

User
→ Streamlit UI
→ Application Services
→ Evidence / Retrieval Layer
→ LLM + Verification Layer
→ Learner Model
→ Persistent Storage

## Core Flow

Course source → ingestion → evidence units → lexical/semantic indexes → retrieval → evidence sufficiency → grounded tutor/assessment → verification → learner update → recommendation.

## Components

### 1. Ingestion

Accept PDF/textbook, PPTX/slides, images/figures, and selected lecture-video transcript/timestamp sources.

### 2. Evidence Store

Maintain:
- source_id,
- source metadata,
- evidence_id,
- source type,
- modality,
- extracted text,
- page/slide/timestamp locator,
- binary image assets (MIME type, SHA-256, width, height),
- topics, concepts, and directed prerequisite chains.

### 3. Retrieval Engine

- **Lexical Retrieval:** SQLite FTS5 `MATCH` queries ranked by Okapi BM25 combined with query term coverage.
- **Semantic Retrieval:** SQLite-persisted 32-bit float vector embeddings with dimension validation and model tracking.
- **Hybrid Fusion:** Deterministic linear combination: $0.45 \times \text{lexical} + 0.55 \times \text{semantic}$, with stable alphabetical tie-breaking on `evidence_id`.
- **Retrieval Trace:** Machine-readable trace capturing query, mode, candidate count, result count, scores breakdown, rankings, source IDs, and fail-closed unsupported reasons.
- **Source Resolver:** Verifiable resolution from `evidence_id` back to exact source location, path, SHA-256, and text/asset payload.

### 4. Evidence Gate

Generation is permitted only when retrieved evidence is relevant, sufficient, valid and addressable. Otherwise return an unsupported/insufficient-evidence state.

### 5. Tutor

Generate only from approved evidence in grounded mode and attach claim-supporting citations.

### 6. Assessment

Generate/select tagged questions from course evidence. Verify before display. Prefer deterministic checking for numerical and objective answers.

### 7. Learner Model

Use Bayesian Knowledge Tracing per topic/skill. Store mastery probability and interaction history.

### 8. Misconception Layer

Convert repeated/strong error patterns into likely misconception signals and map them to evidence-grounded remediation.

### 9. Recommendation

Use mastery, difficulty readiness, prerequisite readiness, recent errors, misconception signals and repetition history to select the next learning action.

### 10. Evaluation

Run fixed benchmark cases and simulated learner sessions. Store raw outputs and calculated metrics for reproducibility.

## Technology Boundary

- Python
- Streamlit
- SQLite
- SQLite FTS5
- lightweight vector store
- one permitted LLM/multimodal provider
- deterministic Python verification

No microservices, Kubernetes, custom model training, or multi-agent orchestration.

## Failure Boundaries

Provider failure → explicit unavailable state.  
Retrieval failure → insufficient evidence.  
Citation mapping failure → no grounded answer.  
Question verification failure → question rejected.  
Quota exceeded → explicit limit state.

## Source of Truth

docs/CHAT0_TECHNICAL_LOCK.md is the detailed Chat 0 architecture/behavior specification.
