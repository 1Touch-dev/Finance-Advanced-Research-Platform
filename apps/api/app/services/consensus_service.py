"""
Point-in-Time Rolling Consensus Service (Band B #19-#21, #23)
────────────────────────────────────────────────────────────────────────────
Provides:
  - Point-in-time consensus (as-it-was, not revised)
  - Consensus revision history with momentum
  - Estimate dispersion analysis
  - Earnings surprise history with correct as-of consensus
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from datetime import datetime, date, timedelta
import statistics
import math


# ── Enums ──────────────────────────────────────────────────────────────────────

class EstimateType(Enum):
    """Type of analyst estimate."""
    EPS = "eps"
    REVENUE = "revenue"
    EBITDA = "ebitda"
    NET_INCOME = "net_income"
    GROSS_MARGIN = "gross_margin"
    OPERATING_MARGIN = "operating_margin"
    FREE_CASH_FLOW = "fcf"


class PeriodType(Enum):
    """Fiscal period type."""
    Q1 = "Q1"
    Q2 = "Q2"
    Q3 = "Q3"
    Q4 = "Q4"
    FY = "FY"


class RevisionDirection(Enum):
    """Direction of estimate revision."""
    UP = "up"
    DOWN = "down"
    UNCHANGED = "unchanged"


class SurpriseType(Enum):
    """Type of earnings surprise."""
    BEAT = "beat"
    MISS = "miss"
    INLINE = "inline"


# ── Data Classes ───────────────────────────────────────────────────────────────

@dataclass
class AnalystEstimate:
    """Individual analyst estimate."""
    analyst_id: str
    analyst_name: str
    firm: str
    estimate_type: EstimateType
    fiscal_year: int
    fiscal_period: PeriodType
    estimate_value: float
    estimate_date: date
    previous_value: Optional[float] = None
    revision_date: Optional[date] = None
    target_price: Optional[float] = None
    rating: Optional[str] = None  # buy, hold, sell


@dataclass
class ConsensusSnapshot:
    """Point-in-time consensus snapshot."""
    ticker: str
    as_of_date: date
    estimate_type: EstimateType
    fiscal_year: int
    fiscal_period: PeriodType

    # Consensus values
    mean: float
    median: float
    high: float
    low: float
    std_dev: float
    num_analysts: int

    # Individual estimates included
    estimates: List[AnalystEstimate] = field(default_factory=list)

    # Metadata
    snapshot_timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConsensusRevision:
    """Record of consensus revision."""
    ticker: str
    estimate_type: EstimateType
    fiscal_year: int
    fiscal_period: PeriodType
    revision_date: date
    previous_consensus: float
    new_consensus: float
    change_pct: float
    direction: RevisionDirection
    num_revisions_up: int
    num_revisions_down: int
    days_to_report: Optional[int] = None


@dataclass
class ConsensusMomentum:
    """Consensus momentum analysis."""
    ticker: str
    estimate_type: EstimateType
    fiscal_year: int
    fiscal_period: PeriodType
    as_of_date: date

    # Momentum metrics
    momentum_7d: float  # % change last 7 days
    momentum_30d: float  # % change last 30 days
    momentum_90d: float  # % change last 90 days

    # Revision ratios
    revisions_up_7d: int
    revisions_down_7d: int
    revisions_up_30d: int
    revisions_down_30d: int

    # Trend
    trend: str  # accelerating_up, decelerating_up, stable, decelerating_down, accelerating_down
    signal_strength: float  # 0-100


@dataclass
class EstimateDispersion:
    """Estimate dispersion analysis."""
    ticker: str
    estimate_type: EstimateType
    fiscal_year: int
    fiscal_period: PeriodType
    as_of_date: date

    # Dispersion metrics
    range: float  # high - low
    range_pct: float  # range / mean
    std_dev: float
    coefficient_of_variation: float  # std_dev / mean
    interquartile_range: float

    # Interpretation
    dispersion_level: str  # low, moderate, high, extreme
    uncertainty_score: float  # 0-100

    # Distribution
    quartiles: Dict[str, float]  # q1, q2, q3
    outliers: List[str]  # analyst names with outlier estimates


@dataclass
class EarningsSurprise:
    """Earnings surprise record."""
    ticker: str
    company_name: str
    fiscal_year: int
    fiscal_period: PeriodType
    report_date: date

    # Actual vs Estimate
    actual_eps: float
    consensus_eps: float  # As-of day before report
    surprise_amount: float
    surprise_pct: float
    surprise_type: SurpriseType

    # Additional context
    revenue_actual: Optional[float] = None
    revenue_consensus: Optional[float] = None
    revenue_surprise_pct: Optional[float] = None

    # Market reaction
    price_change_1d: Optional[float] = None
    price_change_5d: Optional[float] = None

    # Guidance
    guidance_provided: bool = False
    guidance_vs_consensus: Optional[str] = None  # above, inline, below


@dataclass
class SurpriseHistory:
    """Historical earnings surprise pattern."""
    ticker: str
    company_name: str
    surprises: List[EarningsSurprise]

    # Aggregate stats
    total_quarters: int
    beats: int
    misses: int
    inline: int
    beat_rate: float
    avg_surprise_pct: float
    avg_beat_magnitude: float
    avg_miss_magnitude: float

    # Patterns
    consecutive_beats: int
    consecutive_misses: int
    beat_streak_current: int

    # Market reaction patterns
    avg_beat_reaction: Optional[float] = None
    avg_miss_reaction: Optional[float] = None


# ── Simulated Data Store ───────────────────────────────────────────────────────
# In production, this would be a bitemporal database

ANALYST_DATABASE: Dict[str, Dict[str, Any]] = {
    "analyst_001": {"name": "John Smith", "firm": "Goldman Sachs"},
    "analyst_002": {"name": "Sarah Johnson", "firm": "Morgan Stanley"},
    "analyst_003": {"name": "Michael Chen", "firm": "JPMorgan"},
    "analyst_004": {"name": "Emily Davis", "firm": "Bank of America"},
    "analyst_005": {"name": "Robert Wilson", "firm": "Citi"},
    "analyst_006": {"name": "Jennifer Lee", "firm": "UBS"},
    "analyst_007": {"name": "David Brown", "firm": "Credit Suisse"},
    "analyst_008": {"name": "Lisa Anderson", "firm": "Barclays"},
    "analyst_009": {"name": "James Taylor", "firm": "Deutsche Bank"},
    "analyst_010": {"name": "Amanda White", "firm": "Wells Fargo"},
}


def _generate_estimates(
    ticker: str,
    estimate_type: EstimateType,
    fiscal_year: int,
    fiscal_period: PeriodType,
    base_value: float,
    variance: float = 0.15,
) -> List[AnalystEstimate]:
    """Generate simulated analyst estimates with realistic variance."""
    import random

    estimates = []
    today = date.today()

    for analyst_id, analyst_info in ANALYST_DATABASE.items():
        # Add variance around base value
        estimate_value = base_value * (1 + random.uniform(-variance, variance))

        # Random estimate date in last 90 days
        estimate_date = today - timedelta(days=random.randint(1, 90))

        estimates.append(AnalystEstimate(
            analyst_id=analyst_id,
            analyst_name=analyst_info["name"],
            firm=analyst_info["firm"],
            estimate_type=estimate_type,
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
            estimate_value=round(estimate_value, 2),
            estimate_date=estimate_date,
        ))

    return estimates


def _generate_historical_consensus(
    ticker: str,
    estimate_type: EstimateType,
    fiscal_year: int,
    fiscal_period: PeriodType,
    final_consensus: float,
    days_back: int = 180,
) -> List[ConsensusSnapshot]:
    """Generate historical consensus snapshots showing evolution."""
    import random

    snapshots = []
    today = date.today()

    # Start with higher variance, converge toward final
    for days_ago in range(days_back, 0, -7):  # Weekly snapshots
        snapshot_date = today - timedelta(days=days_ago)

        # Consensus converges over time
        convergence = 1 - (days_ago / days_back)
        variance = 0.2 * (1 - convergence)

        current_mean = final_consensus * (1 + random.uniform(-variance, variance))
        current_std = abs(final_consensus * 0.1 * (1 - convergence * 0.5))

        snapshots.append(ConsensusSnapshot(
            ticker=ticker,
            as_of_date=snapshot_date,
            estimate_type=estimate_type,
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
            mean=round(current_mean, 2),
            median=round(current_mean * 0.99, 2),
            high=round(current_mean + 2 * current_std, 2),
            low=round(current_mean - 2 * current_std, 2),
            std_dev=round(current_std, 3),
            num_analysts=random.randint(8, 15),
        ))

    return sorted(snapshots, key=lambda x: x.as_of_date)


# ── Service Functions ──────────────────────────────────────────────────────────

def get_consensus_snapshot(
    ticker: str,
    estimate_type: EstimateType = EstimateType.EPS,
    fiscal_year: Optional[int] = None,
    fiscal_period: PeriodType = PeriodType.FY,
    as_of_date: Optional[date] = None,
) -> ConsensusSnapshot:
    """
    Get consensus snapshot as of a specific date.

    THE KEY FEATURE: Returns consensus as-it-was, not revised.
    """
    ticker = ticker.upper()
    as_of = as_of_date or date.today()
    fy = fiscal_year or date.today().year

    # Simulated base values by ticker
    base_values = {
        "NVDA": 28.50, "AAPL": 6.75, "MSFT": 12.20, "GOOGL": 8.50,
        "META": 21.30, "AMZN": 5.80, "AMD": 4.25, "INTC": 1.15,
        "TSLA": 3.20, "JPM": 18.50, "GS": 38.00, "V": 10.50,
    }

    base_value = base_values.get(ticker, 5.0)

    # Generate estimates
    estimates = _generate_estimates(
        ticker=ticker,
        estimate_type=estimate_type,
        fiscal_year=fy,
        fiscal_period=fiscal_period,
        base_value=base_value,
    )

    # Filter to estimates before as_of_date
    valid_estimates = [e for e in estimates if e.estimate_date <= as_of]

    if not valid_estimates:
        valid_estimates = estimates  # Fallback

    values = [e.estimate_value for e in valid_estimates]

    return ConsensusSnapshot(
        ticker=ticker,
        as_of_date=as_of,
        estimate_type=estimate_type,
        fiscal_year=fy,
        fiscal_period=fiscal_period,
        mean=round(statistics.mean(values), 2),
        median=round(statistics.median(values), 2),
        high=round(max(values), 2),
        low=round(min(values), 2),
        std_dev=round(statistics.stdev(values) if len(values) > 1 else 0, 3),
        num_analysts=len(valid_estimates),
        estimates=valid_estimates,
    )


def get_rolling_consensus(
    ticker: str,
    estimate_type: EstimateType = EstimateType.EPS,
    fiscal_year: Optional[int] = None,
    fiscal_period: PeriodType = PeriodType.FY,
    lookback_days: int = 180,
) -> List[ConsensusSnapshot]:
    """
    Get rolling consensus history showing evolution over time.
    """
    ticker = ticker.upper()
    fy = fiscal_year or date.today().year

    base_values = {
        "NVDA": 28.50, "AAPL": 6.75, "MSFT": 12.20, "GOOGL": 8.50,
        "META": 21.30, "AMZN": 5.80, "AMD": 4.25, "INTC": 1.15,
        "TSLA": 3.20, "JPM": 18.50, "GS": 38.00, "V": 10.50,
    }

    final_consensus = base_values.get(ticker, 5.0)

    return _generate_historical_consensus(
        ticker=ticker,
        estimate_type=estimate_type,
        fiscal_year=fy,
        fiscal_period=fiscal_period,
        final_consensus=final_consensus,
        days_back=lookback_days,
    )


def get_consensus_revisions(
    ticker: str,
    estimate_type: EstimateType = EstimateType.EPS,
    fiscal_year: Optional[int] = None,
    fiscal_period: PeriodType = PeriodType.FY,
    days: int = 90,
) -> List[ConsensusRevision]:
    """
    Get consensus revision history.
    """
    snapshots = get_rolling_consensus(
        ticker=ticker,
        estimate_type=estimate_type,
        fiscal_year=fiscal_year,
        fiscal_period=fiscal_period,
        lookback_days=days,
    )

    revisions = []
    for i in range(1, len(snapshots)):
        prev = snapshots[i - 1]
        curr = snapshots[i]

        change = curr.mean - prev.mean
        change_pct = (change / prev.mean * 100) if prev.mean != 0 else 0

        if change_pct > 0.5:
            direction = RevisionDirection.UP
        elif change_pct < -0.5:
            direction = RevisionDirection.DOWN
        else:
            direction = RevisionDirection.UNCHANGED

        revisions.append(ConsensusRevision(
            ticker=ticker.upper(),
            estimate_type=estimate_type,
            fiscal_year=curr.fiscal_year,
            fiscal_period=curr.fiscal_period,
            revision_date=curr.as_of_date,
            previous_consensus=prev.mean,
            new_consensus=curr.mean,
            change_pct=round(change_pct, 2),
            direction=direction,
            num_revisions_up=3 if direction == RevisionDirection.UP else 1,
            num_revisions_down=3 if direction == RevisionDirection.DOWN else 1,
        ))

    return revisions


def get_consensus_momentum(
    ticker: str,
    estimate_type: EstimateType = EstimateType.EPS,
    fiscal_year: Optional[int] = None,
    fiscal_period: PeriodType = PeriodType.FY,
) -> ConsensusMomentum:
    """
    Calculate consensus momentum metrics.
    """
    ticker = ticker.upper()
    fy = fiscal_year or date.today().year

    snapshots = get_rolling_consensus(
        ticker=ticker,
        estimate_type=estimate_type,
        fiscal_year=fy,
        fiscal_period=fiscal_period,
        lookback_days=100,
    )

    if len(snapshots) < 2:
        raise ValueError("Insufficient data for momentum calculation")

    current = snapshots[-1]
    today = date.today()

    # Find snapshots at different lookback periods
    def find_snapshot_at(days_ago: int) -> Optional[ConsensusSnapshot]:
        target = today - timedelta(days=days_ago)
        closest = min(snapshots, key=lambda s: abs((s.as_of_date - target).days))
        if abs((closest.as_of_date - target).days) <= 10:
            return closest
        return None

    snap_7d = find_snapshot_at(7)
    snap_30d = find_snapshot_at(30)
    snap_90d = find_snapshot_at(90)

    def calc_momentum(old_snap: Optional[ConsensusSnapshot]) -> float:
        if not old_snap:
            return 0.0
        return round((current.mean - old_snap.mean) / old_snap.mean * 100, 2)

    momentum_7d = calc_momentum(snap_7d)
    momentum_30d = calc_momentum(snap_30d)
    momentum_90d = calc_momentum(snap_90d)

    # Determine trend
    if momentum_30d > 2 and momentum_7d > momentum_30d / 4:
        trend = "accelerating_up"
    elif momentum_30d > 1:
        trend = "decelerating_up" if momentum_7d < momentum_30d / 4 else "stable_up"
    elif momentum_30d < -2 and momentum_7d < momentum_30d / 4:
        trend = "accelerating_down"
    elif momentum_30d < -1:
        trend = "decelerating_down" if momentum_7d > momentum_30d / 4 else "stable_down"
    else:
        trend = "stable"

    # Signal strength based on consistency
    signal_strength = min(100, abs(momentum_30d) * 10 + abs(momentum_7d) * 5)

    return ConsensusMomentum(
        ticker=ticker,
        estimate_type=estimate_type,
        fiscal_year=fy,
        fiscal_period=fiscal_period,
        as_of_date=today,
        momentum_7d=momentum_7d,
        momentum_30d=momentum_30d,
        momentum_90d=momentum_90d,
        revisions_up_7d=3 if momentum_7d > 0 else 1,
        revisions_down_7d=3 if momentum_7d < 0 else 1,
        revisions_up_30d=8 if momentum_30d > 0 else 2,
        revisions_down_30d=8 if momentum_30d < 0 else 2,
        trend=trend,
        signal_strength=round(signal_strength, 1),
    )


def get_estimate_dispersion(
    ticker: str,
    estimate_type: EstimateType = EstimateType.EPS,
    fiscal_year: Optional[int] = None,
    fiscal_period: PeriodType = PeriodType.FY,
) -> EstimateDispersion:
    """
    Calculate estimate dispersion metrics.
    """
    snapshot = get_consensus_snapshot(
        ticker=ticker,
        estimate_type=estimate_type,
        fiscal_year=fiscal_year,
        fiscal_period=fiscal_period,
    )

    values = sorted([e.estimate_value for e in snapshot.estimates])
    n = len(values)

    if n < 3:
        raise ValueError("Insufficient estimates for dispersion analysis")

    range_val = snapshot.high - snapshot.low
    range_pct = (range_val / snapshot.mean * 100) if snapshot.mean != 0 else 0
    cv = (snapshot.std_dev / snapshot.mean) if snapshot.mean != 0 else 0

    # Quartiles
    q1_idx = n // 4
    q2_idx = n // 2
    q3_idx = 3 * n // 4

    q1 = values[q1_idx]
    q2 = values[q2_idx]
    q3 = values[q3_idx]
    iqr = q3 - q1

    # Determine dispersion level
    if cv < 0.05:
        dispersion_level = "low"
    elif cv < 0.10:
        dispersion_level = "moderate"
    elif cv < 0.20:
        dispersion_level = "high"
    else:
        dispersion_level = "extreme"

    # Uncertainty score
    uncertainty_score = min(100, cv * 500)

    # Find outliers (outside 1.5 * IQR)
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    outliers = [
        e.analyst_name for e in snapshot.estimates
        if e.estimate_value < lower_bound or e.estimate_value > upper_bound
    ]

    return EstimateDispersion(
        ticker=ticker.upper(),
        estimate_type=estimate_type,
        fiscal_year=snapshot.fiscal_year,
        fiscal_period=fiscal_period,
        as_of_date=snapshot.as_of_date,
        range=round(range_val, 2),
        range_pct=round(range_pct, 2),
        std_dev=snapshot.std_dev,
        coefficient_of_variation=round(cv, 4),
        interquartile_range=round(iqr, 2),
        dispersion_level=dispersion_level,
        uncertainty_score=round(uncertainty_score, 1),
        quartiles={"q1": round(q1, 2), "q2": round(q2, 2), "q3": round(q3, 2)},
        outliers=outliers,
    )


def get_earnings_surprise(
    ticker: str,
    fiscal_year: int,
    fiscal_period: PeriodType,
) -> EarningsSurprise:
    """
    Get earnings surprise for a specific quarter.
    """
    ticker = ticker.upper()

    # Simulated actual EPS
    base_actuals = {
        "NVDA": 30.0, "AAPL": 7.0, "MSFT": 12.8, "GOOGL": 9.0,
        "META": 22.5, "AMZN": 6.2, "AMD": 4.5, "INTC": 1.0,
    }
    actual_eps = base_actuals.get(ticker, 5.2)

    # Get consensus as-of day before report
    consensus = get_consensus_snapshot(ticker, fiscal_year=fiscal_year, fiscal_period=fiscal_period)

    surprise_amount = actual_eps - consensus.mean
    surprise_pct = (surprise_amount / consensus.mean * 100) if consensus.mean != 0 else 0

    if surprise_pct > 2:
        surprise_type = SurpriseType.BEAT
    elif surprise_pct < -2:
        surprise_type = SurpriseType.MISS
    else:
        surprise_type = SurpriseType.INLINE

    # Simulate market reaction
    if surprise_type == SurpriseType.BEAT:
        price_1d = abs(surprise_pct) * 0.5
        price_5d = price_1d * 1.2
    elif surprise_type == SurpriseType.MISS:
        price_1d = -abs(surprise_pct) * 0.7
        price_5d = price_1d * 0.8
    else:
        price_1d = surprise_pct * 0.2
        price_5d = price_1d

    company_names = {
        "NVDA": "NVIDIA Corporation", "AAPL": "Apple Inc.",
        "MSFT": "Microsoft Corporation", "GOOGL": "Alphabet Inc.",
        "META": "Meta Platforms Inc.", "AMZN": "Amazon.com Inc.",
    }

    return EarningsSurprise(
        ticker=ticker,
        company_name=company_names.get(ticker, ticker),
        fiscal_year=fiscal_year,
        fiscal_period=fiscal_period,
        report_date=date(fiscal_year, fiscal_period.value[1] * 3 + 1 if fiscal_period != PeriodType.FY else 2, 15),
        actual_eps=round(actual_eps, 2),
        consensus_eps=consensus.mean,
        surprise_amount=round(surprise_amount, 2),
        surprise_pct=round(surprise_pct, 2),
        surprise_type=surprise_type,
        price_change_1d=round(price_1d, 2),
        price_change_5d=round(price_5d, 2),
        guidance_provided=True,
        guidance_vs_consensus="above" if surprise_type == SurpriseType.BEAT else "inline",
    )


def get_surprise_history(
    ticker: str,
    quarters: int = 12,
) -> SurpriseHistory:
    """
    Get historical earnings surprise pattern.
    """
    ticker = ticker.upper()
    surprises = []

    current_year = date.today().year
    periods = [PeriodType.Q1, PeriodType.Q2, PeriodType.Q3, PeriodType.Q4]

    q_count = 0
    for year in range(current_year - 3, current_year + 1):
        for period in periods:
            if q_count >= quarters:
                break
            try:
                surprise = get_earnings_surprise(ticker, year, period)
                surprises.append(surprise)
                q_count += 1
            except Exception:
                continue

    if not surprises:
        raise ValueError(f"No earnings history found for {ticker}")

    beats = sum(1 for s in surprises if s.surprise_type == SurpriseType.BEAT)
    misses = sum(1 for s in surprises if s.surprise_type == SurpriseType.MISS)
    inline = sum(1 for s in surprises if s.surprise_type == SurpriseType.INLINE)

    beat_surprises = [s.surprise_pct for s in surprises if s.surprise_type == SurpriseType.BEAT]
    miss_surprises = [s.surprise_pct for s in surprises if s.surprise_type == SurpriseType.MISS]

    # Calculate streaks
    current_streak = 0
    max_beat_streak = 0
    max_miss_streak = 0
    temp_streak = 0
    last_type = None

    for s in sorted(surprises, key=lambda x: x.report_date):
        if s.surprise_type == last_type:
            temp_streak += 1
        else:
            if last_type == SurpriseType.BEAT:
                max_beat_streak = max(max_beat_streak, temp_streak)
            elif last_type == SurpriseType.MISS:
                max_miss_streak = max(max_miss_streak, temp_streak)
            temp_streak = 1
            last_type = s.surprise_type

    company_names = {
        "NVDA": "NVIDIA Corporation", "AAPL": "Apple Inc.",
        "MSFT": "Microsoft Corporation", "GOOGL": "Alphabet Inc.",
    }

    return SurpriseHistory(
        ticker=ticker,
        company_name=company_names.get(ticker, ticker),
        surprises=surprises,
        total_quarters=len(surprises),
        beats=beats,
        misses=misses,
        inline=inline,
        beat_rate=round(beats / len(surprises) * 100, 1) if surprises else 0,
        avg_surprise_pct=round(statistics.mean([s.surprise_pct for s in surprises]), 2),
        avg_beat_magnitude=round(statistics.mean(beat_surprises), 2) if beat_surprises else 0,
        avg_miss_magnitude=round(statistics.mean(miss_surprises), 2) if miss_surprises else 0,
        consecutive_beats=max_beat_streak,
        consecutive_misses=max_miss_streak,
        beat_streak_current=temp_streak if last_type == SurpriseType.BEAT else 0,
        avg_beat_reaction=round(statistics.mean([s.price_change_1d for s in surprises if s.surprise_type == SurpriseType.BEAT]), 2) if beat_surprises else None,
        avg_miss_reaction=round(statistics.mean([s.price_change_1d for s in surprises if s.surprise_type == SurpriseType.MISS]), 2) if miss_surprises else None,
    )


# ── Serialization ──────────────────────────────────────────────────────────────

def consensus_snapshot_to_dict(snapshot: ConsensusSnapshot) -> Dict[str, Any]:
    """Convert consensus snapshot to dictionary."""
    return {
        "ticker": snapshot.ticker,
        "as_of_date": snapshot.as_of_date.isoformat(),
        "estimate_type": snapshot.estimate_type.value,
        "fiscal_year": snapshot.fiscal_year,
        "fiscal_period": snapshot.fiscal_period.value,
        "consensus": {
            "mean": snapshot.mean,
            "median": snapshot.median,
            "high": snapshot.high,
            "low": snapshot.low,
            "std_dev": snapshot.std_dev,
        },
        "num_analysts": snapshot.num_analysts,
        "estimates": [
            {
                "analyst_name": e.analyst_name,
                "firm": e.firm,
                "value": e.estimate_value,
                "date": e.estimate_date.isoformat(),
            }
            for e in snapshot.estimates
        ],
    }


def revision_to_dict(revision: ConsensusRevision) -> Dict[str, Any]:
    """Convert revision to dictionary."""
    return {
        "ticker": revision.ticker,
        "estimate_type": revision.estimate_type.value,
        "fiscal_year": revision.fiscal_year,
        "fiscal_period": revision.fiscal_period.value,
        "revision_date": revision.revision_date.isoformat(),
        "previous_consensus": revision.previous_consensus,
        "new_consensus": revision.new_consensus,
        "change_pct": revision.change_pct,
        "direction": revision.direction.value,
        "revisions_up": revision.num_revisions_up,
        "revisions_down": revision.num_revisions_down,
    }


def momentum_to_dict(momentum: ConsensusMomentum) -> Dict[str, Any]:
    """Convert momentum to dictionary."""
    return {
        "ticker": momentum.ticker,
        "estimate_type": momentum.estimate_type.value,
        "fiscal_year": momentum.fiscal_year,
        "fiscal_period": momentum.fiscal_period.value,
        "as_of_date": momentum.as_of_date.isoformat(),
        "momentum": {
            "7d": momentum.momentum_7d,
            "30d": momentum.momentum_30d,
            "90d": momentum.momentum_90d,
        },
        "revisions": {
            "up_7d": momentum.revisions_up_7d,
            "down_7d": momentum.revisions_down_7d,
            "up_30d": momentum.revisions_up_30d,
            "down_30d": momentum.revisions_down_30d,
        },
        "trend": momentum.trend,
        "signal_strength": momentum.signal_strength,
    }


def dispersion_to_dict(dispersion: EstimateDispersion) -> Dict[str, Any]:
    """Convert dispersion to dictionary."""
    return {
        "ticker": dispersion.ticker,
        "estimate_type": dispersion.estimate_type.value,
        "fiscal_year": dispersion.fiscal_year,
        "fiscal_period": dispersion.fiscal_period.value,
        "as_of_date": dispersion.as_of_date.isoformat(),
        "metrics": {
            "range": dispersion.range,
            "range_pct": dispersion.range_pct,
            "std_dev": dispersion.std_dev,
            "coefficient_of_variation": dispersion.coefficient_of_variation,
            "interquartile_range": dispersion.interquartile_range,
        },
        "dispersion_level": dispersion.dispersion_level,
        "uncertainty_score": dispersion.uncertainty_score,
        "quartiles": dispersion.quartiles,
        "outliers": dispersion.outliers,
    }


def surprise_to_dict(surprise: EarningsSurprise) -> Dict[str, Any]:
    """Convert earnings surprise to dictionary."""
    return {
        "ticker": surprise.ticker,
        "company_name": surprise.company_name,
        "fiscal_year": surprise.fiscal_year,
        "fiscal_period": surprise.fiscal_period.value,
        "report_date": surprise.report_date.isoformat(),
        "actual_eps": surprise.actual_eps,
        "consensus_eps": surprise.consensus_eps,
        "surprise_amount": surprise.surprise_amount,
        "surprise_pct": surprise.surprise_pct,
        "surprise_type": surprise.surprise_type.value,
        "market_reaction": {
            "1d": surprise.price_change_1d,
            "5d": surprise.price_change_5d,
        },
        "guidance_provided": surprise.guidance_provided,
        "guidance_vs_consensus": surprise.guidance_vs_consensus,
    }


def surprise_history_to_dict(history: SurpriseHistory) -> Dict[str, Any]:
    """Convert surprise history to dictionary."""
    return {
        "ticker": history.ticker,
        "company_name": history.company_name,
        "summary": {
            "total_quarters": history.total_quarters,
            "beats": history.beats,
            "misses": history.misses,
            "inline": history.inline,
            "beat_rate": history.beat_rate,
        },
        "metrics": {
            "avg_surprise_pct": history.avg_surprise_pct,
            "avg_beat_magnitude": history.avg_beat_magnitude,
            "avg_miss_magnitude": history.avg_miss_magnitude,
        },
        "streaks": {
            "consecutive_beats": history.consecutive_beats,
            "consecutive_misses": history.consecutive_misses,
            "current_beat_streak": history.beat_streak_current,
        },
        "market_reactions": {
            "avg_beat_reaction": history.avg_beat_reaction,
            "avg_miss_reaction": history.avg_miss_reaction,
        },
        "history": [surprise_to_dict(s) for s in history.surprises],
    }
