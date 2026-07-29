"""
F-04 — Investment Alert Service
──────────────────────────────────────────────────────────────────────────────
Runs on PM2 cron every 4 hours (offset 30 min from F-03).
For every WatchlistItem with investment_threshold set:
  1. Fetch insider BUY trades (Form 4 via yfinance)
  2. Fetch institutional holders (13F via yfinance)
  3. Filter by item's threshold
  4. Deduplicate via investment_alert_seen table
  5. Write AlertEvent (kind='investment_alert')
  6. Deliver personalised email/SMS to item.notify_email / item.notify_phone
"""
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.monitor import AlertEvent, InvestmentAlertSeen, WatchlistItem
from app.connectors.gov_trading_connector import get_insider_trades_for_ticker
from app.connectors.institutional_tracker import get_new_institutional_positions
from app.services.sendgrid_client import sendgrid_client
from app.services.twilio_client import twilio_client

log = logging.getLogger(__name__)


def _already_seen(db: Session, item_id: int, ticker: str,
                  investor_name: str, trade_date: str) -> bool:
    """7-day dedup check against investment_alert_seen."""
    cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
    try:
        # Ensure table exists before querying
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS investment_alert_seen (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                watchlist_item_id INTEGER NOT NULL,
                investor_name VARCHAR NOT NULL,
                ticker VARCHAR NOT NULL,
                txn_type VARCHAR NOT NULL,
                value_usd FLOAT,
                trade_date VARCHAR NOT NULL,
                alerted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.commit()
        row = db.execute(text("""
            SELECT id FROM investment_alert_seen
            WHERE watchlist_item_id = :item_id
              AND ticker = :ticker
              AND investor_name = :investor_name
              AND trade_date = :trade_date
              AND alerted_at > :cutoff
            LIMIT 1
        """), {
            "item_id": item_id, "ticker": ticker,
            "investor_name": investor_name, "trade_date": trade_date,
            "cutoff": cutoff,
        }).fetchone()
        return row is not None
    except Exception as e:
        log.warning("_already_seen check error: %s", e)
        return False


def _log_seen(db: Session, item_id: int, trade: dict):
    """Write a dedup record after alerting."""
    try:
        db.execute(text("""
            INSERT INTO investment_alert_seen
              (watchlist_item_id, investor_name, ticker, txn_type, value_usd, trade_date)
            VALUES (:item_id, :investor_name, :ticker, :txn_type, :value_usd, :trade_date)
        """), {
            "item_id": item_id,
            "investor_name": trade.get("investor_name", ""),
            "ticker": trade.get("ticker", ""),
            "txn_type": trade.get("transaction", ""),
            "value_usd": trade.get("value_usd", 0),
            "trade_date": trade.get("date", ""),
        })
        db.commit()
    except Exception as e:
        log.warning("_log_seen write error: %s", e)


def _send_for_item(item: WatchlistItem, trades: list):
    """Send personalised email + SMS to the user who set this watchlist alert."""
    ticker = (item.ticker or "").upper()
    sent = {"email": 0, "sms": 0}

    # ── Email ──────────────────────────────────────────────────────────────────
    if item.notify_email and sendgrid_client.is_configured():
        subject = (
            f"📈 Investment Alert — {ticker}: "
            f"{trades[0].get('investor_name','someone')} invested "
            f"${int(trades[0].get('value_usd',0)):,}"
        )
        rows_html = "".join(
            f"""<tr>
              <td>{t.get('ticker','')}</td>
              <td>{t.get('investor_name','')}</td>
              <td>{t.get('investor_type','').capitalize()}</td>
              <td>{t.get('transaction','')}</td>
              <td>${int(t.get('value_usd',0)):,}</td>
              <td>{t.get('date','')}</td>
            </tr>"""
            for t in trades
        )
        body_html = f"""
        <html><body style="font-family:sans-serif;max-width:700px">
        <h2 style="color:#1976d2">📈 New Investment Detected — {ticker}</h2>
        <p><strong>Your threshold:</strong> ${int(item.investment_threshold or 0):,}</p>
        <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%">
          <thead style="background:#f5f5f5">
            <tr><th>Ticker</th><th>Investor</th><th>Type</th><th>Txn</th><th>Amount</th><th>Date</th></tr>
          </thead>
          <tbody>{rows_html}</tbody>
        </table>
        <p style="color:#888;font-size:12px">Source: SEC Form 4 / 13F filings via yfinance.
           <a href="http://localhost:3003/tracking">Manage My Alerts →</a></p>
        </body></html>"""
        result = sendgrid_client.send_email(item.notify_email, subject, body_html)
        if result.get("success"):
            sent["email"] += 1
        else:
            log.warning("SendGrid error for item %d: %s", item.id, result.get("error"))

    # ── SMS ────────────────────────────────────────────────────────────────────
    if item.notify_phone and twilio_client.is_configured():
        first = trades[0]
        sms_body = (
            f"📈 Investment Alert: {ticker} — "
            f"{first.get('investor_name','?')} ({first.get('investor_type','?')}) "
            f"bought ${int(first.get('value_usd',0)):,} on {first.get('date','?')}. "
            f"Your threshold: ${int(item.investment_threshold or 0):,}."
        )
        result = twilio_client.send_sms(item.notify_phone, sms_body[:160])
        if "error" not in result:
            sent["sms"] += 1
        else:
            log.warning("Twilio error for item %d: %s", item.id, result.get("error"))

    return sent


def run_scan_for_item(db: Session, item: WatchlistItem, dry_run: bool = False) -> dict:
    """Run the investment alert scan for one WatchlistItem."""
    ticker = (item.ticker or "").upper()
    threshold = float(item.investment_threshold or 0)

    # Source A: Insider BUY trades (Form 4)
    insider_trades_raw = get_insider_trades_for_ticker(ticker, days=30)
    insider_buys = []
    for t in insider_trades_raw:
        txn = (t.get("transaction") or "").lower()
        value = float(t.get("value_usd") or 0)
        if item.alert_on_buy and "buy" in txn and value >= threshold:
            insider_buys.append({
                "ticker": ticker,
                "investor_name": t.get("insider", "Unknown"),
                "investor_type": "insider",
                "transaction": "Buy",
                "shares": t.get("shares", 0),
                "value_usd": value,
                "date": t.get("date", ""),
                "source": "SEC Form 4 via yfinance",
            })
        elif item.alert_on_sell and "sale" in txn and value >= threshold:
            insider_buys.append({
                "ticker": ticker,
                "investor_name": t.get("insider", "Unknown"),
                "investor_type": "insider",
                "transaction": "Sale",
                "shares": t.get("shares", 0),
                "value_usd": value,
                "date": t.get("date", ""),
                "source": "SEC Form 4 via yfinance",
            })

    # Source B: Institutional positions (13F)
    institutional = []
    if item.alert_on_buy:
        institutional = get_new_institutional_positions(ticker, threshold=threshold)

    all_investments = insider_buys + institutional
    new_alerts = []
    skipped = 0

    for inv in all_investments:
        if _already_seen(db, item.id, ticker, inv["investor_name"], inv["date"]):
            skipped += 1
            continue
        new_alerts.append(inv)

    notifications_sent = {"email": 0, "sms": 0}
    if not dry_run and new_alerts:
        # Ensure default rule exists for FK
        default_rule_id = _ensure_default_investment_rule(db)

        for inv in new_alerts:
            event = AlertEvent(
                rule_id=default_rule_id,
                ticker=ticker,
                kind="investment_alert",
                payload={
                    **inv,
                    "user_threshold": threshold,
                    "watchlist_item_id": item.id,
                },
                delivered=False,
            )
            db.add(event)
            _log_seen(db, item.id, inv)

        try:
            db.commit()
        except Exception as e:
            log.error("DB commit error for item %d: %s", item.id, e)
            db.rollback()

        notifications_sent = _send_for_item(item, new_alerts)

    return {
        "watchlist_item_id": item.id,
        "ticker": ticker,
        "threshold": threshold,
        "investments_found": len(all_investments),
        "already_alerted": skipped,
        "new_alerts_created": len(new_alerts) if not dry_run else 0,
        "notifications_sent": notifications_sent,
        "alerts": new_alerts,
        "dry_run": dry_run,
    }


def run_scan(db: Session, ticker_filter: str = None, dry_run: bool = False) -> dict:
    """
    Scan all watchlist items with investment_threshold set.
    Optionally filter by a single ticker.
    Called by the PM2 cron script.
    """
    query = db.query(WatchlistItem).filter(
        WatchlistItem.investment_threshold.isnot(None),
        WatchlistItem.ticker.isnot(None),
    )
    if ticker_filter:
        query = query.filter(WatchlistItem.ticker == ticker_filter.upper())

    items = query.all()
    results = []
    total_new = 0
    total_email = 0
    total_sms = 0

    for item in items:
        try:
            r = run_scan_for_item(db, item, dry_run=dry_run)
            results.append(r)
            total_new += r.get("new_alerts_created", 0)
            total_email += r.get("notifications_sent", {}).get("email", 0)
            total_sms += r.get("notifications_sent", {}).get("sms", 0)
            log.info(
                "F-04 item %d (%s): %d new alerts",
                item.id, item.ticker, r["new_alerts_created"],
            )
        except Exception as e:
            log.error("Error scanning item %d (%s): %s", item.id, item.ticker, e)
            results.append({"watchlist_item_id": item.id, "error": str(e)})

    return {
        "scanned_items": len(items),
        "new_alerts_created": total_new,
        "notifications_sent": {"email": total_email, "sms": total_sms, "inapp": total_new},
        "results": results,
        "dry_run": dry_run,
    }


def _ensure_default_investment_rule(db: Session) -> int:
    """Seed (or fetch) the default investment_alert AlertRule. Returns its id."""
    from app.models.monitor import AlertRule
    rule = db.query(AlertRule).filter(AlertRule.kind == "investment_alert").first()
    if not rule:
        rule = AlertRule(
            name="Watchlist Investment Alerts",
            kind="investment_alert",
            params={},
            enabled=True,
        )
        db.add(rule)
        try:
            db.commit()
        except Exception:
            db.rollback()
            rule = db.query(AlertRule).filter(AlertRule.kind == "investment_alert").first()
    return rule.id
