"""
APM tracing utilities — Sentry Performance custom spans.

Usage:
    from app.core.tracing import trace_op

    with trace_op("sec.edgar.fetch", description="Fetch SEC filings for AAPL"):
        result = _fetch_sec("Apple Inc", "AAPL")

    # Or as a decorator:
    @trace_op.decorator("intelligence.generate")
    def generate_report(entity_name: str):
        ...
"""
from __future__ import annotations

import functools
import time
from contextlib import contextmanager
from typing import Optional

try:
    import sentry_sdk as _sentry
    _SENTRY_AVAILABLE = True
except ImportError:
    _SENTRY_AVAILABLE = False


@contextmanager
def trace_op(
    op: str,
    description: Optional[str] = None,
    data: Optional[dict] = None,
):
    """
    Context manager that wraps a block in a Sentry performance span.
    Falls back to a no-op timer if Sentry is not configured.

    Args:
        op: Sentry operation name (e.g. "sec.edgar.fetch", "cache.miss")
        description: Human-readable description shown in Sentry trace view
        data: Extra key/value data attached to the span
    """
    start = time.perf_counter()

    if _SENTRY_AVAILABLE:
        with _sentry.start_span(op=op, description=description or op) as span:
            if data:
                for k, v in data.items():
                    span.set_data(k, v)
            try:
                yield span
            finally:
                elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
                span.set_data("elapsed_ms", elapsed_ms)
    else:
        yield None


def trace(op: str, description: Optional[str] = None):
    """
    Decorator version of trace_op.

    Usage:
        @trace("intelligence.generate_report")
        def generate_report(entity_name):
            ...
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            with trace_op(op, description or fn.__qualname__):
                return fn(*args, **kwargs)
        return wrapper
    return decorator


def set_user_context(user_id: str, email: Optional[str] = None) -> None:
    """Attach user info to the current Sentry scope (call from auth middleware)."""
    if _SENTRY_AVAILABLE:
        _sentry.set_user({"id": user_id, "email": email})


def set_tag(key: str, value: str) -> None:
    """Set a searchable tag on the current Sentry event."""
    if _SENTRY_AVAILABLE:
        _sentry.set_tag(key, value)
