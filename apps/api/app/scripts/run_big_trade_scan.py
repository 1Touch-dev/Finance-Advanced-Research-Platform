"""
F-03 PM2 entry point — invoked by the 'big-trade-scanner' cron process.
Usage: python -m app.scripts.run_big_trade_scan [--dry-run]
"""
import sys
import logging
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [big-trade-scanner] %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


def main():
    dry_run = "--dry-run" in sys.argv
    log.info("Starting F-03 big-trade scan (dry_run=%s)", dry_run)

    from app.db.session import SessionLocal
    from app.db.session import engine
    from app.models.base import Base
    from app.models.monitor import AlertRule, AlertEvent, WatchlistItem  # noqa: ensure tables exist
    from app.services.big_trade_scanner import run_scan_all_rules

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        result = run_scan_all_rules(db, dry_run=dry_run)
        rules_run = result.get("rules_run", 0)
        total_new = sum(r.get("new_alerts_created", 0) for r in result.get("results", []))
        log.info("Done. rules_run=%d new_alerts=%d dry_run=%s", rules_run, total_new, dry_run)
    except Exception as e:
        log.error("Scan failed: %s", e)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
