# CogniVault — Devpost Submission Guide & Project Description

**Hackathon:** Multimodal AI Hackathon 2026 (IIT Mandi KamandPrompt, Augli.ai, PurpleRain Tech, LDV Labs)  
**Track:** Track D — Personalized Tutoring & Adaptive Learning  
**Live Frontend:** [https://cogni-vault.vercel.app](https://cogni-vault.vercel.app)  
**Live Backend API:** [https://cognivault-backend-znn4.onrender.com](https://cognivault-backend-znn4.onrender.com)  
**GitHub Repository:** [https://github.com/SujitSaiY2007/CogniVault](https://github.com/SujitSaiY2007/CogniVault)  

---

## 1. Project Title & Tagline

- **Project Title:** CogniVault: Source-Grounded Multimodal AI Study Companion with Bayesian Learner Modeling
- **Elevator Pitch (Tagline):** An autonomous, fail-closed AI learning companion that unifies course PDFs, slide decks, and lecture notes into a verifiable knowledge graph with exact physical citations, deterministic assessment verification, and Bayesian Knowledge Tracing.

---

## 2. Devpost Long-Form Project Description

### 🌟 Inspiration
In higher education, students study across fragmented materials: 500-page textbook PDFs, 80-slide presentation decks, and multi-hour recorded lectures. When students ask general AI chatbots (like ChatGPT or Claude) for homework or exam help, they encounter two fundamental failures:
1. **Unverifiable Hallucination:** The model produces plausible-sounding explanations that do not match the assigned syllabus, citing nonexistent textbook pages or phantom slide numbers.
2. **Zero Learner Modeling:** General chatbots treat every prompt in isolation. They have no concept of whether a student has mastered Newtonian mechanics before attempting rotational dynamics, frequently causing cognitive overload.

We built **CogniVault** to answer a fundamental question: *Can an AI tutor be made mathematically accountable to the student's actual course materials and their individual learning journey?*

---

### 🚀 What It Does
CogniVault is an end-to-end, source-grounded intelligent study companion designed specifically around Track D requirements:

1. **Multimodal Knowledge Base with Provenance Integrity:**
   - Ingests university textbooks (PDF), slide decks (PPTX), and lecture notes without requiring manual preprocessing.
   - Computes SHA-256 cryptographic provenance hashes and maps every concept to physical locators: exact PDF page numbers, slide indices, or video timestamps.
   - Preserves formulas, diagrams, and structural hierarchy across modalities.

2. **Source-Grounded Evidence Tutor & Fail-Closed Abstention:**
   - Answers questions strictly using indexed course evidence with clickable physical locator pills (`[Physics Mechanics: Page 1]`). Clicking any citation displays the exact verified source excerpt.
   - **Fail-Closed Abstention:** When asked out-of-domain or off-topic queries (e.g. *"What is the capital of France?"*), the tutor refuses to guess and triggers an unambiguous abstention banner: *"Course does not contain sufficient evidence to answer."*

3. **Adaptive Assessment with Deterministic Verifier:**
   - Generates customized quizzes across student-selected scope (MCQ, Short Answer, Numerical) tagged by difficulty and source location.
   - Features an AST-based Deterministic Question Verifier that validates mathematical formulas and numerical tolerances, paired with a repetition suppression filter so students never receive duplicate questions.
   - Delivers claim-by-claim evaluation with targeted citations and misconception diagnosis.

4. **Longitudinal Learner Modeling with Bayesian Knowledge Tracing (BKT):**
   - Implements true Bayesian Knowledge Tracing ($P(L_t)$ updated via Bayes' rule on every interaction) rather than heuristic LLM guessing.
   - Enforces **Prerequisite Gating:** dependent topics remain locked until prerequisite concepts achieve $\ge 70\%$ mastery.
   - Flags persistent misconceptions ($\ge 2$ consecutive errors on a concept) and recommends targeted foundational review.

---

### 🛠️ How We Built It (Architecture & Tech Stack)

CogniVault is engineered around an evidence-first, bounded multi-agent architecture:
- **Agent Orchestration:** Powered by the **Agno AgentOS** framework with bounded, role-specific agents (`EvidenceTutorAgent`, `AssessmentAgent`, `LearningCoachAgent`).
- **Dual Hybrid Retrieval:** A calibrated fusion engine combining **SQLite FTS5 (BM25)** lexical search with **ChromaDB** dense vector embeddings, balanced by our empirical $0.45 \times \text{lexical} + 0.55 \times \text{semantic}$ score.
- **Sufficiency Gate:** A mathematical pre-flight evaluator enforcing minimum relevance thresholds and concept term coverage before tutor generation.
- **Learner Model:** A standalone Python BKT engine tracking $P(L_0)$, $P(T)$, $P(S)$, and $P(G)$ across topics.
- **Frontend UI:** Modern responsive web application built with **Next.js 14**, **TypeScript**, **Tailwind CSS**, and **Lucide React**, deployed globally on **Vercel**.
- **Backend API:** High-performance asynchronous API built with **FastAPI**, **Uvicorn**, and **PyMuPDF**, deployed on **Render** Linux containers.

---

### ⚖️ Honest Evaluation & Engineering Trade-offs (+ss and -ss)

Judges respect honest, reproducible engineering. Here is our transparent self-assessment:

#### Strengths (+ss):
- **100% Citation Addressability:** Every tutor answer and assessment feedback links to an existing, verifiable physical locator (21/21 verified in automated benchmarks).
- **Strict Fail-Closed Abstention:** Zero hallucination on out-of-domain probes (100% rejection rate on ungrounded queries).
- **Mathematical Rigor:** True BKT equations ensure longitudinal mastery curves do not suffer from prompt drift or context window degradation.
- **100% Free Zero-Installation Cloud Deployment:** Organizers and judges can evaluate the full live system immediately with zero setup or paid API provisioning.
- **Comprehensive Test Suite:** 143 passing automated tests covering unit, integration, security, and benchmark evaluations.

#### Limitations & Future Engineering (-ss):
- **Deterministic Heuristic Synthesis Fallback:** In zero-installation mode on free cloud tiers without an external LLM running, our tutor synthesizes plain-language answers directly from extracted definition blocks. While completely grounded and accurate, it prioritizes precision over creative conversational prose.
- **Complex Table & Diagram OCR:** While text and presentation layouts parse flawlessly, multi-column tables and low-contrast scanned PDFs require specialized OCR preprocessing.
- **Cold-Start Learner Priors:** New students without prior interaction history start from a default diagnostic prior ($P(L_0) = 0.10$) until sufficient assessment data is collected.

---

### 🚧 Challenges We Overcame
1. **512MB RAM Cloud Container Limits:** Running heavy deep learning transformer models in free cloud environments caused out-of-memory container crashes. We resolved this by implementing an adaptive try/except fallback and moving vector embeddings to non-blocking background workers (`BackgroundTasks`), reducing upload response latency to under 300ms.
2. **Ephemeral Disk Auto-Seeding:** Free container restarts wipe the local filesystem. We implemented an automatic corpus boot-seeder that indexes core science materials on startup in ~0.5s so judges never arrive at an empty app.
3. **Dependency Version Harmonization:** Resolved subtle sub-dependency conflicts between `google-genai`, `chromadb`, `tenacity`, and `websockets` to ensure reproducible single-command builds.

---

### 🏆 Accomplishments We're Proud Of
- 143 passing automated tests with 100% pass rate.
- Simulated multi-session student studies showing $+0.8917$ mastery progression with $0.0\%$ question repetition.
- Completely seamless zero-installation cloud deployment across Vercel and Render.
- Strict compliance with all Track D requirements and all 5 optional enhancements.

---

### 🔮 What's Next for CogniVault
- Multi-lingual audio tutoring support with real-time speech-to-speech interaction (Hindi and regional Indian languages).
- Visual Course Flow graph rendering using interactive WebGL nodes.
- Canvas and Blackboard LMS LTI integration for automatic gradebook synchronization.

---

## 3. "Built With" Tags & Tool Disclosures

### Software & Cloud Technologies
- `Python 3.12`
- `FastAPI`
- `Agno AgentOS`
- `Next.js 14`
- `TypeScript`
- `Tailwind CSS`
- `SQLite FTS5`
- `ChromaDB`
- `SentenceTransformers`
- `PyMuPDF`
- `python-pptx`
- `Pytest`
- `Vercel`
- `Render`

---

## 4. AI Tools Policy Disclosure (Mandatory Hackathon Compliance)

In strict accordance with the **Multimodal AI Hackathon 2026 AI Tools Policy**:

> *"AI coding assistants are allowed with no restrictions... You must disclose it: list the AI tools you used in Built With and note in your README which parts of the project were AI-assisted."*

### AI Tools Used
- **Google Antigravity IDE (Gemini 2.5/Flash AI pair programmer):** Used as an interactive agentic development environment for code scaffolding, test case authoring, and automated cloud deployment verification.
- **Agno Agent Framework:** Used for bounded agent wrappers and tool execution dispatching.
- **v0 / Tailwind Component Templates:** Used for initial UI card and dashboard layout prototypes.

### Detailed Demarcation of AI Assistance vs. Human Engineering
| Component | Development Method | Description |
|---|---|---|
| **Bayesian Knowledge Tracing (BKT) Engine** | **Human Engineered** | Mathematical derivation of prior, slip, guess, transition update formulas and prerequisite gating logic. |
| **Sufficiency Gate & Abstention** | **Human Engineered** | Dual-threshold formula ($0.45 \times \text{lexical} + 0.55 \times \text{semantic}$), stop-word boundary rules, and fail-closed logic. |
| **Deterministic Question Verifier** | **Human Engineered** | AST structural parsing, numerical tolerance regex, and repetition suppression filters. |
| **FastAPI REST Endpoints & Routers** | **AI-Assisted** | Boilerplate router declarations, Pydantic schema validation, and OpenAPI documentation generated with Antigravity IDE. |
| **Test Suite Expansion (143 Tests)** | **AI-Assisted** | Parametrized unit and integration tests generated under strict human-defined acceptance criteria. |
| **Frontend Component Styling** | **AI-Assisted** | Tailwind CSS utility classes and Lucide React iconography styled with Antigravity IDE assistance. |

*The submission team is 100% responsible for all code submitted and is prepared to explain and defend every architectural decision during technical evaluation.*
