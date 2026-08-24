"""
Tests for Estimate Revision Screener API (Band C #37)
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ── Service Unit Tests ────────────────────────────────────────────────────────


class TestEnums:
    """Test enum definitions."""

    def test_revision_trend_values(self):
        """RevisionTrend has expected values."""
        from app.services.revision_screener_service import RevisionTrend

        assert RevisionTrend.STRONG_UP.value == "strong_up"
        assert RevisionTrend.MODERATE_UP.value == "moderate_up"
        assert RevisionTrend.STABLE.value == "stable"
        assert RevisionTrend.MODERATE_DOWN.value == "moderate_down"
        assert RevisionTrend.STRONG_DOWN.value == "strong_down"

    def test_screener_sort_by_values(self):
        """ScreenerSortBy has expected values."""
        from app.services.revision_screener_service import ScreenerSortBy

        assert ScreenerSortBy.MOMENTUM_7D.value == "momentum_7d"
        assert ScreenerSortBy.MOMENTUM_30D.value == "momentum_30d"
        assert ScreenerSortBy.SIGNAL_STRENGTH.value == "signal_strength"


class TestRevisionScreenerResult:
    """Test RevisionScreenerResult dataclass."""

    def test_to_dict(self):
        """RevisionScreenerResult serializes correctly."""
        from app.services.revision_screener_service import (
            RevisionScreenerResult,
            RevisionTrend,
        )
        from app.services.consensus_service import EstimateType, PeriodType

        result = RevisionScreenerResult(
            ticker="AAPL",
            company_name="Apple Inc.",
            estimate_type=EstimateType.EPS,
            fiscal_year=2025,
            fiscal_period=PeriodType.FY,
            momentum_7d=2.5,
            momentum_30d=5.0,
            momentum_90d=8.0,
            revisions_up_7d=3,
            revisions_down_7d=1,
            revisions_up_30d=8,
            revisions_down_30d=2,
            trend="accelerating_up",
            trend_classification=RevisionTrend.MODERATE_UP,
            signal_strength=65.0,
            current_consensus=6.75,
            num_analysts=12,
        )

        data = result.to_dict()
        assert data["ticker"] == "AAPL"
        assert data["momentum"]["30d"] == 5.0
        assert data["trend_classification"] == "moderate_up"


class TestRevisionScreenerOutput:
    """Test RevisionScreenerOutput dataclass."""

    def test_to_dict(self):
        """RevisionScreenerOutput serializes correctly."""
        from app.services.revision_screener_service import (
            RevisionScreenerOutput,
            RevisionScreenerResult,
            RevisionTrend,
            ScreenerSortBy,
        )
        from app.services.consensus_service import EstimateType, PeriodType
        from datetime import date

        result = RevisionScreenerResult(
            ticker="AAPL",
            company_name="Apple Inc.",
            estimate_type=EstimateType.EPS,
            fiscal_year=2025,
            fiscal_period=PeriodType.FY,
            momentum_7d=2.5,
            momentum_30d=5.0,
            momentum_90d=8.0,
            revisions_up_7d=3,
            revisions_down_7d=1,
            revisions_up_30d=8,
            revisions_down_30d=2,
            trend="accelerating_up",
            trend_classification=RevisionTrend.MODERATE_UP,
            signal_strength=65.0,
            current_consensus=6.75,
            num_analysts=12,
        )

        output = RevisionScreenerOutput(
            results=[result],
            total_screened=20,
            total_matched=1,
            filters_applied={"min_momentum_30d": 2.0},
            sort_by=ScreenerSortBy.MOMENTUM_30D,
            sort_ascending=False,
            as_of_date=date.today(),
        )

        data = output.to_dict()
        assert data["total_screened"] == 20
        assert data["total_matched"] == 1
        assert len(data["results"]) == 1


class TestRevisionAlert:
    """Test RevisionAlert dataclass."""

    def test_to_dict(self):
        """RevisionAlert serializes correctly."""
        from app.services.revision_screener_service import RevisionAlert
        from app.services.consensus_service import EstimateType, PeriodType
        from datetime import datetime

        alert = RevisionAlert(
            ticker="NVDA",
            company_name="NVIDIA Corporation",
            alert_type="momentum_spike",
            estimate_type=EstimateType.EPS,
            fiscal_year=2025,
            fiscal_period=PeriodType.FY,
            description="Significant upward revision momentum: +8.5% in 7 days",
            severity="high",
            momentum_change=8.5,
            triggered_at=datetime.now(),
        )

        data = alert.to_dict()
        assert data["ticker"] == "NVDA"
        assert data["alert_type"] == "momentum_spike"
        assert data["severity"] == "high"


class TestServiceFunctions:
    """Test service functions."""

    def test_screen_by_revisions_default(self):
        """screen_by_revisions returns results with default params."""
        from app.services.revision_screener_service import screen_by_revisions

        output = screen_by_revisions()

        assert output.total_screened > 0
        assert output.as_of_date is not None

    def test_screen_by_revisions_with_filters(self):
        """screen_by_revisions applies momentum filters."""
        from app.services.revision_screener_service import screen_by_revisions

        output = screen_by_revisions(
            min_momentum_30d=0,
            limit=5,
        )

        # All results should have positive momentum
        for result in output.results:
            assert result.momentum_30d >= 0

    def test_screen_by_revisions_with_trend_filter(self):
        """screen_by_revisions filters by trend classification."""
        from app.services.revision_screener_service import (
            screen_by_revisions,
            RevisionTrend,
        )

        output = screen_by_revisions(
            trend_classifications=[RevisionTrend.STRONG_UP, RevisionTrend.MODERATE_UP],
            limit=10,
        )

        for result in output.results:
            assert result.trend_classification in [RevisionTrend.STRONG_UP, RevisionTrend.MODERATE_UP]

    def test_get_top_upward_revisions(self):
        """get_top_upward_revisions returns positive momentum companies."""
        from app.services.revision_screener_service import get_top_upward_revisions

        output = get_top_upward_revisions(limit=5)

        assert len(output.results) <= 5
        # Results should be sorted descending by momentum
        for i in range(len(output.results) - 1):
            assert output.results[i].momentum_30d >= output.results[i + 1].momentum_30d

    def test_get_top_downward_revisions(self):
        """get_top_downward_revisions returns negative momentum companies."""
        from app.services.revision_screener_service import get_top_downward_revisions

        output = get_top_downward_revisions(limit=5)

        assert len(output.results) <= 5
        # Results should be sorted ascending by momentum (most negative first)
        for i in range(len(output.results) - 1):
            assert output.results[i].momentum_30d <= output.results[i + 1].momentum_30d

    def test_get_accelerating_revisions_up(self):
        """get_accelerating_revisions returns accelerating upward revisions."""
        from app.services.revision_screener_service import get_accelerating_revisions

        output = get_accelerating_revisions(direction="up", limit=5)

        assert output is not None
        for result in output.results:
            assert result.momentum_7d >= 0
            assert result.momentum_30d >= 0

    def test_get_accelerating_revisions_down(self):
        """get_accelerating_revisions returns accelerating downward revisions."""
        from app.services.revision_screener_service import get_accelerating_revisions

        output = get_accelerating_revisions(direction="down", limit=5)

        assert output is not None
        for result in output.results:
            assert result.momentum_7d <= 0
            assert result.momentum_30d <= 0

    def test_get_revision_alerts(self):
        """get_revision_alerts returns alerts list."""
        from app.services.revision_screener_service import get_revision_alerts

        alerts = get_revision_alerts(
            tickers=["AAPL", "NVDA", "MSFT"],
            momentum_spike_threshold=3.0,
        )

        assert isinstance(alerts, list)

    @pytest.mark.skip(reason="requires live Finnhub data for consensus momentum")
    def test_get_revision_summary(self):
        """get_revision_summary returns summary statistics."""
        from app.services.revision_screener_service import get_revision_summary

        summary = get_revision_summary()

        assert "total_companies" in summary
        assert "direction_breakdown" in summary
        assert "momentum_stats" in summary


# ── API Tests ─────────────────────────────────────────────────────────────────


class TestReferenceEndpoints:
    """Test reference data endpoints."""

    def test_list_estimate_types(self):
        """GET /revisions/types/estimate-types returns types."""
        response = client.get("/revisions/types/estimate-types")
        assert response.status_code == 200
        data = response.json()
        assert "estimate_types" in data
        assert len(data["estimate_types"]) > 0

    def test_list_periods(self):
        """GET /revisions/types/periods returns periods."""
        response = client.get("/revisions/types/periods")
        assert response.status_code == 200
        data = response.json()
        assert "periods" in data

    def test_list_trend_classifications(self):
        """GET /revisions/types/trends returns trend classifications."""
        response = client.get("/revisions/types/trends")
        assert response.status_code == 200
        data = response.json()
        assert "trend_classifications" in data

    def test_list_sort_options(self):
        """GET /revisions/types/sort-options returns sort options."""
        response = client.get("/revisions/types/sort-options")
        assert response.status_code == 200
        data = response.json()
        assert "sort_options" in data


class TestScreenerAPI:
    """Test screener API endpoints."""

    def test_screen_revisions_default(self):
        """POST /revisions/screen returns results with defaults."""
        response = client.post("/revisions/screen")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total_screened" in data
        assert "total_matched" in data

    def test_screen_revisions_with_momentum_filter(self):
        """POST /revisions/screen applies momentum filter."""
        response = client.post("/revisions/screen?min_momentum_30d=0&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 5

    def test_screen_revisions_invalid_estimate_type(self):
        """POST /revisions/screen rejects invalid estimate type."""
        response = client.post("/revisions/screen?estimate_type=invalid")
        assert response.status_code == 400

    def test_screen_revisions_invalid_period(self):
        """POST /revisions/screen rejects invalid fiscal period."""
        response = client.post("/revisions/screen?fiscal_period=invalid")
        assert response.status_code == 400

    def test_screen_revisions_invalid_sort(self):
        """POST /revisions/screen rejects invalid sort field."""
        response = client.post("/revisions/screen?sort_by=invalid")
        assert response.status_code == 400

    def test_get_top_upward(self):
        """GET /revisions/top-upward returns results."""
        response = client.get("/revisions/top-upward")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_get_top_upward_with_params(self):
        """GET /revisions/top-upward accepts parameters."""
        response = client.get("/revisions/top-upward?estimate_type=revenue&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) <= 5

    def test_get_top_downward(self):
        """GET /revisions/top-downward returns results."""
        response = client.get("/revisions/top-downward")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_get_accelerating_up(self):
        """GET /revisions/accelerating returns upward results."""
        response = client.get("/revisions/accelerating?direction=up")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_get_accelerating_down(self):
        """GET /revisions/accelerating returns downward results."""
        response = client.get("/revisions/accelerating?direction=down")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    def test_get_accelerating_invalid_direction(self):
        """GET /revisions/accelerating rejects invalid direction."""
        response = client.get("/revisions/accelerating?direction=sideways")
        assert response.status_code == 400

    def test_get_alerts(self):
        """GET /revisions/alerts returns alerts."""
        response = client.get("/revisions/alerts")
        assert response.status_code == 200
        data = response.json()
        assert "alert_count" in data
        assert "alerts" in data

    def test_get_alerts_with_threshold(self):
        """GET /revisions/alerts accepts threshold parameter."""
        response = client.get("/revisions/alerts?momentum_threshold=3.0")
        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data

    @pytest.mark.skip(reason="requires live Finnhub data")
    def test_get_summary(self):
        """GET /revisions/summary returns summary statistics."""
        response = client.get("/revisions/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_companies" in data
        assert "direction_breakdown" in data
        assert "momentum_stats" in data

    def test_get_summary_with_params(self):
        """GET /revisions/summary accepts parameters."""
        response = client.get("/revisions/summary?estimate_type=eps&fiscal_period=Q1")
        assert response.status_code == 200
        data = response.json()
        assert "total_companies" in data
