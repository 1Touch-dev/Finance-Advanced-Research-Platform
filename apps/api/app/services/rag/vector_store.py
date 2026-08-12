"""
Vector store — in-process dense retrieval.

Storage today is in-memory (the ingestion service holds chunks in dicts), so this
store is built per-collection from Document lists and optionally persisted to disk
under EXPORT_DIR/rag_index/. Brute-force cosine (normalized dot product) is the
small-N path and the always-available fallback; an HNSW index (faiss/hnswlib) is
used transparently once the collection grows past RAG_HNSW_MIN.

pgvector-on-Postgres is the documented follow-up (see docs/RAG-Upgrade-Plan.md);
it slots behind this same interface once durable storage exists.
"""
from __future__ import annotations

import logging
import os
from typing import List, Optional, Tuple

import numpy as np

from . import embeddings
from .types import Document, ScoredDoc

logger = logging.getLogger(__name__)

_HNSW_MIN = int(os.getenv("RAG_HNSW_MIN", "2000"))
# Query-time accuracy/latency knob (higher = better recall, slower). Tunable
# without rebuilding the index.
_HNSW_EF = int(os.getenv("RAG_HNSW_EF", "128"))
_HNSW_EF_CONSTRUCTION = int(os.getenv("RAG_HNSW_EF_CONSTRUCTION", "200"))
_HNSW_M = int(os.getenv("RAG_HNSW_M", "16"))
# Force exact brute-force cosine even past _HNSW_MIN. For small/critical
# (compliance) corpora where a silently-missed neighbor is unacceptable.
_EXACT_SEARCH = os.getenv("RAG_EXACT_SEARCH", "false").lower() in ("1", "true", "yes")


class VectorStore:
    """Holds documents + their embedding matrix for one collection."""

    def __init__(self, docs: List[Document], matrix: np.ndarray):
        self.docs = docs
        self.matrix = matrix  # (n, dim) normalized
        self._hnsw = None
        if matrix is not None and not _EXACT_SEARCH and len(docs) >= _HNSW_MIN:
            self._try_build_hnsw()

    # ── construction ─────────────────────────────────────────────────────────
    @classmethod
    def build(cls, docs: List[Document]) -> "VectorStore":
        """Embed all docs and build the store. Raises EmbeddingUnavailable upstream."""
        texts = [d.text for d in docs]
        matrix = embeddings.embed_texts(texts) if texts else np.zeros((0, embeddings.model_dim()), dtype=np.float32)
        return cls(docs, matrix)

    def _try_build_hnsw(self) -> None:
        try:
            import hnswlib  # optional
        except ImportError:
            logger.info("hnswlib not installed; using brute-force cosine (fine for N=%d)", len(self.docs))
            return
        try:
            dim = self.matrix.shape[1]
            index = hnswlib.Index(space="cosine", dim=dim)
            index.init_index(max_elements=len(self.docs), ef_construction=_HNSW_EF_CONSTRUCTION, M=_HNSW_M)
            index.add_items(self.matrix, np.arange(len(self.docs)))
            index.set_ef(max(_HNSW_EF, 1))
            self._hnsw = index
            logger.info("Built HNSW index over %d docs (ef=%d, M=%d)", len(self.docs), _HNSW_EF, _HNSW_M)
        except Exception as exc:
            logger.warning("HNSW build failed, falling back to brute force: %s", exc)
            self._hnsw = None

    # ── search ────────────────────────────────────────────────────────────────
    def search(self, query: str, top_k: int = 12) -> List[ScoredDoc]:
        if not self.docs:
            return []
        qvec = embeddings.embed_query(query)  # normalized (dim,)
        if self._hnsw is not None:
            labels, distances = self._hnsw.knn_query(qvec, k=min(top_k, len(self.docs)))
            out = []
            for idx, dist in zip(labels[0], distances[0]):
                out.append(ScoredDoc(self.docs[int(idx)], float(1.0 - dist), {"dense": float(1.0 - dist)}))
            return out
        # brute-force cosine == dot product (rows already normalized)
        sims = self.matrix @ qvec
        order = np.argsort(-sims)[:top_k]
        return [ScoredDoc(self.docs[int(i)], float(sims[int(i)]), {"dense": float(sims[int(i)])}) for i in order]
