# Hallucination & Grounding Control

## Objective

Prevent unsupported course-grounded claims from being presented as verified facts.

## Policy

1. Evidence retrieval precedes grounded generation.
2. Evidence sufficiency is checked before answering.
3. Grounded answers require provenance.
4. Unsupported questions are declined or clearly flagged.
5. Citations must correspond to real stored source locations.
6. Generated questions must pass answer-key verification.
7. Numerical answers should use deterministic checking when feasible.
8. Retrieval/citation/verification failures fail closed.
9. External model knowledge must not be silently represented as course content.
10. Evaluation must include adversarial/off-material questions.

## Honest Claim

The project will not claim mathematically guaranteed zero hallucination. The defensible claim is that the architecture is designed to reject or flag unsupported course-grounded responses and that this behavior is measured by explicit tests.
