# Hallucination & Grounding Control

## Objective

Prevent unsupported course-grounded claims from being presented as verified facts.

## Locked Policy

1. Evidence retrieval precedes grounded generation.
2. Evidence sufficiency is checked before answering.
3. Grounded answers require real provenance.
4. Unsupported questions are declined or explicitly flagged.
5. Citations must resolve to stored source locations.
6. Generated questions must pass answer-key/content verification.
7. Numerical answers should use deterministic checking when feasible.
8. Retrieval, citation and verification failures fail closed.
9. External model knowledge must not be silently represented as course content.
10. Evaluation includes adversarial/off-material questions.

## Evidence Contract

A grounded answer is valid only if each material claim can be mapped to one or more evidence IDs.

For cross-source synthesis, multiple evidence IDs are expected.

## Abstention

Abstain when:

- no relevant evidence is retrieved;
- retrieved evidence is insufficient;
- source location cannot be resolved;
- evidence conflicts and the conflict cannot be safely resolved;
- verification fails.

## Honest Claim

Cognivault does not claim guaranteed zero hallucination. It claims an evidence-first architecture designed to reject or flag unsupported course-grounded responses, with this behavior measured by explicit tests.

## Anti-Citation-Hallucination Rule

Never generate page/slide/timestamp identifiers from model memory. All locators must come from stored evidence metadata.
