"""
Tests for app.services.analyst_scoring_service (Band B #24, #29)
────────────────────────────────────────────────────────────────────────────
Covers:
  - Analyst profile retrieval and search (#29)
  - Accuracy scoring and calibration (#24)
  - Sector/firm rankings
  - Historical estimate tracking
"""
from __future__ import annotations

import pytest
from datetime import date

from app.services.analyst_scoring_service import (
    # Enums
    AnalystTier,
    CoverageStatus,
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
    # Serializers
    profile_to_dict,
    accuracy_score_to_dict,
    estimate_record_to_dict,
    sector_ranking_to_dict,
)


# ── Analyst Profile Tests (#29) ───────────────────────────────────────────────

class TestAnalystProfiles:
    """Tests for public analyst profile functionality - Band B #29."""

    def test_get_profile_by_id(self):
        profile = get_analyst_profile("analyst_001")

        assert profile is not None
        assert profile.analyst_id == "analyst_001"
        assert profile.name == "John Smith"
        assert profile.firm == "Goldman Sachs"

    def test_get_profile_invalid_id(self):
        profile = get_analyst_profile("nonexistent_analyst")
        assert profile is None

    def test_profile_has_required_fields(self):
        profile = get_analyst_profile("analyst_001")

        assert profile.analyst_id is not None
        assert profile.name is not None
        assert profile.firm is not None
        assert profile.title is not None
        assert profile.years_experience > 0
        assert len(profile.sectors_covered) > 0
        assert len(profile.tickers_covered) > 0
        assert profile.coverage_status == CoverageStatus.ACTIVE

    def test_profile_serialization(self):
        profile = get_analyst_profile("analyst_001")
        data = profile_to_dict(profile)

        assert "analyst_id" in data
        assert "name" in data
        assert "firm" in data
        assert "title" in data
        assert "years_experience" in data
        assert "sectors_covered" in data
        assert "tickers_covered" in data
        assert "coverage_status" in data

    def test_search_by_firm(self):
        analysts = search_analysts(firm="Goldman")

        assert len(analysts) > 0
        assert all("Goldman" in a.firm for a in analysts)

    def test_search_by_sector(self):
        analysts = search_analysts(sector="Technology")

        assert len(analysts) > 0
        assert all(any("Technology" in s for s in a.sectors_covered) for a in analysts)

    def test_search_by_ticker(self):
        analysts = search_analysts(ticker="NVDA")

        assert len(analysts) > 0
        assert all("NVDA" in a.tickers_covered for a in analysts)

    def test_search_by_name(self):
        analysts = search_analysts(name="John")

        assert len(analysts) > 0
        assert all("John" in a.name for a in analysts)

    def test_search_multiple_filters(self):
        analysts = search_analysts(firm="Goldman", sector="Technology")

        assert len(analysts) > 0
        for a in analysts:
            assert "Goldman" in a.firm
            assert any("Technology" in s for s in a.sectors_covered)


# ── Analyst Accuracy Scoring Tests (#24) ──────────────────────────────────────

class TestAnalystAccuracy:
    """Tests for per-analyst accuracy scoring - Band B #24."""

    def test_calculate_accuracy_basic(self):
        score = calculate_analyst_accuracy("analyst_001")

        assert score.analyst_id == "analyst_001"
        assert score.analyst_name == "John Smith"
        assert score.firm == "Goldman Sachs"

    def test_accuracy_score_bounded(self):
        score = calculate_analyst_accuracy("analyst_001")

        assert 0 <= score.overall_score <= 100
        assert 1 <= score.percentile_rank <= 100

    def test_accuracy_has_metrics(self):
        score = calculate_analyst_accuracy("analyst_001")

        assert score.mean_absolute_error >= 0
        assert 0 <= score.direction_accuracy <= 100
        assert 0 <= score.hit_rate <= 100
        assert 0 <= score.brier_score <= 1

    def test_accuracy_has_calibration(self):
        score = calculate_analyst_accuracy("analyst_001")

        assert score.brier_score >= 0
        assert score.calibration_score >= 0

    def test_accuracy_has_tier(self):
        score = calculate_analyst_accuracy("analyst_001")

        assert score.tier in [
            AnalystTier.STAR,
            AnalystTier.TOP,
            AnalystTier.ABOVE_AVERAGE,
            AnalystTier.AVERAGE,
            AnalystTier.BELOW_AVERAGE,
        ]

    def test_accuracy_has_coverage_stats(self):
        score = calculate_analyst_accuracy("analyst_001")

        assert score.estimates_count > 0
        assert score.tickers_covered > 0
        assert len(score.sectors_covered) > 0

    def test_accuracy_has_expertise(self):
        score = calculate_analyst_accuracy("analyst_001")

        assert isinstance(score.best_sectors, list)
        assert isinstance(score.best_tickers, list)

    def test_accuracy_invalid_analyst(self):
        with pytest.raises(ValueError):
            calculate_analyst_accuracy("nonexistent")

    def test_accuracy_serialization(self):
        score = calculate_analyst_accuracy("analyst_001")
        data = accuracy_score_to_dict(score)

        assert "analyst_id" in data
        assert "overall_score" in data
        assert "tier" in data
        assert "accuracy_metrics" in data
        assert "calibration" in data
        assert "coverage" in data
        assert "expertise" in data


# ── Analyst Ranking Tests ─────────────────────────────────────────────────────

class TestAnalystRanking:
    """Tests for analyst ranking functionality."""

    def test_get_ranking_returns_sorted(self):
        ranking = get_analyst_ranking(limit=10)

        assert len(ranking) > 0
        # Verify sorted by score descending
        for i in range(1, len(ranking)):
            assert ranking[i].overall_score <= ranking[i-1].overall_score

    def test_get_ranking_by_sector(self):
        ranking = get_analyst_ranking(sector="Technology", limit=10)

        assert len(ranking) > 0
        for analyst in ranking:
            assert "Technology" in analyst.sectors_covered

    def test_get_ranking_by_firm(self):
        ranking = get_analyst_ranking(firm="Goldman", limit=10)

        for analyst in ranking:
            assert "Goldman" in analyst.firm

    def test_get_firm_ranking(self):
        ranking = get_firm_ranking()

        assert len(ranking) > 0
        for firm in ranking:
            assert "firm" in firm
            assert "avg_score" in firm
            assert "analyst_count" in firm
            assert "rank" in firm

    def test_firm_ranking_sorted(self):
        ranking = get_firm_ranking()

        for i in range(1, len(ranking)):
            assert ranking[i]["avg_score"] <= ranking[i-1]["avg_score"]

    def test_get_sector_ranking(self):
        ranking = get_sector_ranking("Technology")

        assert ranking.sector == "Technology"
        assert ranking.coverage_count > 0
        assert len(ranking.analysts) > 0

    def test_sector_ranking_serialization(self):
        ranking = get_sector_ranking("Technology")
        data = sector_ranking_to_dict(ranking)

        assert "sector" in data
        assert "avg_sector_score" in data
        assert "best_analyst" in data
        assert "analysts" in data


# ── Ticker Coverage Tests ─────────────────────────────────────────────────────

class TestTickerCoverage:
    """Tests for ticker coverage functionality."""

    def test_get_ticker_analysts(self):
        analysts = get_ticker_analysts("NVDA")

        assert len(analysts) > 0
        # Should be sorted by score
        for i in range(1, len(analysts)):
            assert analysts[i].overall_score <= analysts[i-1].overall_score

    def test_ticker_analysts_have_scores(self):
        analysts = get_ticker_analysts("AAPL")

        for analyst in analysts:
            assert analyst.overall_score >= 0
            assert analyst.tier is not None


# ── Historical Estimates Tests ────────────────────────────────────────────────

class TestHistoricalEstimates:
    """Tests for historical estimate tracking."""

    def test_get_estimates_history(self):
        records = get_analyst_estimates_history("analyst_001", limit=10)

        assert len(records) == 10

    def test_estimates_have_required_fields(self):
        records = get_analyst_estimates_history("analyst_001", limit=5)

        for record in records:
            assert record.analyst_id == "analyst_001"
            assert record.ticker is not None
            assert record.metric is not None
            assert record.estimate_value is not None
            assert record.actual_value is not None
            assert record.error_pct is not None

    def test_estimates_serialization(self):
        records = get_analyst_estimates_history("analyst_001", limit=3)
        data = estimate_record_to_dict(records[0])

        assert "analyst_id" in data
        assert "ticker" in data
        assert "estimate_value" in data
        assert "actual_value" in data
        assert "error_pct" in data

    def test_estimates_invalid_analyst(self):
        with pytest.raises(ValueError):
            get_analyst_estimates_history("nonexistent")


# ── Compare Analysts Tests ────────────────────────────────────────────────────

class TestCompareAnalysts:
    """Tests for analyst comparison functionality."""

    def test_compare_two_analysts(self):
        comparison = compare_analysts(["analyst_001", "analyst_002"])

        assert len(comparison) == 2
        # Should be sorted by score
        assert comparison[0].overall_score >= comparison[1].overall_score

    def test_compare_multiple_analysts(self):
        comparison = compare_analysts(["analyst_001", "analyst_002", "analyst_003"])

        assert len(comparison) == 3

    def test_compare_handles_invalid_ids(self):
        comparison = compare_analysts(["analyst_001", "nonexistent"])

        # Should still return valid ones
        assert len(comparison) >= 1


# ── Multi-Analyst Tests ───────────────────────────────────────────────────────

class TestMultipleAnalysts:
    """Test functionality across multiple analysts."""

    @pytest.mark.parametrize("analyst_id", [
        "analyst_001", "analyst_002", "analyst_003",
        "analyst_004", "analyst_005"
    ])
    def test_profile_exists(self, analyst_id):
        profile = get_analyst_profile(analyst_id)
        assert profile is not None

    @pytest.mark.parametrize("analyst_id", [
        "analyst_001", "analyst_002", "analyst_003",
        "analyst_004", "analyst_005"
    ])
    def test_accuracy_calculable(self, analyst_id):
        score = calculate_analyst_accuracy(analyst_id)
        assert score.overall_score >= 0
