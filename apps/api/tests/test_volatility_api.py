"""
Tests for app.api.volatility API endpoints (Band B #27)
--------------------------------------------------------------------------------
Tests the FastAPI endpoints for:
  - /volatility/surface/{ticker} - Get IV surface
  - /volatility/snapshot/{ticker} - Get IV snapshot
  - /volatility/history/{ticker} - Get IV history
  - /volatility/skew/{ticker} - Get skew analysis
  - /volatility/screen - Screen by IV criteria
  - /volatility/term-structure/{ticker} - Get term structure
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# -- Volatility Surface Tests -------------------------------------------------

class TestVolatilitySurface:
    """Tests for GET /volatility/surface/{ticker}."""

    def test_surface_returns_200(self):
        """Endpoint returns 200 for valid ticker."""
        response = client.get("/volatility/surface/AAPL")
        assert response.status_code == 200

    def test_surface_structure(self):
        """Response has expected structure."""
        response = client.get("/volatility/surface/NVDA")
        data = response.json()

        assert "ticker" in data
        assert "underlying_price" in data
        assert "as_of_date" in data
        assert "as_of_time" in data
        assert "data_delay_minutes" in data
        assert "surface" in data
        assert "term_structure" in data
        assert "skew" in data

    def test_surface_ticker_uppercase(self):
        """Ticker is returned uppercase."""
        response = client.get("/volatility/surface/aapl")
        data = response.json()
        assert data["ticker"] == "AAPL"

    def test_surface_has_underlying_price(self):
        """Surface includes underlying price."""
        response = client.get("/volatility/surface/MSFT")
        data = response.json()
        assert data["underlying_price"] > 0

    def test_surface_has_delay_disclosure(self):
        """Surface discloses data delay."""
        response = client.get("/volatility/surface/TSLA")
        data = response.json()
        assert data["data_delay_minutes"] >= 0

    def test_surface_data_points(self):
        """Surface contains data points."""
        response = client.get("/volatility/surface/AMD")
        data = response.json()

        assert len(data["surface"]) > 0
        point = data["surface"][0]
        assert "strike" in point
        assert "expiry" in point
        assert "iv" in point
        assert "moneyness" in point

    def test_surface_term_structure(self):
        """Term structure is included."""
        response = client.get("/volatility/surface/META")
        data = response.json()

        assert len(data["term_structure"]) > 0
        term = data["term_structure"][0]
        assert "expiry" in term
        assert "atm_iv" in term

    def test_surface_skew_metrics(self):
        """Skew metrics are included."""
        response = client.get("/volatility/surface/GOOGL")
        data = response.json()

        assert "skew" in data
        skew = data["skew"]
        assert "skew_25d" in skew


# -- Volatility Snapshot Tests ------------------------------------------------

class TestVolatilitySnapshot:
    """Tests for GET /volatility/snapshot/{ticker}."""

    def test_snapshot_returns_200(self):
        """Endpoint returns 200 for valid ticker."""
        response = client.get("/volatility/snapshot/AAPL")
        assert response.status_code == 200

    def test_snapshot_structure(self):
        """Response has expected structure."""
        response = client.get("/volatility/snapshot/NVDA")
        data = response.json()

        assert "ticker" in data
        assert "current_price" in data
        assert "iv_30d" in data
        assert "iv_60d" in data
        assert "iv_90d" in data
        assert "iv_rank" in data
        assert "iv_percentile" in data
        assert "hv_30d" in data
        assert "iv_hv_spread" in data
        assert "put_call_skew" in data
        assert "term_slope" in data

    def test_snapshot_ticker_uppercase(self):
        """Ticker is returned uppercase."""
        response = client.get("/volatility/snapshot/msft")
        data = response.json()
        assert data["ticker"] == "MSFT"

    def test_snapshot_iv_rank_in_range(self):
        """IV rank is between 0-100."""
        response = client.get("/volatility/snapshot/TSLA")
        data = response.json()
        assert 0 <= data["iv_rank"] <= 100

    def test_snapshot_iv_percentile_in_range(self):
        """IV percentile is between 0-100."""
        response = client.get("/volatility/snapshot/AMD")
        data = response.json()
        assert 0 <= data["iv_percentile"] <= 100

    def test_snapshot_iv_values_positive(self):
        """IV values are positive."""
        response = client.get("/volatility/snapshot/META")
        data = response.json()
        assert data["iv_30d"] > 0
        assert data["iv_60d"] > 0
        assert data["iv_90d"] > 0

    def test_snapshot_hv_positive(self):
        """Historical volatility is positive."""
        response = client.get("/volatility/snapshot/GOOGL")
        data = response.json()
        assert data["hv_30d"] > 0


# -- Volatility History Tests -------------------------------------------------

class TestVolatilityHistory:
    """Tests for GET /volatility/history/{ticker}."""

    def test_history_returns_200(self):
        """Endpoint returns 200 for valid ticker."""
        response = client.get("/volatility/history/AAPL")
        assert response.status_code == 200

    def test_history_structure(self):
        """Response has expected structure."""
        response = client.get("/volatility/history/NVDA")
        data = response.json()

        assert "ticker" in data
        assert "period_days" in data
        assert "iv_history" in data
        assert "iv_high_52w" in data
        assert "iv_low_52w" in data
        assert "current_iv_rank" in data

    def test_history_default_period(self):
        """Default period is 252 days."""
        response = client.get("/volatility/history/MSFT")
        data = response.json()
        assert data["period_days"] == 252

    def test_history_custom_period(self):
        """Custom period parameter works."""
        response = client.get("/volatility/history/TSLA?days=90")
        data = response.json()
        assert data["period_days"] == 90

    def test_history_data_points(self):
        """History contains daily data points."""
        response = client.get("/volatility/history/AMD?days=30")
        data = response.json()

        assert len(data["iv_history"]) > 0
        point = data["iv_history"][0]
        assert "date" in point
        assert "iv_30d" in point
        assert "hv_30d" in point

    def test_history_52w_range(self):
        """52-week high is >= 52-week low."""
        response = client.get("/volatility/history/META")
        data = response.json()
        assert data["iv_high_52w"] >= data["iv_low_52w"]

    def test_history_iv_rank_in_range(self):
        """Current IV rank is between 0-100."""
        response = client.get("/volatility/history/GOOGL")
        data = response.json()
        assert 0 <= data["current_iv_rank"] <= 100

    def test_history_days_minimum(self):
        """Days parameter has minimum validation."""
        response = client.get("/volatility/history/AAPL?days=10")
        assert response.status_code == 422

    def test_history_days_maximum(self):
        """Days parameter has maximum validation."""
        response = client.get("/volatility/history/AAPL?days=1000")
        assert response.status_code == 422


# -- Skew Analysis Tests ------------------------------------------------------

class TestSkewAnalysis:
    """Tests for GET /volatility/skew/{ticker}."""

    def test_skew_returns_200(self):
        """Endpoint returns 200 for valid ticker."""
        response = client.get("/volatility/skew/AAPL")
        assert response.status_code == 200

    def test_skew_structure(self):
        """Response has expected structure."""
        response = client.get("/volatility/skew/NVDA")
        data = response.json()

        assert "ticker" in data
        assert "expiry" in data
        assert "underlying_price" in data
        assert "atm_iv" in data
        assert "skew_25d" in data
        assert "skew_10d" in data
        assert "skew_by_strike" in data
        assert "skew_percentile" in data
        assert "interpretation" in data

    def test_skew_ticker_uppercase(self):
        """Ticker is returned uppercase."""
        response = client.get("/volatility/skew/msft")
        data = response.json()
        assert data["ticker"] == "MSFT"

    def test_skew_has_interpretation(self):
        """Skew analysis includes interpretation."""
        response = client.get("/volatility/skew/TSLA")
        data = response.json()
        assert len(data["interpretation"]) > 0

    def test_skew_by_strike(self):
        """Skew by strike is included."""
        response = client.get("/volatility/skew/AMD")
        data = response.json()

        assert len(data["skew_by_strike"]) > 0
        point = data["skew_by_strike"][0]
        assert "strike" in point
        assert "iv" in point
        assert "moneyness" in point

    def test_skew_percentile_in_range(self):
        """Skew percentile is between 0-100."""
        response = client.get("/volatility/skew/META")
        data = response.json()
        assert 0 <= data["skew_percentile"] <= 100


# -- Volatility Screen Tests --------------------------------------------------

class TestVolatilityScreen:
    """Tests for GET /volatility/screen."""

    def test_screen_returns_200(self):
        """Endpoint returns 200."""
        response = client.get("/volatility/screen")
        assert response.status_code == 200

    def test_screen_structure(self):
        """Response has expected structure."""
        response = client.get("/volatility/screen")
        data = response.json()

        assert "results" in data
        assert "count" in data
        assert "filters" in data
        assert "data_note" in data

    def test_screen_returns_results(self):
        """Screen returns stock results."""
        response = client.get("/volatility/screen")
        data = response.json()
        assert data["count"] > 0

    def test_screen_filter_by_min_iv_rank(self):
        """Min IV rank filter works."""
        response = client.get("/volatility/screen?min_iv_rank=50")
        data = response.json()

        for result in data["results"]:
            assert result["iv_rank"] >= 50

    def test_screen_filter_by_max_iv_rank(self):
        """Max IV rank filter works."""
        response = client.get("/volatility/screen?max_iv_rank=50")
        data = response.json()

        for result in data["results"]:
            assert result["iv_rank"] <= 50

    def test_screen_filter_by_iv_hv_spread(self):
        """Min IV-HV spread filter works."""
        response = client.get("/volatility/screen?min_iv_hv_spread=0")
        data = response.json()

        for result in data["results"]:
            assert result["iv_hv_spread"] >= 0

    def test_screen_custom_tickers(self):
        """Custom ticker list works."""
        response = client.get("/volatility/screen?tickers=AAPL,NVDA,TSLA")
        data = response.json()
        assert data["count"] <= 3

    def test_screen_filters_in_response(self):
        """Applied filters are returned."""
        response = client.get("/volatility/screen?min_iv_rank=30&max_iv_rank=70")
        data = response.json()
        assert data["filters"]["min_iv_rank"] == 30
        assert data["filters"]["max_iv_rank"] == 70

    def test_screen_data_note(self):
        """Data note about delay is included."""
        response = client.get("/volatility/screen")
        data = response.json()
        assert "delay" in data["data_note"].lower() or "eod" in data["data_note"].lower()


# -- Term Structure Tests -----------------------------------------------------

class TestTermStructure:
    """Tests for GET /volatility/term-structure/{ticker}."""

    def test_term_structure_returns_200(self):
        """Endpoint returns 200 for valid ticker."""
        response = client.get("/volatility/term-structure/AAPL")
        assert response.status_code == 200

    def test_term_structure_structure(self):
        """Response has expected structure."""
        response = client.get("/volatility/term-structure/NVDA")
        data = response.json()

        assert "ticker" in data
        assert "underlying_price" in data
        assert "term_structure" in data
        assert "as_of_date" in data
        assert "data_delay_minutes" in data

    def test_term_structure_ticker_uppercase(self):
        """Ticker is returned uppercase."""
        response = client.get("/volatility/term-structure/msft")
        data = response.json()
        assert data["ticker"] == "MSFT"

    def test_term_structure_multiple_expiries(self):
        """Term structure includes multiple expiries."""
        response = client.get("/volatility/term-structure/TSLA")
        data = response.json()
        assert len(data["term_structure"]) > 1

    def test_term_structure_expiry_fields(self):
        """Term structure entries have required fields."""
        response = client.get("/volatility/term-structure/AMD")
        data = response.json()

        term = data["term_structure"][0]
        assert "expiry" in term
        assert "expiry_months" in term
        assert "atm_iv" in term
        assert "atm_strike" in term


# -- Service Tests ------------------------------------------------------------

class TestVolatilityService:
    """Tests for the underlying volatility_service module."""

    def test_dataclass_definitions(self):
        """Dataclasses are properly defined."""
        from app.services.volatility_service import (
            VolatilitySurface,
            VolatilitySnapshot,
            VolatilityHistory,
            SkewAnalysis,
        )

        # VolatilitySurface
        surface = VolatilitySurface(
            ticker="AAPL",
            underlying_price=185.0,
            as_of_date="2024-01-15",
            as_of_time="15:45:00",
            data_delay_minutes=15,
            surface=[],
            term_structure=[],
            skew={},
        )
        assert surface.ticker == "AAPL"
        assert surface.data_delay_minutes == 15

        # VolatilitySnapshot
        snapshot = VolatilitySnapshot(
            ticker="NVDA",
            current_price=875.0,
            iv_30d=0.45,
            iv_60d=0.47,
            iv_90d=0.48,
            iv_rank=65.0,
            iv_percentile=70.0,
            hv_30d=0.35,
            iv_hv_spread=0.10,
            put_call_skew=0.03,
            term_slope=0.01,
        )
        assert snapshot.iv_30d == 0.45
        assert snapshot.iv_rank == 65.0

    def test_service_singleton(self):
        """Service returns singleton instance."""
        from app.services.volatility_service import get_volatility_service

        s1 = get_volatility_service()
        s2 = get_volatility_service()
        assert s1 is s2

    def test_service_methods_exist(self):
        """Service has expected methods."""
        from app.services.volatility_service import VolatilityService

        service = VolatilityService()
        assert callable(service.get_volatility_surface)
        assert callable(service.get_volatility_snapshot)
        assert callable(service.get_volatility_history)
        assert callable(service.get_skew_analysis)
        assert callable(service.screen_volatility)

    def test_dataclass_to_dict(self):
        """Dataclasses have to_dict method."""
        from app.services.volatility_service import VolatilitySnapshot

        snapshot = VolatilitySnapshot(
            ticker="AAPL",
            current_price=185.0,
            iv_30d=0.22,
            iv_60d=0.23,
            iv_90d=0.24,
            iv_rank=45.0,
            iv_percentile=50.0,
            hv_30d=0.18,
            iv_hv_spread=0.04,
            put_call_skew=0.02,
            term_slope=0.005,
        )

        d = snapshot.to_dict()
        assert isinstance(d, dict)
        assert d["ticker"] == "AAPL"
        assert d["iv_30d"] == 0.22


# -- Edge Cases ---------------------------------------------------------------

class TestEdgeCases:
    """Edge case and error handling tests."""

    def test_ticker_case_insensitive(self):
        """Ticker should be case insensitive."""
        r1 = client.get("/volatility/snapshot/aapl")
        r2 = client.get("/volatility/snapshot/AAPL")

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()["ticker"] == r2.json()["ticker"]

    def test_unknown_ticker_still_works(self):
        """Unknown tickers still return data (mock service)."""
        response = client.get("/volatility/snapshot/UNKNOWNTICKER")
        assert response.status_code == 200

    def test_screen_empty_tickers(self):
        """Empty tickers string uses defaults."""
        response = client.get("/volatility/screen?tickers=")
        assert response.status_code == 200
        # Empty string becomes empty list, so should use defaults
        data = response.json()
        assert data["count"] > 0
