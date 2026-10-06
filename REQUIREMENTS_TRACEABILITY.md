# Requirements Traceability

This document maps the Track D requirements to planned implementation and verification. Exact implementation references will be filled as code is created.

| Requirement Area | Planned Capability | Planned Verification |
|---|---|---|
| Multimodal ingestion | Extract text, images, figures, diagrams and applicable video timestamps | Ingestion tests + evidence inspection |
| Source-linked KB | Evidence units with page/slide/timestamp metadata | Metadata integrity tests |
| Grounded tutor | Retrieval-first answer generation with citations | G1–G5 |
| Exact source navigation | Citation maps to source location | Citation integrity test |
| Off-material handling | Abstain or clearly flag unsupported questions | G5 |
| Adaptive assessment | Topic/source/difficulty-aware question selection | A1 + learner tests |
| Correctness verification | Verify generated questions and answer keys | A2 |
| Repetition control | Avoid exact/near duplicate questions | A3 |
| Feedback | Evidence-grounded corrective feedback | A4 |
| Learner model | Per-topic mastery state updated by sessions | L1–L3 |
| Misconception support | Detect likely misconceptions and recommend intervention | L3 + evaluation |
| Evaluation | Context precision/recall, faithfulness, relevancy and personalization metrics | Evaluation protocol |
| Simulated learners | Different profiles across multiple sessions | L1–L3 |
| UX/demo | Clear tutor, assessment, learner and evidence views | End-to-end demo |
| Documentation | Architecture, learner model, evaluation and setup docs | Final audit |

No requirement is considered satisfied until its verification evidence is recorded.
