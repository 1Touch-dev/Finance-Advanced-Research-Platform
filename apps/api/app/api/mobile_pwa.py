"""
Mobile PWA API (#33)
Progressive web app with push alerts
"""
from fastapi import APIRouter, Query, HTTPException, Body
from typing import Optional, Dict, Any

from app.services.mobile_pwa_service import (
    register_push_subscription,
    unregister_push_subscription,
    get_notification_preferences,
    update_notification_preferences,
    send_push_notification,
    get_pwa_manifest,
    get_service_worker_config,
    get_install_prompt_config,
    check_pwa_compatibility,
)

router = APIRouter(prefix="/pwa", tags=["PWA"])


@router.get("/manifest")
def get_manifest():
    """Get PWA manifest.json content."""
    return get_pwa_manifest()


@router.get("/sw-config")
def get_sw_config():
    """Get service worker configuration."""
    return get_service_worker_config()


@router.get("/install-prompt")
def get_install_prompt():
    """Get install prompt configuration."""
    return get_install_prompt_config()


@router.get("/compatibility")
def get_compatibility():
    """Check PWA feature compatibility."""
    return check_pwa_compatibility()


@router.post("/push/subscribe")
def subscribe_push(
    user_id: str = Query(..., description="User ID"),
    subscription: Dict[str, Any] = Body(..., description="Push subscription object")
):
    """Register push notification subscription."""
    return register_push_subscription(user_id, subscription)


@router.delete("/push/subscribe")
def unsubscribe_push(
    user_id: str = Query(..., description="User ID")
):
    """Unregister push notification subscription."""
    return unregister_push_subscription(user_id)


@router.get("/notifications/preferences")
def get_preferences(
    user_id: str = Query(..., description="User ID")
):
    """Get user notification preferences."""
    return get_notification_preferences(user_id)


@router.put("/notifications/preferences")
def update_preferences(
    user_id: str = Query(..., description="User ID"),
    preferences: Dict[str, bool] = Body(..., description="Notification preferences")
):
    """Update notification preferences."""
    return update_notification_preferences(user_id, preferences)


@router.post("/notifications/send")
def send_notification(
    user_id: str = Query(..., description="User ID"),
    title: str = Query(..., description="Notification title"),
    body: str = Query(..., description="Notification body"),
    data: Optional[Dict[str, Any]] = Body(None, description="Additional data")
):
    """Send push notification to user."""
    return send_push_notification(user_id, title, body, data)
