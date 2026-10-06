# Requirements Traceability

This maps the Track D project brief to implementation, tests and evidence. It is not a claim that the current repository already satisfies these requirements.

| Requirement | Implementation mapping | Verification | Current state |
|---|---|---|---|
| Multimodal ingestion | PDF, PPTX, figure extraction, video transcript/timestamps | ingestion tests | Planned |
| Source-linked knowledge base | source manifest + evidence units + locators | provenance tests | Planned |
| Grounded tutor | retrieval + sufficiency gate + cited response | G1, G4, G5 | Planned |
| Exact source navigation | evidence_id resolves to page/slide/timestamp | citation integrity test | Planned |
| Off-material handling | abstention/unsupported state | G5 + abstention benchmark | Planned |
| Adaptive assessment | mastery/difficulty/repetition/prerequisite selector | A1, A3, L1-L3 | Planned |
| Question correctness | deterministic/model-assisted verification | A2 | Planned |
| Answer verification | objective deterministic checks + structured free-text rubric | A2/A4 | Planned |
| Repetition control | question fingerprint/history | A3 | Planned |
| Feedback | evidence-grounded corrective feedback | A4 | Planned |
| Learner model | BKT per topic/skill | L1-L2 | Planned |
| Misconception support | repeated/strong error signals | L3 + evaluation | Planned |
| Personalization | mastery/difficulty/recommendation policy | L1-L3 | Planned |
| Evaluation | retrieval, faithfulness, relevancy, abstention, assessment and personalization metrics | evaluation runner | Planned |
| Simulated learners | distinct scripted learner profiles | L1-L3 | Planned |
| UX/demo | Streamlit tutor, assessment, learner and evidence views | end-to-end demo | Planned |
| Security | environment secrets, synthetic users, quotas | security tests | Planned |

No requirement is considered satisfied until verification evidence is recorded.
