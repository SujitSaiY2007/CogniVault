# Cognivault Architecture

## Target Architecture

User
→ Streamlit UI
→ Application Services
→ Evidence / Retrieval Layer
→ LLM + Verification Layer
→ Learner Model
→ Persistent Storage

## Core Components

### 1. Ingestion
Accept supported learning sources and transform them into source-linked evidence units.

### 2. Evidence Store
Maintain searchable evidence with provenance:
- source identifier,
- document/video title,
- page/slide/section,
- timestamp when applicable,
- extracted text,
- visual/figure reference when applicable.

### 3. Retrieval
Retrieve evidence for a learner query and expose the provenance needed by the answer layer.

### 4. Tutor
Generate an answer only after evidence sufficiency checks. The answer includes source references.

### 5. Assessment
Select or generate questions using learner state, topic, source, difficulty, and repetition history. Verification occurs before display.

### 6. Learner Model
Maintain per-topic mastery estimates and session evidence. The model should be simple enough to explain and evaluate.

### 7. Misconception Layer
Infer likely misunderstanding patterns from wrong answers and conversation signals, then map them to evidence-grounded remediation.

### 8. Evaluation
Run a fixed benchmark and simulated learner sessions. Store raw outputs and calculated metrics so reported results are reproducible.

## Technology Boundary

Initial preference:
- Python
- Streamlit
- SQLite
- ChromaDB or an equivalent lightweight vector store
- Gemini or another permitted LLM/multimodal model
- Standard Python libraries for deterministic verification

Technology may change only if the replacement materially improves reliability or required functionality.

## Architecture Rule

Do not introduce microservices, Kubernetes, custom model training, or multi-agent orchestration unless a measured requirement justifies the complexity.
