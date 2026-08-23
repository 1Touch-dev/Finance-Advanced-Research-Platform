"""
Billing & Subscription API
Billing system is in setup mode — Stripe integration pending webhook configuration.
The /plans endpoint returns valid static plan data; all subscription-management
endpoints return an honest "not_configured" status until Stripe is wired.
"""
from fastapi import APIRouter, Depends
from app.auth.security import get_current_user

router = APIRouter(prefix="/billing", tags=["billing"])

_NOT_CONFIGURED = {
    "status": "not_configured",
    "message": "Billing system is in setup mode. Contact support for subscription management.",
    "plans_available": True,
}


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.get("/subscription")
def get_subscription(user_id: str = "demo",
    current_user: dict = Depends(get_current_user),
):
    """Get current subscription details."""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    return _NOT_CONFIGURED


@router.post("/cancel")
def cancel_subscription(user_id: str = "demo",
    current_user: dict = Depends(get_current_user),):
    """Cancel subscription (not yet configured)."""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    return _NOT_CONFIGURED


@router.post("/resubscribe")
def resubscribe(plan_id: str = "pro_monthly", user_id: str = "demo",
    current_user: dict = Depends(get_current_user),):
    """Reactivate a cancelled subscription (not yet configured)."""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    return _NOT_CONFIGURED


@router.get("/usage")
def get_usage(user_id: str = "demo",
    current_user: dict = Depends(get_current_user),
):
    """Get current usage for the billing period."""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    return _NOT_CONFIGURED


@router.get("/invoices")
def list_invoices(user_id: str = "demo", limit: int = 10,
    current_user: dict = Depends(get_current_user),
):
    """List past invoices."""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    return _NOT_CONFIGURED


@router.get("/invoices/{invoice_id}/pdf")
def download_invoice(invoice_id: str):
    """Download invoice PDF (not yet configured)."""
    return _NOT_CONFIGURED


@router.post("/renewal-notice")
def send_renewal_notice(user_id: str = "demo", days_before: int = 7,
    current_user: dict = Depends(get_current_user),):
    """Send renewal notice to user (not yet configured)."""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    return _NOT_CONFIGURED


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
                    "reports": -1,
                    "alerts": -1,
                    "watchlists": -1,
                    "api_calls": 100000,
                },
            },
        ]
    }
