"""
Dashboard & Shared Watchlists Service (Band C #46)
--------------------------------------------------------------------------------
Provides:
- Watchlist sharing functionality
- Dashboard configuration management
- Widget management
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class WidgetType(Enum):
    WATCHLIST = "watchlist"
    PORTFOLIO = "portfolio"
    CHART = "chart"
    NEWS = "news"
    CALENDAR = "calendar"
    ANALYST_RATINGS = "analyst_ratings"
    MARKET_OVERVIEW = "market_overview"
    PRICE_ALERT = "price_alert"


class SharePermission(Enum):
    VIEW = "view"
    EDIT = "edit"


@dataclass
class WatchlistShareInfo:
    """Information about a watchlist share."""
    share_id: int
    watchlist_id: int
    watchlist_name: str
    shared_by: str
    shared_with: str
    permission: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "share_id": self.share_id,
            "watchlist_id": self.watchlist_id,
            "watchlist_name": self.watchlist_name,
            "shared_by": self.shared_by,
            "shared_with": self.shared_with,
            "permission": self.permission,
            "created_at": self.created_at,
        }


@dataclass
class SharedWatchlist:
    """A watchlist shared with the user."""
    watchlist_id: int
    name: str
    owner: str
    permission: str
    item_count: int
    items: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "watchlist_id": self.watchlist_id,
            "name": self.name,
            "owner": self.owner,
            "permission": self.permission,
            "item_count": self.item_count,
            "items": self.items,
        }


@dataclass
class DashboardWidget:
    """Widget configuration for a dashboard."""
    widget_id: int
    widget_type: str
    title: Optional[str]
    config: Dict[str, Any]
    position_x: int
    position_y: int
    width: int
    height: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "widget_id": self.widget_id,
            "widget_type": self.widget_type,
            "title": self.title,
            "config": self.config,
            "position": {"x": self.position_x, "y": self.position_y},
            "size": {"width": self.width, "height": self.height},
        }


@dataclass
class DashboardConfig:
    """Full dashboard configuration."""
    dashboard_id: int
    user_id: str
    name: str
    is_default: bool
    layout: Optional[Dict[str, Any]]
    widgets: List[DashboardWidget]
    created_at: str
    updated_at: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dashboard_id": self.dashboard_id,
            "user_id": self.user_id,
            "name": self.name,
            "is_default": self.is_default,
            "layout": self.layout,
            "widgets": [w.to_dict() for w in self.widgets],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# ── Default Widget Templates ─────────────────────────────────────────────────

DEFAULT_WIDGETS = [
    {
        "widget_type": "market_overview",
        "title": "Market Overview",
        "config": {"indices": ["SPY", "QQQ", "DIA", "IWM"]},
        "position_x": 0,
        "position_y": 0,
        "width": 2,
        "height": 1,
    },
    {
        "widget_type": "watchlist",
        "title": "My Watchlist",
        "config": {"watchlist_id": None, "show_change": True},
        "position_x": 2,
        "position_y": 0,
        "width": 1,
        "height": 2,
    },
    {
        "widget_type": "news",
        "title": "Latest News",
        "config": {"count": 10, "categories": ["markets", "technology"]},
        "position_x": 0,
        "position_y": 1,
        "width": 2,
        "height": 1,
    },
]


def get_default_dashboard_config(user_id: str) -> Dict[str, Any]:
    """Get default dashboard configuration for a new user."""
    return {
        "user_id": user_id,
        "name": "My Dashboard",
        "is_default": True,
        "layout": {
            "columns": 3,
            "rows": 2,
            "gap": 16,
        },
        "widgets": DEFAULT_WIDGETS,
    }


def validate_widget_config(widget_type: str, config: Dict[str, Any]) -> bool:
    """Validate widget configuration based on type."""
    required_fields = {
        "watchlist": [],
        "portfolio": [],
        "chart": ["ticker"],
        "news": [],
        "calendar": [],
        "analyst_ratings": ["ticker"],
        "market_overview": [],
        "price_alert": ["ticker", "threshold"],
    }

    required = required_fields.get(widget_type, [])
    return all(field in config for field in required)


def get_available_widget_types() -> List[Dict[str, Any]]:
    """Get list of available widget types with descriptions."""
    return [
        {
            "type": "watchlist",
            "name": "Watchlist",
            "description": "Display a watchlist with live prices",
            "icon": "list",
            "configurable": ["watchlist_id", "show_change", "columns"],
        },
        {
            "type": "portfolio",
            "name": "Portfolio Summary",
            "description": "Show portfolio performance and holdings",
            "icon": "briefcase",
            "configurable": ["portfolio_id", "show_allocation"],
        },
        {
            "type": "chart",
            "name": "Price Chart",
            "description": "Interactive price chart for a ticker",
            "icon": "chart",
            "configurable": ["ticker", "timeframe", "indicators"],
        },
        {
            "type": "news",
            "name": "News Feed",
            "description": "Latest market news and headlines",
            "icon": "newspaper",
            "configurable": ["count", "categories", "tickers"],
        },
        {
            "type": "calendar",
            "name": "Earnings Calendar",
            "description": "Upcoming earnings and events",
            "icon": "calendar",
            "configurable": ["days_ahead", "watchlist_only"],
        },
        {
            "type": "analyst_ratings",
            "name": "Analyst Ratings",
            "description": "Analyst consensus and price targets",
            "icon": "star",
            "configurable": ["ticker", "show_history"],
        },
        {
            "type": "market_overview",
            "name": "Market Overview",
            "description": "Major indices and market sentiment",
            "icon": "globe",
            "configurable": ["indices"],
        },
        {
            "type": "price_alert",
            "name": "Price Alerts",
            "description": "Active price alerts and triggers",
            "icon": "bell",
            "configurable": ["show_triggered"],
        },
    ]
