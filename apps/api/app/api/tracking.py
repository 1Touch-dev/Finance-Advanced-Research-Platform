"""
Tracking & Watchlist API — entity monitoring + daily digest.

GET    /tracking/watchlist           — list all watched entities
POST   /tracking/watchlist           — add entity to watchlist
DELETE /tracking/watchlist/{name}    — remove entity
GET    /tracking/snapshots/{name}    — last snapshot for entity
POST   /tracking/digest/run          — trigger digest manually (dry_run optional)
GET    /tracking/digest/logs         — past digest logs
GET    /tracking/changes/{name}      — detect changes for entity
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db

try:
    from app.services.tracking_service import (
        add_to_watchlist, remove_from_watchlist, list_watchlist,
        save_snapshot, detect_changes, run_daily_digest,
    )
    _TRACKING_OK = True
except ImportError:
    _TRACKING_OK = False

router = APIRouter(prefix="/tracking", tags=["Tracking"])


class WatchRequest(BaseModel):
    entity_name:  str
    entity_type:  Optional[str] = "org"
    added_by:     Optional[str] = ""
    notes:        Optional[str] = ""


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
def trigger_digest(dry_run: bool = False, background_tasks: BackgroundTasks = None, db: Session = Depends(get_db)):
    """
    Manually trigger the daily digest.
    dry_run=true returns the changes without sending notifications.
    """
    if not _TRACKING_OK:
        raise HTTPException(503, "Tracking service not available")
    return run_daily_digest(db, dry_run=dry_run)


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
    """
    Detect recent changes for an entity vs its last snapshot.
    Optionally provide a report_id to compare against.
    """
    if not _TRACKING_OK:
        raise HTTPException(503, "Tracking service not available")

    if report_id:
        from app.services.intelligence_service import get_intelligence_report
        report = get_intelligence_report(db, report_id)
        if not report:
            raise HTTPException(404, "Report not found")
        return {"entity_name": entity_name, "changes": detect_changes(db, entity_name, report)}

    return {"entity_name": entity_name, "message": "Provide report_id to compare against snapshot"}


# ── Alerts ────────────────────────────────────────────────────────────────────

@router.get("/alerts")
def get_alerts(status: Optional[str] = None, severity: Optional[str] = None,
               limit: int = 50, db: Session = Depends(get_db)):
    """
    Alert inbox: all triggered alerts from entity monitoring.
    Filter by status (new|acknowledged|snoozed|resolved) and severity (info|warn|critical).
    """
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
        # Try dedicated alerts table first, fall back to digest_logs
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
            # Fallback: surface digest log entries as alerts
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
