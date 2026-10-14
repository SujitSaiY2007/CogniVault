"""
ChromaDB persistent vector store for CogniVault evidence units.
Integrates with SQLite/FTS5 while preserving exact physical locators.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional
import numpy as np

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    chromadb = None

from .models import EvidenceUnit, Modality


class ChromaEvidenceStore:
    """Manages dense vector storage and similarity search for evidence units via ChromaDB."""

    COLLECTION_NAME = "cognivault_evidence"

    def __init__(
        self,
        persist_directory: Optional[str | Path] = None,
        in_memory: bool = False,
        collection_name: Optional[str] = None,
    ):
        if chromadb is None:
            raise ImportError("chromadb is not installed. Install with `pip install chromadb`.")

        self.persist_directory = str(persist_directory) if persist_directory else None
        self.in_memory = in_memory
        self.collection_name = collection_name or self.COLLECTION_NAME

        if in_memory or not self.persist_directory:
            self.client = chromadb.Client()
        else:
            os.makedirs(self.persist_directory, exist_ok=True)
            self.client = chromadb.PersistentClient(path=self.persist_directory)

        # Use cosine similarity space for normalized vector comparison
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def reset(self) -> None:
        """Drop and recreate the collection for clean testing isolation."""
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def count(self) -> int:
        """Return total indexed evidence units in ChromaDB."""
        return self.collection.count()

    def add_evidence(
        self,
        unit: EvidenceUnit,
        embedding: list[float] | np.ndarray,
    ) -> None:
        """Add a single evidence unit with its vector embedding."""
        self.batch_add_evidence([unit], [embedding])

    def batch_add_evidence(
        self,
        units: list[EvidenceUnit],
        embeddings: list[list[float]] | list[np.ndarray] | np.ndarray,
    ) -> None:
        """Add or update multiple evidence units with embeddings."""
        if not units:
            return

        ids = [u.evidence_id for u in units]
        documents = [u.text for u in units]
        metadatas = []
        for u in units:
            loc = u.location if isinstance(u.location, dict) else {}
            loc_val = str(loc.get("page") or loc.get("slide") or loc.get("timestamp") or loc.get("locator") or "")
            first_topic = (u.topics[0] if getattr(u, "topics", None) else getattr(u, "topic", "")) or ""
            first_concept = (u.concepts[0] if getattr(u, "concepts", None) else getattr(u, "concept", "")) or ""
            metadatas.append({
                "source_id": u.source_id,
                "modality": u.modality.value if isinstance(u.modality, Modality) else str(u.modality),
                "locator_value": loc_val,
                "topic": first_topic,
                "concept": first_concept,
                "topics": ",".join(getattr(u, "topics", [])) if getattr(u, "topics", None) else first_topic,
                "concepts": ",".join(getattr(u, "concepts", [])) if getattr(u, "concepts", None) else first_concept,
            })

        # Convert numpy embeddings to standard Python float lists
        proc_embeddings: list[list[float]] = []
        for emb in embeddings:
            if isinstance(emb, np.ndarray):
                proc_embeddings.append(emb.astype(float).tolist())
            else:
                proc_embeddings.append([float(x) for x in emb])

        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=proc_embeddings,
        )

    def query(
        self,
        query_embedding: list[float] | np.ndarray,
        top_k: int = 5,
        topic_filter: Optional[str] = None,
        modality_filter: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Query nearest evidence units by cosine similarity.
        Returns a list of dicts: {'evidence_id', 'similarity', 'metadata', 'document'}.
        """
        if self.count() == 0:
            return []

        if isinstance(query_embedding, np.ndarray):
            q_emb = [query_embedding.astype(float).tolist()]
        else:
            q_emb = [[float(x) for x in query_embedding]]

        where_clause: dict[str, Any] = {}
        filters: list[dict[str, Any]] = []
        if topic_filter:
            filters.append({"topic": topic_filter})
        if modality_filter:
            filters.append({"modality": modality_filter})

        if len(filters) == 1:
            where_clause = filters[0]
        elif len(filters) > 1:
            where_clause = {"$and": filters}

        kwargs: dict[str, Any] = {
            "query_embeddings": q_emb,
            "n_results": min(top_k, max(1, self.count())),
        }
        if where_clause:
            kwargs["where"] = where_clause

        res = self.collection.query(**kwargs)

        results: list[dict[str, Any]] = []
        ids_list = res.get("ids", [[]])[0]
        distances = res.get("distances", [[]])[0]
        metadatas = res.get("metadatas", [[]])[0]
        documents = res.get("documents", [[]])[0]

        for i, eid in enumerate(ids_list):
            dist = float(distances[i]) if distances else 0.0
            # For cosine distance (in [0, 2]), similarity = max(0.0, 1.0 - dist)
            similarity = round(max(0.0, min(1.0, 1.0 - dist)), 6)
            results.append({
                "evidence_id": eid,
                "similarity": similarity,
                "distance": dist,
                "metadata": metadatas[i] if metadatas else {},
                "document": documents[i] if documents else "",
            })

        return results

    def delete_evidence(self, evidence_id: str) -> None:
        """Remove an evidence unit from ChromaDB by ID."""
        self.collection.delete(ids=[evidence_id])

    def get_by_id(self, evidence_id: str) -> Optional[dict[str, Any]]:
        """Retrieve stored evidence unit metadata and document by ID."""
        res = self.collection.get(ids=[evidence_id], include=["metadatas", "documents"])
        ids = res.get("ids", [])
        if not ids:
            return None
        metadatas = res.get("metadatas", [{}])
        documents = res.get("documents", [""])
        return {
            "evidence_id": ids[0],
            "metadata": metadatas[0] if metadatas else {},
            "document": documents[0] if documents else "",
        }

    def sync_from_sqlite(self, db, embedder=None) -> int:
        """
        Synchronize all evidence records and embeddings from SQLite EvidenceDB into ChromaDB.
        Returns number of synchronized units.
        """
        all_units = list(db.all_evidence())
        if not all_units:
            return 0

        synced_count = 0
        units_to_add: list[EvidenceUnit] = []
        embeddings_to_add: list[list[float]] = []

        for unit in all_units:
            emb = db.get_embedding(unit.evidence_id)
            if emb is None and embedder is not None:
                emb = embedder.encode(unit.text).tolist()
                db.store_embedding(unit.evidence_id, emb, getattr(embedder, "model_name", "default"))

            if emb is not None:
                units_to_add.append(unit)
                embeddings_to_add.append(emb if isinstance(emb, list) else list(emb))
                synced_count += 1

        if units_to_add:
            self.batch_add_evidence(units_to_add, embeddings_to_add)

        return synced_count
