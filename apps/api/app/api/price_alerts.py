"""
Price Alerts API (Band C #35)
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional, List

from app.auth.security import get_current_user

from app.services.price_alert_service import (
    create_alert,
    get_user_alerts,
    get_alert,
    update_alert,
    delete_alert,
    check_alerts,
    get_user_notifications,
    mark_notification_read,
    get_alert_types,
    get_alert_stats,
)

router = APIRouter(prefix="/alerts", tags=["price-alerts"])


@router.post("")
async def create_price_alert(
    user_id: str = Query(..., description="User ID"),
    ticker: str = Query(..., description="Stock ticker"),
    alert_type: str = Query(..., description="Alert type"),
    target_value: float = Query(..., description="Target value"),
    channels: Optional[str] = Query(None, description="Notification channels (comma-separated)"),
    note: Optional[str] = Query(None, description="Note"),
    expires_in_days: Optional[int] = Query(None, description="Days until expiration"),
    recurring: bool = Query(False, description="Recurring alert"),
    current_user: dict = Depends(get_current_user),
):
    """Create a new price alert."""
    channel_list = [c.strip() for c in channels.split(",")] if channels else None
    
    alert = create_alert(
        user_id=user_id,
        ticker=ticker,
        alert_type=alert_type,
        target_value=target_value,
        notification_channels=channel_list,
        note=note,
        expires_in_days=expires_in_days,
        recurring=recurring,
    )
    
    return {
        "alert": alert.to_dict(),
        "message": "Alert created successfully",
    }


@router.get("")
async def list_alerts(
    user_id: str = Query(..., description="User ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
):
    """Get all alerts for a user."""
    alerts = get_user_alerts(user_id, status, ticker)
    return {
        "alerts": [a.to_dict() for a in alerts],
        "count": len(alerts),
    }


@router.get("/types")
async def list_alert_types():
    """Get available alert types."""
    return {
        "alert_types": get_alert_types(),
    }


@router.get("/stats")
async def alert_stats(
    user_id: str = Query(..., description="User ID"),
):
    """Get alert statistics for a user."""
    return get_alert_stats(user_id)


@router.get("/notifications")
async def list_notifications(
    user_id: str = Query(..., description="User ID"),
    unread_only: bool = Query(False, description="Only unread"),
    limit: int = Query(50, ge=1, le=200),
):
    """Get notifications for a user."""
    notifications = get_user_notifications(user_id, unread_only, limit)
    return {
        "notifications": [n.to_dict() for n in notifications],
        "count": len(notifications),
    }


@router.post("/notifications/{notification_id}/read")
async def mark_read(
    notification_id: str,
    user_id: str = Query(..., description="User ID"),
    current_user: dict = Depends(get_current_user),
):
    """Mark a notification as read."""
    success = mark_notification_read(notification_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    return {"marked_read": True}


@router.get("/{alert_id}")
async def get_single_alert(
    alert_id: str,
    user_id: str = Query(..., description="User ID"),
):
    """Get a specific alert."""
    alert = get_alert(alert_id, user_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"alert": alert.to_dict()}


@router.put("/{alert_id}")
async def update_price_alert(
    alert_id: str,
    user_id: str = Query(..., description="User ID"),
    target_value: Optional[float] = Query(None),
    channels: Optional[str] = Query(None),
    note: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """Update an alert."""
    channel_list = [c.strip() for c in channels.split(",")] if channels else None
    
    alert = update_alert(
        alert_id=alert_id,
        user_id=user_id,
        target_value=target_value,
        notification_channels=channel_list,
        note=note,
        status=status,
    )
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {
        "alert": alert.to_dict(),
        "updated": True,
    }


@router.delete("/{alert_id}")
async def delete_price_alert(
    alert_id: str,
    user_id: str = Query(..., description="User ID"),
    current_user: dict = Depends(get_current_user),
):
    """Delete an alert."""
    success = delete_alert(alert_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"deleted": True, "alert_id": alert_id}


@router.post("/check/{ticker}")
async def check_ticker_alerts(
    ticker: str,
    current_price: float = Query(..., description="Current price"),
    current_user: dict = Depends(get_current_user),
):
    """Check if any alerts should trigger for a ticker (internal use)."""
    triggered = check_alerts(ticker, current_price)
    return {
        "ticker": ticker.upper(),
        "current_price": current_price,
        "triggered_count": len(triggered),
        "triggered_alerts": [a.to_dict() for a in triggered],
    }
