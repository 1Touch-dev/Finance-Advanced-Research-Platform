"""
Support & Ticketing API
Band A Priority #3: Reachable human support + escalation path
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.session import get_db
import uuid
import os

router = APIRouter(prefix="/support", tags=["support"])


# ─── Models ─────────────────────────────────────────────────────────────────

class TicketCreate(BaseModel):
    category: str  # billing, technical, feature, data, account, other
    priority: str = "normal"  # low, normal, high
    subject: str
    message: str
    email: EmailStr


class TicketUpdate(BaseModel):
    status: Optional[str] = None  # open, in_progress, waiting, resolved, closed
    message: Optional[str] = None
    internal_note: Optional[str] = None


class TicketResponse(BaseModel):
    ticket_id: str
    category: str
    priority: str
    subject: str
    status: str
    created_at: str
    sla_deadline: str


# ─── In-Memory Storage (replace with DB in production) ─────────────────────

_tickets = {}


# ─── SLA Configuration ──────────────────────────────────────────────────────

SLA_HOURS = {
    "low": 48,
    "normal": 24,
    "high": 4,
}

ESCALATION_EMAIL = os.getenv("SUPPORT_ESCALATION_EMAIL", "escalations@enterprise-intel.com")
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "support@enterprise-intel.com")


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.post("/tickets", response_model=TicketResponse)
def create_ticket(ticket: TicketCreate, db: Session = Depends(get_db)):
    """Create a new support ticket."""
    ticket_id = f"TKT-{uuid.uuid4().hex[:8].upper()}"
    now = datetime.utcnow()
    sla_hours = SLA_HOURS.get(ticket.priority, 24)
    sla_deadline = now.replace(hour=now.hour + sla_hours)

    ticket_data = {
        "ticket_id": ticket_id,
        "category": ticket.category,
        "priority": ticket.priority,
        "subject": ticket.subject,
        "message": ticket.message,
        "email": ticket.email,
        "status": "open",
        "created_at": now.isoformat(),
        "sla_deadline": sla_deadline.isoformat(),
        "updates": [],
    }

    _tickets[ticket_id] = ticket_data

    # TODO: Send confirmation email to user
    # TODO: Send notification to support team
    # TODO: Log to audit trail

    return TicketResponse(
        ticket_id=ticket_id,
        category=ticket.category,
        priority=ticket.priority,
        subject=ticket.subject,
        status="open",
        created_at=now.isoformat(),
        sla_deadline=sla_deadline.isoformat(),
    )


@router.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str):
    """Get ticket details by ID."""
    ticket = _tickets.get(ticket_id)
    if not ticket:
        raise HTTPException(404, "Ticket not found")
    return ticket


@router.get("/tickets")
def list_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """List tickets with optional filtering."""
    tickets = list(_tickets.values())

    if status:
        tickets = [t for t in tickets if t["status"] == status]
    if priority:
        tickets = [t for t in tickets if t["priority"] == priority]
    if category:
        tickets = [t for t in tickets if t["category"] == category]

    # Sort by created_at descending
    tickets.sort(key=lambda t: t["created_at"], reverse=True)

    return {
        "total": len(tickets),
        "tickets": tickets[offset:offset + limit],
    }


@router.patch("/tickets/{ticket_id}")
def update_ticket(ticket_id: str, update: TicketUpdate):
    """Update a ticket (status, add reply)."""
    ticket = _tickets.get(ticket_id)
    if not ticket:
        raise HTTPException(404, "Ticket not found")

    now = datetime.utcnow().isoformat()

    if update.status:
        ticket["status"] = update.status
        ticket["updates"].append({
            "time": now,
            "type": "status_change",
            "message": f"Status changed to {update.status}",
        })

    if update.message:
        ticket["updates"].append({
            "time": now,
            "type": "reply",
            "message": update.message,
            "from": "support",
        })

    if update.internal_note:
        ticket["updates"].append({
            "time": now,
            "type": "internal_note",
            "message": update.internal_note,
        })

    ticket["updated_at"] = now

    return ticket


@router.post("/tickets/{ticket_id}/escalate")
def escalate_ticket(ticket_id: str, reason: Optional[str] = None):
    """Escalate a ticket to higher priority support."""
    ticket = _tickets.get(ticket_id)
    if not ticket:
        raise HTTPException(404, "Ticket not found")

    now = datetime.utcnow().isoformat()

    # Upgrade priority
    if ticket["priority"] == "low":
        ticket["priority"] = "normal"
    elif ticket["priority"] == "normal":
        ticket["priority"] = "high"

    ticket["escalated"] = True
    ticket["escalated_at"] = now
    ticket["updates"].append({
        "time": now,
        "type": "escalation",
        "message": f"Ticket escalated. Reason: {reason or 'User requested escalation'}",
    })

    # TODO: Notify escalation team

    return {
        "ticket_id": ticket_id,
        "escalated": True,
        "new_priority": ticket["priority"],
        "escalation_email": ESCALATION_EMAIL,
    }


@router.get("/contact-info")
def get_contact_info():
    """Get support contact information."""
    return {
        "email": SUPPORT_EMAIL,
        "escalation_email": ESCALATION_EMAIL,
        "sla": {
            "low": "48 hours",
            "normal": "24 hours",
            "high": "4 hours",
        },
        "hours": "24/7 for critical issues, business hours (9am-6pm EST) for standard support",
    }
