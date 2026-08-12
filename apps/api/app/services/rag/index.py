"""
Index manager — the persistent/cached dense-retrieval layer that keeps us from
re-embedding and rebuilding the vector index on every query (the #1 prod flaw).

Two backends behind one interface (`DenseIndex.search`):
  - PgVectorStore  — durable, in-DB ANN, used when DATABASE_URL is Postgres +
    pgvector installed. Ingest upserts once; queries hit the DB index.
  - _CachedMemoryIndex — process-wide cached in-memory numpy/HNSW store, keyed by
    (collection, content-fingerprint). Built once per unique doc set and reused
    across requests; only rebuilds when the corpus actually changes. This is what
    makes the SQLite/dev path scale to many queries without per-request rebuilds.

Thread-safe: build/lookup guarded by a lock; concurrent queries for the same
collection share one index instead of each constructing their own.
"""
from __future__ import annotations

import hashlib
import logging
import threading
from typing import Dict, List, Optional, Protocol

from .types import Document, ScoredDoc
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


class DenseIndex(Protocol):
    def search(self, query: str, top_k: int = 12) -> List[ScoredDoc]: ...


def fingerprint(docs: List[Document]) -> str:
    """Cheap content hash of a doc set — changes iff the corpus changes."""
    h = hashlib.sha1()
    h.update(str(len(docs)).encode())
    for d in docs:
        h.update(d.id.encode("utf-8", "ignore"))
        h.update(b"\x00")
        h.update(d.text.encode("utf-8", "ignore"))
        h.update(b"\x01")
    return h.hexdigest()


class _CachedMemoryIndex:
    """Wraps a built VectorStore so it is reused until the fingerprint changes."""

    def __init__(self, store: VectorStore, fp: str):
        self.store = store
        self.fp = fp

    def search(self, query: str, top_k: int = 12) -> List[ScoredDoc]:
        return self.store.search(query, top_k=top_k)


class IndexManager:
    """Process-wide registry of dense indexes, one per collection."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._mem: Dict[str, _CachedMemoryIndex] = {}
        self._pg: Dict[str, object] = {}

    # ── memory (dev / SQLite) ──────────────────────────────────────────────────
    def get_memory_index(self, collection: str, docs: List[Document]) -> _CachedMemoryIndex:
        """Return a cached in-memory index, rebuilding only if docs changed.
        Raises EmbeddingUnavailable (from VectorStore.build) if embeddings are down."""
        fp = fingerprint(docs)
        with self._lock:
            cached = self._mem.get(collection)
            if cached is not None and cached.fp == fp:
                return cached  # reuse — no re-embed, no rebuild
        # Build outside the lock (embedding can be slow); then publish.
        store = VectorStore.build(docs)
        idx = _CachedMemoryIndex(store, fp)
        with self._lock:
            self._mem[collection] = idx
        return idx

    # ── pgvector (prod / Postgres) ─────────────────────────────────────────────
    def pg_available(self) -> bool:
        try:
            from . import pgvector_store
            return pgvector_store.pg_available()
        except Exception:
            return False

    def get_pg_store(self, collection: str):
        with self._lock:
            store = self._pg.get(collection)
            if store is not None:
                return store
        from . import pgvector_store
        store = pgvector_store.PgVectorStore(collection=collection)
        with self._lock:
            self._pg[collection] = store
        return store

    def invalidate(self, collection: str) -> None:
        with self._lock:
            self._mem.pop(collection, None)


# Module-level singleton.
_MANAGER = IndexManager()


def get_manager() -> IndexManager:
    return _MANAGER
