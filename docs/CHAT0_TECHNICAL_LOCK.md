# Cognivault — Chat 0 Technical Lock

**Status:** FOUNDATION LOCK — implementation specification for Chat 1  
**Date:** 2026-10-06  
**Project:** Cognivault — Evidence-First Adaptive Learning  
**Hackathon track:** Track D — Personalized Tutoring & Adaptive Learning

## 1. Purpose

This is the authoritative technical specification produced by Chat 0. It converts the existing project direction into implementable boundaries, data contracts, tests, evaluation gates, and demo behavior.

It does not claim implementation is complete. The repository currently contains documentation and scaffolding only.

## 2. Requirement baseline and evidence status

The current project brief defines the Track D capability baseline as:

1. Multimodal learning-material ingestion, including textbooks, slides, and applicable lecture-video content.
2. Source-linked knowledge/evidence representation.
3. Grounded tutoring using course evidence.
4. Adaptive assessment.
5. Per-topic learner mastery modelling.
6. Misconception signals and targeted remediation.
7. Formal evaluation of grounding, answer quality, personalization, and repetition.
8. A usable demonstration application.

The exact hackathon event name/rules URL is not currently recorded in the repository. Therefore this document does not invent official judging criteria. The capability baseline above is the project brief already used to establish Track D. Final submission rules must be checked against the actual event page before submission.

## 3. Locked MVP

### Must ship

- PDF/textbook ingestion.
- PPTX/slide ingestion.
- Image/figure extraction where available.
- Selected lecture-video ingestion through transcript plus timestamped segments; full video understanding is not required for every video.
- Normalized source/evidence records with stable IDs and locators.
- Hybrid retrieval: lexical + semantic, with metadata filtering.
- Evidence sufficiency gate.
- Grounded tutor responses with source citations.
- Explicit abstention for unsupported/off-material questions.
- Adaptive question selection using topic mastery, difficulty, and repetition history.
- Question generation only from retrieved/source evidence.
- Verification before a generated question is shown.
- Deterministic checking for numerical and objective answers where feasible.
- Structured checking/rubric for free-text answers.
- Per-topic mastery estimates.
- Evidence-based misconception signals.
- Targeted next-action recommendations.
- Evaluation benchmark and reproducible evaluation runner.
- Streamlit demo UI.
- Local secret configuration and lightweight quota controls.

### Stretch only

- Image/diagram reasoning beyond extracted captions/nearby text.
- Rich video key-frame visual reasoning.
- English/Hindi interaction.
- Audio tutoring.
- Spaced-repetition scheduling.
- Course-flow visualization.

Stretch work must not block or destabilize the MVP.

## 4. Product boundary

The system is a course-grounded tutor, not a general-purpose chatbot.

Grounded flow:

Retrieve -> assess evidence -> generate -> verify citation/claims -> respond

If evidence is insufficient, the system must abstain or explicitly state that the supplied material does not support the answer.

General world knowledge may not be silently presented as course content.

## 5. Source/corpus strategy

Use a small, legally usable, reproducible school-level Mathematics/Science corpus suitable for the demo. Prefer openly licensed/public educational material and user-provided material.

The corpus should contain enough variety to exercise conceptual explanations, equations/numerical examples, diagrams/figures, cross-section references, prerequisite relationships, and assessment material.

Every ingested source gets a manifest record:

- source_id
- title
- source_type
- subject
- grade/level if known
- license/provenance note
- checksum
- ingestion timestamp
- parser/extractor version
- language
- status

Large/private source files must not be committed merely for convenience. The repository should contain manifests, small fixtures, and instructions for obtaining permitted source material.

## 6. Multimodal ingestion architecture

### PDF

PDF -> page extraction -> text blocks + images/figures + page metadata -> normalized evidence units.

Keep page number and source coordinates where available.

### PPTX

PPTX -> slide text + notes if available + embedded images -> normalized evidence units.

Every evidence unit retains slide number.

### Images/figures

image -> OCR/caption/visual extraction as available -> evidence unit linked to parent page/slide.

Do not claim visual understanding if only OCR/text extraction was performed.

### Video

MVP path:

video -> audio/transcript segments -> timestamped evidence units.

Optional key frames may be attached later. Timestamp citations are valid only when the stored segment can actually be resolved back to the source.

## 7. Evidence/provenance model

Canonical evidence object:

- evidence_id: stable unique identifier
- source_id
- source_type: pdf | pptx | image | video | text
- locator_type: page | slide | timestamp | section | region
- locator_value
- parent_evidence_id when applicable
- text
- modality: text | visual | transcript
- asset_path/reference when applicable
- extraction_method
- extraction_confidence
- content_hash
- created_at

A citation is a reference to an evidence_id plus its human-readable locator. The system must never fabricate a page, slide, figure, or timestamp.

## 8. Retrieval architecture

Use a lightweight hybrid retriever:

1. Lexical retrieval using SQLite FTS5 or equivalent.
2. Semantic retrieval using embeddings and a lightweight vector store.
3. Metadata filters for source/topic/modality.
4. Reciprocal-rank or equivalent deterministic fusion.
5. Top-k evidence passed to the evidence gate.

This is preferred over an agentic retrieval loop because the MVP needs traceability and predictable behavior.

For every tutor/assessment retrieval, retain the query, retrieved evidence IDs, ranks, retrieval scores, retrieval method, fusion score, and timestamp.

## 9. Evidence sufficiency gate

A query is considered supported only when:

1. at least one retrieved evidence unit is relevant;
2. the evidence contains the information needed for the requested claim; and
3. the source is valid and addressable.

For synthesis questions, every material claim must have supporting evidence.

Low-confidence or ambiguous retrieval must not be converted into a confident course-grounded answer.

## 10. Grounded tutor contract

Tutor output has four logical parts:

1. Answer/explanation.
2. Evidence citation(s).
3. Optional reasoning steps/hints.
4. Confidence/support status.

Required behavior:

- Answer only from retrieved course evidence in grounded mode.
- Cite the exact source location.
- Distinguish direct evidence from synthesis.
- Refuse/flag unsupported questions.
- Never invent citations.
- Never cite a source merely because it is top-ranked; the citation must support the claim.

## 11. Hallucination control

The system does not claim mathematically guaranteed zero hallucination.

The defensible architectural policy is:

- no retrieval -> no grounded answer;
- insufficient evidence -> abstention;
- missing citation mapping -> no grounded answer;
- verification failure -> no assessment item;
- API/service failure -> explicit error state;
- off-material question -> explicit unsupported state.

Evaluation must measure both supported-answer quality and abstention behavior.

## 12. Assessment architecture

Each question has:

- question_id
- topic_id
- source/evidence IDs
- difficulty: easy | medium | hard
- type: MCQ | numerical | short_answer
- prompt
- options where applicable
- expected answer
- solution/explanation
- verification status
- difficulty rationale
- generation metadata
- repetition fingerprint

Candidate questions are ranked using lower current mastery priority, appropriate difficulty, prerequisite readiness, recent error/misconception signals, repetition penalty, and source coverage.

The selector must not repeatedly serve an identical question when valid alternatives exist.

## 13. Question generation and verification

Question generation is constrained by source evidence.

### Deterministic verification

Use deterministic checks for numerical answers, multiple-choice answer keys, equation/result consistency where computable, required metadata, and source citation existence.

### Model-assisted verification

Use a verifier for conceptual correctness, answerability from supplied evidence, expected-answer support, distractor plausibility, and free-text rubric alignment.

The verifier receives the source evidence and candidate question/answer, not unrestricted context.

If verification fails or confidence is below the configured threshold, discard the item.

## 14. Answer verification

Numerical answers are normalized for harmless formatting differences and checked against a deterministic expected value with an explicit tolerance when appropriate.

MCQ answers are exact after normalization.

Short/free-text answers use a structured rubric covering correctness, key concept coverage, contradiction/error, and evidence alignment.

The final result is correct / partially correct / incorrect / needs review. An LLM judgement is not represented as mathematically exact.

## 15. Learner model

### Locked MVP method: Bayesian Knowledge Tracing (BKT)

BKT is selected because it is interpretable, compact, and established in intelligent tutoring systems. OATutor is a directly relevant prior-art example using BKT for skill mastery.

Maintain one mastery probability per topic/skill.

For each topic, store:

- p_mastery
- p_guess
- p_slip
- p_transit
- attempts
- correct
- recent correctness
- last_seen
- misconception signals

For an observed response, update the mastery belief using the standard BKT posterior and transition step. Parameters must be explicit configuration, not hidden in prompts.

Initial parameters are implementation configuration and must not be presented as learned from real students unless actually fitted to data.

Deep knowledge tracing is out of scope for the MVP because it requires substantially more interaction data and reduces interpretability.

## 16. Misconception detection

The system reports likely learning misconceptions tied to course concepts, not medical or psychological diagnoses.

Signals:

1. Repeated wrong answers on the same concept.
2. Consistent wrong option/distractor pattern.
3. Error pattern extracted from numerical work.
4. Contradictory explanation in free-text answer.
5. Repeated failure after remediation.

A single isolated mistake should normally be labelled an error signal, not a misconception.

Each signal maps to topic, observed evidence, suspected misconception label, confidence, and recommended remediation source.

## 17. Personalization logic

Initial policy:

- mastery < 0.40 -> foundational explanation + easy practice;
- 0.40-0.70 -> targeted practice at medium difficulty;
- 0.70-0.85 -> mixed application practice;
- > 0.85 -> harder/application question or next prerequisite-dependent topic.

These are initial policy thresholds, not empirical findings. They may be tuned after evaluation and must then be documented.

Recommendations must identify the learner-state evidence that caused the recommendation.

## 18. Evaluation methodology

### Retrieval

- Context Precision@K.
- Context Recall@K.

### Grounded generation

- Faithfulness / supported-claim rate.
- Answer relevancy.
- Reference answer correctness where a gold answer exists.

### Abstention

- Supported-question answer rate.
- Unsupported-question abstention rate.
- Unsupported-answer leakage rate.

### Assessment

- Question validity rate.
- Answer-key verification pass rate.
- Question repetition rate.
- Topic/difficulty tagging accuracy.

### Personalization

- learner-profile divergence,
- mastery update correctness,
- targeted intervention relevance,
- simulated learner improvement over baseline.

### End-to-end

Measure complete journeys from ingestion -> retrieval -> tutoring -> assessment -> learner update -> recommendation.

No single aggregate score replaces the individual metrics.

## 19. Evaluation dataset

Create a fixed benchmark containing:

- direct fact lookup,
- conceptual explanation,
- numerical reasoning,
- diagram/figure,
- cross-source synthesis,
- paraphrased question,
- ambiguous question,
- unsupported/off-material question,
- adversarial citation question,
- assessment generation/verification cases.

The benchmark must record expected evidence IDs and reference answers where applicable.

No result may be reported before execution.

## 20. Initial acceptance gates

Hard MVP gates:

- G1 direct supported answer: pass.
- G2 visual/figure case: pass for the implemented visual scope.
- G3 video timestamp case: pass for the implemented transcript/timestamp scope.
- G4 cross-source synthesis: pass.
- G5 unsupported query: no unsupported course-grounded answer.
- A1 question metadata and source linkage valid.
- A2 incorrect answer key rejected.
- A3 duplicate question suppressed when alternatives exist.
- A4 corrective feedback cites relevant evidence.
- L1 different simulated learners diverge.
- L2 verified responses update mastery.
- L3 weak topic produces targeted intervention.
- Security tests show no committed secrets.
- Clean-start demo succeeds.

A feature failing its acceptance test is not complete.

## 21. Security and usage

- Secrets only through local environment or approved secret manager.
- .env is never committed.
- Synthetic demo identities only.
- No real student personal data required.
- Request/token/ingestion/assessment quotas are configurable.
- Quota values are measured/configured, not claimed as cost guarantees.
- Fail closed on provider, retrieval, verification, and citation failures.

## 22. Technology boundary

Preferred MVP:

- Python
- Streamlit
- SQLite
- SQLite FTS5
- lightweight vector store such as ChromaDB, subject to implementation validation
- one permitted LLM/multimodal provider
- standard deterministic Python verification

No microservices, Kubernetes, custom foundation-model training, or multi-agent orchestration.

A dependency may be replaced only if the replacement improves reliability or is required by the chosen provider/corpus format.

## 23. UI architecture

Streamlit pages/components:

1. Course Setup / Ingestion
2. Evidence Explorer
3. Tutor
4. Assessment
5. Learner Profile
6. Recommendation / Next Action
7. Evaluation / Admin view for the demo

The evidence explorer is important: judges should be able to open the source location behind an answer.

## 24. Demo contract

Target 6-8 minutes.

1. Problem.
2. Ingest material.
3. Show evidence map.
4. Ask supported question.
5. Open exact evidence.
6. Ask unsupported question and show abstention.
7. Take adaptive assessment.
8. Show verification/feedback.
9. Show changed mastery and misconception signal.
10. Show targeted next action.
11. Show real evaluation results.
12. Briefly explain architecture.

Only verified functionality and executed metrics may be shown.

## 25. Prior-art position

Cognivault does not claim invention of RAG, multimodal extraction, intelligent tutoring, BKT/knowledge tracing, adaptive assessment, LLM-based feedback, or citation-grounded generation.

Relevant prior art already demonstrates substantial overlap. OATutor uses BKT and adaptive problem selection; TutorBench evaluates tutoring capabilities; recent work also combines learner state with pedagogical RAG.

The project-level contribution is framed as an engineering/product integration: an evidence-first course workflow connecting multimodal source provenance, grounded tutoring, verified assessment, interpretable learner state, misconception signals, and measurable next-action adaptation in one lightweight demo.

Any stronger novelty claim requires additional evidence.

## 26. Chat sequence

### Chat 1 — Multimodal Knowledge Foundation

Implement only source manifest, ingestion, extraction, evidence object schema, provenance, FTS/embedding indexing, retrieval, and retrieval tests.

Exit only after the evidence/retrieval prerequisites for G1-G4 are executable.

### Chat 2 — Intelligence Core

Implement grounded tutor, evidence sufficiency, abstention, question generation, verification, BKT learner model, misconception signals, and recommendation policy.

Exit only after G5, A1-A4, and L1-L3 are executable.

### Chat 3 — Product & Evaluation

Implement polished Streamlit UX, benchmark runner, simulated learners, evaluation reports, and demo instrumentation.

Exit only after the benchmark is executed and release gates are recorded.

### Chat 4 — Final Audit & Submission

Run clean setup, full tests, security scan, evaluation, demo rehearsal, documentation consistency audit, and submission checklist.

## 27. Chat 0 exit condition

Chat 0 is complete when this specification exists, all control documents agree with it, acceptance tests are sufficiently specific, evaluation methodology is executable in principle, prior-art positioning is honest, security boundaries are explicit, next-chat implementation scope is unambiguous, and PROJECT_STATE/CURRENT_HANDOFF identify Chat 1 as the next phase.

No application feature is marked complete by this document.
