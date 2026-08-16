"""
Tests for M&A Rumor Tracking API (Band C #39)
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestActiveRumors:
    def test_get_active_default(self):
        response = client.get("/ma-rumors/active")
        assert response.status_code == 200
        data = response.json()
        assert "rumors" in data
        assert "count" in data
        assert data["filters"]["days"] == 30

    def test_get_active_with_status(self):
        response = client.get("/ma-rumors/active?status=rumor")
        assert response.status_code == 200
        data = response.json()
        assert data["filters"]["status"] == "rumor"
        for rumor in data["rumors"]:
            assert rumor["status"] == "rumor"

    def test_get_active_with_sector(self):
        response = client.get("/ma-rumors/active?sector=Technology")
        assert response.status_code == 200
        data = response.json()
        assert data["filters"]["sector"] == "Technology"

    def test_get_active_with_min_probability(self):
        response = client.get("/ma-rumors/active?min_probability=30")
        assert response.status_code == 200
        data = response.json()
        for rumor in data["rumors"]:
            assert rumor["probability_score"] >= 30


class TestRumorById:
    def test_get_known_rumor(self):
        response = client.get("/ma-rumors/rumor/MA001")
        assert response.status_code == 200
        data = response.json()
        assert data["rumor"]["rumor_id"] == "MA001"

    def test_get_unknown_rumor(self):
        response = client.get("/ma-rumors/rumor/UNKNOWN123")
        assert response.status_code == 404


class TestRumorsByTicker:
    def test_get_by_target(self):
        response = client.get("/ma-rumors/ticker/SNAP")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "SNAP"
        assert len(data["rumors"]) > 0

    def test_get_by_acquirer(self):
        response = client.get("/ma-rumors/ticker/META")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "META"


class TestHighProbability:
    def test_get_high_probability_default(self):
        response = client.get("/ma-rumors/high-probability")
        assert response.status_code == 200
        data = response.json()
        assert data["min_probability"] == 40.0
        for rumor in data["rumors"]:
            assert rumor["probability_score"] >= 40.0

    def test_get_high_probability_custom(self):
        response = client.get("/ma-rumors/high-probability?min_score=50")
        assert response.status_code == 200
        data = response.json()
        assert data["min_probability"] == 50.0


class TestConfirmedDeals:
    def test_get_confirmed(self):
        response = client.get("/ma-rumors/confirmed")
        assert response.status_code == 200
        data = response.json()
        assert "deals" in data
        for deal in data["deals"]:
            assert deal["status"] == "confirmed"


class TestByDealType:
    def test_get_acquisition(self):
        response = client.get("/ma-rumors/by-type/acquisition")
        assert response.status_code == 200
        data = response.json()
        assert data["deal_type"] == "acquisition"
        for rumor in data["rumors"]:
            assert rumor["deal_type"] == "acquisition"

    def test_get_merger(self):
        response = client.get("/ma-rumors/by-type/merger")
        assert response.status_code == 200

    def test_invalid_deal_type(self):
        response = client.get("/ma-rumors/by-type/invalid_type")
        assert response.status_code == 400


class TestLargestDeals:
    def test_get_largest_default(self):
        response = client.get("/ma-rumors/largest")
        assert response.status_code == 200
        data = response.json()
        assert "deals" in data
        assert len(data["deals"]) <= 10
        # Check sorted by value
        if len(data["deals"]) > 1:
            assert data["deals"][0]["estimated_value"] >= data["deals"][1]["estimated_value"]

    def test_get_largest_custom_limit(self):
        response = client.get("/ma-rumors/largest?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["deals"]) <= 5


class TestMAStats:
    def test_get_stats(self):
        response = client.get("/ma-rumors/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_rumors" in data
        assert "active_rumors" in data
        assert "confirmed_deals" in data
        assert "total_estimated_value" in data
        assert "by_sector" in data
        assert "by_deal_type" in data


class TestSearch:
    def test_search_by_company(self):
        response = client.get("/ma-rumors/search?q=Snap")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert data["query"] == "Snap"

    def test_search_by_ticker(self):
        response = client.get("/ma-rumors/search?q=PINS")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) > 0


class TestRecentUpdates:
    def test_get_updates_default(self):
        response = client.get("/ma-rumors/updates")
        assert response.status_code == 200
        data = response.json()
        assert "updates" in data
        assert data["hours_back"] == 24

    def test_get_updates_custom(self):
        response = client.get("/ma-rumors/updates?hours=48")
        assert response.status_code == 200
        data = response.json()
        assert data["hours_back"] == 48
