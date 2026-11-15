"""Question generation, verification and grading.

Generators work from the course evidence, so every question carries the
evidence ids (and therefore the page/slide/timestamp) it came from.

  definition MCQ   "Which statement best describes X?" Correct option is the
                   course's own definition of X; distractors are definitions
                   of other concepts from the same course. Each distractor
                   remembers which concept it belongs to, so a wrong pick can
                   be diagnosed as "confused X with Y".
  term MCQ         The reverse: show a definition, pick the term.
  numerical        Formulas found in the text (e.g. "E_k = 0.5 * m * v^2")
                   are parsed into a safe expression tree. Values are drawn
                   from a seeded RNG and the answer is computed, so the key is
                   correct by construction. For product/quotient formulas the
                   unknown can be any variable (solved algebraically).
  cloze            A defining sentence with the key term blanked out.

Verification checks structure, answer-key consistency, evidence linkage,
and near-duplicates (Jaccard >= 0.8 on stemmed terms). An optional model can
propose extra MCQs; those are kept only if the correct option is supported
by the evidence clearly better than every distractor and a second, blind
model call picks the same answer.
"""
from __future__ import annotations

import ast
import hashlib
import math
import operator
import random
import re
from dataclasses import dataclass
from typing import Any, Optional

from .knowledge import Definition
from .llm import LLM, LLMError
from .models import Difficulty, EvidenceUnit, Question, QuestionOption, QuestionType, TopicRecord
from .nlp import content_terms, normalize, sentences, stem, term_set, tokens, word_count

KEYS = "ABCD"


# --------------------------------------------------------------- formulas
_ALLOWED_BIN = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Pow: operator.pow}
_ALLOWED_FUN = {"sqrt": math.sqrt}
_FORMULA_RE = re.compile(
    r"(?<![\w=])([A-Za-z][A-Za-z0-9_]{0,7})\s*=\s*([A-Za-z0-9_\s.*/^()+\-]+?)(?=\s*(?:[,;:]|\.\s|\.$|$|\bwhere\b|\bwhich\b|\bfor\b|\bin\b))"
)


class FormulaError(ValueError):
    pass


def parse_expr(expr: str) -> ast.Expression:
    expr = expr.replace("^", "**").strip().rstrip(".")
    if re.search(r"\d\s*[A-Za-z(]|\)\s*[\w(]", expr):  # implicit multiplication like 4ac or 2(a)
        raise FormulaError("implicit multiplication")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as exc:
        raise FormulaError(str(exc)) from exc
    for node in ast.walk(tree):
        if isinstance(node, (ast.Expression, ast.Load, ast.operator, ast.unaryop)):
            continue
        if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BIN:
            continue
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            continue
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            continue
        if isinstance(node, ast.Name):
            continue
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _ALLOWED_FUN and len(node.args) == 1:
            continue
        raise FormulaError(f"unsupported syntax: {type(node).__name__}")
    return tree


def evaluate(tree: ast.AST, env: dict[str, float]) -> float:
    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant):
            return float(n.value)
        if isinstance(n, ast.Name):
            if n.id not in env:
                raise FormulaError(f"unknown variable {n.id}")
            return env[n.id]
        if isinstance(n, ast.UnaryOp):
            v = ev(n.operand)
            return -v if isinstance(n.op, ast.USub) else v
        if isinstance(n, ast.BinOp):
            return _ALLOWED_BIN[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.Call):
            return _ALLOWED_FUN[n.func.id](ev(n.args[0]))
        raise FormulaError("bad node")

    val = ev(tree)
    if not math.isfinite(val):
        raise FormulaError("non-finite result")
    return val


def variables(tree: ast.AST) -> list[str]:
    names = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Name) and n.id not in _ALLOWED_FUN and n.id not in names:
            names.append(n.id)
    return names


def monomial_powers(tree: ast.AST) -> Optional[tuple[float, dict[str, float]]]:
    """If expr is c * prod(x_i ^ p_i), return (c, {x_i: p_i}); else None."""
    def walk(n) -> Optional[tuple[float, dict[str, float]]]:
        if isinstance(n, ast.Expression):
            return walk(n.body)
        if isinstance(n, ast.Constant):
            return float(n.value), {}
        if isinstance(n, ast.Name):
            return 1.0, {n.id: 1.0}
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Mult, ast.Div)):
            a, b = walk(n.left), walk(n.right)
            if a is None or b is None:
                return None
            sign = 1 if isinstance(n.op, ast.Mult) else -1
            if sign == -1 and b[0] == 0:
                return None
            coef = a[0] * b[0] if sign == 1 else a[0] / b[0]
            pw = dict(a[1])
            for k, v in b[1].items():
                pw[k] = pw.get(k, 0) + sign * v
            return coef, pw
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Pow) and isinstance(n.right, ast.Constant):
            a = walk(n.left)
            if a is None:
                return None
            p = float(n.right.value)
            return a[0] ** p, {k: v * p for k, v in a[1].items()}
        return None

    return walk(tree)


@dataclass
class Formula:
    lhs: str
    rhs: str
    tree: ast.Expression
    evidence_id: str
    meanings: dict[str, tuple[str, str]]  # symbol -> (name, unit)

    @property
    def text(self) -> str:
        return f"{self.lhs} = {self.rhs}"


_WHERE_ITEM = re.compile(r"^\s*(?:and\s+)?([A-Za-z][A-Za-z0-9_]{0,7})\s+(?:is|are|=)\s+(?:the\s+)?([a-zA-Z][a-zA-Z \-]{1,40}?)(?:\s+(?:in|measured in)\s+([^,;.]+?))?\s*$")
_NAMED_SYMBOL = re.compile(r"\b([a-z][a-z ]{2,40}?)\s+\(?([A-Za-z](?:_[A-Za-z0-9]+)?)\)?\s+(?:is|equals)\b")


def _units(text: str) -> str:
    m = re.search(r"\(([^)]{1,12})\)", text or "")
    return m.group(1).strip() if m else (text or "").strip()


def find_formulas(unit: EvidenceUnit) -> list[Formula]:
    text = normalize(unit.text)
    meanings: dict[str, tuple[str, str]] = {}
    for m in re.finditer(r"\bwhere\b(.+?)(?:\.\s|\.$|$)", text, re.I | re.S):
        for piece in re.split(r",\s*|\s+and\s+", m.group(1)):
            mm = _WHERE_ITEM.match(piece)
            if mm:
                meanings[mm.group(1)] = (mm.group(2).strip(), _units(mm.group(3) or ""))
    for m in _NAMED_SYMBOL.finditer(text):
        meanings.setdefault(m.group(2), (" ".join(m.group(1).split()[-2:]), ""))
    out: list[Formula] = []
    seen = set()
    for m in _FORMULA_RE.finditer(text):
        lhs, rhs = m.group(1), m.group(2).strip().rstrip(".").strip()
        if lhs.lower() in {"the", "a", "is", "and"} or not rhs:
            continue
        try:
            tree = parse_expr(rhs)
        except FormulaError:
            continue
        vs = variables(tree)
        if not vs or lhs in vs or len(vs) > 4 or any(len(v) > 8 for v in vs):
            continue
        if any(v.lower() in {"is", "the", "and", "of"} for v in vs):
            continue
        key = (lhs, rhs.replace(" ", ""))
        if key in seen:
            continue
        seen.add(key)
        out.append(Formula(lhs, rhs, tree, unit.evidence_id, meanings))
    return out


def _sig(x: float, digits: int = 4) -> float:
    if x == 0:
        return 0.0
    return round(x, -int(math.floor(math.log10(abs(x)))) + (digits - 1))


def _fmt(x: float) -> str:
    x = _sig(x)
    return str(int(x)) if float(x).is_integer() else f"{x:g}"


def _describe(sym: str, f: Formula, value: Optional[float] = None) -> str:
    name, unit = f.meanings.get(sym, ("", ""))
    label = f"{name} {sym}" if name else sym
    if value is None:
        return label + (f" (in {unit})" if unit else "")
    return f"{label} = {_fmt(value)}" + (f" {unit}" if unit else "")


def numerical_questions(f: Formula, topic: TopicRecord, locator: str, seed: str, max_q: int = 2) -> list[Question]:
    rng = random.Random(int(hashlib.sha256(seed.encode()).hexdigest()[:12], 16))
    vs = variables(f.tree)
    out: list[Question] = []
    for attempt in range(6):
        env = {v: float(rng.randint(2, 12)) for v in vs}
        try:
            lhs_val = evaluate(f.tree, env)
        except (FormulaError, ZeroDivisionError, OverflowError):
            continue
        if abs(lhs_val) > 1e7 or abs(lhs_val) < 1e-4:
            continue
        givens = ", ".join(_describe(v, f, env[v]) for v in vs)
        prompt = (f"Using {f.text} (from {locator}), calculate {_describe(f.lhs, f)} when {givens}.")
        ans = _sig(lhs_val)
        sub = f.rhs
        for v in sorted(vs, key=len, reverse=True):
            sub = re.sub(rf"(?<![A-Za-z0-9_]){re.escape(v)}(?![A-Za-z0-9_])", _fmt(env[v]), sub)
        solution = f"{f.lhs} = {f.rhs} = {sub} = {_fmt(ans)}"
        out.append(_make_numeric(topic, f, prompt, ans, solution, Difficulty.easy if len(vs) <= 2 else Difficulty.medium, "forward"))
        # Inverse question: solve for one input of a monomial formula.
        mono = monomial_powers(f.tree)
        if mono and len(vs) >= 1 and len(out) < max_q:
            coef, powers = mono
            target = rng.choice(vs)
            p = powers.get(target, 0)
            if p:
                others = coef * math.prod(env[v] ** powers[v] for v in powers if v != target)
                if others:
                    val = (lhs_val / others) ** (1 / p)
                    if math.isfinite(val) and abs(val - env[target]) < 1e-6 * max(1, abs(val)):
                        given = [_describe(f.lhs, f, lhs_val)] + [_describe(v, f, env[v]) for v in vs if v != target]
                        prompt2 = (f"Using {f.text} (from {locator}), find {_describe(target, f)} when {', '.join(given)}.")
                        sol2 = f"Rearrange {f.text} for {target}, then substitute: {target} = {_fmt(env[target])}"
                        out.append(_make_numeric(topic, f, prompt2, _sig(env[target]), sol2, Difficulty.hard, "inverse"))
        break
    return out[:max_q]


def _make_numeric(topic: TopicRecord, f: Formula, prompt: str, ans: float, solution: str, diff: Difficulty, kind: str) -> Question:
    tol = max(abs(ans) * 0.01, 0.01)
    return Question(
        question_id="", owner_id=topic.owner_id, topic_id=topic.topic_id, evidence_ids=[f.evidence_id], difficulty=diff,
        question_type=QuestionType.numerical, prompt=prompt, expected_answer=_fmt(ans), tolerance=round(tol, 6),
        solution=solution, metadata={"generator": f"formula-{kind}", "formula": f.text},
    )


# --------------------------------------------------------- definitional MCQs
def _short(text: str, max_words: int = 28) -> str:
    text = re.sub(r"\s+", " ", text).strip().rstrip(".")
    words = text.split()
    return " ".join(words[:max_words]) + ("..." if len(words) > max_words else "")


def _definition_body(d: Definition) -> str:
    s = d.sentence
    m = re.search(r"\b(?:is defined as|is called|is known as|states that|says that|describes that|refers to|means|is|are)\b\s*(.+)$", s, re.I)
    body = m.group(1) if m else s
    # remove the term itself from the body so the option does not give it away
    body = re.sub(rf"\b{re.escape(d.term)}\b", "this", body, flags=re.I)
    return _short(body[0].upper() + body[1:] if body else body)


def _jacc(a: str, b: str) -> float:
    ta, tb = term_set(a), term_set(b)
    return len(ta & tb) / max(1, len(ta | tb))


def definition_mcqs(topic: TopicRecord, defs: list[Definition], pool: list[tuple[str, Definition]], seed: str) -> list[Question]:
    """pool: (topic_id, Definition) for the whole course, used for distractors."""
    rng = random.Random(int(hashlib.sha256(seed.encode()).hexdigest()[:12], 16))
    out: list[Question] = []
    for d in defs:
        correct = _definition_body(d)
        if word_count(correct) < 4:
            continue
        others = [(tid, o) for tid, o in pool if stem(o.term.lower()) != stem(d.term.lower())]
        # Prefer distractors from the same topic (harder), then the rest; skip near-identical ones.
        others.sort(key=lambda x: (x[0] != topic.topic_id, -_jacc(_definition_body(x[1]), correct)))
        distractors: list[tuple[str, Definition]] = []
        for tid, o in others:
            body = _definition_body(o)
            if _jacc(body, correct) > 0.6 or any(_jacc(body, _definition_body(x[1])) > 0.6 for x in distractors):
                continue
            distractors.append((tid, o))
            if len(distractors) == 3:
                break
        if len(distractors) < 2:
            continue
        same_topic = sum(1 for tid, _ in distractors if tid == topic.topic_id)
        diff = Difficulty.hard if same_topic >= 2 else Difficulty.medium if same_topic == 1 else Difficulty.easy

        # 1) statement MCQ
        opts = [(correct, None)] + [(_definition_body(o), o.term) for _, o in distractors]
        rng.shuffle(opts)
        options = [QuestionOption(key=KEYS[i], text=t) for i, (t, _) in enumerate(opts)]
        key = KEYS[[i for i, (_, c) in enumerate(opts) if c is None][0]]
        out.append(Question(
            question_id="", owner_id=topic.owner_id, topic_id=topic.topic_id, concept_id=d.term, evidence_ids=[d.evidence_id],
            difficulty=diff, question_type=QuestionType.mcq, prompt=f"Which statement best describes {d.term}, according to your course material?",
            options=options, expected_answer=key, solution=d.sentence,
            metadata={"generator": "definition-mcq", "distractor_concepts": {KEYS[i]: c for i, (_, c) in enumerate(opts) if c}},
        ))
        # 2) term MCQ
        terms = [(d.term, None)] + [(o.term, o.term) for _, o in distractors]
        rng.shuffle(terms)
        options2 = [QuestionOption(key=KEYS[i], text=t) for i, (t, _) in enumerate(terms)]
        key2 = KEYS[[i for i, (_, c) in enumerate(terms) if c is None][0]]
        out.append(Question(
            question_id="", owner_id=topic.owner_id, topic_id=topic.topic_id, concept_id=d.term, evidence_ids=[d.evidence_id],
            difficulty=Difficulty.easy if diff != Difficulty.hard else Difficulty.medium, question_type=QuestionType.mcq,
            prompt=f"Which term matches this description? \"{correct}\"", options=options2, expected_answer=key2, solution=d.sentence,
            metadata={"generator": "term-mcq", "distractor_concepts": {KEYS[i]: c for i, (_, c) in enumerate(terms) if c}},
        ))
    return out


def cloze_questions(topic: TopicRecord, defs: list[Definition]) -> list[Question]:
    out = []
    for d in defs:
        pattern = re.compile(rf"\b{re.escape(d.term)}\b", re.I)
        if not pattern.search(d.sentence) or word_count(d.term) > 4:
            continue
        blanked = pattern.sub("_____", d.sentence, count=1)
        if word_count(blanked) < 6:
            continue
        out.append(Question(
            question_id="", owner_id=topic.owner_id, topic_id=topic.topic_id, concept_id=d.term, evidence_ids=[d.evidence_id],
            difficulty=Difficulty.medium, question_type=QuestionType.short_answer,
            prompt=f"Fill in the blank: {blanked}", expected_answer=d.term, solution=d.sentence,
            metadata={"generator": "cloze"},
        ))
    return out


# ------------------------------------------------------------- verification
def fingerprint(q: Question) -> str:
    key = " ".join(sorted(set(content_terms(q.prompt + " " + q.expected_answer))))
    return hashlib.sha256(f"{q.topic_id}|{q.metadata.get('generator', '')}|{key}".encode()).hexdigest()[:20]


def verify(q: Question, evidence_ids: set[str]) -> list[str]:
    """Return failure reasons (empty list = verified)."""
    fails: list[str] = []
    if word_count(q.prompt) < 4:
        fails.append("prompt too short")
    if not q.evidence_ids or any(e not in evidence_ids for e in q.evidence_ids):
        fails.append("evidence link missing or unresolvable")
    if q.question_type == QuestionType.mcq:
        keys = [o.key for o in q.options]
        texts = [normalize(o.text).lower().strip() for o in q.options]
        if len(q.options) < 3:
            fails.append("fewer than 3 options")
        if len(set(keys)) != len(keys) or len(set(texts)) != len(texts):
            fails.append("duplicate options")
        if q.expected_answer not in keys:
            fails.append("answer key does not match an option")
        if any(not t for t in texts):
            fails.append("empty option")
    elif q.question_type == QuestionType.numerical:
        try:
            v = float(q.expected_answer)
            if not math.isfinite(v):
                fails.append("non-finite answer")
        except ValueError:
            fails.append("answer is not a number")
        if q.tolerance is None or q.tolerance < 0:
            fails.append("invalid tolerance")
        if "formula" in q.metadata:
            try:
                lhs, rhs = q.metadata["formula"].split("=", 1)
                parse_expr(rhs)
            except Exception:
                fails.append("formula does not parse")
    elif q.question_type == QuestionType.short_answer:
        if not q.expected_answer.strip():
            fails.append("empty expected answer")
    return fails


def finalize(questions: list[Question], evidence_ids: set[str], existing: list[Question]) -> list[Question]:
    """Assign ids, verify, and drop duplicates/near-duplicates."""
    kept: list[Question] = []
    seen_terms = [(q.metadata.get("generator"), term_set(q.prompt + " " + q.expected_answer)) for q in existing]
    seen_fp = {q.fingerprint for q in existing}
    for q in questions:
        q.fingerprint = fingerprint(q)
        q.question_id = f"q:{q.topic_id}:{q.fingerprint[:10]}"
        gen = q.metadata.get("generator")
        terms = term_set(q.prompt + " " + q.expected_answer)
        if q.fingerprint in seen_fp or any(g == gen and len(terms & s) / max(1, len(terms | s)) >= 0.8 for g, s in seen_terms):
            continue
        fails = verify(q, evidence_ids)
        q.verification_status = "rejected" if fails else "verified"
        q.verification_reason = "; ".join(fails) or None
        q.metadata["checks"] = ["structure", "answer key", "evidence link", "duplicate"] if not fails else fails
        seen_fp.add(q.fingerprint)
        seen_terms.append((gen, terms))
        kept.append(q)
    return kept


# ---------------------------------------------------------- model-proposed MCQ
LLM_Q_SYSTEM = (
    "You write exam questions for students strictly from the given course text. "
    "Return JSON: {\"questions\": [{\"prompt\": str, \"options\": [str, str, str, str], \"answer_index\": int, "
    "\"explanation\": str, \"difficulty\": \"easy|medium|hard\"}]}. Exactly one option must be correct according to the text."
)


def llm_mcqs(llm: LLM, topic: TopicRecord, unit: EvidenceUnit, idx, n: int = 2) -> list[Question]:
    """Model proposes MCQs; keep only ones that pass evidence and blind cross-checks."""
    from .grounding import claim_support

    try:
        data = llm.generate_json(f"Course text:\n{unit.text}\n\nWrite {n} multiple-choice questions.", system=LLM_Q_SYSTEM)
    except LLMError:
        return []
    items = data.get("questions", []) if isinstance(data, dict) else []
    out = []
    for it in items[:n]:
        try:
            opts = [str(o).strip() for o in it["options"]][:4]
            ai = int(it["answer_index"])
            prompt = str(it["prompt"]).strip()
        except (KeyError, ValueError, TypeError):
            continue
        if len(opts) < 3 or not 0 <= ai < len(opts):
            continue
        support = [claim_support(prompt + " " + o, unit.text, idx) for o in opts]
        if support[ai] < 0.6 or support[ai] < max(s for i, s in enumerate(support) if i != ai) + 0.15:
            continue
        # Blind cross-check: ask again without the key.
        listing = "\n".join(f"{KEYS[i]}. {o}" for i, o in enumerate(opts))
        try:
            blind = llm.generate(f"Course text:\n{unit.text}\n\nQuestion: {prompt}\n{listing}\n\nReply with the single letter of the correct option.",
                                 temperature=0.0, max_tokens=5)
        except LLMError:
            continue
        if not blind.strip() or blind.strip().upper()[0] != KEYS[ai]:
            continue
        diff = it.get("difficulty", "medium")
        out.append(Question(
            question_id="", owner_id=topic.owner_id, topic_id=topic.topic_id, evidence_ids=[unit.evidence_id],
            difficulty=Difficulty(diff) if diff in {"easy", "medium", "hard"} else Difficulty.medium,
            question_type=QuestionType.mcq, prompt=prompt,
            options=[QuestionOption(key=KEYS[i], text=o) for i, o in enumerate(opts)], expected_answer=KEYS[ai],
            solution=str(it.get("explanation", ""))[:400],
            metadata={"generator": f"llm-mcq:{llm.name}", "cross_checked": True},
        ))
    return out


# ------------------------------------------------------------------ grading
@dataclass
class Grade:
    score: float          # 0..1
    status: str           # correct | partially_correct | incorrect
    pattern: str          # error pattern for misconception tracking ('' if correct)
    detail: str = ""

    @property
    def is_correct(self) -> bool:
        return self.score >= 0.75


def parse_number(text: str) -> Optional[float]:
    t = normalize(text).replace(",", "").replace("−", "-").strip()
    m = re.search(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?(?:\s*/\s*\d+(?:\.\d+)?)?|[-+]?\.\d+", t)
    if not m:
        return None
    s = m.group(0)
    try:
        if "/" in s:
            a, b = s.split("/")
            return float(a) / float(b)
        return float(s)
    except (ValueError, ZeroDivisionError):
        return None


def _edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def grade(q: Question, answer: str) -> Grade:
    ans = (answer or "").strip()
    if not ans:
        return Grade(0.0, "incorrect", "no_answer", "No answer given.")
    if q.question_type == QuestionType.mcq:
        key = ans.upper()[:1] if len(ans) <= 3 else None
        if key is None or key not in [o.key for o in q.options]:
            norm = normalize(ans).lower().strip()
            match = [o.key for o in q.options if normalize(o.text).lower().strip() == norm]
            key = match[0] if match else None
        if key == q.expected_answer:
            return Grade(1.0, "correct", "")
        concept = (q.metadata.get("distractor_concepts") or {}).get(key or "", "")
        return Grade(0.0, "incorrect", f"confused_with:{concept}" if concept else "wrong_option",
                     f"Chose option {key}." if key else "Answer did not match any option.")
    if q.question_type == QuestionType.numerical:
        x = parse_number(ans)
        exp = float(q.expected_answer)
        tol = q.tolerance if q.tolerance is not None else max(abs(exp) * 0.01, 0.01)
        if x is None:
            return Grade(0.0, "incorrect", "not_a_number", "Enter a number.")
        if abs(x - exp) <= tol:
            return Grade(1.0, "correct", "")
        if abs(x - exp) <= max(abs(exp) * 0.05, tol * 3):
            return Grade(0.5, "partially_correct", "rounding", "Close: check rounding.")
        if abs(x + exp) <= tol:
            return Grade(0.0, "incorrect", "sign_error", "The sign is wrong.")
        if x != 0 and exp != 0:
            ratio = abs(x / exp)
            k = round(math.log10(ratio)) if ratio > 0 else 0
            if k != 0 and abs(ratio / (10 ** k) - 1) < 0.02:
                return Grade(0.0, "incorrect", "power_of_ten", "Off by a power of ten: check units.")
            if abs(x * exp - 1) < 0.02 or abs(ratio - 2) < 0.02 or abs(ratio - 0.5) < 0.02:
                return Grade(0.0, "incorrect", "formula_misapplied", "Looks like a factor or the formula was misapplied.")
        return Grade(0.0, "incorrect", "wrong_value")
    # short answer
    exp = q.expected_answer
    a_st = [stem(t) for t in tokens(ans)]
    e_st = [stem(t) for t in tokens(exp)]
    if a_st and e_st and (a_st == e_st or set(e_st) <= set(a_st) and len(a_st) <= len(e_st) + 3):
        return Grade(1.0, "correct", "")
    na, ne = re.sub(r"[^a-z0-9]", "", ans.lower()), re.sub(r"[^a-z0-9]", "", exp.lower())
    if ne and _edit_distance(na, ne) <= max(1, len(ne) // 6):
        return Grade(1.0, "correct", "", "Accepted with a minor spelling difference.")
    overlap = len(set(e_st) & set(a_st)) / max(1, len(set(e_st)))
    if overlap >= 0.5:
        return Grade(0.5, "partially_correct", "incomplete_term", "Partly right.")
    return Grade(0.0, "incorrect", "wrong_term")
