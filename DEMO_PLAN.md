# CogniVault — Demo Plan, Walkthrough Script & Recording Package

**Project:** CogniVault — Evidence-First Adaptive Learning  
**Track:** Track D — Personalized Tutoring & Adaptive Learning  
**Target Duration:** 6–8 minutes (Hackathon Requirement: 3–10 minutes)  
**Entry Point:** `streamlit run app/ui/main.py` (Local URL: `http://localhost:8501`)  

---

## 1. Executive Summary & Hackathon Pitch (Track D)

> **"Generative AI tutors commonly suffer from three fatal flaws in education: they hallucinate facts without proving syllabus grounding, they blindly answer out-of-scope questions, and they lack principled learner state modeling. CogniVault solves this by closing the pedagogical loop with an evidence-first architecture: every response cites exact source locators (page, slide, timestamp), off-material queries trigger fail-closed abstention, assessment items undergo deterministic structural verification, and learner mastery is modeled via Bayesian Knowledge Tracing with prerequisite gating."**

---

## 2. Timed 6–8 Minute Demo Script

| Timecode | Demo Segment | Active View / Tab | Spoken Narrative & Key Actions | Expected Visible Outcomes |
| :---: | :--- | :--- | :--- | :--- |
| **0:00–0:45** | **1. The Problem & CogniVault 2.0 Overview** | `🏠 Overview & Dashboard` | *"Welcome to CogniVault 2.0. In personalized tutoring, generic LLMs fail learners when they fabricate equations, cannot point to the textbook, and have no memory of prerequisite mastery. CogniVault is built on one core rule: Evidence First. We start on our Learning Overview & Dashboard, which surfaces curriculum KPIs, active learner mastery, and prescribed next actions before diving into our seven specialized modules."* | CogniVault 2.0 premium light visual system, executive KPI metric cards, prescribed learning action card with prerequisite lock warning, quick-start shortcuts, and sidebar telemetry. |

| **0:45–1:45** | **2. Course Setup & Multimodal Ingestion** | `📥 1. Course Setup & Ingestion` | *"We begin by ingesting multimodal curriculum materials: textbook PDFs with vector diagrams, PPTX lecture slides with speaker notes, and timestamped video lecture transcripts. Clicking 'Re-Seed Default Corpus' or uploading documents parses content into atomic evidence units."* | Source table populates with 4 indexed files, SHA-256 checksums, and evidence unit counts. Manifest metadata expander shows provenance. |
| **1:45–2:45** | **3. Evidence Explorer & Exact Locators** | `🔍 2. Evidence Explorer` | *"In the Evidence Explorer, every chunk is an addressable unit linked to exact physical locators: Page numbers for PDFs, Slide numbers for presentations, and Timestamps for videos. Notice embedded figure `physics_mechanics:e00002`—diagrams are treated as first-class evidence."* | Search filter displays chunks. Badges show `📄 Page 1`, `📊 Slide 1`, `⏱️ Timestamp [00:01:15]`. Embedded visual free-body diagram renders cleanly. |
| **2:45–3:45** | **4. Grounded AI Tutor & Verified Citations** | `💬 3. Grounded AI Tutor` | *"Now we ask a syllabus question: 'What is Newton's second law of motion and its mathematical formula?' The sufficiency gate verifies coverage, formulates the grounded response, and returns exact citations. Clicking the citation links directly to the textbook locator."* | Green badge `🟢 Grounded in Course Evidence`. Response presents $F = ma$. Citation card expands showing `physics_mechanics:e00001` (PDF, Page 1) and exact quote. |
| **3:45–4:30** | **5. Fail-Closed Abstention (Off-Corpus)** | `💬 3. Grounded AI Tutor` | *"Now we test hallucination prevention with an off-curriculum question: 'What were the major economic causes of the French Revolution in 1789?' Rather than hallucinating facts outside the physics syllabus, CogniVault strictly abstains."* | Yellow warning banner `⚠️ Abstention Policy Triggered`. Transparent audit trace shows insufficient topic coverage (1/7 key terms found). Zero leakage, zero fake citations. |
| **4:30–5:30** | **6. Adaptive Assessment & BKT Transitions** | `📝 4. Adaptive Assessment` | *"Next is assessment. Questions must pass deterministic structural verification before presentation. Let's fetch an item for Newtonian Mechanics. When the student submits an answer, CogniVault provides evidence-backed feedback and updates topic mastery in real-time using Bayesian Knowledge Tracing."* | Verified question card renders. Correct submission shows green feedback banner, source evidence citation, and updated mastery $P(L)$ increasing from $0.10 \to 0.4333$. |
| **5:30–6:15** | **7. Learner Profile & Misconception Tracking** | `📊 5. Learner Mastery Profile` | *"In the Learner Profile, we see persisted skill mastery across topics and historical practice. If a student makes repeated errors on the same concept, the system accumulates error signals ($\ge 2$) to diagnose targeted misconceptions rather than penalizing isolated slips."* | Visual mastery progress bars ($P(L)$ bands), interaction logs, and active misconception signals for diagnostic profiles (`sim_misconception`). |
| **6:15–7:00** | **8. Recommendations & Prerequisite Gating** | `🎯 6. Recommendations & Prerequisites` | *"CogniVault's recommendation engine is fully explainable. It enforces prerequisite readiness gates: a student cannot advance to dependent topics ('Work and Energy') if prerequisite mastery ('Newtonian Mechanics') is unmastered ($< 0.70$). It prescribes targeted review with suggested evidence units."* | Recommended action card (`foundational_review`, `targeted_practice`, or `advance_topic`). Prerequisite topology table audits readiness status (`✅ Ready` or `❌ Blocked`). |
| **7:00–7:45** | **9. Empirical Benchmark & Evaluated Trajectories** | `🧪 7. Benchmark & Evaluation` | *"Finally, CogniVault evaluates itself empirically. Our deterministic benchmark tests 28 offline cases: 100% supported answer rate, 100% abstention rate, 0% leakage, and 21/21 resolvable citations. Tab 2 shows multi-turn simulated learner trajectories contrasting adaptive pacing with a fixed-difficulty baseline."* | Metric cards display live results matching `evaluation/benchmark_results.json`. Tab 2 renders simulated trajectory charts and comparison metrics. |
| **7:45–8:00** | **10. Wrap-Up & Boundaries** | Sidebar / Architecture Summary | *"CogniVault delivers a closed-loop, verifiable tutoring experience. We attribute prior art in RAG and BKT, emphasize that structural verification tests syntax rather than universal truth, and invite you to explore the open-source repository. Thank you!"* | Conclusion slide / final screen showcasing Track D readiness. |

---

## 3. Video Recording Preparation Checklist

### A. Environment Preparation
1. Ensure Windows virtual environment is active:
   ```powershell
   .\.venv\Scripts\activate
   ```
2. Verify test suite passes cleanly before recording:
   ```powershell
   pytest -v --durations=10
   ```
   *(Expected: 102 passed in ~25s).*
3. Launch Streamlit server:
   ```powershell
   streamlit run app/ui/main.py
   ```
4. Verify server terminal output confirms URL: `http://localhost:8501`.

### B. Browser & Screen Setup
- **Browser:** Chrome or Edge in dedicated window.
- **Resolution:** 1920x1080 (1080p) or 1280x720 (720p).
- **Zoom Level:** 100% (or 110% for optimal text readability).
- **Recording Software:** OBS Studio, Loom, or Windows Game Bar (`Win + G`).
- **Audio:** Clear microphone audio without background noise.

### C. Exact Ordered Interaction Sequence
1. **Module 1 (Course Setup):**
   - Click **"Re-Seed Default Corpus"** to show instant loading of the 4 standard STEM files.
   - Expand **"View Corpus Manifest & Provenance Details"** to show CC0-1.0 licensing and SHA-256 hashes.
2. **Module 2 (Evidence Explorer):**
   - Type `"Newton"` in the text search filter to demonstrate instant reactivity.
   - Point out `📄 Page 1` on PDF chunk and scroll to show the embedded SVG/PNG vector diagram.
3. **Module 3 (Grounded Tutor):**
   - Click preset button **"Direct: Newton's Law"** $\to$ Click **"Ask Tutor"**.
   - Show the grounded answer and expand the citation card.
   - Click preset button **"Off-Corpus: French Rev"** $\to$ Click **"Ask Tutor"**.
   - Show the fail-closed abstention banner and the sufficiency audit trace expander.
4. **Module 4 (Adaptive Assessment):**
   - Keep active topic as `Newtonian Mechanics`.
   - Click **"🎯 Fetch Next Adaptive Question"**.
   - Select option `B: F = m * a` $\to$ Click **"Submit Answer"**.
   - Show the green feedback banner, evidence citation, and updated BKT score ($0.4333$).
5. **Module 5 (Learner Mastery):**
   - Switch profile dropdown to `sim_advancing` to show high mastery ($0.9917$).
   - Switch to `sim_misconception` to show the active misconception warning.
6. **Module 6 (Recommendations):**
   - Show the pedagogical rationale card.
   - Scroll to the Prerequisite Readiness table to explain the $P(L) \ge 0.70$ gating rule.
7. **Module 7 (Benchmark & Evaluation):**
   - Point out the 28 evaluated test cases, 100% abstention, and 0% leakage.
   - Switch to **"🤖 Simulated Learner Trajectories"** tab to highlight the adaptive vs static difficulty trajectory comparison.

### D. Recovery Procedures
- If Streamlit displays a stale session warning, refresh the browser page (`Ctrl + R`).
- To reset practice questions in Assessment view, click **"🔄 Reset Served Questions"**.
- To reset database state completely, click **"Re-Seed Default Corpus"** in Module 1.

---

## 4. Track D Submission Text (For Devpost / Portal)

### Project Title
**CogniVault — Evidence-First Adaptive Learning**

### Short Description (Tagline)
*A personalized tutoring system that grounds course answers in verifiable source evidence, enforces fail-closed abstention, deterministically verifies assessment items, and adaptively models skill mastery using Bayesian Knowledge Tracing with prerequisite gating.*

### Track
**Track D — Personalized Tutoring & Adaptive Learning**

### Long Description
**Problem:**
Large language models are rapidly being integrated into education, but they routinely fabricate facts, cite non-existent textbook pages, answer queries far outside the curriculum, and lack pedagogical state tracking. In learning environments, a single hallucination can embed stubborn misconceptions.

**Solution:**
CogniVault implements an end-to-end, evidence-first adaptive tutoring architecture:
1. **Multimodal Knowledge Vault:** Ingests textbooks (PDF), slide decks (PPTX), and video lecture transcripts into atomic evidence units with exact physical locators (pages, slides, timestamps) and embedded figures.
2. **Sufficiency Gate & Grounded Tutor:** Evaluates query-evidence relevance before answering. If evidence is insufficient, it strictly abstains rather than hallucinating. Supported queries emit verified, source-addressable citations.
3. **Verified Adaptive Assessment:** Questions undergo deterministic structural verification (MCQ single-choice consistency, numerical tolerance bounds, evidence addressability) before presentation, preventing question repetition.
4. **Bayesian Knowledge Tracing (BKT) & Misconceptions:** Implements a hidden Markov learner model tracking skill mastery ($P(L)$) in real-time. Repeated error patterns ($\ge 2$) trigger targeted misconception diagnoses with remediation routing.
5. **Prerequisite Gating:** Enforces strict pedagogical policy: students cannot advance to dependent topics without achieving mastery ($P(L) \ge 0.70$) in prerequisite topics.
6. **Empirical Evaluation Suite:** 28 offline test cases measuring retrieval recall (100%), precision@3 (39.58%), supported answer rate (100%), abstention rate (100%), and zero leakage (0%), alongside 6 multi-turn simulated learner trajectories.

**Technologies Used:**
Python 3.12, Streamlit, SQLite (FTS5 + BM25), NumPy, PyMuPDF, python-pptx, Pytest, Pydantic.

---

## 5. Scientific Boundaries & Prior Art Attributions

- **Prior Art Attribution:** CogniVault utilizes established concepts in Retrieval-Augmented Generation (RAG), Bayesian Knowledge Tracing (Corbett & Anderson), and adaptive item selection. We do not claim these established frameworks as novel inventions.
- **Verification Scope:** Deterministic question verification confirms structural and syntactic integrity; it does not claim to prove universal external factual truth without subject-matter ground truth.
- **Abstention Claims:** Zero leakage on 3 benchmarked off-corpus test cases demonstrates effective gate tuning on the test set, not a theoretical zero-hallucination guarantee across all possible queries.
- **Learner Simulations:** Multi-turn simulations illustrate dynamic difficulty pacing across scripted personas; they do not claim unproven longitudinal learning gains in real human students.

---

## 6. Outstanding Manual Actions for Submitter

- [ ] Open `http://localhost:8501` and record the 6–8 minute walkthrough using the script in Section 2.
- [ ] Export video in MP4/WebM format and upload to YouTube (unlisted or public) or Google Drive.
- [ ] Paste repository URL (`https://github.com/SujitSaiY2007/CogniVault`) and demo video link into the hackathon submission form.
- [ ] Copy Section 4 pitch and description into the Devpost submission portal fields.
- [ ] Confirm submission before the hackathon deadline.
