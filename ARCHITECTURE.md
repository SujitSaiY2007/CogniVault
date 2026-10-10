# CogniVault — Architecture Reference

**Scope note:** This describes the intended/reported phase-branch system. Main remains the original scaffold/control baseline; this document does not mean the code has been merged to main.

## System flow
Course sources → ingestion/extraction → normalized evidence with stable IDs and locators → lexical/semantic retrieval → sufficiency/addressability gate → grounded tutor or verified assessment → learner state → recommendation → evaluation.

## Layers
1. Presentation: Streamlit shell and course, evidence, tutor, assessment, progress, recommendation and evaluation views.
2. Application services: orchestration and validation.
3. Evidence/retrieval: source manifest, SQLite/FTS5, semantic embeddings/vector search, deterministic fusion and traces.
4. Grounding: evidence sufficiency, citation resolver and fail-closed abstention.
5. Assessment: verified questions and answer validation.
6. Learner state: per-topic BKT, interaction history and misconception signals.
7. Recommendation: mastery, prerequisites, errors, misconceptions and repetition.
8. Evaluation: fixed cases, simulated learner trajectories and reproducible metrics.
9. Persistence: existing local storage contracts; durable cloud persistence is not verified.

## Technology boundary
Python, Streamlit, SQLite/FTS5, lightweight semantic retrieval, one permitted LLM/multimodal provider and deterministic Python verification. No framework replacement or architecture expansion without a demonstrated need.

## Current UI scope
Chat 05 Stage 1 is presentation-only. Preserve database schema, service contracts, retrieval, citations, assessment, BKT parameters, recommendation policy and evaluation formulas. Use real data, not fake demo records.

## Failure boundaries
Provider failure → explicit error. Retrieval/sufficiency failure → abstention. Citation resolution failure → do not present as grounded. Invalid assessment item → reject. Unknown quota/history/progress → honest unavailable/empty state.

## Branch distinction
The code on phase branches is not present on main merely because architecture docs describe it.
