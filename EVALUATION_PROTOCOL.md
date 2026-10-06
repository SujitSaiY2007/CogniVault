# Evaluation Protocol

## Principle

All final performance claims must be supported by executed experiments committed or otherwise reproducibly referenced in this repository.

## Evaluation Layers

### 1. Retrieval / Grounding

Measure context precision and context recall on a fixed source-linked question set.

### 2. Generation Quality

Measure faithfulness/supported-claim rate, answer relevancy, and reference-answer correctness where gold answers exist.

### 3. Abstention

Include known off-material and adversarial questions. Report supported-answer rate, abstention rate and unsupported-answer leakage.

### 4. Assessment

Measure question validity, answer-key correctness, source support, topic/difficulty tagging and repetition rate.

### 5. Personalization

Run distinct simulated learner profiles across multiple sessions. Measure mastery updates, profile divergence and targeted recommendation relevance.

### 6. End-to-End

Run representative learner journeys from source ingestion through tutor → assessment → learner update → recommendation.

## Benchmark Categories

At minimum:

- direct lookup,
- conceptual,
- numerical,
- figure/visual,
- cross-source synthesis,
- paraphrase,
- ambiguity,
- unsupported/off-material,
- adversarial citation,
- assessment generation/verification.

## Reproducibility

Evaluation artifacts should contain:

- benchmark question,
- expected evidence/source,
- reference answer where applicable,
- system output,
- metric calculation,
- pass/fail interpretation,
- execution timestamp,
- software/configuration version where practical.

## Reporting Rule

Never report a metric without denominator, population, method and observed value.

Do not invent target achievement. Targets are acceptance gates; results are measured facts.

## Metric Notes

Context precision and recall diagnose retrieval. Faithfulness measures whether answer claims are supported by retrieved evidence. Answer relevancy measures whether the response addresses the question. These metrics are complementary and must not be collapsed into a misleading single score.

LLM-as-judge metrics are treated as evaluation aids, not absolute truth; deterministic checks and human inspection are retained for critical cases.
