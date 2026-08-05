"""
Billing & Subscription API
Band A Priority #2: Renewal notice + one-click cancel
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.session import get_db
import uuid

router = APIRouter(prefix="/billing", tags=["billing"])


# ─── Models ─────────────────────────────────────────────────────────────────

class CancelRequest(BaseModel):
    reason: Optional[str] = None


class SubscriptionResponse(BaseModel):
    plan: str
    status: str
    price: float
    interval: str
    current_period_start: str
    current_period_end: str
    next_billing_date: Optional[str]
    cancelled_at: Optional[str] = None


class UsageResponse(BaseModel):
    reports: dict
    alerts: dict
    api_calls: dict


# ─── Mock Data (replace with Stripe/payment provider in production) ────────

_subscriptions = {}
_usage = {}


def _get_mock_subscription(user_id: str = "demo"):
    """Get or create mock subscription for demo."""
    if user_id not in _subscriptions:
        now = datetime.utcnow()
        period_start = now.replace(day=8)
        period_end = (period_start + timedelta(days=30)).replace(day=8)

        _subscriptions[user_id] = {
            "id": f"sub_{uuid.uuid4().hex[:12]}",
            "user_id": user_id,
            "plan": "Professional",
            "plan_id": "pro_monthly",
            "status": "active",
            "price": 49.00,
            "interval": "month",
            "current_period_start": period_start.isoformat(),
            "current_period_end": period_end.isoformat(),
            "next_billing_date": period_end.isoformat(),
            "cancelled_at": None,
            "cancel_reason": None,
        }

        _usage[user_id] = {
            "reports": {"used": 42, "limit": 100},
            "alerts": {"used": 18, "limit": 50},
            "api_calls": {"used": 2340, "limit": 5000},
        }

    return _subscriptions[user_id], _usage[user_id]


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.get("/subscription")
def get_subscription(user_id: str = "demo"):
    """Get current subscription details."""
    sub, usage = _get_mock_subscription(user_id)
    return {
        "subscription": sub,
        "usage": usage,
    }


@router.post("/cancel")
def cancel_subscription(request: CancelRequest, user_id: str = "demo"):
    """
    Cancel subscription with one click.
    No dark patterns - immediate cancellation, access retained until period end.
    """
    sub, _ = _get_mock_subscription(user_id)

    if sub["status"] == "cancelled":
        raise HTTPException(400, "Subscription already cancelled")

    now = datetime.utcnow()

    sub["status"] = "cancelled"
    sub["cancelled_at"] = now.isoformat()
    sub["cancel_reason"] = request.reason
    sub["next_billing_date"] = None  # No more charges

    # TODO: Send cancellation confirmation email
    # TODO: Log to audit trail
    # TODO: Trigger Stripe cancellation

    return {
        "status": "cancelled",
        "cancelled_at": now.isoformat(),
        "access_until": sub["current_period_end"],
        "message": f"Your subscription has been cancelled. You will retain access until {sub['current_period_end']}.",
    }


@router.post("/resubscribe")
def resubscribe(plan_id: str = "pro_monthly", user_id: str = "demo"):
    """Reactivate a cancelled subscription."""
    sub, _ = _get_mock_subscription(user_id)

    if sub["status"] == "active":
        raise HTTPException(400, "Subscription is already active")

    now = datetime.utcnow()
    period_end = now + timedelta(days=30)

    sub["status"] = "active"
    sub["cancelled_at"] = None
    sub["cancel_reason"] = None
    sub["current_period_start"] = now.isoformat()
    sub["current_period_end"] = period_end.isoformat()
    sub["next_billing_date"] = period_end.isoformat()

    return {
        "status": "active",
        "message": "Your subscription has been reactivated.",
        "next_billing_date": period_end.isoformat(),
    }


@router.get("/usage")
def get_usage(user_id: str = "demo"):
    """Get current usage for the billing period."""
    _, usage = _get_mock_subscription(user_id)
    return usage


@router.get("/invoices")
def list_invoices(user_id: str = "demo", limit: int = 10):
    """List past invoices."""
    # Mock invoice history
    invoices = []
    base_date = datetime.utcnow()

    for i in range(min(limit, 12)):
        invoice_date = base_date - timedelta(days=30 * i)
        invoices.append({
            "id": f"inv_{uuid.uuid4().hex[:12]}",
            "date": invoice_date.strftime("%Y-%m-%d"),
            "description": "Professional - Monthly",
            "amount": 49.00,
            "status": "paid",
            "pdf_url": f"/billing/invoices/inv_{i}/pdf",
        })

    return {"invoices": invoices}


@router.get("/invoices/{invoice_id}/pdf")
def download_invoice(invoice_id: str):
    """Download invoice PDF."""
    # TODO: Generate actual PDF
    return {
        "message": "PDF generation not implemented",
        "invoice_id": invoice_id,
    }


@router.get("/plans")
def list_plans():
    """List available subscription plans."""
    return {
        "plans": [
            {
                "id": "free",
                "name": "Free",
                "price": 0,
                "interval": "forever",
                "features": [
                    "5 intelligence reports/month",
                    "Basic stock analysis",
                    "Public SEC filings",
                    "Community support",
                ],
                "limits": {
                    "reports": 5,
                    "alerts": 3,
                    "watchlists": 1,
                    "api_calls": 100,
                },
            },
            {
                "id": "pro_monthly",
                "name": "Professional",
                "price": 49,
                "interval": "month",
                "features": [
                    "100 intelligence reports/month",
                    "Full stock & valuation analysis",
                    "SEC filings + insider trading",
                    "Real-time alerts (email)",
                    "13F institutional tracking",
                    "Priority email support",
                ],
                "limits": {
                    "reports": 100,
                    "alerts": 50,
                    "watchlists": 10,
                    "api_calls": 5000,
                },
            },
            {
                "id": "pro_annual",
                "name": "Professional (Annual)",
                "price": 39,
                "interval": "month",
                "billed": "annually",
                "features": ["Same as Professional monthly"],
                "limits": {
                    "reports": 100,
                    "alerts": 50,
                    "watchlists": 10,
                    "api_calls": 5000,
                },
            },
            {
                "id": "enterprise",
                "name": "Enterprise",
                "price": 299,
                "interval": "month",
                "features": [
                    "Unlimited intelligence reports",
                    "Full platform access",
                    "API access + webhooks",
                    "Team collaboration (5 seats)",
                    "Custom entity tracking",
                    "Dedicated account manager",
                    "SLA guarantee",
                ],
                "limits": {
                    "reports": -1,  # unlimited
                    "alerts": -1,
                    "watchlists": -1,
                    "api_calls": 100000,
                },
            },
        ]
    }


@router.post("/renewal-notice")
def send_renewal_notice(user_id: str = "demo", days_before: int = 7):
    """
    Send renewal notice to user.
    Called by scheduled job before billing date.
    """
    sub, _ = _get_mock_subscription(user_id)

    if sub["status"] != "active":
        return {"sent": False, "reason": "subscription not active"}

    # TODO: Actually send email

    return {
        "sent": True,
        "user_id": user_id,
        "renewal_date": sub["next_billing_date"],
        "amount": sub["price"],
        "message": f"Renewal notice sent for ${sub['price']} on {sub['next_billing_date']}",
    }
