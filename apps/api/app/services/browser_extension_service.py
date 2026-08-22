"""
Browser Extension Service (#12)
Chrome/Firefox extension for quick lookups
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from app.core.no_data import no_data_response, NoDataReason


def get_extension_config(user_id: str) -> Dict[str, Any]:
    """Get user's extension configuration."""
    return {"status": "not_available", "reason": "Browser extension backend not configured", **no_data_response(user_id, "extension_config", NoDataReason.DEPENDENCY_MISSING, details="Browser extension backend not configured")}


def update_extension_config(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    """Update extension configuration."""
    return {"status": "not_available", "reason": "Browser extension backend not configured", **no_data_response(user_id, "extension_config_update", NoDataReason.DEPENDENCY_MISSING, details="Browser extension backend not configured")}


def quick_lookup(ticker: str) -> Dict[str, Any]:
    """Quick lookup for browser extension popup."""
    return {"status": "not_available", "reason": "Browser extension backend not configured", **no_data_response(ticker, "quick_lookup", NoDataReason.DEPENDENCY_MISSING, details="Browser extension backend not configured")}


def get_watchlist_preview(user_id: str, limit: int = 5) -> Dict[str, Any]:
    """Get watchlist preview for extension popup."""
    return {"status": "not_available", "reason": "Browser extension backend not configured", **no_data_response(user_id, "watchlist_preview", NoDataReason.DEPENDENCY_MISSING, details="Browser extension backend not configured")}


def get_alerts_preview(user_id: str) -> Dict[str, Any]:
    """Get active alerts preview for extension popup."""
    return {"status": "not_available", "reason": "Browser extension backend not configured", **no_data_response(user_id, "alerts_preview", NoDataReason.DEPENDENCY_MISSING, details="Browser extension backend not configured")}


def get_extension_manifest() -> Dict[str, Any]:
    """Get extension manifest info."""
    return {"status": "not_available", "reason": "Browser extension backend not configured", **no_data_response("extension", "manifest", NoDataReason.DEPENDENCY_MISSING, details="Browser extension backend not configured")}
