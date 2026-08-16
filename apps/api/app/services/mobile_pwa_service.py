"""
Mobile PWA Service (#33)
Progressive web app with push alerts
"""
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import hashlib


@dataclass 
class PushSubscription:
    user_id: str
    endpoint: str
    auth_key: str
    p256dh_key: str
    created_at: datetime


# Mock subscriptions
SUBSCRIPTIONS: Dict[str, PushSubscription] = {}
NOTIFICATION_PREFERENCES: Dict[str, Dict[str, bool]] = {}


def register_push_subscription(user_id: str, subscription_data: Dict[str, Any]) -> Dict[str, Any]:
    """Register a push notification subscription."""
    sub = PushSubscription(
        user_id=user_id,
        endpoint=subscription_data.get("endpoint", ""),
        auth_key=subscription_data.get("keys", {}).get("auth", ""),
        p256dh_key=subscription_data.get("keys", {}).get("p256dh", ""),
        created_at=datetime.now()
    )
    SUBSCRIPTIONS[user_id] = sub
    return {
        "status": "registered",
        "user_id": user_id,
        "subscription_id": hashlib.md5(sub.endpoint.encode()).hexdigest()[:12]
    }


def unregister_push_subscription(user_id: str) -> Dict[str, Any]:
    """Unregister push notification subscription."""
    if user_id in SUBSCRIPTIONS:
        del SUBSCRIPTIONS[user_id]
    return {"status": "unregistered", "user_id": user_id}


def get_notification_preferences(user_id: str) -> Dict[str, Any]:
    """Get user notification preferences."""
    prefs = NOTIFICATION_PREFERENCES.get(user_id, {
        "price_alerts": True,
        "earnings_reminders": True,
        "news_alerts": True,
        "portfolio_updates": True,
        "market_open_close": False,
        "dividend_alerts": True,
        "insider_trading": True,
        "sec_filings": False
    })
    return {"user_id": user_id, "preferences": prefs}


def update_notification_preferences(user_id: str, preferences: Dict[str, bool]) -> Dict[str, Any]:
    """Update notification preferences."""
    current = NOTIFICATION_PREFERENCES.get(user_id, {})
    current.update(preferences)
    NOTIFICATION_PREFERENCES[user_id] = current
    return {"user_id": user_id, "preferences": current, "updated": True}


def send_push_notification(user_id: str, title: str, body: str, data: Dict = None) -> Dict[str, Any]:
    """Send push notification to user."""
    return {
        "status": "sent",
        "user_id": user_id,
        "notification": {
            "title": title,
            "body": body,
            "data": data or {},
            "timestamp": datetime.now().isoformat()
        }
    }


def get_pwa_manifest() -> Dict[str, Any]:
    """Get PWA manifest."""
    return {
        "name": "Finance Research Platform",
        "short_name": "FinanceRP",
        "description": "Advanced financial research and portfolio tracking",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#1a1a2e",
        "theme_color": "#0f3460",
        "icons": [
            {"src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png"}
        ],
        "screenshots": [
            {"src": "/screenshots/dashboard.png", "sizes": "1280x720", "type": "image/png"}
        ],
        "categories": ["finance", "business"],
        "orientation": "any"
    }


def get_service_worker_config() -> Dict[str, Any]:
    """Get service worker configuration."""
    return {
        "cache_name": "finance-platform-v1",
        "cache_urls": [
            "/",
            "/dashboard",
            "/portfolio",
            "/watchlist",
            "/offline.html"
        ],
        "api_cache_strategy": "network-first",
        "static_cache_strategy": "cache-first",
        "offline_fallback": "/offline.html"
    }


def get_install_prompt_config() -> Dict[str, Any]:
    """Get install prompt configuration."""
    return {
        "show_after_visits": 3,
        "show_after_seconds": 30,
        "dismiss_for_days": 7,
        "prompt_text": "Install our app for quick access to your portfolio!",
        "install_button_text": "Install App",
        "dismiss_button_text": "Maybe Later"
    }


def check_pwa_compatibility() -> Dict[str, Any]:
    """Check PWA feature compatibility."""
    return {
        "features": {
            "service_worker": True,
            "push_notifications": True,
            "background_sync": True,
            "offline_storage": True,
            "web_share": True,
            "file_system_access": False,
            "badging": True
        },
        "install_criteria": {
            "https": True,
            "manifest": True,
            "service_worker": True,
            "engagement": True
        }
    }
