"""
Guidance vs Actual Tracking Service (Band B #22)
────────────────────────────────────────────────────────────────────────────
Provides:
  - Management guidance tracking (EPS, Revenue, Margins)
  - Guidance vs actual comparison
  - Management credibility scoring
  - Guidance revision history
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from datetime import datetime, date, timedelta
import statistics


# ── Enums ──────────────────────────────────────────────────────────────────────

class GuidanceMetric(Enum):
    """Type of guidance metric."""
    EPS = "eps"
    REVENUE = "revenue"
    GROSS_MARGIN = "gross_margin"
    OPERATING_MARGIN = "operating_margin"
    EBITDA = "ebitda"
    FREE_CASH_FLOW = "fcf"
    CAPEX = "capex"


class GuidanceType(Enum):
    """Type of guidance provided."""
    POINT = "point"  # Single value
    RANGE = "range"  # Low-high range
    QUALITATIVE = "qualitative"  # Above/below/in-line


class GuidanceOutcome(Enum):
    """Outcome vs guidance."""
    BEAT = "beat"
    MET = "met"
    MISSED = "missed"
    SIGNIFICANTLY_BEAT = "significantly_beat"
    SIGNIFICANTLY_MISSED = "significantly_missed"


class GuidanceRevisionDirection(Enum):
    """Direction of guidance revision."""
    RAISED = "raised"
    LOWERED = "lowered"
    MAINTAINED = "maintained"
    NARROWED = "narrowed"
    WIDENED = "widened"
    WITHDRAWN = "withdrawn"


class CredibilityTier(Enum):
    """Management credibility tier."""
    EXCELLENT = "excellent"  # 90%+ meet/beat
    GOOD = "good"  # 75-90%
    AVERAGE = "average"  # 60-75%
    POOR = "poor"  # 40-60%
    UNRELIABLE = "unreliable"  # <40%


# ── Data Classes ───────────────────────────────────────────────────────────────

@dataclass
class GuidanceRecord:
    """Single guidance record."""
    ticker: str
    metric: GuidanceMetric
    fiscal_year: int
    fiscal_period: str  # Q1, Q2, Q3, Q4, FY
    guidance_type: GuidanceType

    # Guidance values
    guidance_low: Optional[float] = None
    guidance_high: Optional[float] = None
    guidance_point: Optional[float] = None
    guidance_midpoint: Optional[float] = None

    # Metadata
    guidance_date: Optional[date] = None
    source: str = "earnings_call"  # earnings_call, investor_day, 8-K, press_release

    # Prior guidance (if revised)
    prior_low: Optional[float] = None
    prior_high: Optional[float] = None
    revision_direction: Optional[GuidanceRevisionDirection] = None


@dataclass
class GuidanceVsActual:
    """Comparison of guidance vs actual."""
    ticker: str
    company_name: str
    metric: GuidanceMetric
    fiscal_year: int
    fiscal_period: str

    # Guidance
    guidance_low: Optional[float] = None
    guidance_high: Optional[float] = None
    guidance_midpoint: Optional[float] = None

    # Actual
    actual_value: float = 0.0

    # Comparison
    vs_midpoint_pct: float = 0.0
    vs_low_pct: float = 0.0
    vs_high_pct: float = 0.0
    outcome: GuidanceOutcome = GuidanceOutcome.MET

    # Report date
    report_date: Optional[date] = None


@dataclass
class GuidanceRevision:
    """Record of guidance revision."""
    ticker: str
    metric: GuidanceMetric
    fiscal_year: int
    fiscal_period: str
    revision_date: date

    # Old guidance
    old_low: Optional[float] = None
    old_high: Optional[float] = None
    old_midpoint: Optional[float] = None

    # New guidance
    new_low: Optional[float] = None
    new_high: Optional[float] = None
    new_midpoint: Optional[float] = None

    # Change
    midpoint_change_pct: float = 0.0
    direction: GuidanceRevisionDirection = GuidanceRevisionDirection.MAINTAINED
    reason: Optional[str] = None


@dataclass
class ManagementCredibility:
    """Management credibility scoring."""
    ticker: str
    company_name: str
    analysis_date: date

    # Overall score
    credibility_score: float  # 0-100
    credibility_tier: CredibilityTier

    # Component scores
    guidance_accuracy_score: float  # How often they meet guidance
    revision_pattern_score: float  # Quality of revisions (early, honest)
    consistency_score: float  # Consistent guidance methodology
    transparency_score: float  # Range width, qualifier usage

    # Historical stats
    total_guidance_periods: int
    beats: int
    meets: int
    misses: int
    beat_rate: float
    meet_or_beat_rate: float

    # Revision patterns
    total_revisions: int
    raises: int
    lowers: int
    revision_tendency: str  # conservative, aggressive, balanced

    # Red flags
    red_flags: List[str] = field(default_factory=list)
    green_flags: List[str] = field(default_factory=list)

    # Recent track record
    last_8_quarters: List[GuidanceVsActual] = field(default_factory=list)


@dataclass
class GuidanceTrack:
    """Full guidance tracking for a ticker."""
    ticker: str
    company_name: str

    # Current guidance
    current_fy_guidance: List[GuidanceRecord] = field(default_factory=list)
    current_q_guidance: List[GuidanceRecord] = field(default_factory=list)

    # Historical comparison
    historical_vs_actual: List[GuidanceVsActual] = field(default_factory=list)

    # Revision history
    revisions: List[GuidanceRevision] = field(default_factory=list)

    # Credibility
    credibility: Optional[ManagementCredibility] = None


# ── Simulated Data ─────────────────────────────────────────────────────────────

COMPANY_GUIDANCE_DATA: Dict[str, Dict[str, Any]] = {
    "NVDA": {
        "name": "NVIDIA Corporation",
        "guidance_style": "conservative",  # Usually beats
        "fy2024_eps_guidance": (24.0, 26.0),
        "fy2024_eps_actual": 27.50,
        "fy2024_rev_guidance": (55_000, 58_000),  # millions
        "fy2024_rev_actual": 60_900,
        "historical_beat_rate": 0.85,
    },
    "AAPL": {
        "name": "Apple Inc.",
        "guidance_style": "conservative",
        "fy2024_eps_guidance": (6.50, 6.80),
        "fy2024_eps_actual": 6.95,
        "fy2024_rev_guidance": (380_000, 395_000),
        "fy2024_rev_actual": 391_000,
        "historical_beat_rate": 0.82,
    },
    "MSFT": {
        "name": "Microsoft Corporation",
        "guidance_style": "balanced",
        "fy2024_eps_guidance": (11.50, 12.00),
        "fy2024_eps_actual": 11.85,
        "fy2024_rev_guidance": (225_000, 230_000),
        "fy2024_rev_actual": 227_000,
        "historical_beat_rate": 0.78,
    },
    "META": {
        "name": "Meta Platforms Inc.",
        "guidance_style": "volatile",  # Wide ranges
        "fy2024_eps_guidance": (18.00, 22.00),
        "fy2024_eps_actual": 21.20,
        "fy2024_rev_guidance": (130_000, 140_000),
        "fy2024_rev_actual": 135_000,
        "historical_beat_rate": 0.72,
    },
    "TSLA": {
        "name": "Tesla Inc.",
        "guidance_style": "aggressive",  # Often misses
        "fy2024_eps_guidance": (4.00, 4.50),
        "fy2024_eps_actual": 3.45,
        "fy2024_rev_guidance": (100_000, 110_000),
        "fy2024_rev_actual": 97_000,
        "historical_beat_rate": 0.55,
    },
    "INTC": {
        "name": "Intel Corporation",
        "guidance_style": "challenged",
        "fy2024_eps_guidance": (1.50, 2.00),
        "fy2024_eps_actual": 1.10,
        "fy2024_rev_guidance": (52_000, 56_000),
        "fy2024_rev_actual": 50_000,
        "historical_beat_rate": 0.45,
    },
}


def _generate_historical_guidance(ticker: str, quarters: int = 12) -> List[GuidanceVsActual]:
    """Generate simulated historical guidance vs actual."""
    import random

    data = COMPANY_GUIDANCE_DATA.get(ticker.upper(), {})
    beat_rate = data.get("historical_beat_rate", 0.65)
    name = data.get("name", ticker)

    history = []
    current_year = date.today().year

    for i in range(quarters):
        q_idx = 4 - (i % 4)  # 4, 3, 2, 1, 4, 3, 2, 1...
        year = current_year - (i // 4) - 1
        period = f"Q{q_idx}"

        # Generate guidance range
        base_eps = 2.0 + random.uniform(-0.5, 1.5) + (beat_rate * 2)
        guidance_low = base_eps * 0.95
        guidance_high = base_eps * 1.05
        guidance_mid = (guidance_low + guidance_high) / 2

        # Generate actual based on beat rate
        if random.random() < beat_rate:
            # Beat
            actual = guidance_high + random.uniform(0.05, 0.30)
            outcome = GuidanceOutcome.BEAT
        elif random.random() < 0.3:
            # Met
            actual = guidance_mid + random.uniform(-0.05, 0.05)
            outcome = GuidanceOutcome.MET
        else:
            # Miss
            actual = guidance_low - random.uniform(0.10, 0.40)
            outcome = GuidanceOutcome.MISSED

        vs_mid = ((actual - guidance_mid) / guidance_mid * 100) if guidance_mid else 0

        history.append(GuidanceVsActual(
            ticker=ticker.upper(),
            company_name=name,
            metric=GuidanceMetric.EPS,
            fiscal_year=year,
            fiscal_period=period,
            guidance_low=round(guidance_low, 2),
            guidance_high=round(guidance_high, 2),
            guidance_midpoint=round(guidance_mid, 2),
            actual_value=round(actual, 2),
            vs_midpoint_pct=round(vs_mid, 2),
            outcome=outcome,
            report_date=date(year, q_idx * 3, 15),  # Q1=Mar, Q2=Jun, Q3=Sep, Q4=Dec
        ))

    return history


# ── Service Functions ──────────────────────────────────────────────────────────

def get_current_guidance(
    ticker: str,
    metric: GuidanceMetric = GuidanceMetric.EPS,
) -> List[GuidanceRecord]:
    """Get current fiscal year guidance."""
    ticker = ticker.upper()
    data = COMPANY_GUIDANCE_DATA.get(ticker, {})

    if not data:
        raise ValueError(f"No guidance data for {ticker}")

    current_fy = date.today().year

    records = []

    # Full year guidance
    if metric == GuidanceMetric.EPS:
        eps_guidance = data.get("fy2024_eps_guidance", (5.0, 6.0))
        records.append(GuidanceRecord(
            ticker=ticker,
            metric=metric,
            fiscal_year=current_fy,
            fiscal_period="FY",
            guidance_type=GuidanceType.RANGE,
            guidance_low=eps_guidance[0],
            guidance_high=eps_guidance[1],
            guidance_midpoint=(eps_guidance[0] + eps_guidance[1]) / 2,
            guidance_date=date(current_fy, 2, 15),
            source="earnings_call",
        ))
    elif metric == GuidanceMetric.REVENUE:
        rev_guidance = data.get("fy2024_rev_guidance", (50_000, 55_000))
        records.append(GuidanceRecord(
            ticker=ticker,
            metric=metric,
            fiscal_year=current_fy,
            fiscal_period="FY",
            guidance_type=GuidanceType.RANGE,
            guidance_low=rev_guidance[0],
            guidance_high=rev_guidance[1],
            guidance_midpoint=(rev_guidance[0] + rev_guidance[1]) / 2,
            guidance_date=date(current_fy, 2, 15),
            source="earnings_call",
        ))

    return records


def get_guidance_vs_actual(
    ticker: str,
    fiscal_year: int,
    fiscal_period: str,
    metric: GuidanceMetric = GuidanceMetric.EPS,
) -> GuidanceVsActual:
    """Get specific guidance vs actual comparison."""
    ticker = ticker.upper()
    data = COMPANY_GUIDANCE_DATA.get(ticker, {})

    if not data:
        raise ValueError(f"No data for {ticker}")

    name = data.get("name", ticker)

    if metric == GuidanceMetric.EPS:
        guidance = data.get("fy2024_eps_guidance", (5.0, 6.0))
        actual = data.get("fy2024_eps_actual", 5.5)
    else:
        guidance = data.get("fy2024_rev_guidance", (50_000, 55_000))
        actual = data.get("fy2024_rev_actual", 52_000)

    midpoint = (guidance[0] + guidance[1]) / 2
    vs_mid = ((actual - midpoint) / midpoint * 100) if midpoint else 0

    if actual > guidance[1]:
        outcome = GuidanceOutcome.SIGNIFICANTLY_BEAT if vs_mid > 5 else GuidanceOutcome.BEAT
    elif actual >= guidance[0]:
        outcome = GuidanceOutcome.MET
    else:
        outcome = GuidanceOutcome.SIGNIFICANTLY_MISSED if vs_mid < -5 else GuidanceOutcome.MISSED

    return GuidanceVsActual(
        ticker=ticker,
        company_name=name,
        metric=metric,
        fiscal_year=fiscal_year,
        fiscal_period=fiscal_period,
        guidance_low=guidance[0],
        guidance_high=guidance[1],
        guidance_midpoint=midpoint,
        actual_value=actual,
        vs_midpoint_pct=round(vs_mid, 2),
        outcome=outcome,
    )


def get_guidance_history(
    ticker: str,
    metric: GuidanceMetric = GuidanceMetric.EPS,
    quarters: int = 12,
) -> List[GuidanceVsActual]:
    """Get historical guidance vs actual."""
    return _generate_historical_guidance(ticker, quarters)


def get_guidance_revisions(
    ticker: str,
    fiscal_year: Optional[int] = None,
) -> List[GuidanceRevision]:
    """Get guidance revision history."""
    ticker = ticker.upper()
    data = COMPANY_GUIDANCE_DATA.get(ticker, {})
    style = data.get("guidance_style", "balanced")

    fy = fiscal_year or date.today().year
    revisions = []

    # Generate simulated revisions based on style
    if style in ["conservative", "balanced"]:
        # Typically raises
        revisions.append(GuidanceRevision(
            ticker=ticker,
            metric=GuidanceMetric.EPS,
            fiscal_year=fy,
            fiscal_period="FY",
            revision_date=date(fy, 5, 1),
            old_low=5.0,
            old_high=5.5,
            old_midpoint=5.25,
            new_low=5.2,
            new_high=5.6,
            new_midpoint=5.4,
            midpoint_change_pct=2.9,
            direction=GuidanceRevisionDirection.RAISED,
            reason="Q1 beat + strong demand",
        ))
    elif style == "aggressive":
        # Typically lowers
        revisions.append(GuidanceRevision(
            ticker=ticker,
            metric=GuidanceMetric.EPS,
            fiscal_year=fy,
            fiscal_period="FY",
            revision_date=date(fy, 5, 1),
            old_low=4.0,
            old_high=4.5,
            old_midpoint=4.25,
            new_low=3.5,
            new_high=4.0,
            new_midpoint=3.75,
            midpoint_change_pct=-11.8,
            direction=GuidanceRevisionDirection.LOWERED,
            reason="Macro headwinds + delayed deliveries",
        ))

    return revisions


def calculate_management_credibility(
    ticker: str,
) -> ManagementCredibility:
    """Calculate comprehensive management credibility score."""
    ticker = ticker.upper()
    data = COMPANY_GUIDANCE_DATA.get(ticker, {})

    if not data:
        raise ValueError(f"No data for {ticker}")

    name = data.get("name", ticker)
    style = data.get("guidance_style", "balanced")
    beat_rate = data.get("historical_beat_rate", 0.65)

    # Get historical data
    history = _generate_historical_guidance(ticker, 12)

    # Count outcomes
    beats = sum(1 for h in history if h.outcome in [GuidanceOutcome.BEAT, GuidanceOutcome.SIGNIFICANTLY_BEAT])
    meets = sum(1 for h in history if h.outcome == GuidanceOutcome.MET)
    misses = sum(1 for h in history if h.outcome in [GuidanceOutcome.MISSED, GuidanceOutcome.SIGNIFICANTLY_MISSED])
    total = len(history)

    actual_beat_rate = beats / total if total > 0 else 0
    meet_or_beat = (beats + meets) / total if total > 0 else 0

    # Calculate component scores
    guidance_accuracy = meet_or_beat * 100
    revision_score = 70 if style == "conservative" else 50 if style == "balanced" else 30
    consistency_score = 80 if style in ["conservative", "balanced"] else 50
    transparency_score = 75 if style != "volatile" else 60

    # Overall score
    overall = (
        guidance_accuracy * 0.40 +
        revision_score * 0.25 +
        consistency_score * 0.20 +
        transparency_score * 0.15
    )

    # Determine tier
    if overall >= 85:
        tier = CredibilityTier.EXCELLENT
    elif overall >= 70:
        tier = CredibilityTier.GOOD
    elif overall >= 55:
        tier = CredibilityTier.AVERAGE
    elif overall >= 40:
        tier = CredibilityTier.POOR
    else:
        tier = CredibilityTier.UNRELIABLE

    # Flags
    red_flags = []
    green_flags = []

    if meet_or_beat >= 0.80:
        green_flags.append("Consistent guidance achiever")
    if style == "conservative":
        green_flags.append("Conservative guidance approach")
    if actual_beat_rate >= 0.75:
        green_flags.append("High beat rate")

    if meet_or_beat < 0.50:
        red_flags.append("Frequently misses guidance")
    if style == "aggressive":
        red_flags.append("Aggressive guidance tendency")
    if style == "volatile":
        red_flags.append("Volatile/wide guidance ranges")

    # Revision patterns
    revisions = get_guidance_revisions(ticker)
    raises = sum(1 for r in revisions if r.direction == GuidanceRevisionDirection.RAISED)
    lowers = sum(1 for r in revisions if r.direction == GuidanceRevisionDirection.LOWERED)

    if raises > lowers:
        tendency = "conservative"
    elif lowers > raises:
        tendency = "aggressive"
    else:
        tendency = "balanced"

    return ManagementCredibility(
        ticker=ticker,
        company_name=name,
        analysis_date=date.today(),
        credibility_score=round(overall, 1),
        credibility_tier=tier,
        guidance_accuracy_score=round(guidance_accuracy, 1),
        revision_pattern_score=round(revision_score, 1),
        consistency_score=round(consistency_score, 1),
        transparency_score=round(transparency_score, 1),
        total_guidance_periods=total,
        beats=beats,
        meets=meets,
        misses=misses,
        beat_rate=round(actual_beat_rate * 100, 1),
        meet_or_beat_rate=round(meet_or_beat * 100, 1),
        total_revisions=len(revisions),
        raises=raises,
        lowers=lowers,
        revision_tendency=tendency,
        red_flags=red_flags,
        green_flags=green_flags,
        last_8_quarters=history[:8],
    )


def get_full_guidance_track(ticker: str) -> GuidanceTrack:
    """Get complete guidance tracking for a ticker."""
    ticker = ticker.upper()
    data = COMPANY_GUIDANCE_DATA.get(ticker, {})

    if not data:
        raise ValueError(f"No data for {ticker}")

    return GuidanceTrack(
        ticker=ticker,
        company_name=data.get("name", ticker),
        current_fy_guidance=get_current_guidance(ticker, GuidanceMetric.EPS),
        historical_vs_actual=get_guidance_history(ticker, quarters=12),
        revisions=get_guidance_revisions(ticker),
        credibility=calculate_management_credibility(ticker),
    )


# ── Serialization ──────────────────────────────────────────────────────────────

def guidance_record_to_dict(record: GuidanceRecord) -> Dict[str, Any]:
    """Convert guidance record to dictionary."""
    return {
        "ticker": record.ticker,
        "metric": record.metric.value,
        "fiscal_year": record.fiscal_year,
        "fiscal_period": record.fiscal_period,
        "guidance_type": record.guidance_type.value,
        "guidance_low": record.guidance_low,
        "guidance_high": record.guidance_high,
        "guidance_midpoint": record.guidance_midpoint,
        "guidance_date": record.guidance_date.isoformat() if record.guidance_date else None,
        "source": record.source,
    }


def vs_actual_to_dict(vs: GuidanceVsActual) -> Dict[str, Any]:
    """Convert guidance vs actual to dictionary."""
    return {
        "ticker": vs.ticker,
        "company_name": vs.company_name,
        "metric": vs.metric.value,
        "fiscal_year": vs.fiscal_year,
        "fiscal_period": vs.fiscal_period,
        "guidance": {
            "low": vs.guidance_low,
            "high": vs.guidance_high,
            "midpoint": vs.guidance_midpoint,
        },
        "actual": vs.actual_value,
        "vs_midpoint_pct": vs.vs_midpoint_pct,
        "outcome": vs.outcome.value,
        "report_date": vs.report_date.isoformat() if vs.report_date else None,
    }


def revision_to_dict(revision: GuidanceRevision) -> Dict[str, Any]:
    """Convert revision to dictionary."""
    return {
        "ticker": revision.ticker,
        "metric": revision.metric.value,
        "fiscal_year": revision.fiscal_year,
        "fiscal_period": revision.fiscal_period,
        "revision_date": revision.revision_date.isoformat(),
        "old_guidance": {
            "low": revision.old_low,
            "high": revision.old_high,
            "midpoint": revision.old_midpoint,
        },
        "new_guidance": {
            "low": revision.new_low,
            "high": revision.new_high,
            "midpoint": revision.new_midpoint,
        },
        "midpoint_change_pct": revision.midpoint_change_pct,
        "direction": revision.direction.value,
        "reason": revision.reason,
    }


def credibility_to_dict(cred: ManagementCredibility) -> Dict[str, Any]:
    """Convert credibility to dictionary."""
    return {
        "ticker": cred.ticker,
        "company_name": cred.company_name,
        "analysis_date": cred.analysis_date.isoformat(),
        "overall_score": cred.credibility_score,
        "tier": cred.credibility_tier.value,
        "component_scores": {
            "guidance_accuracy": cred.guidance_accuracy_score,
            "revision_pattern": cred.revision_pattern_score,
            "consistency": cred.consistency_score,
            "transparency": cred.transparency_score,
        },
        "historical_stats": {
            "total_periods": cred.total_guidance_periods,
            "beats": cred.beats,
            "meets": cred.meets,
            "misses": cred.misses,
            "beat_rate": cred.beat_rate,
            "meet_or_beat_rate": cred.meet_or_beat_rate,
        },
        "revision_patterns": {
            "total_revisions": cred.total_revisions,
            "raises": cred.raises,
            "lowers": cred.lowers,
            "tendency": cred.revision_tendency,
        },
        "flags": {
            "red": cred.red_flags,
            "green": cred.green_flags,
        },
        "recent_quarters": [vs_actual_to_dict(q) for q in cred.last_8_quarters],
    }


def guidance_track_to_dict(track: GuidanceTrack) -> Dict[str, Any]:
    """Convert full guidance track to dictionary."""
    return {
        "ticker": track.ticker,
        "company_name": track.company_name,
        "current_guidance": [guidance_record_to_dict(g) for g in track.current_fy_guidance],
        "historical_vs_actual": [vs_actual_to_dict(h) for h in track.historical_vs_actual],
        "revisions": [revision_to_dict(r) for r in track.revisions],
        "credibility": credibility_to_dict(track.credibility) if track.credibility else None,
    }
