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


# ── In-Memory Storage ─────────────────────────────────────────────────────────

_watchlist_shares: Dict[int, WatchlistShareInfo] = {}
_dashboards: Dict[int, DashboardConfig] = {}
_widgets: Dict[int, DashboardWidget] = {}
_next_share_id = 1
_next_dashboard_id = 1
_next_widget_id = 1

def _get_watchlist_from_db(watchlist_id: int) -> Optional[Dict[str, Any]]:
    """Get watchlist from database instead of mock data."""
    from app.db.session import get_db_context
    from app.models.monitor import Watchlist, WatchlistItem
    try:
        with get_db_context() as db:
            wl = db.query(Watchlist).filter(Watchlist.id == watchlist_id).first()
            if not wl:
                return None
            items = db.query(WatchlistItem).filter(WatchlistItem.watchlist_id == wl.id).all()
            return {
                "id": wl.id,
                "name": wl.name,
                "owner": wl.meta.get("owner", "unknown") if wl.meta else "unknown",
                "items": [{"ticker": i.ticker, "name": i.notes or i.ticker} for i in items if i.ticker],
            }
    except Exception as e:
        logger.error("Failed to fetch watchlist %d from DB: %s", watchlist_id, e)
        return None


# ── Watchlist Sharing Functions ───────────────────────────────────────────────


def share_watchlist(
    watchlist_id: int,
    shared_by: str,
    shared_with: str,
    permission: str = "view",
) -> WatchlistShareInfo:
    """Share a watchlist with another user."""
    global _next_share_id

    watchlist = _get_watchlist_from_db(watchlist_id)
    if not watchlist:
        raise ValueError(f"Watchlist {watchlist_id} not found")

    if watchlist["owner"] != shared_by:
        raise PermissionError("Only the owner can share a watchlist")

    if shared_by == shared_with:
        raise ValueError("Cannot share watchlist with yourself")

    # Check if already shared
    for share in _watchlist_shares.values():
        if share.watchlist_id == watchlist_id and share.shared_with == shared_with:
            # Update permission
            share.permission = permission
            return share

    share = WatchlistShareInfo(
        share_id=_next_share_id,
        watchlist_id=watchlist_id,
        watchlist_name=watchlist["name"],
        shared_by=shared_by,
        shared_with=shared_with,
        permission=permission,
        created_at=datetime.utcnow().isoformat(),
    )
    _watchlist_shares[_next_share_id] = share
    _next_share_id += 1
    return share


def get_shared_with_me(user_id: str) -> List[SharedWatchlist]:
    """Get all watchlists shared with the current user."""
    result = []
    for share in _watchlist_shares.values():
        if share.shared_with == user_id:
            wl = _get_watchlist_from_db(share.watchlist_id)
            if wl:
                result.append(SharedWatchlist(
                    watchlist_id=share.watchlist_id,
                    name=wl["name"],
                    owner=share.shared_by,
                    permission=share.permission,
                    item_count=len(wl.get("items", [])),
                    items=wl.get("items", []) if share.permission == "edit" else [],
                ))
    return result


def get_my_shares(user_id: str) -> List[WatchlistShareInfo]:
    """Get all shares created by the current user."""
    return [s for s in _watchlist_shares.values() if s.shared_by == user_id]


def get_watchlist_shares(watchlist_id: int) -> List[WatchlistShareInfo]:
    """Get all shares for a specific watchlist."""
    return [s for s in _watchlist_shares.values() if s.watchlist_id == watchlist_id]


def revoke_share(share_id: int, user_id: str) -> bool:
    """Revoke a watchlist share."""
    share = _watchlist_shares.get(share_id)
    if not share:
        return False
    if share.shared_by != user_id:
        raise PermissionError("Only the owner can revoke shares")
    del _watchlist_shares[share_id]
    return True


def update_share_permission(share_id: int, user_id: str, permission: str) -> Optional[WatchlistShareInfo]:
    """Update the permission level of a share."""
    share = _watchlist_shares.get(share_id)
    if not share:
        return None
    if share.shared_by != user_id:
        raise PermissionError("Only the owner can update share permissions")
    share.permission = permission
    return share


# ── Dashboard Functions ───────────────────────────────────────────────────────


def create_dashboard(
    user_id: str,
    name: str = "My Dashboard",
    is_default: bool = False,
    layout: Optional[Dict[str, Any]] = None,
) -> DashboardConfig:
    """Create a new dashboard."""
    global _next_dashboard_id

    # If setting as default, unset others
    if is_default:
        for dash in _dashboards.values():
            if dash.user_id == user_id:
                dash.is_default = False

    now = datetime.utcnow().isoformat()
    dashboard = DashboardConfig(
        dashboard_id=_next_dashboard_id,
        user_id=user_id,
        name=name,
        is_default=is_default,
        layout=layout or {"columns": 3, "rows": 2, "gap": 16},
        widgets=[],
        created_at=now,
        updated_at=None,
    )
    _dashboards[_next_dashboard_id] = dashboard
    _next_dashboard_id += 1
    return dashboard


def get_user_dashboards(user_id: str) -> List[DashboardConfig]:
    """Get all dashboards for a user."""
    return [d for d in _dashboards.values() if d.user_id == user_id]


def get_dashboard(dashboard_id: int, user_id: str) -> Optional[DashboardConfig]:
    """Get a specific dashboard."""
    dash = _dashboards.get(dashboard_id)
    if dash and dash.user_id == user_id:
        return dash
    return None


def update_dashboard(
    dashboard_id: int,
    user_id: str,
    name: Optional[str] = None,
    is_default: Optional[bool] = None,
    layout: Optional[Dict[str, Any]] = None,
) -> Optional[DashboardConfig]:
    """Update dashboard properties."""
    dash = _dashboards.get(dashboard_id)
    if not dash or dash.user_id != user_id:
        return None

    if name is not None:
        dash.name = name
    if layout is not None:
        dash.layout = layout
    if is_default is not None and is_default:
        for d in _dashboards.values():
            if d.user_id == user_id:
                d.is_default = False
        dash.is_default = True

    dash.updated_at = datetime.utcnow().isoformat()
    return dash


def delete_dashboard(dashboard_id: int, user_id: str) -> bool:
    """Delete a dashboard."""
    dash = _dashboards.get(dashboard_id)
    if not dash or dash.user_id != user_id:
        return False

    # Remove widgets
    for w in dash.widgets:
        _widgets.pop(w.widget_id, None)

    del _dashboards[dashboard_id]
    return True


def get_default_dashboard(user_id: str) -> Optional[DashboardConfig]:
    """Get the user's default dashboard."""
    for dash in _dashboards.values():
        if dash.user_id == user_id and dash.is_default:
            return dash
    return None


# ── Widget Functions ──────────────────────────────────────────────────────────


def add_widget(
    dashboard_id: int,
    user_id: str,
    widget_type: str,
    title: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    position_x: int = 0,
    position_y: int = 0,
    width: int = 1,
    height: int = 1,
) -> Optional[DashboardWidget]:
    """Add a widget to a dashboard."""
    global _next_widget_id

    dash = _dashboards.get(dashboard_id)
    if not dash or dash.user_id != user_id:
        return None

    if not validate_widget_config(widget_type, config or {}):
        raise ValueError(f"Invalid config for widget type {widget_type}")

    widget = DashboardWidget(
        widget_id=_next_widget_id,
        widget_type=widget_type,
        title=title or widget_type.replace("_", " ").title(),
        config=config or {},
        position_x=position_x,
        position_y=position_y,
        width=width,
        height=height,
    )
    _widgets[_next_widget_id] = widget
    dash.widgets.append(widget)
    dash.updated_at = datetime.utcnow().isoformat()
    _next_widget_id += 1
    return widget


def update_widget(
    widget_id: int,
    dashboard_id: int,
    user_id: str,
    title: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    position_x: Optional[int] = None,
    position_y: Optional[int] = None,
    width: Optional[int] = None,
    height: Optional[int] = None,
) -> Optional[DashboardWidget]:
    """Update widget properties."""
    dash = _dashboards.get(dashboard_id)
    if not dash or dash.user_id != user_id:
        return None

    widget = _widgets.get(widget_id)
    if not widget:
        return None

    if title is not None:
        widget.title = title
    if config is not None:
        widget.config = config
    if position_x is not None:
        widget.position_x = position_x
    if position_y is not None:
        widget.position_y = position_y
    if width is not None:
        widget.width = width
    if height is not None:
        widget.height = height

    dash.updated_at = datetime.utcnow().isoformat()
    return widget


def remove_widget(widget_id: int, dashboard_id: int, user_id: str) -> bool:
    """Remove a widget from a dashboard."""
    dash = _dashboards.get(dashboard_id)
    if not dash or dash.user_id != user_id:
        return False

    if widget_id not in _widgets:
        return False

    _widgets.pop(widget_id)
    dash.widgets = [w for w in dash.widgets if w.widget_id != widget_id]
    dash.updated_at = datetime.utcnow().isoformat()
    return True


def reorder_widgets(
    dashboard_id: int,
    user_id: str,
    widget_positions: List[Dict[str, int]],
) -> Optional[DashboardConfig]:
    """Update positions of multiple widgets at once."""
    dash = _dashboards.get(dashboard_id)
    if not dash or dash.user_id != user_id:
        return None

    for pos in widget_positions:
        widget_id = pos.get("widget_id")
        widget = _widgets.get(widget_id)
        if widget:
            widget.position_x = pos.get("x", widget.position_x)
            widget.position_y = pos.get("y", widget.position_y)
            widget.width = pos.get("width", widget.width)
            widget.height = pos.get("height", widget.height)

    dash.updated_at = datetime.utcnow().isoformat()
    return dash


# ── Dashboard Templates ───────────────────────────────────────────────────────


def get_dashboard_templates() -> List[Dict[str, Any]]:
    """Get available dashboard templates."""
    return [
        {
            "id": "default",
            "name": "Default",
            "description": "Standard dashboard with market overview, watchlist, and news",
            "preview_widgets": ["market_overview", "watchlist", "news"],
        },
        {
            "id": "trader",
            "name": "Active Trader",
            "description": "Focus on charts, alerts, and quick actions",
            "preview_widgets": ["chart", "price_alert", "watchlist"],
        },
        {
            "id": "analyst",
            "name": "Research Analyst",
            "description": "Emphasis on fundamentals and analyst ratings",
            "preview_widgets": ["analyst_ratings", "calendar", "news"],
        },
        {
            "id": "portfolio",
            "name": "Portfolio Manager",
            "description": "Portfolio-centric view with performance tracking",
            "preview_widgets": ["portfolio", "watchlist", "calendar"],
        },
    ]


def apply_template(user_id: str, template_id: str, name: Optional[str] = None) -> Optional[DashboardConfig]:
    """Create a dashboard from a template."""
    templates = {
        "default": DEFAULT_WIDGETS,
        "trader": [
            {"widget_type": "chart", "title": "Chart", "config": {"ticker": "SPY"}, "position_x": 0, "position_y": 0, "width": 2, "height": 2},
            {"widget_type": "price_alert", "title": "Alerts", "config": {}, "position_x": 2, "position_y": 0, "width": 1, "height": 1},
            {"widget_type": "watchlist", "title": "Quick List", "config": {}, "position_x": 2, "position_y": 1, "width": 1, "height": 1},
        ],
        "analyst": [
            {"widget_type": "analyst_ratings", "title": "Ratings", "config": {"ticker": "AAPL"}, "position_x": 0, "position_y": 0, "width": 1, "height": 2},
            {"widget_type": "calendar", "title": "Earnings", "config": {}, "position_x": 1, "position_y": 0, "width": 1, "height": 1},
            {"widget_type": "news", "title": "Research News", "config": {}, "position_x": 2, "position_y": 0, "width": 1, "height": 2},
        ],
        "portfolio": [
            {"widget_type": "portfolio", "title": "My Portfolio", "config": {}, "position_x": 0, "position_y": 0, "width": 2, "height": 2},
            {"widget_type": "watchlist", "title": "Watchlist", "config": {}, "position_x": 2, "position_y": 0, "width": 1, "height": 1},
            {"widget_type": "calendar", "title": "Events", "config": {}, "position_x": 2, "position_y": 1, "width": 1, "height": 1},
        ],
    }

    if template_id not in templates:
        return None

    dash = create_dashboard(user_id, name or f"{template_id.title()} Dashboard")
    for w in templates[template_id]:
        add_widget(
            dash.dashboard_id, user_id,
            w["widget_type"], w.get("title"), w.get("config", {}),
            w["position_x"], w["position_y"], w["width"], w["height"],
        )

    return get_dashboard(dash.dashboard_id, user_id)
