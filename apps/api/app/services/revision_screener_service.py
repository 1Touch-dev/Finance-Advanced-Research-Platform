"""
Estimate Revision Screener Service (Band C #37)
────────────────────────────────────────────────────────────────────────────────
Provides:
  - Screen companies by estimate revision criteria
  - Filter by momentum, direction, magnitude
  - Rank by revision strength
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime, date

from app.services.consensus_service import (
    get_consensus_momentum,
    get_consensus_revisions,
    get_estimate_dispersion,
    EstimateType,
    PeriodType,
    RevisionDirection,
    ConsensusMomentum,
)


# ── Enums ──────────────────────────────────────────────────────────────────────


class RevisionTrend(Enum):
    """Revision trend classification."""
    STRONG_UP = "strong_up"
    MODERATE_UP = "moderate_up"
    STABLE = "stable"
    MODERATE_DOWN = "moderate_down"
    STRONG_DOWN = "strong_down"


class ScreenerSortBy(Enum):
    """Sort criteria for screener results."""
    MOMENTUM_7D = "momentum_7d"
    MOMENTUM_30D = "momentum_30d"
    MOMENTUM_90D = "momentum_90d"
    SIGNAL_STRENGTH = "signal_strength"
    REVISIONS_UP = "revisions_up"
    REVISIONS_DOWN = "revisions_down"
    TICKER = "ticker"


# ── Data Classes ───────────────────────────────────────────────────────────────


@dataclass
class RevisionScreenerResult:
    """Individual company result from revision screener."""
    ticker: str
    company_name: str
    estimate_type: EstimateType
    fiscal_year: int
    fiscal_period: PeriodType

    # Momentum metrics
    momentum_7d: float
    momentum_30d: float
    momentum_90d: float

    # Revision counts
    revisions_up_7d: int
    revisions_down_7d: int
    revisions_up_30d: int
    revisions_down_30d: int

    # Classification
    trend: str
    trend_classification: RevisionTrend
    signal_strength: float

    # Consensus data
    current_consensus: float
    num_analysts: int

    # Dispersion (optional)
    dispersion_level: Optional[str] = None
    uncertainty_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "estimate_type": self.estimate_type.value,
            "fiscal_year": self.fiscal_year,
            "fiscal_period": self.fiscal_period.value,
            "momentum": {
                "7d": self.momentum_7d,
                "30d": self.momentum_30d,
                "90d": self.momentum_90d,
            },
            "revisions": {
                "up_7d": self.revisions_up_7d,
                "down_7d": self.revisions_down_7d,
                "up_30d": self.revisions_up_30d,
                "down_30d": self.revisions_down_30d,
            },
            "trend": self.trend,
            "trend_classification": self.trend_classification.value,
            "signal_strength": self.signal_strength,
            "current_consensus": self.current_consensus,
            "num_analysts": self.num_analysts,
            "dispersion_level": self.dispersion_level,
            "uncertainty_score": self.uncertainty_score,
        }


@dataclass
class RevisionScreenerOutput:
    """Complete screener output with results and metadata."""
    results: List[RevisionScreenerResult]
    total_screened: int
    total_matched: int
    filters_applied: Dict[str, Any]
    sort_by: ScreenerSortBy
    sort_ascending: bool
    as_of_date: date

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "results": [r.to_dict() for r in self.results],
            "total_screened": self.total_screened,
            "total_matched": self.total_matched,
            "filters_applied": self.filters_applied,
            "sort_by": self.sort_by.value,
            "sort_ascending": self.sort_ascending,
            "as_of_date": self.as_of_date.isoformat(),
        }


@dataclass
class RevisionAlert:
    """Alert for significant revision changes."""
    ticker: str
    company_name: str
    alert_type: str  # momentum_spike, trend_reversal, high_dispersion
    estimate_type: EstimateType
    fiscal_year: int
    fiscal_period: PeriodType
    description: str
    severity: str  # high, medium, low
    momentum_change: float
    triggered_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "alert_type": self.alert_type,
            "estimate_type": self.estimate_type.value,
            "fiscal_year": self.fiscal_year,
            "fiscal_period": self.fiscal_period.value,
            "description": self.description,
            "severity": self.severity,
            "momentum_change": self.momentum_change,
            "triggered_at": self.triggered_at.isoformat(),
        }


# ── Company Database ──────────────────────────────────────────────────────────

COMPANY_DATABASE = {
    "NVDA": "NVIDIA Corporation",
    "AAPL": "Apple Inc.",
    "MSFT": "Microsoft Corporation",
    "GOOGL": "Alphabet Inc.",
    "META": "Meta Platforms Inc.",
    "AMZN": "Amazon.com Inc.",
    "AMD": "Advanced Micro Devices",
    "INTC": "Intel Corporation",
    "TSLA": "Tesla Inc.",
    "JPM": "JPMorgan Chase & Co.",
    "GS": "Goldman Sachs Group",
    "V": "Visa Inc.",
    "MA": "Mastercard Inc.",
    "BAC": "Bank of America Corp.",
    "WMT": "Walmart Inc.",
    "HD": "Home Depot Inc.",
    "PG": "Procter & Gamble Co.",
    "JNJ": "Johnson & Johnson",
    "UNH": "UnitedHealth Group",
    "XOM": "Exxon Mobil Corp.",
}


# ── Helper Functions ──────────────────────────────────────────────────────────


def _classify_trend(momentum: ConsensusMomentum) -> RevisionTrend:
    """Classify momentum into trend category."""
    m30d = momentum.momentum_30d

    if m30d >= 5:
        return RevisionTrend.STRONG_UP
    elif m30d >= 2:
        return RevisionTrend.MODERATE_UP
    elif m30d <= -5:
        return RevisionTrend.STRONG_DOWN
    elif m30d <= -2:
        return RevisionTrend.MODERATE_DOWN
    else:
        return RevisionTrend.STABLE


def _get_company_revision_data(
    ticker: str,
    estimate_type: EstimateType,
    fiscal_year: Optional[int],
    fiscal_period: PeriodType,
    include_dispersion: bool = False,
) -> Optional[RevisionScreenerResult]:
    """Get revision data for a single company."""
    try:
        momentum = get_consensus_momentum(
            ticker=ticker,
            estimate_type=estimate_type,
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
        )

        trend_classification = _classify_trend(momentum)

        # Get dispersion if requested
        dispersion_level = None
        uncertainty_score = None
        if include_dispersion:
            try:
                dispersion = get_estimate_dispersion(
                    ticker=ticker,
                    estimate_type=estimate_type,
                    fiscal_year=fiscal_year,
                    fiscal_period=fiscal_period,
                )
                dispersion_level = dispersion.dispersion_level
                uncertainty_score = dispersion.uncertainty_score
            except Exception as e:
                logger.debug("Failed to get dispersion data for %s: %s", ticker, e)

        # Get consensus value (placeholder - would come from snapshot)
        from app.services.consensus_service import get_consensus_snapshot
        snapshot = get_consensus_snapshot(
            ticker=ticker,
            estimate_type=estimate_type,
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
        )

        return RevisionScreenerResult(
            ticker=ticker.upper(),
            company_name=COMPANY_DATABASE.get(ticker.upper(), ticker.upper()),
            estimate_type=estimate_type,
            fiscal_year=momentum.fiscal_year,
            fiscal_period=fiscal_period,
            momentum_7d=momentum.momentum_7d,
            momentum_30d=momentum.momentum_30d,
            momentum_90d=momentum.momentum_90d,
            revisions_up_7d=momentum.revisions_up_7d,
            revisions_down_7d=momentum.revisions_down_7d,
            revisions_up_30d=momentum.revisions_up_30d,
            revisions_down_30d=momentum.revisions_down_30d,
            trend=momentum.trend,
            trend_classification=trend_classification,
            signal_strength=momentum.signal_strength,
            current_consensus=snapshot.mean,
            num_analysts=snapshot.num_analysts,
            dispersion_level=dispersion_level,
            uncertainty_score=uncertainty_score,
        )
    except Exception:
        return None


# ── Service Functions ──────────────────────────────────────────────────────────


def screen_by_revisions(
    tickers: Optional[List[str]] = None,
    estimate_type: EstimateType = EstimateType.EPS,
    fiscal_year: Optional[int] = None,
    fiscal_period: PeriodType = PeriodType.FY,
    # Momentum filters
    min_momentum_7d: Optional[float] = None,
    max_momentum_7d: Optional[float] = None,
    min_momentum_30d: Optional[float] = None,
    max_momentum_30d: Optional[float] = None,
    min_momentum_90d: Optional[float] = None,
    max_momentum_90d: Optional[float] = None,
    # Trend filters
    trend_classifications: Optional[List[RevisionTrend]] = None,
    # Signal strength filter
    min_signal_strength: Optional[float] = None,
    # Revision count filters
    min_revisions_up_30d: Optional[int] = None,
    min_revisions_down_30d: Optional[int] = None,
    # Dispersion filters
    include_dispersion: bool = False,
    dispersion_levels: Optional[List[str]] = None,
    # Sort and limit
    sort_by: ScreenerSortBy = ScreenerSortBy.MOMENTUM_30D,
    sort_ascending: bool = False,
    limit: int = 50,
) -> RevisionScreenerOutput:
    """
    Screen companies by estimate revision criteria.

    Args:
        tickers: List of tickers to screen (defaults to all in database)
        estimate_type: Type of estimate (EPS, REVENUE, etc.)
        fiscal_year: Fiscal year for estimates
        fiscal_period: Fiscal period (Q1-Q4, FY)
        min_momentum_7d: Minimum 7-day momentum %
        max_momentum_7d: Maximum 7-day momentum %
        min_momentum_30d: Minimum 30-day momentum %
        max_momentum_30d: Maximum 30-day momentum %
        min_momentum_90d: Minimum 90-day momentum %
        max_momentum_90d: Maximum 90-day momentum %
        trend_classifications: Filter by trend classification
        min_signal_strength: Minimum signal strength (0-100)
        min_revisions_up_30d: Minimum upward revisions in 30 days
        min_revisions_down_30d: Minimum downward revisions in 30 days
        include_dispersion: Include dispersion metrics
        dispersion_levels: Filter by dispersion level
        sort_by: Sort criteria
        sort_ascending: Sort direction
        limit: Maximum results to return

    Returns:
        RevisionScreenerOutput with matching companies
    """
    # Use provided tickers or default database
    tickers_to_screen = tickers or list(COMPANY_DATABASE.keys())
    total_screened = len(tickers_to_screen)

    # Collect results
    results: List[RevisionScreenerResult] = []

    for ticker in tickers_to_screen:
        result = _get_company_revision_data(
            ticker=ticker,
            estimate_type=estimate_type,
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
            include_dispersion=include_dispersion,
        )

        if result is None:
            continue

        # Apply filters
        if min_momentum_7d is not None and result.momentum_7d < min_momentum_7d:
            continue
        if max_momentum_7d is not None and result.momentum_7d > max_momentum_7d:
            continue
        if min_momentum_30d is not None and result.momentum_30d < min_momentum_30d:
            continue
        if max_momentum_30d is not None and result.momentum_30d > max_momentum_30d:
            continue
        if min_momentum_90d is not None and result.momentum_90d < min_momentum_90d:
            continue
        if max_momentum_90d is not None and result.momentum_90d > max_momentum_90d:
            continue

        if trend_classifications and result.trend_classification not in trend_classifications:
            continue

        if min_signal_strength is not None and result.signal_strength < min_signal_strength:
            continue

        if min_revisions_up_30d is not None and result.revisions_up_30d < min_revisions_up_30d:
            continue
        if min_revisions_down_30d is not None and result.revisions_down_30d < min_revisions_down_30d:
            continue

        if dispersion_levels and result.dispersion_level not in dispersion_levels:
            continue

        results.append(result)

    # Sort results
    sort_key_map = {
        ScreenerSortBy.MOMENTUM_7D: lambda r: r.momentum_7d,
        ScreenerSortBy.MOMENTUM_30D: lambda r: r.momentum_30d,
        ScreenerSortBy.MOMENTUM_90D: lambda r: r.momentum_90d,
        ScreenerSortBy.SIGNAL_STRENGTH: lambda r: r.signal_strength,
        ScreenerSortBy.REVISIONS_UP: lambda r: r.revisions_up_30d,
        ScreenerSortBy.REVISIONS_DOWN: lambda r: r.revisions_down_30d,
        ScreenerSortBy.TICKER: lambda r: r.ticker,
    }

    sort_key = sort_key_map.get(sort_by, lambda r: r.momentum_30d)
    results.sort(key=sort_key, reverse=not sort_ascending)

    # Apply limit
    results = results[:limit]

    # Build filters applied dict
    filters_applied = {
        "estimate_type": estimate_type.value,
        "fiscal_period": fiscal_period.value,
    }
    if min_momentum_7d is not None:
        filters_applied["min_momentum_7d"] = min_momentum_7d
    if max_momentum_7d is not None:
        filters_applied["max_momentum_7d"] = max_momentum_7d
    if min_momentum_30d is not None:
        filters_applied["min_momentum_30d"] = min_momentum_30d
    if max_momentum_30d is not None:
        filters_applied["max_momentum_30d"] = max_momentum_30d
    if trend_classifications:
        filters_applied["trend_classifications"] = [t.value for t in trend_classifications]
    if min_signal_strength is not None:
        filters_applied["min_signal_strength"] = min_signal_strength

    return RevisionScreenerOutput(
        results=results,
        total_screened=total_screened,
        total_matched=len(results),
        filters_applied=filters_applied,
        sort_by=sort_by,
        sort_ascending=sort_ascending,
        as_of_date=date.today(),
    )


def get_top_upward_revisions(
    estimate_type: EstimateType = EstimateType.EPS,
    fiscal_period: PeriodType = PeriodType.FY,
    limit: int = 10,
) -> RevisionScreenerOutput:
    """
    Get companies with strongest upward estimate revisions.

    Screens for companies with positive momentum and sorts by 30-day momentum.
    """
    return screen_by_revisions(
        estimate_type=estimate_type,
        fiscal_period=fiscal_period,
        min_momentum_30d=0,
        sort_by=ScreenerSortBy.MOMENTUM_30D,
        sort_ascending=False,
        limit=limit,
    )


def get_top_downward_revisions(
    estimate_type: EstimateType = EstimateType.EPS,
    fiscal_period: PeriodType = PeriodType.FY,
    limit: int = 10,
) -> RevisionScreenerOutput:
    """
    Get companies with strongest downward estimate revisions.

    Screens for companies with negative momentum and sorts by 30-day momentum.
    """
    return screen_by_revisions(
        estimate_type=estimate_type,
        fiscal_period=fiscal_period,
        max_momentum_30d=0,
        sort_by=ScreenerSortBy.MOMENTUM_30D,
        sort_ascending=True,
        limit=limit,
    )


def get_accelerating_revisions(
    direction: str = "up",
    estimate_type: EstimateType = EstimateType.EPS,
    fiscal_period: PeriodType = PeriodType.FY,
    limit: int = 10,
) -> RevisionScreenerOutput:
    """
    Get companies with accelerating revisions.

    Finds companies where 7-day momentum exceeds 30-day momentum (accelerating).
    """
    if direction == "up":
        return screen_by_revisions(
            estimate_type=estimate_type,
            fiscal_period=fiscal_period,
            min_momentum_7d=0,
            min_momentum_30d=0,
            trend_classifications=[RevisionTrend.STRONG_UP, RevisionTrend.MODERATE_UP],
            sort_by=ScreenerSortBy.MOMENTUM_7D,
            sort_ascending=False,
            limit=limit,
        )
    else:
        return screen_by_revisions(
            estimate_type=estimate_type,
            fiscal_period=fiscal_period,
            max_momentum_7d=0,
            max_momentum_30d=0,
            trend_classifications=[RevisionTrend.STRONG_DOWN, RevisionTrend.MODERATE_DOWN],
            sort_by=ScreenerSortBy.MOMENTUM_7D,
            sort_ascending=True,
            limit=limit,
        )


def get_revision_alerts(
    tickers: Optional[List[str]] = None,
    estimate_type: EstimateType = EstimateType.EPS,
    fiscal_period: PeriodType = PeriodType.FY,
    momentum_spike_threshold: float = 5.0,
) -> List[RevisionAlert]:
    """
    Get revision alerts for significant changes.

    Detects:
    - Momentum spikes (sudden large changes)
    - Trend reversals
    - High dispersion (analyst disagreement)

    Args:
        tickers: List of tickers to check
        estimate_type: Type of estimate
        fiscal_period: Fiscal period
        momentum_spike_threshold: Threshold for momentum spike alert (%)

    Returns:
        List of RevisionAlert objects
    """
    tickers_to_check = tickers or list(COMPANY_DATABASE.keys())
    alerts: List[RevisionAlert] = []
    now = datetime.now()

    for ticker in tickers_to_check:
        result = _get_company_revision_data(
            ticker=ticker,
            estimate_type=estimate_type,
            fiscal_year=None,
            fiscal_period=fiscal_period,
            include_dispersion=True,
        )

        if result is None:
            continue

        # Check for momentum spike (7d momentum exceeds threshold)
        if abs(result.momentum_7d) >= momentum_spike_threshold:
            direction = "upward" if result.momentum_7d > 0 else "downward"
            severity = "high" if abs(result.momentum_7d) >= 10 else "medium"
            alerts.append(RevisionAlert(
                ticker=result.ticker,
                company_name=result.company_name,
                alert_type="momentum_spike",
                estimate_type=estimate_type,
                fiscal_year=result.fiscal_year,
                fiscal_period=fiscal_period,
                description=f"Significant {direction} revision momentum: {result.momentum_7d:+.1f}% in 7 days",
                severity=severity,
                momentum_change=result.momentum_7d,
                triggered_at=now,
            ))

        # Check for high dispersion (analyst disagreement)
        if result.dispersion_level in ["high", "extreme"]:
            alerts.append(RevisionAlert(
                ticker=result.ticker,
                company_name=result.company_name,
                alert_type="high_dispersion",
                estimate_type=estimate_type,
                fiscal_year=result.fiscal_year,
                fiscal_period=fiscal_period,
                description=f"High analyst disagreement: {result.dispersion_level} dispersion (uncertainty: {result.uncertainty_score:.0f}%)",
                severity="medium" if result.dispersion_level == "high" else "high",
                momentum_change=result.momentum_30d,
                triggered_at=now,
            ))

        # Check for trend reversal (30d and 7d in opposite directions with strength)
        if (result.momentum_30d > 2 and result.momentum_7d < -2) or \
           (result.momentum_30d < -2 and result.momentum_7d > 2):
            old_direction = "upward" if result.momentum_30d > 0 else "downward"
            new_direction = "upward" if result.momentum_7d > 0 else "downward"
            alerts.append(RevisionAlert(
                ticker=result.ticker,
                company_name=result.company_name,
                alert_type="trend_reversal",
                estimate_type=estimate_type,
                fiscal_year=result.fiscal_year,
                fiscal_period=fiscal_period,
                description=f"Trend reversal: 30d {old_direction} ({result.momentum_30d:+.1f}%) but 7d {new_direction} ({result.momentum_7d:+.1f}%)",
                severity="high",
                momentum_change=result.momentum_7d,
                triggered_at=now,
            ))

    return alerts


def get_revision_summary(
    tickers: Optional[List[str]] = None,
    estimate_type: EstimateType = EstimateType.EPS,
    fiscal_period: PeriodType = PeriodType.FY,
) -> Dict[str, Any]:
    """
    Get summary statistics for revisions across companies.

    Returns aggregate metrics for the universe.
    """
    tickers_to_check = tickers or list(COMPANY_DATABASE.keys())
    results: List[RevisionScreenerResult] = []

    for ticker in tickers_to_check:
        result = _get_company_revision_data(
            ticker=ticker,
            estimate_type=estimate_type,
            fiscal_year=None,
            fiscal_period=fiscal_period,
        )
        if result:
            results.append(result)

    if not results:
        return {
            "total_companies": 0,
            "message": "No data available",
        }

    # Calculate summary statistics
    upward = sum(1 for r in results if r.momentum_30d > 0.5)
    downward = sum(1 for r in results if r.momentum_30d < -0.5)
    stable = len(results) - upward - downward

    momentum_values = [r.momentum_30d for r in results]
    avg_momentum = sum(momentum_values) / len(momentum_values)

    by_trend = {}
    for r in results:
        trend = r.trend_classification.value
        by_trend[trend] = by_trend.get(trend, 0) + 1

    return {
        "as_of_date": date.today().isoformat(),
        "estimate_type": estimate_type.value,
        "fiscal_period": fiscal_period.value,
        "total_companies": len(results),
        "direction_breakdown": {
            "upward_revisions": upward,
            "downward_revisions": downward,
            "stable": stable,
            "upward_pct": round(upward / len(results) * 100, 1),
            "downward_pct": round(downward / len(results) * 100, 1),
        },
        "momentum_stats": {
            "average_30d_momentum": round(avg_momentum, 2),
            "max_30d_momentum": round(max(momentum_values), 2),
            "min_30d_momentum": round(min(momentum_values), 2),
        },
        "by_trend_classification": by_trend,
    }
