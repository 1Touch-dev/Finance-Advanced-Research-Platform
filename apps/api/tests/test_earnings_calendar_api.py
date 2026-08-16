"""
Tests for Earnings Calendar API (Band C #36)
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestUpcomingEarnings:
    def test_get_upcoming_default(self):
        response = client.get("/earnings/upcoming")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "count" in data
        assert data["days_ahead"] == 7

    def test_get_upcoming_custom_days(self):
        response = client.get("/earnings/upcoming?days=14")
        assert response.status_code == 200
        data = response.json()
        assert data["days_ahead"] == 14

    def test_get_upcoming_with_tickers(self):
        response = client.get("/earnings/upcoming?tickers=AAPL,MSFT")
        assert response.status_code == 200
        data = response.json()
        assert len(data["events"]) <= 2

    def test_get_upcoming_with_importance(self):
        response = client.get("/earnings/upcoming?importance=high")
        assert response.status_code == 200
        data = response.json()
        for event in data["events"]:
            assert event["importance"] == "high"


class TestEarningsByDate:
    def test_get_by_date(self):
        response = client.get("/earnings/date/2026-08-20")
        assert response.status_code == 200
        data = response.json()
        assert data["date"] == "2026-08-20"
        assert "events" in data

    def test_invalid_date_format(self):
        response = client.get("/earnings/date/20-08-2026")
        assert response.status_code == 400


class TestTickerEarnings:
    def test_get_ticker_history(self):
        response = client.get("/earnings/ticker/AAPL")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert "history" in data
        assert len(data["history"]) == 8

    def test_get_ticker_custom_quarters(self):
        response = client.get("/earnings/ticker/MSFT?quarters=4")
        assert response.status_code == 200
        data = response.json()
        assert data["quarters"] == 4


class TestEarningsWeek:
    def test_get_week_default(self):
        response = client.get("/earnings/week")
        assert response.status_code == 200
        data = response.json()
        assert "calendar" in data
        assert "total_events" in data

    def test_get_week_with_start(self):
        response = client.get("/earnings/week?start_date=2026-08-17")
        assert response.status_code == 200
        data = response.json()
        assert len(data["calendar"]) == 5  # Mon-Fri


class TestEarningsSurprises:
    def test_get_surprises_default(self):
        response = client.get("/earnings/surprises")
        assert response.status_code == 200
        data = response.json()
        assert "surprises" in data
        assert data["min_surprise_threshold"] == 5.0

    def test_get_surprises_custom(self):
        response = client.get("/earnings/surprises?min_surprise=10&days_back=60")
        assert response.status_code == 200
        data = response.json()
        assert data["min_surprise_threshold"] == 10.0


class TestEarningsSearch:
    def test_search_all(self):
        response = client.get("/earnings/search")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "total" in data

    def test_search_with_query(self):
        response = client.get("/earnings/search?query=Apple")
        assert response.status_code == 200

    def test_search_with_dates(self):
        response = client.get("/earnings/search?start_date=2026-08-01&end_date=2026-08-31")
        assert response.status_code == 200


class TestEarningsStats:
    def test_get_stats(self):
        response = client.get("/earnings/stats")
        assert response.status_code == 200
        data = response.json()
        assert "this_week" in data
        assert "next_week" in data
        assert "beats_this_week" in data
