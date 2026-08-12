"""
Cross-encoder reranking.

Reranks the fused top-N candidates → top-K by scoring (query, doc) pairs jointly,
which is far more precise than bi-encoder cosine. Two tiers, both optional:
  - local cross-encoder (sentence-transformers BAAI/bge-reranker-base), CPU-ok
  - disabled → passthrough (fusion order preserved)

Production notes:
  - Model load is guarded by a lock + cached singleton (thread-safe; no N-way
    construction under concurrent first requests). Call preload() at startup.
  - rerank() does NOT mutate the input ScoredDocs — it returns fresh objects, so
    a cached/shared index's docs are never corrupted across requests.
  - Fails soft: any import/runtime error returns the input order unchanged.
"""
from __future__ import annotations

import logging
import os
import threading
from typing import List, Optional

from .types import ScoredDoc

logger = logging.getLogger(__name__)

_ENABLED = os.getenv("RAG_RERANK", "auto")  # auto | on | off
_MODEL = os.getenv("RAG_RERANK_MODEL", "BAAI/bge-reranker-base")

_model = None
_loaded = False
_lock = threading.Lock()


def _load_cross_encoder():
    """Thread-safe, load-once. Returns the model or None (passthrough)."""
    global _model, _loaded
    if _loaded:
        return _model
    with _lock:
        if _loaded:
            return _model
        _loaded = True
        if _ENABLED == "off":
            _model = None
            return None
        try:
            from sentence_transformers import CrossEncoder
        except ImportError:
            if _ENABLED == "on":
                logger.warning("RAG_RERANK=on but sentence-transformers not installed; passthrough")
            _model = None
            return None
        try:
            _model = CrossEncoder(_MODEL)
        except Exception as exc:
            logger.warning("reranker load failed (%s); passthrough", exc)
            _model = None
    return _model


def preload() -> bool:
    """Warm the model at startup. Returns True if a reranker is active."""
    return _load_cross_encoder() is not None


def is_active() -> bool:
    return _load_cross_encoder() is not None


def rerank(query: str, candidates: List[ScoredDoc], top_k: int = 12) -> List[ScoredDoc]:
    if not candidates:
        return []
    model = _load_cross_encoder()
    if model is None:
        return candidates[:top_k]
    try:
        pairs = [(query, c.doc.text) for c in candidates]
        scores = model.predict(pairs)
        # Do NOT mutate inputs — emit fresh ScoredDocs so shared/cached index
        # objects keep their original dense/bm25 scores.
        rescored = [
            ScoredDoc(c.doc, float(s), {**c.components, "rerank": float(s)})
            for c, s in zip(candidates, scores)
        ]
        rescored.sort(key=lambda c: -c.score)
        return rescored[:top_k]
    except Exception as exc:
        logger.warning("rerank failed (%s); passthrough", exc)
        return candidates[:top_k]
