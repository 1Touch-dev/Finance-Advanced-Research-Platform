"""
Freshness Engine API
Band A Priority #7: Scheduled re-generation of stale pages
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.session import get_db
import uuid

router = APIRouter(prefix="/freshness", tags=["freshness"])


# ─── Models ─────────────────────────────────────────────────────────────────

class PageFreshness(BaseModel):
    url: str
    page_type: str
    last_generated: str
    last_data_update: str
    staleness_hours: float
    needs_refresh: bool
    priority: int  # 1-10, higher = more urgent


class RefreshJob(BaseModel):
    job_id: str
    url: str
    status: str  # queued, running, completed, failed
    queued_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    error: Optional[str]


class FreshnessConfig(BaseModel):
    page_type: str
    max_age_hours: int
    refresh_priority: int


# ─── Configuration ──────────────────────────────────────────────────────────

# How long before each page type is considered stale
FRESHNESS_RULES: Dict[str, dict] = {
    "stock": {"max_age_hours": 1, "priority": 10},  # Market data - very fresh
    "company": {"max_age_hours": 24, "priority": 7},  # Company info - daily
    "intelligence": {"max_age_hours": 6, "priority": 8},  # Reports - 6 hours
    "institutional": {"max_age_hours": 1080, "priority": 4},  # 13F - SEC filings can lag up to 45 days
    "gov-trading": {"max_age_hours": 24, "priority": 6},  # Gov trading - daily
    "crypto": {"max_age_hours": 1, "priority": 9},  # Crypto - very fresh
    "economics": {"max_age_hours": 24, "priority": 5},  # Economic data - daily
    "static": {"max_age_hours": 720, "priority": 1},  # Static pages - monthly
}


# ─── In-Memory Storage ──────────────────────────────────────────────────────

_page_freshness: Dict[str, dict] = {}
_refresh_queue: List[dict] = []
_refresh_history: List[dict] = []


# ─── Helper Functions ───────────────────────────────────────────────────────

def _calculate_staleness(last_generated: datetime, page_type: str) -> tuple:
    """Calculate how stale a page is and if it needs refresh."""
    now = datetime.utcnow()
    age_hours = (now - last_generated).total_seconds() / 3600

    rule = FRESHNESS_RULES.get(page_type, FRESHNESS_RULES["static"])
    max_age = rule["max_age_hours"]
    needs_refresh = age_hours > max_age

    return age_hours, needs_refresh, rule["priority"]


def _regenerate_page(url: str, page_type: str) -> bool:
    """
    Trigger page regeneration.

    No regeneration pipeline is wired here yet. Return false rather than
    reporting fake success.
    """
    return False


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.get("/status")
def get_freshness_status():
    """Get overall freshness status of the platform."""
    now = datetime.utcnow()

    stats = {
        "total_pages": len(_page_freshness),
        "stale_pages": 0,
        "fresh_pages": 0,
        "pending_refresh": len([j for j in _refresh_queue if j["status"] == "queued"]),
        "by_type": {},
    }

    for url, page in _page_freshness.items():
        page_type = page.get("page_type", "static")
        last_gen = datetime.fromisoformat(page["last_generated"])
        _, needs_refresh, _ = _calculate_staleness(last_gen, page_type)

        if needs_refresh:
            stats["stale_pages"] += 1
        else:
            stats["fresh_pages"] += 1

        if page_type not in stats["by_type"]:
            stats["by_type"][page_type] = {"total": 0, "stale": 0}
        stats["by_type"][page_type]["total"] += 1
        if needs_refresh:
            stats["by_type"][page_type]["stale"] += 1

    return stats


@router.post("/register")
def register_page(url: str, page_type: str, last_generated: Optional[str] = None):
    """Register a page for freshness tracking."""
    now = datetime.utcnow().isoformat()

    _page_freshness[url] = {
        "url": url,
        "page_type": page_type,
        "last_generated": last_generated or now,
        "last_data_update": now,
        "registered_at": now,
    }

    return {"registered": True, "url": url}


@router.get("/check")
def check_page_freshness(url: str):
    """Check freshness status of a specific page."""
    page = _page_freshness.get(url)
    if not page:
        raise HTTPException(404, "Page not registered")

    last_gen = datetime.fromisoformat(page["last_generated"])
    staleness, needs_refresh, priority = _calculate_staleness(last_gen, page["page_type"])

    return PageFreshness(
        url=url,
        page_type=page["page_type"],
        last_generated=page["last_generated"],
        last_data_update=page["last_data_update"],
        staleness_hours=round(staleness, 2),
        needs_refresh=needs_refresh,
        priority=priority if needs_refresh else 0,
    )


@router.get("/stale")
def list_stale_pages(limit: int = 50):
    """List all pages that need refresh, sorted by priority."""
    stale = []

    for url, page in _page_freshness.items():
        last_gen = datetime.fromisoformat(page["last_generated"])
        staleness, needs_refresh, priority = _calculate_staleness(last_gen, page["page_type"])

        if needs_refresh:
            stale.append({
                "url": url,
                "page_type": page["page_type"],
                "staleness_hours": round(staleness, 2),
                "priority": priority,
            })

    # Sort by priority (desc), then staleness (desc)
    stale.sort(key=lambda x: (-x["priority"], -x["staleness_hours"]))

    return {"stale_pages": stale[:limit], "total": len(stale)}


@router.post("/refresh")
def queue_refresh(url: str, background_tasks: BackgroundTasks):
    """Queue a page for refresh."""
    page = _page_freshness.get(url)
    if not page:
        raise HTTPException(404, "Page not registered")

    # Check if already queued
    if any(j["url"] == url and j["status"] == "queued" for j in _refresh_queue):
        return {"queued": False, "reason": "Already in queue"}

    job_id = f"refresh-{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow().isoformat()

    job = {
        "job_id": job_id,
        "url": url,
        "page_type": page["page_type"],
        "status": "queued",
        "queued_at": now,
        "started_at": None,
        "completed_at": None,
        "error": None,
    }

    _refresh_queue.append(job)

    # Add background task to process refresh
    background_tasks.add_task(_process_refresh_job, job_id)

    return {"queued": True, "job_id": job_id}


@router.post("/refresh-stale")
def refresh_all_stale(background_tasks: BackgroundTasks, max_jobs: int = 10):
    """Queue all stale pages for refresh."""
    stale_result = list_stale_pages(limit=max_jobs)
    queued = []

    for page in stale_result["stale_pages"]:
        # Check if already queued
        if not any(j["url"] == page["url"] and j["status"] == "queued" for j in _refresh_queue):
            job_id = f"refresh-{uuid.uuid4().hex[:8]}"
            now = datetime.utcnow().isoformat()

            job = {
                "job_id": job_id,
                "url": page["url"],
                "page_type": page["page_type"],
                "status": "queued",
                "queued_at": now,
                "started_at": None,
                "completed_at": None,
                "error": None,
            }

            _refresh_queue.append(job)
            background_tasks.add_task(_process_refresh_job, job_id)
            queued.append(job_id)

    return {"queued_count": len(queued), "job_ids": queued}


def _process_refresh_job(job_id: str):
    """Background task to process a refresh job."""
    job = next((j for j in _refresh_queue if j["job_id"] == job_id), None)
    if not job:
        return

    job["status"] = "running"
    job["started_at"] = datetime.utcnow().isoformat()

    try:
        success = _regenerate_page(job["url"], job["page_type"])

        if success:
            job["status"] = "completed"
            # Update freshness tracking
            if job["url"] in _page_freshness:
                _page_freshness[job["url"]]["last_generated"] = datetime.utcnow().isoformat()
        else:
            job["status"] = "failed"
            job["error"] = "No regeneration pipeline is configured for this page type"

    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)

    job["completed_at"] = datetime.utcnow().isoformat()
    _refresh_history.append(job.copy())


@router.get("/queue")
def get_refresh_queue():
    """Get current refresh queue status."""
    return {
        "queued": [j for j in _refresh_queue if j["status"] == "queued"],
        "running": [j for j in _refresh_queue if j["status"] == "running"],
        "recent_completed": _refresh_history[-20:],
    }


@router.get("/config")
def get_freshness_config():
    """Get freshness rules configuration."""
    return {"rules": FRESHNESS_RULES}


@router.put("/config/{page_type}")
def update_freshness_config(page_type: str, max_age_hours: int, priority: int = 5):
    """Update freshness rules for a page type."""
    FRESHNESS_RULES[page_type] = {
        "max_age_hours": max_age_hours,
        "priority": min(max(priority, 1), 10),
    }
    return {"updated": True, "page_type": page_type, "config": FRESHNESS_RULES[page_type]}
