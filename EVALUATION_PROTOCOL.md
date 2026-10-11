# Evaluation Protocol — Current

## Required layers
- Retrieval: precision/recall@K and evidence identity/addressability.
- Grounding: supported-claim/faithfulness proxy and answer relevance with defined methodology.
- Abstention: supported-query behavior, unsupported-query abstention and leakage.
- Assessment: structural validity, answer-key correctness, source support, tags and repetition.
- Learner modelling: BKT update correctness and persistence.
- Personalization: simulated learner divergence, prerequisite gating and recommendation rationale.
- End-to-end: ingestion → tutor → assessment → learner update → recommendation.

## Every metric must include
Numerator/denominator, population, definition, timestamp, code/config version, raw or reproducible artifact and limitations.

## Current reported evidence
Chat 04/05 reports state 102 passing tests, AppTest 8/8 views, and a 28-case evaluation walkthrough. These were not rerun by this docs-only update and must be confirmed from artifacts before submission. Playwright driver download failed in the earlier attempt; browser acceptance remains pending.

## Integrity
Do not tune formulas to inflate results, treat simulated learners as real students, or collapse distinct metrics into a misleading aggregate. Targets are not results.


## Final overhaul decision (2026-10-11)
The forward implementation plan is `docs/FINAL_OVERHAUL_PLAN.md`. Use Agno AgentOS, v0-generated Next.js/TypeScript, local Ollama, SQLite/FTS5 + local ChromaDB, deterministic verification and existing BKT logic. Preserve prior code and evaluation history. The plan is locked; the new architecture is not verified until its own tests and end-to-end walkthrough pass. Follow the three-chat sequence in the final plan.
