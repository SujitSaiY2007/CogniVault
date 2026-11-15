"""Small, dependency-free text utilities shared by every stage.

The same normaliser is applied to documents and queries, so matching is
consistent even though the stemmer is deliberately simple.
"""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter

STOPWORDS = frozenset(
    """
a about above after again against all also am an and any are as at be because been before being below
between both but by can could did do does doing down during each either else even ever every few for from
further get gets given gives had has have having he her here hers him his how however i if in into is it its
itself just let like may me might more most much must my neither no nor not now of off often on once one only
or other our ours out over own per please put quite rather really said same say says shall she should show
since so some such than that the their theirs them then there these they this those though through thus to
too under until up upon us use used uses using very via was we were what whatever when where whether which
while who whom whose why will with within without would yes yet you your yours
explain describe define definition tell give list state mean means meaning example examples
hi hello hey thanks thank ok okay please help know want wondering
defined described explained called meant
""".split()
)

# Common verbs and fillers that make poor concept names.
PHRASE_STOP = frozenset(
    """
act acts applied apply applies bend bends carry carries carrying change changes contain contains control controls
convert converts doubled doubling find found gives happen happens hit hits keep keeps make makes move moves moving
need needed pass passes passing push pushes relate relates release releases show shows start starts stay stays
stress take takes tend tends transfer transfers travel travelling work works working written called known form
start notes speaker slide page figure lecture today going look example following
""".split()
)

# Words that narrow a question to something specific. If a query contains
# one of these (or a number), the evidence must contain it too, otherwise a
# question like "What is Newton's fourth law?" would pass on "Newton" + "law".
SPECIFIERS = frozenset(
    """
first second third fourth fifth sixth seventh eighth ninth tenth zeroth last final
""".split()
)

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_']*|\d+(?:\.\d+)?")
_SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9(\"'])")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    text = text.replace("­", "")  # soft hyphen
    return text


def tokens(text: str) -> list[str]:
    out = []
    for t in _TOKEN_RE.findall(normalize(text).lower()):
        t = t.strip("'")
        if t.endswith("'s"):
            t = t[:-2]
        if t:
            out.append(t)
    return out


def stem(word: str) -> str:
    """Light suffix stripper. Consistency matters more than linguistics."""
    w = word.lower()
    if len(w) <= 3 or w[0].isdigit():
        return w
    for suf, rep in (
        ("ational", "ate"), ("ization", "ize"), ("fulness", "ful"), ("ousness", "ous"),
        ("iveness", "ive"), ("ements", "e"), ("ement", "e"), ("ments", ""), ("ment", ""),
        ("ities", "ity"), ("ations", "ate"), ("ation", "ate"), ("ically", "ic"), ("ically", "ic"),
        ("ingly", ""), ("edly", ""), ("ness", ""), ("ies", "y"), ("ied", "y"),
        ("ing", ""), ("ed", ""), ("ly", ""), ("es", ""), ("s", ""),
    ):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            w = w[: len(w) - len(suf)] + rep
            break
    if len(w) > 4 and w[-1] == w[-2] and w[-1] not in "lsz":
        w = w[:-1]
    if len(w) > 4 and w.endswith("e"):
        w = w[:-1]
    return w


def content_terms(text: str) -> list[str]:
    """Stemmed tokens with stopwords removed (order preserved, duplicates kept)."""
    return [stem(t) for t in tokens(text) if t not in STOPWORDS and (len(t) > 1 or t.isdigit())]


def term_set(text: str) -> set[str]:
    return set(content_terms(text))


# Task words in questions ("calculate", "find") are kept for ranking but do
# not count as subject matter when deciding whether the material covers it.
QUESTION_FILLERS = frozenset(stem(w) for w in """
calculate compute find work determine solve value need needed used happen happens mean difference between
""".split())


def subject_terms(text: str) -> set[str]:
    return term_set(text) - QUESTION_FILLERS


def specifier_terms(text: str) -> set[str]:
    """Numbers and ordinal words in a query that evidence must also contain."""
    out = set()
    for t in tokens(text):
        if t in SPECIFIERS or re.fullmatch(r"\d+(\.\d+)?", t):
            out.add(stem(t))
    return out


def sentences(text: str) -> list[str]:
    text = re.sub(r"[ \t]+", " ", normalize(text))
    parts: list[str] = []
    # Chunks keep one paragraph, bullet or slide line per text line, so a
    # newline is always a sentence boundary.
    for block in text.split("\n"):
        block = block.strip().lstrip("-*• ").strip()
        if not block:
            continue
        parts.extend(p.strip() for p in _SENT_RE.split(block) if p.strip())
    return parts


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text or ""))


def slugify(text: str, max_len: int = 48) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", normalize(text).lower()).strip("-")
    return s[:max_len].strip("-") or "item"


def numbers_in(text: str) -> list[str]:
    return re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?", text or "")


def ngrams(words: list[str], n: int) -> list[tuple[str, ...]]:
    return [tuple(words[i : i + n]) for i in range(len(words) - n + 1)]


def keyphrases(text: str, top_k: int = 8, doc_freq: Counter | None = None, n_docs: int = 1, min_freq: int = 1) -> list[str]:
    """RAKE-style candidate phrases scored by word degree / frequency and IDF.

    Candidates are maximal runs of non-stopword tokens (1-4 words). With a
    document-frequency table the score is weighted by IDF so phrases that
    appear everywhere in a course rank lower than distinctive ones.
    """
    raw = [t for t in _TOKEN_RE.findall(normalize(text))]
    phrases: list[list[str]] = []
    cur: list[str] = []
    for tok in raw:
        low = tok.lower().strip("'")
        if low.endswith("'s"):
            low = low[:-2]
        if low in STOPWORDS or low in PHRASE_STOP or low.isdigit() or len(low) < 3:
            if cur:
                phrases.append(cur)
            cur = []
        else:
            cur.append(low)
    if cur:
        phrases.append(cur)
    phrases = [p[:3] for p in phrases if p]
    if not phrases:
        return []
    freq: Counter = Counter()
    degree: Counter = Counter()
    for p in phrases:
        for w in p:
            freq[w] += 1
            degree[w] += len(p)
    scores: dict[str, float] = {}
    for p in phrases:
        key = " ".join(p)
        s = sum(degree[w] / freq[w] for w in p)
        if doc_freq is not None and n_docs > 1:
            idf = sum(math.log(1 + n_docs / (1 + doc_freq.get(stem(w), 0))) for w in p) / len(p)
            s *= idf
        scores[key] = max(scores.get(key, 0.0), s + 0.5 * phrases.count(p))
    counts = Counter(" ".join(p) for p in phrases)
    if min_freq > 1:
        scores = {k: v for k, v in scores.items() if counts[k] >= min_freq}
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    out: list[str] = []
    seen_stems: set[tuple[str, ...]] = set()
    for phrase, _ in ranked:
        st = tuple(stem(w) for w in phrase.split())
        if st in seen_stems:
            continue
        seen_stems.add(st)
        out.append(phrase)
        if len(out) >= top_k:
            break
    return out


def title_case(phrase: str) -> str:
    small = {"of", "and", "the", "in", "on", "to", "for", "a", "an", "vs"}
    words = phrase.split()
    return " ".join(w if (i and w.lower() in small) else (w[:1].upper() + w[1:]) for i, w in enumerate(words))
