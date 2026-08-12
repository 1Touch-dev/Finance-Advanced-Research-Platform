"""
Durable pgvector-backed store (Postgres) — the production upgrade for the
in-memory numpy VectorStore. Persists chunk vectors so they survive restarts and
so ANN search happens in-DB instead of re-embedding + rebuilding per query.

Activation (all must hold, else callers use the in-memory store):
  - DATABASE_URL is Postgres
  - `pgvector` python package importable
  - RAG_VECTOR_BACKEND != "memory"
  - the pgvector extension + table can be created

Interface mirrors VectorStore.search() so retriever.py is agnostic to the backend.
Schema: rag_embeddings(id text pk, collection text, doc_id text, text text,
source text, metadata jsonb, embedding vector(dim)).
"""
from __future__ import annotations

import logging
import os
from typing import List, Optional

import numpy as np

from . import embeddings
from .types import Document, ScoredDoc

logger = logging.getLogger(__name__)

_BACKEND = os.getenv("RAG_VECTOR_BACKEND", "auto")  # auto | pg | memory
_TABLE = os.getenv("RAG_PG_TABLE", "rag_embeddings")


def pg_available() -> bool:
    """True if the durable backend should/can be used."""
    if _BACKEND == "memory":
        return False
    try:
        from app.core.settings import settings
        url = settings.database_url
    except Exception:
        url = os.getenv("DATABASE_URL", "")
    if not url.startswith(("postgres://", "postgresql://", "postgresql+")):
        return False
    try:
        import pgvector  # noqa: F401
        import sqlalchemy  # noqa: F401
    except ImportError:
        logger.info("pgvector/sqlalchemy missing; using in-memory vector store")
        return False
    return True


class PgVectorStore:
    """Persistent vector store. upsert() at ingest, search() at query time."""

    def __init__(self, collection: str = "default"):
        self.collection = collection
        self.dim = embeddings.model_dim()
        self._current_lists = 100  # matches the create-time default
        self._engine = self._make_engine()
        self._ensure_schema()

    def _make_engine(self):
        from sqlalchemy import create_engine
        try:
            from app.core.settings import settings
            url = settings.database_url
        except Exception:
            url = os.getenv("DATABASE_URL", "")
        return create_engine(url, pool_pre_ping=True, future=True)

    def _ensure_schema(self) -> None:
        from sqlalchemy import text
        with self._engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.execute(text(
                f"""CREATE TABLE IF NOT EXISTS {_TABLE} (
                    id TEXT PRIMARY KEY,
                    collection TEXT NOT NULL,
                    doc_id TEXT,
                    text TEXT,
                    source TEXT,
                    metadata JSONB,
                    embedding vector({self.dim})
                )"""
            ))
            # IVFFlat ANN index (cosine). Created once; harmless if it exists.
            conn.execute(text(
                f"CREATE INDEX IF NOT EXISTS {_TABLE}_emb_idx ON {_TABLE} "
                f"USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
            ))
            self._check_dim_migration(conn)

    def _check_dim_migration(self, conn) -> None:
        """
        Re-embed / dim-migration story: if RAG_EMBED_MODEL changed and the new
        embedding dim differs from the persisted vector(dim), the old rows are
        unusable. We detect the mismatch and (only when explicitly allowed via
        RAG_PG_ALLOW_REEMBED=1) drop+recreate the column so a re-ingest repopulates
        it. Otherwise we log a loud warning and leave data intact for a manual,
        auditable migration.
        """
        from sqlalchemy import text
        try:
            existing = conn.execute(text(
                f"""SELECT a.atttypmod FROM pg_attribute a
                    JOIN pg_class c ON a.attrelid = c.oid
                    WHERE c.relname = '{_TABLE}' AND a.attname = 'embedding'"""
            )).scalar()
        except Exception:
            return
        if existing is None or existing <= 0:
            return
        current_dim = int(existing)
        if current_dim == self.dim:
            return
        if os.getenv("RAG_PG_ALLOW_REEMBED", "0") == "1":
            logger.warning(
                "pgvector dim changed %s→%s; dropping embeddings for re-ingest (RAG_PG_ALLOW_REEMBED=1)",
                current_dim, self.dim,
            )
            conn.execute(text(f"DROP INDEX IF EXISTS {_TABLE}_emb_idx"))
            conn.execute(text(f"TRUNCATE {_TABLE}"))
            conn.execute(text(f"ALTER TABLE {_TABLE} ALTER COLUMN embedding TYPE vector({self.dim})"))
            conn.execute(text(
                f"CREATE INDEX {_TABLE}_emb_idx ON {_TABLE} "
                f"USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
            ))
        else:
            logger.error(
                "pgvector embedding dim mismatch: table=%s, model=%s. Old vectors are "
                "STALE. Set RAG_PG_ALLOW_REEMBED=1 and re-ingest to migrate.",
                current_dim, self.dim,
            )

    def upsert(self, docs: List[Document]) -> int:
        """Embed + persist docs. Returns count written."""
        if not docs:
            return 0
        matrix = embeddings.embed_texts([d.text for d in docs])
        from sqlalchemy import text
        import json
        rows = []
        for d, vec in zip(docs, matrix):
            rows.append({
                "id": f"{self.collection}:{d.id}",
                "collection": self.collection,
                "doc_id": d.id,
                "text": d.text,
                "source": d.source,
                "metadata": json.dumps(d.metadata or {}),
                "embedding": "[" + ",".join(f"{x:.6f}" for x in vec.tolist()) + "]",
            })
        with self._engine.begin() as conn:
            conn.execute(text(
                f"""INSERT INTO {_TABLE} (id, collection, doc_id, text, source, metadata, embedding)
                    VALUES (:id, :collection, :doc_id, :text, :source, CAST(:metadata AS JSONB), CAST(:embedding AS vector))
                    ON CONFLICT (id) DO UPDATE SET
                        text = EXCLUDED.text, source = EXCLUDED.source,
                        metadata = EXCLUDED.metadata, embedding = EXCLUDED.embedding"""
            ), rows)
        self._maybe_tune_index()
        return len(rows)

    def _maybe_tune_index(self) -> None:
        """
        IVFFlat recall/speed depends on `lists` ≈ sqrt(row_count). We hardcoded 100
        at create time; once the table grows we rebuild the index with a tuned value
        and ANALYZE so the planner has fresh stats. Cheap heuristic, runs rarely.
        """
        from sqlalchemy import text
        import math
        try:
            with self._engine.begin() as conn:
                n = conn.execute(
                    text(f"SELECT count(*) FROM {_TABLE} WHERE collection = :c"),
                    {"c": self.collection},
                ).scalar() or 0
                target = max(1, int(math.sqrt(max(n, 1))))
                # Only rebuild on meaningful growth to avoid churn.
                if n >= 1000 and target != self._current_lists:
                    conn.execute(text(f"DROP INDEX IF EXISTS {_TABLE}_emb_idx"))
                    conn.execute(text(
                        f"CREATE INDEX {_TABLE}_emb_idx ON {_TABLE} "
                        f"USING ivfflat (embedding vector_cosine_ops) WITH (lists = {target})"
                    ))
                    self._current_lists = target
                conn.execute(text(f"ANALYZE {_TABLE}"))
        except Exception as exc:
            logger.debug("pgvector index tune skipped: %s", exc)

    def search(self, query: str, top_k: int = 12) -> List[ScoredDoc]:
        qvec = embeddings.embed_query(query)
        qlit = "[" + ",".join(f"{x:.6f}" for x in qvec.tolist()) + "]"
        from sqlalchemy import text
        import json
        with self._engine.connect() as conn:
            # cosine distance operator <=> ; similarity = 1 - distance
            res = conn.execute(text(
                f"""SELECT doc_id, text, source, metadata,
                           1 - (embedding <=> CAST(:q AS vector)) AS score
                    FROM {_TABLE}
                    WHERE collection = :c
                    ORDER BY embedding <=> CAST(:q AS vector)
                    LIMIT :k"""
            ), {"q": qlit, "c": self.collection, "k": top_k})
            out = []
            for row in res:
                meta = row.metadata if isinstance(row.metadata, dict) else json.loads(row.metadata or "{}")
                doc = Document(id=row.doc_id, text=row.text, source=row.source or "", metadata=meta)
                out.append(ScoredDoc(doc, float(row.score), {"dense": float(row.score)}))
            return out
