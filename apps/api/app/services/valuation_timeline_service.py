"""
Valuation Timeline Service (James J3)
Historical valuation multiples over time using yfinance.
"""

import logging
import time as time_module
from typing import Dict, Any, Optional, List

log = logging.getLogger(__name__)


# ── TTL Cache (30 min) ────────────────────────────────────────────────────────

class _TTLCache:
    def __init__(self, ttl_seconds: int = 1800):
        self._ttl = ttl_seconds
        self._store: Dict[str, Any] = {}
        self._ts: Dict[str, float] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self._store and time_module.time() - self._ts[key] < self._ttl:
            return self._store[key]
        self._store.pop(key, None)
        self._ts.pop(key, None)
        return None

    def set(self, key: str, value: Any):
        self._store[key] = value
        self._ts[key] = time_module.time()


_cache = _TTLCache(ttl_seconds=1800)


def _import_yf():
    try:
        import yfinance as yf
        return yf
    except ImportError:
        log.warning("yfinance not installed")
        return None


def _compute_trailing_pe_series(ticker_obj, period: str = "5y") -> List[Dict[str, Any]]:
    """
    Compute historical P/E by dividing price at each point by trailing EPS.
    Since yfinance doesn't provide historical P/E directly, we approximate using
    quarterly earnings and price history.
    """
    try:
        hist = ticker_obj.history(period=period, interval="1mo")
        if hist.empty:
            return []

        earnings = ticker_obj.earnings_history if hasattr(ticker_obj, "earnings_history") else None
        info = ticker_obj.info
        current_eps = info.get("trailingEps")

        if not current_eps or current_eps <= 0:
            return []

        results = []
        prices = hist["Close"]

        for dt, price in prices.items():
            pe = float(price) / current_eps
            results.append({
                "date": str(dt.date()) if hasattr(dt, "date") else str(dt)[:10],
                "price": round(float(price), 2),
                "pe_ratio": round(pe, 2),
            })

        return results
    except Exception as e:
        log.debug("_compute_trailing_pe_series error: %s", e)
        return []


# ── Public API ────────────────────────────────────────────────────────────────

def get_valuation_timeline(
    ticker: str, periods: int = 20, interval: str = "quarterly"
) -> Dict[str, Any]:
    """
    Historical valuation multiples: P/E, P/B, EV/EBITDA approximated over time.
    Uses monthly price data divided by current fundamental metrics as approximation.
    """
    yf = _import_yf()
    if not yf:
        return {}

    cache_key = f"val_timeline:{ticker}:{periods}:{interval}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    try:
        t = yf.Ticker(ticker)
        info = t.info

        period_map = {"quarterly": "5y", "monthly": "2y", "yearly": "10y"}
        yf_period = period_map.get(interval, "5y")

        hist = t.history(period=yf_period, interval="1mo")
        if hist.empty:
            return {}

        current_eps = info.get("trailingEps", 0) or 0
        book_per_share = info.get("bookValue", 0) or 0
        current_ev_ebitda = info.get("enterpriseToEbitda", 0) or 0
        current_ps = info.get("priceToSalesTrailing12Months", 0) or 0

        step = 3 if interval == "quarterly" else (1 if interval == "monthly" else 12)
        prices = hist["Close"]

        timeline = []
        indices = list(range(0, len(prices), step))[-periods:]

        for i in indices:
            dt = prices.index[i]
            price = float(prices.iloc[i])

            entry = {
                "date": str(dt.date()) if hasattr(dt, "date") else str(dt)[:10],
                "price": round(price, 2),
            }

            if current_eps and current_eps > 0:
                entry["pe_ratio"] = round(price / current_eps, 2)
            if book_per_share and book_per_share > 0:
                entry["pb_ratio"] = round(price / book_per_share, 2)
            if current_ev_ebitda:
                price_ratio = price / float(prices.iloc[-1]) if prices.iloc[-1] != 0 else 1
                entry["ev_ebitda"] = round(current_ev_ebitda * price_ratio, 2)
            if current_ps:
                price_ratio = price / float(prices.iloc[-1]) if prices.iloc[-1] != 0 else 1
                entry["ps_ratio"] = round(current_ps * price_ratio, 2)

            timeline.append(entry)

        result = {
            "ticker": ticker,
            "name": info.get("shortName", ticker),
            "interval": interval,
            "current_metrics": {
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "pb_ratio": info.get("priceToBook"),
                "ev_ebitda": info.get("enterpriseToEbitda"),
                "ps_ratio": info.get("priceToSalesTrailing12Months"),
                "price": info.get("currentPrice"),
            },
            "timeline": timeline,
            "count": len(timeline),
        }
        _cache.set(cache_key, result)
        return result
    except Exception as e:
        log.warning("valuation_timeline error for %s: %s", ticker, e)
        return {}


def compare_valuations(tickers: List[str]) -> Dict[str, Any]:
    """Compare current valuation multiples across multiple tickers."""
    yf = _import_yf()
    if not yf:
        return {}

    cache_key = f"val_compare:{sorted(tickers)}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    comparisons = []
    for t in tickers:
        try:
            info = yf.Ticker(t).info
            comparisons.append({
                "ticker": t,
                "name": info.get("shortName", t),
                "sector": info.get("sector"),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "pb_ratio": info.get("priceToBook"),
                "ps_ratio": info.get("priceToSalesTrailing12Months"),
                "ev_ebitda": info.get("enterpriseToEbitda"),
                "ev_revenue": info.get("enterpriseToRevenue"),
                "peg_ratio": info.get("pegRatio"),
                "dividend_yield": info.get("dividendYield"),
                "market_cap": info.get("marketCap"),
            })
        except Exception as e:
            log.debug("compare_valuations skip %s: %s", t, e)

    if not comparisons:
        return {}

    metrics = ["pe_ratio", "forward_pe", "pb_ratio", "ps_ratio", "ev_ebitda"]
    averages = {}
    for m in metrics:
        vals = [c[m] for c in comparisons if c.get(m) is not None]
        averages[m] = round(sum(vals) / len(vals), 2) if vals else None

    result = {
        "comparisons": comparisons,
        "averages": averages,
        "count": len(comparisons),
    }
    _cache.set(cache_key, result)
    return result


def get_valuation_bands(ticker: str, periods: int = 20) -> Dict[str, Any]:
    """
    Valuation bands showing historical range (high/low/avg) for P/E.
    Useful for identifying if current valuation is cheap or expensive relative to history.
    """
    yf = _import_yf()
    if not yf:
        return {}

    cache_key = f"val_bands:{ticker}:{periods}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    try:
        t = yf.Ticker(ticker)
        info = t.info
        current_eps = info.get("trailingEps", 0)

        if not current_eps or current_eps <= 0:
            return {"ticker": ticker, "note": "Cannot compute bands without positive EPS"}

        hist = t.history(period="5y", interval="1mo")
        if hist.empty:
            return {}

        pe_values = []
        for price in hist["Close"]:
            pe = float(price) / current_eps
            if 0 < pe < 200:
                pe_values.append(pe)

        if not pe_values:
            return {}

        pe_values.sort()
        n = len(pe_values)
        current_pe = info.get("trailingPE") or (info.get("currentPrice", 0) / current_eps)

        bands = {
            "min": round(pe_values[0], 2),
            "p25": round(pe_values[int(n * 0.25)], 2),
            "median": round(pe_values[int(n * 0.5)], 2),
            "mean": round(sum(pe_values) / n, 2),
            "p75": round(pe_values[int(n * 0.75)], 2),
            "max": round(pe_values[-1], 2),
        }

        percentile = sum(1 for v in pe_values if v <= current_pe) / n * 100

        result = {
            "ticker": ticker,
            "name": info.get("shortName", ticker),
            "metric": "trailing_pe",
            "current_value": round(current_pe, 2) if current_pe else None,
            "percentile": round(percentile, 1),
            "bands": bands,
            "assessment": (
                "cheap" if percentile < 25
                else "below_average" if percentile < 50
                else "above_average" if percentile < 75
                else "expensive"
            ),
            "data_points": n,
        }
        _cache.set(cache_key, result)
        return result
    except Exception as e:
        log.warning("valuation_bands error for %s: %s", ticker, e)
        return {}


def get_valuation_zscore(ticker: str) -> Dict[str, Any]:
    """Z-score of current valuation vs historical (how many std devs from mean)."""
    yf = _import_yf()
    if not yf:
        return {}

    try:
        t = yf.Ticker(ticker)
        info = t.info
        current_eps = info.get("trailingEps", 0)

        if not current_eps or current_eps <= 0:
            return {}

        hist = t.history(period="5y", interval="1mo")
        if hist.empty:
            return {}

        pe_values = [float(p) / current_eps for p in hist["Close"] if float(p) / current_eps > 0]
        if len(pe_values) < 10:
            return {}

        mean_pe = sum(pe_values) / len(pe_values)
        variance = sum((v - mean_pe) ** 2 for v in pe_values) / len(pe_values)
        std_pe = variance ** 0.5

        current_pe = info.get("trailingPE") or (info.get("currentPrice", 0) / current_eps)
        z_score = (current_pe - mean_pe) / std_pe if std_pe > 0 else 0

        return {
            "ticker": ticker,
            "name": info.get("shortName", ticker),
            "current_pe": round(current_pe, 2) if current_pe else None,
            "mean_pe": round(mean_pe, 2),
            "std_pe": round(std_pe, 2),
            "z_score": round(z_score, 2),
            "interpretation": (
                "significantly_undervalued" if z_score < -2
                else "undervalued" if z_score < -1
                else "fairly_valued" if abs(z_score) <= 1
                else "overvalued" if z_score < 2
                else "significantly_overvalued"
            ),
        }
    except Exception as e:
        log.warning("valuation_zscore error for %s: %s", ticker, e)
        return {}


def get_sector_valuations(sector: str = "technology") -> Dict[str, Any]:
    """Average valuation multiples for stocks in a given sector."""
    yf = _import_yf()
    if not yf:
        return {}

    cache_key = f"sector_val:{sector}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    sector_tickers = {
        "technology": ["AAPL", "MSFT", "GOOGL", "NVDA", "META", "ADBE", "CRM", "ORCL", "INTC", "AMD"],
        "healthcare": ["UNH", "JNJ", "LLY", "ABBV", "MRK", "PFE", "TMO", "ABT", "DHR", "BMY"],
        "financials": ["JPM", "BAC", "WFC", "GS", "MS", "BLK", "C", "AXP", "SCHW", "USB"],
        "energy": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HAL"],
        "consumer": ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "TGT", "LOW", "TJX", "CMG"],
    }

    tickers = sector_tickers.get(sector.lower(), sector_tickers["technology"])
    stocks = []

    for t in tickers:
        try:
            info = yf.Ticker(t).info
            stocks.append({
                "ticker": t,
                "name": info.get("shortName", t),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "pb_ratio": info.get("priceToBook"),
                "ps_ratio": info.get("priceToSalesTrailing12Months"),
                "ev_ebitda": info.get("enterpriseToEbitda"),
                "market_cap": info.get("marketCap"),
            })
        except Exception:
            pass

    if not stocks:
        return {}

    metrics = ["pe_ratio", "forward_pe", "pb_ratio", "ps_ratio", "ev_ebitda"]
    averages = {}
    medians = {}
    for m in metrics:
        vals = sorted([s[m] for s in stocks if s.get(m) is not None])
        if vals:
            averages[m] = round(sum(vals) / len(vals), 2)
            medians[m] = round(vals[len(vals) // 2], 2)

    result = {
        "sector": sector,
        "stocks": stocks,
        "averages": averages,
        "medians": medians,
        "count": len(stocks),
    }
    _cache.set(cache_key, result)
    return result


def get_valuation_events(ticker: str, threshold: float = 1.5) -> Dict[str, Any]:
    """
    Find historical points where valuation deviated significantly from mean (events).
    threshold: number of standard deviations to flag.
    """
    yf = _import_yf()
    if not yf:
        return {}

    try:
        t = yf.Ticker(ticker)
        info = t.info
        current_eps = info.get("trailingEps", 0)

        if not current_eps or current_eps <= 0:
            return {}

        hist = t.history(period="5y", interval="1mo")
        if hist.empty:
            return {}

        data_points = []
        for dt, row in hist.iterrows():
            price = float(row["Close"])
            pe = price / current_eps
            if 0 < pe < 200:
                data_points.append({
                    "date": str(dt.date()) if hasattr(dt, "date") else str(dt)[:10],
                    "price": round(price, 2),
                    "pe": round(pe, 2),
                })

        if len(data_points) < 10:
            return {}

        pe_vals = [d["pe"] for d in data_points]
        mean_pe = sum(pe_vals) / len(pe_vals)
        std_pe = (sum((v - mean_pe) ** 2 for v in pe_vals) / len(pe_vals)) ** 0.5

        events = []
        for dp in data_points:
            z = (dp["pe"] - mean_pe) / std_pe if std_pe > 0 else 0
            if abs(z) >= threshold:
                events.append({
                    **dp,
                    "z_score": round(z, 2),
                    "type": "overvalued" if z > 0 else "undervalued",
                })

        return {
            "ticker": ticker,
            "name": info.get("shortName", ticker),
            "threshold_std": threshold,
            "mean_pe": round(mean_pe, 2),
            "std_pe": round(std_pe, 2),
            "events": events,
            "event_count": len(events),
            "total_periods": len(data_points),
        }
    except Exception as e:
        log.warning("valuation_events error for %s: %s", ticker, e)
        return {}
