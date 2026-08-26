"""
Tests for app.api.analysts API endpoints (Band B #24, #29)
--------------------------------------------------------------------------------
Tests the FastAPI endpoints using REAL Finnhub data:
  - /analysts/search - Analyst search (#29)
  - /analysts/profile/{id} - Analyst profiles (#29)
  - /analysts/score/{id} - Accuracy scoring (#24)
  - /analysts/ranking - Leaderboards
  - /analysts/compare - Side-by-side comparison
  - /analysts/consensus/{ticker} - Comprehensive consensus data
  - /analysts/info - Service information

Note: Tests use real API calls when FINNHUB_API_KEY is set.
"""
from __future__ import annotations

import os
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Check if Finnhub API key is configured
HAS_FINNHUB_KEY = bool(os.environ.get("FINNHUB_API_KEY"))

# Test ticker that should have analyst coverage
TEST_TICKER = "AAPL"


# ── Search Endpoint Tests ────────────────────────────────────────────────────

class TestAnalystSearch:
    """Tests for GET /analysts/search."""

    def test_search_no_params(self):
        """Search without params returns empty list (needs ticker parameter)."""
        response = client.get("/analysts/search")
        assert response.status_code == 200

        data = response.json()
        assert "analysts" in data
        assert "total" in data
        # Without ticker, returns empty (Finnhub requires ticker for lookup)
        assert data["total"] == 0

    @pytest.mark.skipif(not HAS_FINNHUB_KEY, reason="FINNHUB_API_KEY not set")
    def test_search_by_ticker(self):
        """Search by ticker returns analysts covering that stock."""
        response = client.get(f"/analysts/search?ticker={TEST_TICKER}")
        assert response.status_code == 200

        data = response.json()
        assert "analysts" in data
        assert data["filters"]["ticker"] == TEST_TICKER

    def test_search_filters_preserved(self):
        """Search filters are returned in response."""
        response = client.get("/analysts/search?firm=Goldman&sector=Technology")
        assert response.status_code == 200

        data = response.json()
        assert data["filters"]["firm"] == "Goldman"
        assert data["filters"]["sector"] == "Technology"


# ── Profile Endpoint Tests (#29) ─────────────────────────────────────────────

class TestAnalystProfile:
    """Tests for GET /analysts/profile/{analyst_id} - Band B #29."""

    @pytest.mark.skipif(not HAS_FINNHUB_KEY, reason="FINNHUB_API_KEY not set")
    def test_get_profile_by_ticker(self):
        """Get profile using ticker as analyst_id."""
        response = client.get(f"/analysts/profile/{TEST_TICKER}")

        # May return 200 or 404 depending on data availability
        if response.status_code == 200:
            data = response.json()
            assert "analyst_id" in data
            assert "analyst_name" in data
            assert "firm" in data

    def test_profile_not_found(self):
        """Invalid analyst ID returns 404."""
        response = client.get("/analysts/profile/INVALID_XYZ123")
        assert response.status_code == 404


# ── Score Endpoint Tests (#24) ───────────────────────────────────────────────

class TestAnalystScore:
    """Tests for GET /analysts/score/{analyst_id} - Band B #24."""

    @pytest.mark.skipif(not HAS_FINNHUB_KEY, reason="FINNHUB_API_KEY not set")
    def test_get_score_by_ticker(self):
        """Get accuracy score using ticker as analyst_id."""
        response = client.get(f"/analysts/score/{TEST_TICKER}")

        if response.status_code == 200:
            data = response.json()
            assert "analyst_id" in data
            assert "overall_score" in data
            assert "tier" in data

    def test_score_not_found(self):
        """Invalid analyst ID returns 404."""
        response = client.get("/analysts/score/INVALID_XYZ123")
        assert response.status_code == 404


# ── History Endpoint Tests ───────────────────────────────────────────────────

class TestAnalystHistory:
    """Tests for GET /analysts/history/{analyst_id}."""

    def test_get_history(self):
        """Get analyst history returns list."""
        response = client.get(f"/analysts/history/{TEST_TICKER}")
        assert response.status_code == 200

        data = response.json()
        assert data["analyst_id"] == TEST_TICKER
        assert "estimates" in data
        assert isinstance(data["estimates"], list)

    def test_history_limit(self):
        """History limit parameter works."""
        response = client.get(f"/analysts/history/{TEST_TICKER}?limit=5")
        data = response.json()
        assert len(data["estimates"]) <= 5


# ── Ranking Endpoint Tests ───────────────────────────────────────────────────

class TestAnalystRanking:
    """Tests for GET /analysts/ranking."""

    def test_get_ranking(self):
        """Get analyst ranking returns list."""
        response = client.get("/analysts/ranking")
        assert response.status_code == 200

        data = response.json()
        assert "ranking" in data
        assert "total" in data
        assert isinstance(data["ranking"], list)

    def test_ranking_filters(self):
        """Ranking filters are preserved in response."""
        response = client.get("/analysts/ranking?sector=Technology&firm=Goldman")
        assert response.status_code == 200

        data = response.json()
        assert data["filters"]["sector"] == "Technology"
        assert data["filters"]["firm"] == "Goldman"

    def test_ranking_limit(self):
        """Ranking limit parameter works."""
        response = client.get("/analysts/ranking?limit=5")
        data = response.json()
        assert len(data["ranking"]) <= 5


# ── Firm Ranking Endpoint Tests ──────────────────────────────────────────────

class TestFirmRanking:
    """Tests for GET /analysts/ranking/firms."""

    def test_get_firm_ranking(self):
        """Get firm ranking returns list."""
        response = client.get("/analysts/ranking/firms")
        assert response.status_code == 200

        data = response.json()
        assert "ranking" in data
        assert "total_firms" in data
        assert isinstance(data["ranking"], list)


# ── Sector Ranking Endpoint Tests ────────────────────────────────────────────

class TestSectorRanking:
    """Tests for GET /analysts/ranking/sector/{sector}."""

    def test_get_sector_ranking(self):
        """Get sector ranking returns structure."""
        response = client.get("/analysts/ranking/sector/Technology")
        assert response.status_code == 200

        data = response.json()
        # Response is sector_ranking_to_dict output
        assert "sector" in data or "analysts" in data


# ── By Ticker Endpoint Tests ─────────────────────────────────────────────────

class TestTickerCoverage:
    """Tests for GET /analysts/by-ticker/{ticker}."""

    def test_get_ticker_coverage(self):
        """Get ticker coverage returns structure."""
        response = client.get(f"/analysts/by-ticker/{TEST_TICKER}")
        assert response.status_code == 200

        data = response.json()
        assert data["ticker"] == TEST_TICKER
        assert "analysts" in data
        assert "total" in data

    def test_ticker_coverage_structure(self):
        """Ticker coverage returns proper structure."""
        response = client.get("/analysts/by-ticker/MSFT")
        data = response.json()

        assert data["ticker"] == "MSFT"
        assert isinstance(data["analysts"], list)


# ── Compare Endpoint Tests ───────────────────────────────────────────────────

class TestCompareAnalysts:
    """Tests for GET /analysts/compare."""

    def test_compare_needs_two(self):
        """Compare with single ID returns 400."""
        response = client.get("/analysts/compare?analyst_ids=AAPL")
        assert response.status_code == 400

    def test_compare_returns_structure(self):
        """Compare returns proper structure."""
        response = client.get("/analysts/compare?analyst_ids=AAPL,MSFT")
        assert response.status_code == 200

        data = response.json()
        assert "comparison" in data
        assert "leader" in data


# ── Full Profile Endpoint Tests ──────────────────────────────────────────────

class TestFullProfile:
    """Tests for GET /analysts/full/{analyst_id}."""

    @pytest.mark.skipif(not HAS_FINNHUB_KEY, reason="FINNHUB_API_KEY not set")
    def test_get_full_profile(self):
        """Get full profile returns combined data."""
        response = client.get(f"/analysts/full/{TEST_TICKER}")

        if response.status_code == 200:
            data = response.json()
            assert "profile" in data
            assert "score" in data
            assert "recent_estimates" in data

    def test_full_profile_not_found(self):
        """Invalid ID returns 404."""
        response = client.get("/analysts/full/INVALID_XYZ123")
        assert response.status_code == 404


# ── Rating Changes Endpoint Tests (#36) ──────────────────────────────────────

class TestRatingChanges:
    """Tests for GET /analysts/ratings/{ticker} - Band C #36."""

    def test_get_rating_changes(self):
        """Get rating changes returns structure."""
        response = client.get(f"/analysts/ratings/{TEST_TICKER}")
        assert response.status_code == 200

        data = response.json()
        assert data["ticker"] == TEST_TICKER
        assert "summary" in data
        assert "changes" in data

    def test_rating_changes_summary(self):
        """Rating changes summary has required fields."""
        response = client.get("/analysts/ratings/MSFT")
        data = response.json()

        summary = data["summary"]
        assert "total_changes" in summary
        assert "upgrades" in summary
        assert "downgrades" in summary
        assert "initiations" in summary
        assert "net_sentiment" in summary

    def test_rating_changes_with_days(self):
        """Rating changes days parameter works."""
        response = client.get("/analysts/ratings/AAPL?days=30")
        assert response.status_code == 200

        data = response.json()
        assert data["days"] == 30

    @pytest.mark.skipif(not HAS_FINNHUB_KEY, reason="FINNHUB_API_KEY not set")
    def test_rating_change_fields(self):
        """Rating changes have required fields."""
        response = client.get(f"/analysts/ratings/{TEST_TICKER}?days=365")
        data = response.json()

        if data["changes"]:
            change = data["changes"][0]
            assert "ticker" in change
            assert "firm" in change
            assert "action" in change
            assert "date" in change


# ── Price Target History Endpoint Tests (#36) ────────────────────────────────

class TestPriceTargetHistory:
    """Tests for GET /analysts/price-targets/{ticker} - Band C #36."""

    def test_get_price_targets(self):
        """Get price targets returns structure."""
        response = client.get(f"/analysts/price-targets/{TEST_TICKER}")
        assert response.status_code == 200

        data = response.json()
        assert data["ticker"] == TEST_TICKER
        assert "consensus_target" in data
        assert "source" in data
        assert data["source"] == "Finnhub"

    def test_price_target_fields(self):
        """Price targets have required fields."""
        response = client.get("/analysts/price-targets/MSFT")
        data = response.json()

        assert "high_target" in data
        assert "low_target" in data
        assert "median_target" in data
        assert "num_analysts" in data


# ── Rating Distribution Endpoint Tests (#36) ─────────────────────────────────

class TestRatingDistribution:
    """Tests for GET /analysts/distribution/{ticker} - Band C #36."""

    def test_get_distribution(self):
        """Get distribution returns structure."""
        response = client.get(f"/analysts/distribution/{TEST_TICKER}")
        assert response.status_code == 200

        data = response.json()
        assert data["ticker"] == TEST_TICKER
        assert "source" in data
        assert data["source"] == "Finnhub"

    @pytest.mark.skipif(not HAS_FINNHUB_KEY, reason="FINNHUB_API_KEY not set")
    def test_distribution_breakdown(self):
        """Distribution has buy/hold/sell breakdown."""
        response = client.get(f"/analysts/distribution/{TEST_TICKER}")
        data = response.json()

        assert "strong_buy" in data
        assert "buy" in data
        assert "hold" in data
        assert "sell" in data
        assert "strong_sell" in data
        assert "total_analysts" in data
        assert "consensus" in data
        assert "consensus_score" in data


# ── Analyst Rating History Endpoint Tests (#36) ──────────────────────────────

class TestAnalystRatingHistory:
    """Tests for GET /analysts/rating-history/{analyst_id} - Band C #36."""

    def test_get_analyst_rating_history(self):
        """Get analyst rating history returns structure."""
        response = client.get(f"/analysts/rating-history/{TEST_TICKER}")
        assert response.status_code == 200

        data = response.json()
        assert data["analyst_id"] == TEST_TICKER
        assert "ratings" in data
        assert "total" in data

    def test_rating_history_limit(self):
        """Rating history limit parameter works."""
        response = client.get(f"/analysts/rating-history/{TEST_TICKER}?limit=5")
        data = response.json()
        assert len(data["ratings"]) <= 5


# ── Ticker Analyst Summary Endpoint Tests (#36) ──────────────────────────────

class TestTickerAnalystSummary:
    """Tests for GET /analysts/summary/{ticker} - Band C #36."""

    def test_get_summary(self):
        """Get summary returns structure."""
        response = client.get(f"/analysts/summary/{TEST_TICKER}")
        assert response.status_code == 200

        data = response.json()
        assert data["ticker"] == TEST_TICKER
        assert "coverage" in data
        assert "ratings" in data
        assert "price_targets" in data
        assert "recent_activity" in data

    def test_summary_coverage(self):
        """Summary coverage has required fields."""
        response = client.get("/analysts/summary/MSFT")
        data = response.json()

        coverage = data["coverage"]
        assert "total_analysts" in coverage

    def test_summary_price_targets(self):
        """Summary price targets has required fields."""
        response = client.get("/analysts/summary/GOOGL")
        data = response.json()

        pt = data["price_targets"]
        assert "consensus" in pt
        assert "high" in pt
        assert "low" in pt


# ── Consensus Endpoint Tests ─────────────────────────────────────────────────

class TestConsensus:
    """Tests for GET /analysts/consensus/{ticker}."""

    @pytest.mark.skipif(not HAS_FINNHUB_KEY, reason="FINNHUB_API_KEY not set")
    def test_get_consensus(self):
        """Get consensus returns comprehensive data."""
        response = client.get(f"/analysts/consensus/{TEST_TICKER}")

        if response.status_code == 200:
            data = response.json()
            assert data["ticker"] == TEST_TICKER
            assert "recommendation" in data
            assert "price_target" in data
            assert "recent_changes" in data
            assert "consensus_score" in data
            assert "sentiment" in data
            assert "source" in data
            assert data["source"] == "Finnhub"

    def test_consensus_not_found(self):
        """Invalid ticker returns 404."""
        response = client.get("/analysts/consensus/INVALID_XYZ123")
        # Should return 404 (entity not found) or 503 (service unavailable)
        assert response.status_code in [404, 503]


# ── Service Info Endpoint Tests ──────────────────────────────────────────────

class TestServiceInfo:
    """Tests for GET /analysts/info."""

    def test_get_service_info(self):
        """Get service info returns metadata."""
        response = client.get("/analysts/info")
        assert response.status_code == 200

        data = response.json()
        assert data["service"] == "analyst_scoring"
        assert data["source"] == "Finnhub"
        assert "api_key_configured" in data
        assert "cache_ttl_seconds" in data
        assert "endpoints_used" in data
        assert "features" in data

    def test_service_info_key_status(self):
        """Service info shows API key status."""
        response = client.get("/analysts/info")
        data = response.json()

        assert data["api_key_configured"] == HAS_FINNHUB_KEY


# ── Integration Tests ────────────────────────────────────────────────────────

@pytest.mark.skipif(not HAS_FINNHUB_KEY, reason="FINNHUB_API_KEY not set")
class TestIntegration:
    """Integration tests requiring live API access."""

    def test_full_analyst_flow(self):
        """Test the complete flow for a major ticker."""
        ticker = "AAPL"

        # Get consensus
        response = client.get(f"/analysts/consensus/{ticker}")
        if response.status_code == 200:
            data = response.json()
            assert data["ticker"] == ticker
            assert 0 <= data["consensus_score"] <= 100

        # Get distribution
        response = client.get(f"/analysts/distribution/{ticker}")
        assert response.status_code == 200

        # Get summary
        response = client.get(f"/analysts/summary/{ticker}")
        assert response.status_code == 200

    def test_multiple_tickers(self):
        """Test multiple tickers work correctly."""
        tickers = ["AAPL", "MSFT", "GOOGL"]

        for ticker in tickers:
            response = client.get(f"/analysts/distribution/{ticker}")
            assert response.status_code == 200
            data = response.json()
            assert data["ticker"] == ticker
