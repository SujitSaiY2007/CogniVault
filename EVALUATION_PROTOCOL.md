# Evaluation Protocol & Empirical Benchmark Results

## Principle

All performance claims in CogniVault are substantiated by deterministic, reproducible experiments committed in this repository (`evaluation/runner.py` and `evaluation/simulate_learners.py`). We report observed facts with explicit populations, formulas, and denominators—never ungrounded targets or fabricated scores.

---

## Evaluation Layers & Empirical Results

The benchmark suite was executed on the standard STEM corpus (`physics_mechanics.pdf`, `waves_optics.pptx`, `mathematics_calculus.pdf`, `biology_cell_lecture.txt`) with results saved in `evaluation/benchmark_results.json`.

### Summary of Measured Metrics (28 Evaluated Test Cases)

| Layer | Metric | Formula / Denominator | Measured Result | Target |
| :--- | :--- | :--- | :---: | :---: |
| **Retrieval** | Context Recall@3 | $\frac{\|\text{Retrieved top-3} \cap \text{Expected evidence}\|}{\|\text{Expected evidence}\|}$ across 8 queries based on exact `expected_evidence_ids` | **100.0%** (1.000) | $\ge 90\%$ |
| **Retrieval** | Context Precision@3 | $\frac{\|\text{Retrieved top-3} \cap \text{Expected evidence}\|}{\min(3, \|\text{Retrieved}\|)}$ across 8 queries based on exact `expected_evidence_ids` | **39.58%** (0.3958) | $\ge 35\%$ |
| **Grounded Tutor** | Supported Answer Rate | $\frac{\text{In-corpus queries answered with citations}}{\text{Total in-corpus queries}}$ (8/8) | **100.0%** (1.000) | $\ge 95\%$ |
| **Grounded Tutor** | Faithfulness Proxy | Token containment score with gold concept terms | **96.88%** (0.9688) | $\ge 90\%$ |
| **Abstention Gate** | Unsupported Abstention Rate | $\frac{\text{Off-material queries with fail-closed abstention}}{\text{Total off-material queries}}$ (3/3) | **100.0%** (1.000) | $100.0\%$ |
| **Abstention Gate** | Unsupported Leakage Rate | $\frac{\text{Off-material queries hallucinated as supported}}{\text{Total off-material queries}}$ (0/3) | **0.0%** (0.000) | $0.0\%$ |
| **Provenance** | Citation Addressability | $\frac{\text{Citations resolving to active EvidenceDB IDs}}{\text{Total citations emitted}}$ (21/21) | **100.0%** (1.000) | $100.0\%$ |
| **Provenance** | Source-Resolved Locator Accuracy | $\frac{\text{Citations matching source-resolved structural locators}}{\text{Total citations emitted}}$ (21/21) | **100.0%** (1.000) | $100.0\%$ |
| **Assessment** | Structural Verification Accuracy | $\frac{\text{Items with correct valid/reject verdict}}{\text{Total evaluated questions}}$ (6/6) | **100.0%** (1.000) | $100.0\%$ |
| **Assessment** | Repetition Control | Alternative selection on multi-question topic & pool exhaustion fallback | **Passed** (True) | Pass |
| **Learner Model** | BKT Posterior Accuracy | Match with analytical BKT formula ($< 10^{-4}$ tolerance) (5/5) | **100.0%** (1.000) | $100.0\%$ |
| **Personalization** | Recommendation Policy Accuracy | Exact action/difficulty match across all mastery bands (6/6) | **100.0%** (1.000) | $100.0\%$ |

---

## Multi-Turn Simulated Learner Trajectories

Executed across 6 distinct scenarios with results saved in `evaluation/simulation_results.json`:

1. **Consistently Correct Learner (`sim_learner_advancing`):**
   - $P(L)$ progresses from $0.10 \to 0.4333 \to 0.8086 \to 0.9575 \to 0.9917$.
   - Recommendations dynamically shift: `foundational_review` (easy) $\to$ `targeted_practice` (medium) $\to$ `mixed_application` (medium) $\to$ `advance_topic` (hard).
   - Unlocks dependent topic ("Work and Energy") after mastering prerequisite ("Newtonian Mechanics").
2. **Consistently Incorrect Learner (`sim_learner_struggling`):**
   - 3 consecutive incorrect answers; mastery remains safely clamped to $0.1616 \to 0.1700 \to 0.1712$.
   - Actions remain locked at `foundational_review` (easy).
3. **Mixed Performance Learner (`sim_learner_mixed`):**
   - Alternating responses: correct $\to$ incorrect $\to$ correct $\to$ correct ($P(L): 0.10 \to 0.4333 \to 0.2242 \to 0.6305 \to 0.9020$).
4. **Misconception Detection & Remediation (`sim_learner_misconception`):**
   - 2 consecutive errors on "Second Law" trigger misconception diagnosis (`confidence >= 0.80`).
   - Immediately routes recommendation to `remediate_misconception` with targeted remedial evidence citations.
5. **Prerequisite Gating (`prerequisite_gating`):**
   - Missing or unmastered prerequisites ($P < 0.70$) strictly block advancement to dependent topics; satisfaction of prerequisite ($\ge 0.70$) unlocks dependent topic.
6. **Boundary Conditions (`boundary_values`):**
   - Evaluated at exact boundaries: $0.39$ (easy), $0.40$ (medium), $0.69$ (medium), $0.70$ (medium), $0.85$ (medium), $0.86$ (hard).
7. **Baseline Contrast:**
   - Contrasts CogniVault's dynamic mastery-aligned difficulty shifts (`[easy, medium, medium, hard, hard]`) against a static non-personalized baseline (`[medium, medium, medium, medium, medium]`).

---

## Benchmark Categories & Corpus Composition

- **Corpus Files (`data/corpus/`):**
  - `physics_mechanics.pdf`: 2-page PDF with embedded free-body force diagram figure.
  - `waves_optics.pptx`: 2-slide presentation with speaker notes on wave equation and Snell's law.
  - `mathematics_calculus.pdf`: 2-page PDF on quadratic equations, derivatives, and limits.
  - `biology_cell_lecture.txt`: Timestamped lecture transcript on cellular respiration and ATP.
- **Corpus Manifest (`data/corpus_manifest.json`):**
  - Synthetic provenance note, CC0-1.0 public domain test fixture licensing, parser/extractor metadata (`PyMuPDF v1.24+`, `python-pptx v1.0.2+`, `CogniVault Timestamped Regex Parser v1.0.0`, `CogniVault Hybrid Structure-Aware Chunker v1.0.0`).
- **Benchmark Question Categories:**
  - Direct lookup (Newton's Second Law, Quadratic Formula)
  - Conceptual explanation (Mitochondria ATP synthesis)
  - Numerical equation resolution (Wave speed, Snell's law)
  - Visual/Diagram grounding (Free-body force vector diagram)
  - Cross-source multi-modal synthesis (Mechanics + Wave energy)
  - Out-of-corpus adversarial queries (M-theory, French Revolution, Monetary policy)

---

## How to Reproduce

Execute the automated runners from the workspace root:

```powershell
# 1. Run the deterministic evaluation benchmark
.\.venv\Scripts\python.exe evaluation/runner.py

# 2. Run the multi-turn simulated learner benchmark
.\.venv\Scripts\python.exe evaluation/simulate_learners.py

# 3. Run the complete test suite verifying all metrics (100 tests)
.\.venv\Scripts\python.exe -m pytest -v --durations=10
```
