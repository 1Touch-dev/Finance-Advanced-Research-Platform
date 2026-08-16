"""
Valuation Timeline Service (James J3)
Historical valuation multiples over time
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import random


@dataclass
class ValuationDataPoint:
    """Valuation metrics at a point in time"""
    date: str
    pe_ratio: float
    forward_pe: float
    ps_ratio: float
    pb_ratio: float
    ev_ebitda: float
    ev_revenue: float
    price: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "pe_ratio": self.pe_ratio,
            "forward_pe": self.forward_pe,
            "ps_ratio": self.ps_ratio,
            "pb_ratio": self.pb_ratio,
            "ev_ebitda": self.ev_ebitda,
            "ev_revenue": self.ev_revenue,
            "price": self.price,
        }


# Base valuation multiples for mock data
BASE_VALUATIONS = {
    "NVDA": {"pe": 65, "fwd_pe": 45, "ps": 28, "pb": 45, "ev_ebitda": 55, "ev_rev": 25},
    "AAPL": {"pe": 28, "fwd_pe": 25, "ps": 7.5, "pb": 45, "ev_ebitda": 22, "ev_rev": 7},
    "MSFT": {"pe": 35, "fwd_pe": 30, "ps": 12, "pb": 12, "ev_ebitda": 25, "ev_rev": 11},
    "GOOGL": {"pe": 25, "fwd_pe": 22, "ps": 6, "pb": 6, "ev_ebitda": 18, "ev_rev": 5.5},
    "TSLA": {"pe": 75, "fwd_pe": 55, "ps": 8, "pb": 12, "ev_ebitda": 45, "ev_rev": 7},
    "META": {"pe": 28, "fwd_pe": 24, "ps": 8, "pb": 8, "ev_ebitda": 15, "ev_rev": 7.5},
    "AMZN": {"pe": 60, "fwd_pe": 40, "ps": 3, "pb": 8, "ev_ebitda": 18, "ev_rev": 2.8},
}


def get_valuation_timeline(
    ticker: str,
    periods: int = 20,
    interval: str = "quarterly",  # quarterly, monthly, yearly
) -> Dict[str, Any]:
    """Get historical valuation multiples"""
    ticker = ticker.upper()
    base = BASE_VALUATIONS.get(ticker, BASE_VALUATIONS["AAPL"])

    # Generate historical data
    history = []
    base_date = datetime.now()

    if interval == "quarterly":
        days_per_period = 90
    elif interval == "monthly":
        days_per_period = 30
    else:
        days_per_period = 365

    base_price = 100.0

    for i in range(periods, 0, -1):
        date = base_date - timedelta(days=days_per_period * i)

        # Add some variation to multiples
        variation = random.uniform(0.85, 1.15)
        price_change = random.uniform(-5, 8)
        base_price = max(50, base_price + price_change)

        data_point = ValuationDataPoint(
            date=date.strftime("%Y-%m-%d"),
            pe_ratio=round(base["pe"] * variation, 1),
            forward_pe=round(base["fwd_pe"] * variation, 1),
            ps_ratio=round(base["ps"] * variation, 2),
            pb_ratio=round(base["pb"] * variation, 1),
            ev_ebitda=round(base["ev_ebitda"] * variation, 1),
            ev_revenue=round(base["ev_rev"] * variation, 2),
            price=round(base_price, 2),
        )
        history.append(data_point.to_dict())

    # Current values
    current = {
        "pe_ratio": base["pe"],
        "forward_pe": base["fwd_pe"],
        "ps_ratio": base["ps"],
        "pb_ratio": base["pb"],
        "ev_ebitda": base["ev_ebitda"],
        "ev_revenue": base["ev_rev"],
    }

    # Calculate averages
    avg_pe = sum(h["pe_ratio"] for h in history) / len(history)
    avg_fwd_pe = sum(h["forward_pe"] for h in history) / len(history)

    return {
        "ticker": ticker,
        "interval": interval,
        "periods": periods,
        "history": history,
        "current": current,
        "averages": {
            "pe_ratio": round(avg_pe, 1),
            "forward_pe": round(avg_fwd_pe, 1),
            "ps_ratio": round(sum(h["ps_ratio"] for h in history) / len(history), 2),
            "pb_ratio": round(sum(h["pb_ratio"] for h in history) / len(history), 1),
            "ev_ebitda": round(sum(h["ev_ebitda"] for h in history) / len(history), 1),
            "ev_revenue": round(sum(h["ev_revenue"] for h in history) / len(history), 2),
        },
        "vs_average": {
            "pe_ratio": round(((current["pe_ratio"] / avg_pe) - 1) * 100, 1),
            "forward_pe": round(((current["forward_pe"] / avg_fwd_pe) - 1) * 100, 1),
        },
    }


def compare_valuations(tickers: List[str]) -> Dict[str, Any]:
    """Compare current valuations across multiple tickers"""
    comparisons = []

    for ticker in tickers[:10]:
        ticker = ticker.upper()
        base = BASE_VALUATIONS.get(ticker)
        if base:
            comparisons.append({
                "ticker": ticker,
                "pe_ratio": base["pe"],
                "forward_pe": base["fwd_pe"],
                "ps_ratio": base["ps"],
                "pb_ratio": base["pb"],
                "ev_ebitda": base["ev_ebitda"],
                "ev_revenue": base["ev_rev"],
            })

    # Calculate sector averages
    if comparisons:
        sector_avg = {
            "pe_ratio": round(sum(c["pe_ratio"] for c in comparisons) / len(comparisons), 1),
            "forward_pe": round(sum(c["forward_pe"] for c in comparisons) / len(comparisons), 1),
            "ps_ratio": round(sum(c["ps_ratio"] for c in comparisons) / len(comparisons), 2),
            "pb_ratio": round(sum(c["pb_ratio"] for c in comparisons) / len(comparisons), 1),
            "ev_ebitda": round(sum(c["ev_ebitda"] for c in comparisons) / len(comparisons), 1),
            "ev_revenue": round(sum(c["ev_revenue"] for c in comparisons) / len(comparisons), 2),
        }
    else:
        sector_avg = {}

    return {
        "comparisons": comparisons,
        "sector_average": sector_avg,
        "count": len(comparisons),
    }


def get_valuation_bands(ticker: str, periods: int = 20) -> Dict[str, Any]:
    """Get valuation bands (min/max/avg) over time"""
    timeline = get_valuation_timeline(ticker, periods)

    if "error" in timeline:
        return timeline

    history = timeline["history"]

    metrics = ["pe_ratio", "forward_pe", "ps_ratio", "pb_ratio", "ev_ebitda", "ev_revenue"]
    bands = {}

    for metric in metrics:
        values = [h[metric] for h in history]
        bands[metric] = {
            "min": round(min(values), 2),
            "max": round(max(values), 2),
            "avg": round(sum(values) / len(values), 2),
            "current": timeline["current"].get(metric.replace("_ratio", "")),
            "percentile": _calculate_percentile(values, timeline["current"].get(metric.replace("_ratio", ""), values[-1])),
        }

    return {
        "ticker": ticker.upper(),
        "bands": bands,
        "periods": periods,
    }


def _calculate_percentile(values: List[float], current: float) -> int:
    """Calculate percentile of current value"""
    sorted_values = sorted(values)
    count_below = sum(1 for v in sorted_values if v < current)
    return round((count_below / len(sorted_values)) * 100)


def get_valuation_zscore(ticker: str) -> Dict[str, Any]:
    """Get Z-score of current valuation vs history"""
    timeline = get_valuation_timeline(ticker, 20)

    if "error" in timeline:
        return timeline

    history = timeline["history"]
    current = timeline["current"]

    metrics = ["pe_ratio", "forward_pe", "ps_ratio", "pb_ratio"]
    zscores = {}

    for metric in metrics:
        values = [h[metric] for h in history]
        mean = sum(values) / len(values)
        std = (sum((x - mean) ** 2 for x in values) / len(values)) ** 0.5

        current_val = current.get(metric.replace("_ratio", ""), values[-1])
        zscore = (current_val - mean) / std if std > 0 else 0

        zscores[metric] = {
            "zscore": round(zscore, 2),
            "interpretation": _interpret_zscore(zscore),
            "current": current_val,
            "mean": round(mean, 2),
            "std": round(std, 2),
        }

    # Overall valuation signal
    avg_zscore = sum(z["zscore"] for z in zscores.values()) / len(zscores)

    return {
        "ticker": ticker.upper(),
        "zscores": zscores,
        "overall_zscore": round(avg_zscore, 2),
        "signal": _interpret_zscore(avg_zscore),
    }


def _interpret_zscore(zscore: float) -> str:
    """Interpret z-score as valuation signal"""
    if zscore > 2:
        return "extremely_overvalued"
    elif zscore > 1:
        return "overvalued"
    elif zscore > 0.5:
        return "slightly_overvalued"
    elif zscore > -0.5:
        return "fairly_valued"
    elif zscore > -1:
        return "slightly_undervalued"
    elif zscore > -2:
        return "undervalued"
    else:
        return "extremely_undervalued"


def get_sector_valuations(sector: str = "technology") -> Dict[str, Any]:
    """Get valuation metrics for a sector"""
    sector_tickers = {
        "technology": ["NVDA", "AAPL", "MSFT", "GOOGL", "META"],
        "consumer": ["AMZN", "TSLA"],
    }

    tickers = sector_tickers.get(sector.lower(), sector_tickers["technology"])
    return compare_valuations(tickers)


def get_valuation_events(ticker: str, threshold: float = 1.5) -> List[Dict[str, Any]]:
    """Get notable valuation events (peaks/troughs)"""
    timeline = get_valuation_timeline(ticker, 40)

    if "error" in timeline:
        return []

    history = timeline["history"]
    events = []

    # Find PE peaks and troughs
    pe_values = [h["pe_ratio"] for h in history]
    pe_mean = sum(pe_values) / len(pe_values)
    pe_std = (sum((x - pe_mean) ** 2 for x in pe_values) / len(pe_values)) ** 0.5

    for i, h in enumerate(history):
        zscore = (h["pe_ratio"] - pe_mean) / pe_std if pe_std > 0 else 0
        if abs(zscore) > threshold:
            events.append({
                "date": h["date"],
                "metric": "pe_ratio",
                "value": h["pe_ratio"],
                "zscore": round(zscore, 2),
                "type": "peak" if zscore > 0 else "trough",
                "price": h["price"],
            })

    return events
