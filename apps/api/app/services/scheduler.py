"""
Data refresh scheduler.
Runs background jobs to keep external data fresh.

Uses daemon threads with sleep loops — no Redis, no Celery, no APScheduler dependency.
Each job calls the relevant connector and logs success/failure.
The fetched data lands in the connector's module-level cache, so the next API request
sees fresh results without hitting the external source.
"""

import threading
import time
import logging
from datetime import datetime, timezone
from typing import Dict, Optional

log = logging.getLogger(__name__)

# ─── Job Registry ────────────────────────────────────────────────────────────

_job_status: Dict[str, dict] = {}
_lock = threading.Lock()
_started = False


def _update_status(name: str, *, running: bool = False, last_run: Optional[str] = None,
                   last_result: Optional[str] = None, error: Optional[str] = None):
    with _lock:
        entry = _job_status.setdefault(name, {})
        entry["running"] = running
        if last_run:
            entry["last_run"] = last_run
        if last_result is not None:
            entry["last_result"] = last_result
        if error is not None:
            entry["last_error"] = error


def _run_loop(name: str, interval_seconds: int, fn):
    """Generic loop: run fn(), sleep, repeat."""
    _update_status(name, running=True, last_result="pending")
    while True:
        now = datetime.now(timezone.utc).isoformat()
        try:
            fn()
            _update_status(name, last_run=now, last_result="ok", error=None)
            log.info({"event": "scheduler_job_ok", "job": name})
        except Exception as exc:
            _update_status(name, last_run=now, last_result="error", error=str(exc)[:300])
            log.warning({"event": "scheduler_job_error", "job": name, "error": str(exc)[:200]})
        time.sleep(interval_seconds)


# ─── Individual Job Functions ────────────────────────────────────────────────

def _refresh_earnings_calendar():
    from app.connectors.finnhub_earnings_connector import get_upcoming_earnings
    get_upcoming_earnings(days_ahead=14)


def _refresh_short_interest():
    from app.connectors.finra_short_interest_connector import get_most_shorted_stocks
    get_most_shorted_stocks(limit=25)


def _refresh_gov_trading():
    from app.connectors.gov_trading_connector import gov_trading_summary
    gov_trading_summary(days=90)


def _refresh_fred_macro():
    from app.connectors.financial_news_connector import fred_macro_dashboard
    fred_macro_dashboard(limit=5)


def _refresh_global_indices():
    from app.connectors.yfinance_connector import yf_price_history
    indices = ["^GSPC", "^DJI", "^IXIC", "^FTSE", "^N225", "^HSI"]
    for idx in indices:
        try:
            yf_price_history(idx, period="5d", interval="1d")
        except Exception:
            pass


def _refresh_graph_ingestion():
    from app.services.graph_ingestion_service import ingest_entity_full

    KEY_TICKERS = [
        {"name": "Apple Inc.", "cik": "0000320193"},
        {"name": "Microsoft Corporation", "cik": "0000789019"},
        {"name": "NVIDIA Corporation", "cik": "0001045810"},
        {"name": "Alphabet Inc.", "cik": "0001652044"},
        {"name": "Meta Platforms, Inc.", "cik": "0001326801"},
    ]

    total_entities = 0
    total_edges = 0
    errors = []

    for company in KEY_TICKERS:
        try:
            stats = ingest_entity_full(
                entity_name=company["name"],
                cik=company["cik"],
                include_sec=True,
                include_fec=True,
                include_contracts=True,
            )
            total_entities += stats.get("total_entities", 0)
            total_edges += stats.get("total_edges", 0)
            if stats.get("errors"):
                errors.extend(stats["errors"])
        except Exception as exc:
            errors.append(f"{company['name']}: {str(exc)[:200]}")

    log.info({
        "event": "graph_ingestion_complete",
        "entities_found": total_entities,
        "edges_created": total_edges,
        "errors_count": len(errors),
    })
    if errors:
        log.warning({"event": "graph_ingestion_errors", "errors": errors[:10]})


# ─── Schedule Table ──────────────────────────────────────────────────────────

JOBS = [
    {"name": "earnings_calendar", "interval": 3600, "fn": _refresh_earnings_calendar},
    {"name": "short_interest", "interval": 14400, "fn": _refresh_short_interest},
    {"name": "gov_trading", "interval": 21600, "fn": _refresh_gov_trading},
    {"name": "fred_macro", "interval": 3600, "fn": _refresh_fred_macro},
    {"name": "global_indices", "interval": 1800, "fn": _refresh_global_indices},
    {"name": "graph_ingestion", "interval": 43200, "fn": _refresh_graph_ingestion},
]


# ─── Public API ──────────────────────────────────────────────────────────────

def start_scheduler():
    """Launch all background refresh threads. Safe to call multiple times."""
    global _started
    if _started:
        log.info({"event": "scheduler_already_started"})
        return
    _started = True

    for job in JOBS:
        t = threading.Thread(
            target=_run_loop,
            args=(job["name"], job["interval"], job["fn"]),
            name=f"sched-{job['name']}",
            daemon=True,
        )
        t.start()
        log.info({"event": "scheduler_thread_started", "job": job["name"],
                  "interval_s": job["interval"]})


def get_scheduler_status() -> dict:
    """Return current status of all scheduled jobs."""
    with _lock:
        jobs = []
        for job in JOBS:
            info = _job_status.get(job["name"], {})
            last_run = info.get("last_run")
            next_run = None
            if last_run:
                try:
                    lr = datetime.fromisoformat(last_run)
                    next_run = (lr.timestamp() + job["interval"])
                    next_run = datetime.fromtimestamp(next_run, tz=timezone.utc).isoformat()
                except Exception:
                    pass

            jobs.append({
                "name": job["name"],
                "interval_seconds": job["interval"],
                "interval_human": _humanize(job["interval"]),
                "last_run": last_run,
                "next_run_approx": next_run,
                "last_result": info.get("last_result", "not_yet_run"),
                "last_error": info.get("last_error"),
                "running": info.get("running", False),
            })

    return {
        "scheduler_active": _started,
        "jobs": jobs,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def _humanize(seconds: int) -> str:
    if seconds >= 3600:
        h = seconds // 3600
        return f"{h}h"
    return f"{seconds // 60}m"
