"""
Health & ops endpoints — readiness + metrics for the entire platform.

GET /health/rag  → RAG pipeline status (embeddings, vector backend, reranker)
GET /health/db   → Database connectivity and pool status
GET /health/full → Combined health check for all components
"""
from __future__ import annotations

import os
from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/rag")
def rag_health():
    """RAG pipeline health check."""
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


@router.get("/db")
def db_health():
    """Database connectivity and pool health check."""
    try:
        from app.db.session import check_db_health
        return check_db_health()
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


@router.get("/full")
def full_health():
    """Combined health check for all platform components."""
    result = {
        "status": "ok",
        "components": {},
    }

    # Database
    try:
        from app.db.session import check_db_health
        db_result = check_db_health()
        result["components"]["database"] = db_result
        if db_result.get("status") != "ok":
            result["status"] = "degraded"
    except Exception as exc:
        result["components"]["database"] = {"status": "error", "error": str(exc)}
        result["status"] = "degraded"

    # RAG pipeline
    try:
        rag_result = rag_health()
        result["components"]["rag"] = rag_result
    except Exception as exc:
        result["components"]["rag"] = {"status": "error", "error": str(exc)}
        result["status"] = "degraded"

    # Quality classifier
    try:
        from app.services.quality.classifier import get_classifier
        clf = get_classifier()
        if clf:
            result["components"]["quality_classifier"] = {
                "status": "ok",
                "version": clf.version,
                "metrics": clf.metrics.get("test_f1", "unknown") if clf.metrics else "unknown",
            }
        else:
            result["components"]["quality_classifier"] = {"status": "not_trained"}
    except Exception as exc:
        result["components"]["quality_classifier"] = {"status": "error", "error": str(exc)}

    return result
