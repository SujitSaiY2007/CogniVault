# CogniVault — Official Hackathon Demo Video Plan & Script

**Event:** Multimodal AI Hackathon 2026  
**Track:** Track D — Personalized Tutoring & Adaptive Learning  
**Target Duration:** 5:30 – 6:45 minutes (Optimal sweet spot within the 3–10 minute guideline)  
**Video Platform:** YouTube (Unlisted or Public, 1080p / 60fps, English audio & closed captions)  
**Live Application URLs Shown:**
- Frontend: [https://cogni-vault.vercel.app](https://cogni-vault.vercel.app)
- Backend API: [https://cognivault-backend-znn4.onrender.com](https://cognivault-backend-znn4.onrender.com)
- GitHub Repository: [https://github.com/SujitSaiY2007/CogniVault](https://github.com/SujitSaiY2007/CogniVault)

---

## Executive Production Guidelines: "Showcase Bigger, Present Like a Pro"

1. **Pacing & Energy:** Confident, engaging, articulate technical cadence. No filler words or prolonged loading waits (the live cloud app responds in milliseconds).
2. **Resolution & Capture:** Record at 1920×1080 or 4K. Use a high-quality condenser microphone.
3. **Cursor & Focus:** Smooth mouse gestures. When clicking citations or inspecting BKT probability curves, briefly zoom in (120–130%) to highlight the exact physical locators.
4. **Honest Scientific Evaluation (+ss and -ss):** Judges respect rigor. Do not claim the system is magic; highlight our rock-solid guarantees (fail-closed abstention, mathematical BKT, zero hallucination) alongside real engineering trade-offs (cold-start heuristics, complex tabular parsing).
5. **AI Tools Attribution:** Follow the hackathon AI Tools Policy by prominently acknowledging AI coding assistance in the credits and README walkthrough.

---

## Scene-by-Scene Storyboard & Script

| Scene | Timecode | Phase | Visual / On-Screen Action | Spoken Voiceover Script | Key Technical Point |
|---|---|---|---|---|---|
| **Scene 1** | `00:00 - 00:45` | **Hook & Problem Statement** | • Camera on presenter or animated title slide.<br>• Split-screen graphic showing fragmented student materials: PDFs, slides, videos, alongside a generic ChatGPT hallucination. | *"Every semester, students struggle with fragmented course materials — textbooks, slide decks, and lecture recordings scattered across multiple portals. When students turn to general AI chatbots, they encounter a critical flaw: generic hallucinations with zero verifiable page citations, and zero memory of what the student actually understands.<br><br>Welcome to **CogniVault**, an evidence-first, source-grounded intelligent learning companion built for Track D of the Multimodal AI Hackathon 2026. CogniVault unifies multimodal course content into a verifiable knowledge graph, pairing bounded Agno agents with Bayesian Knowledge Tracing to deliver trustworthy tutoring with mathematical guarantees."* | • Pinpoint the core flaw of generic LLMs in education.<br>• State project vision and Track D alignment. |
| **Scene 2** | `00:45 - 01:45` | **Multimodal Ingestion & Knowledge Base** | • Switch to live browser: `https://cogni-vault.vercel.app`.<br>• Click **Ingestion** tab.<br>• Drag-and-drop a PDF (`physics_mechanics.pdf`) and PPTX deck (`waves_optics.pptx`).<br>• Show instantaneous ingestion progress, SHA-256 deduplication badge, and auto-extracted metadata (Pages, Slides, Text). | *"Let's look at how CogniVault ingests real course materials without requiring manual preprocessing.<br><br>Here on our live production dashboard, we upload a university physics textbook and a wave optics slide deck. CogniVault instantly computes SHA-256 cryptographic hashes for tamper-proof provenance, parses slide layouts and page coordinates, and normalizes the text into addressable evidence units.<br><br>Notice the physical locators: every chunk is tagged with its exact page number, slide index, or video timestamp. Behind the scenes, our dual hybrid retriever indexes these units simultaneously into SQLite FTS5 for exact keyword matching and ChromaDB for dense semantic retrieval, scoring candidates with our tuned 0.45/0.55 hybrid fusion formula."* | • Zero manual preprocessing.<br>• SHA-256 provenance manifests.<br>• Physical coordinate tagging (Page, Slide, Timestamp).<br>• Hybrid retrieval architecture. |
| **Scene 3** | `01:45 - 03:00` | **Source-Grounded Evidence Tutor & Fail-Closed Abstention** | • Click **Evidence Tutor** tab.<br>• Type question: *'What is Newton\'s second law of motion?'*<br>• Show response with bold definition, formula `F = m · a`, and pill badge `[Physics Mechanics: Page 1]`.<br>• Click citation badge to open modal inspection.<br>• Now type off-topic probe: *'What is the capital of France?'*<br>• Show immediate Amber Alert: *'Fail-Closed Abstention: Course does not contain sufficient evidence to answer.'* | *"Now let's test our Grounded Evidence Tutor.<br><br>We ask: 'What is Newton's second law of motion?' Within milliseconds, CogniVault returns a concise, conversational explanation with the exact mathematical formulation: F equals m times a, alongside variable definitions in Newtons and kilograms.<br><br>Notice this citation badge: 'Physics Mechanics: Page 1'. Clicking it opens the exact excerpt and page coordinates from our indexed material.<br><br>Now watch what happens when we ask an out-of-domain question: 'What is the capital of France?' Instead of hallucinating outside trivia, our deterministic Sufficiency Gate intercepts the query and triggers a fail-closed abstention banner. CogniVault refuses to answer because Paris is not in your physics syllabus. This 100% fail-closed boundary is our first major technical advantage."* | • Clean, plain-language answers.<br>• Exact physical citation clickability.<br>• **Fail-Closed Abstention** demonstration.<br>• Zero hallucination guarantee. |
| **Scene 4** | `03:00 - 04:15` | **Adaptive Assessment & Deterministic Verification** | • Click **Assessment** tab.<br>• Choose scope: *'Classical Mechanics & Dynamics'*, difficulty: *'Medium'*, format: *'Multiple Choice & Numerical'*.<br>• Click **Generate Adaptive Assessment**.<br>• Show generated question with exact source citation and options.<br>• Select an answer and click **Submit Assessment**.<br>• Show instant claim-by-claim evaluation with source locators. | *"Adaptive assessment cannot rely on unverified LLM generation, which often produces incorrect answer keys. CogniVault solves this with an AST-based Deterministic Question Verifier.<br><br>Here, we generate an assessment on Classical Mechanics. Each question is tagged with its topic, difficulty level, and source location. Our verification engine parses the formula structure, ensures numerical tolerances, and runs repetition suppression so students never see duplicate questions.<br><br>Upon submission, the engine evaluates the answer deterministically, provides targeted feedback with exact physical citations, and immediately sends the performance signal to our learner model."* | • AST-based answer key verification.<br>• Repetition bloom filter.<br>• Multi-format: MCQ, Short Answer, Numerical.<br>• Immediate cited feedback. |
| **Scene 5** | `04:15 - 05:15` | **Learner Modeling: Bayesian Knowledge Tracing (BKT)** | • Click **Learner Progress / BKT Model** tab.<br>• Show the interactive mastery bar chart for topics: *Newtonian Mechanics*, *Wave Optics*, *Calculus*.<br>• Highlight topic mastery probability changing: $P(L_t) = 0.10 \to 0.45 \to 0.82$.<br>• Point to Prerequisite Gate: *'Advanced Dynamics locked until Mechanics >= 0.70'*. | *"Most educational apps use basic heuristics or ask an LLM to guess student ability. In CogniVault, we implemented true Bayesian Knowledge Tracing.<br><br>Every topic is tracked by four parameters: initial mastery P(L_0), transition probability P(T), slip probability P(S), and guess probability P(G). When our student answers correctly, the latent knowledge state updates mathematically via Bayes' theorem.<br><br>Notice our Prerequisite Gating: dependent topics like 'Rotational Dynamics' remain locked until prerequisite concepts cross our strict 70% mastery threshold. Furthermore, if a student commits two consecutive errors on the same concept, our Misconception Detector automatically schedules targeted foundational remediation."* | • True Bayesian Knowledge Tracing equations.<br>• Mathematically grounded mastery updates.<br>• Strict prerequisite gating ($\ge 0.70$).<br>• Automated misconception detection. |
| **Scene 6** | `05:15 - 06:15` | **Honest System Evaluation (+ss and -ss)** | • Display Evaluation Summary slide / documentation.<br>• Show test metrics: 143 passing automated tests, RAGAS-style metrics, 1.0 precision on citations, 0% repetition rate.<br>• Presenter speaks to camera on Strengths (+ss) and Limitations (-ss). | *"Let's talk about our empirical evaluation, highlighting both our strengths and current limitations.<br><br>On our benchmark test suite of 143 automated tests, CogniVault achieved a 100% pass rate. In empirical retrieval evaluations, our hybrid pipeline delivered 1.0 citation precision and 100% abstention accuracy on out-of-domain queries. In multi-session simulated student profiles, progressing students gained +0.89 in topic mastery with zero question repetition.<br><br>Now, our engineering trade-offs (-ss): First, our free cloud deployment utilizes deterministic heuristic synthesis when external LLMs are offline, prioritizing zero cost over creative prose. Second, while OCR on clean PDFs and slides is near-perfect, heavily degraded handwritten notes require pre-cleaning. Third, cold-start learners rely on diagnostic prior assumptions before personalized BKT curves diverge."* | • **Honest +ss (Strengths):** Fail-closed safety, 143 tests passing, mathematical BKT.<br>• **Honest -ss (Weaknesses):** Deterministic synthesis fallback on free tier, complex table OCR, cold-start priors. |
| **Scene 7** | `06:15 - 07:00` | **Cloud Deployments, AI Tools Disclosure & Conclusion** | • Show Vercel dashboard and Render live backend service.<br>• Briefly show GitHub README section: 'AI Tools & Attribution Disclosure'.<br>• Display final closing slide with project links, team names, and contact info. | *"CogniVault is fully deployed on 100% free cloud infrastructure: our responsive Next.js frontend is live on Vercel, and our Agno backend is running on Render, ready for organizers to test immediately without installing Ollama or provisioning API keys.<br><br>In compliance with the hackathon AI Tools Policy, all AI coding assistance — including Google Antigravity IDE and Agno scaffolding — is fully documented in our repository README, while the core domain algorithms were architected and verified by our team.<br><br>CogniVault bridges the gap between multimodal AI research and trustworthy classroom education. Thank you, and we welcome your questions!"* | • 100% free live cloud deployment verified.<br>• Full compliance with AI Tools Policy.<br>• Professional closing and call to action. |

---

## Technical Setup & Screen Recording Checklist

### Pre-Recording Checklist
- [ ] Open browser window to `https://cogni-vault.vercel.app` (clear browser cache and test full flow once).
- [ ] Ensure backend container at `https://cognivault-backend-znn4.onrender.com/api/v1/health` is active and warm (`"status": "healthy"`).
- [ ] Set browser zoom to 110% for crisp readability on high-DPI screens.
- [ ] Prepare test queries in a clipboard or notepad for instant pasting:
  - Query 1 (Supported): `What is Newton's second law of motion?`
  - Query 2 (Fail-Closed): `What is the capital of France?`
  - Query 3 (Optics): `What is Snell's law of refraction?`
- [ ] Set microphone gain to avoid clipping; record in a quiet room with minimal reverb.
- [ ] Resolution: 1080p (1920×1080) at 60 FPS in OBS Studio or Screenflow.

### Post-Recording & Upload
- [ ] Edit out any momentary pauses; keep transitions swift (fade to black or slide jump).
- [ ] Add English subtitles / closed captions (.srt file or YouTube auto-caption review).
- [ ] Upload to YouTube as **Unlisted** (or Public).
- [ ] Copy YouTube link into the Devpost submission form.

---

## Judge Presentation & Slide Deck Outline (Optional Presentation Slides)

If you present live slides before or during the video, use this 6-slide structure:

1. **Slide 1 — Title:** CogniVault: Evidence-First Adaptive Study Companion (Track D, Team Names, Live URL).
2. **Slide 2 — The Problem:** The Unverifiable LLM Dilemma in Higher Education (Hallucination risk, lack of provenance, unmodeled learners).
3. **Slide 3 — System Architecture:** The CogniVault Engine (Multimodal Ingestion $\to$ Hybrid Index $\to$ Deterministic Gate $\to$ Agno AgentOS $\to$ BKT Model).
4. **Slide 4 — Core Innovations (+ss):**
   - Exact Physical Citations (Page, Slide, Timestamp).
   - Strict Fail-Closed Abstention (Zero Hallucination).
   - Mathematical Bayesian Knowledge Tracing ($P(L_t)$ vs. LLM prompt drift).
   - AST Deterministic Answer Key Verifier.
5. **Slide 5 — Empirical Evaluation & Trade-offs (-ss):**
   - 143 passing automated tests.
   - 1.0 citation precision; +0.89 mastery gain on simulated learners.
   - Honest trade-offs: offline fallback synthesis, complex table parsing, cold-start priors.
6. **Slide 6 — Live Demonstration & Links:** Vercel frontend, Render backend, GitHub repository, and AI tools disclosure.
