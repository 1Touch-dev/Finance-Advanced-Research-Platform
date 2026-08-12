"""
Unified retriever — one interface over any Document collection (report claims or
uploaded doc chunks). Selects the mode, applies reranking + guardrails, records a
trace, and emits ops metrics. Single entry point for rag_chat_service and
document_ingestion_service.

Dense retrieval goes through IndexManager, which reuses a cached/persistent index
per collection instead of rebuilding per query (pgvector on Postgres; cached
in-memory numpy/HNSW on SQLite/dev).

Fallback chain (nothing hard-fails):
  vector/hybrid → embeddings unavailable → keyword (BM25) → TF-IDF
"""
from __future__ import annotations

import logging
import os
import time
from typing import List, Optional

from . import guardrails, hybrid, keyword, metrics, rerank
from .embeddings import EmbeddingUnavailable
from .index import get_manager
from .trace import Trace
from .types import Document, RetrievalMode, ScoredDoc

logger = logging.getLogger(__name__)

# Retrieve a wider candidate pool before reranking down to top_k.
_CANDIDATE_MULT = 4
# Hard upper bound so a caller can't request top_k=1e9 and OOM a slice.
_MAX_TOP_K = int(os.getenv("RAG_MAX_TOP_K", "100"))


def retrieve(
    query: str,
    docs: List[Document],
    *,
    mode: RetrievalMode = RetrievalMode.HYBRID,
    top_k: int = 12,
    use_rerank: bool = True,
    trace: Optional[Trace] = None,
    collection: str = "default",
    correlation_id: Optional[str] = None,
) -> List[ScoredDoc]:
    trace = trace or Trace()
    t0 = time.perf_counter()

    # Input validation / bounds.
    top_k = max(1, min(int(top_k), _MAX_TOP_K))
    trace.stage("input", query_len=len(query or ""), corpus_size=len(docs),
                mode=mode.value, collection=collection)

    if not docs or not (query or "").strip():
        return []

    cand_k = min(top_k * _CANDIDATE_MULT, _MAX_TOP_K * _CANDIDATE_MULT)
    effective_mode = mode
    dense: List[ScoredDoc] = []
    sparse: List[ScoredDoc] = []
    backend = "none"
    fallback = False

    # ── dense side (vector or hybrid) via cached/persistent index ───────────────
    if mode in (RetrievalMode.VECTOR, RetrievalMode.HYBRID):
        try:
            mgr = get_manager()
            if mgr.pg_available():
                store = mgr.get_pg_store(collection)
                backend = "pgvector"
            else:
                store = mgr.get_memory_index(collection, docs)  # cached; no per-query rebuild
                backend = "memory-cached"
            dense = store.search(query, top_k=cand_k)
            trace.stage("dense", hits=len(dense), top=_top(dense), backend=backend)
        except EmbeddingUnavailable as exc:
            logger.info("embeddings unavailable (%s); degrading to keyword", exc)
            trace.stage("dense_fallback", reason=str(exc))
            effective_mode = RetrievalMode.KEYWORD
            fallback = True

    # ── sparse side (keyword or hybrid) ────────────────────────────────────────
    if effective_mode in (RetrievalMode.KEYWORD, RetrievalMode.HYBRID):
        sparse = keyword.keyword_search(query, docs, top_k=cand_k)
        trace.stage("sparse", hits=len(sparse), top=_top(sparse))

    # ── combine ────────────────────────────────────────────────────────────────
    if effective_mode == RetrievalMode.HYBRID and dense and sparse:
        candidates = hybrid.reciprocal_rank_fusion(dense, sparse, top_k=cand_k)
        trace.stage("fusion", method="rrf", hits=len(candidates))
    elif effective_mode == RetrievalMode.VECTOR:
        candidates = dense
    else:
        candidates = sparse or dense

    # ── rerank ───────────────────────────────────────────────────────────────
    rerank_active = False
    if use_rerank and candidates:
        reranked = rerank.rerank(query, candidates, top_k=top_k)
        rerank_active = rerank.is_active()
        trace.stage("rerank", before=len(candidates), after=len(reranked), active=rerank_active)
        candidates = reranked
    else:
        candidates = candidates[:top_k]

    # ── retrieval guardrail ────────────────────────────────────────────────────
    verdict = guardrails.check_retrieval(candidates)
    trace.stage("guardrail_retrieval", ok=verdict.ok, flags=verdict.flags)

    # ── ops metrics (fail-soft) ────────────────────────────────────────────────
    latency_ms = (time.perf_counter() - t0) * 1000
    metrics.record_retrieval(
        mode=mode.value, backend=backend, corpus_size=len(docs), latency_ms=latency_ms,
        top_score=_top(candidates), fallback=fallback, rerank_active=rerank_active,
        guardrail_flags=verdict.flags, query=query or "", correlation_id=correlation_id,
    )

    return candidates


def _top(results: List[ScoredDoc]) -> Optional[float]:
    return round(results[0].score, 4) if results else None
