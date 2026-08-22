"""
Data Visualization Service (James J2)
Generate chart-ready data (treemap, correlation, performance bars, etc.) via yfinance.
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

DEFAULT_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
    "UNH", "JNJ", "XOM", "JPM", "V", "PG", "MA", "HD", "CVX", "LLY",
    "ABBV", "MRK",
]


def _import_yf():
    try:
        import yfinance as yf
        return yf
    except ImportError:
        log.warning("yfinance not installed")
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def get_sector_breakdown(tickers: Optional[List[str]] = None) -> Dict[str, Any]:
    """Market cap by sector for treemap/pie chart."""
    yf = _import_yf()
    if not yf:
        return {}

    cache_key = f"sector_breakdown:{tickers}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    ticker_list = tickers or DEFAULT_TICKERS
    sectors: Dict[str, Dict[str, Any]] = {}

    for t in ticker_list:
        try:
            info = yf.Ticker(t).info
            sector = info.get("sector", "Unknown")
            mcap = info.get("marketCap", 0)
            if not mcap:
                continue

            if sector not in sectors:
                sectors[sector] = {"sector": sector, "total_market_cap": 0, "stocks": [], "count": 0}
            sectors[sector]["total_market_cap"] += mcap
            sectors[sector]["count"] += 1
            sectors[sector]["stocks"].append({
                "ticker": t,
                "name": info.get("shortName", t),
                "market_cap": mcap,
            })
        except Exception as e:
            log.debug("sector_breakdown skip %s: %s", t, e)

    total_mcap = sum(s["total_market_cap"] for s in sectors.values())
    for s in sectors.values():
        s["weight_pct"] = round(s["total_market_cap"] / total_mcap * 100, 2) if total_mcap else 0

    result = {
        "chart_type": "treemap",
        "sectors": sorted(sectors.values(), key=lambda x: x["total_market_cap"], reverse=True),
        "total_market_cap": total_mcap,
        "ticker_count": len(ticker_list),
    }
    _cache.set(cache_key, result)
    return result


def get_performance_comparison(tickers: List[str], period: str = "1Y") -> Dict[str, Any]:
    """Returns comparison bar chart data for specified tickers."""
    yf = _import_yf()
    if not yf:
        return {}

    cache_key = f"perf_comp:{sorted(tickers)}:{period}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    period_map = {"1W": "5d", "1M": "1mo", "3M": "3mo", "6M": "6mo", "1Y": "1y", "2Y": "2y", "5Y": "5y", "YTD": "ytd"}
    yf_period = period_map.get(period.upper(), "1y")

    bars = []
    for t in tickers:
        try:
            hist = yf.Ticker(t).history(period=yf_period)
            if hist.empty or len(hist) < 2:
                continue
            start_price = float(hist["Close"].iloc[0])
            end_price = float(hist["Close"].iloc[-1])
            ret = (end_price / start_price - 1) * 100
            bars.append({
                "ticker": t,
                "return_pct": round(ret, 2),
                "start_price": round(start_price, 2),
                "end_price": round(end_price, 2),
                "period": period,
            })
        except Exception as e:
            log.debug("perf_comparison skip %s: %s", t, e)

    bars.sort(key=lambda x: x["return_pct"], reverse=True)
    result = {"chart_type": "bar", "period": period, "data": bars, "count": len(bars)}
    _cache.set(cache_key, result)
    return result


def get_time_series(ticker: str, period: str = "1Y", interval: str = "daily") -> Dict[str, Any]:
    """OHLCV time series for line/candlestick charts."""
    yf = _import_yf()
    if not yf:
        return {}

    cache_key = f"ts:{ticker}:{period}:{interval}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    period_map = {"1W": "5d", "1M": "1mo", "3M": "3mo", "6M": "6mo", "1Y": "1y", "2Y": "2y", "5Y": "5y"}
    interval_map = {"daily": "1d", "weekly": "1wk", "monthly": "1mo", "hourly": "1h"}

    yf_period = period_map.get(period.upper(), "1y")
    yf_interval = interval_map.get(interval.lower(), "1d")

    try:
        hist = yf.Ticker(ticker).history(period=yf_period, interval=yf_interval)
        if hist.empty:
            return {}

        data = []
        for dt, row in hist.iterrows():
            data.append({
                "date": str(dt.date()) if hasattr(dt, "date") else str(dt)[:10],
                "open": round(float(row.get("Open", 0)), 2),
                "high": round(float(row.get("High", 0)), 2),
                "low": round(float(row.get("Low", 0)), 2),
                "close": round(float(row.get("Close", 0)), 2),
                "volume": int(row.get("Volume", 0)),
            })

        result = {
            "chart_type": "time_series",
            "ticker": ticker,
            "period": period,
            "interval": interval,
            "data": data,
            "count": len(data),
        }
        _cache.set(cache_key, result)
        return result
    except Exception as e:
        log.warning("time_series error for %s: %s", ticker, e)
        return {}


def get_correlation_matrix(tickers: List[str]) -> Dict[str, Any]:
    """Price correlation matrix using daily returns."""
    yf = _import_yf()
    if not yf:
        return {}

    cache_key = f"corr:{sorted(tickers)}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    try:
        import pandas as pd

        close_data = {}
        for t in tickers:
            hist = yf.Ticker(t).history(period="1y")
            if not hist.empty:
                close_data[t] = hist["Close"]

        if len(close_data) < 2:
            return {}

        df = pd.DataFrame(close_data)
        returns = df.pct_change().dropna()
        corr = returns.corr()

        matrix = []
        for t1 in corr.columns:
            row = {}
            for t2 in corr.columns:
                row[t2] = round(float(corr.loc[t1, t2]), 4)
            matrix.append({"ticker": t1, "correlations": row})

        result = {
            "chart_type": "heatmap",
            "tickers": list(corr.columns),
            "matrix": matrix,
            "period": "1Y",
            "method": "pearson",
        }
        _cache.set(cache_key, result)
        return result
    except Exception as e:
        log.warning("correlation_matrix error: %s", e)
        return {}


def get_treemap_data(group_by: str = "sector") -> Dict[str, Any]:
    """Market cap treemap data grouped by sector or industry."""
    return get_sector_breakdown(DEFAULT_TICKERS)


def get_scatter_plot(
    x_metric: str = "market_cap",
    y_metric: str = "pe_ratio",
    tickers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Scatter plot of two fundamentals."""
    yf = _import_yf()
    if not yf:
        return {}

    from app.services.bubble_chart_service import METRIC_MAP, _extract_metric

    ticker_list = tickers or DEFAULT_TICKERS
    points = []

    for t in ticker_list:
        try:
            info = yf.Ticker(t).info
            x_val = _extract_metric(info, x_metric)
            y_val = _extract_metric(info, y_metric)
            if x_val is not None and y_val is not None:
                points.append({
                    "ticker": t,
                    "name": info.get("shortName", t),
                    "x": x_val,
                    "y": y_val,
                    "sector": info.get("sector"),
                })
        except Exception:
            pass

    return {
        "chart_type": "scatter",
        "x_axis": x_metric,
        "y_axis": y_metric,
        "data": points,
        "count": len(points),
    }


def get_candlestick_data(ticker: str, period: str = "3M") -> Dict[str, Any]:
    """Candlestick chart data."""
    return get_time_series(ticker, period=period, interval="daily")


def get_area_chart(tickers: List[str], stacked: bool = True, period: str = "1Y") -> Dict[str, Any]:
    """Area chart comparing multiple tickers (normalized to 100)."""
    yf = _import_yf()
    if not yf:
        return {}

    cache_key = f"area:{sorted(tickers)}:{period}:{stacked}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    period_map = {"1M": "1mo", "3M": "3mo", "6M": "6mo", "1Y": "1y", "2Y": "2y", "5Y": "5y"}
    yf_period = period_map.get(period.upper(), "1y")

    series = {}
    dates = None

    for t in tickers:
        try:
            hist = yf.Ticker(t).history(period=yf_period)
            if hist.empty:
                continue
            closes = hist["Close"]
            normalized = (closes / closes.iloc[0] * 100).round(2)
            series[t] = normalized.tolist()
            if dates is None:
                dates = [str(d.date()) if hasattr(d, "date") else str(d)[:10] for d in hist.index]
        except Exception:
            pass

    if not series:
        return {}

    result = {
        "chart_type": "area",
        "stacked": stacked,
        "period": period,
        "dates": dates,
        "series": series,
        "base": 100,
        "note": "Normalized to 100 at start of period",
    }
    _cache.set(cache_key, result)
    return result


def get_radar_chart(ticker: str) -> Dict[str, Any]:
    """Radar/spider chart of fundamental metrics (normalized 0-100 scale)."""
    yf = _import_yf()
    if not yf:
        return {}

    try:
        info = yf.Ticker(ticker).info

        metrics = {
            "Profitability": min(max((info.get("profitMargins", 0) or 0) * 100, 0), 100),
            "Growth": min(max((info.get("revenueGrowth", 0) or 0) * 100, 0), 100),
            "Valuation": max(0, 100 - min((info.get("trailingPE", 50) or 50), 100)),
            "Efficiency": min(max((info.get("returnOnEquity", 0) or 0) * 100, 0), 100),
            "Stability": max(0, 100 - min(abs((info.get("beta", 1) or 1) - 1) * 50, 100)),
            "Dividend": min((info.get("dividendYield", 0) or 0) * 1000, 100),
        }

        return {
            "chart_type": "radar",
            "ticker": ticker,
            "name": info.get("shortName", ticker),
            "metrics": metrics,
            "axes": list(metrics.keys()),
            "values": list(metrics.values()),
        }
    except Exception as e:
        log.warning("radar_chart error for %s: %s", ticker, e)
        return {}


def get_histogram(metric: str = "returns", period: str = "1Y") -> Dict[str, Any]:
    """Distribution histogram of a metric across default tickers."""
    yf = _import_yf()
    if not yf:
        return {}

    period_map = {"1M": "1mo", "3M": "3mo", "6M": "6mo", "1Y": "1y"}
    yf_period = period_map.get(period.upper(), "1y")

    values = []
    for t in DEFAULT_TICKERS:
        try:
            if metric == "returns":
                hist = yf.Ticker(t).history(period=yf_period)
                if len(hist) >= 2:
                    ret = (float(hist["Close"].iloc[-1]) / float(hist["Close"].iloc[0]) - 1) * 100
                    values.append({"ticker": t, "value": round(ret, 2)})
            elif metric == "pe_ratio":
                info = yf.Ticker(t).info
                pe = info.get("trailingPE")
                if pe:
                    values.append({"ticker": t, "value": round(float(pe), 2)})
            elif metric == "dividend_yield":
                info = yf.Ticker(t).info
                dy = info.get("dividendYield")
                if dy:
                    values.append({"ticker": t, "value": round(float(dy) * 100, 2)})
        except Exception:
            pass

    if not values:
        return {}

    vals = [v["value"] for v in values]
    return {
        "chart_type": "histogram",
        "metric": metric,
        "period": period,
        "data": values,
        "stats": {
            "mean": round(sum(vals) / len(vals), 2),
            "min": round(min(vals), 2),
            "max": round(max(vals), 2),
            "count": len(vals),
        },
    }


def get_gauge_chart(metric: str = "portfolio_health", value: Optional[float] = None) -> Dict[str, Any]:
    """Gauge chart for a single metric (0-100 scale)."""
    gauge_value = value

    if gauge_value is None:
        gauge_value = 65.0

    thresholds = {
        "portfolio_health": {"low": 30, "medium": 60, "high": 80},
        "risk_score": {"low": 20, "medium": 50, "high": 75},
        "diversification": {"low": 25, "medium": 50, "high": 75},
    }

    thresh = thresholds.get(metric, {"low": 30, "medium": 60, "high": 80})
    if gauge_value >= thresh["high"]:
        status = "excellent"
    elif gauge_value >= thresh["medium"]:
        status = "good"
    elif gauge_value >= thresh["low"]:
        status = "fair"
    else:
        status = "poor"

    return {
        "chart_type": "gauge",
        "metric": metric,
        "value": gauge_value,
        "max": 100,
        "status": status,
        "thresholds": thresh,
    }


def get_waterfall_chart(ticker: str) -> Dict[str, Any]:
    """Waterfall chart showing income statement breakdown."""
    yf = _import_yf()
    if not yf:
        return {}

    try:
        info = yf.Ticker(ticker).info
        revenue = info.get("totalRevenue", 0) or 0
        gross = info.get("grossProfits", 0) or 0
        ebitda = info.get("ebitda", 0) or 0
        net = info.get("netIncomeToCommon", 0) or 0

        if not revenue:
            return {}

        cogs = revenue - gross
        opex = gross - ebitda
        other = ebitda - net

        steps = [
            {"label": "Revenue", "value": revenue, "type": "total"},
            {"label": "COGS", "value": -cogs, "type": "decrease"},
            {"label": "Gross Profit", "value": gross, "type": "subtotal"},
            {"label": "OpEx", "value": -opex, "type": "decrease"},
            {"label": "EBITDA", "value": ebitda, "type": "subtotal"},
            {"label": "Tax & Other", "value": -other, "type": "decrease"},
            {"label": "Net Income", "value": net, "type": "total"},
        ]

        return {
            "chart_type": "waterfall",
            "ticker": ticker,
            "name": info.get("shortName", ticker),
            "steps": steps,
            "currency": info.get("financialCurrency", "USD"),
        }
    except Exception as e:
        log.warning("waterfall_chart error for %s: %s", ticker, e)
        return {}
