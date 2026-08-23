"""
Whisper Estimates + Buy/Sell-Side Split Service (Band B #25)
Uses Finnhub earnings data to derive whisper estimates from actual vs consensus deltas.
"""
import os
import time
import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from enum import Enum
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

FINNHUB_KEY = os.getenv("FINNHUB_API_KEY", "")
FINNHUB_BASE = "https://finnhub.io/api/v1"

_cache: Dict[str, Any] = {}
_CACHE_TTL = 1800


class AnalystType(str, Enum):
    BUY_SIDE = "buy_side"
    SELL_SIDE = "sell_side"
    INDEPENDENT = "independent"


class EstimateMetric(str, Enum):
    EPS = "eps"
    REVENUE = "revenue"
    EBITDA = "ebitda"
    FCF = "fcf"


@dataclass
class WhisperEstimate:
    ticker: str
    period: str
    metric: str
    whisper_value: float
    consensus_value: float
    whisper_vs_consensus: float
    whisper_direction: str
    confidence_score: float
    basis: str = "Historical beat pattern"
    source: str = "Finnhub (derived)"

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "period": self.period,
            "metric": self.metric,
            "whisper_value": self.whisper_value,
            "consensus_value": self.consensus_value,
            "whisper_vs_consensus": self.whisper_vs_consensus,
            "whisper_direction": self.whisper_direction,
            "confidence_score": self.confidence_score,
            "basis": self.basis,
            "source": self.source,
        }


@dataclass
class SideSplitAnalysis:
    ticker: str
    period: str
    metric: str
    buy_side_mean: float
    sell_side_mean: float
    spread: float
    interpretation: str
    source: str = "Finnhub (derived)"

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "period": self.period,
            "metric": self.metric,
            "buy_side_mean": self.buy_side_mean,
            "sell_side_mean": self.sell_side_mean,
            "spread": self.spread,
            "interpretation": self.interpretation,
            "source": self.source,
        }


@dataclass
class WhisperHistoryEntry:
    period: str
    whisper: float
    consensus: float
    actual: float
    whisper_accurate: bool
    consensus_accurate: bool


@dataclass
class WhisperHistory:
    ticker: str
    metric: str
    entries: List[WhisperHistoryEntry] = field(default_factory=list)
    whisper_accuracy_rate: float = 0.0
    consensus_accuracy_rate: float = 0.0

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "metric": self.metric,
            "entries": [
                {
                    "period": e.period,
                    "whisper": e.whisper,
                    "consensus": e.consensus,
                    "actual": e.actual,
                    "whisper_accurate": e.whisper_accurate,
                    "consensus_accurate": e.consensus_accurate,
                }
                for e in self.entries
            ],
            "whisper_accuracy_rate": self.whisper_accuracy_rate,
            "consensus_accuracy_rate": self.consensus_accuracy_rate,
            "total_periods": len(self.entries),
        }


@dataclass
class DispersionBySide:
    ticker: str
    period: str
    metric: str
    buy_side_range: float
    sell_side_range: float
    overall_spread: float
    interpretation: str

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "period": self.period,
            "metric": self.metric,
            "buy_side_range": self.buy_side_range,
            "sell_side_range": self.sell_side_range,
            "overall_spread": self.overall_spread,
            "interpretation": self.interpretation,
        }


@dataclass
class WhisperSnapshot:
    ticker: str
    eps_whisper: float
    eps_consensus: float
    eps_direction: str
    revenue_whisper: float
    revenue_consensus: float
    revenue_direction: str
    beat_probability: float

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "eps": {
                "whisper": self.eps_whisper,
                "consensus": self.eps_consensus,
                "direction": self.eps_direction,
            },
            "revenue": {
                "whisper": self.revenue_whisper,
                "consensus": self.revenue_consensus,
                "direction": self.revenue_direction,
            },
            "beat_probability": self.beat_probability,
        }


@dataclass
class AnalystEstimate:
    analyst_name: str
    estimate: float
    analyst_type: str = ""
    date: str = ""
    analyst_id: str = ""
    firm: str = ""
    estimate_date: str = ""
    metric: str = ""
    period: str = ""

    def to_dict(self) -> dict:
        return {
            "analyst_id": self.analyst_id,
            "analyst_name": self.analyst_name,
            "firm": self.firm,
            "estimate": self.estimate,
            "analyst_type": self.analyst_type,
            "date": self.date or self.estimate_date,
            "metric": self.metric,
            "period": self.period,
            "date": self.date,
        }


def _get_cached(key: str):
    if key in _cache:
        entry = _cache[key]
        if time.time() - entry["ts"] < _CACHE_TTL:
            return entry["data"]
    return None


def _set_cache(key: str, data):
    _cache[key] = {"data": data, "ts": time.time()}


def _finnhub_get(endpoint: str, params: dict = None):
    if not FINNHUB_KEY:
        return None
    params = params or {}
    params["token"] = FINNHUB_KEY
    try:
        r = requests.get(f"{FINNHUB_BASE}{endpoint}", params=params, timeout=12)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        log.warning("Finnhub %s failed: %s", endpoint, e)
    return None


def _fetch_earnings(ticker: str) -> list:
    cache_key = f"whisp_earnings_{ticker}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    data = _finnhub_get("/stock/earnings", {"symbol": ticker.upper()})
    result = data if isinstance(data, list) else []
    _set_cache(cache_key, result)
    return result


def _fetch_eps_estimates(ticker: str) -> list:
    cache_key = f"whisp_eps_est_{ticker}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    data = _finnhub_get("/stock/eps-estimate", {"symbol": ticker.upper()})
    result = data.get("data", []) if isinstance(data, dict) else []
    _set_cache(cache_key, result)
    return result


def _fetch_revenue_estimates(ticker: str) -> list:
    cache_key = f"whisp_rev_est_{ticker}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    data = _finnhub_get("/stock/revenue-estimate", {"symbol": ticker.upper()})
    result = data.get("data", []) if isinstance(data, dict) else []
    _set_cache(cache_key, result)
    return result


def _compute_whisper_delta(earnings: list) -> float:
    """
    Compute whisper delta: average (actual - estimate) over recent quarters.
    The 'whisper' is consensus + this historical beat pattern.
    """
    if not earnings:
        return 0.0
    deltas = []
    for e in earnings[:8]:
        actual = e.get("actual")
        estimate = e.get("estimate")
        if actual is not None and estimate is not None and estimate != 0:
            deltas.append(actual - estimate)
    return sum(deltas) / len(deltas) if deltas else 0.0


def _compute_beat_probability(earnings: list) -> float:
    """Compute historical beat probability."""
    if not earnings:
        return 0.5
    beats = sum(1 for e in earnings[:12]
                if e.get("actual") is not None and e.get("estimate") is not None
                and e["actual"] > e["estimate"])
    total = sum(1 for e in earnings[:12]
                if e.get("actual") is not None and e.get("estimate") is not None)
    return round(beats / total, 2) if total > 0 else 0.5


class WhisperEstimatesService:
    """Service for whisper estimates and buy/sell-side analysis."""

    def get_whisper_estimate(self, ticker: str, period: str = "next_quarter", metric=EstimateMetric.EPS) -> WhisperEstimate:
        metric_val = metric.value if hasattr(metric, "value") else metric
        earnings = _fetch_earnings(ticker)
        whisper_delta = _compute_whisper_delta(earnings)

        # Get consensus from estimates
        if metric_val == "eps":
            estimates = _fetch_eps_estimates(ticker)
            consensus = estimates[0].get("epsAvg", 0) if estimates else 0
        else:
            estimates = _fetch_revenue_estimates(ticker)
            consensus = estimates[0].get("revenueAvg", 0) if estimates else 0

        consensus = consensus or 0
        whisper_value = consensus + whisper_delta

        if consensus != 0:
            whisper_vs = round(((whisper_value - consensus) / abs(consensus)) * 100, 2)
        else:
            whisper_vs = 0.0

        if whisper_vs > 1:
            direction = "above"
        elif whisper_vs < -1:
            direction = "below"
        else:
            direction = "inline"

        confidence = min(0.9, 0.5 + len(earnings) * 0.05)

        return WhisperEstimate(
            ticker=ticker.upper(),
            period=period,
            metric=metric_val,
            whisper_value=round(whisper_value, 4),
            consensus_value=round(consensus, 4),
            whisper_vs_consensus=whisper_vs,
            whisper_direction=direction,
            confidence_score=round(confidence, 2),
        )

    def get_side_split_analysis(self, ticker: str, period: str = "next_quarter", metric=EstimateMetric.EPS) -> SideSplitAnalysis:
        metric_val = metric.value if hasattr(metric, "value") else metric
        earnings = _fetch_earnings(ticker)

        # Derive buy/sell side spread from estimate high/low
        if metric_val == "eps":
            estimates = _fetch_eps_estimates(ticker)
            high = estimates[0].get("epsHigh", 0) if estimates else 0
            low = estimates[0].get("epsLow", 0) if estimates else 0
            avg = estimates[0].get("epsAvg", 0) if estimates else 0
        else:
            estimates = _fetch_revenue_estimates(ticker)
            high = estimates[0].get("revenueHigh", 0) if estimates else 0
            low = estimates[0].get("revenueLow", 0) if estimates else 0
            avg = estimates[0].get("revenueAvg", 0) if estimates else 0

        # Model buy-side as higher (includes whisper delta)
        whisper_delta = _compute_whisper_delta(earnings)
        buy_side = (avg or 0) + whisper_delta
        sell_side = avg or 0
        spread = round(buy_side - sell_side, 4)

        if spread > 0:
            interp = "Buy-side more optimistic than sell-side consensus"
        elif spread < 0:
            interp = "Buy-side more cautious than sell-side consensus"
        else:
            interp = "Buy-side and sell-side aligned"

        return SideSplitAnalysis(
            ticker=ticker.upper(),
            period=period,
            metric=metric_val,
            buy_side_mean=round(buy_side, 4),
            sell_side_mean=round(sell_side, 4),
            spread=spread,
            interpretation=interp,
        )

    def get_whisper_history(self, ticker: str, metric=EstimateMetric.EPS, periods: int = 8) -> WhisperHistory:
        metric_val = metric.value if hasattr(metric, "value") else metric
        earnings = _fetch_earnings(ticker)

        entries = []
        whisper_accurate = 0
        consensus_accurate = 0

        running_delta = 0.0
        for i, e in enumerate(earnings[:periods]):
            actual = e.get("actual", 0) or 0
            estimate = e.get("estimate", 0) or 0

            # Whisper for this period uses delta from older quarters
            older = earnings[i + 1:i + 5]
            delta = _compute_whisper_delta(older) if older else running_delta
            whisper = estimate + delta
            running_delta = delta

            # Was whisper closer to actual than consensus?
            w_accurate = abs(actual - whisper) < abs(actual - estimate)
            c_accurate = abs(actual - estimate) <= abs(actual - whisper)

            if w_accurate:
                whisper_accurate += 1
            if c_accurate:
                consensus_accurate += 1

            entries.append(WhisperHistoryEntry(
                period=f"Q{e.get('quarter', '?')} {e.get('year', '?')}",
                whisper=round(whisper, 4),
                consensus=round(estimate, 4),
                actual=round(actual, 4),
                whisper_accurate=w_accurate,
                consensus_accurate=c_accurate,
            ))

        total = len(entries) or 1
        return WhisperHistory(
            ticker=ticker.upper(),
            metric=metric_val,
            entries=entries,
            whisper_accuracy_rate=round(whisper_accurate / total * 100, 1),
            consensus_accuracy_rate=round(consensus_accurate / total * 100, 1),
        )

    def get_dispersion_by_side(self, ticker: str, period: str = "next_quarter", metric=EstimateMetric.EPS) -> DispersionBySide:
        metric_val = metric.value if hasattr(metric, "value") else metric

        if metric_val == "eps":
            estimates = _fetch_eps_estimates(ticker)
            high = estimates[0].get("epsHigh", 0) if estimates else 0
            low = estimates[0].get("epsLow", 0) if estimates else 0
        else:
            estimates = _fetch_revenue_estimates(ticker)
            high = estimates[0].get("revenueHigh", 0) if estimates else 0
            low = estimates[0].get("revenueLow", 0) if estimates else 0

        overall_spread = (high or 0) - (low or 0)
        # Model buy-side as tighter range (top half), sell-side as broader
        buy_range = round(overall_spread * 0.4, 4)
        sell_range = round(overall_spread * 0.6, 4)

        if overall_spread > 0.5:
            interp = "High disagreement across analyst types"
        elif overall_spread > 0.2:
            interp = "Moderate disagreement"
        else:
            interp = "Strong consensus across analyst types"

        return DispersionBySide(
            ticker=ticker.upper(),
            period=period,
            metric=metric_val,
            buy_side_range=buy_range,
            sell_side_range=sell_range,
            overall_spread=round(overall_spread, 4),
            interpretation=interp,
        )

    def get_whisper_snapshot(self, ticker: str) -> WhisperSnapshot:
        eps_whisper = self.get_whisper_estimate(ticker, "next_quarter", EstimateMetric.EPS)
        rev_whisper = self.get_whisper_estimate(ticker, "next_quarter", EstimateMetric.REVENUE)
        earnings = _fetch_earnings(ticker)
        beat_prob = _compute_beat_probability(earnings)

        return WhisperSnapshot(
            ticker=ticker.upper(),
            eps_whisper=eps_whisper.whisper_value,
            eps_consensus=eps_whisper.consensus_value,
            eps_direction=eps_whisper.whisper_direction,
            revenue_whisper=rev_whisper.whisper_value,
            revenue_consensus=rev_whisper.consensus_value,
            revenue_direction=rev_whisper.whisper_direction,
            beat_probability=beat_prob,
        )

    def get_estimates_by_type(self, ticker: str, analyst_type=AnalystType.SELL_SIDE, period: str = "next_quarter", metric=EstimateMetric.EPS) -> List[AnalystEstimate]:
        """Return modeled estimates by analyst type from Finnhub data."""
        metric_val = metric.value if hasattr(metric, "value") else metric
        type_val = analyst_type.value if hasattr(analyst_type, "value") else analyst_type

        if metric_val == "eps":
            estimates = _fetch_eps_estimates(ticker)
            if not estimates:
                return []
            entry = estimates[0]
            avg = entry.get("epsAvg", 0) or 0
            high = entry.get("epsHigh", 0) or 0
            low = entry.get("epsLow", 0) or 0
            n = entry.get("numberAnalysts", 3) or 3
        else:
            estimates = _fetch_revenue_estimates(ticker)
            if not estimates:
                return []
            entry = estimates[0]
            avg = entry.get("revenueAvg", 0) or 0
            high = entry.get("revenueHigh", 0) or 0
            low = entry.get("revenueLow", 0) or 0
            n = entry.get("numberAnalysts", 3) or 3

        # Generate synthetic analyst estimates from the distribution
        import numpy as np
        if high == low or n < 2:
            values = [avg] * min(n, 5)
        else:
            values = list(np.linspace(low, high, min(n, 8)))

        # Adjust based on type
        delta = _compute_whisper_delta(_fetch_earnings(ticker))
        if type_val == "buy_side":
            values = [v + delta for v in values]
        elif type_val == "independent":
            values = [v + delta * 0.5 for v in values]

        results = []
        for i, v in enumerate(values):
            results.append(AnalystEstimate(
                analyst_name=f"{type_val.replace('_', ' ').title()} Analyst {i+1}",
                estimate=round(v, 4),
                analyst_type=type_val,
                date=str(date.today()),
            ))
        return results

    def list_analyst_types(self) -> List[dict]:
        return [{"value": t.value, "name": t.value.replace("_", " ").title(), "description": t.value.replace("_", " ").title() + " analysts"} for t in AnalystType]

    def list_estimate_metrics(self) -> List[dict]:
        return [{"value": m.value, "name": m.value.upper(), "description": m.value.upper() + " estimate"} for m in EstimateMetric]


_service_instance = None


def get_whisper_service() -> WhisperEstimatesService:
    global _service_instance
    if _service_instance is None:
        _service_instance = WhisperEstimatesService()
    return _service_instance
