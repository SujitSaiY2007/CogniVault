"""SQLite storage. Every row that belongs to a user carries its owner id.

The shared demo course uses owner id ``public``. A user's queries can see
``public`` plus their own rows, never another user's.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

import numpy as np

from .models import (
    PUBLIC_OWNER,
    EvidenceUnit,
    MisconceptionSignal,
    Modality,
    Question,
    SourceRecord,
    TopicMasteryRecord,
    TopicRecord,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources(
    source_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, title TEXT NOT NULL, modality TEXT NOT NULL,
    path TEXT NOT NULL DEFAULT '', sha256 TEXT NOT NULL DEFAULT '', metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS sources_owner ON sources(owner_id);
CREATE TABLE IF NOT EXISTS evidence(
    evidence_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE,
    owner_id TEXT NOT NULL, modality TEXT NOT NULL, text TEXT NOT NULL, location_json TEXT NOT NULL,
    evidence_type TEXT NOT NULL, section TEXT NOT NULL DEFAULT '', topics_json TEXT NOT NULL DEFAULT '[]',
    concepts_json TEXT NOT NULL DEFAULT '[]', metadata_json TEXT NOT NULL DEFAULT '{}', position INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS evidence_owner ON evidence(owner_id);
CREATE INDEX IF NOT EXISTS evidence_source ON evidence(source_id);
CREATE VIRTUAL TABLE IF NOT EXISTS evidence_fts USING fts5(
    evidence_id UNINDEXED, owner_id UNINDEXED, text, section, tokenize='porter unicode61');
CREATE TABLE IF NOT EXISTS embeddings(
    evidence_id TEXT PRIMARY KEY REFERENCES evidence(evidence_id) ON DELETE CASCADE,
    owner_id TEXT NOT NULL, model TEXT NOT NULL, dim INTEGER NOT NULL, vector BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS assets(
    asset_id TEXT PRIMARY KEY, evidence_id TEXT NOT NULL REFERENCES evidence(evidence_id) ON DELETE CASCADE,
    mime_type TEXT NOT NULL, data BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS topics(
    topic_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, name TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
    source_id TEXT, position INTEGER NOT NULL DEFAULT 0, concepts_json TEXT NOT NULL DEFAULT '[]',
    prerequisites_json TEXT NOT NULL DEFAULT '[]');
CREATE INDEX IF NOT EXISTS topics_owner ON topics(owner_id);
CREATE TABLE IF NOT EXISTS questions(
    question_id TEXT PRIMARY KEY, owner_id TEXT NOT NULL, topic_id TEXT NOT NULL, fingerprint TEXT NOT NULL,
    verification_status TEXT NOT NULL, data_json TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS questions_owner_topic ON questions(owner_id, topic_id);
CREATE TABLE IF NOT EXISTS learner_states(
    learner_id TEXT NOT NULL, topic_id TEXT NOT NULL, p_mastery REAL NOT NULL, attempts INTEGER NOT NULL,
    correct INTEGER NOT NULL, recent_json TEXT NOT NULL, last_seen TEXT, misconceptions_json TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY(learner_id, topic_id));
CREATE TABLE IF NOT EXISTS interactions(
    interaction_id TEXT PRIMARY KEY, learner_id TEXT NOT NULL, question_id TEXT NOT NULL, topic_id TEXT NOT NULL,
    answer TEXT NOT NULL, is_correct INTEGER NOT NULL, score REAL NOT NULL, timestamp TEXT NOT NULL,
    session_id TEXT, p_before REAL, p_after REAL);
CREATE INDEX IF NOT EXISTS interactions_learner ON interactions(learner_id, timestamp);
CREATE TABLE IF NOT EXISTS misconceptions(
    signal_id TEXT PRIMARY KEY, learner_id TEXT NOT NULL, topic_id TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1,
    data_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS error_signals(
    learner_id TEXT NOT NULL, topic_id TEXT NOT NULL, concept_id TEXT NOT NULL, pattern TEXT NOT NULL,
    count INTEGER NOT NULL, last_seen TEXT, PRIMARY KEY(learner_id, topic_id, concept_id, pattern));
CREATE TABLE IF NOT EXISTS quiz_sessions(
    session_id TEXT PRIMARY KEY, learner_id TEXT NOT NULL, created_at TEXT NOT NULL, finished_at TEXT,
    data_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS card_reviews(
    learner_id TEXT NOT NULL, card_id TEXT NOT NULL, ease REAL NOT NULL, interval_days REAL NOT NULL,
    reps INTEGER NOT NULL, due TEXT NOT NULL, PRIMARY KEY(learner_id, card_id));
CREATE TABLE IF NOT EXISTS learner_meta(
    learner_id TEXT PRIMARY KEY, data_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS auth_users(
    username TEXT PRIMARY KEY, password_hash TEXT NOT NULL, learner_id TEXT NOT NULL UNIQUE, created_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS auth_sessions(
    token_hash TEXT PRIMARY KEY, username TEXT NOT NULL, expires_at INTEGER NOT NULL, created_at INTEGER NOT NULL);
"""

# Tables whose rows belong to one user and are saved in that user's snapshot.
# (table, owner column)
OWNER_TABLES: tuple[tuple[str, str], ...] = (
    ("topics", "owner_id"),
    ("questions", "owner_id"),
    ("learner_states", "learner_id"),
    ("interactions", "learner_id"),
    ("misconceptions", "learner_id"),
    ("error_signals", "learner_id"),
    ("quiz_sessions", "learner_id"),
    ("card_reviews", "learner_id"),
    ("learner_meta", "learner_id"),
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _j(v: Any) -> str:
    return json.dumps(v, ensure_ascii=False, default=str)


class Database:
    def __init__(self, path: str | Path = ":memory:"):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path, check_same_thread=False, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        with self.lock:
            self.conn.execute("PRAGMA foreign_keys=ON")
            if self.path != ":memory:":
                self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.executescript(SCHEMA)
            self.conn.commit()

    def close(self) -> None:
        with self.lock:
            self.conn.close()

    # ------------------------------------------------------------------ helpers
    def _q(self, sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        with self.lock:
            return self.conn.execute(sql, tuple(params)).fetchall()

    def _x(self, sql: str, params: Iterable[Any] = ()) -> None:
        with self.lock:
            self.conn.execute(sql, tuple(params))
            self.conn.commit()

    # When False, signed-in users see only their own uploads (the shared demo course is hidden).
    show_public = True

    def _scope(self, owner_id: str) -> tuple[str, list[str]]:
        owners = [PUBLIC_OWNER] if owner_id == PUBLIC_OWNER else [PUBLIC_OWNER, owner_id] if self.show_public else [owner_id]
        return "(" + ",".join("?" for _ in owners) + ")", owners

    # ------------------------------------------------------------------ sources
    def add_source(self, s: SourceRecord) -> None:
        self._x(
            "INSERT OR REPLACE INTO sources VALUES(?,?,?,?,?,?,?,?)",
            (s.source_id, s.owner_id, s.title, s.modality.value, s.path, s.sha256, _j(s.metadata), s.created_at or now_iso()),
        )

    def _source(self, r: sqlite3.Row) -> SourceRecord:
        count = self._q("SELECT COUNT(*) c FROM evidence WHERE source_id=?", (r["source_id"],))[0]["c"]
        return SourceRecord(
            source_id=r["source_id"], owner_id=r["owner_id"], title=r["title"], modality=Modality(r["modality"]),
            path=r["path"], sha256=r["sha256"], metadata=json.loads(r["metadata_json"]), evidence_count=count,
            created_at=r["created_at"],
        )

    def get_source(self, source_id: str) -> Optional[SourceRecord]:
        rows = self._q("SELECT * FROM sources WHERE source_id=?", (source_id,))
        return self._source(rows[0]) if rows else None

    def sources(self, owner_id: str, include_public: bool = True) -> list[SourceRecord]:
        if include_public:
            scope, params = self._scope(owner_id)
            rows = self._q(f"SELECT * FROM sources WHERE owner_id IN {scope} ORDER BY owner_id='public', created_at", params)
        else:
            rows = self._q("SELECT * FROM sources WHERE owner_id=? ORDER BY created_at", (owner_id,))
        return [self._source(r) for r in rows]

    def delete_source(self, source_id: str) -> None:
        with self.lock:
            ids = [r["evidence_id"] for r in self.conn.execute("SELECT evidence_id FROM evidence WHERE source_id=?", (source_id,))]
            self.conn.executemany("DELETE FROM evidence_fts WHERE evidence_id=?", [(i,) for i in ids])
            self.conn.execute("DELETE FROM sources WHERE source_id=?", (source_id,))
            self.conn.execute("DELETE FROM topics WHERE source_id=?", (source_id,))
            self.conn.commit()

    # ----------------------------------------------------------------- evidence
    def add_evidence(self, units: list[EvidenceUnit]) -> None:
        with self.lock:
            for pos, e in enumerate(units):
                self.conn.execute(
                    "INSERT OR REPLACE INTO evidence VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (e.evidence_id, e.source_id, e.owner_id, e.modality.value, e.text, _j(e.location), e.evidence_type,
                     e.section, _j(e.topics), _j(e.concepts), _j(e.metadata), pos),
                )
                self.conn.execute("DELETE FROM evidence_fts WHERE evidence_id=?", (e.evidence_id,))
                self.conn.execute(
                    "INSERT INTO evidence_fts(evidence_id, owner_id, text, section) VALUES(?,?,?,?)",
                    (e.evidence_id, e.owner_id, e.text + " " + " ".join(e.metadata.get("keywords", [])), e.section),
                )
            self.conn.commit()

    def update_evidence_tags(self, evidence_id: str, topics: list[str], concepts: list[str]) -> None:
        self._x("UPDATE evidence SET topics_json=?, concepts_json=? WHERE evidence_id=?", (_j(topics), _j(concepts), evidence_id))

    def _evidence(self, r: sqlite3.Row) -> EvidenceUnit:
        return EvidenceUnit(
            evidence_id=r["evidence_id"], source_id=r["source_id"], owner_id=r["owner_id"], modality=Modality(r["modality"]),
            text=r["text"], location=json.loads(r["location_json"]), evidence_type=r["evidence_type"], section=r["section"],
            topics=json.loads(r["topics_json"]), concepts=json.loads(r["concepts_json"]), metadata=json.loads(r["metadata_json"]),
        )

    def get_evidence(self, evidence_id: str) -> Optional[EvidenceUnit]:
        rows = self._q("SELECT * FROM evidence WHERE evidence_id=?", (evidence_id,))
        return self._evidence(rows[0]) if rows else None

    def evidence_for_owner(self, owner_id: str) -> list[EvidenceUnit]:
        scope, params = self._scope(owner_id)
        rows = self._q(f"SELECT * FROM evidence WHERE owner_id IN {scope} ORDER BY source_id, position", params)
        return [self._evidence(r) for r in rows]

    def evidence_for_source(self, source_id: str) -> list[EvidenceUnit]:
        rows = self._q("SELECT * FROM evidence WHERE source_id=? ORDER BY position", (source_id,))
        return [self._evidence(r) for r in rows]

    def evidence_for_topic(self, topic_id: str) -> list[EvidenceUnit]:
        rows = self._q("SELECT * FROM evidence WHERE topics_json LIKE ? ORDER BY source_id, position", (f'%"{topic_id}"%',))
        return [e for e in (self._evidence(r) for r in rows) if topic_id in e.topics]

    def count_evidence(self, owner_id: Optional[str] = None) -> int:
        if owner_id is None:
            return self._q("SELECT COUNT(*) c FROM evidence")[0]["c"]
        return self._q("SELECT COUNT(*) c FROM evidence WHERE owner_id=?", (owner_id,))[0]["c"]

    def fts_search(self, match: str, owner_id: str, limit: int = 50) -> list[tuple[str, float]]:
        scope, params = self._scope(owner_id)
        try:
            rows = self._q(
                f"SELECT evidence_id, bm25(evidence_fts, 1.0, 0.6) AS r FROM evidence_fts "
                f"WHERE evidence_fts MATCH ? AND owner_id IN {scope} ORDER BY r LIMIT ?",
                [match, *params, limit],
            )
        except sqlite3.OperationalError:
            return []
        return [(r["evidence_id"], -float(r["r"])) for r in rows]

    # --------------------------------------------------------------- embeddings
    def put_embeddings(self, items: list[tuple[str, str, str, np.ndarray]]) -> None:
        with self.lock:
            self.conn.executemany(
                "INSERT OR REPLACE INTO embeddings VALUES(?,?,?,?,?)",
                [(eid, owner, model, int(v.shape[0]), v.astype(np.float32).tobytes()) for eid, owner, model, v in items],
            )
            self.conn.commit()

    def embeddings_for_owner(self, owner_id: str, model: str) -> tuple[list[str], np.ndarray]:
        scope, params = self._scope(owner_id)
        rows = self._q(f"SELECT evidence_id, dim, vector FROM embeddings WHERE owner_id IN {scope} AND model=?", [*params, model])
        if not rows:
            return [], np.zeros((0, 1), dtype=np.float32)
        ids = [r["evidence_id"] for r in rows]
        mat = np.vstack([np.frombuffer(r["vector"], dtype=np.float32) for r in rows])
        return ids, mat

    def missing_embeddings(self, model: str) -> list[EvidenceUnit]:
        rows = self._q(
            "SELECT e.* FROM evidence e LEFT JOIN embeddings m ON m.evidence_id=e.evidence_id AND m.model=? "
            "WHERE m.evidence_id IS NULL", (model,))
        return [self._evidence(r) for r in rows]

    # ------------------------------------------------------------------- assets
    def add_asset(self, asset_id: str, evidence_id: str, mime: str, data: bytes) -> None:
        self._x("INSERT OR REPLACE INTO assets VALUES(?,?,?,?)", (asset_id, evidence_id, mime, data))

    def get_asset(self, asset_id: str) -> Optional[tuple[str, bytes]]:
        rows = self._q("SELECT mime_type, data FROM assets WHERE asset_id=?", (asset_id,))
        return (rows[0]["mime_type"], rows[0]["data"]) if rows else None

    # ------------------------------------------------------------------- topics
    def put_topics(self, topics: list[TopicRecord]) -> None:
        with self.lock:
            for t in topics:
                self.conn.execute(
                    "INSERT OR REPLACE INTO topics VALUES(?,?,?,?,?,?,?,?)",
                    (t.topic_id, t.owner_id, t.name, t.description, t.source_id, t.position, _j(t.concepts), _j(t.prerequisites)),
                )
            self.conn.commit()

    def _topic(self, r: sqlite3.Row) -> TopicRecord:
        return TopicRecord(
            topic_id=r["topic_id"], owner_id=r["owner_id"], name=r["name"], description=r["description"],
            source_id=r["source_id"], position=r["position"], concepts=json.loads(r["concepts_json"]),
            prerequisites=json.loads(r["prerequisites_json"]),
        )

    def topics(self, owner_id: str) -> list[TopicRecord]:
        scope, params = self._scope(owner_id)
        rows = self._q(f"SELECT * FROM topics WHERE owner_id IN {scope} ORDER BY owner_id='public', source_id, position", params)
        return [self._topic(r) for r in rows]

    def get_topic(self, topic_id: str) -> Optional[TopicRecord]:
        rows = self._q("SELECT * FROM topics WHERE topic_id=?", (topic_id,))
        return self._topic(rows[0]) if rows else None

    # ---------------------------------------------------------------- questions
    def put_question(self, q: Question) -> None:
        self._x(
            "INSERT OR REPLACE INTO questions VALUES(?,?,?,?,?,?)",
            (q.question_id, q.owner_id, q.topic_id, q.fingerprint, q.verification_status, q.model_dump_json()),
        )

    def get_question(self, question_id: str) -> Optional[Question]:
        rows = self._q("SELECT data_json FROM questions WHERE question_id=?", (question_id,))
        return Question.model_validate_json(rows[0]["data_json"]) if rows else None

    def questions(self, owner_id: str, topic_id: Optional[str] = None, verified_only: bool = True) -> list[Question]:
        scope, params = self._scope(owner_id)
        sql = f"SELECT data_json FROM questions WHERE owner_id IN {scope}"
        if topic_id:
            sql += " AND topic_id=?"
            params = [*params, topic_id]
        if verified_only:
            sql += " AND verification_status='verified'"
        return [Question.model_validate_json(r["data_json"]) for r in self._q(sql + " ORDER BY question_id", params)]

    def delete_questions_for_topics(self, topic_ids: list[str]) -> None:
        with self.lock:
            self.conn.executemany("DELETE FROM questions WHERE topic_id=?", [(t,) for t in topic_ids])
            self.conn.commit()

    # ------------------------------------------------------------ learner state
    def get_mastery(self, learner_id: str, topic_id: str) -> Optional[TopicMasteryRecord]:
        rows = self._q("SELECT * FROM learner_states WHERE learner_id=? AND topic_id=?", (learner_id, topic_id))
        return self._mastery(rows[0]) if rows else None

    def _mastery(self, r: sqlite3.Row) -> TopicMasteryRecord:
        return TopicMasteryRecord(
            learner_id=r["learner_id"], topic_id=r["topic_id"], p_mastery=r["p_mastery"], attempts=r["attempts"],
            correct=r["correct"], recent_correctness=json.loads(r["recent_json"]), last_seen=r["last_seen"],
            misconception_signals=json.loads(r["misconceptions_json"]),
        )

    def all_mastery(self, learner_id: str) -> list[TopicMasteryRecord]:
        return [self._mastery(r) for r in self._q("SELECT * FROM learner_states WHERE learner_id=? ORDER BY topic_id", (learner_id,))]

    def put_mastery(self, m: TopicMasteryRecord) -> None:
        self._x(
            "INSERT OR REPLACE INTO learner_states VALUES(?,?,?,?,?,?,?,?)",
            (m.learner_id, m.topic_id, m.p_mastery, m.attempts, m.correct, _j(m.recent_correctness), m.last_seen,
             _j(m.misconception_signals)),
        )

    def add_interaction(self, row: dict[str, Any]) -> None:
        self._x(
            "INSERT OR REPLACE INTO interactions VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (row["interaction_id"], row["learner_id"], row["question_id"], row["topic_id"], row["answer"],
             int(row["is_correct"]), row["score"], row["timestamp"], row.get("session_id"), row.get("p_before"), row.get("p_after")),
        )

    def interactions(self, learner_id: str) -> list[dict[str, Any]]:
        return [dict(r) for r in self._q("SELECT * FROM interactions WHERE learner_id=? ORDER BY timestamp", (learner_id,))]

    def served_question_ids(self, learner_id: str) -> set[str]:
        return {r["question_id"] for r in self._q("SELECT DISTINCT question_id FROM interactions WHERE learner_id=?", (learner_id,))}

    # ----------------------------------------------------------- misconceptions
    def bump_error(self, learner_id: str, topic_id: str, concept_id: str, pattern: str) -> int:
        with self.lock:
            self.conn.execute(
                "INSERT INTO error_signals VALUES(?,?,?,?,1,?) ON CONFLICT(learner_id, topic_id, concept_id, pattern) "
                "DO UPDATE SET count=count+1, last_seen=excluded.last_seen",
                (learner_id, topic_id, concept_id, pattern, now_iso()),
            )
            self.conn.commit()
            return self.conn.execute(
                "SELECT SUM(count) c FROM error_signals WHERE learner_id=? AND topic_id=? AND concept_id=?",
                (learner_id, topic_id, concept_id),
            ).fetchone()["c"]

    def error_patterns(self, learner_id: str, topic_id: str, concept_id: str) -> dict[str, int]:
        rows = self._q("SELECT pattern, count FROM error_signals WHERE learner_id=? AND topic_id=? AND concept_id=?",
                       (learner_id, topic_id, concept_id))
        return {r["pattern"]: r["count"] for r in rows}

    def clear_errors(self, learner_id: str, topic_id: str, concept_id: Optional[str] = None) -> None:
        if concept_id:
            self._x("DELETE FROM error_signals WHERE learner_id=? AND topic_id=? AND concept_id=?", (learner_id, topic_id, concept_id))
        else:
            self._x("DELETE FROM error_signals WHERE learner_id=? AND topic_id=?", (learner_id, topic_id))

    def put_misconception(self, m: MisconceptionSignal, active: bool = True) -> None:
        self._x("INSERT OR REPLACE INTO misconceptions VALUES(?,?,?,?,?)",
                (m.signal_id, m.learner_id, m.topic_id, int(active), m.model_dump_json()))

    def get_misconception(self, signal_id: str) -> Optional[MisconceptionSignal]:
        rows = self._q("SELECT data_json FROM misconceptions WHERE signal_id=?", (signal_id,))
        return MisconceptionSignal.model_validate_json(rows[0]["data_json"]) if rows else None

    def active_misconceptions(self, learner_id: str, topic_id: Optional[str] = None) -> list[MisconceptionSignal]:
        sql, params = "SELECT data_json FROM misconceptions WHERE learner_id=? AND active=1", [learner_id]
        if topic_id:
            sql += " AND topic_id=?"
            params.append(topic_id)
        items = [MisconceptionSignal.model_validate_json(r["data_json"]) for r in self._q(sql, params)]
        return sorted(items, key=lambda m: (-m.confidence, m.signal_id))

    def deactivate_misconceptions(self, learner_id: str, topic_id: str, concept_id: Optional[str] = None) -> None:
        for m in self.active_misconceptions(learner_id, topic_id):
            if concept_id is None or m.concept_id == concept_id:
                self._x("UPDATE misconceptions SET active=0 WHERE signal_id=?", (m.signal_id,))

    # ---------------------------------------------------------- quiz / cards / meta
    def put_quiz(self, session_id: str, learner_id: str, data: dict[str, Any], finished: bool = False) -> None:
        created = data.get("created_at") or now_iso()
        self._x("INSERT OR REPLACE INTO quiz_sessions VALUES(?,?,?,?,?)",
                (session_id, learner_id, created, now_iso() if finished else None, _j(data)))

    def get_quiz(self, session_id: str) -> Optional[dict[str, Any]]:
        rows = self._q("SELECT learner_id, data_json FROM quiz_sessions WHERE session_id=?", (session_id,))
        if not rows:
            return None
        d = json.loads(rows[0]["data_json"])
        d["learner_id"] = rows[0]["learner_id"]
        return d

    def quizzes(self, learner_id: str) -> list[dict[str, Any]]:
        rows = self._q("SELECT data_json FROM quiz_sessions WHERE learner_id=? ORDER BY created_at DESC", (learner_id,))
        return [json.loads(r["data_json"]) for r in rows]

    def get_card(self, learner_id: str, card_id: str) -> Optional[dict[str, Any]]:
        rows = self._q("SELECT * FROM card_reviews WHERE learner_id=? AND card_id=?", (learner_id, card_id))
        return dict(rows[0]) if rows else None

    def put_card(self, learner_id: str, card_id: str, ease: float, interval: float, reps: int, due: str) -> None:
        self._x("INSERT OR REPLACE INTO card_reviews VALUES(?,?,?,?,?,?)", (learner_id, card_id, ease, interval, reps, due))

    def cards(self, learner_id: str) -> dict[str, dict[str, Any]]:
        return {r["card_id"]: dict(r) for r in self._q("SELECT * FROM card_reviews WHERE learner_id=?", (learner_id,))}

    def get_meta(self, learner_id: str) -> dict[str, Any]:
        rows = self._q("SELECT data_json FROM learner_meta WHERE learner_id=?", (learner_id,))
        return json.loads(rows[0]["data_json"]) if rows else {}

    def put_meta(self, learner_id: str, data: dict[str, Any]) -> None:
        self._x("INSERT OR REPLACE INTO learner_meta VALUES(?,?)", (learner_id, _j(data)))

    # ---------------------------------------------------------------- snapshots
    def export_owner(self, owner_id: str) -> dict[str, list[dict[str, Any]]]:
        out: dict[str, list[dict[str, Any]]] = {}
        for table, col in OWNER_TABLES:
            out[table] = [dict(r) for r in self._q(f"SELECT * FROM {table} WHERE {col}=?", (owner_id,))]
        return out

    def import_owner(self, owner_id: str, snapshot: dict[str, list[dict[str, Any]]]) -> None:
        with self.lock:
            for table, col in OWNER_TABLES:
                cols = [r[1] for r in self.conn.execute(f"PRAGMA table_info({table})")]
                self.conn.execute(f"DELETE FROM {table} WHERE {col}=?", (owner_id,))
                for row in snapshot.get(table, []) or []:
                    if row.get(col) != owner_id:
                        continue  # never import rows that belong to someone else
                    keep = [c for c in cols if c in row]
                    self.conn.execute(
                        f"INSERT OR REPLACE INTO {table} ({','.join(keep)}) VALUES ({','.join('?' for _ in keep)})",
                        [row[c] for c in keep],
                    )
            self.conn.commit()

    def owner_has_rows(self, owner_id: str) -> bool:
        return bool(self._q("SELECT 1 FROM sources WHERE owner_id=? LIMIT 1", (owner_id,)))
