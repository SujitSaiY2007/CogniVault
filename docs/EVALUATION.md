# Evaluation

All numbers come from scripts in `evaluation/`; results are saved in `evaluation/results/`.

## Test sets
* `evaluation/dataset.json`: 51 supported questions (gold source and locator plus required answer words), 12 on-topic traps and 12 off-topic questions on the demo course. **This set was used during development**, so treat its scores as optimistic.
* `evaluation/heldout/`: 20 + 6 + 5 new demo questions, plus a document never seen during development (`electricity_notes.md`) with 8 + 3 + 2 questions. First run: `results/heldout_first_run.json`. After adding one rule (terms the material never uses → partial): `results/heldout.json`.

## Metrics
RAGAS-style definitions computed deterministically, without an LLM judge: context precision@5 (average precision), context recall@5, MRR, citation accuracy, answer correctness (required words present) and faithfulness (sentence support ≥ 60%). Faithfulness is high by construction for extractive answers; it matters in model mode. Abstention counts declined, flagged and leaked questions.

## Findings
* BM25 alone scores slightly higher than the hybrid on this small, keyword-rich corpus (MRR 0.98 vs 0.94). Hybrid is kept because it helps with paraphrases on real material; this tradeoff hasn't been measured on a large corpus.
* Gate ablation: removing the number/ordinal rule leaks a trap; removing partial mode loses 2 answerable questions.
* Held-out trap leaks ("Newton's law of gravitation", "critical angle of water") are lexical false positives. A configured model reduces them; they remain the main known weakness.
* Simulation (`simulate.py`): students are synthetic with known ground truth, and learning depends on prerequisites. This favours any prerequisite-aware policy, so read the gains as "the policy behaves as designed", not as classroom evidence. BKT discrimination is modest (AUC 0.63–0.68). The first run showed 26% repetition for adaptive practice; interleaving and bank-exhaustion rules (in `learner.py`) brought it down to 5–10%. Both runs are saved.
* Not done: RAGAS with an LLM judge, real-student studies, and a large public corpus.
