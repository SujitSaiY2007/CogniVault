> **Historical copy / superseded phase handoff:** The canonical, current three-chat roadmap is on `main`: [FINAL_OVERHAUL_PLAN.md](https://github.com/SujitSaiY2007/CogniVault/blob/main/docs/FINAL_OVERHAUL_PLAN.md). The authoritative Chat 02 prompt is [CHAT02_EXECUTION_PROMPT.md](https://github.com/SujitSaiY2007/CogniVault/blob/main/docs/CHAT02_EXECUTION_PROMPT.md). This branch copy is retained for history; where its old Chat 2/Chat 3 wording differs, follow the canonical main roadmap. Chat 02 combines the Agno assessment/BKT/misconception/recommendation API work with the v0-generated Next.js frontend in one phase.

---

# CogniVault — Final Overhaul Plan: Agno AgentOS & Local-First Intelligence

**Status:** AUTHORITATIVE TECHNICAL OVERHAUL SPECIFICATION  
**Phase:** Multi-Chat Overhaul (Starting Chat 01)  
**Project:** CogniVault — Evidence-First Adaptive Learning  
**Hackathon Track:** Track D — Personalized Tutoring & Adaptive Learning  
**Canonical Repository:** `https://github.com/SujitSaiY2007/CogniVault`  
**Active Overhaul Branch:** `overhaul/chat-01-agno-foundation`  

---

## 1. Executive Summary & Architectural Motivation

CogniVault was established during Chat 0–Chat 04 as an evidence-first adaptive tutoring and assessment prototype adhering strictly to Hackathon Track D requirements. In the baseline system, core services (ingestion, hybrid SQLite/FTS5 retrieval, sufficiency evaluation, grounded tutoring, verified assessment, Bayesian Knowledge Tracing, misconception detection, and recommendations) were composed into a Streamlit interactive application.

This **Final Overhaul Plan** defines the production-grade architectural evolution of CogniVault to an **Agno AgentOS** foundation featuring:
1. **Agno AgentOS:** A modular, standards-based autonomous agent runtime and FastAPI service layer for grounded educational workflows.
2. **Local Ollama Intelligence:** Zero-mandatory-cost, private, and local LLM execution (defaulting to `llama3.2:latest`, `mistral`, or user-specified local models) with fail-closed deterministic fallback when offline. No mandatory paid APIs or credentials required.
3. **ChromaDB + SQLite/FTS5 Hybrid Storage:** Dense semantic retrieval powered by an embedded ChromaDB vector collection integrated with the existing SQLite FTS5 BM25 lexical engine, preserving exact deterministic fusion scoring ($0.45 \times \text{lexical} + 0.55 \times \text{semantic}$).
4. **Preserved Core Evidence Contracts:** Complete preservation of exact page/slide/timestamp physical locators, deterministic sufficiency gating, claim-by-claim citation verification, BKT learner modeling, and historical Streamlit UI capabilities.

---

## 2. Track D Compliance & Preserved Invariants

The system guarantees compliance with all Track D requirements across both the new AgentOS runtime and the preserved Streamlit UI:

| Track D Requirement | CogniVault Implementation | Preserved Contract |
|---|---|---|
| **1. Multimodal Knowledge Base** | Ingestion of PDF textbooks, PPTX slide decks, video transcripts, and diagram figures. | `SourceRecord`, `EvidenceUnit`, SHA-256 provenance manifests, exact locators (`page`, `slide`, `timestamp`). |
| **2. Source Grounding & Abstention** | Dual hybrid retrieval (FTS5 + ChromaDB), deterministic `EvidenceGate`, claim-level citation validation. | Fail-closed refusal for off-material queries; no hallucinated citations or synthetic facts. |
| **3. Adaptive Assessment** | Topic and difficulty tagged questions generated only from course evidence; structural verification. | Question schema with verified answer keys, misconception detection, and repetition suppression. |
| **4. Learner Model** | Bayesian Knowledge Tracing (BKT) tracking latent skill mastery $P(L_t)$ per topic; misconception accumulation ($\ge 2$ errors). | Persistent interaction logging, prerequisite gatekeeping, and personalized next-step recommendations. |
| **5. System Evaluation** | Deterministic benchmark runner (28 cases), simulated multi-turn learner profiles (6 scenarios). | Explicit mathematical formulas for precision, recall, faithfulness, and mastery progression. |

---

## 3. Dual Runtime Architecture

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
               | - SQLite FTS5 (Lexical)   |  | - Agno Agent (Ollama LLM) |  | - BKT State Tracker       |
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

---

## 4. Multi-Phase Implementation Roadmap

### Phase 1: Agno AgentOS & Retrieval Foundation (Chat 01 — This Phase)
- **Branch:** `overhaul/chat-01-agno-foundation`
- **Deliverables:**
  1. Add dependencies: `agno`, `chromadb`, `fastapi`, `ollama`, `openai` into `pyproject.toml` and lock in `requirements.txt`.
  2. Implement `app/chroma_store.py`: `ChromaEvidenceStore` providing persistent dense vector storage with exact locator metadata, filtering, and bidirectional SQLite synchronization.
  3. Integrate ChromaDB into `app/retrieval.py` (`HybridRetriever` supports ChromaDB semantic search alongside SQLite FTS5).
  4. Implement `app/ollama_provider.py`: Local Ollama integration with model configuration, health checks, and deterministic offline fallback.
  5. Implement `app/agent_os/`:
     - `tools.py`: Agno Agent tools for retrieval, sufficiency gating, citation verification, and locator resolution.
     - `tutor_agent.py`: Grounded Agno Evidence-Tutor Agent enforcing citation integrity and abstention.
     - `service.py`: High-level tutor service wrapping Agno Agent execution into the standard `TutorResponse` contract.
     - `app.py`: `AgentOS` instance and FastAPI REST application (`/health`, `/api/v1/tutor/query`, `/api/v1/evidence/search`, `/api/v1/sources`, `/api/v1/evidence/sync-chroma`).
  6. Automated test suite expansion: `tests/test_agent_os.py`, `tests/test_chroma_store.py`, and API smoke tests.
  7. Maintain 100% pass rate on all existing 102 tests.

### Phase 2: Intelligence Core on AgentOS (Chat 02)
- Multi-agent orchestration for assessment generation and verification.
- Agno tools for BKT learner state updates and misconception diagnostics.
- Prerequisite recommendation policy exposed via AgentOS REST endpoints.

### Phase 3: Product, Evaluation & Client Layer (Chat 03)
- Unified AgentOS client integration and interactive exploration.
- Benchmark runner integration with AgentOS tutor endpoints.
- Simulated learner evaluation executed over AgentOS agents.

### Phase 4: Final Demonstration, Rehearsal & Submission (Chat 04)
- Full end-to-end rehearsal with seed STEM corpus and local Ollama.
- Video demonstration recording and submission packet finalization.

---

## 5. Security, Secrets & Privacy Policy

1. **Zero Secret Leakage:** No API keys, credentials, or personal tokens are committed to source control or repository history.
2. **Local-First Privacy:** All ingestion, indexing, retrieval, and inference can run completely on the local workstation without data egress or paid API requirements.
3. **Preservation of Canonical Branches:** Branches `main`, `chat01-evidence-foundation`, `chat02-intelligence-core`, `chat03-product-evaluation`, `chat04-final-demo-submission`, `chat05-ui-overhaul`, and `chat06-ui-repair` remain untouched. PR #1 remains open/draft.

---

## 6. Verification & Acceptance Gates

A phase is accepted only when:
1. `pytest` executes and all tests (existing + new) pass with zero errors.
2. Live API endpoints respond to health, retrieval, and tutor query probes.
3. Citation locators are physically verifiable back to source material.
4. Unsupported off-corpus queries deterministically abstain without hallucination.
5. All file changes and test outputs are documented in the phase implementation report.
