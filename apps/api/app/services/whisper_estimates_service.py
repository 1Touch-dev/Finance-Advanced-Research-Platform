"""
Whisper Estimates + Buy/Sell-Side Split Service (Band B #25)
--------------------------------------------------------------------------------
Features:
- Whisper estimates (unofficial/street expectations)
- Buy-side vs sell-side analyst breakdown
- Estimate variance by analyst type
- Historical whisper vs consensus comparison
- Whisper revision tracking
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum
import random


# ── Enums ────────────────────────────────────────────────────────────────────

class AnalystType(Enum):
    """Type of analyst (buy-side or sell-side)."""
    BUY_SIDE = "buy_side"
    SELL_SIDE = "sell_side"
    INDEPENDENT = "independent"


class EstimateMetric(Enum):
    """Types of financial metrics for estimates."""
    EPS = "eps"
    REVENUE = "revenue"
    EBITDA = "ebitda"
    FREE_CASH_FLOW = "fcf"
    GROSS_MARGIN = "gross_margin"
    OPERATING_INCOME = "operating_income"


# ── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class AnalystEstimate:
    """Individual analyst estimate."""
    analyst_id: str
    analyst_name: str
    firm: str
    analyst_type: AnalystType
    estimate: float
    estimate_date: str
    metric: EstimateMetric
    period: str  # e.g., "Q1 2025", "FY 2025"
    is_whisper: bool = False
    confidence: float = 0.8

    def to_dict(self) -> Dict:
        return {
            "analyst_id": self.analyst_id,
            "analyst_name": self.analyst_name,
            "firm": self.firm,
            "analyst_type": self.analyst_type.value,
            "estimate": self.estimate,
            "estimate_date": self.estimate_date,
            "metric": self.metric.value,
            "period": self.period,
            "is_whisper": self.is_whisper,
            "confidence": self.confidence,
        }


@dataclass
class WhisperEstimate:
    """Whisper estimate for a ticker/period."""
    ticker: str
    period: str
    metric: EstimateMetric
    whisper_value: float
    consensus_value: float
    whisper_vs_consensus: float  # percentage difference
    whisper_direction: str  # "above", "below", "inline"
    whisper_sources: int  # number of sources
    last_updated: str
    confidence_score: float  # 0-100

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SideSplitAnalysis:
    """Buy-side vs sell-side analysis."""
    ticker: str
    period: str
    metric: EstimateMetric

    # Buy-side metrics
    buy_side_count: int
    buy_side_mean: float
    buy_side_high: float
    buy_side_low: float
    buy_side_std: float

    # Sell-side metrics
    sell_side_count: int
    sell_side_mean: float
    sell_side_high: float
    sell_side_low: float
    sell_side_std: float

    # Independent metrics
    independent_count: int
    independent_mean: Optional[float]

    # Comparison
    buy_sell_spread: float  # buy_side_mean - sell_side_mean
    buy_sell_spread_pct: float  # as percentage
    historical_spread_percentile: float  # current spread vs history

    # Interpretation
    bullish_side: str  # "buy_side", "sell_side", "neutral"
    interpretation: str

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class WhisperHistory:
    """Historical whisper estimates."""
    ticker: str
    metric: EstimateMetric
    history: List[Dict[str, Any]]  # [{period, whisper, consensus, actual, surprise}]
    whisper_accuracy_rate: float  # % of times whisper was closer to actual than consensus
    avg_whisper_vs_actual_error: float
    avg_consensus_vs_actual_error: float

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class EstimateDispersionBySide:
    """Estimate dispersion breakdown by analyst type."""
    ticker: str
    period: str
    metric: EstimateMetric
    buy_side_dispersion: float
    sell_side_dispersion: float
    overall_dispersion: float
    most_dispersed_side: str
    convergence_trend: str  # "converging", "diverging", "stable"

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class WhisperSnapshot:
    """Quick whisper snapshot for a ticker."""
    ticker: str
    eps_whisper: Optional[float]
    eps_consensus: float
    eps_whisper_vs_consensus: float
    revenue_whisper: Optional[float]
    revenue_consensus: float
    revenue_whisper_vs_consensus: float
    next_earnings_date: str
    whisper_confidence: float
    beat_probability: float  # Based on whisper
    as_of_date: str

    def to_dict(self) -> Dict:
        return asdict(self)


# ── Sample Data ──────────────────────────────────────────────────────────────

# Sell-side firms (research desks at brokerages)
SELL_SIDE_FIRMS = [
    "Goldman Sachs", "Morgan Stanley", "JP Morgan", "Bank of America",
    "Citi", "Barclays", "UBS", "Credit Suisse", "Deutsche Bank",
    "Wells Fargo", "RBC Capital", "Jefferies", "Piper Sandler"
]

# Buy-side firms (investment managers)
BUY_SIDE_FIRMS = [
    "BlackRock", "Vanguard", "Fidelity", "T. Rowe Price",
    "Capital Group", "Wellington", "Invesco", "State Street",
    "PIMCO", "Schroders", "Aberdeen", "Dodge & Cox"
]

# Independent research
INDEPENDENT_FIRMS = [
    "CFRA", "Morningstar", "Argus Research", "ValuEngine",
    "Zacks", "TipRanks", "Estimize"
]


# ── Service Implementation ───────────────────────────────────────────────────

class WhisperEstimatesService:
    """Service for whisper estimates and buy/sell-side analysis."""

    def __init__(self):
        self._cache: Dict[str, Any] = {}

    def _generate_analyst_estimates(
        self,
        ticker: str,
        period: str,
        metric: EstimateMetric,
        base_value: float,
    ) -> List[AnalystEstimate]:
        """Generate simulated analyst estimates."""
        estimates = []
        today = datetime.now()

        # Sell-side estimates (typically more, more public)
        for i, firm in enumerate(SELL_SIDE_FIRMS[:8]):
            estimate = AnalystEstimate(
                analyst_id=f"ss_{ticker}_{i}",
                analyst_name=f"Analyst {i+1}",
                firm=firm,
                analyst_type=AnalystType.SELL_SIDE,
                estimate=round(base_value * random.uniform(0.95, 1.05), 2),
                estimate_date=(today - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d"),
                metric=metric,
                period=period,
                is_whisper=False,
                confidence=random.uniform(0.7, 0.95),
            )
            estimates.append(estimate)

        # Buy-side estimates (fewer, often more bullish)
        for i, firm in enumerate(BUY_SIDE_FIRMS[:5]):
            # Buy-side tends to be slightly more optimistic
            estimate = AnalystEstimate(
                analyst_id=f"bs_{ticker}_{i}",
                analyst_name=f"PM {i+1}",
                firm=firm,
                analyst_type=AnalystType.BUY_SIDE,
                estimate=round(base_value * random.uniform(0.98, 1.08), 2),
                estimate_date=(today - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d"),
                metric=metric,
                period=period,
                is_whisper=False,
                confidence=random.uniform(0.6, 0.85),
            )
            estimates.append(estimate)

        # Independent estimates
        for i, firm in enumerate(INDEPENDENT_FIRMS[:3]):
            estimate = AnalystEstimate(
                analyst_id=f"ind_{ticker}_{i}",
                analyst_name=f"Research {i+1}",
                firm=firm,
                analyst_type=AnalystType.INDEPENDENT,
                estimate=round(base_value * random.uniform(0.94, 1.06), 2),
                estimate_date=(today - timedelta(days=random.randint(1, 30))).strftime("%Y-%m-%d"),
                metric=metric,
                period=period,
                is_whisper=random.random() > 0.5,  # Some are whispers
                confidence=random.uniform(0.5, 0.8),
            )
            estimates.append(estimate)

        return estimates

    def _calculate_whisper(
        self,
        estimates: List[AnalystEstimate],
        consensus_value: float,
    ) -> float:
        """Calculate whisper estimate from available data."""
        # Whisper incorporates:
        # 1. Buy-side estimates (weighted higher)
        # 2. Recent revisions trend
        # 3. Whisper-flagged estimates

        buy_side = [e.estimate for e in estimates if e.analyst_type == AnalystType.BUY_SIDE]
        whispers = [e.estimate for e in estimates if e.is_whisper]

        if whispers:
            whisper_avg = sum(whispers) / len(whispers)
        elif buy_side:
            whisper_avg = sum(buy_side) / len(buy_side)
        else:
            # Default: slightly above consensus
            whisper_avg = consensus_value * 1.02

        return round(whisper_avg, 2)

    def get_whisper_estimate(
        self,
        ticker: str,
        period: str = "next_quarter",
        metric: EstimateMetric = EstimateMetric.EPS,
    ) -> WhisperEstimate:
        """Get whisper estimate for a ticker."""
        # Base consensus values (simulated)
        base_values = {
            "NVDA": 5.50,
            "AAPL": 1.85,
            "MSFT": 3.20,
            "GOOGL": 1.90,
            "META": 5.25,
            "AMZN": 1.10,
            "TSLA": 0.85,
            "AMD": 0.95,
        }
        base = base_values.get(ticker.upper(), random.uniform(1.0, 5.0))

        # Generate estimates
        estimates = self._generate_analyst_estimates(ticker, period, metric, base)

        # Calculate consensus (simple average of all)
        all_values = [e.estimate for e in estimates]
        consensus = round(sum(all_values) / len(all_values), 2)

        # Calculate whisper
        whisper = self._calculate_whisper(estimates, consensus)

        # Whisper vs consensus
        vs_consensus = round((whisper - consensus) / consensus * 100, 2)

        if vs_consensus > 1:
            direction = "above"
        elif vs_consensus < -1:
            direction = "below"
        else:
            direction = "inline"

        return WhisperEstimate(
            ticker=ticker.upper(),
            period=period,
            metric=metric,
            whisper_value=whisper,
            consensus_value=consensus,
            whisper_vs_consensus=vs_consensus,
            whisper_direction=direction,
            whisper_sources=len([e for e in estimates if e.is_whisper or e.analyst_type == AnalystType.BUY_SIDE]),
            last_updated=datetime.now().strftime("%Y-%m-%d %H:%M"),
            confidence_score=round(random.uniform(60, 85), 1),
        )

    def get_side_split_analysis(
        self,
        ticker: str,
        period: str = "next_quarter",
        metric: EstimateMetric = EstimateMetric.EPS,
    ) -> SideSplitAnalysis:
        """Get buy-side vs sell-side analysis."""
        base_values = {
            "NVDA": 5.50, "AAPL": 1.85, "MSFT": 3.20, "GOOGL": 1.90,
            "META": 5.25, "AMZN": 1.10, "TSLA": 0.85, "AMD": 0.95,
        }
        base = base_values.get(ticker.upper(), random.uniform(1.0, 5.0))

        estimates = self._generate_analyst_estimates(ticker, period, metric, base)

        # Split by type
        buy_side = [e.estimate for e in estimates if e.analyst_type == AnalystType.BUY_SIDE]
        sell_side = [e.estimate for e in estimates if e.analyst_type == AnalystType.SELL_SIDE]
        independent = [e.estimate for e in estimates if e.analyst_type == AnalystType.INDEPENDENT]

        # Calculate metrics
        def calc_stats(values: List[float]) -> tuple:
            if not values:
                return 0, 0.0, 0.0, 0.0, 0.0
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            return len(values), mean, max(values), min(values), variance ** 0.5

        bs_count, bs_mean, bs_high, bs_low, bs_std = calc_stats(buy_side)
        ss_count, ss_mean, ss_high, ss_low, ss_std = calc_stats(sell_side)
        ind_count, ind_mean, _, _, _ = calc_stats(independent)

        # Spread analysis
        spread = round(bs_mean - ss_mean, 4) if bs_mean and ss_mean else 0
        spread_pct = round(spread / ss_mean * 100, 2) if ss_mean else 0

        # Interpretation
        if spread_pct > 2:
            bullish_side = "buy_side"
            interpretation = "Buy-side analysts are more bullish, potentially indicating institutional conviction"
        elif spread_pct < -2:
            bullish_side = "sell_side"
            interpretation = "Sell-side analysts are more bullish, potentially due to client positioning"
        else:
            bullish_side = "neutral"
            interpretation = "Buy-side and sell-side estimates are aligned"

        return SideSplitAnalysis(
            ticker=ticker.upper(),
            period=period,
            metric=metric,
            buy_side_count=bs_count,
            buy_side_mean=round(bs_mean, 2),
            buy_side_high=round(bs_high, 2),
            buy_side_low=round(bs_low, 2),
            buy_side_std=round(bs_std, 4),
            sell_side_count=ss_count,
            sell_side_mean=round(ss_mean, 2),
            sell_side_high=round(ss_high, 2),
            sell_side_low=round(ss_low, 2),
            sell_side_std=round(ss_std, 4),
            independent_count=ind_count,
            independent_mean=round(ind_mean, 2) if ind_mean else None,
            buy_sell_spread=spread,
            buy_sell_spread_pct=spread_pct,
            historical_spread_percentile=round(random.uniform(30, 70), 1),
            bullish_side=bullish_side,
            interpretation=interpretation,
        )

    def get_whisper_history(
        self,
        ticker: str,
        metric: EstimateMetric = EstimateMetric.EPS,
        periods: int = 8,
    ) -> WhisperHistory:
        """Get historical whisper accuracy."""
        history = []
        whisper_wins = 0
        whisper_errors = []
        consensus_errors = []

        today = datetime.now()

        for i in range(periods):
            quarter = ((today.month - 1) // 3) - i
            year = today.year
            while quarter < 0:
                quarter += 4
                year -= 1

            period = f"Q{quarter + 1} {year}"

            # Simulated values
            actual = round(random.uniform(1.0, 3.0), 2)
            consensus = round(actual * random.uniform(0.95, 1.05), 2)
            whisper = round(actual * random.uniform(0.97, 1.03), 2)

            whisper_error = abs(whisper - actual)
            consensus_error = abs(consensus - actual)

            if whisper_error < consensus_error:
                whisper_wins += 1

            whisper_errors.append(whisper_error)
            consensus_errors.append(consensus_error)

            history.append({
                "period": period,
                "whisper": whisper,
                "consensus": consensus,
                "actual": actual,
                "whisper_error": round(whisper_error, 4),
                "consensus_error": round(consensus_error, 4),
                "whisper_closer": whisper_error < consensus_error,
                "surprise_vs_whisper": round((actual - whisper) / whisper * 100, 2),
                "surprise_vs_consensus": round((actual - consensus) / consensus * 100, 2),
            })

        return WhisperHistory(
            ticker=ticker.upper(),
            metric=metric,
            history=list(reversed(history)),  # Chronological order
            whisper_accuracy_rate=round(whisper_wins / periods * 100, 1),
            avg_whisper_vs_actual_error=round(sum(whisper_errors) / len(whisper_errors), 4),
            avg_consensus_vs_actual_error=round(sum(consensus_errors) / len(consensus_errors), 4),
        )

    def get_dispersion_by_side(
        self,
        ticker: str,
        period: str = "next_quarter",
        metric: EstimateMetric = EstimateMetric.EPS,
    ) -> EstimateDispersionBySide:
        """Get estimate dispersion broken down by analyst type."""
        base = random.uniform(1.5, 4.0)
        estimates = self._generate_analyst_estimates(ticker, period, metric, base)

        # Calculate dispersion by type
        def calc_dispersion(values: List[float]) -> float:
            if len(values) < 2:
                return 0.0
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            std = variance ** 0.5
            cv = std / mean * 100 if mean else 0
            return round(cv, 2)

        buy_side = [e.estimate for e in estimates if e.analyst_type == AnalystType.BUY_SIDE]
        sell_side = [e.estimate for e in estimates if e.analyst_type == AnalystType.SELL_SIDE]
        all_values = [e.estimate for e in estimates]

        bs_disp = calc_dispersion(buy_side)
        ss_disp = calc_dispersion(sell_side)
        overall = calc_dispersion(all_values)

        if bs_disp > ss_disp:
            most_dispersed = "buy_side"
        elif ss_disp > bs_disp:
            most_dispersed = "sell_side"
        else:
            most_dispersed = "equal"

        # Random convergence trend
        trends = ["converging", "diverging", "stable"]
        trend = random.choice(trends)

        return EstimateDispersionBySide(
            ticker=ticker.upper(),
            period=period,
            metric=metric,
            buy_side_dispersion=bs_disp,
            sell_side_dispersion=ss_disp,
            overall_dispersion=overall,
            most_dispersed_side=most_dispersed,
            convergence_trend=trend,
        )

    def get_whisper_snapshot(self, ticker: str) -> WhisperSnapshot:
        """Get quick whisper snapshot."""
        eps_whisper = self.get_whisper_estimate(ticker, "next_quarter", EstimateMetric.EPS)
        rev_whisper = self.get_whisper_estimate(ticker, "next_quarter", EstimateMetric.REVENUE)

        # Simulate earnings date
        today = datetime.now()
        days_to_earnings = random.randint(7, 45)
        earnings_date = (today + timedelta(days=days_to_earnings)).strftime("%Y-%m-%d")

        # Beat probability based on whisper vs consensus
        if eps_whisper.whisper_direction == "above":
            beat_prob = random.uniform(55, 70)
        elif eps_whisper.whisper_direction == "below":
            beat_prob = random.uniform(35, 50)
        else:
            beat_prob = random.uniform(45, 55)

        return WhisperSnapshot(
            ticker=ticker.upper(),
            eps_whisper=eps_whisper.whisper_value,
            eps_consensus=eps_whisper.consensus_value,
            eps_whisper_vs_consensus=eps_whisper.whisper_vs_consensus,
            revenue_whisper=rev_whisper.whisper_value,
            revenue_consensus=rev_whisper.consensus_value,
            revenue_whisper_vs_consensus=rev_whisper.whisper_vs_consensus,
            next_earnings_date=earnings_date,
            whisper_confidence=eps_whisper.confidence_score,
            beat_probability=round(beat_prob, 1),
            as_of_date=datetime.now().strftime("%Y-%m-%d"),
        )

    def get_estimates_by_type(
        self,
        ticker: str,
        analyst_type: AnalystType,
        period: str = "next_quarter",
        metric: EstimateMetric = EstimateMetric.EPS,
    ) -> List[AnalystEstimate]:
        """Get estimates filtered by analyst type."""
        base = random.uniform(1.5, 4.0)
        estimates = self._generate_analyst_estimates(ticker, period, metric, base)
        return [e for e in estimates if e.analyst_type == analyst_type]

    def list_analyst_types(self) -> List[Dict]:
        """List available analyst types."""
        return [
            {"value": t.value, "description": _ANALYST_TYPE_DESCRIPTIONS.get(t, "")}
            for t in AnalystType
        ]

    def list_estimate_metrics(self) -> List[Dict]:
        """List available estimate metrics."""
        return [
            {"value": m.value, "description": _METRIC_DESCRIPTIONS.get(m, "")}
            for m in EstimateMetric
        ]


# ── Reference Data ───────────────────────────────────────────────────────────

_ANALYST_TYPE_DESCRIPTIONS = {
    AnalystType.BUY_SIDE: "Investment managers (hedge funds, mutual funds, pension funds)",
    AnalystType.SELL_SIDE: "Research analysts at brokerages and investment banks",
    AnalystType.INDEPENDENT: "Independent research providers",
}

_METRIC_DESCRIPTIONS = {
    EstimateMetric.EPS: "Earnings Per Share",
    EstimateMetric.REVENUE: "Total Revenue",
    EstimateMetric.EBITDA: "Earnings Before Interest, Taxes, Depreciation, Amortization",
    EstimateMetric.FREE_CASH_FLOW: "Free Cash Flow",
    EstimateMetric.GROSS_MARGIN: "Gross Margin Percentage",
    EstimateMetric.OPERATING_INCOME: "Operating Income",
}


# ── Singleton ────────────────────────────────────────────────────────────────

_service_instance = None


def get_whisper_service() -> WhisperEstimatesService:
    """Get singleton service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = WhisperEstimatesService()
    return _service_instance
