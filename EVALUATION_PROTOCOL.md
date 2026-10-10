# Evaluation Protocol & Empirical Benchmark Results

## Principle

All performance claims in CogniVault are substantiated by deterministic, reproducible experiments committed in this repository (`evaluation/runner.py` and `evaluation/simulate_learners.py`). We report observed facts with explicit populations, formulas, and denominators—never ungrounded targets or fabricated scores.

---

## Evaluation Layers & Empirical Results

The benchmark suite was executed on the standard STEM corpus (`physics_mechanics.pdf`, `waves_optics.pptx`, `mathematics_calculus.pdf`, `biology_cell_lecture.txt`) with results saved in `evaluation/benchmark_results.json`.

### Summary of Measured Metrics (28 Test Cases)

| Layer | Metric | Formula / Denominator | Measured Result |
| :--- | :--- | :--- | :---: |
| **Retrieval** | Context Recall@3 | $\frac{\text{Expected items in top-3}}{\text{Total expected items}}$ | **100.0%** (8/8 queries) |
| **Retrieval** | Context Precision@3 | $\frac{\text{Relevant items in top-3}}{3}$ | **47.62%** |
| **Grounded Tutor** | Supported Answer Rate | $\frac{\text{In-corpus queries answered with citations}}{\text{Total in-corpus queries}}$ | **100.0%** (8/8) |
| **Grounded Tutor** | Faithfulness Proxy | Token containment score with gold concept terms | **96.88%** |
| **Abstention Gate** | Unsupported Abstention Rate | $\frac{\text{Off-material queries with fail-closed abstention}}{\text{Total off-material queries}}$ | **100.0%** (3/3) |
| **Abstention Gate** | Unsupported Leakage Rate | $\frac{\text{Off-material queries hallucinated as supported}}{\text{Total off-material queries}}$ | **0.0%** (0/3) |
| **Provenance** | Citation Addressability | $\frac{\text{Citations resolving to active EvidenceDB IDs}}{\text{Total citations emitted}}$ | **100.0%** |
| **Provenance** | Locator Accuracy | $\frac{\text{Citations with verified page/slide/timestamp}}{\text{Total citations emitted}}$ | **100.0%** |
| **Assessment** | Structural Verification Accuracy | $\frac{\text{Items with correct valid/reject verdict}}{\text{Total evaluated questions}}$ | **100.0%** (6/6 items) |
| **Assessment** | Repetition Suppression | Fraction of repeat candidates filtered | **100.0% Pass** |
| **Learner Model** | BKT Posterior Accuracy | Match with analytical BKT formula ($< 10^{-4}$ tolerance) | **100.0%** (5/5 steps) |
| **Personalization** | Recommendation Policy Accuracy | Exact action/difficulty match across all mastery bands | **100.0%** (6/6 bands) |

---

## Multi-Turn Simulated Learner Trajectories

Executed across 15 interactive turns with results saved in `evaluation/simulation_results.json`:

1. **Struggling Learner (`learner_alpha`):**
   - 5 consecutive incorrect answers across Physics & Calculus.
   - Mastery trajectory: $0.1000 \to 0.1616 \to 0.1616 \to \dots$
   - Misconception detector triggered on Turn 2 after 2 consecutive wrong answers on Newton's Second Law.
   - Recommendation engine locked topic advancement and served `foundational_review` with remedial evidence citations.
2. **Fast Learner (`learner_beta`):**
   - 5 consecutive correct answers on Calculus & Optics.
   - Mastery trajectory: $0.1000 \to 0.4333 \to 0.8086 \to 0.9575 \to 0.9917$.
   - Recommendations transitioned smoothly: `targeted_practice` (easy/medium) $\to$ `mixed_application` $\to$ `advance_topic` (hard).
3. **Misconception Intervention Learner (`learner_gamma`):**
   - 2 incorrect attempts triggering misconception $\to$ remedial review served $\to$ subsequent successful attempt resolving misconception state.

---

## Benchmark Categories & Corpus Composition

- **Corpus Files:**
  - `data/corpus/physics_mechanics.pdf`: 2-page PDF with embedded free-body force diagram figure.
  - `data/corpus/waves_optics.pptx`: 2-slide presentation with speaker notes and refraction laws.
  - `data/corpus/mathematics_calculus.pdf`: 2-page PDF on quadratic equations, derivatives, and limits.
  - `data/corpus/biology_cell_lecture.txt`: Timestamped lecture transcript on cellular respiration and ATP.
- **Benchmark Question Types:**
  - Direct lookup (e.g., Newton's Second Law)
  - Conceptual explanation (e.g., Mitochondria ATP synthesis)
  - Numerical equation resolution (e.g., Wave speed, Snell's law)
  - Visual/Diagram grounding (e.g., Free-body force vector diagram)
  - Cross-source multi-modal synthesis (e.g., Mechanics + Wave energy)
  - Out-of-corpus adversarial queries (e.g., 11-dimensional M-theory, French Revolution, Federal Reserve monetary policy)

---

## How to Reproduce

Execute the automated runners from the workspace root:

```powershell
# Run the deterministic evaluation benchmark
.\.venv\Scripts\python.exe evaluation/runner.py

# Run the multi-turn simulated learner benchmark
.\.venv\Scripts\python.exe evaluation/simulate_learners.py

# Run the complete test suite verifying all metrics
.\.venv\Scripts\python.exe -m pytest -v --durations=10
```
