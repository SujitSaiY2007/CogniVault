"""Held-out evaluation, run once after development (see heldout/dataset.json).

Part A: new questions on the demo course. Part B: a document never seen
during development, uploaded as an ordinary user, with questions about it.

Run:  python -m evaluation.run_heldout
"""
from __future__ import annotations

import json
from pathlib import Path

from app.ingest import locator_label
from app.models import PUBLIC_OWNER

from .run_eval import service

ROOT = Path(__file__).resolve().parent / "heldout"


def score(svc, owner, supported, traps, off, is_gold):
    out = {"answered": 0, "partial": 0, "citation_ok": 0, "answer_ok": 0, "trap_declined": 0, "trap_flagged": 0, "trap_leaked": 0,
           "off_declined": 0, "off_leaked": 0, "misses": []}
    for it in supported:
        r = svc.ask(owner, it["q"])
        if r.support_status in {"supported", "partial"}:
            out["answered"] += 1
            out["partial"] += r.support_status == "partial"
            units = [svc.db.get_evidence(c.evidence_id) for c in r.citations]
            c_ok = any(is_gold(u, it) for u in units if u)
            a_ok = all(any(alt.lower() in r.answer.lower() for alt in m.split("|")) for m in it["must_include"])
            out["citation_ok"] += c_ok
            out["answer_ok"] += a_ok
            if not (c_ok and a_ok):
                out["misses"].append({"q": it["q"], "status": r.support_status, "cited": [c.locator_label for c in r.citations], "answer": r.answer[:200]})
        else:
            out["misses"].append({"q": it["q"], "status": r.support_status, "reason": r.unsupported_reason})
    for q in traps:
        st = svc.ask(owner, q).support_status
        out["trap_declined" if st == "unsupported" else "trap_flagged" if st == "partial" else "trap_leaked"] += 1
        if st == "supported":
            out["misses"].append({"q": q, "status": "LEAKED"})
    for q in off:
        st = svc.ask(owner, q).support_status
        out["off_declined" if st == "unsupported" else "off_leaked"] += 1
    n = len(supported)
    out["answer_rate"] = round(out["answered"] / n, 3)
    out["citation_accuracy"] = round(out["citation_ok"] / max(1, out["answered"]), 3)
    out["answer_correctness"] = round(out["answer_ok"] / max(1, out["answered"]), 3)
    out["n"] = {"supported": n, "trap": len(traps), "off": len(off)}
    return out


def run():
    data = json.loads((ROOT / "dataset.json").read_text())
    svc = service()
    a = data["demo"]
    part_a = score(svc, PUBLIC_OWNER, a["supported"], a["trap"], a["off"],
                   lambda u, it: any(u.source_id == s and locator_label(u.location) == loc for s, loc in it["gold"]))
    b = data["upload"]
    up = svc.ingest("heldout_user", (ROOT / b["file"]).read_bytes(), b["file"], persist=False)
    part_b = score(svc, "heldout_user", b["supported"], b["trap"], b["off"],
                   lambda u, it: u.source_id == up["source_id"] and u.section == it["section"])
    part_b["upload"] = {k: up[k] for k in ("evidence_count", "topics", "question_count")}
    res = {"demo_course": part_a, "unseen_upload": part_b}
    out = Path(__file__).resolve().parent / "results"
    out.mkdir(exist_ok=True)
    (out / "heldout.json").write_text(json.dumps(res, indent=2))
    return res


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
