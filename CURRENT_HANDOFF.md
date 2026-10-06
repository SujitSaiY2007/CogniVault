# Current Handoff

## Last Completed Action

Completed Chat 0 — Project Lock & Foundation.

## Verified GitHub State

- Repository: SujitSaiY2007/CogniVault
- Default branch: main
- Only branch currently present: main.
- Latest work adds the Chat 0 technical lock and prior-art positioning.
- app/, tests/, evaluation/, and data/ remain scaffolds.
- No application feature is verified complete.
- No benchmark result is verified.

## Authoritative Chat 0 Specification

docs/CHAT0_TECHNICAL_LOCK.md

Supporting positioning:
docs/PRIOR_ART_AND_POSITIONING.md

## Locked Decisions

- Track D: Personalized Tutoring & Adaptive Learning.
- School Mathematics + Science initial corpus.
- PDF/PPTX plus transcript/timestamp video ingestion in MVP.
- Evidence IDs with page/slide/timestamp provenance.
- Hybrid lexical + semantic retrieval.
- Evidence sufficiency gate and fail-closed grounding.
- BKT for per-topic mastery.
- Misconception signals require repeated/strong evidence.
- Adaptive policy uses mastery, difficulty, prerequisite readiness, errors and repetition.
- Deterministic answer checks wherever practical.
- Model-assisted verification for conceptual/free-text cases.
- Streamlit + SQLite/FTS5 + lightweight vector store + one permitted LLM provider.
- No unnecessary multi-agent/microservice architecture.
- No unsupported novelty claims.

## Do Not Assume

- No feature is implemented merely because it is specified.
- BKT parameters are not learned from real students unless later fitted and documented.
- Evaluation thresholds are not empirical results.
- Visual reasoning is not available beyond what the implemented extractor/model actually supports.
- Official hackathon judging rules are not reproduced here because the event name/rules URL is not stored in the repository; verify them before final submission.

## Next Chat

### Chat 1 — Multimodal Knowledge Foundation

Implementation scope only:

1. source manifest and corpus fixtures,
2. evidence/provenance data model,
3. PDF/PPTX extraction,
4. video transcript/timestamp path,
5. SQLite/FTS5 indexing,
6. semantic embeddings/vector index,
7. hybrid retrieval,
8. retrieval/evidence tests.

### Chat 1 Exit

Do not proceed to tutor or learner-model implementation until the evidence/retrieval layer is tested and documented.
