"""
Tests for IPO Calendar API (Band C #38)
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestUpcomingIPOs:
    def test_get_upcoming_default(self):
        response = client.get("/ipo/upcoming")
        assert response.status_code == 200
        data = response.json()
        assert "upcoming" in data
        assert "count" in data
        assert data["days_ahead"] == 30

    def test_get_upcoming_custom_days(self):
        response = client.get("/ipo/upcoming?days=14")
        assert response.status_code == 200
        data = response.json()
        assert data["days_ahead"] == 14

    def test_get_upcoming_with_sector(self):
        response = client.get("/ipo/upcoming?sector=Technology")
        assert response.status_code == 200
        data = response.json()
        assert data["sector_filter"] == "Technology"


class TestRecentIPOs:
    def test_get_recent_default(self):
        response = client.get("/ipo/recent")
        assert response.status_code == 200
        data = response.json()
        assert "recent" in data
        assert data["days_back"] == 30

    def test_get_recent_custom(self):
        response = client.get("/ipo/recent?days=60&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert data["days_back"] == 60
        assert len(data["recent"]) <= 5


class TestIPOByTicker:
    def test_get_known_ipo(self):
        response = client.get("/ipo/ticker/FINX")
        assert response.status_code == 200
        data = response.json()
        assert data["ipo"]["ticker"] == "FINX"
        assert "offer_price" in data["ipo"]

    def test_get_unknown_ipo(self):
        response = client.get("/ipo/ticker/UNKNOWN123")
        assert response.status_code == 404


class TestLockupExpirations:
    def test_get_lockups_default(self):
        response = client.get("/ipo/lockups")
        assert response.status_code == 200
        data = response.json()
        assert "lockup_expirations" in data
        assert data["days_ahead"] == 30

    def test_get_lockups_custom(self):
        response = client.get("/ipo/lockups?days=180")
        assert response.status_code == 200
        data = response.json()
        assert data["days_ahead"] == 180


class TestIPOCalendarWeek:
    def test_get_week_calendar(self):
        response = client.get("/ipo/week")
        assert response.status_code == 200
        data = response.json()
        assert "calendar" in data
        # Should have 7 days
        assert len(data["calendar"]) == 7


class TestIPOPerformance:
    def test_get_performance_default(self):
        response = client.get("/ipo/performance")
        assert response.status_code == 200
        data = response.json()
        assert "performance" in data
        for ipo in data["performance"]:
            assert "total_return" in ipo
            assert "days_since_ipo" in ipo


class TestIPOStats:
    def test_get_stats(self):
        response = client.get("/ipo/stats")
        assert response.status_code == 200
        data = response.json()
        assert "upcoming_count" in data
        assert "priced_count" in data
        assert "avg_first_day_return" in data
        assert "by_sector" in data


class TestIPOSearch:
    def test_search_by_name(self):
        response = client.get("/ipo/search?q=Energy")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert data["query"] == "Energy"

    def test_search_by_ticker(self):
        response = client.get("/ipo/search?q=FINX")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) > 0


class TestIPOBySector:
    def test_get_sector(self):
        response = client.get("/ipo/sector/Technology")
        assert response.status_code == 200
        data = response.json()
        assert data["sector"] == "Technology"
        assert "ipos" in data
