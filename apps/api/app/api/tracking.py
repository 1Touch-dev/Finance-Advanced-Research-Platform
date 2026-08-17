"""
Tracking & Watchlist API — entity monitoring + daily digest.

GET    /tracking/watchlist           — list all watched entities
POST   /tracking/watchlist           — add entity to watchlist
DELETE /tracking/watchlist/{name}    — remove entity
GET    /tracking/snapshots/{name}    — last snapshot for entity
POST   /tracking/digest/run          — trigger digest manually (dry_run optional)
GET    /tracking/digest/logs         — past digest logs
GET    /tracking/changes/{name}      — detect changes for entity

── F-03 Big Trade Alerts ──────────────────────────────────────────
GET    /tracking/alert-rules                   — list insider_trade rules
POST   /tracking/alert-rules                   — create alert rule
GET    /tracking/alert-rules/{rule_id}         — get single rule
PATCH  /tracking/alert-rules/{rule_id}         — update threshold/scope/name
DELETE /tracking/alert-rules/{rule_id}         — delete rule
POST   /tracking/scan/insider-trades           — trigger F-03 scan manually

── F-04 Investment Threshold Alerts ───────────────────────────────
GET    /tracking/watchlist/{ticker}/threshold  — get user threshold settings
PATCH  /tracking/watchlist/{ticker}/threshold  — save user threshold settings
POST   /tracking/scan/investments              — trigger F-04 scan manually

── Alert Inbox UX (Task 2.2) ──────────────────────────────────────
GET    /tracking/alerts/count                  — unread count for nav badge
"""
import re
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db, SessionLocal

try:
    from app.services.tracking_service import (
        add_to_watchlist, remove_from_watchlist, list_watchlist,
        save_snapshot, detect_changes, run_daily_digest,
    )
    _TRACKING_OK = True
except ImportError:
    _TRACKING_OK = False

router = APIRouter(prefix="/tracking", tags=["Tracking"])

_E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")

# In-memory digest jobs (same pattern as intelligence report-job).
# Long sync digests drop browser fetch after minutes → "Failed to fetch".
_DIGEST_JOBS: Dict[str, Dict[str, Any]] = {}


def _run_digest_job(job_id: str, dry_run: bool):
    db = SessionLocal()
    try:
        _DIGEST_JOBS[job_id]["status"] = "running"
        result = run_daily_digest(db, dry_run=dry_run)
        _DIGEST_JOBS[job_id].update({
            "status": "completed",
            "result": result,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:
        _DIGEST_JOBS[job_id].update({
            "status": "failed",
            "error": str(exc),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })
    finally:
        db.close()


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class WatchRequest(BaseModel):
    entity_name:  str
    entity_type:  Optional[str] = "org"
    added_by:     Optional[str] = ""
    notes:        Optional[str] = ""


class AlertRuleCreate(BaseModel):
    name:         str
    threshold:    float
    watchlist_id: Optional[int] = None
    enabled:      Optional[bool] = True


class AlertRulePatch(BaseModel):
    name:         Optional[str] = None
    threshold:    Optional[float] = None
    watchlist_id: Optional[int] = None
    enabled:      Optional[bool] = None


class ThresholdSettings(BaseModel):
    threshold:    float
    notify_email: Optional[str] = None
    notify_phone: Optional[str] = None
    alert_on_buy: Optional[bool] = True
    alert_on_sell: Optional[bool] = False


# ── Existing watchlist / digest endpoints ─────────────────────────────────────

@router.get("/watchlist")
def get_watchlist(db: Session = Depends(get_db)):
    if not _TRACKING_OK:
        raise HTTPException(503, "Tracking service not available")
    return list_watchlist(db)


@router.post("/watchlist")
def add_watch(payload: WatchRequest, db: Session = Depends(get_db)):
    if not _TRACKING_OK:
        raise HTTPException(503, "Tracking service not available")
    return add_to_watchlist(db, payload.entity_name, payload.entity_type, payload.added_by, payload.notes)


@router.delete("/watchlist/{entity_name:path}")
def remove_watch(entity_name: str, db: Session = Depends(get_db)):
    if not _TRACKING_OK:
        raise HTTPException(503, "Tracking service not available")
    return remove_from_watchlist(db, entity_name)


@router.post("/digest/run")
def trigger_digest(dry_run: bool = False, background_tasks: BackgroundTasks = None):
    """
    Start digest in the background and return a job_id immediately.
    Poll GET /tracking/digest/job/{job_id} for status/result.
    """
    if not _TRACKING_OK:
        raise HTTPException(503, "Tracking service not available")

    job_id = str(uuid.uuid4())[:8]
    _DIGEST_JOBS[job_id] = {
        "job_id": job_id,
        "status": "started",
        "dry_run": dry_run,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "result": None,
        "error": None,
    }
    if background_tasks is not None:
        background_tasks.add_task(_run_digest_job, job_id, dry_run)
    else:
        _run_digest_job(job_id, dry_run)
    return {"job_id": job_id, "status": "started", "dry_run": dry_run}


@router.get("/digest/job/{job_id}")
def digest_job_status(job_id: str):
    job = _DIGEST_JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Digest job not found")
    out = {
        "job_id": job["job_id"],
        "status": job["status"],
        "dry_run": job.get("dry_run"),
        "started_at": job.get("started_at"),
        "completed_at": job.get("completed_at"),
        "error": job.get("error"),
    }
    if job.get("result"):
        out.update(job["result"])
    return out


@router.get("/digest/logs")
def digest_logs(limit: int = 20, db: Session = Depends(get_db)):
    if not _TRACKING_OK:
        raise HTTPException(503, "Tracking service not available")
    try:
        rows = db.execute(text("""
            SELECT id, sent_at, recipient, channel, status, entity_count, detail
            FROM digest_logs ORDER BY sent_at DESC LIMIT :lim
        """), {"lim": limit}).fetchall()
        return [dict(r._mapping) for r in rows]
    except Exception:
        return []


@router.get("/changes/{entity_name:path}")
def entity_changes(entity_name: str, report_id: Optional[int] = None, db: Session = Depends(get_db)):
    if not _TRACKING_OK:
        raise HTTPException(503, "Tracking service not available")
    if report_id:
        from app.services.intelligence_service import get_intelligence_report
        report = get_intelligence_report(db, report_id)
        if not report:
            raise HTTPException(404, "Report not found")
        return {"entity_name": entity_name, "changes": detect_changes(db, entity_name, report)}
    return {"entity_name": entity_name, "message": "Provide report_id to compare against snapshot"}


# ── Alerts inbox ──────────────────────────────────────────────────────────────

@router.get("/alerts/count")
def get_alerts_count(db: Session = Depends(get_db)):
    """
    Unread-alert badge count for the nav (Task 2.2 — in-app UX). "Unread" =
    status='new' (i.e. not yet acknowledged or snoozed). Also breaks down by
    severity so the UI can color the badge.
    """
    try:
        rows = db.execute(text("""
            SELECT severity, COUNT(*) as n
            FROM entity_alerts
            WHERE status = 'new'
            GROUP BY severity
        """)).fetchall()
        by_severity = {r._mapping["severity"] or "info": r._mapping["n"] for r in rows}
        total = sum(by_severity.values())
        return {
            "total": total,
            "by_severity": by_severity,
            "has_critical": by_severity.get("critical", 0) > 0,
        }
    except Exception:
        return {"total": 0, "by_severity": {}, "has_critical": False}


@router.get("/alerts")
def get_alerts(status: Optional[str] = None, severity: Optional[str] = None,
               limit: int = 50, db: Session = Depends(get_db)):
    try:
        where_clauses = []
        params: dict = {"lim": limit}
        if status:
            where_clauses.append("status = :status")
            params["status"] = status
        if severity:
            where_clauses.append("severity = :severity")
            params["severity"] = severity
        where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
        try:
            rows = db.execute(text(f"""
                SELECT id, entity_name, alert_type, severity, message,
                       status, created_at, acknowledged_at, snoozed_until
                FROM entity_alerts
                {where_sql}
                ORDER BY created_at DESC LIMIT :lim
            """), params).fetchall()
            return {"alerts": [dict(r._mapping) for r in rows], "total": len(rows)}
        except Exception:
            rows = db.execute(text("""
                SELECT id, sent_at as created_at, recipient, channel,
                       status, entity_count, detail
                FROM digest_logs ORDER BY sent_at DESC LIMIT :lim
            """), {"lim": limit}).fetchall()
            alerts = []
            for r in rows:
                rd = dict(r._mapping)
                alerts.append({
                    "id": rd.get("id"),
                    "entity_name": "Multiple entities",
                    "alert_type": "digest",
                    "severity": "info",
                    "message": rd.get("detail", "Daily digest ran"),
                    "status": rd.get("status", "resolved"),
                    "created_at": rd.get("created_at"),
                })
            return {"alerts": alerts, "total": len(alerts)}
    except Exception as e:
        return {"alerts": [], "total": 0, "error": str(e)}


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: int, db: Session = Depends(get_db)):
    try:
        db.execute(text("""
            UPDATE entity_alerts SET status='acknowledged', acknowledged_at=NOW()
            WHERE id=:id
        """), {"id": alert_id})
        db.commit()
        return {"status": "acknowledged", "id": alert_id}
    except Exception:
        return {"status": "ok", "id": alert_id, "note": "alerts table not available"}


@router.post("/alerts/{alert_id}/snooze")
def snooze_alert(alert_id: int, hours: int = 24, db: Session = Depends(get_db)):
    try:
        db.execute(text("""
            UPDATE entity_alerts
            SET status='snoozed', snoozed_until = NOW() + INTERVAL ':h hours'
            WHERE id=:id
        """), {"id": alert_id, "h": hours})
        db.commit()
        return {"status": "snoozed", "id": alert_id, "hours": hours}
    except Exception:
        return {"status": "ok", "id": alert_id, "note": "alerts table not available"}


# ── F-03: AlertRule CRUD ──────────────────────────────────────────────────────

def _rule_to_dict(rule) -> dict:
    threshold = 500_000.0
    if rule.params and isinstance(rule.params, dict):
        try:
            threshold = float(rule.params.get("threshold", threshold))
        except (TypeError, ValueError):
            pass
    return {
        "id": rule.id,
        "name": rule.name,
        "kind": rule.kind,
        "threshold": threshold,
        "watchlist_id": rule.watchlist_id,
        "ticker_scope": f"watchlist:{rule.watchlist_id}" if rule.watchlist_id else "global (all watchlisted tickers)",
        "enabled": rule.enabled,
    }


@router.get("/alert-rules")
def list_alert_rules(db: Session = Depends(get_db)):
    """List all insider_trade alert rules (F-03)."""
    from app.models.monitor import AlertRule
    rules = db.query(AlertRule).filter(AlertRule.kind == "insider_trade").all()
    return [_rule_to_dict(r) for r in rules]


@router.post("/alert-rules", status_code=201)
def create_alert_rule(payload: AlertRuleCreate, db: Session = Depends(get_db)):
    """Create a new insider_trade alert rule with custom threshold + optional watchlist scope (F-03)."""
    from app.models.monitor import AlertRule, Watchlist
    if not payload.name or len(payload.name.strip()) == 0:
        raise HTTPException(400, "name must be a non-empty string")
    if payload.threshold <= 0:
        raise HTTPException(400, "threshold must be > 0")
    if payload.watchlist_id:
        wl = db.query(Watchlist).filter(Watchlist.id == payload.watchlist_id).first()
        if not wl:
            raise HTTPException(404, f"Watchlist {payload.watchlist_id} not found")
    rule = AlertRule(
        name=payload.name.strip()[:255],
        kind="insider_trade",
        params={"threshold": payload.threshold},
        watchlist_id=payload.watchlist_id,
        enabled=payload.enabled if payload.enabled is not None else True,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return _rule_to_dict(rule)


@router.get("/alert-rules/{rule_id}")
def get_alert_rule(rule_id: int, db: Session = Depends(get_db)):
    """Get a single alert rule by ID (F-03)."""
    from app.models.monitor import AlertRule
    rule = db.query(AlertRule).filter(
        AlertRule.id == rule_id, AlertRule.kind == "insider_trade"
    ).first()
    if not rule:
        raise HTTPException(404, f"AlertRule {rule_id} not found")
    return _rule_to_dict(rule)


@router.patch("/alert-rules/{rule_id}")
def update_alert_rule(rule_id: int, payload: AlertRulePatch, db: Session = Depends(get_db)):
    """Partial update: threshold, name, watchlist_id, enabled (F-03)."""
    from app.models.monitor import AlertRule, Watchlist
    rule = db.query(AlertRule).filter(
        AlertRule.id == rule_id, AlertRule.kind == "insider_trade"
    ).first()
    if not rule:
        raise HTTPException(404, f"AlertRule {rule_id} not found")
    if payload.name is not None:
        if len(payload.name.strip()) == 0:
            raise HTTPException(400, "name must be non-empty")
        rule.name = payload.name.strip()[:255]
    if payload.threshold is not None:
        if payload.threshold <= 0:
            raise HTTPException(400, "threshold must be > 0")
        rule.params = {**(rule.params or {}), "threshold": payload.threshold}
    if "watchlist_id" in payload.model_fields_set:
        if payload.watchlist_id is not None:
            wl = db.query(Watchlist).filter(Watchlist.id == payload.watchlist_id).first()
            if not wl:
                raise HTTPException(404, f"Watchlist {payload.watchlist_id} not found")
        rule.watchlist_id = payload.watchlist_id
    if payload.enabled is not None:
        rule.enabled = payload.enabled
    db.commit()
    db.refresh(rule)
    return _rule_to_dict(rule)


@router.delete("/alert-rules/{rule_id}", status_code=204)
def delete_alert_rule(rule_id: int, db: Session = Depends(get_db)):
    """Permanently delete an alert rule. Historical alert_events are kept (F-03)."""
    from app.models.monitor import AlertRule
    rule = db.query(AlertRule).filter(
        AlertRule.id == rule_id, AlertRule.kind == "insider_trade"
    ).first()
    if not rule:
        raise HTTPException(404, f"AlertRule {rule_id} not found")
    db.delete(rule)
    db.commit()
    return None


# ── F-03: Manual scan trigger ─────────────────────────────────────────────────

@router.post("/scan/insider-trades")
def scan_insider_trades(
    rule_id: Optional[int] = None,
    threshold: float = 500_000,
    dry_run: bool = False,
    db: Session = Depends(get_db),
):
    """
    Manually trigger the F-03 big-trade scan.
    - rule_id: run only that rule; omit to run ALL enabled insider_trade rules.
    - dry_run=true: scan and return results without writing to DB or sending notifications.
    """
    from app.models.base import Base
    from app.db.session import engine
    Base.metadata.create_all(bind=engine)

    from app.services.big_trade_scanner import run_scan_for_rule, run_scan_all_rules, _ensure_default_rule
    from app.models.monitor import AlertRule

    if rule_id is not None:
        rule = db.query(AlertRule).filter(
            AlertRule.id == rule_id, AlertRule.kind == "insider_trade"
        ).first()
        if not rule:
            raise HTTPException(404, f"AlertRule {rule_id} not found")
        result = run_scan_for_rule(db, rule, dry_run=dry_run)
        return {"rules_run": 1, "results": [result], "dry_run": dry_run}

    _ensure_default_rule(db)
    return run_scan_all_rules(db, dry_run=dry_run)


# ── F-04: Watchlist item threshold settings ───────────────────────────────────

def _get_watchlist_item_by_ticker(db: Session, ticker: str):
    from app.models.monitor import WatchlistItem
    item = db.query(WatchlistItem).filter(
        WatchlistItem.ticker == ticker.upper()
    ).first()
    return item


@router.get("/watchlist/{ticker}/threshold")
def get_threshold(ticker: str, db: Session = Depends(get_db)):
    """Get investment threshold settings for a watchlisted ticker (F-04)."""
    item = _get_watchlist_item_by_ticker(db, ticker)
    if not item or item.investment_threshold is None:
        raise HTTPException(404, f"{ticker.upper()} not in watchlist or no threshold set")
    return {
        "ok": True,
        "ticker": item.ticker.upper(),
        "watchlist_item_id": item.id,
        "threshold": item.investment_threshold,
        "notify_email": item.notify_email,
        "notify_phone": item.notify_phone,
        "alert_on_buy": item.alert_on_buy,
        "alert_on_sell": item.alert_on_sell,
    }


@router.patch("/watchlist/{ticker}/threshold")
def set_threshold(ticker: str, payload: ThresholdSettings, db: Session = Depends(get_db)):
    """
    Save or update investment alert threshold + contact info for a watchlisted ticker (F-04).
    At least one of notify_email or notify_phone must be provided.
    Minimum threshold: 1000.
    """
    if payload.threshold < 1000:
        raise HTTPException(400, "threshold must be ≥ 1000 to avoid alert spam")

    if not payload.notify_email and not payload.notify_phone:
        raise HTTPException(400, "At least one of notify_email or notify_phone is required")

    if payload.notify_phone:
        if not _E164_RE.match(payload.notify_phone):
            raise HTTPException(400, "notify_phone must be in E.164 format e.g. +14155551234")

    item = _get_watchlist_item_by_ticker(db, ticker)
    if not item:
        raise HTTPException(404, f"{ticker.upper()} not found in any watchlist. Add it first via POST /tracking/watchlist")

    item.investment_threshold = payload.threshold
    item.notify_email = payload.notify_email or item.notify_email
    item.notify_phone = payload.notify_phone or item.notify_phone
    item.alert_on_buy = payload.alert_on_buy if payload.alert_on_buy is not None else True
    item.alert_on_sell = payload.alert_on_sell if payload.alert_on_sell is not None else False

    db.commit()
    db.refresh(item)
    return {
        "ok": True,
        "ticker": item.ticker.upper(),
        "watchlist_item_id": item.id,
        "threshold": item.investment_threshold,
        "notify_email": item.notify_email,
        "notify_phone": item.notify_phone,
        "alert_on_buy": item.alert_on_buy,
        "alert_on_sell": item.alert_on_sell,
    }


# ── F-04: Manual scan trigger ─────────────────────────────────────────────────

@router.post("/scan/investments")
def scan_investments(
    ticker: Optional[str] = None,
    dry_run: bool = False,
    db: Session = Depends(get_db),
):
    """
    Manually trigger the F-04 investment alert scan.
    - ticker: scan only this ticker; omit to scan all watchlist items with threshold set.
    - dry_run=true: return results without writing to DB or sending notifications.
    """
    from app.models.base import Base
    from app.db.session import engine
    Base.metadata.create_all(bind=engine)

    from app.services.investment_alert_service import run_scan
    return run_scan(db, ticker_filter=ticker, dry_run=dry_run)
