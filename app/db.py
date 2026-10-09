from __future__ import annotations
import json
import re
import sqlite3
from collections import deque
from pathlib import Path
from .models import (
    ConceptRecord,
    Difficulty,
    EvidenceUnit,
    MisconceptionSignal,
    Modality,
    PrerequisiteLink,
    Question,
    QuestionOption,
    QuestionType,
    SourceRecord,
    TopicMasteryRecord,
    TopicRecord,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources(
    source_id TEXT PRIMARY KEY,
    path TEXT NOT NULL,
    modality TEXT NOT NULL,
    title TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    metadata_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evidence(
    evidence_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    modality TEXT NOT NULL,
    text TEXT NOT NULL,
    location_json TEXT NOT NULL,
    evidence_type TEXT NOT NULL,
    asset_id TEXT,
    topics_json TEXT NOT NULL,
    concepts_json TEXT NOT NULL,
    prerequisites_json TEXT NOT NULL,
    metadata_json TEXT NOT NULL,
    FOREIGN KEY(source_id) REFERENCES sources(source_id)
);
CREATE VIRTUAL TABLE IF NOT EXISTS evidence_fts USING fts5(
    evidence_id UNINDEXED,
    text,
    topics,
    concepts
);
CREATE TABLE IF NOT EXISTS embeddings(
    evidence_id TEXT PRIMARY KEY,
    vector BLOB NOT NULL,
    model_name TEXT,
    dimension INTEGER
);
CREATE TABLE IF NOT EXISTS assets(
    asset_id TEXT PRIMARY KEY,
    evidence_id TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    width INTEGER,
    height INTEGER,
    data BLOB NOT NULL,
    FOREIGN KEY(evidence_id) REFERENCES evidence(evidence_id)
);
CREATE TABLE IF NOT EXISTS topics(
    topic_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT
);
CREATE TABLE IF NOT EXISTS concepts(
    concept_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    topic_id TEXT,
    description TEXT,
    FOREIGN KEY(topic_id) REFERENCES topics(topic_id)
);
CREATE TABLE IF NOT EXISTS evidence_concepts(
    evidence_id TEXT NOT NULL,
    concept_id TEXT NOT NULL,
    PRIMARY KEY(evidence_id, concept_id),
    FOREIGN KEY(evidence_id) REFERENCES evidence(evidence_id) ON DELETE CASCADE,
    FOREIGN KEY(concept_id) REFERENCES concepts(concept_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS evidence_topics(
    evidence_id TEXT NOT NULL,
    topic_id TEXT NOT NULL,
    PRIMARY KEY(evidence_id, topic_id),
    FOREIGN KEY(evidence_id) REFERENCES evidence(evidence_id) ON DELETE CASCADE,
    FOREIGN KEY(topic_id) REFERENCES topics(topic_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS concept_prerequisites(
    concept_id TEXT NOT NULL,
    prerequisite_concept_id TEXT NOT NULL,
    PRIMARY KEY(concept_id, prerequisite_concept_id),
    FOREIGN KEY(concept_id) REFERENCES concepts(concept_id) ON DELETE CASCADE,
    FOREIGN KEY(prerequisite_concept_id) REFERENCES concepts(concept_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS learner_states(
    learner_id TEXT NOT NULL,
    topic_id TEXT NOT NULL,
    p_mastery REAL NOT NULL,
    attempts INTEGER NOT NULL,
    correct INTEGER NOT NULL,
    recent_correctness_json TEXT NOT NULL,
    last_seen TEXT,
    PRIMARY KEY(learner_id, topic_id)
);
CREATE TABLE IF NOT EXISTS questions(
    question_id TEXT PRIMARY KEY,
    topic_id TEXT NOT NULL,
    concept_id TEXT,
    evidence_ids_json TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    question_type TEXT NOT NULL,
    prompt TEXT NOT NULL,
    options_json TEXT NOT NULL,
    expected_answer TEXT NOT NULL,
    tolerance REAL,
    solution TEXT NOT NULL,
    verification_status TEXT NOT NULL,
    verification_reason TEXT,
    fingerprint TEXT NOT NULL,
    repetition_count INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS learner_interactions(
    interaction_id TEXT PRIMARY KEY,
    learner_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    topic_id TEXT NOT NULL,
    user_answer TEXT NOT NULL,
    is_correct INTEGER NOT NULL,
    score REAL NOT NULL,
    feedback TEXT NOT NULL,
    timestamp TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS misconceptions(
    signal_id TEXT PRIMARY KEY,
    learner_id TEXT NOT NULL,
    topic_id TEXT NOT NULL,
    concept_id TEXT,
    suspected_misconception TEXT NOT NULL,
    error_count INTEGER NOT NULL,
    confidence REAL NOT NULL,
    remediation_concept_id TEXT,
    remediation_evidence_ids_json TEXT NOT NULL,
    remediation_note TEXT NOT NULL,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS error_signals(
    signal_key TEXT PRIMARY KEY,
    learner_id TEXT NOT NULL,
    topic_id TEXT NOT NULL,
    concept_id TEXT NOT NULL,
    error_pattern TEXT NOT NULL,
    occurrence_count INTEGER NOT NULL,
    last_occurred TEXT
);
"""

class EvidenceDB:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript(SCHEMA)

        # Migrations for backwards compatibility
        ev_cols = {r[1] for r in self.conn.execute("PRAGMA table_info(evidence)")}
        if "asset_id" not in ev_cols:
            self.conn.execute("ALTER TABLE evidence ADD COLUMN asset_id TEXT")

        emb_cols = {r[1] for r in self.conn.execute("PRAGMA table_info(embeddings)")}
        if "model_name" not in emb_cols:
            self.conn.execute("ALTER TABLE embeddings ADD COLUMN model_name TEXT")
        if "dimension" not in emb_cols:
            self.conn.execute("ALTER TABLE embeddings ADD COLUMN dimension INTEGER")
        self.conn.commit()

    # --- Sources ---
    def add_source(self, s: SourceRecord):
        self.conn.execute(
            "INSERT OR REPLACE INTO sources VALUES (?,?,?,?,?,?)",
            (s.source_id, s.path, s.modality.value, s.title, s.sha256, json.dumps(s.metadata))
        )
        self.conn.commit()

    def get_source(self, source_id: str) -> SourceRecord | None:
        row = self.conn.execute(
            "SELECT source_id, path, modality, title, sha256, metadata_json FROM sources WHERE source_id=?",
            (source_id,)
        ).fetchone()
        if not row:
            return None
        return SourceRecord(
            source_id=row[0],
            path=row[1],
            modality=Modality(row[2]),
            title=row[3],
            sha256=row[4],
            metadata=json.loads(row[5])
        )

    def all_sources(self) -> list[SourceRecord]:
        rows = self.conn.execute(
            "SELECT source_id, path, modality, title, sha256, metadata_json FROM sources ORDER BY source_id"
        ).fetchall()
        return [
            SourceRecord(
                source_id=r[0],
                path=r[1],
                modality=Modality(r[2]),
                title=r[3],
                sha256=r[4],
                metadata=json.loads(r[5])
            )
            for r in rows
        ]

    # --- Evidence ---
    def add_evidence(self, e: EvidenceUnit):
        self.conn.execute(
            "INSERT OR REPLACE INTO evidence VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                e.evidence_id,
                e.source_id,
                e.modality.value,
                e.text,
                json.dumps(e.location),
                e.evidence_type,
                e.asset_id,
                json.dumps(e.topics),
                json.dumps(e.concepts),
                json.dumps(e.prerequisites),
                json.dumps(e.metadata),
            )
        )
        self.conn.execute("DELETE FROM evidence_fts WHERE evidence_id=?", (e.evidence_id,))
        self.conn.execute(
            "INSERT INTO evidence_fts VALUES (?,?,?,?)",
            (e.evidence_id, e.text, " ".join(e.topics), " ".join(e.concepts))
        )

        # Relational synchronization
        for c_name in e.concepts:
            c_clean = c_name.strip()
            if not c_clean:
                continue
            self.conn.execute("INSERT OR IGNORE INTO concepts (concept_id, name) VALUES (?,?)", (c_clean, c_clean))
            self.conn.execute("INSERT OR IGNORE INTO evidence_concepts (evidence_id, concept_id) VALUES (?,?)", (e.evidence_id, c_clean))

        for t_name in e.topics:
            t_clean = t_name.strip()
            if not t_clean:
                continue
            self.conn.execute("INSERT OR IGNORE INTO topics (topic_id, name) VALUES (?,?)", (t_clean, t_clean))
            self.conn.execute("INSERT OR IGNORE INTO evidence_topics (evidence_id, topic_id) VALUES (?,?)", (e.evidence_id, t_clean))

        for p_name in e.prerequisites:
            p_clean = p_name.strip()
            if not p_clean:
                continue
            self.conn.execute("INSERT OR IGNORE INTO concepts (concept_id, name) VALUES (?,?)", (p_clean, p_clean))
            for c_name in e.concepts:
                c_clean = c_name.strip()
                if c_clean and c_clean != p_clean:
                    self.conn.execute("INSERT OR IGNORE INTO concept_prerequisites (concept_id, prerequisite_concept_id) VALUES (?,?)", (c_clean, p_clean))

        self.conn.commit()

    def get_evidence(self, evidence_id: str) -> EvidenceUnit | None:
        r = self.conn.execute(
            "SELECT evidence_id, source_id, modality, text, location_json, evidence_type, asset_id, topics_json, concepts_json, prerequisites_json, metadata_json FROM evidence WHERE evidence_id=?",
            (evidence_id,)
        ).fetchone()
        if not r:
            return None
        return EvidenceUnit(
            evidence_id=r[0],
            source_id=r[1],
            modality=Modality(r[2]),
            text=r[3],
            location=json.loads(r[4]),
            evidence_type=r[5],
            asset_id=r[6],
            topics=json.loads(r[7]),
            concepts=json.loads(r[8]),
            prerequisites=json.loads(r[9]),
            metadata=json.loads(r[10])
        )

    def all_evidence(self):
        for r in self.conn.execute(
            "SELECT evidence_id, source_id, modality, text, location_json, evidence_type, asset_id, topics_json, concepts_json, prerequisites_json, metadata_json FROM evidence ORDER BY evidence_id"
        ):
            yield EvidenceUnit(
                evidence_id=r[0],
                source_id=r[1],
                modality=Modality(r[2]),
                text=r[3],
                location=json.loads(r[4]),
                evidence_type=r[5],
                asset_id=r[6],
                topics=json.loads(r[7]),
                concepts=json.loads(r[8]),
                prerequisites=json.loads(r[9]),
                metadata=json.loads(r[10])
            )

    # --- Topics and Concepts ---
    def add_topic(self, topic_id: str, name: str, description: str = ""):
        self.conn.execute(
            "INSERT OR REPLACE INTO topics (topic_id, name, description) VALUES (?,?,?)",
            (topic_id, name, description)
        )
        self.conn.commit()

    def get_topic(self, topic_id: str) -> TopicRecord | None:
        row = self.conn.execute(
            "SELECT topic_id, name, description FROM topics WHERE topic_id=? OR name=?",
            (topic_id, topic_id)
        ).fetchone()
        if not row:
            return None
        return TopicRecord(topic_id=row[0], name=row[1], description=row[2] or "")

    def all_topics(self) -> list[TopicRecord]:
        rows = self.conn.execute("SELECT topic_id, name, description FROM topics ORDER BY topic_id").fetchall()
        return [TopicRecord(topic_id=r[0], name=r[1], description=r[2] or "") for r in rows]

    def add_concept(self, concept_id: str, name: str, topic_id: str | None = None, description: str = ""):
        if topic_id:
            self.conn.execute("INSERT OR IGNORE INTO topics (topic_id, name) VALUES (?,?)", (topic_id, topic_id))
        self.conn.execute(
            "INSERT OR REPLACE INTO concepts (concept_id, name, topic_id, description) VALUES (?,?,?,?)",
            (concept_id, name, topic_id, description)
        )
        self.conn.commit()

    def get_concept(self, concept_id: str) -> ConceptRecord | None:
        row = self.conn.execute(
            "SELECT concept_id, name, topic_id, description FROM concepts WHERE concept_id=? OR name=?",
            (concept_id, concept_id)
        ).fetchone()
        if not row:
            return None
        return ConceptRecord(concept_id=row[0], name=row[1], topic_id=row[2], description=row[3] or "")

    def all_concepts(self) -> list[ConceptRecord]:
        rows = self.conn.execute("SELECT concept_id, name, topic_id, description FROM concepts ORDER BY concept_id").fetchall()
        return [ConceptRecord(concept_id=r[0], name=r[1], topic_id=r[2], description=r[3] or "") for r in rows]

    def link_concept_prerequisite(self, concept_id: str, prerequisite_concept_id: str):
        self.conn.execute("INSERT OR IGNORE INTO concepts (concept_id, name) VALUES (?,?)", (concept_id, concept_id))
        self.conn.execute("INSERT OR IGNORE INTO concepts (concept_id, name) VALUES (?,?)", (prerequisite_concept_id, prerequisite_concept_id))
        self.conn.execute(
            "INSERT OR IGNORE INTO concept_prerequisites (concept_id, prerequisite_concept_id) VALUES (?,?)",
            (concept_id, prerequisite_concept_id)
        )
        self.conn.commit()

    def add_concept_prerequisite(self, concept_id: str, prerequisite_concept_id: str):
        self.link_concept_prerequisite(concept_id, prerequisite_concept_id)

    def get_concept_prerequisites(self, concept_id: str) -> list[str]:
        rows = self.conn.execute(
            "SELECT prerequisite_concept_id FROM concept_prerequisites WHERE concept_id=? ORDER BY prerequisite_concept_id",
            (concept_id,)
        ).fetchall()
        return [r[0] for r in rows]

    def get_prerequisites(self, concept_id: str) -> list[str]:
        return self.get_concept_prerequisites(concept_id)

    def get_all_prerequisites(self, concept_id: str) -> list[str]:
        visited: list[str] = []
        queue = deque(self.get_concept_prerequisites(concept_id))
        seen = set(queue)
        while queue:
            curr = queue.popleft()
            visited.append(curr)
            for prereq in self.get_concept_prerequisites(curr):
                if prereq != concept_id and prereq not in seen:
                    seen.add(prereq)
                    queue.append(prereq)
        return visited

    def get_concepts_for_evidence(self, evidence_id: str) -> list[ConceptRecord]:
        sql = (
            "SELECT c.concept_id, c.name, c.topic_id, c.description "
            "FROM concepts c JOIN evidence_concepts ec ON c.concept_id = ec.concept_id "
            "WHERE ec.evidence_id = ? ORDER BY c.concept_id"
        )
        rows = self.conn.execute(sql, (evidence_id,)).fetchall()
        return [ConceptRecord(concept_id=r[0], name=r[1], topic_id=r[2], description=r[3] or "") for r in rows]

    def get_evidence_for_concept(self, concept_id: str) -> list[EvidenceUnit]:
        sql = (
            "SELECT e.evidence_id, e.source_id, e.modality, e.text, e.location_json, "
            "e.evidence_type, e.asset_id, e.topics_json, e.concepts_json, e.prerequisites_json, e.metadata_json "
            "FROM evidence e JOIN evidence_concepts ec ON e.evidence_id = ec.evidence_id "
            "WHERE ec.concept_id = ? ORDER BY e.evidence_id"
        )
        rows = self.conn.execute(sql, (concept_id,)).fetchall()
        return [
            EvidenceUnit(
                evidence_id=r[0],
                source_id=r[1],
                modality=Modality(r[2]),
                text=r[3],
                location=json.loads(r[4]),
                evidence_type=r[5],
                asset_id=r[6],
                topics=json.loads(r[7]),
                concepts=json.loads(r[8]),
                prerequisites=json.loads(r[9]),
                metadata=json.loads(r[10])
            )
            for r in rows
        ]

    def get_evidence_for_topic(self, topic_id: str) -> list[EvidenceUnit]:
        sql = (
            "SELECT e.evidence_id, e.source_id, e.modality, e.text, e.location_json, "
            "e.evidence_type, e.asset_id, e.topics_json, e.concepts_json, e.prerequisites_json, e.metadata_json "
            "FROM evidence e JOIN evidence_topics et ON e.evidence_id = et.evidence_id "
            "WHERE et.topic_id = ? ORDER BY e.evidence_id"
        )
        rows = self.conn.execute(sql, (topic_id,)).fetchall()
        return [
            EvidenceUnit(
                evidence_id=r[0],
                source_id=r[1],
                modality=Modality(r[2]),
                text=r[3],
                location=json.loads(r[4]),
                evidence_type=r[5],
                asset_id=r[6],
                topics=json.loads(r[7]),
                concepts=json.loads(r[8]),
                prerequisites=json.loads(r[9]),
                metadata=json.loads(r[10])
            )
            for r in rows
        ]

    # --- Assets ---
    def add_asset(self, asset_id, evidence_id, mime_type, sha256, data, width=None, height=None):
        self.conn.execute(
            "INSERT OR REPLACE INTO assets VALUES (?,?,?,?,?,?,?)",
            (asset_id, evidence_id, mime_type, sha256, width, height, sqlite3.Binary(data))
        )
        self.conn.commit()

    def get_asset(self, asset_id):
        return self.conn.execute(
            "SELECT asset_id, evidence_id, mime_type, sha256, width, height, data FROM assets WHERE asset_id=?",
            (asset_id,)
        ).fetchone()

    # --- Embeddings ---
    def has_embeddings(self) -> bool:
        row = self.conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()
        return bool(row and row[0] > 0)

    def get_embedding_metadata(self) -> dict | None:
        row = self.conn.execute("SELECT dimension, model_name FROM embeddings WHERE dimension IS NOT NULL LIMIT 1").fetchone()
        if not row:
            return None
        return {"dimension": row[0], "model_name": row[1]}

    def add_embedding(self, evidence_id: str, vector, model_name: str | None = None):
        import numpy as np
        arr = np.asarray(vector, dtype="float32")
        dim = int(arr.shape[0])
        existing_meta = self.get_embedding_metadata()
        if existing_meta and existing_meta["dimension"] is not None and existing_meta["dimension"] != dim:
            raise ValueError(
                f"Embedding dimension mismatch: expected {existing_meta['dimension']}, got {dim}"
            )
        effective_model = model_name or (existing_meta["model_name"] if existing_meta else None)
        self.conn.execute(
            "INSERT OR REPLACE INTO embeddings (evidence_id, vector, model_name, dimension) VALUES (?,?,?,?)",
            (evidence_id, arr.tobytes(), effective_model, dim)
        )
        self.conn.commit()

    def get_embedding(self, evidence_id: str):
        row = self.conn.execute("SELECT vector FROM embeddings WHERE evidence_id=?", (evidence_id,)).fetchone()
        if not row:
            return None
        import numpy as np
        return np.frombuffer(row[0], dtype="float32")

    def get_embedding_info(self, evidence_id: str) -> dict | None:
        row = self.conn.execute("SELECT evidence_id, model_name, dimension FROM embeddings WHERE evidence_id=?", (evidence_id,)).fetchone()
        if not row:
            return None
        return {"evidence_id": row[0], "model_name": row[1], "dimension": row[2]}

    # --- FTS5 Lexical Search ---
    @staticmethod
    def _fts_query(query: str) -> str:
        tokens = re.findall(r"[A-Za-z0-9_]+", query.lower())
        if not tokens:
            return ""
        return " OR ".join(f'"{t.replace(chr(34), chr(34)+chr(34))}"' for t in dict.fromkeys(tokens))

    def fts_search(self, query: str, limit: int | None = None):
        match = self._fts_query(query)
        if not match:
            return []
        sql = (
            "SELECT evidence_id, bm25(evidence_fts) AS rank "
            "FROM evidence_fts WHERE evidence_fts MATCH ? ORDER BY rank, evidence_id"
        )
        params: list[str | int] = [match]
        if limit is not None:
            sql += " LIMIT ?"
            params.append(int(limit))
        return self.conn.execute(sql, params).fetchall()

    # --- Learner States (BKT) ---
    def save_learner_mastery(self, record: TopicMasteryRecord):
        self.conn.execute(
            "INSERT OR REPLACE INTO learner_states (learner_id, topic_id, p_mastery, attempts, correct, recent_correctness_json, last_seen) VALUES (?,?,?,?,?,?,?)",
            (
                record.learner_id,
                record.topic_id,
                float(record.p_mastery),
                int(record.attempts),
                int(record.correct),
                json.dumps(record.recent_correctness),
                record.last_seen,
            )
        )
        self.conn.commit()

    def get_learner_mastery(self, learner_id: str, topic_id: str) -> TopicMasteryRecord | None:
        row = self.conn.execute(
            "SELECT learner_id, topic_id, p_mastery, attempts, correct, recent_correctness_json, last_seen FROM learner_states WHERE learner_id=? AND topic_id=?",
            (learner_id, topic_id)
        ).fetchone()
        if not row:
            return None
        return TopicMasteryRecord(
            learner_id=row[0],
            topic_id=row[1],
            p_mastery=float(row[2]),
            attempts=int(row[3]),
            correct=int(row[4]),
            recent_correctness=json.loads(row[5]),
            last_seen=row[6],
        )

    def get_all_learner_masteries(self, learner_id: str) -> list[TopicMasteryRecord]:
        rows = self.conn.execute(
            "SELECT learner_id, topic_id, p_mastery, attempts, correct, recent_correctness_json, last_seen FROM learner_states WHERE learner_id=? ORDER BY topic_id",
            (learner_id,)
        ).fetchall()
        return [
            TopicMasteryRecord(
                learner_id=r[0],
                topic_id=r[1],
                p_mastery=float(r[2]),
                attempts=int(r[3]),
                correct=int(r[4]),
                recent_correctness=json.loads(r[5]),
                last_seen=r[6],
            )
            for r in rows
        ]

    # --- Questions ---
    def add_question(self, q: Question):
        options_data = [opt.model_dump() for opt in q.options]
        self.conn.execute(
            "INSERT OR REPLACE INTO questions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                q.question_id,
                q.topic_id,
                q.concept_id,
                json.dumps(q.evidence_ids),
                q.difficulty.value,
                q.question_type.value,
                q.prompt,
                json.dumps(options_data),
                q.expected_answer,
                q.tolerance,
                q.solution,
                q.verification_status,
                q.verification_reason,
                q.fingerprint,
                q.repetition_count,
                json.dumps(q.metadata),
            )
        )
        self.conn.commit()

    def get_question(self, question_id: str) -> Question | None:
        row = self.conn.execute(
            "SELECT question_id, topic_id, concept_id, evidence_ids_json, difficulty, question_type, prompt, options_json, expected_answer, tolerance, solution, verification_status, verification_reason, fingerprint, repetition_count, metadata_json FROM questions WHERE question_id=?",
            (question_id,)
        ).fetchone()
        if not row:
            return None
        raw_options = json.loads(row[7])
        options = [QuestionOption(**opt) for opt in raw_options]
        return Question(
            question_id=row[0],
            topic_id=row[1],
            concept_id=row[2],
            evidence_ids=json.loads(row[3]),
            difficulty=Difficulty(row[4]),
            question_type=QuestionType(row[5]),
            prompt=row[6],
            options=options,
            expected_answer=row[8],
            tolerance=row[9],
            solution=row[10],
            verification_status=row[11],
            verification_reason=row[12],
            fingerprint=row[13],
            repetition_count=int(row[14]),
            metadata=json.loads(row[15]),
        )

    def get_questions_for_topic(self, topic_id: str, verified_only: bool = True) -> list[Question]:
        sql = "SELECT question_id, topic_id, concept_id, evidence_ids_json, difficulty, question_type, prompt, options_json, expected_answer, tolerance, solution, verification_status, verification_reason, fingerprint, repetition_count, metadata_json FROM questions WHERE topic_id=?"
        params = [topic_id]
        if verified_only:
            sql += " AND verification_status='verified'"
        sql += " ORDER BY question_id"
        rows = self.conn.execute(sql, params).fetchall()
        out = []
        for row in rows:
            raw_options = json.loads(row[7])
            options = [QuestionOption(**opt) for opt in raw_options]
            out.append(
                Question(
                    question_id=row[0],
                    topic_id=row[1],
                    concept_id=row[2],
                    evidence_ids=json.loads(row[3]),
                    difficulty=Difficulty(row[4]),
                    question_type=QuestionType(row[5]),
                    prompt=row[6],
                    options=options,
                    expected_answer=row[8],
                    tolerance=row[9],
                    solution=row[10],
                    verification_status=row[11],
                    verification_reason=row[12],
                    fingerprint=row[13],
                    repetition_count=int(row[14]),
                    metadata=json.loads(row[15]),
                )
            )
        return out

    def all_questions(self, verified_only: bool = False) -> list[Question]:
        sql = "SELECT question_id, topic_id, concept_id, evidence_ids_json, difficulty, question_type, prompt, options_json, expected_answer, tolerance, solution, verification_status, verification_reason, fingerprint, repetition_count, metadata_json FROM questions"
        if verified_only:
            sql += " WHERE verification_status='verified'"
        sql += " ORDER BY question_id"
        rows = self.conn.execute(sql).fetchall()
        out = []
        for row in rows:
            raw_options = json.loads(row[7])
            options = [QuestionOption(**opt) for opt in raw_options]
            out.append(
                Question(
                    question_id=row[0],
                    topic_id=row[1],
                    concept_id=row[2],
                    evidence_ids=json.loads(row[3]),
                    difficulty=Difficulty(row[4]),
                    question_type=QuestionType(row[5]),
                    prompt=row[6],
                    options=options,
                    expected_answer=row[8],
                    tolerance=row[9],
                    solution=row[10],
                    verification_status=row[11],
                    verification_reason=row[12],
                    fingerprint=row[13],
                    repetition_count=int(row[14]),
                    metadata=json.loads(row[15]),
                )
            )
        return out

    # --- Learner Interactions ---
    def record_interaction(self, interaction_id: str, learner_id: str, question_id: str, topic_id: str, user_answer: str, is_correct: bool, score: float, feedback: str, timestamp: str | None = None) -> str:
        from datetime import datetime, timezone
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT OR REPLACE INTO learner_interactions VALUES (?,?,?,?,?,?,?,?,?)",
            (
                interaction_id,
                learner_id,
                question_id,
                topic_id,
                user_answer,
                1 if is_correct else 0,
                float(score),
                feedback,
                ts,
            )
        )
        self.conn.commit()
        return interaction_id

    def get_interactions(self, learner_id: str, topic_id: str | None = None) -> list[dict]:
        sql = "SELECT interaction_id, learner_id, question_id, topic_id, user_answer, is_correct, score, feedback, timestamp FROM learner_interactions WHERE learner_id=?"
        params = [learner_id]
        if topic_id:
            sql += " AND topic_id=?"
            params.append(topic_id)
        sql += " ORDER BY timestamp ASC"
        rows = self.conn.execute(sql, params).fetchall()
        return [
            {
                "interaction_id": r[0],
                "learner_id": r[1],
                "question_id": r[2],
                "topic_id": r[3],
                "user_answer": r[4],
                "is_correct": bool(r[5]),
                "score": float(r[6]),
                "feedback": r[7],
                "timestamp": r[8],
            }
            for r in rows
        ]

    # --- Error Signals & Misconceptions ---
    def record_error_signal(self, learner_id: str, topic_id: str, concept_id: str, error_pattern: str) -> int:
        from datetime import datetime, timezone
        key = f"{learner_id}:{topic_id}:{concept_id}:{error_pattern}"
        now = datetime.now(timezone.utc).isoformat()
        row = self.conn.execute("SELECT occurrence_count FROM error_signals WHERE signal_key=?", (key,)).fetchone()
        if row:
            new_count = int(row[0]) + 1
            self.conn.execute("UPDATE error_signals SET occurrence_count=?, last_occurred=? WHERE signal_key=?", (new_count, now, key))
        else:
            new_count = 1
            self.conn.execute("INSERT INTO error_signals VALUES (?,?,?,?,?,?,?)", (key, learner_id, topic_id, concept_id, error_pattern, new_count, now))
        self.conn.commit()
        return new_count

    def get_error_signal_count(self, learner_id: str, topic_id: str, concept_id: str, error_pattern: str | None = None) -> int:
        if error_pattern:
            key = f"{learner_id}:{topic_id}:{concept_id}:{error_pattern}"
            row = self.conn.execute("SELECT occurrence_count FROM error_signals WHERE signal_key=?", (key,)).fetchone()
            return int(row[0]) if row else 0
        rows = self.conn.execute("SELECT occurrence_count FROM error_signals WHERE learner_id=? AND topic_id=? AND concept_id=?", (learner_id, topic_id, concept_id)).fetchall()
        return sum(int(r[0]) for r in rows)

    def reset_error_signal(self, learner_id: str, topic_id: str, concept_id: str):
        self.conn.execute("DELETE FROM error_signals WHERE learner_id=? AND topic_id=? AND concept_id=?", (learner_id, topic_id, concept_id))
        self.conn.commit()

    def add_misconception(self, m: MisconceptionSignal):
        self.conn.execute(
            "INSERT OR REPLACE INTO misconceptions VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                m.signal_id,
                m.learner_id,
                m.topic_id,
                m.concept_id,
                m.suspected_misconception,
                int(m.error_count),
                float(m.confidence),
                m.remediation_concept_id,
                json.dumps(m.remediation_evidence_ids),
                m.remediation_note,
                m.created_at,
            )
        )
        self.conn.commit()

    def get_active_misconceptions(self, learner_id: str, topic_id: str | None = None) -> list[MisconceptionSignal]:
        sql = "SELECT signal_id, learner_id, topic_id, concept_id, suspected_misconception, error_count, confidence, remediation_concept_id, remediation_evidence_ids_json, remediation_note, created_at FROM misconceptions WHERE learner_id=?"
        params = [learner_id]
        if topic_id:
            sql += " AND topic_id=?"
            params.append(topic_id)
        sql += " ORDER BY created_at DESC"
        rows = self.conn.execute(sql, params).fetchall()
        return [
            MisconceptionSignal(
                signal_id=r[0],
                learner_id=r[1],
                topic_id=r[2],
                concept_id=r[3],
                suspected_misconception=r[4],
                error_count=int(r[5]),
                confidence=float(r[6]),
                remediation_concept_id=r[7],
                remediation_evidence_ids=json.loads(r[8]),
                remediation_note=r[9],
                created_at=r[10],
            )
            for r in rows
        ]

    def clear_misconceptions(self, learner_id: str, topic_id: str | None = None):
        if topic_id:
            self.conn.execute("DELETE FROM misconceptions WHERE learner_id=? AND topic_id=?", (learner_id, topic_id))
        else:
            self.conn.execute("DELETE FROM misconceptions WHERE learner_id=?", (learner_id,))
        self.conn.commit()

