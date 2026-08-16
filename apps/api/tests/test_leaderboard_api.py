"""
Tests for app.api.leaderboard API endpoints (Band B #30)
────────────────────────────────────────────────────────────────────────────
Tests the FastAPI endpoints for:
  - /leaderboard/predictions - Get prediction leaderboard
  - /leaderboard/ideas - Get idea leaderboard
  - /leaderboard/predict - Submit prediction
  - /leaderboard/idea - Submit trading idea
  - /leaderboard/user/{id} - Get user score
  - /leaderboard/calibration/{id} - Get user calibration
  - /leaderboard/tiers - Get tier definitions
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── Prediction Leaderboard Tests ─────────────────────────────────────────────

class TestPredictionLeaderboard:
    """Tests for GET /leaderboard/predictions."""

    def test_get_leaderboard_default(self):
        response = client.get("/leaderboard/predictions")
        assert response.status_code == 200

        data = response.json()
        assert "leaderboard" in data
        assert "metric" in data
        assert "count" in data

    def test_get_leaderboard_by_metric(self):
        for metric in ["brier", "accuracy", "calibration"]:
            response = client.get(f"/leaderboard/predictions?metric={metric}")
            assert response.status_code == 200

            data = response.json()
            assert data["metric"] == metric

    def test_leaderboard_respects_limit(self):
        response = client.get("/leaderboard/predictions?limit=5")
        assert response.status_code == 200

        data = response.json()
        assert len(data["leaderboard"]) <= 5

    def test_leaderboard_entries_have_fields(self):
        response = client.get("/leaderboard/predictions")
        data = response.json()

        if data["leaderboard"]:
            entry = data["leaderboard"][0]
            assert "rank" in entry
            assert "user_id" in entry
            assert "score" in entry
            assert "tier" in entry


# ── Idea Leaderboard Tests ───────────────────────────────────────────────────

class TestIdeaLeaderboard:
    """Tests for GET /leaderboard/ideas."""

    def test_get_idea_leaderboard(self):
        response = client.get("/leaderboard/ideas")
        assert response.status_code == 200

        data = response.json()
        assert "ideas" in data
        assert "count" in data

    def test_idea_leaderboard_limit(self):
        response = client.get("/leaderboard/ideas?limit=10")
        assert response.status_code == 200


# ── Submit Prediction Tests ──────────────────────────────────────────────────

class TestSubmitPrediction:
    """Tests for POST /leaderboard/predict."""

    def test_submit_prediction(self):
        response = client.post("/leaderboard/predict", json={
            "user_id": "test_user_001",
            "ticker": "NVDA",
            "prediction_type": "earnings_beat",
            "predicted_value": 1.0,
            "confidence": 0.75,
            "target_date": "2025-01-15"
        })
        assert response.status_code == 200

        data = response.json()
        assert "id" in data
        assert data["user_id"] == "test_user_001"
        assert data["ticker"] == "NVDA"
        assert data["confidence"] == 0.75

    def test_submit_direction_prediction(self):
        response = client.post("/leaderboard/predict", json={
            "user_id": "test_user_002",
            "ticker": "AAPL",
            "prediction_type": "direction",
            "predicted_value": 1.0,
            "confidence": 0.65,
            "target_date": "2025-02-01"
        })
        assert response.status_code == 200

    def test_submit_price_target_prediction(self):
        response = client.post("/leaderboard/predict", json={
            "user_id": "test_user_003",
            "ticker": "MSFT",
            "prediction_type": "price_target",
            "predicted_value": 450.0,
            "confidence": 0.70,
            "target_date": "2025-03-01"
        })
        assert response.status_code == 200

    def test_invalid_confidence_rejected(self):
        # Confidence must be between 0 and 1 exclusive
        response = client.post("/leaderboard/predict", json={
            "user_id": "test_user",
            "ticker": "TSLA",
            "prediction_type": "direction",
            "predicted_value": 1.0,
            "confidence": 1.5,  # Invalid
            "target_date": "2025-01-01"
        })
        assert response.status_code == 400


# ── Resolve Prediction Tests ─────────────────────────────────────────────────

class TestResolvePrediction:
    """Tests for POST /leaderboard/resolve."""

    def test_resolve_prediction(self):
        # First submit a prediction
        submit = client.post("/leaderboard/predict", json={
            "user_id": "resolve_test_user",
            "ticker": "GOOGL",
            "prediction_type": "earnings_beat",
            "predicted_value": 1.0,
            "confidence": 0.80,
            "target_date": "2025-01-20"
        })
        assert submit.status_code == 200
        prediction_id = submit.json()["id"]

        # Resolve it
        response = client.post("/leaderboard/resolve", json={
            "prediction_id": prediction_id,
            "actual_value": 1.0
        })
        assert response.status_code == 200

        data = response.json()
        assert data["outcome"] is not None
        assert data["brier_score"] is not None

    def test_resolve_nonexistent_fails(self):
        response = client.post("/leaderboard/resolve", json={
            "prediction_id": "nonexistent_prediction_12345",
            "actual_value": 1.0
        })
        assert response.status_code == 404


# ── Submit Idea Tests ────────────────────────────────────────────────────────

class TestSubmitIdea:
    """Tests for POST /leaderboard/idea."""

    def test_submit_long_idea(self):
        response = client.post("/leaderboard/idea", json={
            "user_id": "idea_user_001",
            "ticker": "NVDA",
            "direction": "long",
            "thesis": "AI demand continues to grow",
            "entry_price": 500.0,
            "target_price": 600.0,
            "stop_price": 450.0,
            "time_horizon_days": 30
        })
        assert response.status_code == 200

        data = response.json()
        assert data["direction"] == "long"
        assert data["ticker"] == "NVDA"

    def test_submit_short_idea(self):
        response = client.post("/leaderboard/idea", json={
            "user_id": "idea_user_002",
            "ticker": "GME",
            "direction": "short",
            "thesis": "Meme stock deflation",
            "entry_price": 20.0,
            "target_price": 10.0,
            "stop_price": 25.0,
            "time_horizon_days": 60
        })
        assert response.status_code == 200

        data = response.json()
        assert data["direction"] == "short"

    def test_invalid_direction_rejected(self):
        response = client.post("/leaderboard/idea", json={
            "user_id": "idea_user",
            "ticker": "AAPL",
            "direction": "invalid",  # Invalid
            "thesis": "Test",
            "entry_price": 150.0,
            "target_price": 180.0,
            "stop_price": 140.0
        })
        assert response.status_code == 400


# ── User Score Tests ─────────────────────────────────────────────────────────

class TestUserScore:
    """Tests for GET /leaderboard/user/{user_id}."""

    def test_get_user_score(self):
        # First submit a prediction to create user
        client.post("/leaderboard/predict", json={
            "user_id": "score_test_user",
            "ticker": "AAPL",
            "prediction_type": "direction",
            "predicted_value": 1.0,
            "confidence": 0.60,
            "target_date": "2025-02-01"
        })

        response = client.get("/leaderboard/user/score_test_user")
        assert response.status_code == 200

        data = response.json()
        assert "user_id" in data
        assert "total_predictions" in data
        assert "tier" in data

    def test_user_score_has_metrics(self):
        response = client.get("/leaderboard/user/score_test_user")
        if response.status_code == 200:
            data = response.json()
            assert "accuracy_rate" in data
            assert "avg_brier_score" in data

    def test_nonexistent_user(self):
        response = client.get("/leaderboard/user/definitely_not_a_user_12345")
        assert response.status_code == 404


# ── Calibration Tests ────────────────────────────────────────────────────────

class TestCalibration:
    """Tests for GET /leaderboard/calibration/{user_id}."""

    def test_get_calibration(self):
        # Create user with prediction
        client.post("/leaderboard/predict", json={
            "user_id": "calib_test_user",
            "ticker": "META",
            "prediction_type": "direction",
            "predicted_value": 1.0,
            "confidence": 0.70,
            "target_date": "2025-03-01"
        })

        response = client.get("/leaderboard/calibration/calib_test_user")
        assert response.status_code == 200


# ── Tier Definitions Tests ───────────────────────────────────────────────────

class TestTierDefinitions:
    """Tests for GET /leaderboard/tiers."""

    def test_get_tiers(self):
        response = client.get("/leaderboard/tiers")
        assert response.status_code == 200

        data = response.json()
        assert "tiers" in data
        assert "scoring" in data

    def test_tiers_have_required_fields(self):
        response = client.get("/leaderboard/tiers")
        data = response.json()

        for tier in data["tiers"]:
            assert "name" in tier
            assert "threshold" in tier
            assert "description" in tier

    def test_tiers_include_expected_levels(self):
        response = client.get("/leaderboard/tiers")
        data = response.json()

        tier_names = [t["name"] for t in data["tiers"]]
        assert "elite" in tier_names
        assert "novice" in tier_names
