from __future__ import annotations
import re
from .db import EvidenceDB
from .models import CandidateTrace, EvidenceUnit, RetrievalResult, RetrievalTrace

class HybridRetriever:
    def __init__(
        self,
        db: EvidenceDB,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        model=None,
        chroma_store=None,
    ):
        self.db = db
        self.model_name = model_name
        self.model = model
        self.chroma_store = chroma_store

    def _model(self):
        if self.model is None:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.model_name)
        return self.model

    @staticmethod
    def _token_overlap(q: str, t: str) -> float:
        a = set(re.findall(r"\w+", q.lower()))
        b = set(re.findall(r"\w+", t.lower()))
        return len(a & b) / max(1, len(a))

    def _lexical_scores(self, query: str, rows: list[EvidenceUnit]) -> list[float]:
        matched = dict(self.db.fts_search(query))
        if not matched:
            return [0.0] * len(rows)

        # SQLite FTS5 bm25 returns negative values where more negative = better match.
        # Compute raw positive relevance: raw = -rank.
        raw_scores = {eid: max(0.0, -rank) for eid, rank in matched.items()}
        max_raw = max(raw_scores.values()) if raw_scores else 1.0
        if max_raw <= 0.0:
            max_raw = 1.0

        return [round(raw_scores.get(e.evidence_id, 0.0) / max_raw, 6) for e in rows]

    def search(self, query: str, k: int = 5, mode: str = "hybrid") -> tuple[list[RetrievalResult], RetrievalTrace]:
        if not query or not query.strip():
            return [], RetrievalTrace(
                query=query,
                mode=mode,
                candidate_count=0,
                result_count=0,
                result_ids=[],
                source_ids=[],
                candidates=[],
                scores=[],
                ranking=[],
                unsupported=True,
                reason="empty query"
            )

        if mode not in {"lexical", "semantic", "hybrid"}:
            return [], RetrievalTrace(
                query=query,
                mode=mode,
                candidate_count=0,
                result_count=0,
                result_ids=[],
                source_ids=[],
                candidates=[],
                scores=[],
                ranking=[],
                unsupported=True,
                reason="unsupported retrieval mode"
            )

        rows = list(self.db.all_evidence())
        if not rows:
            return [], RetrievalTrace(
                query=query,
                mode=mode,
                candidate_count=0,
                result_count=0,
                result_ids=[],
                source_ids=[],
                candidates=[],
                scores=[],
                ranking=[],
                unsupported=True,
                reason="empty evidence index"
            )

        lex = self._lexical_scores(query, rows)
        sem = [0.0] * len(rows)

        if mode in ("semantic", "hybrid"):
            has_chroma = self.chroma_store is not None and self.chroma_store.count() > 0
            has_sqlite = any(self.db.get_embedding(e.evidence_id) is not None for e in rows)
            has_any_embedding = has_chroma or has_sqlite

            if mode == "semantic" and not has_any_embedding:
                return [], RetrievalTrace(
                    query=query,
                    mode=mode,
                    candidate_count=len(rows),
                    result_count=0,
                    result_ids=[],
                    source_ids=[],
                    candidates=[],
                    scores=[],
                    ranking=[],
                    unsupported=True,
                    reason="missing semantic embeddings"
                )

            if has_any_embedding:
                import numpy as np
                qv = self._model().encode([query], normalize_embeddings=True)[0]
                if has_chroma:
                    chroma_res = {
                        r["evidence_id"]: r["similarity"]
                        for r in self.chroma_store.query(qv, top_k=max(len(rows), 1))
                    }
                    for i, e in enumerate(rows):
                        if e.evidence_id in chroma_res:
                            sem[i] = chroma_res[e.evidence_id]
                        else:
                            v = self.db.get_embedding(e.evidence_id)
                            if v is not None:
                                sem[i] = float(np.dot(qv, v))
                else:
                    for i, e in enumerate(rows):
                        v = self.db.get_embedding(e.evidence_id)
                        if v is not None:
                            if v.shape[0] != qv.shape[0]:
                                raise ValueError(
                                    f"Embedding dimension mismatch: query dimension {qv.shape[0]} != evidence dimension {v.shape[0]}"
                                )
                            sem[i] = float(np.dot(qv, v))

        if mode == "lexical":
            scores = lex
        elif mode == "semantic":
            scores = sem
        else:
            scores = [round(0.45 * a + 0.55 * b, 6) for a, b in zip(lex, sem)]

        ranked = sorted(range(len(rows)), key=lambda i: (-round(scores[i], 6), rows[i].evidence_id))
        out = [
            RetrievalResult(
                evidence_id=rows[i].evidence_id,
                score=float(scores[i]),
                lexical_score=float(lex[i]),
                semantic_score=float(sem[i]),
                source_id=rows[i].source_id,
                snippet=rows[i].text[:500],
                location=rows[i].location
            )
            for i in ranked[:max(0, k)]
            if scores[i] > 0
        ]

        scores_trace = [
            CandidateTrace(
                evidence_id=r.evidence_id,
                source_id=r.source_id,
                lexical_score=r.lexical_score,
                semantic_score=r.semantic_score,
                score=r.score,
                rank=idx + 1
            )
            for idx, r in enumerate(out)
        ]

        unsupported = (len(out) == 0)
        reason = None if not unsupported else "no supported evidence matched"

        trace = RetrievalTrace(
            query=query,
            mode=mode,
            candidate_count=len(rows),
            result_count=len(out),
            result_ids=[x.evidence_id for x in out],
            source_ids=list(dict.fromkeys(x.source_id for x in out)),
            candidates=scores_trace,
            scores=scores_trace,
            ranking=[x.evidence_id for x in out],
            unsupported=unsupported,
            reason=reason
        )
        return out, trace

def build_embeddings(
    db: EvidenceDB,
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    model=None,
    chroma_store=None,
):
    if model is None:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(model_name)
    units = list(db.all_evidence())
    embeddings = []
    for e in units:
        vec = model.encode(e.text, normalize_embeddings=True)
        db.add_embedding(e.evidence_id, vec, model_name=model_name)
        embeddings.append(vec)
    if chroma_store is not None and units:
        chroma_store.batch_add_evidence(units, embeddings)

