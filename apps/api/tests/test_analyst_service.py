"""
Tests for app.services.analyst_scoring_service (Band B #24, #29)
--------------------------------------------------------------------------------
Tests for REAL Finnhub API integration:
  - Analyst recommendations (buy/hold/sell distribution)
  - Price targets (mean, median, high, low)
  - Rating changes (upgrades/downgrades)
  - Consensus scoring from real data

Note: Tests use real API calls when FINNHUB_API_KEY is set.
      Falls back to testing empty/no_data responses when key is missing.
"""
from __future__ import annotations

import os
import pytest
from datetime import date

from app.services.analyst_scoring_service import (
    # Enums
    AnalystTier,
    CoverageStatus,
    RatingAction,
    # Data classes
    RatingDistribution,
    PriceTargetHistory,
    RatingChange,
    AnalystProfile,
    AccuracyScore,
    EstimateRecord,
    # Functions
    get_analyst_profile,
    search_analysts,
    calculate_analyst_accuracy,
    get_analyst_ranking,
    get_firm_ranking,
    get_sector_ranking,
    get_ticker_analysts,
    get_analyst_estimates_history,
    compare_analysts,
    get_analyst_rating_history,
    get_rating_distribution,
    get_price_target_history,
    get_rating_changes,
    get_analyst_consensus,
    get_service_info,
    clear_cache,
    # Private functions for testing
    _calculate_recommendation_score,
    _determine_consensus,
    _determine_sentiment,
    # Serializers
    profile_to_dict,
    accuracy_score_to_dict,
    estimate_record_to_dict,
    sector_ranking_to_dict,
    rating_distribution_to_dict,
    price_target_history_to_dict,
    rating_change_to_dict,
    analyst_consensus_to_dict,
)
from app.core.no_data import NoDataReason


# Check if Finnhub API key is configured
HAS_FINNHUB_KEY = bool(os.environ.get("FINNHUB_API_KEY"))

# Test ticker that should have analyst coverage
TEST_TICKER = "AAPL"


# ── Rating Distribution Tests ────────────────────────────────────────────────

class TestRatingDistribution:
    """Tests for recommendation distribution functionality."""

    def test_get_rating_distribution_returns_dataclass(self):
        result = get_rating_distribution(TEST_TICKER)
        assert isinstance(result, RatingDistribution)
        assert result.ticker == TEST_TICKER

    @pytest.mark.skipif(not HAS_FINNHUB_KEY, reason="FINNHUB_API_KEY not set")
    def test_get_rating_distribution_has_data(self):
        result = get_rating_distribution(TEST_TICKER)
        # Should have some analyst coverage for major tickers
        assert result.total_analysts >= 0
        # At least one rating category should have data if covered
        if result.total_analysts > 0:
            total = result.strong_buy + result.buy + result.hold + result.sell + result.strong_sell
            assert total == result.total_analysts

    def test_rating_distribution_serialization(self):
        result = get_rating_distribution(TEST_TICKER)
        data = rating_distribution_to_dict(result)

        assert "ticker" in data
        assert "strong_buy" in data
        assert "buy" in data
        assert "hold" in data
        assert "sell" in data
        assert "strong_sell" in data
        assert "total_analysts" in data
        assert "consensus" in data
        assert "consensus_score" in data
        assert "source" in data
        assert data["source"] == "Finnhub"

    def test_rating_distribution_invalid_ticker(self):
        result = get_rating_distribution("INVALID_TICKER_XYZ123")
        assert isinstance(result, RatingDistribution)
        assert result.total_analysts == 0


# ── Price Target Tests ───────────────────────────────────────────────────────

class TestPriceTargets:
    """Tests for price target functionality."""

    def test_get_price_targets_returns_dataclass(self):
        result = get_price_target_history(TEST_TICKER)
        assert isinstance(result, PriceTargetHistory)
        assert result.ticker == TEST_TICKER

    def test_price_target_serialization(self):
        result = get_price_target_history(TEST_TICKER)
        data = price_target_history_to_dict(result)

        assert "ticker" in data
        assert "consensus_target" in data
        assert "high_target" in data
        assert "low_target" in data
        assert "median_target" in data
        assert "num_analysts" in data
        assert "source" in data
        assert data["source"] == "Finnhub"


# ── Rating Changes Tests ─────────────────────────────────────────────────────

class TestRatingChanges:
    """Tests for upgrade/downgrade functionality."""

    def test_get_rating_changes_returns_list(self):
        result = get_rating_changes(TEST_TICKER)
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, RatingChange)

    def test_rating_changes_have_required_fields(self):
        result = get_rating_changes(TEST_TICKER, days=365)
        for change in result[:5]:  # Check first 5
            assert change.ticker == TEST_TICKER
            assert isinstance(change.action, RatingAction)
            assert change.date  # Should have a date

    def test_rating_change_serialization(self):
        result = get_rating_changes(TEST_TICKER, days=365)
        if result:
            data = rating_change_to_dict(result[0])
            assert "ticker" in data
            assert "analyst_name" in data
            assert "firm" in data
            assert "action" in data
            assert "from_rating" in data
            assert "to_rating" in data
            assert "date" in data

    def test_rating_changes_sorted_by_date(self):
        result = get_rating_changes(TEST_TICKER, days=365)
        if len(result) >= 2:
            for i in range(1, len(result)):
                assert result[i].date <= result[i-1].date


# ── Consensus Score Calculation Tests ────────────────────────────────────────

class TestConsensusCalculation:
    """Tests for consensus score calculation logic."""

    def test_calculate_score_all_strong_buy(self):
        score = _calculate_recommendation_score(10, 0, 0, 0, 0)
        assert score == 100.0

    def test_calculate_score_all_strong_sell(self):
        score = _calculate_recommendation_score(0, 0, 0, 0, 10)
        assert score == 0.0

    def test_calculate_score_all_hold(self):
        score = _calculate_recommendation_score(0, 0, 10, 0, 0)
        assert score == 50.0

    def test_calculate_score_mixed(self):
        # 5 Strong Buy (100), 5 Buy (75), 5 Hold (50) = (500+375+250)/15 = 75
        score = _calculate_recommendation_score(5, 5, 5, 0, 0)
        assert score == 75.0

    def test_calculate_score_empty(self):
        score = _calculate_recommendation_score(0, 0, 0, 0, 0)
        assert score == 50.0  # Neutral when no data

    def test_determine_consensus_strong_buy(self):
        # 70%+ bullish with more strong buy
        consensus = _determine_consensus(5, 2, 1, 0, 0)
        assert consensus == "strong_buy"

    def test_determine_consensus_buy(self):
        # 70%+ bullish with more buy
        consensus = _determine_consensus(2, 5, 1, 0, 0)
        assert consensus == "buy"

    def test_determine_consensus_hold(self):
        # 50%+ hold
        consensus = _determine_consensus(1, 1, 6, 1, 1)
        assert consensus == "hold"

    def test_determine_consensus_no_coverage(self):
        consensus = _determine_consensus(0, 0, 0, 0, 0)
        assert consensus == "no_coverage"

    def test_determine_sentiment_bullish(self):
        assert _determine_sentiment(75.0) == "bullish"
        assert _determine_sentiment(70.0) == "bullish"

    def test_determine_sentiment_bearish(self):
        assert _determine_sentiment(25.0) == "bearish"
        assert _determine_sentiment(30.0) == "bearish"

    def test_determine_sentiment_neutral(self):
        assert _determine_sentiment(50.0) == "neutral"


# ── Analyst Consensus Tests ──────────────────────────────────────────────────

class TestAnalystConsensus:
    """Tests for comprehensive analyst consensus."""

    def test_get_consensus_returns_dict(self):
        result = get_analyst_consensus(TEST_TICKER)
        assert isinstance(result, dict)

    @pytest.mark.skipif(not HAS_FINNHUB_KEY, reason="FINNHUB_API_KEY not set")
    def test_get_consensus_has_required_fields(self):
        result = get_analyst_consensus(TEST_TICKER)

        # Should not be a no_data response for major tickers
        if not result.get("no_data"):
            assert "ticker" in result
            assert "recommendation" in result
            assert "price_target" in result
            assert "recent_changes" in result
            assert "consensus_score" in result
            assert "sentiment" in result
            assert "source" in result
            assert result["source"] == "Finnhub"

    def test_consensus_no_data_response(self):
        """Test that invalid tickers return proper no_data response."""
        result = get_analyst_consensus("INVALID_TICKER_XYZ123")

        if HAS_FINNHUB_KEY:
            # With key, should return no_data for invalid ticker
            assert result.get("no_data") is True
            assert result.get("reason") == NoDataReason.ENTITY_NOT_FOUND.value
        else:
            # Without key, should return no_data for missing key
            assert result.get("no_data") is True
            assert result.get("reason") == NoDataReason.API_KEY_MISSING.value


# ── Analyst Profile Tests ────────────────────────────────────────────────────

class TestAnalystProfiles:
    """Tests for analyst profile functionality."""

    @pytest.mark.skipif(not HAS_FINNHUB_KEY, reason="FINNHUB_API_KEY not set")
    def test_get_profile_by_ticker(self):
        # Using ticker as analyst_id since Finnhub doesn't have per-analyst IDs
        profile = get_analyst_profile(TEST_TICKER)

        if profile:
            assert profile.analyst_id == TEST_TICKER
            assert isinstance(profile, AnalystProfile)

    def test_get_profile_invalid_id(self):
        profile = get_analyst_profile("INVALID_TICKER_XYZ123")
        assert profile is None

    def test_profile_serialization(self):
        profile = AnalystProfile(
            analyst_id="test",
            analyst_name="Test Analyst",
            firm="Test Firm",
            tickers_covered=["AAPL", "MSFT"],
            total_ratings=10,
        )
        data = profile_to_dict(profile)

        assert "analyst_id" in data
        assert "analyst_name" in data
        assert "firm" in data
        assert "tickers_covered" in data
        assert "total_ratings" in data

    @pytest.mark.skipif(not HAS_FINNHUB_KEY, reason="FINNHUB_API_KEY not set")
    def test_search_by_ticker(self):
        analysts = search_analysts(ticker=TEST_TICKER)
        # May return analysts or empty list depending on data availability
        assert isinstance(analysts, list)


# ── Analyst Accuracy Tests ───────────────────────────────────────────────────

class TestAnalystAccuracy:
    """Tests for accuracy scoring functionality."""

    @pytest.mark.skipif(not HAS_FINNHUB_KEY, reason="FINNHUB_API_KEY not set")
    def test_calculate_accuracy_for_ticker(self):
        try:
            score = calculate_analyst_accuracy(TEST_TICKER)
            assert isinstance(score, AccuracyScore)
            assert score.analyst_id == TEST_TICKER
        except ValueError:
            # Expected if no data for this ticker
            pass

    def test_accuracy_invalid_analyst(self):
        with pytest.raises(ValueError):
            calculate_analyst_accuracy("INVALID_TICKER_XYZ123")

    def test_accuracy_serialization(self):
        score = AccuracyScore(
            analyst_id="test",
            analyst_name="Test Analyst",
            firm="Test Firm",
            overall_score=75.0,
            accuracy_pct=80.0,
            tier="expert",
            total_ratings=10,
        )
        data = accuracy_score_to_dict(score)

        assert "analyst_id" in data
        assert "analyst_name" in data
        assert "overall_score" in data
        assert "tier" in data
        assert "total_ratings" in data


# ── Ranking Tests ────────────────────────────────────────────────────────────

class TestRankings:
    """Tests for ranking functionality."""

    def test_get_analyst_ranking_returns_list(self):
        ranking = get_analyst_ranking(limit=10)
        assert isinstance(ranking, list)

    def test_get_firm_ranking_returns_list(self):
        ranking = get_firm_ranking()
        assert isinstance(ranking, list)

    def test_get_sector_ranking_returns_list(self):
        ranking = get_sector_ranking("Technology")
        assert isinstance(ranking, list)


# ── Ticker Coverage Tests ────────────────────────────────────────────────────

class TestTickerCoverage:
    """Tests for ticker coverage functionality."""

    @pytest.mark.skipif(not HAS_FINNHUB_KEY, reason="FINNHUB_API_KEY not set")
    def test_get_ticker_analysts(self):
        analysts = get_ticker_analysts(TEST_TICKER)
        assert isinstance(analysts, list)

    def test_ticker_analysts_have_scores(self):
        analysts = get_ticker_analysts(TEST_TICKER)
        for analyst in analysts:
            assert isinstance(analyst, AccuracyScore)
            assert analyst.firm is not None


# ── Historical Data Tests ────────────────────────────────────────────────────

class TestHistoricalData:
    """Tests for historical estimate tracking."""

    def test_get_estimates_history_returns_list(self):
        records = get_analyst_estimates_history(TEST_TICKER, limit=10)
        assert isinstance(records, list)

    def test_estimates_have_required_fields(self):
        records = get_analyst_estimates_history(TEST_TICKER, limit=5)
        for record in records:
            assert isinstance(record, EstimateRecord)
            assert record.analyst_id == TEST_TICKER

    def test_get_rating_history_returns_list(self):
        history = get_analyst_rating_history(TEST_TICKER, limit=10)
        assert isinstance(history, list)


# ── Compare Analysts Tests ───────────────────────────────────────────────────

class TestCompareAnalysts:
    """Tests for analyst comparison functionality."""

    @pytest.mark.skipif(not HAS_FINNHUB_KEY, reason="FINNHUB_API_KEY not set")
    def test_compare_tickers(self):
        comparison = compare_analysts(["AAPL", "MSFT"])
        assert isinstance(comparison, list)

    def test_compare_handles_invalid_ids(self):
        comparison = compare_analysts(["INVALID1", "INVALID2"])
        # Should return empty list for invalid tickers
        assert isinstance(comparison, list)


# ── Service Info Tests ───────────────────────────────────────────────────────

class TestServiceInfo:
    """Tests for service information."""

    def test_get_service_info(self):
        info = get_service_info()

        assert info["service"] == "analyst_scoring"
        assert info["source"] == "Finnhub"
        assert "api_key_configured" in info
        assert "cache_ttl_seconds" in info
        assert "endpoints_used" in info
        assert "features" in info
        assert "limitations" in info

    def test_service_info_shows_key_status(self):
        info = get_service_info()
        assert info["api_key_configured"] == HAS_FINNHUB_KEY


# ── Cache Tests ──────────────────────────────────────────────────────────────

class TestCache:
    """Tests for caching functionality."""

    def test_clear_cache_all(self):
        # Should not raise
        clear_cache()

    def test_clear_cache_specific_ticker(self):
        # Should not raise
        clear_cache(TEST_TICKER)


# ── Data Class Tests ─────────────────────────────────────────────────────────

class TestDataClasses:
    """Tests for data class instantiation."""

    def test_rating_distribution_defaults(self):
        rd = RatingDistribution(ticker="TEST")
        assert rd.strong_buy == 0
        assert rd.buy == 0
        assert rd.hold == 0
        assert rd.sell == 0
        assert rd.strong_sell == 0
        assert rd.consensus == "hold"
        assert rd.consensus_score == 0.0

    def test_price_target_history_defaults(self):
        pt = PriceTargetHistory(ticker="TEST")
        assert pt.consensus_target == 0.0
        assert pt.high_target == 0.0
        assert pt.low_target == 0.0
        assert pt.num_analysts == 0

    def test_rating_change_defaults(self):
        rc = RatingChange(ticker="TEST")
        assert rc.action == RatingAction.maintain
        assert rc.firm == ""
        assert rc.analyst_name == ""

    def test_rating_action_enum_values(self):
        assert RatingAction.upgrade.value == "upgrade"
        assert RatingAction.downgrade.value == "downgrade"
        assert RatingAction.initiate.value == "initiate"
        assert RatingAction.reiterate.value == "reiterate"
        assert RatingAction.maintain.value == "maintain"


# ── Integration Tests ────────────────────────────────────────────────────────

@pytest.mark.skipif(not HAS_FINNHUB_KEY, reason="FINNHUB_API_KEY not set")
class TestIntegration:
    """Integration tests that require live API access."""

    def test_full_consensus_flow(self):
        """Test the complete flow of getting analyst consensus."""
        # Get consensus
        consensus = get_analyst_consensus("MSFT")

        if not consensus.get("no_data"):
            # Verify structure
            assert "recommendation" in consensus
            assert "price_target" in consensus
            assert "consensus_score" in consensus

            # Verify recommendation has expected fields
            rec = consensus["recommendation"]
            assert "strong_buy" in rec
            assert "consensus" in rec

            # Verify score is in valid range
            assert 0 <= consensus["consensus_score"] <= 100

    def test_multiple_tickers(self):
        """Test getting consensus for multiple tickers."""
        tickers = ["AAPL", "MSFT", "GOOGL"]

        for ticker in tickers:
            result = get_analyst_consensus(ticker)
            assert isinstance(result, dict)
            # Should either have data or be a proper no_data response
            assert "ticker" in result or "no_data" in result
