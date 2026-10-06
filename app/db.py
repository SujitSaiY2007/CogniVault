from __future__ import annotations
import json, re, sqlite3
from pathlib import Path
from .models import EvidenceUnit, SourceRecord

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources(
 source_id TEXT PRIMARY KEY, path TEXT NOT NULL, modality TEXT NOT NULL,
 title TEXT NOT NULL, sha256 TEXT NOT NULL, metadata_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS evidence(
 evidence_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, modality TEXT NOT NULL,
 text TEXT NOT NULL, location_json TEXT NOT NULL, evidence_type TEXT NOT NULL,
 topics_json TEXT NOT NULL, concepts_json TEXT NOT NULL, prerequisites_json TEXT NOT NULL,
 metadata_json TEXT NOT NULL, FOREIGN KEY(source_id) REFERENCES sources(source_id));
CREATE VIRTUAL TABLE IF NOT EXISTS evidence_fts USING fts5(
 evidence_id UNINDEXED, text, topics, concepts);
CREATE TABLE IF NOT EXISTS embeddings(evidence_id TEXT PRIMARY KEY, vector BLOB NOT NULL);
"""

class EvidenceDB:
    def __init__(self, path: str|Path):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.conn=sqlite3.connect(self.path); self.conn.execute("PRAGMA foreign_keys=ON"); self.conn.executescript(SCHEMA)

    def add_source(self,s):
        self.conn.execute("INSERT OR REPLACE INTO sources VALUES (?,?,?,?,?,?)",
            (s.source_id,s.path,s.modality.value,s.title,s.sha256,json.dumps(s.metadata))); self.conn.commit()

    def add_evidence(self,e):
        self.conn.execute("INSERT OR REPLACE INTO evidence VALUES (?,?,?,?,?,?,?,?,?,?)",
            (e.evidence_id,e.source_id,e.modality.value,e.text,json.dumps(e.location),e.evidence_type,
             json.dumps(e.topics),json.dumps(e.concepts),json.dumps(e.prerequisites),json.dumps(e.metadata)))
        self.conn.execute("DELETE FROM evidence_fts WHERE evidence_id=?",(e.evidence_id,))
        self.conn.execute("INSERT INTO evidence_fts VALUES (?,?,?,?)",
            (e.evidence_id,e.text," ".join(e.topics)," ".join(e.concepts)))
        self.conn.commit()

    def add_embedding(self,evidence_id,vector):
        import numpy as np
        self.conn.execute("INSERT OR REPLACE INTO embeddings VALUES (?,?)",
            (evidence_id,np.asarray(vector,dtype="float32").tobytes())); self.conn.commit()

    def get_embedding(self,evidence_id):
        row=self.conn.execute("SELECT vector FROM embeddings WHERE evidence_id=?",(evidence_id,)).fetchone()
        if not row:return None
        import numpy as np
        return np.frombuffer(row[0],dtype="float32")

    @staticmethod
    def _fts_query(query):
        tokens=re.findall(r"[A-Za-z0-9_]+",query.lower())
        return " OR ".join(f'"{t.replace(chr(34), chr(34)+chr(34))}"' for t in dict.fromkeys(tokens))

    def fts_search(self,query,limit=None):
        match=self._fts_query(query)
        if not match:return []
        sql=("SELECT evidence_id, bm25(evidence_fts) AS rank "
             "FROM evidence_fts WHERE evidence_fts MATCH ? ORDER BY rank, evidence_id")
        params=[match]
        if limit is not None:
            sql += " LIMIT ?"; params.append(int(limit))
        return self.conn.execute(sql,params).fetchall()

    def all_evidence(self):
        for r in self.conn.execute("SELECT * FROM evidence ORDER BY evidence_id"):
            yield EvidenceUnit(evidence_id=r[0],source_id=r[1],modality=r[2],text=r[3],location=json.loads(r[4]),evidence_type=r[5],topics=json.loads(r[6]),concepts=json.loads(r[7]),prerequisites=json.loads(r[8]),metadata=json.loads(r[9]))

    def get_evidence(self,evidence_id):
        r=self.conn.execute("SELECT * FROM evidence WHERE evidence_id=?",(evidence_id,)).fetchone()
        if not r:return None
        return EvidenceUnit(evidence_id=r[0],source_id=r[1],modality=r[2],text=r[3],location=json.loads(r[4]),evidence_type=r[5],topics=json.loads(r[6]),concepts=json.loads(r[7]),prerequisites=json.loads(r[8]),metadata=json.loads(r[9]))
