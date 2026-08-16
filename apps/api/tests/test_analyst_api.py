"""
Tests for app.api.analysts API endpoints (Band B #24, #29)
────────────────────────────────────────────────────────────────────────────
Tests the FastAPI endpoints for:
  - /analysts/search - Analyst search (#29)
  - /analysts/profile/{id} - Analyst profiles (#29)
  - /analysts/score/{id} - Accuracy scoring (#24)
  - /analysts/ranking - Leaderboards
  - /analysts/compare - Side-by-side comparison
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── Search Endpoint Tests ─────────────────────────────────────────────────────

class TestAnalystSearch:
    """Tests for GET /analysts/search."""

    def test_search_all(self):
        response = client.get("/analysts/search")
        assert response.status_code == 200

        data = response.json()
        assert "analysts" in data
        assert "total" in data
        assert data["total"] > 0

    def test_search_by_firm(self):
        response = client.get("/analysts/search?firm=Goldman")
        assert response.status_code == 200

        data = response.json()
        assert len(data["analysts"]) > 0
        for analyst in data["analysts"]:
            assert "Goldman" in analyst["firm"]

    def test_search_by_sector(self):
        response = client.get("/analysts/search?sector=Technology")
        assert response.status_code == 200

        data = response.json()
        assert len(data["analysts"]) > 0

    def test_search_by_ticker(self):
        response = client.get("/analysts/search?ticker=NVDA")
        assert response.status_code == 200

        data = response.json()
        assert len(data["analysts"]) > 0
        for analyst in data["analysts"]:
            assert "NVDA" in analyst["tickers_covered"]

    def test_search_by_name(self):
        response = client.get("/analysts/search?name=John")
        assert response.status_code == 200

        data = response.json()
        assert len(data["analysts"]) > 0


# ── Profile Endpoint Tests (#29) ──────────────────────────────────────────────

class TestAnalystProfile:
    """Tests for GET /analysts/profile/{analyst_id} - Band B #29."""

    def test_get_profile(self):
        response = client.get("/analysts/profile/analyst_001")
        assert response.status_code == 200

        data = response.json()
        assert data["analyst_id"] == "analyst_001"
        assert "name" in data
        assert "firm" in data
        assert "title" in data
        assert "sectors_covered" in data

    def test_profile_not_found(self):
        response = client.get("/analysts/profile/nonexistent")
        assert response.status_code == 404


# ── Score Endpoint Tests (#24) ────────────────────────────────────────────────

class TestAnalystScore:
    """Tests for GET /analysts/score/{analyst_id} - Band B #24."""

    def test_get_score(self):
        response = client.get("/analysts/score/analyst_001")
        assert response.status_code == 200

        data = response.json()
        assert data["analyst_id"] == "analyst_001"
        assert "overall_score" in data
        assert "tier" in data
        assert "percentile_rank" in data

    def test_score_has_metrics(self):
        response = client.get("/analysts/score/analyst_001")
        data = response.json()

        assert "accuracy_metrics" in data
        metrics = data["accuracy_metrics"]
        assert "mean_absolute_error" in metrics
        assert "direction_accuracy" in metrics
        assert "hit_rate" in metrics

    def test_score_has_calibration(self):
        response = client.get("/analysts/score/analyst_001")
        data = response.json()

        assert "calibration" in data
        assert "brier_score" in data["calibration"]
        assert "calibration_score" in data["calibration"]

    def test_score_has_expertise(self):
        response = client.get("/analysts/score/analyst_001")
        data = response.json()

        assert "expertise" in data
        assert "best_sectors" in data["expertise"]
        assert "best_tickers" in data["expertise"]

    def test_score_not_found(self):
        response = client.get("/analysts/score/nonexistent")
        assert response.status_code == 404


# ── History Endpoint Tests ────────────────────────────────────────────────────

class TestAnalystHistory:
    """Tests for GET /analysts/history/{analyst_id}."""

    def test_get_history(self):
        response = client.get("/analysts/history/analyst_001")
        assert response.status_code == 200

        data = response.json()
        assert data["analyst_id"] == "analyst_001"
        assert "estimates" in data
        assert len(data["estimates"]) > 0

    def test_history_limit(self):
        response = client.get("/analysts/history/analyst_001?limit=5")
        data = response.json()

        assert len(data["estimates"]) == 5

    def test_history_estimate_fields(self):
        response = client.get("/analysts/history/analyst_001?limit=1")
        data = response.json()

        estimate = data["estimates"][0]
        assert "ticker" in estimate
        assert "estimate_value" in estimate
        assert "actual_value" in estimate
        assert "error_pct" in estimate


# ── Ranking Endpoint Tests ────────────────────────────────────────────────────

class TestAnalystRanking:
    """Tests for GET /analysts/ranking."""

    def test_get_ranking(self):
        response = client.get("/analysts/ranking")
        assert response.status_code == 200

        data = response.json()
        assert "ranking" in data
        assert "total" in data
        assert data["total"] > 0

    def test_ranking_sorted(self):
        response = client.get("/analysts/ranking")
        data = response.json()

        ranking = data["ranking"]
        for i in range(1, len(ranking)):
            assert ranking[i]["overall_score"] <= ranking[i-1]["overall_score"]

    def test_ranking_by_sector(self):
        response = client.get("/analysts/ranking?sector=Technology")
        assert response.status_code == 200

        data = response.json()
        assert data["filters"]["sector"] == "Technology"

    def test_ranking_limit(self):
        response = client.get("/analysts/ranking?limit=5")
        data = response.json()

        assert len(data["ranking"]) <= 5


# ── Firm Ranking Endpoint Tests ───────────────────────────────────────────────

class TestFirmRanking:
    """Tests for GET /analysts/ranking/firms."""

    def test_get_firm_ranking(self):
        response = client.get("/analysts/ranking/firms")
        assert response.status_code == 200

        data = response.json()
        assert "ranking" in data
        assert "total_firms" in data

    def test_firm_ranking_fields(self):
        response = client.get("/analysts/ranking/firms")
        data = response.json()

        firm = data["ranking"][0]
        assert "firm" in firm
        assert "avg_score" in firm
        assert "analyst_count" in firm
        assert "rank" in firm


# ── Sector Ranking Endpoint Tests ─────────────────────────────────────────────

class TestSectorRanking:
    """Tests for GET /analysts/ranking/sector/{sector}."""

    def test_get_sector_ranking(self):
        response = client.get("/analysts/ranking/sector/Technology")
        assert response.status_code == 200

        data = response.json()
        assert data["sector"] == "Technology"
        assert "avg_sector_score" in data
        assert "best_analyst" in data
        assert "analysts" in data


# ── By Ticker Endpoint Tests ──────────────────────────────────────────────────

class TestTickerCoverage:
    """Tests for GET /analysts/by-ticker/{ticker}."""

    def test_get_ticker_coverage(self):
        response = client.get("/analysts/by-ticker/NVDA")
        assert response.status_code == 200

        data = response.json()
        assert data["ticker"] == "NVDA"
        assert "analysts" in data
        assert "total" in data

    def test_ticker_coverage_sorted(self):
        response = client.get("/analysts/by-ticker/AAPL")
        data = response.json()

        analysts = data["analysts"]
        if len(analysts) > 1:
            for i in range(1, len(analysts)):
                assert analysts[i]["overall_score"] <= analysts[i-1]["overall_score"]


# ── Compare Endpoint Tests ────────────────────────────────────────────────────

class TestCompareAnalysts:
    """Tests for GET /analysts/compare."""

    def test_compare_two_analysts(self):
        response = client.get("/analysts/compare?analyst_ids=analyst_001,analyst_002")
        assert response.status_code == 200

        data = response.json()
        assert "comparison" in data
        assert len(data["comparison"]) == 2
        assert "leader" in data

    def test_compare_needs_two(self):
        response = client.get("/analysts/compare?analyst_ids=analyst_001")
        assert response.status_code == 400


# ── Full Profile Endpoint Tests ───────────────────────────────────────────────

class TestFullProfile:
    """Tests for GET /analysts/full/{analyst_id}."""

    def test_get_full_profile(self):
        response = client.get("/analysts/full/analyst_001")
        assert response.status_code == 200

        data = response.json()
        assert "profile" in data
        assert "score" in data
        assert "recent_estimates" in data

    def test_full_profile_not_found(self):
        response = client.get("/analysts/full/nonexistent")
        assert response.status_code == 404


# ── Rating Changes Endpoint Tests (#36) ──────────────────────────────────────

class TestRatingChanges:
    """Tests for GET /analysts/ratings/{ticker} - Band C #36."""

    def test_get_rating_changes(self):
        response = client.get("/analysts/ratings/NVDA")
        assert response.status_code == 200

        data = response.json()
        assert data["ticker"] == "NVDA"
        assert "summary" in data
        assert "changes" in data

    def test_rating_changes_summary(self):
        response = client.get("/analysts/ratings/AAPL")
        data = response.json()

        summary = data["summary"]
        assert "total_changes" in summary
        assert "upgrades" in summary
        assert "downgrades" in summary
        assert "initiations" in summary
        assert "net_sentiment" in summary

    def test_rating_changes_with_days(self):
        response = client.get("/analysts/ratings/MSFT?days=30")
        assert response.status_code == 200

        data = response.json()
        assert data["days"] == 30

    def test_rating_change_fields(self):
        response = client.get("/analysts/ratings/NVDA")
        data = response.json()

        if data["changes"]:
            change = data["changes"][0]
            assert "analyst_name" in change
            assert "firm" in change
            assert "action" in change
            assert "new_rating" in change
            assert "new_target" in change


# ── Price Target History Endpoint Tests (#36) ────────────────────────────────

class TestPriceTargetHistory:
    """Tests for GET /analysts/price-targets/{ticker} - Band C #36."""

    def test_get_price_targets(self):
        response = client.get("/analysts/price-targets/NVDA")
        assert response.status_code == 200

        data = response.json()
        assert data["ticker"] == "NVDA"
        assert "consensus" in data
        assert "target_evolution" in data
        assert "recent_changes" in data

    def test_price_target_consensus(self):
        response = client.get("/analysts/price-targets/AAPL")
        data = response.json()

        consensus = data["consensus"]
        assert "target" in consensus
        assert "upside_pct" in consensus
        assert "high_target" in consensus
        assert "low_target" in consensus
        assert "num_analysts" in consensus

    def test_price_target_evolution(self):
        response = client.get("/analysts/price-targets/MSFT")
        data = response.json()

        evolution = data["target_evolution"]
        assert "target_30d_ago" in evolution
        assert "target_90d_ago" in evolution
        assert "change_30d_pct" in evolution
        assert "change_90d_pct" in evolution


# ── Rating Distribution Endpoint Tests (#36) ─────────────────────────────────

class TestRatingDistribution:
    """Tests for GET /analysts/distribution/{ticker} - Band C #36."""

    def test_get_distribution(self):
        response = client.get("/analysts/distribution/NVDA")
        assert response.status_code == 200

        data = response.json()
        assert data["ticker"] == "NVDA"
        assert "total_analysts" in data
        assert "consensus_rating" in data
        assert "distribution" in data

    def test_distribution_breakdown(self):
        response = client.get("/analysts/distribution/AAPL")
        data = response.json()

        dist = data["distribution"]
        assert "buy" in dist
        assert "hold" in dist
        assert "sell" in dist

        for rating in ["buy", "hold", "sell"]:
            assert "count" in dist[rating]
            assert "pct" in dist[rating]


# ── Analyst Rating History Endpoint Tests (#36) ──────────────────────────────

class TestAnalystRatingHistory:
    """Tests for GET /analysts/rating-history/{analyst_id} - Band C #36."""

    def test_get_analyst_rating_history(self):
        response = client.get("/analysts/rating-history/analyst_001")
        assert response.status_code == 200

        data = response.json()
        assert data["analyst_id"] == "analyst_001"
        assert "ratings" in data
        assert "total" in data

    def test_rating_history_limit(self):
        response = client.get("/analysts/rating-history/analyst_001?limit=5")
        data = response.json()

        assert len(data["ratings"]) <= 5

    def test_rating_history_not_found(self):
        response = client.get("/analysts/rating-history/nonexistent")
        assert response.status_code == 404


# ── Ticker Analyst Summary Endpoint Tests (#36) ──────────────────────────────

class TestTickerAnalystSummary:
    """Tests for GET /analysts/summary/{ticker} - Band C #36."""

    def test_get_summary(self):
        response = client.get("/analysts/summary/NVDA")
        assert response.status_code == 200

        data = response.json()
        assert data["ticker"] == "NVDA"
        assert "coverage" in data
        assert "ratings" in data
        assert "price_targets" in data
        assert "recent_activity" in data

    def test_summary_coverage(self):
        response = client.get("/analysts/summary/AAPL")
        data = response.json()

        coverage = data["coverage"]
        assert "total_analysts" in coverage
        assert "top_rated_analyst" in coverage

    def test_summary_price_targets(self):
        response = client.get("/analysts/summary/MSFT")
        data = response.json()

        pt = data["price_targets"]
        assert "consensus" in pt
        assert "upside_pct" in pt
        assert "high" in pt
        assert "low" in pt
