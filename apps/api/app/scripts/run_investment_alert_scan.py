"""
F-04 PM2 entry point — invoked by the 'investment-alert-scanner' cron process.
Usage: python -m app.scripts.run_investment_alert_scan [--dry-run] [--ticker AAPL]
"""
import sys
import logging
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [investment-alert-scanner] %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


def main():
    dry_run = "--dry-run" in sys.argv
    ticker_filter = None
    if "--ticker" in sys.argv:
        idx = sys.argv.index("--ticker")
        if idx + 1 < len(sys.argv):
            ticker_filter = sys.argv[idx + 1].upper()

    log.info("Starting F-04 investment scan (dry_run=%s, ticker=%s)", dry_run, ticker_filter)

    from app.db.session import SessionLocal, engine
    from app.models.base import Base
    from app.models.monitor import WatchlistItem, AlertEvent, InvestmentAlertSeen  # noqa
    from app.services.investment_alert_service import run_scan

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        result = run_scan(db, ticker_filter=ticker_filter, dry_run=dry_run)
        log.info(
            "Done. scanned=%d new_alerts=%d email=%d sms=%d dry_run=%s",
            result["scanned_items"],
            result["new_alerts_created"],
            result["notifications_sent"]["email"],
            result["notifications_sent"]["sms"],
            dry_run,
        )
    except Exception as e:
        log.error("Scan failed: %s", e)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
