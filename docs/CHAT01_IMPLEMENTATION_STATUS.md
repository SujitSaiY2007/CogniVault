# Chat 01 — Implementation Status
Baseline: audited main commit 0dd3acd0f973f7afcf8dada234f844ee5095b19a.
Implemented: typed evidence/source contracts; SQLite persistence and FTS5; PDF page provenance; PPTX slide provenance; transcript timestamp provenance; optional Sentence Transformer embeddings; deterministic lexical/semantic/hybrid scoring; retrieval traces; initial automated tests.
Not implemented: tutor chat, BKT, personalization, misconception diagnosis, question generation/verification, adaptive scheduling, final dashboard.
Verification: tests are present but no K1-K10 pass claim is made until executed in a real Python environment.
Next: fixture PDF/PPTX tests, figure/image evidence, topic/concept/prerequisite linking, reproducible embedding index, K1-K10 acceptance harness, documentation reconciliation.
