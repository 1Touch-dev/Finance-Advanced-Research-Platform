"""
F-03 — Big Trade Scanner Service
──────────────────────────────────────────────────────────────────────────────
Runs on a PM2 cron every 4 hours.
Loads all enabled 'insider_trade' AlertRules, resolves their ticker scope
(watchlist-scoped or global), fetches Form 4 data per ticker, filters by
per-rule threshold, deduplicates, writes AlertEvents, and delivers via
SendGrid + Twilio.
"""
import os
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.monitor import AlertRule, AlertEvent, WatchlistItem
from app.connectors.gov_trading_connector import scan_big_trades
from app.services.sendgrid_client import sendgrid_client
from app.services.twilio_client import twilio_client

log = logging.getLogger(__name__)

DEFAULT_THRESHOLD = float(os.getenv("BIG_TRADE_THRESHOLD", "500000"))
ALERT_RECIPIENT_EMAIL = os.getenv("ALERT_RECIPIENT_EMAIL", "")
ALERT_RECIPIENT_PHONE = os.getenv("ALERT_RECIPIENT_PHONE", "")


def _get_tickers_for_rule(db: Session, rule: AlertRule) -> list:
    """Resolve which tickers to scan for this rule."""
    # Prefer explicit tickers list in rule params
    if rule.params and isinstance(rule.params, dict):
        explicit = rule.params.get("tickers")
        if explicit and isinstance(explicit, list) and len(explicit) > 0:
            return [t.upper() for t in explicit if t]

    # Fall back to watchlist items
    if rule.watchlist_id:
        rows = db.query(WatchlistItem).filter(
            WatchlistItem.watchlist_id == rule.watchlist_id,
            WatchlistItem.ticker.isnot(None),
        ).all()
    else:
        rows = db.query(WatchlistItem).filter(
            WatchlistItem.ticker.isnot(None)
        ).all()
    return list({r.ticker.upper() for r in rows if r.ticker})


def _already_alerted(db: Session, rule_id: int, ticker: str, trade_date: str, insider_name: str) -> bool:
    """Check 7-day dedup window for this rule + trade combo."""
    cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
    try:
        row = db.execute(text("""
            SELECT id FROM alert_events
            WHERE kind = 'insider_trade'
              AND rule_id = :rule_id
              AND ticker = :ticker
              AND JSON_EXTRACT(payload, '$.date') = :trade_date
              AND JSON_EXTRACT(payload, '$.insider_name') = :insider_name
              AND created_at > :cutoff
            LIMIT 1
        """), {
            "rule_id": rule_id,
            "ticker": ticker,
            "trade_date": trade_date,
            "insider_name": insider_name,
            "cutoff": cutoff,
        }).fetchone()
        return row is not None
    except Exception:
        # If query fails (e.g. JSON_EXTRACT not supported), be conservative: don't skip
        return False


def _resolve_threshold(rule: AlertRule) -> float:
    if rule.params and isinstance(rule.params, dict):
        try:
            return float(rule.params.get("threshold", DEFAULT_THRESHOLD))
        except (TypeError, ValueError):
            pass
    return DEFAULT_THRESHOLD


def _send_notifications(trades: list, rule: AlertRule) -> dict:
    """Send email + SMS for a batch of qualifying trades."""
    sent = {"email": 0, "sms": 0}
    if not trades:
        return sent

    # ── Email ──────────────────────────────────────────────────────────────────
    if ALERT_RECIPIENT_EMAIL and sendgrid_client.is_configured():
        subject = f"🚨 Big Trade Alert — {len(trades)} insider trade(s) detected ({rule.name})"
        rows_html = "".join(
            f"""<tr>
              <td>{t.get('ticker','')}</td>
              <td>{t.get('insider','')}</td>
              <td>{t.get('title','')}</td>
              <td>{t.get('transaction','')}</td>
              <td>${int(t.get('value_usd',0)):,}</td>
              <td>{t.get('date','')}</td>
            </tr>"""
            for t in trades
        )
        body_html = f"""
        <html><body style="font-family:sans-serif;max-width:700px">
        <h2 style="color:#d32f2f">🚨 Big Insider Trade Alert</h2>
        <p><strong>Rule:</strong> {rule.name} &nbsp;|&nbsp;
           <strong>Threshold:</strong> ${int(_resolve_threshold(rule)):,}</p>
        <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%">
          <thead style="background:#f5f5f5">
            <tr><th>Ticker</th><th>Insider</th><th>Title</th><th>Txn</th><th>Value</th><th>Date</th></tr>
          </thead>
          <tbody>{rows_html}</tbody>
        </table>
        <p style="color:#888;font-size:12px">Source: SEC Form 4 via yfinance. 
           <a href="http://localhost:3003/gov-trading">View in Platform →</a></p>
        </body></html>"""
        result = sendgrid_client.send_email(ALERT_RECIPIENT_EMAIL, subject, body_html)
        if result.get("success"):
            sent["email"] += 1
        else:
            log.warning("SendGrid error: %s", result.get("error"))

    # ── SMS ────────────────────────────────────────────────────────────────────
    if ALERT_RECIPIENT_PHONE and twilio_client.is_configured():
        first = trades[0]
        sms_body = (
            f"🚨 Big Trade: {first.get('ticker')} — "
            f"{first.get('insider','?')} {first.get('transaction','?')} "
            f"${int(first.get('value_usd',0)):,} on {first.get('date','?')}."
        )
        if len(trades) > 1:
            sms_body += f" (+{len(trades)-1} more)"
        result = twilio_client.send_sms(ALERT_RECIPIENT_PHONE, sms_body[:160])
        if "error" not in result:
            sent["sms"] += 1
        else:
            log.warning("Twilio error: %s", result.get("error"))

    return sent


def run_scan_for_rule(db: Session, rule: AlertRule, dry_run: bool = False) -> dict:
    """Run the big-trade scan for one AlertRule. Returns a summary dict."""
    threshold = _resolve_threshold(rule)
    tickers = _get_tickers_for_rule(db, rule)

    if not tickers:
        return {
            "rule_id": rule.id, "rule_name": rule.name,
            "threshold_used": threshold, "ticker_scope": "empty",
            "scanned_tickers": 0, "trades_found": 0,
            "above_threshold": 0, "already_alerted": 0,
            "new_alerts_created": 0, "notifications_sent": {"email": 0, "sms": 0},
            "alerts": [],
        }

    all_trades = scan_big_trades(
        tickers,
        threshold=threshold,
        days=rule.params.get("lookback_days", 30) if rule.params and isinstance(rule.params, dict) else 30
    )
    new_alerts = []
    skipped = 0

    for trade in all_trades:
        insider_name = trade.get("insider", "") or ""
        trade_date = trade.get("date", "") or ""
        ticker = trade.get("ticker", "") or ""

        if _already_alerted(db, rule.id, ticker, trade_date, insider_name):
            skipped += 1
            continue

        payload = {
            "insider_name": insider_name,
            "title": trade.get("title", ""),
            "transaction": trade.get("transaction", ""),
            "shares": trade.get("shares", 0),
            "value_usd": trade.get("value_usd", 0),
            "date": trade_date,
            "ticker": ticker,
            "threshold_used": threshold,
            "rule_id": rule.id,
            "rule_name": rule.name,
            "source": "SEC Form 4 via yfinance",
        }
        new_alerts.append({"trade": trade, "payload": payload})

    notifications_sent = {"email": 0, "sms": 0}
    if not dry_run and new_alerts:
        # Write AlertEvents
        for item in new_alerts:
            event = AlertEvent(
                rule_id=rule.id,
                ticker=item["trade"].get("ticker"),
                kind="insider_trade",
                payload=item["payload"],
                delivered=False,
            )
            db.add(event)
        db.commit()

        # Deliver in one batch
        notifications_sent = _send_notifications(
            [item["trade"] for item in new_alerts], rule
        )

        # Mark as delivered
        db.execute(text("""
            UPDATE alert_events SET delivered=1
            WHERE kind='insider_trade' AND rule_id=:rule_id AND delivered=0
        """), {"rule_id": rule.id})
        db.commit()

    return {
        "rule_id": rule.id,
        "rule_name": rule.name,
        "threshold_used": threshold,
        "ticker_scope": f"watchlist:{rule.watchlist_id}" if rule.watchlist_id else "global",
        "scanned_tickers": len(tickers),
        "trades_found": len(all_trades),
        "above_threshold": len(all_trades),
        "already_alerted": skipped,
        "new_alerts_created": len(new_alerts) if not dry_run else 0,
        "notifications_sent": notifications_sent,
        "alerts": [item["trade"] for item in new_alerts],
        "dry_run": dry_run,
    }


def run_scan_all_rules(db: Session, dry_run: bool = False) -> dict:
    """
    Load all enabled insider_trade rules and run a scan for each.
    Called by the PM2 cron script.
    """
    # Ensure default rule exists
    _ensure_default_rule(db)

    rules = db.query(AlertRule).filter(
        AlertRule.kind == "insider_trade",
        AlertRule.enabled == True,
    ).all()

    results = []
    for rule in rules:
        try:
            result = run_scan_for_rule(db, rule, dry_run=dry_run)
            results.append(result)
            log.info(
                "F-03 rule %d (%s): %d new alerts, %d skipped",
                rule.id, rule.name,
                result["new_alerts_created"], result["already_alerted"],
            )
        except Exception as e:
            log.error("Error scanning rule %d: %s", rule.id, e)
            results.append({"rule_id": rule.id, "error": str(e)})

    return {"rules_run": len(rules), "results": results, "dry_run": dry_run}


def _ensure_default_rule(db: Session):
    """Seed the default global $500k insider_trade rule if none exists."""
    existing = db.query(AlertRule).filter(AlertRule.kind == "insider_trade").first()
    if not existing:
        rule = AlertRule(
            name="Big Trade Watch",
            kind="insider_trade",
            params={"threshold": DEFAULT_THRESHOLD},
            watchlist_id=None,
            enabled=True,
        )
        db.add(rule)
        try:
            db.commit()
        except Exception:
            db.rollback()
