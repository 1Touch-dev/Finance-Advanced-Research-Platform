"""
Rate-limiting middleware (sliding-window, per-IP).

Two tiers:
  - Default: 100 req/min for read (GET/HEAD/OPTIONS) endpoints
  - Strict:  20 req/min for write (POST/PUT/PATCH/DELETE) endpoints

In-memory — sufficient for a single-replica deployment. Swap for Redis-backed
when horizontally scaling.

Usage in main.py:
    from app.core.rate_limit import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware, requests_per_minute=100)
"""
from __future__ import annotations

import os
import time
import threading
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

_DISABLED = os.getenv("RATE_LIMIT", "on") == "off"
_lock = threading.Lock()
_hits: Dict[str, Deque[float]] = defaultdict(deque)

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
STRICT_MULTIPLIER = 0.2  # write endpoints get 20% of the read limit


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_rate(key: str, limit: int, window: int = 60) -> int | None:
    """Returns None if allowed, or retry-after seconds if blocked."""
    now = time.monotonic()
    with _lock:
        dq = _hits[key]
        cutoff = now - window
        while dq and dq[0] < cutoff:
            dq.popleft()
        if len(dq) >= limit:
            retry = int(window - (now - dq[0])) + 1
            return retry
        dq.append(now)
    return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware enforcing per-IP sliding-window rate limits.

    Args:
        requests_per_minute: limit for read endpoints (GET/HEAD/OPTIONS).
            Write endpoints automatically get requests_per_minute * STRICT_MULTIPLIER.
    """

    def __init__(self, app, requests_per_minute: int = 100):
        super().__init__(app)
        self.read_limit = requests_per_minute
        self.write_limit = max(1, int(requests_per_minute * STRICT_MULTIPLIER))

    async def dispatch(self, request: Request, call_next):
        if _DISABLED:
            return await call_next(request)

        ip = _get_client_ip(request)
        method = request.method.upper()

        if method in WRITE_METHODS:
            limit = self.write_limit
            bucket = f"write:{ip}"
        else:
            limit = self.read_limit
            bucket = f"read:{ip}"

        retry_after = _check_rate(bucket, limit)
        if retry_after is not None:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Rate limit exceeded ({limit}/min). Retry in ~{retry_after}s."
                },
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)


def rate_limiter(bucket: str, limit: int = 30, window: int = 60):
    """Dependency-based rate limiter for individual routes (unchanged from before)."""
    def _dep(request: Request) -> None:
        if _DISABLED:
            return
        ip = _get_client_ip(request)
        key = f"{bucket}:{ip}"
        retry_after = _check_rate(key, limit, window)
        if retry_after is not None:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded ({limit}/{window}s). Retry in ~{retry_after}s.",
                headers={"Retry-After": str(retry_after)},
            )
    return _dep
