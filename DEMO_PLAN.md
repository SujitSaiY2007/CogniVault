# Demo Plan & Streamlit Walkthrough Script

Target duration: 6–8 minutes (Hackathon requirement: 3–10 minutes).

Application entry point: `streamlit run app/ui/main.py`

---

## Step-by-Step Demo Sequence Mapped to Streamlit Views

| Step | Topic & Intent | Streamlit View / Tab | Key On-Screen Actions & Verifications |
| :---: | :--- | :--- | :--- |
| **1** | **Problem Statement** | Intro / Context | Highlight the problem: generic LLMs hallucinate facts, fail to prove syllabus grounding, and lack pedagogical state tracking. |
| **2** | **Multi-Modal Ingestion** | `📥 Ingestion` | Upload or click **"Seed Standard Benchmark Corpus"** to load STEM materials: PDF with vector diagram, PPTX with slide notes, and timestamped lecture transcript. |
| **3** | **Evidence Explorer** | `🔍 Evidence Explorer` | Filter by document and view extracted chunks. Inspect page numbers, slide locators, timestamp ranges, and embedded image/diagram assets. |
| **4** | **Supported Query (Grounded Tutor)** | `💬 Grounded Tutor` | Ask: *"What is Newton's Second Law equation and how does it relate to acceleration?"*<br>Show grounded response with clickable citation badges linking to `physics_mechanics.pdf:p1`. |
| **5** | **Unsupported Query (Fail-Closed Abstention)** | `💬 Grounded Tutor` | Ask an off-material question: *"Explain the Reign of Terror in the 1793 French Revolution."*<br>Show the **Fail-Closed Abstention** banner: *"I cannot answer this question because the provided course materials do not contain sufficient evidence."* |
| **6** | **Adaptive Assessment** | `📝 Adaptive Assessment` | Request a practice question for topic `Newtonian Mechanics`. Answer correctly to observe instant structural verification and evidence-backed feedback. |
| **7** | **Misconception Trigger** | `📝 Adaptive Assessment` | Answer incorrectly on related prerequisite questions. Show how repeated errors accumulate error signals. |
| **8** | **Learner Profile & BKT** | `📊 Learner Profile` | Switch to Learner Profile for `learner_alpha`. Show real-time Bayesian Knowledge Tracing mastery bars and the active misconception alert badge. |
| **9** | **Recommendations & Prerequisites** | `🧭 Recommendations` | Show the explainable next-action recommendation: locked from advancing due to misconception; prescribed `foundational_review` with target evidence. |
| **10** | **Empirical Benchmark Dashboard** | `📈 Benchmark & Eval` | Review the live benchmark dashboard: 100% supported answer rate, 100% abstention rate, 0% leakage, and multi-turn simulated learner trajectory curves. |
| **11** | **Architecture & Wrap-Up** | Architecture Slide | Conclude with the closed-loop architecture: Evidence Vault $\to$ Sufficiency Gate $\to$ Grounded Tutor $\to$ Assessment $\to$ BKT Mastery Model $\to$ Recommendations. |

---

## Demo Integrity Checklist

- **Strictly Grounded:** All citations link to active evidence units in SQLite `EvidenceDB`.
- **Deterministic Verifiers:** No fabricated metrics or unverified assertions.
- **Fail-Safe Offline Mode:** Operates fully standalone on local synthetic fixtures without external API dependencies.
