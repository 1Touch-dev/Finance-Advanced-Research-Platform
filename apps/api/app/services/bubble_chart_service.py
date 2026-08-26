"""
Interactive Bubble Charts Service (James J5)
Generates scatter/bubble chart data using yfinance fundamentals.
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

SP500_TOP20 = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
    "UNH", "JNJ", "XOM", "JPM", "V", "PG", "MA", "HD", "CVX", "LLY",
    "ABBV", "MRK",
]

METRIC_MAP = {
    "market_cap": "marketCap",
    "pe_ratio": "trailingPE",
    "forward_pe": "forwardPE",
    "pb_ratio": "priceToBook",
    "ps_ratio": "priceToSalesTrailing12Months",
    "ev_ebitda": "enterpriseToEbitda",
    "dividend_yield": "dividendYield",
    "revenue": "totalRevenue",
    "ebitda": "ebitda",
    "net_income": "netIncomeToCommon",
    "profit_margin": "profitMargins",
    "operating_margin": "operatingMargins",
    "roe": "returnOnEquity",
    "roa": "returnOnAssets",
    "beta": "beta",
    "volume": "averageVolume",
    "price": "currentPrice",
    "52w_change": "52WeekChange",
    "debt_to_equity": "debtToEquity",
    "current_ratio": "currentRatio",
}

SECTOR_COLORS = {
    "Technology": "#3b82f6",
    "Healthcare": "#10b981",
    "Financial Services": "#f59e0b",
    "Consumer Cyclical": "#ef4444",
    "Communication Services": "#8b5cf6",
    "Industrials": "#6b7280",
    "Consumer Defensive": "#06b6d4",
    "Energy": "#f97316",
    "Utilities": "#84cc16",
    "Real Estate": "#ec4899",
    "Basic Materials": "#a855f7",
}


def _fetch_ticker_info(ticker: str) -> Dict[str, Any]:
    """Fetch yfinance info with caching."""
    cache_key = f"info:{ticker}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).info
        _cache.set(cache_key, info)
        return info
    except Exception as e:
        log.warning("yfinance info fetch failed for %s: %s", ticker, e)
        return {}


def _extract_metric(info: Dict, metric: str) -> Optional[float]:
    """Extract a metric value from yfinance info dict."""
    yf_key = METRIC_MAP.get(metric, metric)
    val = info.get(yf_key)
    if val is not None:
        try:
            return float(val)
        except (TypeError, ValueError) as e:
            log.debug("Failed to convert metric '%s' value to float: %s", metric, e)
    return None


# ── Public API ────────────────────────────────────────────────────────────────

def get_bubble_chart(
    x_metric: str = "market_cap",
    y_metric: str = "pe_ratio",
    size_metric: str = "revenue",
    color_by: str = "sector",
    tickers: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Generate bubble chart data: x/y position from fundamentals, size from another metric.
    """
    cache_key = f"bubble:{x_metric}:{y_metric}:{size_metric}:{tickers}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    ticker_list = tickers or SP500_TOP20
    bubbles = []

    for t in ticker_list:
        info = _fetch_ticker_info(t)
        if not info:
            continue

        x_val = _extract_metric(info, x_metric)
        y_val = _extract_metric(info, y_metric)
        size_val = _extract_metric(info, size_metric)

        if x_val is None or y_val is None:
            continue

        sector = info.get("sector", "Unknown")
        bubbles.append({
            "ticker": t,
            "name": info.get("shortName") or info.get("longName") or t,
            "x": x_val,
            "y": y_val,
            "size": size_val or 1,
            "sector": sector,
            "color": SECTOR_COLORS.get(sector, "#6b7280"),
        })

    result = {
        "chart_type": "bubble",
        "x_axis": {"metric": x_metric, "label": x_metric.replace("_", " ").title()},
        "y_axis": {"metric": y_metric, "label": y_metric.replace("_", " ").title()},
        "size_axis": {"metric": size_metric, "label": size_metric.replace("_", " ").title()},
        "color_by": color_by,
        "data": bubbles,
        "count": len(bubbles),
    }
    _cache.set(cache_key, result)
    return result


def get_bubble_presets() -> Dict[str, Any]:
    """Available preset configurations for bubble charts."""
    return {
        "presets": [
            {
                "id": "valuation_size",
                "name": "Valuation vs Size",
                "x_metric": "market_cap",
                "y_metric": "pe_ratio",
                "size_metric": "revenue",
                "description": "Market cap on X, P/E on Y, sized by revenue",
            },
            {
                "id": "growth_profitability",
                "name": "Growth vs Profitability",
                "x_metric": "revenue",
                "y_metric": "profit_margin",
                "size_metric": "market_cap",
                "description": "Revenue on X, profit margin on Y, sized by market cap",
            },
            {
                "id": "risk_return",
                "name": "Risk vs Return",
                "x_metric": "beta",
                "y_metric": "52w_change",
                "size_metric": "market_cap",
                "description": "Beta on X, 52-week change on Y, sized by market cap",
            },
            {
                "id": "efficiency",
                "name": "Capital Efficiency",
                "x_metric": "roe",
                "y_metric": "roa",
                "size_metric": "ebitda",
                "description": "ROE on X, ROA on Y, sized by EBITDA",
            },
        ]
    }


def get_animated_bubble_data(
    ticker: str, periods: int = 12, interval: str = "quarterly"
) -> Dict[str, Any]:
    """Bubble data over time for animation (shows fundamental changes)."""
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        info = t.info

        period_map = {"quarterly": "3mo", "yearly": "1y"}
        hist = t.history(period="5y", interval="1mo")
        if hist.empty:
            return {}

        frames = []
        step = 3 if interval == "quarterly" else 12
        prices = hist["Close"].tolist()

        for i in range(0, min(len(prices), periods * step), step):
            price = prices[i] if i < len(prices) else prices[-1]
            frames.append({
                "period": i // step + 1,
                "price": round(price, 2),
                "index": i,
            })

        return {
            "ticker": ticker,
            "name": info.get("shortName", ticker),
            "sector": info.get("sector"),
            "frames": frames[-periods:],
            "current_market_cap": info.get("marketCap"),
            "current_pe": info.get("trailingPE"),
        }
    except Exception as e:
        log.warning("animated_bubble_data error for %s: %s", ticker, e)
        return {}


def get_sector_bubble_chart(sector: Optional[str] = None) -> Dict[str, Any]:
    """Bubble chart for stocks within a sector."""
    tickers = SP500_TOP20
    bubbles = []

    for t in tickers:
        info = _fetch_ticker_info(t)
        if not info:
            continue
        stock_sector = info.get("sector", "")
        if sector and stock_sector.lower() != sector.lower():
            continue

        mcap = _extract_metric(info, "market_cap")
        pe = _extract_metric(info, "pe_ratio")
        rev = _extract_metric(info, "revenue")

        if mcap and pe:
            bubbles.append({
                "ticker": t,
                "name": info.get("shortName", t),
                "sector": stock_sector,
                "market_cap": mcap,
                "pe_ratio": pe,
                "revenue": rev or 0,
                "color": SECTOR_COLORS.get(stock_sector, "#6b7280"),
            })

    return {
        "sector_filter": sector or "all",
        "chart_type": "bubble",
        "data": bubbles,
        "count": len(bubbles),
    }


def get_comparison_bubble_chart(ticker1: str, ticker2: str, periods: int = 8) -> Dict[str, Any]:
    """Side-by-side bubble comparison of two tickers."""
    info1 = _fetch_ticker_info(ticker1)
    info2 = _fetch_ticker_info(ticker2)

    if not info1 or not info2:
        return {}

    metrics = ["market_cap", "pe_ratio", "revenue", "profit_margin", "beta", "roe"]
    comparison = []

    for metric in metrics:
        v1 = _extract_metric(info1, metric)
        v2 = _extract_metric(info2, metric)
        if v1 is not None and v2 is not None:
            comparison.append({
                "metric": metric,
                "label": metric.replace("_", " ").title(),
                ticker1: v1,
                ticker2: v2,
            })

    return {
        "ticker1": {"symbol": ticker1, "name": info1.get("shortName", ticker1), "sector": info1.get("sector")},
        "ticker2": {"symbol": ticker2, "name": info2.get("shortName", ticker2), "sector": info2.get("sector")},
        "comparison": comparison,
    }


def get_bubble_metrics() -> Dict[str, Any]:
    """List all available metrics for bubble chart axes."""
    return {
        "metrics": [
            {"id": k, "label": k.replace("_", " ").title(), "yf_key": v}
            for k, v in METRIC_MAP.items()
        ]
    }


def get_portfolio_bubble_chart(user_id: str) -> Dict[str, Any]:
    """Generate bubble chart from user's portfolio positions."""
    try:
        from app.services.cost_basis_service import get_user_positions
        positions = get_user_positions(user_id)
    except Exception as exc:
        log.debug("portfolio positions fetch failed for user %s: %s", user_id, exc)
        positions = []

    if not positions:
        return {"data": [], "note": "No portfolio positions found"}

    tickers = list({p["ticker"] for p in positions if p.get("ticker")})
    bubbles = []

    for t in tickers:
        info = _fetch_ticker_info(t)
        if not info:
            continue
        mcap = _extract_metric(info, "market_cap")
        pe = _extract_metric(info, "pe_ratio")
        price = _extract_metric(info, "price")

        pos_qty = sum(p["qty"] for p in positions if p.get("ticker") == t)
        pos_value = pos_qty * price if price else 0

        if mcap and pe:
            bubbles.append({
                "ticker": t,
                "name": info.get("shortName", t),
                "x": mcap,
                "y": pe,
                "size": pos_value,
                "shares": pos_qty,
                "sector": info.get("sector"),
                "color": SECTOR_COLORS.get(info.get("sector", ""), "#6b7280"),
            })

    return {
        "chart_type": "portfolio_bubble",
        "x_axis": {"metric": "market_cap", "label": "Market Cap"},
        "y_axis": {"metric": "pe_ratio", "label": "P/E Ratio"},
        "size_axis": {"metric": "position_value", "label": "Position Value"},
        "data": bubbles,
        "count": len(bubbles),
    }
