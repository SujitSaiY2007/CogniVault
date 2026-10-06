# Evaluation Protocol

## Principle

All final performance claims must be supported by executed experiments committed or otherwise reproducibly referenced in this repository.

## Evaluation Layers

### 1. Retrieval / Grounding
Measure context precision and context recall on a fixed source-linked question set.

### 2. Generation Quality
Measure faithfulness and answer relevancy.

### 3. Abstention
Include known off-material questions and record unsupported-answer behavior.

### 4. Assessment
Measure question validity, answer-key correctness, topic/difficulty tagging, and repetition rate.

### 5. Personalization
Run simulated learner profiles across multiple sessions and compare mastery updates and recommendations.

### 6. End-to-End
Run representative learner journeys from source ingestion through tutor → assessment → learner update → recommendation.

## Reproducibility

Evaluation artifacts should contain:
- benchmark questions,
- expected evidence/source,
- model/system output,
- metric calculation,
- pass/fail interpretation,
- execution timestamp,
- software/configuration version where practical.

## Reporting Rule

Never report a metric without its denominator, test population, method, and actual observed value.
