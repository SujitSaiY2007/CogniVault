"""Evaluate retrieval, grounding, answers and the question bank on the demo course.

Run:  python -m evaluation.run_eval
Writes evaluation/results/grounding.json and prints a summary. The numbers in
README.md and docs/EVALUATION.md come from this script (plus simulate.py).

Metric definitions (k = 5, relevance = the passage's source and locator match a gold pair)
  context_precision@k  RAGAS-style average precision: sum_i P@i * rel_i / (#relevant in top-k)
  context_recall@k     share of supported questions with a gold passage in the top k
  mrr                  mean reciprocal rank of the first gold passage
  answer_rate          supported questions answered (fully or flagged as partial)
  citation_accuracy    answered questions whose citations include a gold passage
  answer_correctness   answered questions whose answer contains every 'must_include' string
                       ('a|b' accepts either wording)
  faithfulness         share of answer sentences supported by their cited passage
                       (>= 60% of IDF-weighted content words present). For the extractive
                       engine this is high by construction; it matters for model-written answers.
  abstention           trap/off questions declined; 'flagged' = answered as partial with the gap named
  leakage              trap/off questions answered as fully supported (the failure we care about)
"""
from __future__ import annotations

import json
import math
import re
import time
from pathlib import Path

import numpy as np

from app.config import Settings
from app.db import Database
from app.grounding import claim_support, gate
from app.ingest import locator_label
from app.llm import LLM
from app.models import PUBLIC_OWNER, QuestionType
from app.nlp import sentences, term_set
from app.questions import evaluate, parse_expr
from app.retrieval import fts_query
from app.service import CogniVault

ROOT = Path(__file__).resolve().parent
K = 5


def service() -> CogniVault:
    svc = CogniVault(Settings(data_dir=ROOT.parent / "data"), db=Database(":memory:"), llm=LLM())
    svc.seed_demo_course()
    return svc


def is_gold(unit, gold) -> bool:
    lab = locator_label(unit.location)
    return any(unit.source_id == s and lab == loc for s, loc in gold)


def avg_precision(rels: list[bool]) -> float:
    hits, total = 0, 0.0
    for i, r in enumerate(rels, 1):
        if r:
            hits += 1
            total += hits / i
    return total / hits if hits else 0.0


def retrieval_metrics(rankings: list[list[bool]]) -> dict[str, float]:
    ap = [avg_precision(r[:K]) for r in rankings]
    rec = [1.0 if any(r[:K]) else 0.0 for r in rankings]
    mrr = [next((1 / i for i, x in enumerate(r[:K], 1) if x), 0.0) for r in rankings]
    return {"context_precision@5": round(float(np.mean(ap)), 4), "context_recall@5": round(float(np.mean(rec)), 4), "mrr": round(float(np.mean(mrr)), 4)}


def run() -> dict:
    data = json.loads((ROOT / "dataset.json").read_text())
    svc = service()
    idx = svc.retriever.index(PUBLIC_OWNER)
    t0 = time.time()

    # ---------------------------------------------------------- retrieval
    hybrid, lexical, dense = [], [], []
    for item in data["supported"]:
        q, gold = item["q"], item["gold"]
        hits = svc.retriever.search(q, PUBLIC_OWNER, k=K)
        hybrid.append([is_gold(h.unit, gold) for h in hits])
        lex = svc.db.fts_search(fts_query(q), PUBLIC_OWNER, limit=K)
        lexical.append([is_gold(idx.units[e], gold) for e, _ in lex])
        qv = svc.embedder.embed([q])[0]
        order = np.argsort(-(idx.matrix @ qv))[:K]
        dense.append([is_gold(idx.units[idx.vec_ids[int(i)]], gold) for i in order])

    # ------------------------------------------------------------ answers
    answered = flagged = cite_ok = correct = 0
    faith_scores: list[float] = []
    per_question = []
    for item in data["supported"]:
        r = svc.ask(PUBLIC_OWNER, item["q"])
        ok_answer = r.support_status in {"supported", "partial"}
        units = [svc.db.get_evidence(c.evidence_id) for c in r.citations]
        c_ok = any(is_gold(u, item["gold"]) for u in units if u)
        has_all = all(any(alt.lower() in r.answer.lower() for alt in m.split("|")) for m in item["must_include"])
        if ok_answer:
            answered += 1
            flagged += r.support_status == "partial"
            cite_ok += c_ok
            correct += has_all
            text = " ".join(u.text for u in units if u)
            for s in sentences(re.sub(r"\[\d+\]", "", r.answer)):
                if len(s.split()) >= 4 and not s.startswith(("Your material does not mention", "Here is what", "The passages below")):
                    faith_scores.append(1.0 if claim_support(s, text, idx) >= 0.6 else 0.0)
        per_question.append({"q": item["q"], "status": r.support_status, "citation_ok": c_ok, "answer_ok": has_all,
                             "cited": [f"{c.source_id} {c.locator_label}" for c in r.citations]})

    def neg(qs):
        out = {"declined": 0, "flagged": 0, "leaked": 0, "items": []}
        for q in qs:
            r = svc.ask(PUBLIC_OWNER, q)
            key = {"unsupported": "declined", "partial": "flagged"}.get(r.support_status, "leaked")
            out[key] += 1
            out["items"].append({"q": q, "status": r.support_status, "reason": r.unsupported_reason})
        return out

    traps, off = neg(data["trap"]), neg(data["off"])
    n_sup = len(data["supported"])
    n_neg = len(data["trap"]) + len(data["off"])
    tp = answered
    fn = n_sup - answered
    fp = traps["leaked"] + off["leaked"]
    tn = n_neg - fp
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0

    # ------------------------------------------------------- gate ablation
    def ablate(variant: str) -> dict[str, int]:
        """Re-run the decision with one rule removed to show what each rule buys."""
        import app.grounding as g

        saved = (g.specifier_terms, g.PARTIAL_COVERAGE)
        try:
            if variant == "no_specifier_rule":
                g.specifier_terms = lambda text: set()
            if variant == "no_partial_mode":
                g.PARTIAL_COVERAGE = 2.0
            res = {"supported_answered": 0, "negatives_leaked": 0}
            for item in data["supported"]:
                hits = svc.retriever.search(item["q"], PUBLIC_OWNER, k=K)
                res["supported_answered"] += gate(item["q"], hits, idx).supported
            for q in data["trap"] + data["off"]:
                hits = svc.retriever.search(q, PUBLIC_OWNER, k=K)
                d = gate(q, hits, idx)
                res["negatives_leaked"] += d.supported and not d.partial
            return res
        finally:
            g.specifier_terms, g.PARTIAL_COVERAGE = saved

    # ------------------------------------------------------ question bank
    qs = svc.db.questions(PUBLIC_OWNER, verified_only=False)
    by_type: dict[str, int] = {}
    by_gen: dict[str, int] = {}
    for q in qs:
        by_type[q.question_type.value] = by_type.get(q.question_type.value, 0) + 1
        by_gen[q.metadata.get("generator", "?")] = by_gen.get(q.metadata.get("generator", "?"), 0) + 1
    recomputed = ok = 0
    for q in qs:
        if q.metadata.get("generator") == "formula-forward":
            env = {m.group(1): float(m.group(2)) for m in re.finditer(r"\b([A-Za-z_][A-Za-z0-9_]*) = ([-\d.]+)", q.prompt.split("when", 1)[1])}
            recomputed += 1
            ok += abs(evaluate(parse_expr(q.metadata["formula"].split("=", 1)[1]), env) - float(q.expected_answer)) <= (q.tolerance or 0)
    ids = {u.evidence_id for u in svc.db.evidence_for_owner(PUBLIC_OWNER)}
    terms = [term_set(q.prompt + " " + q.expected_answer) for q in qs]
    near_dup = sum(1 for i in range(len(terms)) for j in range(i + 1, len(terms))
                   if qs[i].topic_id == qs[j].topic_id and qs[i].metadata.get("generator") == qs[j].metadata.get("generator")
                   and len(terms[i] & terms[j]) / max(1, len(terms[i] | terms[j])) >= 0.8)

    results = {
        "dataset": {"supported": n_sup, "trap": len(data["trap"]), "off": len(data["off"])},
        "retrieval": {"hybrid_rrf_rerank": retrieval_metrics(hybrid), "bm25_only": retrieval_metrics(lexical), "dense_only": retrieval_metrics(dense)},
        "answers": {
            "answer_rate": round(answered / n_sup, 4),
            "answered_as_partial": flagged,
            "citation_accuracy": round(cite_ok / max(1, answered), 4),
            "answer_correctness": round(correct / max(1, answered), 4),
            "faithfulness": round(float(np.mean(faith_scores)) if faith_scores else 0.0, 4),
        },
        "abstention": {
            "trap": {k: v for k, v in traps.items() if k != "items"},
            "off": {k: v for k, v in off.items() if k != "items"},
            "confusion": {"tp": tp, "fn": fn, "fp": fp, "tn": tn},
            "answer_precision": round(precision, 4), "answer_recall": round(recall, 4),
            "f1": round(2 * precision * recall / (precision + recall), 4) if precision + recall else 0.0,
            "leakage_rate": round(fp / n_neg, 4),
        },
        "gate_ablation": {"full": ablate("full"), "no_specifier_rule": ablate("no_specifier_rule"), "no_partial_mode": ablate("no_partial_mode")},
        "question_bank": {
            "total": len(qs), "verified": sum(q.verification_status == "verified" for q in qs), "by_type": by_type, "by_generator": by_gen,
            "numerical_recomputed_ok": f"{ok}/{recomputed}",
            "evidence_links_valid": sum(set(q.evidence_ids) <= ids for q in qs), "near_duplicates": near_dup,
            "topics_with_questions": len({q.topic_id for q in qs}), "topics_total": len(svc.db.topics(PUBLIC_OWNER)),
        },
        "per_question": per_question,
        "negatives": traps["items"] + off["items"],
        "runtime_seconds": round(time.time() - t0, 2),
        "engine": {"answers": "extractive (no model configured)", "embeddings": svc.embedder.name},
    }
    out = ROOT / "results"
    out.mkdir(exist_ok=True)
    (out / "grounding.json").write_text(json.dumps(results, indent=2))
    return results


if __name__ == "__main__":
    r = run()
    print(json.dumps({k: v for k, v in r.items() if k not in {"per_question", "negatives"}}, indent=2))
