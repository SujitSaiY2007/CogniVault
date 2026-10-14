# CogniVault — Evidence-First Adaptive Learning

**Multimodal AI Hackathon 2026 · Track D: Personalized Tutoring & Adaptive Learning**  
**Repository:** [https://github.com/SujitSaiY2007/CogniVault](https://github.com/SujitSaiY2007/CogniVault)  
**Live Public Application:** Deploying on Vercel (Frontend) & Render (Backend)

> CogniVault is an evidence-first, source-grounded intelligent learning companion that unifies lecture videos, textbooks, and slide decks into a physical-locator-cited knowledge base, running grounded tutoring and adaptive assessments with exact page/slide/timestamp locators, deterministic abstention, and per-topic Bayesian Knowledge Tracing.

---

## Key Features

1. **Multimodal Evidence Ingestion:** Ingests textbook PDFs, PPTX slide decks, video transcripts, and diagrams with SHA-256 provenance manifests and physical locators (PDF page, PPTX slide, video timestamp).
2. **Dual Hybrid Retrieval:** Fuses lexical BM25 (SQLite FTS5) with dense semantic vector search (ChromaDB) with deterministic fusion scoring ($0.45 \times \text{lexical} + 0.55 \times \text{semantic}$).
3. **Deterministic Abstention Gate:** Evaluates evidence confidence and essential concept coverage before tutor generation. Unsupported queries trigger fail-closed refusal with zero hallucination.
4. **Agno AgentOS Multi-Role Architecture:** Specialized agents for Grounded Evidence Tutoring, Assessment Verification, and Learning Coaching.
5. **Adaptive Assessment:** Validates MCQ, short-answer, and numerical items against course evidence with structural verification and repetition suppression.
6. **Bayesian Knowledge Tracing (BKT):** Tracks latent mastery $P(L_t)$ per topic with prerequisite gating ($\ge 0.70$) and misconception diagnostics ($\ge 2$ repeated errors).
7. **Dual Runtime:** Modern responsive Next.js 14 frontend (`frontend/`) and preserved historical Streamlit 9-view workspace (`app/ui/main.py`).

---

## System Architecture

```
Course Materials (PDF, PPTX, Video, Images)
  → Multimodal Ingestion & SHA-256 Provenance (app/ingest.py)
  → Normalized Evidence Units with Physical Locators (Page, Slide, Timestamp)
  → Hybrid Indexing: SQLite FTS5 (BM25) + ChromaDB (Dense Vectors)
  → Deterministic Evidence Sufficiency Gate (Relevance & Term Coverage) (app/sufficiency.py)
  → Agno Grounded Tutor Agent (Local Ollama / Cloud Adapter / Fail-Closed Abstention)
  → Claim-by-Claim Citation Verification & Source Resolver (app/source_resolver.py)
  → Verified Adaptive Assessment & Bayesian Knowledge Tracing (BKT) (app/assessment.py, app/learner_model.py)
  → Misconception Diagnostics & Targeted Prerequisite Remediation (app/misconceptions.py)
```

---

## Quickstart & Local Setup

### 1. Prerequisites
- Python 3.12+
- Node.js 18+ & npm
- Ollama (for local offline mode) with `ollama pull llama3.2:latest`

### 2. Backend Setup
```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\activate   # Linux/macOS: source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Configure environment (optional, defaults to local Ollama)
cp .env.example .env
```

### 3. Start Agno AgentOS Backend Server
```powershell
python -m uvicorn app.agent_os.app:app --host 0.0.0.0 --port 8000
```
- API Health Check: `http://localhost:8000/health`
- Swagger Documentation: `http://localhost:8000/docs`

### 4. Start Next.js Frontend
```powershell
cd frontend
npm install
npm run dev
```
- Frontend application: `http://localhost:3000`

### 5. (Alternative) Launch Preserved Streamlit UI
```powershell
streamlit run app/ui/main.py
```
- Streamlit application: `http://localhost:8501`

---

## Automated Tests & Empirical Evaluation

```powershell
# Run complete automated test suite (138 tests)
pytest -v --durations=10

# Build Next.js frontend production bundle
cd frontend; npm run build; cd ..

# Run deterministic grounding benchmark
python -m evaluation.runner

# Run multi-session learner simulations
python -m evaluation.simulate_learners
```

### Empirical Verification Summary
- **Automated Tests:** 138 passing tests across unit, integration, and security suites.
- **Grounding Benchmark:** Precision = 1.0, Recall = 1.0, F1 = 1.0, Faithfulness = 0.9688.
- **Citation Addressability:** 21/21 physical citations verified against source locators (100%).
- **Multi-Session Simulations:** 6 distinct profiles verified: Progressing ($+0.8917$ gain), Struggling, Misconception remediation, Prerequisite gating ($\ge 0.70$), 0.0% question repetition.
- **Security Tests:** 8/8 passing tests covering learner isolation, file upload caps, and path traversal protection.

---

## Repository Governance & Preservation
- **PR #1 (`chat01-evidence-foundation`):** Strictly preserved open and untouched.
- **Historical Branches:** All phase branches (`main`, `chat01-evidence-foundation` through `chat06-ui-repair`, and `overhaul/chat-01` through `chat-03`) are preserved in commit history.
- **Zero Paid Mandatory APIs:** Runs 100% locally and privately with local Ollama, with optional cloud model adapter for hosted deployments.
