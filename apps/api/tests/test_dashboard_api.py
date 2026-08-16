"""
Tests for Dashboard & Shared Watchlists API (Band C #46)
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── Dashboard Service Tests ──────────────────────────────────────────────────

class TestDashboardService:
    """Test dashboard service functions."""

    def test_default_config(self):
        """Default dashboard config is returned correctly."""
        from app.services.dashboard_service import get_default_dashboard_config

        config = get_default_dashboard_config("user123")

        assert config["user_id"] == "user123"
        assert config["name"] == "My Dashboard"
        assert config["is_default"] is True
        assert "widgets" in config
        assert len(config["widgets"]) > 0

    def test_widget_types(self):
        """Available widget types are returned."""
        from app.services.dashboard_service import get_available_widget_types

        types = get_available_widget_types()

        assert len(types) > 0
        assert all("type" in t for t in types)
        assert all("name" in t for t in types)
        assert all("description" in t for t in types)

    def test_widget_type_names(self):
        """Expected widget types are available."""
        from app.services.dashboard_service import get_available_widget_types

        types = get_available_widget_types()
        type_names = [t["type"] for t in types]

        assert "watchlist" in type_names
        assert "portfolio" in type_names
        assert "chart" in type_names
        assert "news" in type_names

    def test_validate_widget_config(self):
        """Widget config validation works."""
        from app.services.dashboard_service import validate_widget_config

        # Valid configs
        assert validate_widget_config("watchlist", {}) is True
        assert validate_widget_config("chart", {"ticker": "AAPL"}) is True

        # Invalid configs
        assert validate_widget_config("chart", {}) is False
        assert validate_widget_config("price_alert", {}) is False


# ── Dashboard Dataclass Tests ────────────────────────────────────────────────

class TestDashboardDataclasses:
    """Test dashboard dataclasses."""

    def test_widget_to_dict(self):
        """DashboardWidget serializes correctly."""
        from app.services.dashboard_service import DashboardWidget as DWConfig

        widget = DWConfig(
            widget_id=1,
            widget_type="watchlist",
            title="My Watchlist",
            config={"watchlist_id": 1},
            position_x=0,
            position_y=0,
            width=2,
            height=1,
        )

        data = widget.to_dict()
        assert data["widget_id"] == 1
        assert data["widget_type"] == "watchlist"
        assert "position" in data
        assert "size" in data

    def test_shared_watchlist_to_dict(self):
        """SharedWatchlist serializes correctly."""
        from app.services.dashboard_service import SharedWatchlist

        shared = SharedWatchlist(
            watchlist_id=1,
            name="Tech Stocks",
            owner="user1",
            permission="view",
            item_count=5,
            items=[],
        )

        data = shared.to_dict()
        assert data["watchlist_id"] == 1
        assert data["name"] == "Tech Stocks"
        assert data["owner"] == "user1"
        assert data["permission"] == "view"

    def test_watchlist_share_info_to_dict(self):
        """WatchlistShareInfo serializes correctly."""
        from app.services.dashboard_service import WatchlistShareInfo

        share = WatchlistShareInfo(
            share_id=1,
            watchlist_id=2,
            watchlist_name="My List",
            shared_by="alice",
            shared_with="bob",
            permission="edit",
            created_at="2025-01-01T00:00:00",
        )

        data = share.to_dict()
        assert data["share_id"] == 1
        assert data["shared_by"] == "alice"
        assert data["shared_with"] == "bob"


# ── Dashboard API Tests ──────────────────────────────────────────────────────

class TestDashboardAPI:
    """Test dashboard API endpoints."""

    def test_list_dashboards_returns_default(self):
        """GET /dashboard returns default config for new user."""
        response = client.get("/dashboard?user_id=new_user_123")
        # Returns default config when DB tables don't exist
        assert response.status_code == 200
        data = response.json()
        assert "dashboards" in data
        assert "count" in data

    def test_create_dashboard_requires_user(self):
        """POST /dashboard requires user_id."""
        response = client.post("/dashboard")
        assert response.status_code == 422  # Missing required param


# ── Widget API Tests ─────────────────────────────────────────────────────────
# Note: These tests require DB tables to exist. Skipped for now.

class TestWidgetAPI:
    """Test widget API endpoints."""

    def test_widget_type_enum_values(self):
        """Widget types have correct enum values."""
        from app.services.dashboard_service import WidgetType

        # All widget types should have string values
        for wt in WidgetType:
            assert isinstance(wt.value, str)
            assert len(wt.value) > 0


# ── Watchlist Sharing API Tests ──────────────────────────────────────────────

class TestWatchlistSharingAPI:
    """Test watchlist sharing API endpoints."""

    def test_share_requires_params(self):
        """POST /watchlist/{id}/share requires shared_by and shared_with."""
        response = client.post("/watchlist/1/share")
        assert response.status_code == 422

    def test_get_shared_watchlists_requires_user(self):
        """GET /watchlist/shared requires user_id."""
        response = client.get("/watchlist/shared")
        assert response.status_code == 422

    def test_get_shared_watchlists_empty(self):
        """GET /watchlist/shared returns empty for user with no shares."""
        response = client.get("/watchlist/shared?user_id=nonexistent_user")
        # Returns empty list when DB tables don't exist
        assert response.status_code == 200
        data = response.json()
        assert "shared_watchlists" in data
        assert data["count"] == 0


# ── Share Permission Tests ───────────────────────────────────────────────────

class TestSharePermissions:
    """Test share permission validation."""

    def test_permission_enum_values(self):
        """SharePermission enum has correct values."""
        from app.services.dashboard_service import SharePermission

        assert SharePermission.VIEW.value == "view"
        assert SharePermission.EDIT.value == "edit"
        assert len(list(SharePermission)) == 2


# ── Enum Tests ───────────────────────────────────────────────────────────────

class TestEnums:
    """Test enum definitions."""

    def test_widget_type_enum(self):
        """WidgetType enum has expected values."""
        from app.services.dashboard_service import WidgetType

        assert WidgetType.WATCHLIST.value == "watchlist"
        assert WidgetType.PORTFOLIO.value == "portfolio"
        assert WidgetType.CHART.value == "chart"
        assert WidgetType.NEWS.value == "news"

    def test_share_permission_enum(self):
        """SharePermission enum has expected values."""
        from app.services.dashboard_service import SharePermission

        assert SharePermission.VIEW.value == "view"
        assert SharePermission.EDIT.value == "edit"
