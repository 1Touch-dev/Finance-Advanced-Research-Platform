"""
Tests for app.api.consensus API endpoints (Band B #19, #20, #21, #23)
────────────────────────────────────────────────────────────────────────────
Tests the FastAPI endpoints for:
  - /consensus/snapshot - Point-in-time consensus
  - /consensus/dispersion - Estimate dispersion (#21)
  - /consensus/surprise - Individual earnings surprise
  - /consensus/surprise-history - Earnings surprise history (#23)
  - /consensus/dashboard/{ticker} - Combined dashboard
  - /consensus/compare - Multi-ticker comparison
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from datetime import date

# Import the app for testing
from app.main import app

client = TestClient(app)


# ── Test Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def test_ticker():
    return "NVDA"


@pytest.fixture
def current_year():
    return date.today().year


# ── Consensus Snapshot Endpoint ───────────────────────────────────────────────

class TestConsensusSnapshotEndpoint:
    """Tests for GET /consensus/snapshot."""

    def test_snapshot_basic(self, test_ticker):
        response = client.get(f"/consensus/snapshot?ticker={test_ticker}")
        assert response.status_code == 200

        data = response.json()
        assert data["ticker"] == test_ticker.upper()
        assert "consensus" in data
        assert "mean" in data["consensus"]
        assert "median" in data["consensus"]

    def test_snapshot_with_estimate_type(self, test_ticker):
        response = client.get(f"/consensus/snapshot?ticker={test_ticker}&estimate_type=revenue")
        assert response.status_code == 200

        data = response.json()
        assert data["estimate_type"] == "revenue"

    def test_snapshot_with_fiscal_period(self, test_ticker):
        response = client.get(f"/consensus/snapshot?ticker={test_ticker}&fiscal_period=Q1")
        assert response.status_code == 200

        data = response.json()
        assert data["fiscal_period"] == "Q1"

    def test_snapshot_invalid_estimate_type(self, test_ticker):
        response = client.get(f"/consensus/snapshot?ticker={test_ticker}&estimate_type=invalid")
        assert response.status_code == 400

    def test_snapshot_invalid_fiscal_period(self, test_ticker):
        response = client.get(f"/consensus/snapshot?ticker={test_ticker}&fiscal_period=Q9")
        assert response.status_code == 400


# ── Estimate Dispersion Endpoint (#21) ────────────────────────────────────────

class TestDispersionEndpoint:
    """Tests for GET /consensus/dispersion - Band B #21."""

    def test_dispersion_basic(self, test_ticker):
        response = client.get(f"/consensus/dispersion?ticker={test_ticker}")
        assert response.status_code == 200

        data = response.json()
        assert data["ticker"] == test_ticker.upper()
        assert "metrics" in data
        assert "range" in data["metrics"]
        assert "coefficient_of_variation" in data["metrics"]
        assert "dispersion_level" in data
        assert "uncertainty_score" in data

    def test_dispersion_has_quartiles(self, test_ticker):
        response = client.get(f"/consensus/dispersion?ticker={test_ticker}")
        assert response.status_code == 200

        data = response.json()
        assert "quartiles" in data
        assert "q1" in data["quartiles"]
        assert "q2" in data["quartiles"]
        assert "q3" in data["quartiles"]

    def test_dispersion_with_estimate_type(self, test_ticker):
        response = client.get(f"/consensus/dispersion?ticker={test_ticker}&estimate_type=revenue")
        assert response.status_code == 200

        data = response.json()
        assert data["estimate_type"] == "revenue"

    def test_dispersion_uncertainty_bounded(self, test_ticker):
        response = client.get(f"/consensus/dispersion?ticker={test_ticker}")
        data = response.json()

        assert 0 <= data["uncertainty_score"] <= 100

    def test_dispersion_level_valid(self, test_ticker):
        response = client.get(f"/consensus/dispersion?ticker={test_ticker}")
        data = response.json()

        assert data["dispersion_level"] in ["low", "moderate", "high", "extreme"]


# ── Earnings Surprise Endpoint ────────────────────────────────────────────────

class TestSurpriseEndpoint:
    """Tests for GET /consensus/surprise."""

    def test_surprise_basic(self, test_ticker, current_year):
        response = client.get(
            f"/consensus/surprise?ticker={test_ticker}&fiscal_year={current_year}&fiscal_period=Q1"
        )
        assert response.status_code == 200

        data = response.json()
        assert data["ticker"] == test_ticker.upper()
        assert "actual_eps" in data
        assert "consensus_eps" in data
        assert "surprise_pct" in data
        assert "surprise_type" in data

    def test_surprise_has_market_reaction(self, test_ticker, current_year):
        response = client.get(
            f"/consensus/surprise?ticker={test_ticker}&fiscal_year={current_year}&fiscal_period=Q1"
        )
        data = response.json()

        assert "market_reaction" in data
        assert "1d" in data["market_reaction"]
        assert "5d" in data["market_reaction"]

    def test_surprise_type_valid(self, test_ticker, current_year):
        response = client.get(
            f"/consensus/surprise?ticker={test_ticker}&fiscal_year={current_year}&fiscal_period=Q1"
        )
        data = response.json()

        assert data["surprise_type"] in ["beat", "miss", "inline"]


# ── Earnings Surprise History Endpoint (#23) ──────────────────────────────────

class TestSurpriseHistoryEndpoint:
    """Tests for GET /consensus/surprise-history - Band B #23."""

    def test_history_basic(self, test_ticker):
        response = client.get(f"/consensus/surprise-history?ticker={test_ticker}")
        assert response.status_code == 200

        data = response.json()
        assert data["ticker"] == test_ticker.upper()
        assert "summary" in data
        assert "history" in data

    def test_history_summary_stats(self, test_ticker):
        response = client.get(f"/consensus/surprise-history?ticker={test_ticker}")
        data = response.json()

        summary = data["summary"]
        assert "total_quarters" in summary
        assert "beats" in summary
        assert "misses" in summary
        assert "inline" in summary
        assert "beat_rate" in summary

    def test_history_metrics(self, test_ticker):
        response = client.get(f"/consensus/surprise-history?ticker={test_ticker}")
        data = response.json()

        assert "metrics" in data
        assert "avg_surprise_pct" in data["metrics"]
        assert "avg_beat_magnitude" in data["metrics"]
        assert "avg_miss_magnitude" in data["metrics"]

    def test_history_streaks(self, test_ticker):
        response = client.get(f"/consensus/surprise-history?ticker={test_ticker}")
        data = response.json()

        assert "streaks" in data
        assert "consecutive_beats" in data["streaks"]
        assert "consecutive_misses" in data["streaks"]
        assert "current_beat_streak" in data["streaks"]

    def test_history_market_reactions(self, test_ticker):
        response = client.get(f"/consensus/surprise-history?ticker={test_ticker}")
        data = response.json()

        assert "market_reactions" in data

    def test_history_with_quarters_param(self, test_ticker):
        response = client.get(f"/consensus/surprise-history?ticker={test_ticker}&quarters=8")
        assert response.status_code == 200

        data = response.json()
        # Should have history entries
        assert len(data["history"]) > 0

    def test_history_entries_have_required_fields(self, test_ticker):
        response = client.get(f"/consensus/surprise-history?ticker={test_ticker}&quarters=4")
        data = response.json()

        for entry in data["history"]:
            assert "ticker" in entry
            assert "fiscal_year" in entry
            assert "fiscal_period" in entry
            assert "actual_eps" in entry
            assert "consensus_eps" in entry
            assert "surprise_pct" in entry
            assert "surprise_type" in entry


# ── Dashboard Endpoint ────────────────────────────────────────────────────────

class TestDashboardEndpoint:
    """Tests for GET /consensus/dashboard/{ticker}."""

    def test_dashboard_basic(self, test_ticker):
        response = client.get(f"/consensus/dashboard/{test_ticker}")
        assert response.status_code == 200

        data = response.json()
        assert data["ticker"] == test_ticker.upper()
        assert "current_consensus" in data
        assert "momentum" in data
        assert "dispersion" in data
        assert "recent_surprises" in data

    def test_dashboard_includes_dispersion(self, test_ticker):
        response = client.get(f"/consensus/dashboard/{test_ticker}")
        data = response.json()

        dispersion = data["dispersion"]
        assert "metrics" in dispersion
        assert "dispersion_level" in dispersion
        assert "uncertainty_score" in dispersion

    def test_dashboard_includes_surprise_stats(self, test_ticker):
        response = client.get(f"/consensus/dashboard/{test_ticker}")
        data = response.json()

        surprises = data["recent_surprises"]
        assert "beat_rate" in surprises
        assert "avg_surprise" in surprises
        assert "last_4_quarters" in surprises


# ── Compare Endpoint ──────────────────────────────────────────────────────────

class TestCompareEndpoint:
    """Tests for GET /consensus/compare."""

    def test_compare_multiple_tickers(self):
        response = client.get("/consensus/compare?tickers=NVDA,AAPL,MSFT")
        assert response.status_code == 200

        data = response.json()
        assert "comparison" in data
        assert len(data["comparison"]) == 3

    def test_compare_includes_dispersion_metrics(self):
        response = client.get("/consensus/compare?tickers=NVDA,AAPL")
        data = response.json()

        for item in data["comparison"]:
            if "error" not in item:
                assert "dispersion_level" in item
                assert "uncertainty_score" in item


# ── Momentum Endpoint ─────────────────────────────────────────────────────────

class TestMomentumEndpoint:
    """Tests for GET /consensus/momentum."""

    def test_momentum_basic(self, test_ticker):
        response = client.get(f"/consensus/momentum?ticker={test_ticker}")
        assert response.status_code == 200

        data = response.json()
        assert data["ticker"] == test_ticker.upper()
        assert "momentum" in data
        assert "7d" in data["momentum"]
        assert "30d" in data["momentum"]
        assert "90d" in data["momentum"]
        assert "trend" in data


# ── Revisions Endpoint ────────────────────────────────────────────────────────

class TestRevisionsEndpoint:
    """Tests for GET /consensus/revisions."""

    def test_revisions_basic(self, test_ticker):
        response = client.get(f"/consensus/revisions?ticker={test_ticker}")
        assert response.status_code == 200

        data = response.json()
        assert data["ticker"] == test_ticker.upper()
        assert "summary" in data
        assert "revisions" in data

    def test_revisions_summary(self, test_ticker):
        response = client.get(f"/consensus/revisions?ticker={test_ticker}")
        data = response.json()

        summary = data["summary"]
        assert "total_revisions" in summary
        assert "revisions_up" in summary
        assert "revisions_down" in summary
        assert "net_direction" in summary


# ── Rolling History Endpoint ──────────────────────────────────────────────────

class TestRollingEndpoint:
    """Tests for GET /consensus/rolling."""

    def test_rolling_basic(self, test_ticker):
        response = client.get(f"/consensus/rolling?ticker={test_ticker}")
        assert response.status_code == 200

        data = response.json()
        assert data["ticker"] == test_ticker.upper()
        assert "snapshots" in data
        assert "count" in data
        assert len(data["snapshots"]) > 0


# ── Forward Multiples Endpoint (#35) ─────────────────────────────────────────

class TestForwardMultiplesEndpoint:
    """Tests for GET /consensus/multiples - Band C #35."""

    def test_multiples_basic(self, test_ticker):
        response = client.get(f"/consensus/multiples?ticker={test_ticker}")
        assert response.status_code == 200

        data = response.json()
        assert data["ticker"] == test_ticker.upper()
        assert "forward_multiples" in data
        assert "market_data" in data

    def test_multiples_has_forward_pe(self, test_ticker):
        response = client.get(f"/consensus/multiples?ticker={test_ticker}")
        data = response.json()

        assert "forward_pe" in data["forward_multiples"]
        assert data["forward_multiples"]["forward_pe"] > 0

    def test_multiples_has_forward_ps(self, test_ticker):
        response = client.get(f"/consensus/multiples?ticker={test_ticker}")
        data = response.json()

        assert "forward_ps" in data["forward_multiples"]
        assert data["forward_multiples"]["forward_ps"] > 0

    def test_multiples_has_ev_ebitda(self, test_ticker):
        response = client.get(f"/consensus/multiples?ticker={test_ticker}")
        data = response.json()

        assert "forward_ev_ebitda" in data["forward_multiples"]
        assert data["forward_multiples"]["forward_ev_ebitda"] > 0

    def test_multiples_has_peg_ratio(self, test_ticker):
        response = client.get(f"/consensus/multiples?ticker={test_ticker}")
        data = response.json()

        assert "growth_adjusted" in data
        assert "peg_ratio" in data["growth_adjusted"]

    def test_multiples_has_relative_valuation(self, test_ticker):
        response = client.get(f"/consensus/multiples?ticker={test_ticker}")
        data = response.json()

        assert "relative_valuation" in data
        assert "sector_avg_pe" in data["relative_valuation"]
        assert "pe_premium_discount_pct" in data["relative_valuation"]

    def test_multiples_has_historical_context(self, test_ticker):
        response = client.get(f"/consensus/multiples?ticker={test_ticker}")
        data = response.json()

        assert "historical_context" in data
        assert "historical_avg_pe" in data["historical_context"]
        assert "pe_vs_historical_pct" in data["historical_context"]

    def test_multiples_has_market_data(self, test_ticker):
        response = client.get(f"/consensus/multiples?ticker={test_ticker}")
        data = response.json()

        market_data = data["market_data"]
        assert "current_price" in market_data
        assert "market_cap_bn" in market_data
        assert "enterprise_value_bn" in market_data

    def test_multiples_with_fiscal_year(self, test_ticker, current_year):
        response = client.get(f"/consensus/multiples?ticker={test_ticker}&fiscal_year={current_year}")
        assert response.status_code == 200

        data = response.json()
        assert data["fiscal_year"] == current_year


class TestForwardMultiplesCompareEndpoint:
    """Tests for GET /consensus/multiples/compare - Band C #35."""

    def test_multiples_compare_basic(self):
        response = client.get("/consensus/multiples/compare?tickers=NVDA,AAPL,MSFT")
        assert response.status_code == 200

        data = response.json()
        assert "comparison" in data
        assert len(data["comparison"]) == 3

    def test_multiples_compare_has_summary(self):
        response = client.get("/consensus/multiples/compare?tickers=NVDA,AAPL")
        data = response.json()

        assert "summary" in data
        assert "avg_forward_pe" in data["summary"]
        assert "avg_forward_ev_ebitda" in data["summary"]
        assert "cheapest_pe" in data["summary"]
        assert "most_expensive_pe" in data["summary"]

    def test_multiples_compare_items_have_metrics(self):
        response = client.get("/consensus/multiples/compare?tickers=NVDA,AAPL")
        data = response.json()

        for item in data["comparison"]:
            if "error" not in item:
                assert "ticker" in item
                assert "forward_pe" in item
                assert "forward_ps" in item
                assert "forward_ev_ebitda" in item
                assert "peg_ratio" in item

    def test_multiples_compare_with_fiscal_year(self, current_year):
        response = client.get(f"/consensus/multiples/compare?tickers=NVDA,AAPL&fiscal_year={current_year}")
        assert response.status_code == 200

        data = response.json()
        assert data["fiscal_year"] == current_year
