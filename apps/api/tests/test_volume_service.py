"""
Tests for app.services.volume_screening_service (Band B #28)
────────────────────────────────────────────────────────────────────────────
Covers:
  - Unusual volume screening
  - Volume profile analysis
  - Sector volume flow
  - Volume alerts
"""
from __future__ import annotations

import pytest
from datetime import date

from app.services.volume_screening_service import (
    # Enums
    VolumeSignal,
    PriceVolumePattern,
    # Functions
    get_volume_bar,
    get_volume_history,
    screen_unusual_volume,
    get_ticker_volume_profile,
    get_sector_volume_flow,
    # Serializers
    volume_bar_to_dict,
    profile_to_dict,
    sector_flow_to_dict,
)


# ── Volume Bar Tests ──────────────────────────────────────────────────────────

class TestVolumeBar:
    """Tests for single volume bar retrieval."""

    def test_get_volume_bar_basic(self):
        bar = get_volume_bar("NVDA")

        assert bar is not None
        assert bar.ticker == "NVDA"

    def test_volume_bar_has_data(self):
        bar = get_volume_bar("AAPL")

        assert bar.volume > 0
        assert bar.avg_volume_20d > 0
        assert bar.avg_volume_50d > 0
        assert bar.volume_ratio > 0

    def test_volume_bar_has_signal(self):
        bar = get_volume_bar("MSFT")

        assert bar.signal in [
            VolumeSignal.EXTREME_SPIKE,
            VolumeSignal.HIGH_VOLUME,
            VolumeSignal.ELEVATED,
            VolumeSignal.NORMAL,
            VolumeSignal.LOW,
            VolumeSignal.EXTREME_LOW,
        ]

    def test_volume_bar_serialization(self):
        bar = get_volume_bar("NVDA")
        data = volume_bar_to_dict(bar)

        assert "ticker" in data
        assert "volume" in data
        assert "avg_volume_20d" in data
        assert "volume_ratio" in data
        assert "signal" in data


# ── Volume History Tests ──────────────────────────────────────────────────────

class TestVolumeHistory:
    """Tests for volume history retrieval."""

    def test_history_returns_bars(self):
        history = get_volume_history("NVDA", days=20)

        assert len(history) > 0

    def test_history_respects_limit(self):
        history = get_volume_history("AAPL", days=10)

        # May be fewer due to weekend exclusion
        assert len(history) <= 10

    def test_history_bars_have_dates(self):
        history = get_volume_history("MSFT", days=5)

        for bar in history:
            assert bar.date is not None
            assert bar.volume > 0


# ── Unusual Volume Screening Tests (#28) ──────────────────────────────────────

class TestUnusualVolumeScreening:
    """Tests for unusual volume screening - Band B #28."""

    def test_screen_returns_results(self):
        results = screen_unusual_volume(min_ratio=1.5)

        assert results is not None
        assert hasattr(results, 'alerts')
        assert isinstance(results.alerts, list)

    def test_screen_filters_by_ratio(self):
        # Higher threshold should have higher ratio alerts
        results = screen_unusual_volume(min_ratio=2.5)

        for alert in results.alerts:
            assert alert.volume_ratio >= 2.5

    def test_screen_results_sorted(self):
        results = screen_unusual_volume(min_ratio=1.5)

        if len(results.alerts) > 1:
            for i in range(1, len(results.alerts)):
                assert results.alerts[i].volume_ratio <= results.alerts[i-1].volume_ratio

    def test_screen_has_summary(self):
        results = screen_unusual_volume(min_ratio=2.0)

        assert results.total_screened > 0
        assert results.alerts_count >= 0
        assert results.extreme_spikes >= 0
        assert results.high_volume >= 0


# ── Volume Profile Tests ──────────────────────────────────────────────────────

class TestVolumeProfile:
    """Tests for ticker volume profile analysis."""

    def test_profile_basic(self):
        profile = get_ticker_volume_profile("NVDA")

        assert profile is not None
        assert profile.ticker == "NVDA"

    def test_profile_has_averages(self):
        profile = get_ticker_volume_profile("AAPL")

        assert profile.avg_volume_20d > 0
        assert profile.avg_volume_50d > 0
        assert profile.latest_ratio > 0

    def test_profile_has_statistics(self):
        profile = get_ticker_volume_profile("MSFT")

        assert profile.spikes_30d >= 0
        assert profile.spikes_90d >= 0
        assert profile.volume_trend in ["increasing", "decreasing", "stable"]

    def test_profile_has_recent_bars(self):
        profile = get_ticker_volume_profile("GOOGL")

        assert len(profile.recent_bars) > 0

    def test_profile_serialization(self):
        profile = get_ticker_volume_profile("NVDA")
        data = profile_to_dict(profile)

        assert "ticker" in data
        assert "averages" in data
        assert "20d" in data["averages"]
        assert "patterns" in data
        assert "trend" in data["patterns"]


# ── Sector Volume Flow Tests ──────────────────────────────────────────────────

class TestSectorVolumeFlow:
    """Tests for sector-level volume analysis."""

    def test_sector_flow_basic(self):
        flow = get_sector_volume_flow("Technology")

        assert flow is not None
        assert flow.sector == "Technology"

    def test_sector_flow_has_stats(self):
        flow = get_sector_volume_flow("Technology")

        assert flow.total_volume > 0
        assert flow.volume_vs_avg > 0
        assert flow.tickers_elevated >= 0

    def test_sector_flow_has_top_tickers(self):
        flow = get_sector_volume_flow("Technology")

        assert len(flow.top_volume_tickers) > 0

    def test_sector_flow_has_direction(self):
        flow = get_sector_volume_flow("Technology")

        assert flow.flow_direction in ["bullish", "bearish", "neutral"]

    def test_sector_flow_serialization(self):
        flow = get_sector_volume_flow("Financials")
        data = sector_flow_to_dict(flow)

        assert "sector" in data
        assert "volume" in data
        assert "total" in data["volume"]
        assert "flow" in data
        assert "top_tickers" in data


# ── Multi-Ticker Tests ────────────────────────────────────────────────────────

class TestMultipleTickers:
    """Test functionality across multiple tickers."""

    @pytest.mark.parametrize("ticker", ["NVDA", "AAPL", "MSFT", "GOOGL", "META"])
    def test_volume_bar_exists(self, ticker):
        bar = get_volume_bar(ticker)
        assert bar.ticker == ticker

    @pytest.mark.parametrize("ticker", ["NVDA", "AAPL", "MSFT", "GOOGL", "META"])
    def test_volume_profile_exists(self, ticker):
        profile = get_ticker_volume_profile(ticker)
        assert profile.ticker == ticker


# ── Edge Cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Test edge cases."""

    def test_unknown_ticker_raises(self):
        with pytest.raises(ValueError):
            get_ticker_volume_profile("UNKNOWNTICKER")

    def test_lowercase_ticker_normalized(self):
        bar = get_volume_bar("nvda")
        assert bar.ticker == "NVDA"

    def test_very_high_threshold(self):
        results = screen_unusual_volume(min_ratio=10.0)
        # Might return empty list with very high threshold
        assert results is not None
        assert isinstance(results.alerts, list)
