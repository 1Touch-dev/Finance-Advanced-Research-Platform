"""
Tracking & Watchlist service — monitor entities for changes over time.

Features:
  1. Watchlist CRUD           — add/remove entities to watch
  2. Change detection         — compare new vs cached report data for an entity
  3. Daily digest worker      — runs at 6 AM UTC, sends email (SendGrid) + SMS (Twilio)
  4. Notification preferences — per-user settings (email, SMS, frequency)

Tables used (created here if missing):
  - tracked_entities  : { id, entity_name, entity_type, added_by, created_at, last_checked, last_digest }
  - entity_snapshots  : { id, entity_name, snapshot_json, created_at }
  - digest_logs       : { id, sent_at, recipient, channel, status, entity_count }
"""
import os
import json
import logging
import requests
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

_SENDGRID_KEY   = os.getenv("SENDGRID_API_KEY", "")
_TWILIO_SID     = os.getenv("TWILIO_ACCOUNT_SID", "")
_TWILIO_TOKEN   = os.getenv("TWILIO_AUTH_TOKEN", "")
_TWILIO_FROM    = os.getenv("TWILIO_PHONE_NUMBER", "")
_DIGEST_EMAIL   = os.getenv("DIGEST_RECIPIENT_EMAIL", "")
_DIGEST_PHONE   = os.getenv("DIGEST_RECIPIENT_PHONE", "")


# ── DB helpers ─────────────────────────────────────────────────────────────────

def _ensure_tables(db: Session):
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS tracked_entities (
            id          SERIAL PRIMARY KEY,
            entity_name VARCHAR(500) NOT NULL,
            entity_type VARCHAR(50)  NOT NULL DEFAULT 'org',
            added_by    VARCHAR(200),
            created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
            last_checked TIMESTAMPTZ,
            last_digest TIMESTAMPTZ,
            notes       TEXT,
            UNIQUE(entity_name)
        )
    """))
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS entity_snapshots (
            id           SERIAL PRIMARY KEY,
            entity_name  VARCHAR(500) NOT NULL,
            snapshot_json JSONB,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """))
    db.execute(text("""
        CREATE TABLE IF NOT EXISTS digest_logs (
            id           SERIAL PRIMARY KEY,
            sent_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            recipient    VARCHAR(500),
            channel      VARCHAR(50),
            status       VARCHAR(50),
            entity_count INT DEFAULT 0,
            detail       TEXT
        )
    """))
    db.commit()


# ── Watchlist CRUD ─────────────────────────────────────────────────────────────

def add_to_watchlist(db: Session, entity_name: str, entity_type: str = 'org', added_by: str = '', notes: str = '') -> dict:
    _ensure_tables(db)
    try:
        db.execute(text("""
            INSERT INTO tracked_entities (entity_name, entity_type, added_by, notes)
            VALUES (:name, :type, :by, :notes)
            ON CONFLICT (entity_name) DO UPDATE SET notes = EXCLUDED.notes
        """), {"name": entity_name, "type": entity_type, "by": added_by, "notes": notes})
        db.commit()
        return {"ok": True, "entity_name": entity_name, "action": "added"}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}


def remove_from_watchlist(db: Session, entity_name: str) -> dict:
    _ensure_tables(db)
    try:
        result = db.execute(text("DELETE FROM tracked_entities WHERE entity_name = :name"), {"name": entity_name})
        db.commit()
        return {"ok": True, "entity_name": entity_name, "deleted": result.rowcount > 0}
    except Exception as e:
        db.rollback()
        return {"ok": False, "error": str(e)}


def list_watchlist(db: Session) -> List[dict]:
    _ensure_tables(db)
    rows = db.execute(text("""
        SELECT id, entity_name, entity_type, added_by, created_at, last_checked, last_digest, notes
        FROM tracked_entities
        ORDER BY created_at DESC
    """)).fetchall()
    return [dict(r._mapping) for r in rows]


# ── Snapshot & change detection ───────────────────────────────────────────────

def save_snapshot(db: Session, entity_name: str, report: dict):
    _ensure_tables(db)
    snapshot = {
        "summary":   report.get("summary", {}),
        "sections":  [{"name": s.get("name"), "claim_count": len(s.get("claims", []))}
                       for s in (report.get("sections") or [])],
        "entity_id": report.get("entity_id"),
        "ts":        datetime.now(timezone.utc).isoformat(),
    }
    db.execute(text("""
        INSERT INTO entity_snapshots (entity_name, snapshot_json)
        VALUES (:name, :snap::jsonb)
    """), {"name": entity_name, "snap": json.dumps(snapshot)})
    db.commit()


def detect_changes(db: Session, entity_name: str, new_report: dict) -> List[str]:
    """
    Compare new report against the last snapshot.
    Returns a list of human-readable change descriptions.
    """
    _ensure_tables(db)
    row = db.execute(text("""
        SELECT snapshot_json FROM entity_snapshots
        WHERE entity_name = :name
        ORDER BY created_at DESC LIMIT 1
    """), {"name": entity_name}).fetchone()

    if not row:
        return [f"First snapshot recorded for {entity_name}."]

    prev = row[0] if isinstance(row[0], dict) else json.loads(row[0])
    changes = []

    new_summary  = new_report.get("summary", {})
    prev_summary = prev.get("summary", {})

    # Detect KPI changes
    checks = [
        ("total_obligated_usd",   "government contract value",    1_000_000),
        ("lobbying_filings",      "lobbying filings",             0),
        ("court_cases",           "court cases",                  0),
        ("sec_filings",           "SEC filings",                  0),
        ("relationships_written", "relationships mapped",         5),
        ("news_articles",         "news articles",                0),
    ]
    for key, label, threshold in checks:
        old_val = prev_summary.get(key, 0) or 0
        new_val = new_summary.get(key, 0)  or 0
        delta   = new_val - old_val
        if abs(delta) > threshold:
            direction = "increased" if delta > 0 else "decreased"
            if key == "total_obligated_usd":
                changes.append(f"📈 Contract value {direction} by ${abs(delta)/1e6:.1f}M (now ${new_val/1e6:.1f}M).")
            else:
                changes.append(f"{'🔺' if delta > 0 else '🔻'} {label.title()} {direction} by {abs(delta)} (now {new_val}).")

    # Risk flag changes
    for risk_key, label in [("kpi_court_risk", "court risk"), ("kpi_sanctions_risk", "sanctions risk")]:
        old_r = str(prev_summary.get(risk_key, "LOW")).upper()
        new_r = str(new_summary.get(risk_key, "LOW")).upper()
        if old_r != new_r:
            changes.append(f"⚠️  {label.title()} changed: {old_r} → {new_r}.")

    return changes if changes else ["No significant changes detected."]


# ── Notification senders ──────────────────────────────────────────────────────

def send_email_digest(subject: str, html_body: str, recipient: str) -> bool:
    if not _SENDGRID_KEY or not recipient:
        logger.warning("SendGrid not configured — skipping email digest")
        return False
    try:
        resp = requests.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {_SENDGRID_KEY}", "Content-Type": "application/json"},
            json={
                "personalizations": [{"to": [{"email": recipient}]}],
                "from":             {"email": "noreply@intelligenceplatform.ai", "name": "Intelligence Platform"},
                "subject":          subject,
                "content":          [{"type": "text/html", "value": html_body}],
            },
            timeout=15,
        )
        return resp.status_code in (200, 202)
    except Exception as e:
        logger.warning("SendGrid error: %s", e)
        return False


def send_sms_digest(message: str, phone: str) -> bool:
    if not all([_TWILIO_SID, _TWILIO_TOKEN, _TWILIO_FROM, phone]):
        logger.warning("Twilio not configured — skipping SMS digest")
        return False
    try:
        resp = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{_TWILIO_SID}/Messages.json",
            auth=(_TWILIO_SID, _TWILIO_TOKEN),
            data={"Body": message[:1600], "From": _TWILIO_FROM, "To": phone},
            timeout=15,
        )
        return resp.status_code in (200, 201)
    except Exception as e:
        logger.warning("Twilio error: %s", e)
        return False


# ── Daily digest orchestrator ─────────────────────────────────────────────────

def _build_digest_html(entity_changes: Dict[str, List[str]]) -> str:
    rows = ""
    for entity, changes in entity_changes.items():
        items = "".join(f"<li>{c}</li>" for c in changes)
        rows += f"""
        <tr>
          <td style="padding:8px 12px;font-weight:700;color:#818cf8;vertical-align:top">{entity}</td>
          <td style="padding:8px 12px;color:#e2e8f0"><ul style="margin:0;padding-left:1rem">{items}</ul></td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html><body style="font-family:sans-serif;background:#0f172a;color:#e2e8f0;padding:20px">
<div style="max-width:600px;margin:0 auto">
  <h2 style="color:#818cf8;margin-bottom:4px">Intelligence Daily Digest</h2>
  <p style="color:#64748b;font-size:13px;margin-top:0">{datetime.utcnow().strftime('%A, %B %d, %Y')} — 6:00 AM UTC</p>
  <table style="width:100%;border-collapse:collapse;background:#1e293b;border-radius:8px;overflow:hidden">
    <thead>
      <tr style="background:#0f172a">
        <th style="padding:10px 12px;text-align:left;color:#818cf8;font-size:12px">Entity</th>
        <th style="padding:10px 12px;text-align:left;color:#818cf8;font-size:12px">Changes Detected</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
  <p style="color:#475569;font-size:11px;margin-top:16px">
    Enterprise Intelligence Platform · Automated digest ·
    <a href="http://184.72.123.188:3003/intelligence" style="color:#818cf8">View platform →</a>
  </p>
</div></body></html>"""


def run_daily_digest(db: Session, dry_run: bool = False) -> dict:
    """
    Main daily digest worker:
    1. Fetch all watched entities
    2. Re-generate each report
    3. Detect changes vs last snapshot
    4. Send email + SMS if changes found
    5. Log result
    """
    from app.services.intelligence_service import generate_intelligence_report

    _ensure_tables(db)
    watched = list_watchlist(db)
    if not watched:
        return {"status": "no_entities", "entities_checked": 0}

    entity_changes = {}
    total_changes  = 0

    for entity in watched:
        name = entity["entity_name"]
        etype = entity.get("entity_type", "org")
        try:
            report = generate_intelligence_report(db, entity_name=name, entity_type=etype)
            changes = detect_changes(db, name, report)
            save_snapshot(db, name, report)
            entity_changes[name] = changes
            total_changes += len([c for c in changes if "No significant" not in c])

            # Update last_checked
            db.execute(text("UPDATE tracked_entities SET last_checked = NOW() WHERE entity_name = :n"), {"n": name})
            db.commit()
        except Exception as exc:
            logger.warning("Digest failed for %s: %s", name, exc)
            entity_changes[name] = [f"Error during refresh: {exc}"]

    if dry_run:
        return {"status": "dry_run", "entities_checked": len(watched), "changes": entity_changes}

    # Send notifications
    html_body = _build_digest_html(entity_changes)
    subject   = f"Intelligence Digest — {total_changes} change{'s' if total_changes != 1 else ''} detected"
    email_ok  = send_email_digest(subject, html_body, _DIGEST_EMAIL)
    sms_lines = [f"{n}: {c[0]}" for n, c in entity_changes.items() if c and "No significant" not in c[0]]
    sms_ok    = send_sms_digest(
        f"Intel Digest: {total_changes} changes in {len(watched)} entities.\n" + "\n".join(sms_lines[:5]),
        _DIGEST_PHONE,
    ) if _DIGEST_PHONE else False

    # Log
    db.execute(text("""
        INSERT INTO digest_logs (recipient, channel, status, entity_count, detail)
        VALUES (:r, :ch, :s, :ec, :d)
    """), {
        "r":  _DIGEST_EMAIL, "ch": "email+sms",
        "s":  "sent" if (email_ok or sms_ok) else "failed",
        "ec": len(watched),
        "d":  json.dumps({"email": email_ok, "sms": sms_ok, "changes": total_changes}),
    })
    # Update last_digest for all entities
    db.execute(text("UPDATE tracked_entities SET last_digest = NOW()"))
    db.commit()

    return {
        "status":           "sent" if (email_ok or sms_ok) else "failed",
        "entities_checked": len(watched),
        "total_changes":    total_changes,
        "email_sent":       email_ok,
        "sms_sent":         sms_ok,
        "changes":          entity_changes,
    }
