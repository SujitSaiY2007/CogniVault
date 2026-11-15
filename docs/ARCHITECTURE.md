# Architecture (v2)

One FastAPI backend (`app/`) and one Next.js frontend (`frontend/`). The math and data flow live in the module docstrings; this page is a map.

| Module | Responsibility |
|---|---|
| `ingest.py` | Pure parsers → evidence units with exact locators. PDF headings by font size, chunks of ~140 words that never cross pages, figures with nearest caption, logo filtering. PPTX slides, tables, notes, alt text. SRT/VTT/`[mm:ss]` cues grouped into ~60 s windows. Markdown/plain notes by section. |
| `knowledge.py` | Topic segmentation (headings, else TextTiling-style cohesion dips), definition extraction, IDF keyphrases, prerequisites by *definition-before-use* plus explicit cues ("requires", "builds on"), kept acyclic. |
| `embeddings.py` | Default 512-d signed feature hashing (stemmed words, bigrams, char 4-grams). Optional Gemini or sentence-transformers. |
| `retrieval.py` | FTS5 BM25 + dense cosine → Reciprocal Rank Fusion → re-rank by IDF-weighted query coverage and section-heading match → MMR (λ = 0.75). Scoped to the shared demo course plus the user's own files. |
| `grounding.py` | Evidence gate (coverage ≥ 0.6 over the top 3, single-chunk ≥ 0.4, numbers/ordinals must co-occur with the subject, unseen terms → partial). Extractive composer with definition and antecedent rules. Model answers verified sentence by sentence (citation present, ≥ 60% IDF-weighted support, every number present). |
| `questions.py` | Definition/term MCQs with concept-tagged distractors, cloze, numerical questions from parsed formulas (safe AST evaluator, inverse solving for monomials), verifier, de-duplication, grading with error patterns (sign, power of ten, confusion with concept X). |
| `learner.py` | BKT with item-aware guess (1/options) and slip (by difficulty), partial credit, transit before observation (stored value = posterior), forgetting `p = floor + (p0 - floor)·e^(-Δt/τ)`, misconceptions after 2 errors, recommendations with prerequisite gating, interleaving, bank-exhaustion and wheel-spinning rules. |
| `study.py` | SM-2 flashcards, capacity-aware study plan with forgetting-curve reviews, course map. |
| `service.py` | Orchestration, quizzes and reports, hydration after restarts. |
| `persistence.py` | Local SQLite or Supabase backend (accounts, sessions, original files, per-user progress snapshots). After a restart, files are re-parsed deterministically, so evidence ids stay identical. |
| `api.py` | Routes, auth, per-user isolation, rate limits, safe error messages. |

**Security.** PBKDF2-SHA256 (310k iterations) passwords. Hashed bearer tokens. Every query is scoped by owner. Answer keys are never sent before submission. The Supabase key is server-only. CORS is configurable.

**Changes from v1.** Agno, ChromaDB, sentence-transformers/torch and the Streamlit UI were removed. They added hundreds of MB and import-time side effects without improving answers. The v1 code remains in git history.
