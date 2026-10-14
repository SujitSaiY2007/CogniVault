# CogniVault — Architecture Reference

**Project:** CogniVault — Evidence-First Adaptive Learning  
**Hackathon Track:** Track D — Personalized Tutoring & Adaptive Learning  
**Repository:** `https://github.com/SujitSaiY2007/CogniVault`

---

## 1. Dual Runtime Architecture

CogniVault supports two concurrent, fully integrated runtimes:

```
                                  +----------------------------------------------------+
                                  |                  CogniVault User                   |
                                  +-------------------------+--------------------------+
                                                            |
                             +------------------------------+------------------------------+
                             |                                                             |
                             v                                                             v
              +------------------------------+                              +------------------------------+
              |    Historical Streamlit UI   |                              |         Agno AgentOS         |
              |     (app/ui/main.py: 8501)    |                              |   FastAPI Service (:8000)    |
              +--------------+---------------+                              +--------------+---------------+
                             |                                                             |
                             +------------------------------+------------------------------+
                                                            |
                                                            v
                                            +-------------------------------+
                                            |   Core Application Services   |
                                            +---------------+---------------+
                                                            |
                             +------------------------------+------------------------------+
                             |                              |                              |
                             v                              v                              v
               +---------------------------+  +---------------------------+  +---------------------------+
               |     Evidence Retrieval    |  |     Tutor & Verification  |  |    Learner & Adaptive     |
               | - SQLite FTS5 (Lexical)   |  | - Agno Agent (Ollama/Cloud|  | - BKT State Tracker       |
               | - ChromaDB (Semantic)     |  | - EvidenceGate (Abstain)  |  | - Misconception Engine    |
               | - Deterministic Fusion    |  | - Source Citation Resolver|  | - Prerequisite Navigator  |
               +-------------+-------------+  +-------------+-------------+  +-------------+-------------+
                             |                              |                              |
                             +------------------------------+------------------------------+
                                                            |
                                                            v
                                            +-------------------------------+
                                            |       Persistent Storage      |
                                            | - SQLite: cognivault.db       |
                                            | - ChromaDB: data/chroma/      |
                                            | - Source Assets: data/corpus/ |
                                            +-------------------------------+
```

1. **Next.js 14 Frontend (`frontend/`) + Agno AgentOS REST API (`app/agent_os/`):**
   - Modern, responsive TypeScript/Tailwind application with 8 modular interactive views (`Dashboard`, `Courses`, `Add Materials`, `AI Tutor`, `Practice`, `My Progress`, `Recommendations`, `Evaluation`).
   - Grounded Evidence Tutor Agent, Assessment Agent, and Learning Coach powered by Agno AgentOS.
   - Dual model provider adapter: zero-cost local Ollama (`llama3.2:latest`) for local development, with free-tier cloud provider adapter (Gemini) when configured for hosted deployment.
   - Hybrid retrieval fusing SQLite FTS5 BM25 lexical search with ChromaDB dense vector search.
   - Clickable citation drawer resolving directly to source physical locators.

2. **Historical Streamlit UI (`app/ui/main.py`):**
   - Preserved 9-view desktop/demonstration shell executing on `http://localhost:8501`.
   - Verified via in-memory `streamlit.testing.v1.AppTest`.

---

## 2. Core Application Pipeline

```
Course Materials (PDF, PPTX, Video, Images)
  → Multimodal Ingestion & SHA-256 Provenance (app/ingest.py)
  → Normalized Evidence Units with Physical Locators (Page, Slide, Timestamp)
  → Hybrid Indexing: SQLite FTS5 (BM25) + ChromaDB (Dense Vectors)
  → Deterministic Evidence Sufficiency Gate (Relevance & Term Coverage) (app/sufficiency.py)
  → Agno Grounded Tutor Agent (Local Ollama / Cloud Adapter / Fail-Closed Abstention) (app/agent_os/tutor_agent.py)
  → Claim-by-Claim Citation Verification & Source Resolver (app/source_resolver.py)
  → Verified Adaptive Assessment & Bayesian Knowledge Tracing (BKT) (app/assessment.py, app/learner_model.py)
  → Misconception Diagnostics & Targeted Prerequisite Remediation (app/misconceptions.py, app/recommendation.py)
```

---

## 3. Retrieval Engine & Provenance

- **Lexical Retrieval:** SQLite FTS5 `MATCH` queries ranked by Okapi BM25 combined with query term coverage.
- **Semantic Retrieval:** ChromaDB dense vector store with persistent storage and cosine similarity search.
- **Hybrid Fusion:** Deterministic linear combination: $0.45 \times \text{lexical} + 0.55 \times \text{semantic}$, with stable alphabetical tie-breaking on `evidence_id`.
- **Retrieval Trace:** Machine-readable trace capturing candidate count, result count, scores breakdown, rankings, source IDs, and fail-closed unsupported reasons.
- **Source Resolver:** Verifiable resolution from `evidence_id` back to exact source location, file path, SHA-256, and text/asset payload.

---

## 4. Grounding & Abstention Gate

- Generation is permitted only when retrieved evidence satisfies threshold relevance ($\ge 0.15$) and essential query term coverage ($\ge 35\%$).
- If evidence is insufficient, the system deterministically triggers fail-closed abstention with an explicit explanation rather than hallucinating answers.
- Every substantive factual claim is anchored to a verified citation pointing to a physical page, slide, or timestamp.

---

## 5. Learner Modeling & Adaptation

- **Bayesian Knowledge Tracing (BKT):** Latent skill mastery $P(L_t)$ per topic updated via analytical Bayes rule:
  $$P(L_{t+1} \mid \text{obs}) = \text{posterior} + (1 - \text{posterior}) \times P(T)$$
- **Misconception Detection:** Requires $\ge 2$ repeated errors on the same concept before diagnosing a misconception, linking directly to prerequisite evidence for targeted remediation.
- **Prerequisite Gating:** Enforces mastery thresholds ($\ge 0.70$) on prerequisite topics before unlocking dependent advanced topics.
- **Repetition Suppression:** Question fingerprinting suppresses previously served questions within the topic pool.

---

## 6. Failure Boundaries & Security

- **Provider Failure:** Explicit fallback / unavailable status; no fake responses.
- **Retrieval Insufficiency:** Fail-closed abstention banner with transparent audit reason.
- **Citation Mapping Failure:** Response rejected or ungrounded claims suppressed.
- **Question Verification Failure:** Question rejected from the pool before learner presentation.
- **Security Boundaries:** Learner ID regex validation, 25MB upload payload limits, filename sanitization, and header/body learner identity enforcement.
