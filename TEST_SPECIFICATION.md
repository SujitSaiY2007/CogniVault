# Acceptance Test Specification

Tests are defined before completion claims.

## Grounding

### G1 — Directly Supported
Input: question explicitly answered by course material.  
Expected: correct answer with valid citation.  
Pass: citation resolves to supporting evidence and answer contains no unsupported course claim.

### G2 — Visual/Diagram
Input: question requiring implemented figure/visual evidence.  
Expected: correct interpretation with figure/source reference.  
Pass: referenced visual evidence actually supports the answer.

### G3 — Video
Input: question whose evidence occurs in an ingested lecture segment.  
Expected: answer with resolvable timestamp.  
Pass: timestamp maps to the supporting segment.

### G4 — Cross-Source Synthesis
Input: question requiring two course sources.  
Expected: synthesis with both supporting references.  
Pass: every material claim has supporting evidence.

### G5 — Unsupported
Input: question outside supplied course material.  
Expected: abstention or explicit unsupported-material state.  
Pass: no unsupported answer is presented as course-grounded.

## Assessment

### A1 — Tagged Question
Question has valid topic, difficulty, source evidence and verification status.  
Pass: all required fields validate.

### A2 — Correctness Verification
Present an intentionally incorrect answer key or unsupported question.  
Pass: verifier rejects it before presentation.

### A3 — Repetition Control
Run repeated sessions with multiple valid candidate questions.  
Pass: identical/near-duplicate question is suppressed when alternatives exist.

### A4 — Corrective Feedback
Submit a wrong answer.  
Pass: feedback is tied to relevant evidence and identifies the learner's next action.

## Learner Model

### L1 — Profile Divergence
Run two simulated learners with materially different answer histories.  
Pass: mastery states and recommendations differ in the expected direction.

### L2 — Session Update
Run verified correct/incorrect responses.  
Pass: BKT state changes deterministically according to configured parameters and observation.

### L3 — Targeted Intervention
Give a learner repeated errors on one topic.  
Pass: recommendation targets that topic and cites the remediation evidence.

## Security

### S1 — Secret Safety
Repository scan contains no committed real secret.  
Pass: no credential is present.

### S2 — Failure Closure
Force retrieval/provider/verification failure.  
Pass: system shows explicit failure/abstention state rather than fabricated output.

## Evaluation Gates

The evaluation runner must report executed values for:

- context precision,
- context recall,
- faithfulness/supported-claim rate,
- answer relevancy,
- supported-answer rate,
- unsupported-question abstention rate,
- question repetition rate,
- mastery/recommendation metrics.

No threshold is considered achieved until the metric is actually measured.
