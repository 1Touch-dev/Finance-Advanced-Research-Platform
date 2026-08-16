"""
Tests for app.services.guidance_service (Band B #22)
────────────────────────────────────────────────────────────────────────────
Covers:
  - Guidance vs actual tracking
  - Management credibility scoring
  - Historical guidance records
  - Guidance revisions
"""
from __future__ import annotations

import pytest
from datetime import date

from app.services.guidance_service import (
    # Enums
    GuidanceMetric,
    GuidanceOutcome,
    CredibilityTier,
    # Functions
    get_current_guidance,
    get_guidance_vs_actual,
    get_guidance_history,
    get_guidance_revisions,
    calculate_management_credibility,
    # Serializers
    guidance_record_to_dict,
    vs_actual_to_dict,
    credibility_to_dict,
)


# ── Current Guidance Tests ────────────────────────────────────────────────────

class TestCurrentGuidance:
    """Tests for current guidance retrieval."""

    def test_get_current_guidance_returns_list(self):
        guidance = get_current_guidance("NVDA", GuidanceMetric.EPS)

        assert isinstance(guidance, list)
        assert len(guidance) > 0

    def test_current_guidance_has_ticker(self):
        guidance = get_current_guidance("AAPL", GuidanceMetric.REVENUE)

        assert len(guidance) > 0
        assert guidance[0].ticker == "AAPL"

    def test_current_guidance_has_range(self):
        guidance = get_current_guidance("MSFT", GuidanceMetric.EPS)

        record = guidance[0]
        assert record.guidance_low is not None
        assert record.guidance_high is not None
        assert record.guidance_low <= record.guidance_high

    def test_current_guidance_multiple_metrics(self):
        for metric in [GuidanceMetric.EPS, GuidanceMetric.REVENUE]:
            guidance = get_current_guidance("NVDA", metric)
            assert len(guidance) > 0
            assert guidance[0].metric == metric

    def test_current_guidance_serialization(self):
        guidance = get_current_guidance("NVDA", GuidanceMetric.EPS)
        data = guidance_record_to_dict(guidance[0])

        assert "ticker" in data
        assert "metric" in data
        assert "guidance_low" in data
        assert "guidance_high" in data

    def test_current_guidance_unknown_ticker_raises(self):
        with pytest.raises(ValueError):
            get_current_guidance("UNKNOWNTICKER", GuidanceMetric.EPS)


# ── Guidance vs Actual Tests (#22) ────────────────────────────────────────────

class TestGuidanceVsActual:
    """Tests for guidance vs actual comparison - Band B #22."""

    def test_vs_actual_basic(self):
        result = get_guidance_vs_actual("NVDA", 2024, "Q4", GuidanceMetric.EPS)

        assert result is not None
        assert result.ticker == "NVDA"
        assert result.fiscal_year == 2024
        assert result.fiscal_period == "Q4"

    def test_vs_actual_has_both_values(self):
        result = get_guidance_vs_actual("AAPL", 2024, "Q3", GuidanceMetric.EPS)

        assert result.guidance_midpoint is not None
        assert result.actual_value is not None
        assert result.vs_midpoint_pct is not None

    def test_vs_actual_has_outcome(self):
        result = get_guidance_vs_actual("MSFT", 2024, "Q2", GuidanceMetric.REVENUE)

        assert result.outcome in [
            GuidanceOutcome.BEAT,
            GuidanceOutcome.SIGNIFICANTLY_BEAT,
            GuidanceOutcome.MET,
            GuidanceOutcome.MISSED,
            GuidanceOutcome.SIGNIFICANTLY_MISSED,
        ]

    def test_vs_actual_serialization(self):
        result = get_guidance_vs_actual("META", 2024, "Q1", GuidanceMetric.EPS)
        data = vs_actual_to_dict(result)

        assert "ticker" in data
        assert "guidance" in data
        assert "midpoint" in data["guidance"]
        assert "actual" in data
        assert "outcome" in data


# ── Guidance History Tests ────────────────────────────────────────────────────

class TestGuidanceHistory:
    """Tests for historical guidance tracking."""

    def test_history_returns_records(self):
        history = get_guidance_history("NVDA", GuidanceMetric.EPS, quarters=8)

        assert len(history) > 0

    def test_history_has_outcomes(self):
        history = get_guidance_history("MSFT", GuidanceMetric.EPS, quarters=4)

        for record in history:
            assert record.guidance_midpoint is not None
            assert record.actual_value is not None


# ── Guidance Revisions Tests ──────────────────────────────────────────────────

class TestGuidanceRevisions:
    """Tests for guidance revision tracking."""

    def test_revisions_returns_list(self):
        revisions = get_guidance_revisions("NVDA", 2024)

        assert isinstance(revisions, list)

    def test_revisions_have_direction(self):
        revisions = get_guidance_revisions("AAPL", 2024)

        for rev in revisions:
            assert rev.direction.value in ["raised", "lowered", "narrowed", "widened", "maintained"]


# ── Management Credibility Tests ──────────────────────────────────────────────

class TestManagementCredibility:
    """Tests for management credibility scoring."""

    def test_credibility_basic(self):
        cred = calculate_management_credibility("NVDA")

        assert cred is not None
        assert cred.ticker == "NVDA"

    def test_credibility_has_score(self):
        cred = calculate_management_credibility("AAPL")

        assert 0 <= cred.credibility_score <= 100
        assert cred.credibility_tier in [
            CredibilityTier.EXCELLENT,
            CredibilityTier.GOOD,
            CredibilityTier.AVERAGE,
            CredibilityTier.POOR,
            CredibilityTier.UNRELIABLE,
        ]

    def test_credibility_has_rates(self):
        cred = calculate_management_credibility("MSFT")

        assert 0 <= cred.meet_or_beat_rate <= 100
        assert 0 <= cred.beat_rate <= 100
        assert cred.total_guidance_periods > 0

    def test_credibility_serialization(self):
        cred = calculate_management_credibility("META")
        data = credibility_to_dict(cred)

        assert "ticker" in data
        assert "overall_score" in data
        assert "tier" in data
        assert "historical_stats" in data
        assert "meet_or_beat_rate" in data["historical_stats"]


# ── Multi-Ticker Tests ────────────────────────────────────────────────────────

class TestMultipleTickers:
    """Test functionality across multiple tickers."""

    @pytest.mark.parametrize("ticker", ["NVDA", "AAPL", "MSFT", "META", "TSLA"])
    def test_current_guidance_exists(self, ticker):
        guidance = get_current_guidance(ticker, GuidanceMetric.EPS)
        assert len(guidance) > 0
        assert guidance[0].ticker == ticker

    @pytest.mark.parametrize("ticker", ["NVDA", "AAPL", "MSFT", "META", "TSLA"])
    def test_credibility_calculable(self, ticker):
        cred = calculate_management_credibility(ticker)
        assert cred.credibility_score >= 0
