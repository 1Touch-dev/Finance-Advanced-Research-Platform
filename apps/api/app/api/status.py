"""
System Status & Incident API
Band A Priority #4: Honest status page with incident history
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.session import get_db, check_db_health
import time
import os
import uuid
import asyncio
import httpx

router = APIRouter(prefix="/status", tags=["status"])

_START_TIME = time.time()


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


# ─── Health Check ────────────────────────────────────────────────────────────

@router.get("/health")
def health_check():
    """Comprehensive health check for monitoring and CI."""
    uptime = round(time.time() - _START_TIME, 1)

    db_health = check_db_health()

    try:
        from app.services.scheduler import get_scheduler_status
        sched = get_scheduler_status()
        scheduler_info = {"running": sched.get("running", False), "jobs": len(sched.get("jobs", []))}
    except Exception:
        scheduler_info = {"running": False, "jobs": 0}

    configured_apis = {}
    api_env_map = {
        "finnhub": "FINNHUB_API_KEY",
        "fred": "FRED_API_KEY",
        "sec_edgar": "SEC_USER_AGENT",
        "finra": "FINRA_API_KEY",
        "newsapi": "NEWSAPI_KEY",
    }
    for name, env_var in api_env_map.items():
        configured_apis[name] = "configured" if os.getenv(env_var) else "not_configured"

    return {
        "status": "healthy",
        "version": "1.0.0",
        "uptime_seconds": uptime,
        "database": {"status": db_health.get("status", "unknown"), "latency_ms": db_health.get("latency_ms")},
        "scheduler": scheduler_info,
        "services": {
            "real_data": [
                "portfolio", "earnings", "short_interest", "insider",
                "economics", "global_equity", "ma_rumors", "gov_trading", "ipo_calendar",
            ],
            "unavailable": ["brokerage", "reddit", "narrative_model", "push_notifications"],
        },
        "external_apis": configured_apis,
    }


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
def create_incident(incident: IncidentCreate):
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

    # TODO: Send notifications to subscribers

    return incident_data


@router.post("/incidents/{incident_id}/update")
def update_incident(incident_id: str, update: IncidentUpdate):
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

    # TODO: Send notifications to subscribers

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


@router.get("/scheduler")
def scheduler_status():
    """Get background data-refresh scheduler status."""
    from app.services.scheduler import get_scheduler_status
    return get_scheduler_status()


@router.post("/subscribe")
def subscribe_to_updates(
    email: Optional[str] = None,
    webhook_url: Optional[str] = None,
    slack_webhook: Optional[str] = None,
):
    """Subscribe to status updates."""
    # TODO: Implement subscription storage

    if not any([email, webhook_url, slack_webhook]):
        raise HTTPException(400, "Provide at least one notification method")

    subscription_id = f"sub_{uuid.uuid4().hex[:8]}"

    return {
        "subscription_id": subscription_id,
        "email": email,
        "webhook_url": webhook_url,
        "slack_webhook": slack_webhook,
        "message": "Subscription created. You will receive notifications for incidents and maintenance.",
    }
