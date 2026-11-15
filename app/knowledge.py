"""Build a topic and concept map from parsed evidence.

1. Segment each source into topics. Use document headings where they exist
   (PDF font size, slide titles, markdown headings). Where they don't
   (transcripts), cut at drops in lexical cohesion between neighbouring
   chunks (TextTiling idea).
2. Merge segments that are too small, and cap topics per source.
3. Pick concepts per topic: defined terms first ("X is ...", "X states that"),
   then IDF-weighted keyphrases.
4. Infer prerequisites by definition-before-use: if topic B uses a concept
   that topic A defines, and B does not define it, then A is a prerequisite
   of B. Edges that would create a cycle are dropped.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from .models import EvidenceUnit, TopicRecord
from .nlp import content_terms, keyphrases, normalize, sentences, slugify, stem, term_set, title_case, word_count

MIN_TOPIC_WORDS = 35
MAX_TOPICS_PER_SOURCE = 14

_DEF_PATTERNS = [
    re.compile(r"^(?:the\s+)?(?P<term>[A-Z][\w'\- ]{2,60}?)\s+(?:is|are)\s+(?:defined as|called|known as)\s+(?P<body>.+)$", re.I),
    re.compile(r"^(?:the\s+)?(?P<term>[A-Z][\w'\- ]{2,60}?)\s+(?:states|says|describes|explains)\s+that\s+(?P<body>.+)$", re.I),
    re.compile(r"^(?:the\s+)?(?P<term>[A-Z][\w'\- ]{2,50}?)\s*(?:\([^)]*\))?\s*(?:is|are|refers to|means)\s+(?P<body>(?:a|an|the)\s+.+)$", re.I),
    re.compile(r"^(?P<term>[A-Z][\w'\- ]{2,50}?)\s*[:–—-]\s+(?P<body>[A-Z].{15,})$"),
]
_GENERIC_HEADINGS = re.compile(r"^(slide \d+|page \d+|introduction|overview|summary|contents|table of contents|agenda|outline|references|questions\??)$", re.I)
_NUM_PREFIX = re.compile(r"^\s*(?:chapter|unit|lecture|section|module|part)?\s*\d+(?:\.\d+)*\s*[.):\-–]?\s*", re.I)


@dataclass
class Definition:
    term: str
    sentence: str
    evidence_id: str


@dataclass
class TopicDraft:
    name: str
    units: list[EvidenceUnit] = field(default_factory=list)
    heading: str = ""

    @property
    def text(self) -> str:
        return "\n".join(u.text for u in self.units if u.evidence_type != "figure")

    @property
    def words(self) -> int:
        return word_count(self.text)


def clean_heading(h: str) -> str:
    h = _NUM_PREFIX.sub("", normalize(h)).strip(" :.-–")
    h = re.sub(r"\s+", " ", h)
    if h.isupper() and len(h) > 4:
        h = title_case(h.lower())
    return h


def find_definitions(units: list[EvidenceUnit]) -> list[Definition]:
    out: list[Definition] = []
    seen: set[str] = set()
    for u in units:
        if u.evidence_type == "figure":
            continue
        for s in sentences(u.text):
            s_clean = re.sub(r"^\s*(?:\d+[.)]|[-*•])\s*", "", s).strip()
            if word_count(s_clean) < 6 or word_count(s_clean) > 70:
                continue
            for pat in _DEF_PATTERNS:
                m = pat.match(s_clean)
                if not m:
                    continue
                term = m.group("term").strip(" ,:")
                term = re.sub(r"^(?:the|a|an)\s+", "", term, flags=re.I)
                if (word_count(term) > 6 or term.lower() in {"this", "it", "there", "that", "which", "these", "here"}
                        or term.lower().startswith(("where ", "when ", "if ", "for ", "in ", "this ", "it "))):
                    continue
                key = " ".join(stem(t) for t in term.lower().split())
                if key in seen:
                    continue
                seen.add(key)
                out.append(Definition(term=term, sentence=s_clean, evidence_id=u.evidence_id))
                break
    return out


def _vec(text: str) -> Counter:
    return Counter(content_terms(text))


def _cos(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    dot = sum(v * b.get(k, 0) for k, v in a.items())
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


def _segment_by_cohesion(units: list[EvidenceUnit], title: str) -> list[TopicDraft]:
    """TextTiling-style cut points where neighbour similarity dips."""
    text_units = [u for u in units if u.evidence_type != "figure"]
    if len(text_units) <= 3:
        return [TopicDraft(name=title, units=list(units))]
    vecs = [_vec(u.text) for u in text_units]
    sims = [_cos(vecs[i], vecs[i + 1]) for i in range(len(vecs) - 1)]
    mean = sum(sims) / len(sims)
    sd = math.sqrt(sum((s - mean) ** 2 for s in sims) / len(sims))
    cuts = {i + 1 for i, s in enumerate(sims) if s < mean - 0.5 * sd}
    drafts: list[TopicDraft] = []
    cur = TopicDraft(name="")
    for i, u in enumerate(text_units):
        if i in cuts and len(cur.units) >= 2:
            drafts.append(cur)
            cur = TopicDraft(name="")
        cur.units.append(u)
    drafts.append(cur)
    # Attach figures to the draft holding the nearest preceding unit.
    order = {u.evidence_id: i for i, u in enumerate(units)}
    for f in (u for u in units if u.evidence_type == "figure"):
        best = drafts[0]
        for d in drafts:
            if d.units and order[d.units[0].evidence_id] <= order[f.evidence_id]:
                best = d
        best.units.append(f)
    return drafts


def segment_source(units: list[EvidenceUnit], title: str) -> list[TopicDraft]:
    has_headings = any(u.section and u.section != title for u in units)
    if not has_headings:
        drafts = _segment_by_cohesion(units, title)
    else:
        drafts = []
        for u in units:
            sec = u.section or title
            if drafts and drafts[-1].heading == sec:
                drafts[-1].units.append(u)
            else:
                drafts.append(TopicDraft(name=clean_heading(sec), units=[u], heading=sec))

    # Merge small or generic segments into a neighbour.
    def mergeable(d: TopicDraft) -> bool:
        return d.words < MIN_TOPIC_WORDS or bool(_GENERIC_HEADINGS.match(d.name or ""))

    changed = True
    while changed and len(drafts) > 1:
        changed = False
        for i, d in enumerate(drafts):
            if not mergeable(d):
                continue
            # merge into the more similar neighbour; prefer the previous one on ties
            cands = [j for j in (i - 1, i + 1) if 0 <= j < len(drafts)]
            j = max(cands, key=lambda j: (_cos(_vec(d.text), _vec(drafts[j].text)) + (0.05 if j < i else 0)))
            tgt = drafts[j]
            if j > i:
                tgt.units = d.units + tgt.units
                if _GENERIC_HEADINGS.match(tgt.name or "") and d.name and not _GENERIC_HEADINGS.match(d.name):
                    tgt.name = d.name
            else:
                tgt.units = tgt.units + d.units
            drafts.pop(i)
            changed = True
            break
    while len(drafts) > MAX_TOPICS_PER_SOURCE:
        # merge the adjacent pair with the highest similarity
        best_i, best_s = 0, -1.0
        for i in range(len(drafts) - 1):
            s = _cos(_vec(drafts[i].text), _vec(drafts[i + 1].text))
            if s > best_s:
                best_i, best_s = i, s
        a, b = drafts[best_i], drafts.pop(best_i + 1)
        a.units += b.units
    return drafts


def _name_for(d: TopicDraft, title: str, doc_freq: Counter, n_docs: int, single: bool, defs: list[Definition]) -> str:
    if d.name and not _GENERIC_HEADINGS.match(d.name) and word_count(d.name) <= 10:
        return d.name
    if single:
        return re.sub(r"\s*\([^)]*\)\s*$", "", title).strip() or title
    terms = [x.term for x in defs if word_count(x.term) <= 3][:2]
    if terms:
        return title_case(" and ".join(terms))
    kp = keyphrases(d.text, top_k=1, doc_freq=doc_freq, n_docs=n_docs, min_freq=2)
    return title_case(kp[0]) if kp else title_case(title)


def build_topics(
    source_id: str,
    owner_id: str,
    title: str,
    units: list[EvidenceUnit],
    position_offset: int = 0,
) -> tuple[list[TopicRecord], dict[str, list[str]], dict[str, list[Definition]]]:
    """Return topics, evidence->topic ids, and topic->definitions for one source."""
    drafts = segment_source(units, title)
    doc_freq: Counter = Counter()
    for d in drafts:
        doc_freq.update(term_set(d.text))
    n_docs = max(2, len(drafts))
    topics: list[TopicRecord] = []
    tags: dict[str, list[str]] = defaultdict(list)
    defs_by_topic: dict[str, list[Definition]] = {}
    used_ids: set[str] = set()
    for pos, d in enumerate(drafts):
        defs = find_definitions(d.units)
        name = _name_for(d, title, doc_freq, n_docs, len(drafts) == 1, defs)
        tid = f"{source_id}:{slugify(name, 40)}"
        k = 2
        while tid in used_ids:
            tid = f"{source_id}:{slugify(name, 40)}-{k}"
            k += 1
        used_ids.add(tid)
        concepts: list[str] = []
        seen_st: set[str] = set()
        for df in defs:
            st = " ".join(content_terms(df.term))
            if st not in seen_st:
                seen_st.add(st)
                concepts.append(df.term)
        stem_counts = Counter(content_terms(d.text))
        for kp in keyphrases(d.text, top_k=12, doc_freq=doc_freq, n_docs=n_docs, min_freq=2):
            st = " ".join(content_terms(kp))
            if len(kp.split()) == 1 and kp.lower() not in (d.name or "").lower():
                continue
            if re.search(r"[\d_]", kp):
                continue
            if st in seen_st or any(st in s or s in st for s in seen_st):
                continue
            seen_st.add(st)
            concepts.append(title_case(kp))
            if len(concepts) >= 8:
                break
        first = next((s for u in d.units if u.evidence_type != "figure" for s in sentences(u.text) if word_count(s) >= 6), "")
        topics.append(TopicRecord(
            topic_id=tid, owner_id=owner_id, name=name, description=first[:220], source_id=source_id,
            position=position_offset + pos, concepts=concepts[:8],
        ))
        defs_by_topic[tid] = defs
        for u in d.units:
            tags[u.evidence_id].append(tid)
    return topics, dict(tags), defs_by_topic


_CUE = re.compile(r"\b(requires?|required|needed before|builds? on|depends? on|prerequisites?|assumes?|before working with|covered in)\b", re.I)


def infer_prerequisites(topics: list[TopicRecord], topic_text: dict[str, str],
                        defs_by_topic: dict[str, list[Definition]], max_prereqs: int = 3) -> None:
    """Definition-before-use edges, kept acyclic. Mutates ``topics`` in place.

    Rules (to keep edges meaningful rather than lexical noise):
      * within one source, the defining topic must come earlier;
      * across sources, only multi-word terms count (e.g. "net force");
      * single-word terms must be used at least twice in the dependent topic;
      * an explicit cue ("requires", "needed before", "builds on") that names a
        concept of another topic always counts.
    """
    by_id = {t.topic_id: t for t in topics}
    defined: dict[str, str] = {}
    for t in sorted(topics, key=lambda t: t.position):
        for d in defs_by_topic.get(t.topic_id, []):
            defined.setdefault(" ".join(content_terms(d.term)), t.topic_id)
    graph: dict[str, set[str]] = {t.topic_id: set() for t in topics}

    def reaches(a: str, b: str) -> bool:
        stack, seen = [a], set()
        while stack:
            x = stack.pop()
            if x == b:
                return True
            if x in seen:
                continue
            seen.add(x)
            stack.extend(graph.get(x, ()))
        return False

    def allowed(owner: str, t: TopicRecord, key: str, count: int) -> bool:
        o = by_id[owner]
        multi = len(key.split()) >= 2
        if o.source_id == t.source_id:
            return o.position < t.position and (multi or count >= 2)
        return multi and count >= 1

    for t in sorted(topics, key=lambda t: t.position):
        own = {" ".join(content_terms(d.term)) for d in defs_by_topic.get(t.topic_id, [])}
        text = topic_text.get(t.topic_id, "")
        stems_text = " " + " ".join(content_terms(text)) + " "
        votes: Counter = Counter()
        for key, owner in defined.items():
            if owner == t.topic_id or key in own or not key:
                continue
            count = stems_text.count(f" {key} ")
            if count and allowed(owner, t, key, count):
                votes[owner] += count
        for sent in sentences(text):
            if not _CUE.search(sent):
                continue
            st = " " + " ".join(content_terms(sent)) + " "
            for key, owner in defined.items():
                if key and owner != t.topic_id and key not in own and f" {key} " in st:
                    o = by_id[owner]
                    if (o.source_id == t.source_id and o.position < t.position) or len(key.split()) >= 2:
                        votes[owner] += 5
        for owner, _ in votes.most_common():
            if len(graph[t.topic_id]) >= max_prereqs:
                break
            if reaches(owner, t.topic_id):
                continue
            graph[t.topic_id].add(owner)
    for t in topics:
        t.prerequisites = sorted(graph[t.topic_id], key=lambda x: by_id[x].position)


def concepts_in(text: str, concepts: list[str]) -> list[str]:
    stems_text = " " + " ".join(content_terms(text)) + " "
    out = []
    for c in concepts:
        key = " ".join(content_terms(c))
        if key and f" {key} " in stems_text:
            out.append(c)
    return out
