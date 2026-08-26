"""
Mobile PWA Service (#33)
Progressive web app with push alerts

BLOCKED: Push notification delivery requires VAPID keys configuration.
Push notification functions return no_data responses until the push service is configured.
PWA manifest, service worker config, and preference management are fully functional.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging
from app.core.no_data import no_data_response, NoDataReason

log = logging.getLogger(__name__)

# Notification preferences — backed by Redis with in-memory fallback
try:
    from app.core.cache import cache_json_get, cache_json_set
    _REDIS_PREFS = True
except ImportError:
    _REDIS_PREFS = False
    def cache_json_get(k): return None
    def cache_json_set(k, v, ttl=0): pass

_PREFS_TTL = 86400 * 90   # 90-day TTL (refreshed on every write)
_notification_preferences: Dict[str, Dict[str, bool]] = {}  # in-memory fallback


def _prefs_key(user_id: str) -> str:
    return f"pwa:prefs:{user_id}"


def _load_prefs(user_id: str) -> Optional[Dict[str, bool]]:
    cached = cache_json_get(_prefs_key(user_id))
    if cached is not None:
        return cached
    return _notification_preferences.get(user_id)


def _save_prefs(user_id: str, prefs: Dict[str, bool]) -> None:
    _notification_preferences[user_id] = prefs
    cache_json_set(_prefs_key(user_id), prefs, ttl=_PREFS_TTL)


def register_push_subscription(user_id: str, subscription_data: Dict[str, Any]) -> Dict[str, Any]:
    """Register a push notification subscription.

    BLOCKED: Push notification delivery requires VAPID keys configuration.
    Subscription is stored but notifications cannot be delivered until service is configured.
    """
    return no_data_response(
        entity=user_id,
        data_type="push_subscription",
        reason=NoDataReason.SERVICE_UNAVAILABLE,
        source="Push Notification Service",
        details="Push notification service not configured. VAPID keys required for Web Push API.",
    )


def unregister_push_subscription(user_id: str) -> Dict[str, Any]:
    """Unregister push notification subscription.

    BLOCKED: Push notification service requires VAPID keys configuration.
    """
    return no_data_response(
        entity=user_id,
        data_type="push_unsubscription",
        reason=NoDataReason.SERVICE_UNAVAILABLE,
        source="Push Notification Service",
        details="Push notification service not configured. VAPID keys required for Web Push API.",
    )


def get_notification_preferences(user_id: str) -> Dict[str, Any]:
    """Get user notification preferences."""
    defaults = {
        "price_alerts": True,
        "earnings_alerts": True,
        "news_alerts": True,
        "portfolio_updates": True,
        "market_opens": False,
        "insider_trading": True,
    }
    prefs = _load_prefs(user_id) or defaults
    return {"user_id": user_id, "preferences": prefs}


def update_notification_preferences(user_id: str, preferences: Dict[str, bool]) -> Dict[str, Any]:
    """Update notification preferences."""
    current = _load_prefs(user_id) or {}
    current.update(preferences)
    _save_prefs(user_id, current)
    return {"user_id": user_id, "preferences": current, "updated": True}


def send_push_notification(user_id: str, title: str, body: str, data: Dict = None) -> Dict[str, Any]:
    """Send push notification to user.

    BLOCKED: Push notification delivery requires VAPID keys configuration.
    Cannot send push notifications until the service is configured.
    """
    return no_data_response(
        entity=user_id,
        data_type="push_notification",
        reason=NoDataReason.SERVICE_UNAVAILABLE,
        source="Push Notification Service",
        details="Push notification service not configured. VAPID keys required for Web Push API.",
    )


def get_pwa_manifest() -> Dict[str, Any]:
    """Get PWA manifest."""
    return {
        "name": "Finance Research Platform",
        "short_name": "FinanceRP",
        "description": "Advanced financial research and portfolio analytics",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0f172a",
        "theme_color": "#6366f1",
        "orientation": "any",
        "icons": [
            {"src": "/icons/icon-72x72.png", "sizes": "72x72", "type": "image/png"},
            {"src": "/icons/icon-96x96.png", "sizes": "96x96", "type": "image/png"},
            {"src": "/icons/icon-128x128.png", "sizes": "128x128", "type": "image/png"},
            {"src": "/icons/icon-144x144.png", "sizes": "144x144", "type": "image/png"},
            {"src": "/icons/icon-152x152.png", "sizes": "152x152", "type": "image/png"},
            {"src": "/icons/icon-192x192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/icons/icon-384x384.png", "sizes": "384x384", "type": "image/png"},
            {"src": "/icons/icon-512x512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
        ],
        "categories": ["finance", "business", "productivity"],
        "screenshots": [
            {"src": "/screenshots/desktop.png", "sizes": "1280x720", "type": "image/png", "form_factor": "wide"},
            {"src": "/screenshots/mobile.png", "sizes": "750x1334", "type": "image/png", "form_factor": "narrow"},
        ],
        "shortcuts": [
            {"name": "Portfolio", "short_name": "Portfolio", "url": "/portfolio", "icons": [{"src": "/icons/portfolio.png", "sizes": "96x96"}]},
            {"name": "Watchlist", "short_name": "Watch", "url": "/watchlist", "icons": [{"src": "/icons/watchlist.png", "sizes": "96x96"}]},
            {"name": "Search", "short_name": "Search", "url": "/search", "icons": [{"src": "/icons/search.png", "sizes": "96x96"}]},
        ],
    }


def get_service_worker_config() -> Dict[str, Any]:
    """Get service worker configuration."""
    return {
        "cache_name": "finance-rp-v1",
        "cache_first_routes": [
            "/api/market/indices",
            "/api/stock/*/quote",
        ],
        "network_first_routes": [
            "/api/portfolio/*",
            "/api/watchlist/*",
            "/api/alerts/*",
        ],
        "offline_fallback": "/offline.html",
        "precache_routes": [
            "/",
            "/portfolio",
            "/watchlist",
            "/search",
            "/offline.html",
        ],
        "max_cache_age_seconds": 3600,
        "background_sync_enabled": True,
        "periodic_sync_interval_hours": 1,
    }


def get_install_prompt_config() -> Dict[str, Any]:
    """Get install prompt configuration."""
    return {
        "show_after_visits": 2,
        "show_after_seconds": 30,
        "dismiss_cooldown_days": 7,
        "never_show_after_dismissals": 3,
        "custom_prompt": {
            "title": "Install Finance Research Platform",
            "description": "Get quick access to your portfolio and real-time market data",
            "install_button": "Install App",
            "dismiss_button": "Maybe Later",
        },
    }


def check_pwa_compatibility() -> Dict[str, Any]:
    """Check PWA feature compatibility."""
    return {
        "features": {
            "service_worker": {"required": True, "description": "Offline support and caching"},
            "manifest": {"required": True, "description": "App installation metadata"},
            "push_api": {"required": False, "description": "Push notifications (needs VAPID)"},
            "background_sync": {"required": False, "description": "Background data sync"},
            "periodic_sync": {"required": False, "description": "Periodic background updates"},
            "web_share": {"required": False, "description": "Native share dialog"},
            "badging": {"required": False, "description": "App badge notifications"},
        },
        "minimum_requirements": {
            "https": True,
            "service_worker": True,
            "manifest": True,
        },
        "browser_support": {
            "chrome": "49+",
            "firefox": "44+",
            "safari": "11.1+",
            "edge": "17+",
        },
    }
