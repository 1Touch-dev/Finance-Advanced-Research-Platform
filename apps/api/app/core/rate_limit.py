"""
Lightweight in-process rate limiter for the cost/CPU-sensitive RAG endpoints
(/chat/ask, /documents/search). No external deps — a per-key sliding-window
counter guarded by a lock. Good enough to stop trivial bill-spike/DoS; swap for
Redis-backed limiting when you run multiple API replicas.

Usage (FastAPI dependency):
    from app.core.rate_limit import rate_limiter
    @router.get(..., dependencies=[Depends(rate_limiter("docs_search", limit=30, window=60))])
"""
from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import HTTPException, Request

_DISABLED = os.getenv("RAG_RATE_LIMIT", "on") == "off"
_lock = threading.Lock()
_hits: Dict[str, Deque[float]] = defaultdict(deque)


def _client_key(request: Request, bucket: str) -> str:
    ip = request.client.host if request.client else "unknown"
    user = request.headers.get("x-user-id") or request.query_params.get("user_id") or ""
    return f"{bucket}:{user or ip}"


def rate_limiter(bucket: str, limit: int = 30, window: int = 60):
    """Return a FastAPI dependency enforcing `limit` requests per `window` seconds."""
    def _dep(request: Request) -> None:
        if _DISABLED:
            return
        key = _client_key(request, bucket)
        now = time.monotonic()
        with _lock:
            dq = _hits[key]
            cutoff = now - window
            while dq and dq[0] < cutoff:
                dq.popleft()
            if len(dq) >= limit:
                retry = int(window - (now - dq[0])) + 1
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded ({limit}/{window}s). Retry in ~{retry}s.",
                    headers={"Retry-After": str(retry)},
                )
            dq.append(now)
    return _dep
