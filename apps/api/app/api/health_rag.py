"""
RAG ops endpoints — readiness + metrics for the retrieval pipeline.

GET /health/rag  → which backends are active (pgvector vs cached memory), whether
the reranker/NLI models are warm, embedding provider, and a live metrics snapshot
(latency percentiles, fallback rate, guardrail blocks). This is the ops-facing
counterpart to the dev-facing per-request ?debug trace.
"""
from __future__ import annotations

import os
from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/rag")
def rag_health():
    info = {"status": "ok", "components": {}}

    # Embeddings provider / dim.
    try:
        from app.services.rag import embeddings as _emb
        info["components"]["embeddings"] = {
            "provider": getattr(_emb, "provider_name", lambda: "unknown")(),
            "dim": _emb.model_dim(),
        }
    except Exception as exc:
        info["components"]["embeddings"] = {"error": str(exc)}

    # Vector backend.
    try:
        from app.services.rag.index import get_manager
        pg = get_manager().pg_available()
        info["components"]["vector_backend"] = "pgvector" if pg else "memory-cached"
    except Exception as exc:
        info["components"]["vector_backend"] = f"error: {exc}"

    # Reranker warm state.
    try:
        from app.services.rag import rerank
        info["components"]["reranker"] = {
            "active": rerank.is_active(),
            "model": os.getenv("RAG_RERANK_MODEL", "BAAI/bge-reranker-base"),
        }
    except Exception as exc:
        info["components"]["reranker"] = {"error": str(exc)}

    # Metrics snapshot.
    try:
        from app.services.rag import metrics
        info["metrics"] = metrics.snapshot()
    except Exception as exc:
        info["metrics"] = {"error": str(exc)}

    return info
