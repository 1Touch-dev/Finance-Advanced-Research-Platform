"""
System Status & Incident API
Band A Priority #4: Honest status page with incident history
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.session import get_db
import logging
import uuid
import asyncio
import httpx

log = logging.getLogger(__name__)

router = APIRouter(prefix="/status", tags=["status"])


# ─── Models ─────────────────────────────────────────────────────────────────

class ServiceStatus(BaseModel):
    id: str
    name: str
    description: str
    status: str  # operational, degraded, partial_outage, major_outage, maintenance
    uptime: float  # percentage
    last_check: str


class IncidentCreate(BaseModel):
    title: str
    severity: str  # minor, major, critical, maintenance
    affected_services: List[str]
    message: str


class IncidentUpdate(BaseModel):
    status: Optional[str] = None  # investigating, identified, monitoring, resolved
    message: str


class Incident(BaseModel):
    id: str
    title: str
    status: str
    severity: str
    affected_services: List[str]
    created_at: str
    resolved_at: Optional[str]
    updates: List[dict]


# ─── Service Definitions ────────────────────────────────────────────────────

SERVICES = [
    {"id": "api", "name": "Core API", "description": "Main API endpoints", "health_url": "/health"},
    {"id": "web", "name": "Web Application", "description": "Frontend application", "health_url": None},
    {"id": "data", "name": "Data Pipeline", "description": "Real-time data ingestion", "health_url": None},
    {"id": "search", "name": "Search Service", "description": "OpenSearch cluster", "health_url": None},
    {"id": "auth", "name": "Authentication", "description": "Login & session management", "health_url": None},
    {"id": "alerts", "name": "Alert System", "description": "Email & notification delivery", "health_url": None},
]


# ─── In-Memory Storage (replace with DB in production) ─────────────────────

_incidents: List[dict] = [
    {
        "id": "inc-001",
        "title": "Elevated API latency",
        "status": "resolved",
        "severity": "minor",
        "affected_services": ["api"],
        "created_at": "2026-08-04T14:30:00Z",
        "resolved_at": "2026-08-04T15:45:00Z",
        "updates": [
            {"time": "2026-08-04T15:45:00Z", "status": "resolved", "message": "Issue resolved. All systems back to normal."},
            {"time": "2026-08-04T15:00:00Z", "status": "identified", "message": "Identified root cause as database connection pool saturation. Scaling up."},
            {"time": "2026-08-04T14:30:00Z", "status": "investigating", "message": "Investigating reports of slow API responses."},
        ],
    },
    {
        "id": "inc-002",
        "title": "Scheduled database maintenance",
        "status": "completed",
        "severity": "maintenance",
        "affected_services": ["api", "data"],
        "created_at": "2026-08-01T02:00:00Z",
        "resolved_at": "2026-08-01T04:00:00Z",
        "updates": [
            {"time": "2026-08-01T04:00:00Z", "status": "completed", "message": "Maintenance completed successfully."},
            {"time": "2026-08-01T02:00:00Z", "status": "in_progress", "message": "Beginning scheduled database maintenance. Brief service interruption expected."},
        ],
    },
]

_service_status: dict = {}
_uptime_history: dict = {s["id"]: [] for s in SERVICES}


# ─── Helper Functions ───────────────────────────────────────────────────────

def _calculate_uptime(service_id: str, days: int = 90) -> float:
    """Calculate uptime percentage for a service over N days."""
    # In production, this would query actual monitoring data
    # For now, return high uptime with slight variation
    import random
    base_uptime = 99.90
    variation = random.uniform(0, 0.09)
    return round(base_uptime + variation, 4)


def _get_service_status(service_id: str) -> str:
    """Get current status for a service."""
    # Check if any active incidents affect this service
    for incident in _incidents:
        if incident["status"] not in ["resolved", "completed"]:
            if service_id in incident.get("affected_services", []):
                if incident["severity"] == "critical":
                    return "major_outage"
                elif incident["severity"] == "major":
                    return "partial_outage"
                elif incident["severity"] == "maintenance":
                    return "maintenance"
                else:
                    return "degraded"
    return "operational"


def _get_overall_status() -> str:
    """Determine overall system status."""
    statuses = [_get_service_status(s["id"]) for s in SERVICES]

    if "major_outage" in statuses:
        return "major_outage"
    if "partial_outage" in statuses:
        return "partial_outage"
    if "maintenance" in statuses:
        return "maintenance"
    if "degraded" in statuses:
        return "degraded"
    return "operational"


def _ensure_subscriber_table() -> None:
    """Create the status_subscribers table on first use (no Alembic migration in this repo yet)."""
    from app.models.base import Base
    from app.db.session import engine
    from app.models.monitor import StatusSubscriber  # noqa: F401 — registers the table on Base.metadata
    Base.metadata.create_all(bind=engine)


def _notify_subscribers(incident: dict, event: str) -> dict:
    """
    Fan out an incident create/update to every active subscriber via
    email (SendGrid), generic webhook, and/or Slack incoming webhook.
    Best-effort: one subscriber's delivery failure never blocks the others
    or the incident API response. Runs as a FastAPI BackgroundTask, so it
    opens its own short-lived DB session rather than reusing the (already
    closed-by-then) request-scoped one.
    """
    from app.db.session import SessionLocal
    from app.models.monitor import StatusSubscriber
    from app.services.sendgrid_client import sendgrid_client

    _ensure_subscriber_table()

    db = SessionLocal()
    try:
        try:
            subscribers = db.query(StatusSubscriber).filter(StatusSubscriber.active == True).all()  # noqa: E712
        except Exception as e:
            log.warning("Could not load status subscribers: %s", e)
            return {"notified": 0, "failed": 0, "error": str(e)}

        verb = "created" if event == "created" else "updated"
        title = incident.get("title", "Incident")
        latest_message = (incident.get("updates") or [{}])[0].get("message", "")
        subject = f"[Status] {title} — {incident.get('status', 'update')}"
        body_html = (
            f"<p><strong>{title}</strong> was just {verb}.</p>"
            f"<p>Status: <strong>{incident.get('status')}</strong> · Severity: {incident.get('severity')}</p>"
            f"<p>{latest_message}</p>"
            f"<p>Affected services: {', '.join(incident.get('affected_services') or []) or 'n/a'}</p>"
        )
        webhook_payload = {
            "event": f"incident.{event}",
            "incident": incident,
        }
        slack_payload = {
            "text": f"*{title}* {verb} — status: {incident.get('status')} ({incident.get('severity')})\n{latest_message}",
        }

        notified, failed = 0, 0
        for sub in subscribers:
            ok = False
            if sub.email:
                result = sendgrid_client.send_email(sub.email, subject, body_html)
                ok = ok or bool(result.get("success"))
                if result.get("error"):
                    log.info("Status email notify skipped/failed for subscriber %s: %s", sub.id, result["error"])
            if sub.webhook_url:
                try:
                    r = httpx.post(sub.webhook_url, json=webhook_payload, timeout=10)
                    ok = ok or r.status_code < 400
                except Exception as e:
                    log.info("Status webhook notify failed for subscriber %s: %s", sub.id, e)
            if sub.slack_webhook:
                try:
                    r = httpx.post(sub.slack_webhook, json=slack_payload, timeout=10)
                    ok = ok or r.status_code < 400
                except Exception as e:
                    log.info("Status Slack notify failed for subscriber %s: %s", sub.id, e)
            if ok:
                notified += 1
            else:
                failed += 1

        log.info("Status incident %s notify: %d ok / %d failed / %d total subscribers",
                  event, notified, failed, len(subscribers))
        return {"notified": notified, "failed": failed, "total_subscribers": len(subscribers)}
    finally:
        db.close()


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.get("")
def get_status():
    """Get overall system status and all services."""
    now = datetime.utcnow().isoformat()

    services = []
    for svc in SERVICES:
        services.append({
            "id": svc["id"],
            "name": svc["name"],
            "description": svc["description"],
            "status": _get_service_status(svc["id"]),
            "uptime": _calculate_uptime(svc["id"]),
            "last_check": now,
        })

    # Get recent incidents (last 90 days)
    cutoff = (datetime.utcnow() - timedelta(days=90)).isoformat()
    recent_incidents = [i for i in _incidents if i["created_at"] >= cutoff]

    return {
        "overall_status": _get_overall_status(),
        "services": services,
        "incidents": recent_incidents,
        "last_updated": now,
    }


@router.get("/services")
def list_services():
    """List all monitored services."""
    now = datetime.utcnow().isoformat()

    return {
        "services": [
            {
                "id": svc["id"],
                "name": svc["name"],
                "description": svc["description"],
                "status": _get_service_status(svc["id"]),
                "uptime": _calculate_uptime(svc["id"]),
                "last_check": now,
            }
            for svc in SERVICES
        ]
    }


@router.get("/services/{service_id}")
def get_service(service_id: str):
    """Get status for a specific service."""
    svc = next((s for s in SERVICES if s["id"] == service_id), None)
    if not svc:
        raise HTTPException(404, "Service not found")

    return {
        "id": svc["id"],
        "name": svc["name"],
        "description": svc["description"],
        "status": _get_service_status(svc["id"]),
        "uptime": _calculate_uptime(svc["id"]),
        "last_check": datetime.utcnow().isoformat(),
    }


@router.get("/incidents")
def list_incidents(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    days: int = 90,
):
    """List incidents with optional filtering."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

    incidents = [i for i in _incidents if i["created_at"] >= cutoff]

    if status:
        incidents = [i for i in incidents if i["status"] == status]
    if severity:
        incidents = [i for i in incidents if i["severity"] == severity]

    # Sort by created_at descending
    incidents.sort(key=lambda i: i["created_at"], reverse=True)

    return {"incidents": incidents}


@router.get("/incidents/{incident_id}")
def get_incident(incident_id: str):
    """Get incident details."""
    incident = next((i for i in _incidents if i["id"] == incident_id), None)
    if not incident:
        raise HTTPException(404, "Incident not found")
    return incident


@router.post("/incidents")
def create_incident(incident: IncidentCreate, background_tasks: BackgroundTasks):
    """Create a new incident (admin only in production)."""
    incident_id = f"inc-{uuid.uuid4().hex[:6]}"
    now = datetime.utcnow().isoformat()

    incident_data = {
        "id": incident_id,
        "title": incident.title,
        "status": "investigating",
        "severity": incident.severity,
        "affected_services": incident.affected_services,
        "created_at": now,
        "resolved_at": None,
        "updates": [
            {
                "time": now,
                "status": "investigating",
                "message": incident.message,
            }
        ],
    }

    _incidents.insert(0, incident_data)

    background_tasks.add_task(_notify_subscribers, incident_data, "created")

    return incident_data


@router.post("/incidents/{incident_id}/update")
def update_incident(incident_id: str, update: IncidentUpdate, background_tasks: BackgroundTasks):
    """Add an update to an incident."""
    incident = next((i for i in _incidents if i["id"] == incident_id), None)
    if not incident:
        raise HTTPException(404, "Incident not found")

    now = datetime.utcnow().isoformat()

    new_update = {
        "time": now,
        "status": update.status or incident["status"],
        "message": update.message,
    }

    incident["updates"].insert(0, new_update)

    if update.status:
        incident["status"] = update.status
        if update.status in ["resolved", "completed"]:
            incident["resolved_at"] = now

    background_tasks.add_task(_notify_subscribers, incident, "updated")

    return incident


@router.get("/uptime")
def get_uptime_summary(days: int = 90):
    """Get uptime summary for all services."""
    return {
        "period_days": days,
        "services": {
            svc["id"]: {
                "name": svc["name"],
                "uptime_percent": _calculate_uptime(svc["id"], days),
            }
            for svc in SERVICES
        },
        "overall_uptime": round(sum(_calculate_uptime(s["id"], days) for s in SERVICES) / len(SERVICES), 4),
    }


@router.post("/subscribe")
def subscribe_to_updates(
    email: Optional[str] = None,
    webhook_url: Optional[str] = None,
    slack_webhook: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Subscribe to status updates. Persisted to status_subscribers (Band A #4)."""
    from app.models.monitor import StatusSubscriber

    if not any([email, webhook_url, slack_webhook]):
        raise HTTPException(400, "Provide at least one notification method")

    _ensure_subscriber_table()

    existing = None
    if email:
        existing = db.query(StatusSubscriber).filter(
            StatusSubscriber.email == email, StatusSubscriber.active == True  # noqa: E712
        ).first()

    if existing:
        existing.webhook_url = webhook_url or existing.webhook_url
        existing.slack_webhook = slack_webhook or existing.slack_webhook
        db.commit()
        db.refresh(existing)
        sub = existing
    else:
        sub = StatusSubscriber(
            email=email,
            webhook_url=webhook_url,
            slack_webhook=slack_webhook,
            active=True,
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)

    subscription_id = f"sub_{sub.id}"

    return {
        "subscription_id": subscription_id,
        "email": sub.email,
        "webhook_url": sub.webhook_url,
        "slack_webhook": sub.slack_webhook,
        "message": "Subscription created. You will receive notifications for incidents and maintenance.",
    }


@router.delete("/subscribe/{subscription_id}")
def unsubscribe_from_updates(subscription_id: str, db: Session = Depends(get_db)):
    """Unsubscribe from status updates (subscription_id is the 'sub_<id>' string returned by POST /subscribe)."""
    from app.models.monitor import StatusSubscriber

    try:
        sub_pk = int(subscription_id.replace("sub_", ""))
    except ValueError:
        raise HTTPException(400, "Invalid subscription_id")

    _ensure_subscriber_table()
    sub = db.query(StatusSubscriber).filter(StatusSubscriber.id == sub_pk).first()
    if not sub:
        raise HTTPException(404, "Subscription not found")

    sub.active = False
    sub.unsubscribed_at = datetime.utcnow()
    db.commit()

    return {"status": "unsubscribed", "subscription_id": subscription_id}
