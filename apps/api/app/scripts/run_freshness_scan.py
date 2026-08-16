"""
#7 Freshness Engine PM2 entry point — invoked by the 'freshness-scanner' cron process.
Usage: python -m app.scripts.run_freshness_scan [--dry-run] [--max-jobs 10]

Scheduled task that:
1. Checks all registered pages for staleness
2. Queues the most urgent stale pages for refresh
3. Reports on freshness status
"""
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [freshness-scanner] %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


def main():
    dry_run = "--dry-run" in sys.argv
    max_jobs = 10

    if "--max-jobs" in sys.argv:
        idx = sys.argv.index("--max-jobs")
        if idx + 1 < len(sys.argv):
            max_jobs = int(sys.argv[idx + 1])

    log.info("Starting freshness scan (dry_run=%s, max_jobs=%d)", dry_run, max_jobs)

    # Import freshness module
    from app.api.freshness import (
        get_freshness_status,
        list_stale_pages,
        _refresh_queue,
        _page_freshness,
        _process_refresh_job,
        FRESHNESS_RULES,
    )
    import uuid

    # Get current status
    status = get_freshness_status()
    log.info(
        "Current status: total=%d, stale=%d, fresh=%d, pending=%d",
        status["total_pages"],
        status["stale_pages"],
        status["fresh_pages"],
        status["pending_refresh"],
    )

    # List stale pages
    stale_result = list_stale_pages(limit=max_jobs)
    stale_pages = stale_result["stale_pages"]
    total_stale = stale_result["total"]

    log.info("Found %d stale pages (showing top %d)", total_stale, len(stale_pages))

    if not stale_pages:
        log.info("No stale pages found. Exiting.")
        return {"scanned": status["total_pages"], "stale": 0, "refreshed": 0}

    # In dry-run mode, just report what would be refreshed
    if dry_run:
        for page in stale_pages:
            log.info(
                "Would refresh: %s (type=%s, staleness=%.1fh, priority=%d)",
                page["url"],
                page["page_type"],
                page["staleness_hours"],
                page["priority"],
            )
        return {"scanned": status["total_pages"], "stale": total_stale, "refreshed": 0, "dry_run": True}

    # Queue pages for refresh
    refreshed = 0
    for page in stale_pages:
        url = page["url"]

        # Skip if already queued
        if any(j["url"] == url and j["status"] == "queued" for j in _refresh_queue):
            log.info("Already queued: %s", url)
            continue

        # Create job
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
        log.info("Queued refresh: %s (job_id=%s)", url, job_id)

        # Process synchronously (since this is a cron job)
        _process_refresh_job(job_id)
        refreshed += 1

        log.info(
            "Refreshed: %s (status=%s)",
            url,
            next((j["status"] for j in _refresh_queue if j["job_id"] == job_id), "unknown"),
        )

    log.info(
        "Done. scanned=%d, total_stale=%d, refreshed=%d",
        status["total_pages"],
        total_stale,
        refreshed,
    )

    return {"scanned": status["total_pages"], "stale": total_stale, "refreshed": refreshed}


if __name__ == "__main__":
    result = main()
    sys.exit(0 if result.get("refreshed", 0) >= 0 else 1)
