# Requirements Traceability

This maps the Track D project brief to implementation, tests and evidence. It is not a claim that the current repository already satisfies these requirements.

| Requirement | Implementation mapping | Verification | Current state |
|---|---|---|---|
| Multimodal ingestion | PDF, PPTX, figure extraction, video transcript/timestamps (`app/ingest.py`) | `test_k1_to_k10.py`, `test_ingestion.py`, `test_pdf_pptx.py` | Implemented & Verified |
| Source-linked knowledge base | Source manifest, evidence units, locators, SQLite schema (`app/db.py`, `app/models.py`) | `test_k1_to_k10.py`, `test_models_db.py`, `test_evidence_continuity.py` | Implemented & Verified |
| Grounded tutor | Retrieval + sufficiency gate + cited response (`app/tutor.py`) | `test_g1_directly_supported_grounding`, `test_g4_cross_source_synthesis_grounding`, `test_tutor.py` | Implemented & Verified |
| Exact source navigation | `evidence_id` resolves to page/slide/timestamp/asset (`app/source_resolver.py`) | `test_k10_end_to_end_provenance_and_unsupported_behavior`, `test_source_resolver.py` | Implemented & Verified |
| Off-material handling | Fail-closed sufficiency gate + abstention response (`app/sufficiency.py`, `app/tutor.py`) | `test_g5_unsupported_abstention`, `test_sufficiency.py`, `test_s2_failure_closure` | Implemented & Verified |
| Adaptive assessment | Mastery/difficulty/repetition/prerequisite selector (`app/assessment.py`) | `test_a1_tagged_question_metadata`, `test_a3_repetition_suppression`, `test_assessment.py` | Implemented & Verified |
| Question correctness | Deterministic question verifier (`app/assessment.py`) | `test_a2_incorrect_answer_key_rejected`, `test_assessment.py` | Implemented & Verified |
| Answer verification | Objective deterministic checks + tolerance + rubric (`app/assessment.py`) | `test_a4_corrective_feedback_cites_evidence`, `test_assessment.py` | Implemented & Verified |
| Repetition control | Question fingerprinting and served candidate suppression (`app/assessment.py`) | `test_a3_repetition_suppression`, `test_assessment.py` | Implemented & Verified |
| Feedback | Evidence-grounded corrective feedback with citations (`app/assessment.py`) | `test_a4_corrective_feedback_cites_evidence`, `test_assessment.py` | Implemented & Verified |
| Learner model | Bayesian Knowledge Tracing per topic (`app/learner_model.py`) | `test_l1_learner_profile_divergence`, `test_l2_bkt_session_deterministic_update`, `test_learner_bkt.py` | Implemented & Verified |
| Misconception support | Error signal accumulation ($\ge 2$) + prerequisite remediation (`app/misconceptions.py`) | `test_l3_targeted_intervention_misconception`, `test_misconceptions.py` | Implemented & Verified |
| Personalization | Mastery bands (<0.40, 0.40-0.70, 0.70-0.85, >=0.85) + prerequisite policy (`app/recommendation.py`) | `test_l1_learner_profile_divergence`, `test_l3_targeted_intervention_misconception`, `test_recommendations.py` | Implemented & Verified |
| Visual/Diagram grounding | Embedded figure addressability and visual citing (`app/ingest.py`, `app/tutor.py`) | `test_k5_embedded_figure_image_evidence`, `test_g2_visual_diagram_grounding` | Implemented & Verified |
| Video timestamp grounding | Transcript segment parsing and timestamp citations (`app/ingest.py`, `app/tutor.py`) | `test_k4_transcript_timestamp_evidence`, `test_g3_video_timestamp_grounding` | Implemented & Verified |
| Evaluation runner | Retrieval, faithfulness, abstention, assessment benchmark runner | `evaluation/` runner (Chat 03) | Planned (Chat 03) |
| Simulated learners | Scripted multi-turn learner profiles benchmark | `evaluation/` runner (Chat 03) | Planned (Chat 03) |
| UX/demo | Streamlit tutor, assessment, learner and evidence explorer views | `app/ui/` Streamlit app (Chat 03) | Planned (Chat 03) |
| Security & Failure Closure | Environment secrets, synthetic accounts, fail-closed boundaries | `test_s2_failure_closure`, secret scans | Implemented & Verified |

No requirement is considered satisfied until verification evidence is recorded.

