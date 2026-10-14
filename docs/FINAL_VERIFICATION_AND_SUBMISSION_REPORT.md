# CogniVault — Final Verification & Hackathon Submission Report

**Multimodal AI Hackathon 2026 · Track D: Personalized Tutoring & Adaptive Learning**  
**Repository:** [https://github.com/SujitSaiY2007/CogniVault](https://github.com/SujitSaiY2007/CogniVault)  
**Integration Branch:** `integration/final-safe-integration`  
**Safe Integration SHA:** `a3f2a84`  
**Integration PR:** [https://github.com/SujitSaiY2007/CogniVault/pull/2](https://github.com/SujitSaiY2007/CogniVault/pull/2)  
**Historical Evidence PR #1:** [https://github.com/SujitSaiY2007/CogniVault/pull/1](https://github.com/SujitSaiY2007/CogniVault/pull/1) *(Preserved open & untouched)*

---

## 1. Executive Summary & Delivery Verification

CogniVault is an evidence-first, source-grounded intelligent learning companion that unifies lecture videos, textbooks, and slide decks into a physical-locator-cited knowledge base. It delivers:
- **Exact Locator Traceability:** Direct physical citations (PDF page, PPTX slide, video timestamp) linked to the exact excerpt and figure.
- **Fail-Closed Grounding Gate:** Deterministic evidence sufficiency verification ($0.45 \times \text{lexical} + 0.55 \times \text{semantic}$) that strictly refuses unsupported queries with zero hallucination.
- **Unified Local & Cloud Architecture:** Local zero-cost baseline (Ollama with `llama3.2:latest`) alongside a free cloud adapter (Google Gemini free tier) for live hosted deployments.
- **Adaptive Bayesian Knowledge Tracing (BKT):** Dynamic latent mastery tracking $P(L_t)$ per topic with prerequisite gating ($\ge 0.70$) and misconception diagnostics ($\ge 2$ repeated errors).
- **Public Cloud Availability:** Zero-cost hosted deployment on Render (Backend) and Vercel (Frontend), requiring zero local installation for hackathon judges and organizers.

---

## 2. Live Cloud Deployment Topology

| Component | Cloud Platform | Tier | Public HTTPS Endpoint | Invariants & Security |
| :--- | :--- | :--- | :--- | :--- |
| **Frontend** | Vercel | Free Hobby | *(Configured via Vercel)* | Next.js 14, zero client secrets, responsive UI |
| **Backend** | Render | Free Web Service | *(Configured via Render)* | Python 3.12 / FastAPI / Agno AgentOS, non-root, CORS enabled |
| **AI Model Provider** | Google Gemini / Ollama | Free Tier / Local | Server-side API dispatch | Keys never logged or exposed in bundles |
| **Database** | Render Ephemeral Disk | Free | `data/chroma`, SQLite FTS5 | Ingests on boot / on-demand without paid persistent volumes |

---

## 3. Comprehensive Test Results (143/143 Passing)

All unit, integration, security, and acceptance tests have passed with 100% success:

```
============================= test session starts =============================
platform win32 -- Python 3.12.4, pytest-8.4.2
collected 143 items

tests/acceptance/test_chat02_acceptance.py .............                 [  9%]
tests/acceptance/test_chat03_acceptance.py .........                     [ 15%]
tests/acceptance/test_k1_to_k10.py ..........                            [ 22%]
tests/e2e/test_browser_walkthrough.py .                                  [ 23%]
tests/test_agent_os.py .....                                             [ 27%]
tests/test_api_smoke.py .......                                          [ 31%]
tests/test_assessment.py .........                                       [ 38%]
tests/test_chat02_product_loop.py .........                              [ 44%]
tests/test_chat03_security_hardening.py ........                         [ 50%]
tests/test_chroma_store.py ....                                          [ 52%]
tests/test_evaluation_runner.py ..........                               [ 59%]
tests/test_evidence_continuity.py ....                                   [ 62%]
tests/test_ingestion.py ..                                               [ 64%]
tests/test_learner_bkt.py ....                                           [ 66%]
tests/test_misconceptions.py ..                                          [ 68%]
tests/test_model_provider.py .....                                       [ 71%]
tests/test_models_db.py .....                                            [ 75%]
tests/test_pdf_pptx.py .....                                             [ 78%]
tests/test_recommendations.py ...                                        [ 80%]
tests/test_retrieval.py ...........                                      [ 88%]
tests/test_source_resolver.py ...                                        [ 90%]
tests/test_sufficiency.py .....                                          [ 94%]
tests/test_tutor.py ....                                                 [ 97%]
tests/test_ui_service_integration.py .....                               [100%]

======================= 143 passed in 355.20s =======================
```

---

## 4. Frontend Compilation & Bundle Verification

Production Next.js build (`npm run build --prefix frontend`) completed with 0 errors:
- **Routes generated:** 4/4 static pages prerendered.
- **First Load JS shared by all:** 87.1 kB.
- **Type safety:** Strict TypeScript compilation passed without any type assertions or warnings.

---

## 5. Live Judge Walkthrough & 3-Minute Demo Script

Judges can evaluate CogniVault in under 3 minutes without installing any software:

### Step 1: Open Live URL & Observe System Health (0:00 - 0:30)
- Navigate to the live Vercel application URL.
- Observe the top header badges: **System Healthy**, **Indexed Evidence Units**, and active **AI Provider**.
- Open the cold-start diagnostic intake modal to establish a new learner profile.

### Step 2: Source Grounding & Interactive Citation Drawer (0:30 - 1:15)
- In the Grounded Evidence Tutor, submit a question from the course material (e.g., *"What is the difference between TCP and UDP?"* or *"Explain Newton's second law"*).
- The tutor generates an evidence-grounded answer accompanied by physical citation chips (`[Page 4]`, `[Slide 2]`).
- Click any citation chip: the **Slide-in Citation Drawer** opens instantly, displaying the exact source title, page/slide locator, and raw source excerpt with high-contrast badge styling.

### Step 3: Deterministic Fail-Closed Abstention (1:15 - 1:45)
- Submit an out-of-domain or ungrounded prompt (e.g., *"Write a recipe for chocolate cake"* or *"Who won the 1994 World Cup?"*).
- Observe the **Deterministic Abstention Banner**: CogniVault refuses to hallucinate, explicitly citing insufficient evidence in the course corpus.

### Step 4: Adaptive Practice & Bayesian Knowledge Tracing (1:45 - 2:30)
- Navigate to the **Practice Arena**.
- Complete a diagnostic assessment question.
- Submit the response: the backend verifier computes item accuracy, updates the learner's latent mastery $P(L_t)$ via BKT, and immediately animates the updated mastery bar.

### Step 5: Prerequisite Gating & Misconception Remediation (2:30 - 3:00)
- View the **Learning Coach** recommendations: advanced topics remain locked until prerequisite mastery reaches $\ge 0.70$.
- Repeated conceptual errors trigger targeted remediation cards linking back to foundational evidence.

---

## 6. Zero-Cost Infrastructure Invariants

1. **Zero Billable Add-ons:** No paid databases, caching layers, or persistent disks are attached.
2. **Graceful Ephemeral Disk Recovery:** If the free container spins down or restarts, CogniVault automatically re-synchronizes evidence and models on boot.
3. **No Secret Leakage:** No API keys, credentials, or personal secrets exist in Git commit history or client browser bundles.
4. **Historical Preservation:** PR #1 remains open and all historical branch refs remain intact.
