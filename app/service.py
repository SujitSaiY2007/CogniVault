"""Application service: ties parsing, knowledge map, retrieval, tutoring,
assessment, learner model and persistence together.

All methods take an ``owner_id`` (the signed-in learner) and only ever see
the shared demo course plus that owner's own uploads.
"""
from __future__ import annotations

import hashlib
import logging
import threading
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any, Optional

from .config import Settings, load_settings
from .db import Database, now_iso
from .embeddings import Embedder, make_embedder
from .grounding import GENERAL_SYSTEM, citation_for, compose, gate
from .ingest import IngestError, ParsedSource, locator_label, parse_file
from .knowledge import Definition, build_topics, concepts_in, find_definitions, infer_prerequisites
from .learner import MASTERED, READY, LearnerModel, decayed
from .llm import LLM, LLMError, make_llm
from .models import (
    PUBLIC_OWNER, AnswerEvaluation, Difficulty, EvidenceUnit, Modality, Question, QuestionType, TopicRecord, TutorResponse,
)
from .persistence import Backend, LocalBackend, StorageError, SupabaseBackend
from .questions import (
    cloze_questions, definition_mcqs, finalize, find_formulas, grade, llm_mcqs, numerical_questions,
)
from .retrieval import Retriever, expand_followup
from .study import build_cards, course_map, due_cards, review_card, study_plan

log = logging.getLogger("cognivault.service")

MIME = {".pdf": "application/pdf", ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".txt": "text/plain", ".md": "text/plain", ".vtt": "text/vtt", ".srt": "application/x-subrip"}


class ServiceError(ValueError):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


class CogniVault:
    def __init__(self, settings: Optional[Settings] = None, db: Optional[Database] = None, llm: Optional[LLM] = None,
                 embedder: Optional[Embedder] = None, backend: Optional[Backend] = None):
        self.settings = settings or load_settings()
        self.db = db or Database(self.settings.db_path)
        self.embedder = embedder or make_embedder(self.settings.embedding_provider, self.settings.gemini_api_key,
                                                  self.settings.gemini_embed_model)
        self.llm = llm if llm is not None else make_llm(self.settings.model_provider, self.settings.gemini_api_key,
                                                        self.settings.gemini_model, self.settings.ollama_host,
                                                        self.settings.ollama_model)
        if backend is not None:
            self.backend = backend
        elif self.settings.supabase_enabled:
            self.backend = SupabaseBackend(self.settings.supabase_url, self.settings.supabase_service_role_key)
        else:
            self.backend = LocalBackend(self.db)
        self.retriever = Retriever(self.db, self.embedder)
        self.learner = LearnerModel(self.db)
        self._defs: dict[str, list[Definition]] = {}
        self._hydrated: set[str] = set()
        self._owner_locks: dict[str, threading.RLock] = defaultdict(threading.RLock)

    # ================================================================ setup
    def owner_lock(self, owner_id: str) -> threading.RLock:
        return self._owner_locks[owner_id]

    def seed_demo_course(self, corpus_dir: Optional[Path] = None) -> dict[str, Any]:
        """Load the bundled demo course into the shared ``public`` scope (idempotent)."""
        from .corpus import DEMO_TITLES, ensure_corpus

        from .config import ROOT

        corpus_dir = corpus_dir or (ROOT / "data" / "corpus")
        files = ensure_corpus(corpus_dir)
        added = 0
        for path in files:
            sid = "demo-" + path.stem.replace("_", "-")
            if self.db.get_source(sid):
                continue
            self.ingest(PUBLIC_OWNER, path.read_bytes(), path.name, title=DEMO_TITLES.get(path.name), source_id=sid,
                        persist=False, rebuild=False)
            added += 1
        if added:
            self.rebuild_knowledge(PUBLIC_OWNER)
        return {"sources_added": added, "sources": len(self.db.sources(PUBLIC_OWNER))}

    # ============================================================== ingestion
    def ingest(self, owner_id: str, data: bytes, filename: str, title: Optional[str] = None, source_id: Optional[str] = None,
               persist: bool = True, rebuild: bool = True) -> dict[str, Any]:
        ext = Path(filename).suffix.lower()
        sha = hashlib.sha256(data).hexdigest()
        for s in self.db.sources(owner_id, include_public=False):
            if s.sha256 == sha:
                raise ServiceError("This file is already in your library.", 409)
        sid = source_id or ("src-" + hashlib.sha256(f"{owner_id}:{sha}".encode()).hexdigest()[:20])
        try:
            parsed = parse_file(data, filename, sid, title, owner_id)
        except IngestError as exc:
            raise ServiceError(str(exc), 422) from exc
        parsed.source.metadata["file_size_bytes"] = len(data)
        self._store_parsed(parsed)
        self._describe_figures(parsed)
        if persist and self.backend.durable:
            rows = [{"evidence_id": u.evidence_id, "owner_id": owner_id, "source_id": sid, "modality": u.modality.value,
                     "evidence_text": u.text, "location": u.location, "evidence_type": u.evidence_type,
                     "metadata": {**u.metadata, "section": u.section, "source_title": parsed.source.title}} for u in parsed.units]
            src_row = {"source_id": sid, "filename": Path(filename).name, "title": parsed.source.title,
                       "modality": parsed.source.modality.value, "sha256": sha, "evidence_count": len(parsed.units),
                       "file_size_bytes": len(data)}
            try:
                self.backend.save_file(owner_id, src_row, data, MIME.get(ext, "application/octet-stream"), rows)
            except StorageError as exc:
                self.db.delete_source(sid)
                self.retriever.invalidate(owner_id)
                raise ServiceError(f"Upload could not be saved: {exc}", 503) from exc
        topics = self.rebuild_knowledge(owner_id, only_source=sid) if rebuild else []
        if persist:
            self.save_progress(owner_id)
        n_q = sum(len(self.db.questions(owner_id, t.topic_id)) for t in topics)
        return {
            "source_id": sid, "title": parsed.source.title, "modality": parsed.source.modality.value, "sha256": sha,
            "evidence_count": len(parsed.units), "figure_count": sum(1 for u in parsed.units if u.evidence_type == "figure"),
            "topics": [{"topic_id": t.topic_id, "name": t.name} for t in topics], "question_count": n_q,
            "warnings": parsed.warnings, "status": "indexed",
        }

    def _store_parsed(self, parsed: ParsedSource) -> None:
        self.db.add_source(parsed.source)
        self.db.add_evidence(parsed.units)
        for aid, eid, mime, blob in parsed.assets:
            self.db.add_asset(aid, eid, mime, blob)
        self.retriever.ensure_embeddings()
        self.retriever.invalidate(parsed.source.owner_id)

    def _describe_figures(self, parsed: ParsedSource, limit: int = 6) -> None:
        """With a vision model, replace weak figure captions with a description."""
        describe = getattr(self.llm, "describe_image", None)
        if not describe or not self.llm.available:
            return
        changed = []
        for aid, eid, mime, blob in parsed.assets[:limit]:
            unit = self.db.get_evidence(eid)
            if unit is None:
                continue
            try:
                desc = describe(blob, mime, f"{unit.section}. {unit.metadata.get('caption', '')}")
            except LLMError:
                break
            if desc:
                unit.text = f"{unit.text}. Figure description (AI-generated from the image): {desc}"
                unit.metadata["ai_description"] = True
                changed.append(unit)
        if changed:
            self.db.add_evidence(changed)
            self.db._x("DELETE FROM embeddings WHERE evidence_id IN (%s)" % ",".join("?" * len(changed)), [u.evidence_id for u in changed])
            self.retriever.ensure_embeddings()

    def rebuild_knowledge(self, owner_id: str, only_source: Optional[str] = None) -> list[TopicRecord]:
        """(Re)build topics, prerequisites and the question bank for an owner's sources."""
        sources = self.db.sources(owner_id, include_public=False)
        existing = {t.topic_id: t for t in self.db.topics(owner_id) if t.owner_id == owner_id}
        new_topics: list[TopicRecord] = []
        offset = 0
        for s in sources:
            units = self.db.evidence_for_source(s.source_id)
            if only_source and s.source_id != only_source:
                offset += len([t for t in existing.values() if t.source_id == s.source_id])
                continue
            stale = [tid for tid, t in existing.items() if t.source_id == s.source_id]
            self.db.delete_questions_for_topics(stale)
            self.db._x("DELETE FROM topics WHERE source_id=?", (s.source_id,))
            topics, tags, defs = build_topics(s.source_id, owner_id, s.title, units, position_offset=offset)
            offset += len(topics)
            by_tid = {t.topic_id: t for t in topics}
            for u in units:
                tids = tags.get(u.evidence_id, [])
                cons = sorted({c for tid in tids for c in concepts_in(u.text, by_tid[tid].concepts)})
                self.db.update_evidence_tags(u.evidence_id, tids, cons)
            self.db.put_topics(topics)
            self._defs.update(defs)
            new_topics.extend(topics)
        # Prerequisites across all of this owner's topics.
        all_topics = [t for t in self.db.topics(owner_id) if t.owner_id == owner_id]
        texts = {t.topic_id: " ".join(u.text for u in self.db.evidence_for_topic(t.topic_id)) for t in all_topics}
        for t in all_topics:
            t.prerequisites = []
            if t.topic_id not in self._defs:
                self._defs[t.topic_id] = find_definitions(self.db.evidence_for_topic(t.topic_id))
        infer_prerequisites(all_topics, texts, self._defs)
        self.db.put_topics(all_topics)
        self.retriever.invalidate(owner_id)
        for t in new_topics or all_topics:
            self.build_question_bank(owner_id, self.db.get_topic(t.topic_id) or t)
        return [self.db.get_topic(t.topic_id) or t for t in new_topics]

    def definitions(self, topic_id: str) -> list[Definition]:
        if topic_id not in self._defs:
            self._defs[topic_id] = find_definitions(self.db.evidence_for_topic(topic_id))
        return self._defs[topic_id]

    def build_question_bank(self, owner_id: str, topic: TopicRecord, use_llm: bool = True) -> list[Question]:
        units = self.db.evidence_for_topic(topic.topic_id)
        defs = self.definitions(topic.topic_id)
        pool = [(t.topic_id, d) for t in self.db.topics(owner_id) if t.owner_id == topic.owner_id for d in self.definitions(t.topic_id)]
        titles = {s.source_id: s.title for s in self.db.sources(owner_id)}
        cands: list[Question] = []
        cands += definition_mcqs(topic, defs, pool, seed=topic.topic_id)
        cands += cloze_questions(topic, defs)
        for u in units:
            for f in find_formulas(u):
                cands += numerical_questions(f, topic, f"{titles.get(u.source_id, 'course')}, {locator_label(u.location)}", seed=u.evidence_id + f.text)
        if use_llm and self.llm.available and len(cands) < 6:
            idx = self.retriever.index(owner_id)
            for u in [x for x in units if x.evidence_type != "figure"][:2]:
                cands += llm_mcqs(self.llm, topic, u, idx)
        existing = self.db.questions(owner_id, topic.topic_id, verified_only=False)
        valid_ids = {u.evidence_id for u in units}
        kept = finalize(cands, valid_ids, existing)
        for q in kept:
            self.db.put_question(q)
        return kept

    def delete_source(self, owner_id: str, source_id: str) -> None:
        s = self.db.get_source(source_id)
        if not s or s.owner_id != owner_id:
            raise ServiceError("Source not found.", 404)
        if self.backend.durable:
            try:
                self.backend.delete_file(owner_id, source_id)
            except StorageError as exc:
                raise ServiceError(f"Could not delete the stored file: {exc}", 503) from exc
        topic_ids = [t.topic_id for t in self.db.topics(owner_id) if t.source_id == source_id]
        self.db.delete_questions_for_topics(topic_ids)
        self.db.delete_source(source_id)
        for tid in topic_ids:
            self._defs.pop(tid, None)
        self.retriever.invalidate(owner_id)
        self.rebuild_knowledge(owner_id, only_source="__none__")
        self.save_progress(owner_id)

    # ============================================================ persistence
    def hydrate(self, owner_id: str) -> None:
        """Restore an owner's files and progress after a server restart (once per process)."""
        if owner_id in self._hydrated or not self.backend.durable:
            self._hydrated.add(owner_id)
            return
        with self.owner_lock(owner_id):
            if owner_id in self._hydrated:
                return
            files = self.backend.list_files(owner_id)
            restored = False
            for f in files:
                if self.db.get_source(f["source_id"]):
                    continue
                data = self.backend.load_file(owner_id, f["source_id"])
                if not data:
                    log.warning("Stored file for %s missing", f["source_id"])
                    continue
                try:
                    parsed = parse_file(data, f["filename"], f["source_id"], f.get("title"), owner_id)
                except IngestError:
                    continue
                parsed.source.metadata["file_size_bytes"] = len(data)
                self._store_parsed(parsed)
                restored = True
            if restored:
                self.rebuild_knowledge(owner_id)
            snap = self.backend.load_snapshot(owner_id)
            if snap and isinstance(snap, dict) and snap.get("version") == 2:
                self.db.import_owner(owner_id, snap.get("tables", {}))
                self.retriever.invalidate(owner_id)
            self._hydrated.add(owner_id)

    def save_progress(self, owner_id: str) -> None:
        if not self.backend.durable or owner_id == PUBLIC_OWNER:
            return
        try:
            self.backend.save_snapshot(owner_id, {"version": 2, "saved_at": now_iso(), "tables": self.db.export_owner(owner_id)})
        except StorageError as exc:
            log.warning("Snapshot save failed for %s: %s", owner_id, exc)

    # ================================================================= tutor
    def source_titles(self, owner_id: str) -> dict[str, str]:
        return {s.source_id: s.title for s in self.db.sources(owner_id)}

    def ask(self, owner_id: str, query: str, history: Optional[list[str]] = None, topic_id: Optional[str] = None,
            source_ids: Optional[list[str]] = None, allow_general: bool = False) -> TutorResponse:
        query = (query or "").strip()
        if not query:
            raise ServiceError("Ask a question first.")
        if len(query) > 2000:
            raise ServiceError("Questions are limited to 2,000 characters.")
        effective = expand_followup(query, history or [])
        idx = self.retriever.index(owner_id)
        if not idx.units:
            return TutorResponse(query=query, answer="Your library is empty. Upload course material first.", is_grounded=False,
                                 support_status="unsupported", unsupported_reason="No course material indexed yet.")
        hits = self.retriever.search(effective, owner_id, k=5, source_ids=set(source_ids) if source_ids else None, topic_id=topic_id)
        decision = gate(effective, hits, idx)
        steps = [f"Searched {len(idx.units)} passages (BM25 + embeddings, RRF fusion).",
                 f"Question coverage by top passages: {decision.coverage:.0%} (needs 60%)."]
        if effective != query:
            steps.insert(0, "Treated as a follow-up to your previous question.")
        titles = self.source_titles(owner_id)
        if not decision.supported:
            steps.append(f"Abstained: {decision.reason}")
            answer = ("I can't answer this from your course material. " + decision.reason)
            general = None
            if allow_general and self.llm.available:
                try:
                    general = self.llm.generate(query, system=GENERAL_SYSTEM, temperature=0.3, max_tokens=350)
                except LLMError:
                    general = None
            meta: dict[str, Any] = {"missing_terms": decision.missing_terms[:8]}
            if general:
                answer += "\n\nOutside your course material (general knowledge, not verified against your sources):\n" + general
                meta["general_knowledge"] = True
            near = [citation_for(h.unit, titles.get(h.unit.source_id, "")) for h in hits[:2] if h.coverage >= 0.3]
            if near:
                meta["closest_passages"] = [c.model_dump() for c in near]
            meta["coverage"] = round(decision.coverage, 3)
            return TutorResponse(query=query, answer=answer, is_grounded=False, support_status="unsupported",
                                 confidence=0.0, unsupported_reason=decision.reason, reasoning_steps=steps,
                                 generator="general" if general else "none", metadata=meta)
        composed = compose(effective, hits, idx, self.embedder, self.llm, titles)
        citations = [citation_for(u, titles.get(u.source_id, ""), self.db.get_source(u.source_id).path if self.db.get_source(u.source_id) else "")
                     for u in composed.used]
        topics = list(dict.fromkeys(t for u in composed.used for t in u.topics))
        steps.append(f"Answer written by {'the ' + composed.generator + ' model and verified sentence by sentence' if composed.generator != 'extractive' else 'extracting the best-matching sentences'}.")
        steps.extend(composed.notes)
        answer = composed.answer
        status = "supported"
        if decision.partial or composed.downgrade:
            status = "partial"
            reason = decision.reason if decision.partial else "The passages below may not fully answer this question."
            answer = (reason + " Here is what your material does say:\n\n" + answer)
            steps.append("Partial support: some question terms are not in the material.")
        if owner_id != PUBLIC_OWNER:
            for tid in topics[:2]:
                self.learner.observe_instruction(owner_id, tid)
            self.save_progress(owner_id)
        topic_names = {t.topic_id: t.name for t in self.db.topics(owner_id)}
        return TutorResponse(
            query=query, answer=answer, citations=citations, is_grounded=True,
            is_synthesis=len({c.source_id for c in citations}) > 1, confidence=decision.confidence, support_status=status,
            reasoning_steps=steps, topics=[topic_names.get(t, t) for t in topics], generator=composed.generator,
            metadata={"faithfulness": composed.faithfulness, "topic_ids": topics},
        )

    # ============================================================ assessment
    def topic_names(self, owner_id: str) -> dict[str, str]:
        return {t.topic_id: t.name for t in self.db.topics(owner_id)}

    def next_question(self, owner_id: str, topic_id: str, difficulty: Optional[Difficulty] = None,
                      exclude: Optional[list[str]] = None, qtype: Optional[QuestionType] = None) -> Optional[Question]:
        topic = self.db.get_topic(topic_id)
        if not topic or topic.owner_id not in {PUBLIC_OWNER, owner_id}:
            raise ServiceError("Topic not found.", 404)
        bank = self.db.questions(owner_id, topic_id)
        if qtype:
            bank = [q for q in bank if q.question_type == qtype] or bank
        return self.learner.select_question(owner_id, bank, difficulty, set(exclude or []))

    def submit(self, owner_id: str, question_id: str, answer: str, session_id: Optional[str] = None) -> dict[str, Any]:
        q = self.db.get_question(question_id)
        if not q or q.owner_id not in {PUBLIC_OWNER, owner_id}:
            raise ServiceError("Question not found.", 404)
        g = grade(q, answer)
        before, mastery = self.learner.observe(owner_id, q, g.score)
        misconception = None
        if g.is_correct:
            self.learner.record_success(owner_id, q)
        else:
            misconception = self.learner.record_error(owner_id, q, g.pattern)
        ts = now_iso()
        self.db.add_interaction({"interaction_id": f"int-{uuid.uuid4().hex[:16]}", "learner_id": owner_id, "question_id": q.question_id,
                                 "topic_id": q.topic_id, "answer": answer[:500], "is_correct": g.is_correct, "score": g.score,
                                 "timestamp": ts, "session_id": session_id, "p_before": before, "p_after": mastery.p_mastery})
        q.repetition_count += 1
        self.db.put_question(q)
        titles = self.source_titles(owner_id)
        cites = [citation_for(u, titles.get(u.source_id, "")) for u in (self.db.get_evidence(e) for e in q.evidence_ids) if u]
        where = ", ".join(f"{c.source_title} ({c.locator_label})" for c in cites)
        if g.is_correct:
            fb = "Correct." + (f" {g.detail}" if g.detail else "") + (f" Source: {where}." if where else "")
        elif g.status == "partially_correct":
            fb = f"Partly correct. {g.detail} The expected answer is {self._answer_text(q)}." + (f" Review: {where}." if where else "")
        else:
            fb = (f"Not quite. {g.detail} The correct answer is {self._answer_text(q)}." + (f" Review: {where}." if where else "")).replace("  ", " ")
        evaluation = AnswerEvaluation(
            learner_id=owner_id, question_id=q.question_id, is_correct=g.is_correct, status=g.status, score=g.score, feedback=fb,
            expected_answer=self._answer_text(q), solution=q.solution, citations=cites,
            remediation_action=None if g.is_correct else f"review_topic:{q.topic_id}",
            remediation_evidence_ids=[] if g.is_correct else q.evidence_ids,
        )
        mastery.topic_name = self.topic_names(owner_id).get(q.topic_id, q.topic_id)
        rec = self.learner.recommend(owner_id, self.db.topics(owner_id), q.topic_id)
        self.save_progress(owner_id)
        return {"evaluation": evaluation.model_dump(), "mastery": mastery.model_dump(), "p_before": round(before, 4),
                "misconception_detected": misconception is not None,
                "misconception": misconception.model_dump() if misconception else None,
                "next_recommendation": rec.model_dump()}

    @staticmethod
    def _answer_text(q: Question) -> str:
        if q.question_type == QuestionType.mcq:
            opt = next((o for o in q.options if o.key == q.expected_answer), None)
            return f"{q.expected_answer}. {opt.text}" if opt else q.expected_answer
        return q.expected_answer

    # ---------------------------------------------------------- quizzes/exams
    def create_quiz(self, owner_id: str, topic_ids: Optional[list[str]] = None, count: int = 8,
                    types: Optional[list[str]] = None, difficulty: Optional[str] = None, mode: str = "practice") -> dict[str, Any]:
        topics = self.db.topics(owner_id)
        valid = {t.topic_id for t in topics}
        chosen = [t for t in (topic_ids or []) if t in valid] or [t.topic_id for t in topics]
        if not chosen:
            raise ServiceError("No topics available. Upload course material first.", 404)
        count = max(1, min(40, count))
        wanted = {QuestionType(t) for t in (types or []) if t in {"mcq", "numerical", "short_answer"}} or set(QuestionType)
        diff = Difficulty(difficulty) if difficulty in {"easy", "medium", "hard"} else None
        # Allocate questions to topics, weaker topics get more (proportional to 1 - p, at least one each).
        weights = {t: 1.05 - self.learner.current(owner_id, t) for t in chosen}
        total_w = sum(weights.values())
        alloc = {t: max(1, round(count * w / total_w)) for t, w in weights.items()}
        picked: list[Question] = []
        used: set[str] = set()
        for tid in sorted(chosen, key=lambda t: -weights[t]):
            bank = [q for q in self.db.questions(owner_id, tid) if q.question_type in wanted]
            for _ in range(alloc[tid]):
                gens = [p.metadata.get("generator") for p in picked]
                avail = [b for b in bank if b.question_id not in used]
                # prefer a question type not yet used in this quiz
                fresh = [b for b in avail if b.metadata.get("generator") not in gens] or avail
                q = self.learner.select_question(owner_id, fresh, diff or self.learner.target_difficulty(owner_id, tid))
                if not q:
                    break
                picked.append(q)
                used.add(q.question_id)
        # Top up to the requested count from any topic in scope.
        pool = [q for tid in chosen for q in self.db.questions(owner_id, tid) if q.question_type in wanted and q.question_id not in used]
        while len(picked) < count and pool:
            q = self.learner.select_question(owner_id, pool, diff)
            picked.append(q)
            used.add(q.question_id)
            pool = [x for x in pool if x.question_id != q.question_id]
        picked = picked[:count]
        if not picked:
            raise ServiceError("No verified questions match that scope yet. Try other topics or question types.", 404)
        sid = f"quiz-{uuid.uuid4().hex[:12]}"
        data = {"session_id": sid, "mode": mode if mode in {"practice", "exam"} else "practice", "created_at": now_iso(),
                "topic_ids": chosen, "question_ids": [q.question_id for q in picked], "answers": {},
                "mastery_before": {t: round(self.learner.current(owner_id, t), 4) for t in chosen}, "finished": False}
        self.db.put_quiz(sid, owner_id, data)
        self.save_progress(owner_id)
        return {**data, "questions": [q.public() for q in picked]}

    def quiz_answer(self, owner_id: str, session_id: str, question_id: str, answer: str) -> dict[str, Any]:
        quiz = self.db.get_quiz(session_id)
        if not quiz or quiz["learner_id"] != owner_id:
            raise ServiceError("Quiz not found.", 404)
        if quiz.get("finished"):
            raise ServiceError("This quiz is already finished.", 409)
        if question_id not in quiz["question_ids"]:
            raise ServiceError("That question is not part of this quiz.")
        if question_id in quiz["answers"]:
            raise ServiceError("You already answered this question.", 409)
        result = self.submit(owner_id, question_id, answer, session_id=session_id)
        ev = result["evaluation"]
        quiz["answers"][question_id] = {"answer": answer[:500], "is_correct": ev["is_correct"], "score": ev["score"], "status": ev["status"]}
        quiz.pop("learner_id", None)
        self.db.put_quiz(session_id, owner_id, quiz)
        self.save_progress(owner_id)
        if quiz["mode"] == "exam":
            return {"recorded": True, "answered": len(quiz["answers"]), "total": len(quiz["question_ids"])}
        return {**result, "answered": len(quiz["answers"]), "total": len(quiz["question_ids"])}

    def finish_quiz(self, owner_id: str, session_id: str) -> dict[str, Any]:
        quiz = self.db.get_quiz(session_id)
        if not quiz or quiz["learner_id"] != owner_id:
            raise ServiceError("Quiz not found.", 404)
        quiz.pop("learner_id", None)
        quiz["finished"] = True
        report = self.quiz_report(owner_id, quiz)
        quiz["report"] = report
        self.db.put_quiz(session_id, owner_id, quiz, finished=True)
        self.save_progress(owner_id)
        return report

    def quiz_report(self, owner_id: str, quiz: dict[str, Any]) -> dict[str, Any]:
        names = self.topic_names(owner_id)
        titles = self.source_titles(owner_id)
        per_topic: dict[str, dict[str, Any]] = {}
        review: list[dict[str, Any]] = []
        confusions: list[dict[str, Any]] = []
        items = []
        for qid in quiz["question_ids"]:
            q = self.db.get_question(qid)
            if not q:
                continue
            a = quiz["answers"].get(qid)
            row = per_topic.setdefault(q.topic_id, {"topic_id": q.topic_id, "topic_name": names.get(q.topic_id, q.topic_id),
                                                    "answered": 0, "correct": 0, "score": 0.0})
            item = {"question_id": qid, "prompt": q.prompt, "topic_name": row["topic_name"], "your_answer": a["answer"] if a else None,
                    "is_correct": bool(a and a["is_correct"]), "status": a["status"] if a else "unanswered",
                    "expected_answer": self._answer_text(q), "solution": q.solution}
            if a and not a["is_correct"] and q.question_type == QuestionType.mcq:
                chosen_key = a["answer"].strip().upper()[:1]
                other = (q.metadata.get("distractor_concepts") or {}).get(chosen_key)
                if other and q.concept_id:
                    confusions.append({"concept": q.concept_id, "chosen": other, "topic_name": row["topic_name"],
                                       "note": f"You picked the description of '{other}' for '{q.concept_id}'." if q.metadata.get("generator") == "definition-mcq"
                                       else f"You chose '{other}' where the answer was '{q.concept_id}'."})
            if a:
                row["answered"] += 1
                row["correct"] += int(a["is_correct"])
                row["score"] += a["score"]
            if not a or not a["is_correct"]:
                for eid in q.evidence_ids[:1]:
                    u = self.db.get_evidence(eid)
                    if u:
                        c = citation_for(u, titles.get(u.source_id, ""))
                        item["citation"] = c.model_dump()
                        review.append({"topic_name": row["topic_name"], "citation": c.model_dump()})
            items.append(item)
        before = quiz.get("mastery_before", {})
        for tid, row in per_topic.items():
            row["accuracy"] = round(row["correct"] / row["answered"], 3) if row["answered"] else None
            row["mastery_before"] = before.get(tid)
            row["mastery_after"] = round(self.learner.current(owner_id, tid), 4)
            row["status"] = ("strong" if row["mastery_after"] >= MASTERED else "weak" if (row["mastery_after"] < 0.6 or (row["accuracy"] or 0) < 0.6) else "developing")
        answered = sum(r["answered"] for r in per_topic.values())
        score = sum(r["score"] for r in per_topic.values())
        weak = sorted([r for r in per_topic.values() if r["status"] == "weak"], key=lambda r: r["mastery_after"])
        misc = [m.model_dump() for m in self.db.active_misconceptions(owner_id) if m.topic_id in per_topic]
        rec = self.learner.recommend(owner_id, self.db.topics(owner_id))
        seen: set[str] = set()
        review_unique = []
        for r in review:
            if r["citation"]["evidence_id"] not in seen:
                seen.add(r["citation"]["evidence_id"])
                review_unique.append(r)
        return {
            "session_id": quiz["session_id"], "mode": quiz.get("mode", "practice"), "total": len(quiz["question_ids"]),
            "answered": answered, "score": round(score, 2), "percent": round(100 * score / max(1, len(quiz["question_ids"])), 1),
            "topics": sorted(per_topic.values(), key=lambda r: r["topic_name"]), "weak_topics": weak, "misconceptions": misc, "confusions": confusions,
            "review": review_unique[:8], "items": items, "next_recommendation": rec.model_dump(),
        }

    def quiz_history(self, owner_id: str) -> list[dict[str, Any]]:
        out = []
        for q in self.db.quizzes(owner_id)[:20]:
            rep = q.get("report") or {}
            out.append({"session_id": q["session_id"], "mode": q.get("mode"), "created_at": q.get("created_at"), "finished": q.get("finished", False),
                        "total": len(q.get("question_ids", [])), "answered": len(q.get("answers", {})), "percent": rep.get("percent")})
        return out

    # ========================================================== learner views
    def profile(self, owner_id: str) -> dict[str, Any]:
        names = self.topic_names(owner_id)
        records = []
        for m in self.db.all_mastery(owner_id):
            if m.topic_id not in names:
                continue
            d = m.model_dump()
            d["p_mastery_stored"] = m.p_mastery
            d["p_mastery"] = decayed(m)
            d["topic_name"] = names[m.topic_id]
            records.append(d)
        inter = self.db.interactions(owner_id)
        return {
            "learner_id": owner_id, "topic_mastery": {r["topic_id"]: r["p_mastery"] for r in records},
            "total_attempts": len(inter), "total_correct": sum(1 for i in inter if i["is_correct"]),
            "interaction_count": len(inter), "active_misconceptions": [m.suspected_misconception for m in self.db.active_misconceptions(owner_id)],
            "records": records, "history": [{"timestamp": i["timestamp"], "topic_id": i["topic_id"], "topic_name": names.get(i["topic_id"], i["topic_id"]),
                                             "is_correct": bool(i["is_correct"]), "p_after": i["p_after"]} for i in inter[-60:]],
            "meta": self.db.get_meta(owner_id),
        }

    def intake(self, owner_id: str, self_ratings: Optional[dict[str, float]] = None,
               responses: Optional[list[dict[str, Any]]] = None) -> dict[str, Any]:
        names = self.topic_names(owner_id)
        for tid, r in (self_ratings or {}).items():
            if tid in names:
                self.learner.set_prior(owner_id, tid, float(r))
        for resp in responses or []:
            if resp.get("question_id"):
                self.submit(owner_id, resp["question_id"], str(resp.get("answer", "")))
            elif resp.get("topic_id") in names:
                self.learner.observe_binary(owner_id, resp["topic_id"], bool(resp.get("is_correct")))
        meta = self.db.get_meta(owner_id)
        meta["intake_completed_at"] = now_iso()
        self.db.put_meta(owner_id, meta)
        self.save_progress(owner_id)
        return {"learner_id": owner_id, "intake_status": "completed", "profile": self.profile(owner_id),
                "initial_recommendation": self.learner.recommend(owner_id, self.db.topics(owner_id)).model_dump()}

    def diagnostic(self, owner_id: str, per_topic: int = 1, max_questions: int = 10) -> dict[str, Any]:
        """Cold start: one easy question per topic, foundational topics first."""
        from .study import topo_order

        picked = []
        for t in topo_order(self.db.topics(owner_id)):
            bank = self.db.questions(owner_id, t.topic_id)
            q = self.learner.select_question(owner_id, bank, Difficulty.easy)
            if q:
                picked.append(q)
            if len(picked) >= max_questions:
                break
        return self.create_quiz_from(owner_id, picked, mode="diagnostic")

    def create_quiz_from(self, owner_id: str, questions: list[Question], mode: str) -> dict[str, Any]:
        if not questions:
            raise ServiceError("No questions available yet.", 404)
        sid = f"quiz-{uuid.uuid4().hex[:12]}"
        tids = list(dict.fromkeys(q.topic_id for q in questions))
        data = {"session_id": sid, "mode": mode, "created_at": now_iso(), "topic_ids": tids, "question_ids": [q.question_id for q in questions],
                "answers": {}, "mastery_before": {t: round(self.learner.current(owner_id, t), 4) for t in tids}, "finished": False}
        self.db.put_quiz(sid, owner_id, data)
        return {**data, "questions": [q.public() for q in questions]}

    def recommendation(self, owner_id: str, active_topic: Optional[str] = None) -> dict[str, Any]:
        rec = self.learner.recommend(owner_id, self.db.topics(owner_id), active_topic)
        if rec.topic_id:
            q = self.next_question(owner_id, rec.topic_id, rec.difficulty) if self.db.get_topic(rec.topic_id) else None
            rec.suggested_question_id = q.question_id if q else None
        return rec.model_dump()

    def misconceptions(self, owner_id: str, topic_id: Optional[str] = None) -> list[dict[str, Any]]:
        titles = self.source_titles(owner_id)
        names = self.topic_names(owner_id)
        out = []
        for m in self.db.active_misconceptions(owner_id, topic_id):
            items = []
            for eid in m.remediation_evidence_ids:
                u = self.db.get_evidence(eid)
                if u:
                    items.append({"evidence_id": eid, "text": u.text, "location": u.location, "modality": u.modality.value,
                                  "source_title": titles.get(u.source_id, ""), "locator_label": locator_label(u.location)})
            out.append({**m.model_dump(), "topic_name": names.get(m.topic_id, m.topic_id), "evidence_items": items})
        return out

    def resolve_misconception(self, owner_id: str, signal_id: str) -> dict[str, Any]:
        m = self.db.get_misconception(signal_id)
        if not m or m.learner_id != owner_id:
            raise ServiceError("Misconception not found.", 404)
        self.learner.resolve(owner_id, m.topic_id, m.concept_id)
        self.save_progress(owner_id)
        return {"status": "resolved", "learner_id": owner_id, "topic_id": m.topic_id}

    # ============================================================ study tools
    def _formulas_by_topic(self, owner_id: str) -> dict[str, list[tuple[str, str]]]:
        out: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for t in self.db.topics(owner_id):
            for u in self.db.evidence_for_topic(t.topic_id):
                for f in find_formulas(u):
                    if f.text not in [x[0] for x in out[t.topic_id]]:
                        out[t.topic_id].append((f.text, u.evidence_id))
        return out

    def flashcards(self, owner_id: str, topic_id: Optional[str] = None, limit: int = 20) -> list[dict[str, Any]]:
        topics = [t for t in self.db.topics(owner_id) if not topic_id or t.topic_id == topic_id]
        cards = build_cards(topics, {t.topic_id: self.definitions(t.topic_id) for t in topics}, self._formulas_by_topic(owner_id))
        titles = self.source_titles(owner_id)
        out = due_cards(self.db, self.learner, owner_id, cards, limit)
        for c in out:
            u = self.db.get_evidence(c["evidence_id"])
            if u:
                c["citation"] = citation_for(u, titles.get(u.source_id, "")).model_dump()
        return out

    def review_flashcard(self, owner_id: str, card_id: str, grade_value: int) -> dict[str, Any]:
        res = review_card(self.db, owner_id, card_id, grade_value)
        self.save_progress(owner_id)
        return res

    def plan(self, owner_id: str, exam_date: Optional[str], minutes_per_day: int) -> dict[str, Any]:
        meta = self.db.get_meta(owner_id)
        if exam_date:
            meta["exam_date"] = exam_date
            meta["minutes_per_day"] = minutes_per_day
            self.db.put_meta(owner_id, meta)
            self.save_progress(owner_id)
        topics = self.db.topics(owner_id)
        own = [t for t in topics if t.owner_id == owner_id]
        # Plan for the learner's own course when they have one; the demo course otherwise.
        return study_plan(self.learner, owner_id, own or topics, exam_date or meta.get("exam_date"),
                          minutes_per_day or meta.get("minutes_per_day", 60))

    def map(self, owner_id: str) -> dict[str, Any]:
        return course_map(self.learner, owner_id, self.db.topics(owner_id))

    def topics(self, owner_id: str) -> list[dict[str, Any]]:
        out = []
        for t in self.db.topics(owner_id):
            out.append({"topic_id": t.topic_id, "name": t.name, "description": t.description, "concepts": t.concepts,
                        "prerequisites": t.prerequisites, "source_id": t.source_id, "owner": "you" if t.owner_id == owner_id else "demo",
                        "question_count": len(self.db.questions(owner_id, t.topic_id))})
        return out

    def health(self) -> dict[str, Any]:
        return {
            "status": "healthy", "version": "2.0.0",
            "sqlite_db": {"path": "configured", "sources_count": len(self.db.sources(PUBLIC_OWNER)), "evidence_count": self.db.count_evidence(),
                          "questions_count": len(self.db.questions(PUBLIC_OWNER))},
            "chroma_db": {"persist_directory": "not used (vectors in SQLite)", "indexed_units": self.db.count_evidence()},
            "ollama": {"host": "", "available": self.llm.name.startswith("ollama"), "configured_model": self.settings.ollama_model, "installed_models": []},
            "model_provider": {"active_provider": self.llm.name, "available": self.llm.available},
            "embedding_model": self.embedder.name, "persistence": self.backend.name,
        }
