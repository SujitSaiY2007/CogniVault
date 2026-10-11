# CogniVault

**Evidence-First Adaptive Learning with Agno AgentOS**

> A personalized tutoring system that unifies lecture videos, textbooks, and slide decks into a source-cited knowledge base, running grounded tutoring and adaptive assessments with exact page/slide/timestamp locators, deterministic abstention, and per-topic mastery modeling.

## Hackathon

**Track D — Personalized Tutoring & Adaptive Learning**  
**Multimodal AI Hackathon 2026** (KamandPrompt, IIT Mandi, Augli.ai, PurpleRain Tech, LDV Labs)

## Project Status

**Phase:** Overhaul Chat 01 — Agno AgentOS & Local-First Foundation  
**Status:** COMPLETE & VERIFIED (118/118 tests passing green, Agno AgentOS REST API operational, local Ollama integration with zero paid API requirement and deterministic offline fallback, ChromaDB persistent vector store integrated with SQLite/FTS5 hybrid retrieval, Evidence Tutor Agent operational with exact physical locators and fail-closed abstention, historical Streamlit 9-view application shell fully preserved and passing).  
**Repository:** `SujitSaiY2007/CogniVault`  
**Default Branch:** `main`  
**Active Overhaul Branch:** `overhaul/chat-01-agno-foundation`  

GitHub is the canonical source of truth.

---

## Technical Architecture & Overhaul Plan

The authoritative architectural specifications and project control documents are:

- `docs/FINAL_OVERHAUL_PLAN.md` — Authoritative technical overhaul plan (Chat 01 to Chat 04).
- `docs/CHAT01_AGNO_FOUNDATION_REPORT.md` — Chat 01 Agno foundation implementation report.
- `docs/CHAT0_TECHNICAL_LOCK.md` — Historical technical specification and MVP boundaries.
- `docs/PRIOR_ART_AND_POSITIONING.md` — Prior-art analysis and competitive positioning.
- `ARCHITECTURE.md` — System architecture and data flow.
- `REQUIREMENTS_TRACEABILITY.md` — Track D requirement to code/test traceability matrix.

---

## Dual Runtime Architecture

CogniVault supports two concurrent, fully integrated runtimes:

1. **Agno AgentOS REST API (`app/agent_os/`):**
   - Autonomous agent runtime powered by Agno AgentOS.
   - Grounded Evidence Tutor Agent powered by local Ollama (`llama3.2:latest`, `mistral`) with zero-cost, private execution and deterministic offline fallback.
   - Hybrid dense vector search with ChromaDB alongside SQLite FTS5 BM25 lexical search ($0.45 \times \text{lexical} + 0.55 \times \text{semantic}$).
   - FastAPI REST endpoints for health, sources, hybrid search, tutor queries, and vector synchronization.

2. **Historical Streamlit Web UI (`app/ui/`):**
   - Complete 9-view interactive learning workspace (`Home`, `Courses`, `Add Materials`, `AI Tutor`, `Practice`, `My Progress`, `Recommendations`, `Evidence Explorer`, `Evaluation`).
   - Verified via in-memory `streamlit.testing.v1.AppTest`.

---

## Core Product Loop

```
Course Materials (PDF, PPTX, Video, Images)
  → Multimodal Ingestion & SHA-256 Provenance
  → Normalized Evidence Units with Physical Locators (Page, Slide, Timestamp)
  → Hybrid Indexing: SQLite FTS5 (BM25) + ChromaDB (Dense Vectors)
  → Deterministic Evidence Sufficiency Gate (Relevance & Term Coverage)
  → Agno Grounded Tutor Agent (Local Ollama LLM / Fail-Closed Abstention)
  → Claim-by-Claim Citation Verification & Source Resolver
  → Verified Adaptive Assessment & Bayesian Knowledge Tracing (BKT)
  → Misconception Diagnostics & Targeted Prerequisite Remediation
```

---

## Grounding & Safety Principles

1. **Evidence First:** Grounded answers are generated only from retrieved course materials.
2. **Deterministic Abstention:** If evidence confidence or key term coverage is insufficient, the system explicitly abstains rather than producing an ungrounded hallucination.
3. **Exact Physical Locators:** Citations must reference actual physical pages, slides, or timestamps. Locators are never fabricated.
4. **Citation Verification:** Every substantive claim must overlap with and map directly to an addressable evidence unit.
5. **Verified Assessments:** Generated quizzes and practice problems are structurally verified before presentation to the learner.
6. **Zero Mandatory Paid APIs:** Inference runs locally via Ollama; vector storage runs locally via ChromaDB and SQLite; embedding runs locally via Sentence Transformers.

---

## Developer Usage & Setup

### 1. Environment Setup & Installation
```powershell
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
pip install -e .
```

### 2. Configure Environment (Optional)
Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```
Default configuration runs entirely local:
```env
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:latest
CHROMA_PERSIST_DIR=data/chroma
AGENTOS_HOST=0.0.0.0
AGENTOS_PORT=8000
```

### 3. Launch the Agno AgentOS REST API Server
```powershell
python -m uvicorn app.agent_os.app:app --host 0.0.0.0 --port 8000
```
- Interactive API Documentation: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`
- Tutor Query Endpoint: `POST http://localhost:8000/api/v1/tutor/query`

### 4. Launch the Historical Streamlit Web UI
```powershell
streamlit run app/ui/main.py
```
- Interactive UI: `http://localhost:8501`

### 5. Run the Automated Test Suite (118 Tests)
```powershell
pytest -v --durations=10
```

### 6. Run Deterministic Benchmark Evaluation
```powershell
python -m evaluation.runner
python -m evaluation.simulate_learners
```

---

## Repository Governance

- **PR #1 (`chat01-evidence-foundation`):** Open/draft baseline. Preserved without closing, merging, or rebasing.
- **Branches:** Historical branches (`main`, `chat01-evidence-foundation`, `chat02-intelligence-core`, `chat03-product-evaluation`, `chat04-final-demo-submission`, `chat05-ui-overhaul`, `chat06-ui-repair`) are strictly preserved.
- **Active Branch:** All changes for this phase reside exclusively on `overhaul/chat-01-agno-foundation`.
