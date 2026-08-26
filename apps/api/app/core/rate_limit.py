"""
Rate-limiting middleware — sliding-window, per-IP and per-user.

Two tiers (applied to EVERY request):
  - IP tier:   100 read req/min, 20 write req/min (global anti-abuse)
  - User tier: 300 read req/min, 60 write req/min per authenticated user
               (identified via JWT sub claim — no DB call needed)

Why two tiers?
  - IP limit stops unauthenticated abuse / DDoS.
  - User limit provides fair-use quotas per account regardless of IP
    (important when multiple users share an IP, e.g. office NAT).

In-memory store — sufficient for single-replica. For horizontal scaling,
swap _hits for a Redis-backed sorted-set store.

Usage in main.py:
    from app.core.rate_limit import RateLimitMiddleware
    app.add_middleware(RateLimitMiddleware, requests_per_minute=100)
"""
from __future__ import annotations

import os
import time
import threading
from collections import defaultdict, deque
from typing import Deque, Dict, Optional

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

_DISABLED = os.getenv("RATE_LIMIT", "on") == "off"
_lock = threading.Lock()
_hits: Dict[str, Deque[float]] = defaultdict(deque)

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
STRICT_MULTIPLIER = 0.2      # write endpoints: 20% of read limit
USER_MULTIPLIER   = 3.0      # authenticated users get 3× the IP limit
_HEALTH_PREFIXES  = ("/health", "/metrics", "/docs", "/openapi", "/redoc")


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _extract_user_id(request: Request) -> Optional[str]:
    """Extract user ID from JWT Authorization header (no DB call)."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:]
    try:
        import jwt as _jwt
        from app.core.settings import settings
        payload = _jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            options={"verify_exp": False},  # expiry enforced by auth layer, not here
        )
        return str(payload.get("sub", ""))
    except Exception:
        return None


def _check_rate(key: str, limit: int, window: int = 60) -> Optional[int]:
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
    ASGI middleware enforcing sliding-window rate limits.

    Checks in order:
    1. IP-level limit  (applies to all requests, auth or not)
    2. User-level limit (only when a valid JWT is present; higher allowance)

    A request is rejected if EITHER limit is exceeded.

    Args:
        requests_per_minute: base limit for read endpoints per IP.
            Write endpoints get requests_per_minute * STRICT_MULTIPLIER.
            Authenticated users get requests_per_minute * USER_MULTIPLIER.
    """

    def __init__(self, app, requests_per_minute: int = 100):
        super().__init__(app)
        self.read_limit  = requests_per_minute
        self.write_limit = max(1, int(requests_per_minute * STRICT_MULTIPLIER))
        self.user_read_limit  = max(1, int(requests_per_minute * USER_MULTIPLIER))
        self.user_write_limit = max(1, int(self.user_read_limit * STRICT_MULTIPLIER))

    async def dispatch(self, request: Request, call_next):
        if _DISABLED:
            return await call_next(request)

        # Never rate-limit health / metrics probes
        path = request.url.path
        if any(path.startswith(p) for p in _HEALTH_PREFIXES):
            return await call_next(request)

        ip = _get_client_ip(request)
        method = request.method.upper()
        is_write = method in WRITE_METHODS

        # ── Tier 1: IP-level ────────────────────────────────────────────────
        ip_limit  = self.write_limit if is_write else self.read_limit
        ip_bucket = f"{'w' if is_write else 'r'}:ip:{ip}"
        retry = _check_rate(ip_bucket, ip_limit)
        if retry is not None:
            return JSONResponse(
                status_code=429,
                content={"detail": f"IP rate limit exceeded ({ip_limit}/min). Retry in ~{retry}s."},
                headers={"Retry-After": str(retry), "X-RateLimit-Scope": "ip"},
            )

        # ── Tier 2: User-level (JWT) ─────────────────────────────────────────
        user_id = _extract_user_id(request)
        if user_id:
            user_limit  = self.user_write_limit if is_write else self.user_read_limit
            user_bucket = f"{'w' if is_write else 'r'}:user:{user_id}"
            retry = _check_rate(user_bucket, user_limit)
            if retry is not None:
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": f"User rate limit exceeded ({user_limit}/min). Retry in ~{retry}s."
                    },
                    headers={"Retry-After": str(retry), "X-RateLimit-Scope": "user"},
                )

        return await call_next(request)


def rate_limiter(bucket: str, limit: int = 30, window: int = 60):
    """
    Dependency-based rate limiter for individual routes.
    Uses user ID when authenticated, falls back to IP.
    """
    def _dep(request: Request) -> None:
        if _DISABLED:
            return
        user_id = _extract_user_id(request)
        identifier = f"user:{user_id}" if user_id else f"ip:{_get_client_ip(request)}"
        key = f"{bucket}:{identifier}"
        retry_after = _check_rate(key, limit, window)
        if retry_after is not None:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded ({limit}/{window}s). Retry in ~{retry_after}s.",
                headers={"Retry-After": str(retry_after)},
            )
    return _dep
