# Decision Log

| ID | Decision | Rationale | Status |
|---|---|---|---|
| D-001 | Project name: Cognivault | Stable hackathon product identity | Locked |
| D-002 | Track D | Target is Personalized Tutoring & Adaptive Learning | Locked |
| D-003 | Evidence-first architecture | Reduces unsupported course-grounded answers | Locked |
| D-004 | School Mathematics + Science as initial domain | Strong multimodal and assessment demonstration potential | Locked |
| D-005 | English/Hindi interaction is optional | Prevents unnecessary MVP scope expansion | Locked |
| D-006 | Streamlit-first UI | Fast iteration and suitable demo surface | Locked |
| D-007 | Lightweight services over unnecessary multi-agent architecture | Lower complexity and failure surface | Locked |
| D-008 | No secrets in Git | Required security practice | Locked |
| D-009 | No unsupported novelty claims | Prior-art integrity | Locked |
| D-010 | Evaluation results must be executed, not invented | Credibility and reproducibility | Locked |
| D-011 | Hybrid lexical + semantic retrieval | Combines exact course terminology with semantic matching while remaining inspectable | Locked |
| D-012 | SQLite/FTS5 plus lightweight vector index | Keeps MVP infrastructure small and reproducible | Locked |
| D-013 | Evidence units carry stable source locators | Enables citation integrity and evaluation | Locked |
| D-014 | Fail-closed evidence sufficiency gate | Prevents unsupported course-grounded answers | Locked |
| D-015 | BKT for MVP learner model | Interpretable and established for skill mastery/adaptive tutoring | Locked |
| D-016 | Misconception requires repeated/strong evidence | Avoids over-interpreting one wrong answer | Locked |
| D-017 | Deterministic verification where feasible | Numerical/objective correctness is better handled without an LLM | Locked |
| D-018 | Model-assisted verification only for semantic cases | Covers conceptual/free-text cases while preserving a hard rejection path | Locked |
| D-019 | No custom foundation-model training | Unnecessary for hackathon MVP | Locked |
| D-020 | Video MVP uses transcript/timestamps; key-frame reasoning is stretch | Provides real multimodal source coverage without excessive complexity | Locked |
| D-021 | Chat 0 technical lock is authoritative for implementation | Prevents implementation drift | Locked |
| D-022 | Embedded images stored as first-class evidence and binary assets | Figures are independently addressable evidence units with MIME type and SHA-256 | Implemented & Verified |
| D-023 | Relational topic, concept, and prerequisite representation in SQLite | Supports many-to-many evidence-concept mapping and directed prerequisite chains with transitive closure | Implemented & Verified |
| D-024 | SQLite FTS5 MATCH with BM25-backed ranking for lexical search | Uses genuine FTS5 BM25 score combined with term coverage rather than naive token overlap | Implemented & Verified |
| D-025 | Persisted embeddings with dimension validation and explicit failure handling | Stored in SQLite, reused across searches without re-encoding, and catches dimension mismatches | Implemented & Verified |
| D-026 | Deterministic hybrid scoring ($0.45 \times \text{lex} + 0.55 \times \text{sem}$) with stable tie-breaking | Ensures identical ranking across runs with alphabetical tie-breaking on `evidence_id` | Implemented & Verified |
| D-027 | Full provenance source resolver with safe error boundaries | Resolves evidence ID into source path, title, SHA-256, locator, text, asset, and metadata; fails safely on invalid inputs | Implemented & Verified |
| D-028 | Structured machine-readable RetrievalTrace | Captures candidate count, result count, scores, rankings, source IDs, and explicit unsupported reasons | Implemented & Verified |

New decisions must be added here with rationale and status.
