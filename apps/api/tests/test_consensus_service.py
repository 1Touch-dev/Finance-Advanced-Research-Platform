"""
Tests for app.services.consensus_service (Band B #19, #20, #21, #23)
────────────────────────────────────────────────────────────────────────────
Covers:
  - Point-in-time consensus snapshots (#19)
  - Consensus revision history (#20)
  - Estimate dispersion analysis (#21)
  - Earnings surprise history (#23)

No network dependency - uses simulated data store.
"""
from __future__ import annotations

import pytest
from datetime import date, timedelta

from app.services.consensus_service import (
    # Enums
    EstimateType,
    PeriodType,
    SurpriseType,
    RevisionDirection,
    # Functions
    get_consensus_snapshot,
    get_rolling_consensus,
    get_consensus_revisions,
    get_consensus_momentum,
    get_estimate_dispersion,
    get_earnings_surprise,
    get_surprise_history,
    # Serializers
    consensus_snapshot_to_dict,
    revision_to_dict,
    momentum_to_dict,
    dispersion_to_dict,
    surprise_to_dict,
    surprise_history_to_dict,
)


# ── Test Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def test_ticker():
    return "NVDA"


@pytest.fixture
def current_year():
    return date.today().year


# ── Point-in-Time Consensus (#19) ─────────────────────────────────────────────

class TestConsensusSnapshot:
    """Tests for get_consensus_snapshot function."""

    def test_snapshot_returns_valid_structure(self, test_ticker):
        snapshot = get_consensus_snapshot(test_ticker)

        assert snapshot.ticker == test_ticker.upper()
        assert snapshot.estimate_type == EstimateType.EPS
        assert snapshot.fiscal_period == PeriodType.FY
        assert snapshot.num_analysts > 0
        assert len(snapshot.estimates) > 0

    def test_snapshot_has_valid_statistics(self, test_ticker):
        snapshot = get_consensus_snapshot(test_ticker)

        assert snapshot.mean > 0
        assert snapshot.median > 0
        assert snapshot.high >= snapshot.mean
        assert snapshot.low <= snapshot.mean
        assert snapshot.std_dev >= 0

    def test_snapshot_respects_estimate_type(self, test_ticker):
        for est_type in [EstimateType.EPS, EstimateType.REVENUE, EstimateType.EBITDA]:
            snapshot = get_consensus_snapshot(test_ticker, estimate_type=est_type)
            assert snapshot.estimate_type == est_type

    def test_snapshot_respects_fiscal_period(self, test_ticker):
        for period in [PeriodType.Q1, PeriodType.Q2, PeriodType.FY]:
            snapshot = get_consensus_snapshot(test_ticker, fiscal_period=period)
            assert snapshot.fiscal_period == period

    def test_snapshot_respects_as_of_date(self, test_ticker):
        past_date = date.today() - timedelta(days=30)
        snapshot = get_consensus_snapshot(test_ticker, as_of_date=past_date)
        assert snapshot.as_of_date == past_date

    def test_snapshot_serialization(self, test_ticker):
        snapshot = get_consensus_snapshot(test_ticker)
        data = consensus_snapshot_to_dict(snapshot)

        assert "ticker" in data
        assert "consensus" in data
        assert "mean" in data["consensus"]
        assert "median" in data["consensus"]
        assert "estimates" in data
        assert len(data["estimates"]) == len(snapshot.estimates)


# ── Consensus Revision History (#20) ──────────────────────────────────────────

class TestConsensusRevisions:
    """Tests for get_consensus_revisions and get_rolling_consensus."""

    def test_rolling_consensus_returns_snapshots(self, test_ticker):
        snapshots = get_rolling_consensus(test_ticker, lookback_days=90)

        assert len(snapshots) > 0
        # Snapshots should be sorted by date
        for i in range(1, len(snapshots)):
            assert snapshots[i].as_of_date >= snapshots[i-1].as_of_date

    def test_revisions_track_changes(self, test_ticker):
        revisions = get_consensus_revisions(test_ticker, days=90)

        assert len(revisions) > 0
        for rev in revisions:
            assert rev.direction in [
                RevisionDirection.UP,
                RevisionDirection.DOWN,
                RevisionDirection.UNCHANGED
            ]
            assert rev.num_revisions_up >= 0
            assert rev.num_revisions_down >= 0

    def test_momentum_calculation(self, test_ticker):
        momentum = get_consensus_momentum(test_ticker)

        assert momentum.ticker == test_ticker.upper()
        assert isinstance(momentum.momentum_7d, float)
        assert isinstance(momentum.momentum_30d, float)
        assert isinstance(momentum.momentum_90d, float)
        assert momentum.signal_strength >= 0
        assert momentum.trend in [
            "accelerating_up", "decelerating_up", "stable_up",
            "accelerating_down", "decelerating_down", "stable_down",
            "stable"
        ]

    def test_revision_serialization(self, test_ticker):
        revisions = get_consensus_revisions(test_ticker)
        if revisions:
            data = revision_to_dict(revisions[0])
            assert "ticker" in data
            assert "direction" in data
            assert "change_pct" in data

    def test_momentum_serialization(self, test_ticker):
        momentum = get_consensus_momentum(test_ticker)
        data = momentum_to_dict(momentum)

        assert "ticker" in data
        assert "momentum" in data
        assert "7d" in data["momentum"]
        assert "30d" in data["momentum"]
        assert "trend" in data


# ── Estimate Dispersion (#21) ─────────────────────────────────────────────────

class TestEstimateDispersion:
    """Tests for get_estimate_dispersion function - Band B #21."""

    def test_dispersion_basic_metrics(self, test_ticker):
        dispersion = get_estimate_dispersion(test_ticker)

        assert dispersion.ticker == test_ticker.upper()
        assert dispersion.range >= 0
        assert dispersion.range_pct >= 0
        assert dispersion.std_dev >= 0
        assert dispersion.coefficient_of_variation >= 0
        assert dispersion.interquartile_range >= 0

    def test_dispersion_has_quartiles(self, test_ticker):
        dispersion = get_estimate_dispersion(test_ticker)

        assert "q1" in dispersion.quartiles
        assert "q2" in dispersion.quartiles
        assert "q3" in dispersion.quartiles
        # Quartiles should be ordered
        assert dispersion.quartiles["q1"] <= dispersion.quartiles["q2"]
        assert dispersion.quartiles["q2"] <= dispersion.quartiles["q3"]

    def test_dispersion_level_classification(self, test_ticker):
        dispersion = get_estimate_dispersion(test_ticker)

        assert dispersion.dispersion_level in ["low", "moderate", "high", "extreme"]
        # Verify classification logic
        cv = dispersion.coefficient_of_variation
        if cv < 0.05:
            assert dispersion.dispersion_level == "low"
        elif cv < 0.10:
            assert dispersion.dispersion_level == "moderate"
        elif cv < 0.20:
            assert dispersion.dispersion_level == "high"
        else:
            assert dispersion.dispersion_level == "extreme"

    def test_uncertainty_score_bounded(self, test_ticker):
        dispersion = get_estimate_dispersion(test_ticker)

        assert 0 <= dispersion.uncertainty_score <= 100

    def test_outliers_are_analyst_names(self, test_ticker):
        dispersion = get_estimate_dispersion(test_ticker)

        # outliers should be a list (possibly empty)
        assert isinstance(dispersion.outliers, list)
        for outlier in dispersion.outliers:
            assert isinstance(outlier, str)

    def test_dispersion_for_multiple_estimate_types(self, test_ticker):
        for est_type in [EstimateType.EPS, EstimateType.REVENUE]:
            dispersion = get_estimate_dispersion(test_ticker, estimate_type=est_type)
            assert dispersion.estimate_type == est_type

    def test_dispersion_serialization(self, test_ticker):
        dispersion = get_estimate_dispersion(test_ticker)
        data = dispersion_to_dict(dispersion)

        assert "ticker" in data
        assert "metrics" in data
        assert "range" in data["metrics"]
        assert "coefficient_of_variation" in data["metrics"]
        assert "dispersion_level" in data
        assert "uncertainty_score" in data
        assert "quartiles" in data
        assert "outliers" in data


# ── Earnings Surprise History (#23) ───────────────────────────────────────────

class TestEarningsSurprise:
    """Tests for get_earnings_surprise function."""

    def test_surprise_basic_structure(self, test_ticker, current_year):
        surprise = get_earnings_surprise(test_ticker, current_year, PeriodType.Q1)

        assert surprise.ticker == test_ticker.upper()
        assert surprise.fiscal_year == current_year
        assert surprise.fiscal_period == PeriodType.Q1
        assert isinstance(surprise.actual_eps, float)
        assert isinstance(surprise.consensus_eps, float)

    def test_surprise_calculation(self, test_ticker, current_year):
        surprise = get_earnings_surprise(test_ticker, current_year, PeriodType.Q1)

        expected_surprise = surprise.actual_eps - surprise.consensus_eps
        assert abs(surprise.surprise_amount - expected_surprise) < 0.01

    def test_surprise_type_classification(self, test_ticker, current_year):
        surprise = get_earnings_surprise(test_ticker, current_year, PeriodType.Q1)

        assert surprise.surprise_type in [SurpriseType.BEAT, SurpriseType.MISS, SurpriseType.INLINE]

        # Verify classification logic
        pct = surprise.surprise_pct
        if pct > 2:
            assert surprise.surprise_type == SurpriseType.BEAT
        elif pct < -2:
            assert surprise.surprise_type == SurpriseType.MISS
        else:
            assert surprise.surprise_type == SurpriseType.INLINE

    def test_surprise_has_market_reaction(self, test_ticker, current_year):
        surprise = get_earnings_surprise(test_ticker, current_year, PeriodType.Q1)

        assert surprise.price_change_1d is not None
        assert surprise.price_change_5d is not None

    def test_surprise_serialization(self, test_ticker, current_year):
        surprise = get_earnings_surprise(test_ticker, current_year, PeriodType.Q1)
        data = surprise_to_dict(surprise)

        assert "ticker" in data
        assert "actual_eps" in data
        assert "consensus_eps" in data
        assert "surprise_pct" in data
        assert "surprise_type" in data
        assert "market_reaction" in data


class TestSurpriseHistory:
    """Tests for get_surprise_history function - Band B #23."""

    def test_history_returns_multiple_quarters(self, test_ticker):
        history = get_surprise_history(test_ticker, quarters=8)

        assert history.ticker == test_ticker.upper()
        assert len(history.surprises) > 0
        assert history.total_quarters == len(history.surprises)

    def test_history_aggregate_stats(self, test_ticker):
        history = get_surprise_history(test_ticker, quarters=12)

        assert history.beats + history.misses + history.inline == history.total_quarters
        assert 0 <= history.beat_rate <= 100

    def test_history_magnitude_stats(self, test_ticker):
        history = get_surprise_history(test_ticker, quarters=12)

        # These are calculated from actual surprises
        assert isinstance(history.avg_surprise_pct, float)
        if history.beats > 0:
            assert isinstance(history.avg_beat_magnitude, float)
        if history.misses > 0:
            assert isinstance(history.avg_miss_magnitude, float)

    def test_history_streak_tracking(self, test_ticker):
        history = get_surprise_history(test_ticker, quarters=12)

        assert history.consecutive_beats >= 0
        assert history.consecutive_misses >= 0
        assert history.beat_streak_current >= 0

    def test_history_market_reaction_patterns(self, test_ticker):
        history = get_surprise_history(test_ticker, quarters=12)

        if history.beats > 0:
            assert history.avg_beat_reaction is not None
        if history.misses > 0:
            assert history.avg_miss_reaction is not None

    def test_history_serialization(self, test_ticker):
        history = get_surprise_history(test_ticker, quarters=8)
        data = surprise_history_to_dict(history)

        assert "ticker" in data
        assert "summary" in data
        assert "beats" in data["summary"]
        assert "misses" in data["summary"]
        assert "beat_rate" in data["summary"]
        assert "metrics" in data
        assert "avg_surprise_pct" in data["metrics"]
        assert "streaks" in data
        assert "market_reactions" in data
        assert "history" in data

    def test_history_individual_surprises_serialized(self, test_ticker):
        history = get_surprise_history(test_ticker, quarters=4)
        data = surprise_history_to_dict(history)

        assert len(data["history"]) == len(history.surprises)
        for item in data["history"]:
            assert "ticker" in item
            assert "surprise_pct" in item
            assert "surprise_type" in item


# ── Multi-Ticker Support ──────────────────────────────────────────────────────

class TestMultiTickerSupport:
    """Test that all functions work with multiple tickers."""

    @pytest.mark.parametrize("ticker", ["AAPL", "MSFT", "GOOGL", "META", "AMZN"])
    def test_dispersion_multi_ticker(self, ticker):
        dispersion = get_estimate_dispersion(ticker)
        assert dispersion.ticker == ticker.upper()
        assert dispersion.range >= 0

    @pytest.mark.parametrize("ticker", ["AAPL", "MSFT", "GOOGL", "META", "AMZN"])
    def test_surprise_history_multi_ticker(self, ticker):
        history = get_surprise_history(ticker, quarters=4)
        assert history.ticker == ticker.upper()
        assert len(history.surprises) > 0


# ── Edge Cases ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_unknown_ticker_uses_default_base_value(self):
        dispersion = get_estimate_dispersion("UNKNOWNTICKER")
        assert dispersion.ticker == "UNKNOWNTICKER"
        assert dispersion.range >= 0

    def test_lowercase_ticker_normalized(self):
        dispersion = get_estimate_dispersion("nvda")
        assert dispersion.ticker == "NVDA"

    def test_single_quarter_history(self, test_ticker):
        history = get_surprise_history(test_ticker, quarters=1)
        assert history.total_quarters >= 1

    def test_many_quarters_history(self, test_ticker):
        history = get_surprise_history(test_ticker, quarters=20)
        # Should handle gracefully even if fewer quarters exist
        assert history.total_quarters > 0
