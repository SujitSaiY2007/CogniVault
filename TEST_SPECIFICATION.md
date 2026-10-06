# Acceptance Test Specification

Tests are defined before completion claims.

## Grounding

### G1 — Directly Supported
**Input:** Question whose answer is explicitly present in the course material.  
**Expected:** Correct answer with valid source citation.  
**Pass:** Citation resolves to the supporting evidence.

### G2 — Visual/Diagram Evidence
**Input:** Question requiring information from a diagram/figure.  
**Expected:** Correct interpretation with figure/source reference.  
**Pass:** Answer is supported by the referenced visual evidence.

### G3 — Video Evidence
**Input:** Question whose evidence occurs in lecture video.  
**Expected:** Correct answer with timestamp metadata.  
**Pass:** Timestamp resolves to the supporting segment.

### G4 — Cross-Source Synthesis
**Input:** Question requiring two course sources.  
**Expected:** Correct synthesis with both supporting references.  
**Pass:** Each major claim has supporting evidence.

### G5 — Unsupported
**Input:** Question outside the provided course material.  
**Expected:** Abstention or explicit unsupported-material flag.  
**Pass:** No unsupported factual answer is presented as course-grounded.

## Assessment

### A1 — Tagged Question
Question has valid topic, difficulty and source metadata and a verified answer.

### A2 — Correctness Verification
Deterministic or model-assisted verification rejects an incorrect answer key before display.

### A3 — Repetition Control
Repeated sessions do not return the same or near-duplicate question when alternatives exist.

### A4 — Corrective Feedback
Wrong answer produces evidence-grounded feedback and points to relevant material.

## Learner Model

### L1 — Profile Divergence
Two simulated learners with different weaknesses produce different mastery states/recommendations.

### L2 — Session Update
A learner's mastery changes after verified assessment evidence.

### L3 — Targeted Intervention
A learner with a demonstrated weakness receives a recommendation targeting that weakness.

## System Evaluation

The benchmark must report executed values for:
- context precision,
- context recall,
- faithfulness,
- answer relevancy,
- mastery improvement,
- question repetition rate,
- intervention/recommendation relevance.

The exact formulas and thresholds will be finalized in EVALUATION_PROTOCOL.md.
