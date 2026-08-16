"""
Tests for app.api.whisper API endpoints (Band B #25)
--------------------------------------------------------------------------------
Tests the FastAPI endpoints for:
  - /whisper/{ticker} - Get whisper estimate
  - /whisper/{ticker}/snapshot - Quick whisper snapshot
  - /whisper/{ticker}/side-split - Buy-side vs sell-side analysis
  - /whisper/{ticker}/history - Whisper accuracy history
  - /whisper/{ticker}/dispersion - Dispersion by analyst type
  - /whisper/{ticker}/estimates - Estimates by analyst type
  - /whisper/types/* - Reference data
  - /whisper/compare - Compare whispers across tickers
  - /whisper/screen - Screen by whisper characteristics
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# -- Whisper Estimate Tests ---------------------------------------------------

class TestWhisperEstimate:
    """Tests for GET /whisper/{ticker}."""

    def test_whisper_returns_200(self):
        """Endpoint returns 200 for valid ticker."""
        response = client.get("/whisper/NVDA")
        assert response.status_code == 200

    def test_whisper_structure(self):
        """Response has expected structure."""
        response = client.get("/whisper/AAPL")
        data = response.json()

        assert "ticker" in data
        assert "period" in data
        assert "metric" in data
        assert "whisper_value" in data
        assert "consensus_value" in data
        assert "whisper_vs_consensus" in data
        assert "whisper_direction" in data
        assert "whisper_sources" in data
        assert "confidence_score" in data

    def test_whisper_ticker_uppercase(self):
        """Ticker is returned uppercase."""
        response = client.get("/whisper/msft")
        data = response.json()
        assert data["ticker"] == "MSFT"

    def test_whisper_with_period(self):
        """Custom period parameter works."""
        response = client.get("/whisper/NVDA?period=Q1_2025")
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "Q1_2025"

    def test_whisper_with_metric(self):
        """Custom metric parameter works."""
        response = client.get("/whisper/NVDA?metric=revenue")
        assert response.status_code == 200
        data = response.json()
        assert data["metric"] == "revenue"

    def test_whisper_invalid_metric(self):
        """Invalid metric returns 400."""
        response = client.get("/whisper/NVDA?metric=invalid")
        assert response.status_code == 400

    def test_whisper_direction_values(self):
        """Whisper direction is one of expected values."""
        response = client.get("/whisper/TSLA")
        data = response.json()
        assert data["whisper_direction"] in ["above", "below", "inline"]

    def test_whisper_values_positive(self):
        """Whisper and consensus values are positive."""
        response = client.get("/whisper/AMD")
        data = response.json()
        assert data["whisper_value"] > 0
        assert data["consensus_value"] > 0


# -- Whisper Snapshot Tests ---------------------------------------------------

class TestWhisperSnapshot:
    """Tests for GET /whisper/{ticker}/snapshot."""

    def test_snapshot_returns_200(self):
        """Endpoint returns 200."""
        response = client.get("/whisper/NVDA/snapshot")
        assert response.status_code == 200

    def test_snapshot_structure(self):
        """Snapshot has expected structure."""
        response = client.get("/whisper/AAPL/snapshot")
        data = response.json()

        assert "ticker" in data
        assert "eps_whisper" in data
        assert "eps_consensus" in data
        assert "eps_whisper_vs_consensus" in data
        assert "revenue_whisper" in data
        assert "revenue_consensus" in data
        assert "next_earnings_date" in data
        assert "whisper_confidence" in data
        assert "beat_probability" in data

    def test_snapshot_beat_probability_in_range(self):
        """Beat probability is between 0-100."""
        response = client.get("/whisper/MSFT/snapshot")
        data = response.json()
        assert 0 <= data["beat_probability"] <= 100

    def test_snapshot_has_earnings_date(self):
        """Snapshot includes earnings date."""
        response = client.get("/whisper/GOOGL/snapshot")
        data = response.json()
        # Date format YYYY-MM-DD
        assert len(data["next_earnings_date"]) == 10


# -- Side Split Analysis Tests ------------------------------------------------

class TestSideSplitAnalysis:
    """Tests for GET /whisper/{ticker}/side-split."""

    def test_side_split_returns_200(self):
        """Endpoint returns 200."""
        response = client.get("/whisper/NVDA/side-split")
        assert response.status_code == 200

    def test_side_split_structure(self):
        """Side split has expected structure."""
        response = client.get("/whisper/AAPL/side-split")
        data = response.json()

        # Buy-side metrics
        assert "buy_side_count" in data
        assert "buy_side_mean" in data
        assert "buy_side_high" in data
        assert "buy_side_low" in data
        assert "buy_side_std" in data

        # Sell-side metrics
        assert "sell_side_count" in data
        assert "sell_side_mean" in data
        assert "sell_side_high" in data
        assert "sell_side_low" in data
        assert "sell_side_std" in data

        # Comparison
        assert "buy_sell_spread" in data
        assert "buy_sell_spread_pct" in data
        assert "bullish_side" in data
        assert "interpretation" in data

    def test_side_split_has_interpretation(self):
        """Side split includes interpretation."""
        response = client.get("/whisper/MSFT/side-split")
        data = response.json()
        assert len(data["interpretation"]) > 0

    def test_side_split_bullish_side_values(self):
        """Bullish side is one of expected values."""
        response = client.get("/whisper/TSLA/side-split")
        data = response.json()
        assert data["bullish_side"] in ["buy_side", "sell_side", "neutral"]

    def test_side_split_with_metric(self):
        """Custom metric works."""
        response = client.get("/whisper/AMD/side-split?metric=revenue")
        assert response.status_code == 200
        data = response.json()
        assert data["metric"] == "revenue"


# -- Whisper History Tests ----------------------------------------------------

class TestWhisperHistory:
    """Tests for GET /whisper/{ticker}/history."""

    def test_history_returns_200(self):
        """Endpoint returns 200."""
        response = client.get("/whisper/NVDA/history")
        assert response.status_code == 200

    def test_history_structure(self):
        """History has expected structure."""
        response = client.get("/whisper/AAPL/history")
        data = response.json()

        assert "ticker" in data
        assert "metric" in data
        assert "history" in data
        assert "whisper_accuracy_rate" in data
        assert "avg_whisper_vs_actual_error" in data
        assert "avg_consensus_vs_actual_error" in data

    def test_history_has_periods(self):
        """History includes period data."""
        response = client.get("/whisper/MSFT/history?periods=4")
        data = response.json()
        assert len(data["history"]) >= 4

    def test_history_period_structure(self):
        """Each period has expected fields."""
        response = client.get("/whisper/GOOGL/history")
        data = response.json()

        if data["history"]:
            period = data["history"][0]
            assert "period" in period
            assert "whisper" in period
            assert "consensus" in period
            assert "actual" in period
            assert "whisper_error" in period
            assert "consensus_error" in period

    def test_history_accuracy_in_range(self):
        """Accuracy rate is between 0-100."""
        response = client.get("/whisper/META/history")
        data = response.json()
        assert 0 <= data["whisper_accuracy_rate"] <= 100


# -- Dispersion Tests ---------------------------------------------------------

class TestDispersionBySide:
    """Tests for GET /whisper/{ticker}/dispersion."""

    def test_dispersion_returns_200(self):
        """Endpoint returns 200."""
        response = client.get("/whisper/NVDA/dispersion")
        assert response.status_code == 200

    def test_dispersion_structure(self):
        """Dispersion has expected structure."""
        response = client.get("/whisper/AAPL/dispersion")
        data = response.json()

        assert "ticker" in data
        assert "period" in data
        assert "metric" in data
        assert "buy_side_dispersion" in data
        assert "sell_side_dispersion" in data
        assert "overall_dispersion" in data
        assert "most_dispersed_side" in data
        assert "convergence_trend" in data

    def test_dispersion_values_non_negative(self):
        """Dispersion values are non-negative."""
        response = client.get("/whisper/MSFT/dispersion")
        data = response.json()
        assert data["buy_side_dispersion"] >= 0
        assert data["sell_side_dispersion"] >= 0
        assert data["overall_dispersion"] >= 0

    def test_dispersion_trend_values(self):
        """Convergence trend is one of expected values."""
        response = client.get("/whisper/TSLA/dispersion")
        data = response.json()
        assert data["convergence_trend"] in ["converging", "diverging", "stable"]


# -- Estimates by Type Tests --------------------------------------------------

class TestEstimatesByType:
    """Tests for GET /whisper/{ticker}/estimates."""

    def test_estimates_returns_200(self):
        """Endpoint returns 200."""
        response = client.get("/whisper/NVDA/estimates?analyst_type=buy_side")
        assert response.status_code == 200

    def test_estimates_structure(self):
        """Estimates have expected structure."""
        response = client.get("/whisper/AAPL/estimates?analyst_type=sell_side")
        data = response.json()

        assert "ticker" in data
        assert "analyst_type" in data
        assert "estimates" in data
        assert "count" in data
        assert "mean" in data

    def test_estimates_filter_by_type(self):
        """Estimates are filtered by analyst type."""
        response = client.get("/whisper/MSFT/estimates?analyst_type=buy_side")
        data = response.json()

        for estimate in data["estimates"]:
            assert estimate["analyst_type"] == "buy_side"

    def test_estimates_invalid_type(self):
        """Invalid analyst type returns 400."""
        response = client.get("/whisper/NVDA/estimates?analyst_type=invalid")
        assert response.status_code == 400

    def test_estimates_with_metric(self):
        """Custom metric works."""
        response = client.get("/whisper/AMD/estimates?analyst_type=sell_side&metric=revenue")
        assert response.status_code == 200
        data = response.json()
        assert data["metric"] == "revenue"

    def test_estimate_structure(self):
        """Individual estimate has expected fields."""
        response = client.get("/whisper/GOOGL/estimates?analyst_type=sell_side")
        data = response.json()

        if data["estimates"]:
            estimate = data["estimates"][0]
            assert "analyst_id" in estimate
            assert "analyst_name" in estimate
            assert "firm" in estimate
            assert "estimate" in estimate
            assert "estimate_date" in estimate


# -- Reference Data Tests -----------------------------------------------------

class TestReferenceData:
    """Tests for /whisper/types/* endpoints."""

    def test_list_analyst_types(self):
        """List analyst types."""
        response = client.get("/whisper/types/analyst")
        assert response.status_code == 200

        data = response.json()
        assert "analyst_types" in data
        assert len(data["analyst_types"]) > 0

        for t in data["analyst_types"]:
            assert "value" in t
            assert "description" in t

    def test_analyst_types_include_expected(self):
        """Analyst types include expected values."""
        response = client.get("/whisper/types/analyst")
        data = response.json()

        values = [t["value"] for t in data["analyst_types"]]
        assert "buy_side" in values
        assert "sell_side" in values
        assert "independent" in values

    def test_list_estimate_metrics(self):
        """List estimate metrics."""
        response = client.get("/whisper/types/metrics")
        assert response.status_code == 200

        data = response.json()
        assert "metrics" in data
        assert len(data["metrics"]) > 0

    def test_metrics_include_expected(self):
        """Metrics include expected values."""
        response = client.get("/whisper/types/metrics")
        data = response.json()

        values = [m["value"] for m in data["metrics"]]
        assert "eps" in values
        assert "revenue" in values


# -- Compare Tests ------------------------------------------------------------

class TestWhisperCompare:
    """Tests for GET /whisper/compare."""

    def test_compare_returns_200(self):
        """Endpoint returns 200."""
        response = client.get("/whisper/compare?tickers=NVDA,AMD")
        assert response.status_code == 200

    def test_compare_structure(self):
        """Compare has expected structure."""
        response = client.get("/whisper/compare?tickers=AAPL,MSFT,GOOGL")
        data = response.json()

        assert "metric" in data
        assert "comparisons" in data
        assert "most_bullish_whisper" in data
        assert "most_bearish_whisper" in data

    def test_compare_includes_all_tickers(self):
        """Compare includes all requested tickers."""
        response = client.get("/whisper/compare?tickers=NVDA,AMD,INTC")
        data = response.json()

        tickers = [c["ticker"] for c in data["comparisons"]]
        assert "NVDA" in tickers
        assert "AMD" in tickers
        assert "INTC" in tickers

    def test_compare_needs_two_tickers(self):
        """Compare requires at least 2 tickers."""
        response = client.get("/whisper/compare?tickers=NVDA")
        assert response.status_code == 400

    def test_compare_sorted_by_spread(self):
        """Comparisons are sorted by whisper vs consensus."""
        response = client.get("/whisper/compare?tickers=NVDA,AMD,TSLA")
        data = response.json()

        spreads = [c["whisper_vs_consensus"] for c in data["comparisons"]]
        assert spreads == sorted(spreads, reverse=True)


# -- Screen Tests -------------------------------------------------------------

class TestWhisperScreen:
    """Tests for GET /whisper/screen."""

    def test_screen_returns_200(self):
        """Endpoint returns 200."""
        response = client.get("/whisper/screen")
        assert response.status_code == 200

    def test_screen_structure(self):
        """Screen has expected structure."""
        response = client.get("/whisper/screen")
        data = response.json()

        assert "results" in data
        assert "count" in data
        assert "filters" in data

    def test_screen_filter_by_min(self):
        """Filter by min whisper vs consensus works."""
        response = client.get("/whisper/screen?min_whisper_vs_consensus=0")
        data = response.json()

        for result in data["results"]:
            assert result["whisper_vs_consensus"] >= 0

    def test_screen_filter_by_direction(self):
        """Filter by direction works."""
        response = client.get("/whisper/screen?direction=above")
        data = response.json()

        for result in data["results"]:
            assert result["direction"] == "above"

    def test_screen_with_custom_tickers(self):
        """Screen with custom tickers works."""
        response = client.get("/whisper/screen?tickers=NVDA,AAPL")
        data = response.json()
        assert data["count"] <= 2


# -- Service Tests ------------------------------------------------------------

class TestWhisperService:
    """Tests for the underlying whisper_estimates_service module."""

    def test_enums_exist(self):
        """Enums are properly defined."""
        from app.services.whisper_estimates_service import (
            AnalystType,
            EstimateMetric,
        )

        assert AnalystType.BUY_SIDE.value == "buy_side"
        assert AnalystType.SELL_SIDE.value == "sell_side"
        assert EstimateMetric.EPS.value == "eps"
        assert EstimateMetric.REVENUE.value == "revenue"

    def test_dataclasses_exist(self):
        """Dataclasses are properly defined."""
        from app.services.whisper_estimates_service import (
            AnalystEstimate,
            WhisperEstimate,
            SideSplitAnalysis,
            WhisperHistory,
            WhisperSnapshot,
            AnalystType,
            EstimateMetric,
        )

        estimate = AnalystEstimate(
            analyst_id="test",
            analyst_name="Test Analyst",
            firm="Test Firm",
            analyst_type=AnalystType.SELL_SIDE,
            estimate=2.50,
            estimate_date="2025-01-15",
            metric=EstimateMetric.EPS,
            period="Q1 2025",
        )
        assert estimate.estimate == 2.50

    def test_service_singleton(self):
        """Service returns singleton instance."""
        from app.services.whisper_estimates_service import get_whisper_service

        s1 = get_whisper_service()
        s2 = get_whisper_service()
        assert s1 is s2

    def test_service_methods_exist(self):
        """Service has expected methods."""
        from app.services.whisper_estimates_service import WhisperEstimatesService

        service = WhisperEstimatesService()
        assert callable(service.get_whisper_estimate)
        assert callable(service.get_side_split_analysis)
        assert callable(service.get_whisper_history)
        assert callable(service.get_dispersion_by_side)
        assert callable(service.get_whisper_snapshot)
        assert callable(service.get_estimates_by_type)


# -- Edge Cases ---------------------------------------------------------------

class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_ticker_case_insensitive(self):
        """Ticker should be case insensitive."""
        r1 = client.get("/whisper/nvda")
        r2 = client.get("/whisper/NVDA")

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["ticker"] == r2.json()["ticker"]

    def test_unknown_ticker_still_works(self):
        """Unknown tickers still return data (mock service)."""
        response = client.get("/whisper/UNKNOWNTICKER")
        assert response.status_code == 200

    def test_all_metrics_work(self):
        """All metric types work."""
        metrics = ["eps", "revenue", "ebitda", "fcf", "gross_margin", "operating_income"]
        for metric in metrics:
            response = client.get(f"/whisper/AAPL?metric={metric}")
            assert response.status_code == 200, f"Metric {metric} failed"

    def test_all_analyst_types_work(self):
        """All analyst types work."""
        types = ["buy_side", "sell_side", "independent"]
        for analyst_type in types:
            response = client.get(f"/whisper/AAPL/estimates?analyst_type={analyst_type}")
            assert response.status_code == 200, f"Analyst type {analyst_type} failed"
