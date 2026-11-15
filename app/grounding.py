"""Evidence gate, answer composition and claim verification.

Gate (decides answer vs. abstain)
  q      = content terms of the question (stemmed, stopwords removed)
  cov_k  = IDF-weighted share of q found in the union of the top-3 chunks
  cov_1  = the same share for the best single chunk
  spec   = numbers and ordinals in the question ("fourth", "1994")
  Answer only if cov_k >= 0.60, cov_1 >= 0.40, every term in spec is found,
  and the top retrieval score >= 0.30. Terms the course never uses get the
  highest IDF, so off-topic questions fail quickly.

Answer
  Extractive (always available): choose 1-4 sentences from the retrieved
  chunks by coverage + similarity, drop redundant ones, cite each one.
  Generative (Gemini/Ollama, optional): the model writes from numbered
  evidence, then every sentence is checked. A sentence is kept only if it
  cites a real evidence number, at least 60% of its content terms (IDF
  weighted) appear in the cited evidence, and every number it states
  appears there. If fewer than half the sentences survive, the extractive
  answer is used instead.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from .embeddings import Embedder
from .ingest import locator_label
from .llm import LLM, LLMError
from .models import Citation, EvidenceUnit
from .nlp import content_terms, numbers_in, sentences, specifier_terms, subject_terms, term_set, word_count
from .retrieval import CorpusIndex, Hit

GATE_COVERAGE = 0.60
GATE_SINGLE = 0.40
GATE_SCORE = 0.30
CLAIM_SUPPORT = 0.60


PARTIAL_COVERAGE = 0.40


@dataclass
class GateDecision:
    supported: bool
    reason: str
    coverage: float
    single_coverage: float
    top_score: float
    missing_terms: list[str] = field(default_factory=list)
    partial: bool = False

    @property
    def confidence(self) -> float:
        return round(min(1.0, 0.6 * self.coverage + 0.4 * min(1.0, self.top_score / 0.6)), 3)


def gate(query: str, hits: list[Hit], idx: CorpusIndex) -> GateDecision:
    q = subject_terms(query) or term_set(query)
    if not q:
        return GateDecision(False, "The question has no subject words to look up.", 0, 0, 0)
    if not hits:
        return GateDecision(False, "Nothing in your course material matches this question.", 0, 0, 0, sorted(q))
    top = hits[:3]
    union: set[str] = set()
    for h in top:
        union |= idx.terms.get(h.unit.evidence_id, set())
    cov = idx.coverage(q, union)
    single = max(h.coverage for h in top)
    missing = sorted(t for t in q if t not in union)
    # Numbers and ordinals must appear in a passage that is itself about the
    # question, not merely somewhere in the top results ("third" in "Newton's
    # third law" does not license "the third rule of differentiation").
    spec = specifier_terms(query)
    spec_missing: list[str] = []
    if spec:
        ok = [h for h in top if spec <= idx.terms.get(h.unit.evidence_id, set()) and h.coverage >= GATE_SINGLE]
        if not ok:
            spec_missing = sorted(t for t in spec if not any(t in idx.terms.get(h.unit.evidence_id, set()) and h.coverage >= GATE_SINGLE for h in top)) or sorted(spec)
    top_score = hits[0].score
    if spec_missing:
        return GateDecision(False, f"The material does not mention '{', '.join(spec_missing)}' in this context.",
                            cov, single, top_score, missing)
    if cov < GATE_COVERAGE:
        # Partly covered: answer what the material does say, and flag the gap.
        if cov >= PARTIAL_COVERAGE and single >= GATE_SINGLE * 0.75 and len(missing) <= 2 and top_score >= GATE_SCORE:
            return GateDecision(True, f"Your material does not mention: {', '.join(missing)}.", cov, single, top_score, missing, partial=True)
        return GateDecision(False, "Your course material covers too little of this question to answer it reliably.",
                            cov, single, top_score, missing)
    if single < GATE_SINGLE:
        return GateDecision(False, "The matching terms are scattered across unrelated passages.", cov, single, top_score, missing)
    if top_score < GATE_SCORE:
        return GateDecision(False, "The best matching passage is only weakly related.", cov, single, top_score, missing)
    # A question that names something the material never mentions can be
    # answered only partially, never as fully supported.
    unseen = sorted(t for t in q if idx.df.get(t, 0) == 0)
    if unseen:
        return GateDecision(True, f"Your material does not mention: {', '.join(unseen)}.", cov, single, top_score, unseen, partial=True)
    return GateDecision(True, "", cov, single, top_score, missing)


def citation_for(unit: EvidenceUnit, source_title: str, source_path: str = "") -> Citation:
    return Citation(
        evidence_id=unit.evidence_id, source_id=unit.source_id, modality=unit.modality, location=unit.location,
        snippet=unit.text[:600], source_title=source_title, source_path=source_path or None,
        locator_label=locator_label(unit.location), asset_id=unit.metadata.get("asset_id"),
    )


@dataclass
class Composed:
    answer: str
    used: list[EvidenceUnit]
    generator: str
    faithfulness: float
    notes: list[str] = field(default_factory=list)
    downgrade: bool = False  # a model judged the evidence insufficient


_ASKS_FORMULA = re.compile(r"\b(formula|equation|expression|relation|calculate|compute)\b", re.I)
_DEFINITIONAL = re.compile(r"\b(is defined as|states that|is called|is known as|refers to|is the|are the|means)\b", re.I)


_WANTS_FIGURE = re.compile(r"\b(figure|diagram|image|picture|graph|chart|illustration|drawing)\b", re.I)
_DEFINITION_START = re.compile(r"^((?:the |a |an )?[\w'\- ]{1,50}?)\s+(?:is|are|states|means|refers to)\b", re.I)
_PRONOUN_START = re.compile(r"^(it|this|these|they|its|their|he|she|for example|for instance)\b", re.I)
_CONTINUATION = re.compile(r"^(it|this|these|they|its|their|for example|for instance|in equation form|in other words|so|therefore|thus|where|that is|doubling|as a result)\b", re.I)


def compose_extractive(query: str, hits: list[Hit], idx: CorpusIndex, embedder: Embedder, max_sentences: int = 4,
                       max_words: int = 130) -> Composed:
    """Pick the sentences that answer the question, plus their direct continuations.

    Sentence weight of a query term = corpus IDF x sentence-pool IDF, so the
    distinctive word ("chain" in "chain rule") matters more than the shared
    one ("rule"). A further sentence is added only if it covers a query term
    not yet covered, or directly continues a chosen sentence ("It is
    calculated as ...").
    """
    q = term_set(query)
    wants_formula = bool(_ASKS_FORMULA.search(query))
    wants_figure = bool(_WANTS_FIGURE.search(query))
    cands: list[dict] = []
    for hi, h in enumerate(hits[:5]):
        u = h.unit
        if u.evidence_type == "figure" and not wants_figure and len(hits) > 1 and hi > 0:
            continue
        sents = sentences(u.text) if u.evidence_type != "figure" else [u.text]
        for si, s in enumerate(sents):
            if word_count(s) < 5 or s.strip().rstrip(".").lower() == (u.section or "").lower():
                continue
            cands.append({"s": s, "u": u, "hi": hi, "si": si, "terms": term_set(s)})
    if not cands:
        u = hits[0].unit
        return Composed(u.text[:600], [u], "extractive", 1.0)
    n = len(cands)
    sdf: dict[str, int] = {}
    for c in cands:
        for t in c["terms"] & q:
            sdf[t] = sdf.get(t, 0) + 1
    w = {t: idx.idf(t) * math.log(1 + n / (1 + sdf.get(t, 0))) for t in q}
    wsum = sum(w.values()) or 1.0
    try:
        sv = embedder.embed([c["s"] for c in cands] + [query])
        sims = sv[:-1] @ sv[-1]
    except Exception:
        sims = np.zeros(n)
    head = max(q, key=lambda t: w[t]) if q else ""
    for c, sim in zip(cands, sims):
        c["cov"] = sum(w[t] for t in q & c["terms"]) / wsum
        score = 0.60 * c["cov"] + 0.30 * float(sim) + 0.10 / (1 + c["hi"])
        if _DEFINITIONAL.search(c["s"]):
            score += 0.05
        # "What is X?" is best answered by the sentence that defines X.
        m = _DEFINITION_START.match(c["s"])
        if q and m:
            subject = term_set(m.group(1))
            if subject and (subject <= q or (head in subject and len(subject - q) <= 1)):
                score += 0.20
        if wants_formula and "=" in c["s"]:
            score += 0.10
        if c["u"].evidence_type == "figure" and not wants_figure:
            score -= 0.15
        c["score"] = score
    ranked = sorted(cands, key=lambda c: -c["score"])
    best = ranked[0]
    picked = [best]
    covered = q & best["terms"]
    words = word_count(best["s"])

    def is_next(c, p):
        return c["u"].evidence_id == p["u"].evidence_id and c["si"] == p["si"] + 1

    top_term = max(q, key=lambda t: w[t]) if q else ""
    best_topics = set(best["u"].topics)
    hit_cov = {h.unit.evidence_id: h.coverage for h in hits}

    def related(c) -> bool:
        if any(c["u"].evidence_id == p["u"].evidence_id for p in picked):
            return True
        return hit_cov.get(c["u"].evidence_id, 0) >= GATE_SINGLE and bool(best_topics & set(c["u"].topics))

    # A chosen sentence that opens with a pronoun needs its antecedent.
    if _PRONOUN_START.search(best["s"]):
        prev = next((c for c in cands if c["u"].evidence_id == best["u"].evidence_id and c["si"] == best["si"] - 1), None)
        if prev is not None:
            picked.insert(0, prev)
            covered |= q & prev["terms"]
            words += word_count(prev["s"])

    changed = True
    while changed and len(picked) < max_sentences:
        changed = False
        for c in ranked:
            if c in picked or words + word_count(c["s"]) > max_words:
                continue
            if any(len(c["terms"] & p["terms"]) / max(1, len(c["terms"] | p["terms"])) > 0.6 for p in picked):
                continue
            nxt = any(is_next(c, p) for p in picked)
            cont = nxt and (_CONTINUATION.search(c["s"]) or (wants_formula and "=" in c["s"]) or top_term in c["terms"])
            adds = bool((q & c["terms"]) - covered) and c["cov"] >= 0.5 * best["cov"] and related(c)
            if cont or adds:
                picked.append(c)
                covered |= q & c["terms"]
                words += word_count(c["s"])
                changed = True
                break
    picked.sort(key=lambda c: (c["hi"], c["si"]))
    used: list[EvidenceUnit] = []
    parts = []
    for c in picked:
        u = c["u"]
        if u.evidence_id not in [x.evidence_id for x in used]:
            used.append(u)
        num = [x.evidence_id for x in used].index(u.evidence_id) + 1
        s = c["s"].strip()
        if not s.endswith((".", "!", "?")):
            s += "."
        parts.append(f"{s} [{num}]")
    return Composed(" ".join(parts), used, "extractive", 1.0)


TUTOR_SYSTEM = (
    "You are CogniVault, a tutor that answers ONLY from the numbered course evidence provided. "
    "Write a clear explanation for a student in 2-6 sentences. After every sentence put the evidence "
    "number(s) it relies on, like [1] or [2][3]. Do not use outside knowledge, do not invent numbers, "
    "page numbers or examples. If the evidence does not answer the question, reply exactly NOT_IN_MATERIAL."
)


def claim_support(sentence: str, evidence_text: str, idx: CorpusIndex) -> float:
    s_terms = term_set(re.sub(r"\[\d+\]", "", sentence))
    if not s_terms:
        return 1.0
    return idx.coverage(s_terms, term_set(evidence_text))


def verify_generated(answer: str, evidence: list[EvidenceUnit], idx: CorpusIndex) -> tuple[str, list[EvidenceUnit], float, int]:
    """Keep only sentences that cite real evidence and are supported by it."""
    kept: list[str] = []
    used_idx: list[int] = []
    sents = [s for s in sentences(answer) if word_count(s) >= 3]
    for s in sents:
        refs = [int(x) for x in re.findall(r"\[(\d+)\]", s)]
        refs = [r for r in refs if 1 <= r <= len(evidence)]
        if not refs:
            continue
        cited_text = " ".join(evidence[r - 1].text for r in refs)
        nums = numbers_in(re.sub(r"\[\d+\]", "", s))
        if any(n.lstrip("+-") not in cited_text for n in nums):
            continue
        if claim_support(s, cited_text, idx) < CLAIM_SUPPORT:
            continue
        kept.append(s)
        used_idx.extend(r for r in refs if r not in used_idx)
    total = len(sents) or 1
    # renumber citations to the order they are first used
    order = sorted(set(used_idx), key=used_idx.index)
    remap = {old: new for new, old in enumerate(order, 1)}
    text = " ".join(kept)
    text = re.sub(r"\[(\d+)\]", lambda m: f"[{remap.get(int(m.group(1)), m.group(1))}]", text)
    return text, [evidence[i - 1] for i in order], len(kept) / total, len(sents)


def compose(query: str, hits: list[Hit], idx: CorpusIndex, embedder: Embedder, llm: Optional[LLM],
            source_titles: dict[str, str]) -> Composed:
    extractive = compose_extractive(query, hits, idx, embedder)
    if llm is None or not llm.available:
        return extractive
    evidence = [h.unit for h in hits[:5]]
    blocks = "\n\n".join(
        f"[{i}] ({source_titles.get(u.source_id, 'Course')}, {locator_label(u.location)})\n{u.text}" for i, u in enumerate(evidence, 1)
    )
    prompt = f"Course evidence:\n\n{blocks}\n\nStudent question: {query}\n\nAnswer:"
    try:
        raw = llm.generate(prompt, system=TUTOR_SYSTEM, temperature=0.2)
    except LLMError:
        extractive.notes.append("Model unavailable; used extractive answer.")
        return extractive
    if "NOT_IN_MATERIAL" in raw:
        extractive.notes.append("The model judged that the passages do not answer the question; showing them as partial support.")
        extractive.downgrade = True
        return extractive
    text, used, faith, n = verify_generated(raw, evidence, idx)
    if not text or faith < 0.5:
        extractive.notes.append(f"Model answer failed verification ({faith:.0%} of sentences supported); used extractive answer.")
        return extractive
    notes = [] if faith == 1 else [f"{n - round(faith * n)} unsupported sentence(s) removed by verification."]
    return Composed(text, used, llm.name, round(faith, 3), notes)


GENERAL_SYSTEM = (
    "Answer the student's question briefly (3-5 sentences) from general knowledge. "
    "This answer is NOT from their course material, so be careful and factual."
)
