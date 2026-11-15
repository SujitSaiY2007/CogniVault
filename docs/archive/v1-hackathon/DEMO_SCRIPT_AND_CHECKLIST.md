# CogniVault Hackathon Demonstration Script & Verification Checklist

**Track:** Track D (Course Material Ingestion, Cognitive Grounding & Adaptive Learning)  
**Target Duration:** 3 – 5 minutes (Maximum allowed: 10 minutes)  
**Submission Package:** Live Next.js Web App (`:3000`) + AgentOS Backend (`:8000`) + Playwright Walkthrough Artifacts  

---

## 1. Pre-Demo Setup & Environment Launch (30 seconds)

### Required Terminal Commands
1. **Terminal 1: Start AgentOS Backend**
   ```powershell
   cd C:\Users\sujit\CogniVault
   .\.venv\Scripts\python.exe -m uvicorn app.agent_os.app:app --host 127.0.0.1 --port 8000
   ```
2. **Terminal 2: Start Next.js Frontend**
   ```powershell
   cd C:\Users\sujit\CogniVault\frontend
   npm run start -- -p 3000
   # Or for development: npm run dev
   ```
3. Open browser at: `http://localhost:3000`

---

## 2. Walkthrough Click-by-Click Script (3 - 5 Minutes)

### Step 1: System Badges & Architecture Overview (0:00 - 0:45)
- **Visual Action:** Observe the top navigation bar with live status indicators:
  - Database: `SQLite (Persistent)`
  - Vector Store: `ChromaDB`
  - Ingestion Engine: `MarkItDown + fastembed`
  - Orchestration: `Agno Framework`
- **Narrative:**  
  *"CogniVault is an AI-powered course companion that unifies multi-modal course ingestion, strict evidence-grounded tutoring, and cognitive student modeling with Bayesian Knowledge Tracing."*

### Step 2: Course Materials & Exact Physical Locators (0:45 - 1:30)
- **Visual Action:** Click **Course Materials** tab.
  - Review indexed course documents: `physics_mechanics.pdf`, `waves_optics.pptx`, `video_lecture.mp4`.
  - Click **View Units** on `physics_mechanics.pdf`.
  - Observe extracted evidence units tagged with exact physical locations (`Page 1`, `Page 2`, `Page 3`, SHA-256 hashes).
- **Narrative:**  
  *"Unlike generic RAG that provides fuzzy chunk approximations, CogniVault preserves exact page numbers, slide numbers, and video timestamps down to the sentence level."*

### Step 3: Evidence Tutor & Fail-Closed Abstention (1:30 - 2:30)
- **Visual Action:** Click **Evidence Tutor** tab.
  - Click sample prompt: **"Newton's Second Law"**.
  - Observe the grounded answer rendered with **CheckCircle2 Course-Grounded Answer** badge, confidence score (86%), and exact citation badges.
  - Click citation badge `physics_mechanics: Page 1` to open the **Citation Drawer**, displaying the exact excerpt, source file, and page location.
  - Next, click sample prompt: **"Off-Material Abstention Test"** (*"What were the primary economic causes of the French Revolution in 1789?"*).
  - Observe the system **explicitly abstaining** with the amber warning: *"Fail-Closed Abstention: Course does not contain sufficient evidence to answer."*
- **Narrative:**  
  *"The Evidence Sufficiency Gate evaluates whether candidate evidence meets lexical and semantic thresholds. If the material does not support the claim, it fails closed with zero hallucinations."*

### Step 4: Adaptive Practice & BKT Real-Time Update (2:30 - 3:30)
- **Visual Action:** Click **Adaptive Practice** tab.
  - Select an MCQ option (e.g., Option B for Newton's Second Law) and click **Submit Answer**.
  - Observe instant verified feedback:
    - Correctness evaluation.
    - Updated Bayesian Knowledge Tracing mastery delta ($P(L_t)$ updated from 10% to 43%).
    - Source evidence citations proving the correct answer.
- **Narrative:**  
  *"Every assessment attempt updates the learner's posterior mastery probability using standard BKT parameters ($P_L0=0.10, P_T=0.20, P_G=0.25, P_S=0.10$)."*

### Step 5: Misconceptions Diagnosis & Curriculum Roadmap (3:30 - 4:30)
- **Visual Action:** Click **Misconceptions** tab.
  - View diagnosed systematic student error patterns (e.g. confusing mass with weight or velocity with acceleration).
  - Observe the remediation note and linked review materials.
  - Click **Resolve Misconception** button.
  - Switch to **Curriculum Roadmap** tab to show personalized next actions (targeted practice vs. advance topic) dynamically selected based on prerequisite mastery.
- **Narrative:**  
  *"When a learner demonstrates repeated error patterns, CogniVault isolates the cognitive misconception, prescribes targeted foundational materials, and gates subsequent curriculum topics until mastery is restored."*

---

## 3. Evidence Screenshots & Verification Checklist

All visual evidence has been captured via automated Playwright Chromium test execution:
- [x] [`docs/evidence/chat03_walkthrough/01_desktop_home.png`](file:///C:/Users/sujit/CogniVault/docs/evidence/chat03_walkthrough/01_desktop_home.png) — Desktop Home & System Badges
- [x] [`docs/evidence/chat03_walkthrough/02_diagnostic_intake_modal.png`](file:///C:/Users/sujit/CogniVault/docs/evidence/chat03_walkthrough/02_diagnostic_intake_modal.png) — Cold-Start Diagnostic Intake Modal
- [x] [`docs/evidence/chat03_walkthrough/03_course_materials.png`](file:///C:/Users/sujit/CogniVault/docs/evidence/chat03_walkthrough/03_course_materials.png) — Ingested Sources & Unit Inspection
- [x] [`docs/evidence/chat03_walkthrough/04_tutor_grounded_answer.png`](file:///C:/Users/sujit/CogniVault/docs/evidence/chat03_walkthrough/04_tutor_grounded_answer.png) — Tutor Grounded Response
- [x] [`docs/evidence/chat03_walkthrough/05_citation_drawer.png`](file:///C:/Users/sujit/CogniVault/docs/evidence/chat03_walkthrough/05_citation_drawer.png) — Exact Citation Inspection Drawer
- [x] [`docs/evidence/chat03_walkthrough/06_tutor_abstention.png`](file:///C:/Users/sujit/CogniVault/docs/evidence/chat03_walkthrough/06_tutor_abstention.png) — Fail-Closed Abstention Banner
- [x] [`docs/evidence/chat03_walkthrough/07_practice_arena_feedback.png`](file:///C:/Users/sujit/CogniVault/docs/evidence/chat03_walkthrough/07_practice_arena_feedback.png) — Adaptive Practice Arena Feedback
- [x] [`docs/evidence/chat03_walkthrough/08_mastery_dashboard.png`](file:///C:/Users/sujit/CogniVault/docs/evidence/chat03_walkthrough/08_mastery_dashboard.png) — BKT Mastery Dashboard
- [x] [`docs/evidence/chat03_walkthrough/09_misconceptions.png`](file:///C:/Users/sujit/CogniVault/docs/evidence/chat03_walkthrough/09_misconceptions.png) — Misconception Diagnostics
- [x] [`docs/evidence/chat03_walkthrough/10_recommendations.png`](file:///C:/Users/sujit/CogniVault/docs/evidence/chat03_walkthrough/10_recommendations.png) — Curriculum Recommendations
- [x] [`docs/evidence/chat03_walkthrough/11_mobile_tutor.png`](file:///C:/Users/sujit/CogniVault/docs/evidence/chat03_walkthrough/11_mobile_tutor.png) — Mobile Tutor (390x844)
- [x] [`docs/evidence/chat03_walkthrough/12_mobile_practice.png`](file:///C:/Users/sujit/CogniVault/docs/evidence/chat03_walkthrough/12_mobile_practice.png) — Mobile Practice Arena (390x844)
- [x] [`docs/evidence/chat03_walkthrough/13_mobile_mastery.png`](file:///C:/Users/sujit/CogniVault/docs/evidence/chat03_walkthrough/13_mobile_mastery.png) — Mobile Mastery View (390x844)

---

## 4. Human-Only Submission Action Items (Post-Merge)

1. [ ] **Video Recording:** Record video following the above 3-5 minute script (e.g. using OBS or Loom).
2. [ ] **Video Upload:** Upload video to YouTube (Unlisted) or Google Drive.
3. [ ] **Portal Submission:** Submit GitHub repository link and video link to the hackathon portal before deadline.
