"""
Health & ops endpoints — readiness + metrics for the entire platform.

GET /health/live  → Liveness probe  (load balancer / k8s — is the process alive?)
GET /health/ready → Readiness probe (load balancer / k8s — can traffic be sent here?)
GET /health/rag   → RAG pipeline status (embeddings, vector backend, reranker)
GET /health/db    → Database connectivity and pool status
GET /health/redis → Redis connectivity status
GET /health/full  → Combined health check for all components
"""
from __future__ import annotations

import os
import time
from fastapi import APIRouter, Response

router = APIRouter(prefix="/health", tags=["health"])

_START_TIME = time.time()


@router.get("/live", summary="Liveness probe")
def liveness():
    """
    Liveness probe — confirms the process is alive and not deadlocked.
    Load balancers and k8s use this to decide whether to restart the container.
    Returns 200 immediately; no expensive checks.
    """
    return {
        "status": "alive",
        "uptime_seconds": round(time.time() - _START_TIME, 1),
        "version": os.getenv("APP_VERSION", "dev"),
    }


@router.get("/ready", summary="Readiness probe")
def readiness(response: Response):
    """
    Readiness probe — confirms the process can serve traffic.
    Checks DB connectivity (the minimum requirement to handle requests).
    Load balancers use this to route traffic away from unhealthy replicas.
    Returns 200 when ready, 503 when not.
    """
    checks = {}
    healthy = True

    # DB (required)
    try:
        from app.db.session import check_db_health
        db = check_db_health()
        checks["database"] = db.get("status", "unknown")
        if db.get("status") != "ok":
            healthy = False
    except Exception as exc:
        checks["database"] = f"error: {exc}"
        healthy = False

    # Redis (optional — degraded is ok, not fatal)
    try:
        checks["redis"] = _check_redis_fast()
    except Exception:
        checks["redis"] = "unavailable"

    status = "ready" if healthy else "not_ready"
    if not healthy:
        response.status_code = 503

    return {"status": status, "checks": checks}


def _check_redis_fast() -> str:
    """Quick Redis ping — returns 'ok', 'not_configured', or error string."""
    try:
        redis_url = os.getenv("REDIS_URL", "")
        if not redis_url:
            return "not_configured"
        import redis as _redis
        r = _redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
        r.ping()
        return "ok"
    except Exception as exc:
        return f"error: {exc}"


@router.get("/redis", summary="Redis connectivity check")
def redis_health():
    """Check Redis connectivity."""
    import time as _time
    start = _time.monotonic()
    status = _check_redis_fast()
    latency_ms = round((_time.monotonic() - start) * 1000, 1)
    return {
        "status": "ok" if status == "ok" else "degraded",
        "redis": status,
        "latency_ms": latency_ms,
    }


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

    # Redis
    try:
        redis_status = _check_redis_fast()
        result["components"]["redis"] = {
            "status": "ok" if redis_status == "ok" else "degraded",
            "detail": redis_status,
        }
    except Exception as exc:
        result["components"]["redis"] = {"status": "error", "error": str(exc)}

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

    result["uptime_seconds"] = round(time.time() - _START_TIME, 1)
    result["version"] = os.getenv("APP_VERSION", "dev")
    return result
