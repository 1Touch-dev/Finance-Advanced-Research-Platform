"""
Ops-facing observability for the RAG pipeline.

- In-process metrics counters/histograms (no hard dependency on Prometheus; if
  prometheus_client is installed we also register real metrics, else we keep
  lightweight in-memory aggregates exposed via /health/rag).
- A structured per-retrieval log line (query hash — never the raw query — mode,
  corpus size, latency, top score, fallback tier, rerank state, guardrail flags,
  correlation id).

Every helper is fail-soft: metrics must never break a request.
"""
from __future__ import annotations

import hashlib
import logging
import threading
import time
from typing import Dict, Optional

logger = logging.getLogger("rag.metrics")

_lock = threading.Lock()
_counters: Dict[str, float] = {}
_hist: Dict[str, list] = {}

# Optional Prometheus mirror.
try:
    from prometheus_client import Counter, Histogram
    _PROM = True
    _p_requests = Counter("rag_retrievals_total", "RAG retrievals", ["mode", "backend"])
    _p_fallback = Counter("rag_fallback_total", "RAG fallbacks to keyword", [])
    _p_rerank = Counter("rag_rerank_active_total", "RAG rerank applied", [])
    _p_guard = Counter("rag_guardrail_block_total", "RAG guardrail blocks", ["stage"])
    _p_latency = Histogram("rag_retrieval_latency_ms", "RAG retrieval latency (ms)",
                           buckets=(5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000))
except Exception:  # prometheus optional
    _PROM = False


def incr(name: str, value: float = 1.0, **labels) -> None:
    key = name + ("|" + ",".join(f"{k}={v}" for k, v in sorted(labels.items())) if labels else "")
    with _lock:
        _counters[key] = _counters.get(key, 0.0) + value


def observe(name: str, value: float) -> None:
    with _lock:
        _hist.setdefault(name, []).append(value)
        if len(_hist[name]) > 1000:  # cap memory
            _hist[name] = _hist[name][-1000:]


def snapshot() -> Dict:
    with _lock:
        counters = dict(_counters)
        hist = {}
        for k, vals in _hist.items():
            if vals:
                s = sorted(vals)
                hist[k] = {
                    "count": len(s),
                    "p50": s[len(s) // 2],
                    "p95": s[int(len(s) * 0.95)] if len(s) > 1 else s[0],
                    "max": s[-1],
                }
    return {"counters": counters, "histograms": hist, "prometheus": _PROM}


def query_hash(q: str) -> str:
    return hashlib.sha1(q.encode("utf-8", "ignore")).hexdigest()[:12]


def record_retrieval(
    *, mode: str, backend: str, corpus_size: int, latency_ms: float,
    top_score: Optional[float], fallback: bool, rerank_active: bool,
    guardrail_flags: list, query: str, correlation_id: Optional[str] = None,
) -> None:
    """One structured, PII-safe log line + metrics per retrieval."""
    try:
        incr("rag_retrievals_total", mode=mode, backend=backend)
        observe("retrieval_latency_ms", latency_ms)
        if fallback:
            incr("rag_fallback_total")
        if rerank_active:
            incr("rag_rerank_active_total")
        for f in guardrail_flags or []:
            incr("rag_guardrail_block_total", stage=f)
        if _PROM:
            _p_requests.labels(mode=mode, backend=backend).inc()
            _p_latency.observe(latency_ms)
            if fallback:
                _p_fallback.inc()
            if rerank_active:
                _p_rerank.inc()
            for f in guardrail_flags or []:
                _p_guard.labels(stage=f).inc()
        logger.info(
            "rag_retrieval",
            extra={"rag": {
                "cid": correlation_id, "q": query_hash(query), "mode": mode,
                "backend": backend, "corpus": corpus_size, "latency_ms": round(latency_ms, 2),
                "top": top_score, "fallback": fallback, "rerank": rerank_active,
                "guardrail_flags": guardrail_flags,
            }},
        )
    except Exception as exc:  # metrics must never break a request
        logger.debug("metrics record failed: %s", exc)
