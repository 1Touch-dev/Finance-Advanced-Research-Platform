"""
Tests for Short Interest API (Band C #40)
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestTickerShortInterest:
    def test_get_known_ticker(self):
        response = client.get("/short-interest/ticker/GME")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["ticker"] == "GME"
        assert "short_interest" in data
        assert "short_percent_float" in data
        assert "days_to_cover" in data

    def test_get_unknown_ticker(self):
        response = client.get("/short-interest/ticker/XYZ")
        assert response.status_code == 200  # Returns generic data
        data = response.json()["data"]
        assert data["ticker"] == "XYZ"


class TestShortHistory:
    def test_get_history_default(self):
        response = client.get("/short-interest/ticker/TSLA/history")
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "TSLA"
        assert len(data["history"]) == 12

    def test_get_history_custom_periods(self):
        response = client.get("/short-interest/ticker/AAPL/history?periods=6")
        assert response.status_code == 200
        data = response.json()
        assert data["periods"] == 6


class TestMostShorted:
    def test_get_most_shorted_default(self):
        response = client.get("/short-interest/most-shorted")
        assert response.status_code == 200
        data = response.json()
        assert "stocks" in data
        assert data["min_threshold"] == 10.0
        for stock in data["stocks"]:
            assert stock["short_percent_float"] >= 10.0

    def test_get_most_shorted_custom(self):
        response = client.get("/short-interest/most-shorted?min_short_percent=20&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["stocks"]) <= 5


class TestSqueezeCandidates:
    def test_get_candidates_default(self):
        response = client.get("/short-interest/squeeze-candidates")
        assert response.status_code == 200
        data = response.json()
        assert "candidates" in data
        for candidate in data["candidates"]:
            assert "squeeze_score" in candidate
            assert "risk_level" in candidate

    def test_get_candidates_custom(self):
        response = client.get("/short-interest/squeeze-candidates?min_score=70&limit=10")
        assert response.status_code == 200
        data = response.json()
        for candidate in data["candidates"]:
            assert candidate["squeeze_score"] >= 70


class TestShortChanges:
    def test_get_changes_default(self):
        response = client.get("/short-interest/changes")
        assert response.status_code == 200
        data = response.json()
        assert "stocks" in data
        assert data["direction_filter"] == "both"

    def test_get_changes_up(self):
        response = client.get("/short-interest/changes?direction=up")
        assert response.status_code == 200
        data = response.json()
        for stock in data["stocks"]:
            assert stock["short_change_percent"] >= 0

    def test_get_changes_down(self):
        response = client.get("/short-interest/changes?direction=down")
        assert response.status_code == 200

    def test_invalid_direction(self):
        response = client.get("/short-interest/changes?direction=invalid")
        assert response.status_code == 400


class TestSectorSummary:
    def test_get_sectors(self):
        response = client.get("/short-interest/sectors")
        assert response.status_code == 200
        data = response.json()
        assert "sectors" in data
        for sector in data["sectors"]:
            assert "sector" in sector
            assert "avg_short_percent_float" in sector
            assert "most_shorted" in sector


class TestShortStats:
    def test_get_stats(self):
        response = client.get("/short-interest/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_tracked" in data
        assert "highly_shorted_count" in data
        assert "most_shorted" in data
        assert "biggest_increase" in data


class TestCompare:
    def test_compare_tickers(self):
        response = client.get("/short-interest/compare?tickers=GME,AMC,TSLA")
        assert response.status_code == 200
        data = response.json()
        assert len(data["comparison"]) == 3
        tickers = [d["ticker"] for d in data["comparison"]]
        assert "GME" in tickers
        assert "AMC" in tickers
        assert "TSLA" in tickers

    def test_compare_limit(self):
        # Should limit to 10 tickers
        tickers = ",".join([f"T{i}" for i in range(15)])
        response = client.get(f"/short-interest/compare?tickers={tickers}")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] <= 10
