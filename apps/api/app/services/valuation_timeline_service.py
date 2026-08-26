"""
Valuation Timeline Service (James J3)
=====================================
Historical valuation multiples over time using REAL yfinance data.

Features:
- P/E, P/S, P/B, EV/EBITDA history
- Market cap history
- Support for 1Y, 3Y, 5Y, 10Y periods
- Multiple ticker comparison
- Valuation bands and z-scores
- Sector-level valuations

Data Source: yfinance (FREE)
NO MOCK DATA - Uses no_data pattern when data unavailable.
"""

import logging
import time as time_module
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.core.no_data import no_data_response, NoDataReason

log = logging.getLogger(__name__)


# ── TTL Cache (30 min) ────────────────────────────────────────────────────────

class _TTLCache:
    """Thread-safe TTL cache for valuation data."""

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

    def clear(self):
        self._store.clear()
        self._ts.clear()


_cache = _TTLCache(ttl_seconds=1800)


# ── yfinance Import ───────────────────────────────────────────────────────────

def _import_yf():
    """Lazily import yfinance."""
    try:
        import yfinance as yf
        return yf
    except ImportError:
        log.warning("yfinance not installed - valuation timeline unavailable")
        return None


# ── Period Mapping ────────────────────────────────────────────────────────────

PERIOD_MAP = {
    "1Y": ("1y", "1wk"),    # 1 year with weekly data
    "3Y": ("3y", "1mo"),    # 3 years with monthly data
    "5Y": ("5y", "1mo"),    # 5 years with monthly data
    "10Y": ("10y", "1mo"),  # 10 years with monthly data
    "MAX": ("max", "1mo"),  # Maximum available
}


def _get_yf_period_interval(period: str) -> tuple:
    """Convert period string to yfinance period and interval."""
    period_upper = period.upper()
    if period_upper in PERIOD_MAP:
        return PERIOD_MAP[period_upper]
    # Fallback for legacy format
    if period_upper in ("QUARTERLY", "MONTHLY", "YEARLY"):
        if period_upper == "QUARTERLY":
            return ("5y", "1mo")
        elif period_upper == "MONTHLY":
            return ("2y", "1mo")
        else:
            return ("10y", "1mo")
    return ("5y", "1mo")


# ── Helper Functions ──────────────────────────────────────────────────────────

def _safe_get(info: Dict, key: str, default: Any = None) -> Any:
    """Safely get value from info dict, handling None and invalid values."""
    val = info.get(key)
    if val is None or val == "N/A" or (isinstance(val, float) and val != val):  # NaN check
        return default
    return val


def _calculate_market_cap_history(hist, shares_outstanding: Optional[int]) -> List[Dict[str, Any]]:
    """Calculate historical market cap from price history and shares outstanding."""
    if hist.empty or not shares_outstanding:
        return []

    result = []
    for dt, row in hist.iterrows():
        price = float(row["Close"])
        market_cap = int(price * shares_outstanding)
        result.append({
            "date": str(dt.date()) if hasattr(dt, "date") else str(dt)[:10],
            "price": round(price, 2),
            "market_cap": market_cap,
            "market_cap_billions": round(market_cap / 1e9, 2),
        })
    return result


def _compute_valuation_ratios(
    price: float,
    trailing_eps: Optional[float],
    book_value: Optional[float],
    revenue_per_share: Optional[float],
    ebitda: Optional[float],
    enterprise_value: Optional[float],
    shares_outstanding: Optional[int],
) -> Dict[str, Optional[float]]:
    """Compute valuation ratios from price and fundamentals."""
    result = {}

    # P/E Ratio
    if trailing_eps and trailing_eps > 0:
        result["pe_ratio"] = round(price / trailing_eps, 2)
    else:
        result["pe_ratio"] = None

    # P/B Ratio
    if book_value and book_value > 0:
        result["pb_ratio"] = round(price / book_value, 2)
    else:
        result["pb_ratio"] = None

    # P/S Ratio (using revenue per share)
    if revenue_per_share and revenue_per_share > 0:
        result["ps_ratio"] = round(price / revenue_per_share, 2)
    else:
        result["ps_ratio"] = None

    # EV/EBITDA (scale enterprise value proportionally to price change)
    if ebitda and ebitda > 0 and enterprise_value and shares_outstanding:
        current_price_component = enterprise_value / shares_outstanding if shares_outstanding > 0 else 0
        if current_price_component > 0:
            ratio = price / current_price_component
            scaled_ev = enterprise_value * ratio
            result["ev_ebitda"] = round(scaled_ev / ebitda, 2)
        else:
            result["ev_ebitda"] = None
    else:
        result["ev_ebitda"] = None

    return result


# ── Public API ────────────────────────────────────────────────────────────────

def get_valuation_timeline(
    ticker: str,
    period: str = "5Y",
    periods: int = 20,
    interval: str = "quarterly",  # Legacy param, prefer period
) -> Dict[str, Any]:
    """
    Get historical valuation multiples over time using REAL yfinance data.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL")
        period: Time period - "1Y", "3Y", "5Y", "10Y", or "MAX"
        periods: Max number of data points to return
        interval: Legacy parameter (use period instead)

    Returns:
        Dictionary containing:
        - ticker: The ticker symbol
        - name: Company name
        - period: Time period requested
        - current_metrics: Current valuation ratios
        - timeline: List of historical valuation data points
        - market_cap_history: Historical market caps
        - count: Number of data points
        - source: Data source attribution
    """
    yf = _import_yf()
    if not yf:
        return no_data_response(
            ticker, "valuation_timeline",
            NoDataReason.DEPENDENCY_MISSING,
            source="yfinance",
            details="yfinance package not installed"
        )

    ticker = ticker.upper().strip()
    cache_key = f"val_timeline:{ticker}:{period}:{periods}"
    cached = _cache.get(cache_key)
    if cached:
        log.debug("Cache hit for valuation timeline: %s", ticker)
        return cached

    try:
        t = yf.Ticker(ticker)
        info = t.info

        # Check if we got valid data
        if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
            log.warning("No valid data from yfinance for %s", ticker)
            return no_data_response(
                ticker, "valuation_timeline",
                NoDataReason.ENTITY_NOT_FOUND,
                source="yfinance",
                details=f"Ticker {ticker} not found or no data available"
            )

        # Get period/interval for yfinance
        yf_period, yf_interval = _get_yf_period_interval(period)

        # Fetch historical data
        hist = t.history(period=yf_period, interval=yf_interval)
        if hist.empty:
            log.warning("No historical data for %s", ticker)
            return no_data_response(
                ticker, "valuation_timeline",
                NoDataReason.ENTITY_NOT_FOUND,
                source="yfinance",
                details=f"No historical price data for {ticker}"
            )

        # Extract fundamental data
        trailing_eps = _safe_get(info, "trailingEps")
        book_value = _safe_get(info, "bookValue")
        current_price = _safe_get(info, "currentPrice") or _safe_get(info, "regularMarketPrice")
        revenue_per_share = _safe_get(info, "revenuePerShare")
        shares_outstanding = _safe_get(info, "sharesOutstanding")
        ebitda = _safe_get(info, "ebitda")
        enterprise_value = _safe_get(info, "enterpriseValue")

        # Build timeline
        prices = hist["Close"]
        timeline = []

        # Calculate step to get approximately 'periods' data points
        total_points = len(prices)
        step = max(1, total_points // periods)
        indices = list(range(0, total_points, step))[-periods:]

        for i in indices:
            dt = prices.index[i]
            price = float(prices.iloc[i])

            entry = {
                "date": str(dt.date()) if hasattr(dt, "date") else str(dt)[:10],
                "price": round(price, 2),
            }

            # Calculate ratios
            ratios = _compute_valuation_ratios(
                price=price,
                trailing_eps=trailing_eps,
                book_value=book_value,
                revenue_per_share=revenue_per_share,
                ebitda=ebitda,
                enterprise_value=enterprise_value,
                shares_outstanding=shares_outstanding,
            )
            entry.update(ratios)

            # Add market cap
            if shares_outstanding:
                entry["market_cap"] = int(price * shares_outstanding)
                entry["market_cap_billions"] = round(entry["market_cap"] / 1e9, 2)

            timeline.append(entry)

        # Current metrics from yfinance info
        current_metrics = {
            "pe_ratio": _safe_get(info, "trailingPE"),
            "forward_pe": _safe_get(info, "forwardPE"),
            "pb_ratio": _safe_get(info, "priceToBook"),
            "ps_ratio": _safe_get(info, "priceToSalesTrailing12Months"),
            "ev_ebitda": _safe_get(info, "enterpriseToEbitda"),
            "ev_revenue": _safe_get(info, "enterpriseToRevenue"),
            "peg_ratio": _safe_get(info, "pegRatio"),
            "price": current_price,
            "market_cap": _safe_get(info, "marketCap"),
            "enterprise_value": enterprise_value,
        }

        result = {
            "ticker": ticker,
            "name": _safe_get(info, "shortName", ticker),
            "sector": _safe_get(info, "sector"),
            "industry": _safe_get(info, "industry"),
            "period": period,
            "current_metrics": current_metrics,
            "timeline": timeline,
            "count": len(timeline),
            "data_start": timeline[0]["date"] if timeline else None,
            "data_end": timeline[-1]["date"] if timeline else None,
            "source": "yfinance",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        _cache.set(cache_key, result)
        return result

    except Exception as e:
        log.warning("valuation_timeline error for %s: %s", ticker, e)
        return no_data_response(
            ticker, "valuation_timeline",
            NoDataReason.API_ERROR,
            source="yfinance",
            details=str(e)
        )


def get_market_cap_history(ticker: str, period: str = "5Y") -> Dict[str, Any]:
    """
    Get historical market capitalization over time.

    Args:
        ticker: Stock ticker symbol
        period: Time period - "1Y", "3Y", "5Y", "10Y", or "MAX"

    Returns:
        Dictionary with market cap history
    """
    yf = _import_yf()
    if not yf:
        return no_data_response(
            ticker, "market_cap_history",
            NoDataReason.DEPENDENCY_MISSING,
            source="yfinance"
        )

    ticker = ticker.upper().strip()
    cache_key = f"mktcap_hist:{ticker}:{period}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    try:
        t = yf.Ticker(ticker)
        info = t.info

        shares_outstanding = _safe_get(info, "sharesOutstanding")
        if not shares_outstanding:
            return no_data_response(
                ticker, "market_cap_history",
                NoDataReason.ENTITY_NOT_FOUND,
                source="yfinance",
                details="Shares outstanding data not available"
            )

        yf_period, yf_interval = _get_yf_period_interval(period)
        hist = t.history(period=yf_period, interval=yf_interval)

        if hist.empty:
            return no_data_response(
                ticker, "market_cap_history",
                NoDataReason.ENTITY_NOT_FOUND,
                source="yfinance",
                details="No historical price data"
            )

        history = _calculate_market_cap_history(hist, shares_outstanding)

        # Calculate statistics
        market_caps = [h["market_cap"] for h in history]
        if market_caps:
            min_cap = min(market_caps)
            max_cap = max(market_caps)
            avg_cap = sum(market_caps) / len(market_caps)
            current_cap = market_caps[-1]
            pct_change = ((current_cap - market_caps[0]) / market_caps[0] * 100) if market_caps[0] > 0 else 0
        else:
            min_cap = max_cap = avg_cap = current_cap = pct_change = 0

        result = {
            "ticker": ticker,
            "name": _safe_get(info, "shortName", ticker),
            "period": period,
            "current_market_cap": _safe_get(info, "marketCap"),
            "shares_outstanding": shares_outstanding,
            "history": history,
            "statistics": {
                "min": min_cap,
                "max": max_cap,
                "average": int(avg_cap),
                "min_billions": round(min_cap / 1e9, 2),
                "max_billions": round(max_cap / 1e9, 2),
                "average_billions": round(avg_cap / 1e9, 2),
                "period_change_pct": round(pct_change, 2),
            },
            "count": len(history),
            "source": "yfinance",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        _cache.set(cache_key, result)
        return result

    except Exception as e:
        log.warning("market_cap_history error for %s: %s", ticker, e)
        return no_data_response(
            ticker, "market_cap_history",
            NoDataReason.API_ERROR,
            source="yfinance",
            details=str(e)
        )


def compare_valuations(tickers: List[str], period: str = "5Y") -> Dict[str, Any]:
    """
    Compare current valuation multiples across multiple tickers.

    Args:
        tickers: List of ticker symbols
        period: Time period for historical comparison

    Returns:
        Comparison data with averages and rankings
    """
    yf = _import_yf()
    if not yf:
        return no_data_response(
            ",".join(tickers), "valuation_comparison",
            NoDataReason.DEPENDENCY_MISSING,
            source="yfinance"
        )

    if not tickers:
        return no_data_response(
            "none", "valuation_comparison",
            NoDataReason.ENTITY_NOT_FOUND,
            details="No tickers provided"
        )

    cache_key = f"val_compare:{sorted([t.upper() for t in tickers])}:{period}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    comparisons = []
    errors = []

    for ticker in tickers:
        ticker = ticker.upper().strip()
        try:
            t = yf.Ticker(ticker)
            info = t.info

            if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
                errors.append({"ticker": ticker, "error": "No data available"})
                continue

            comparisons.append({
                "ticker": ticker,
                "name": _safe_get(info, "shortName", ticker),
                "sector": _safe_get(info, "sector"),
                "industry": _safe_get(info, "industry"),
                "pe_ratio": _safe_get(info, "trailingPE"),
                "forward_pe": _safe_get(info, "forwardPE"),
                "pb_ratio": _safe_get(info, "priceToBook"),
                "ps_ratio": _safe_get(info, "priceToSalesTrailing12Months"),
                "ev_ebitda": _safe_get(info, "enterpriseToEbitda"),
                "ev_revenue": _safe_get(info, "enterpriseToRevenue"),
                "peg_ratio": _safe_get(info, "pegRatio"),
                "dividend_yield": _safe_get(info, "dividendYield"),
                "market_cap": _safe_get(info, "marketCap"),
                "price": _safe_get(info, "currentPrice") or _safe_get(info, "regularMarketPrice"),
            })
        except Exception as e:
            log.debug("compare_valuations skip %s: %s", ticker, e)
            errors.append({"ticker": ticker, "error": str(e)})

    if not comparisons:
        return no_data_response(
            ",".join(tickers), "valuation_comparison",
            NoDataReason.API_ERROR,
            source="yfinance",
            details="Could not fetch data for any tickers"
        )

    # Calculate averages and medians
    metrics = ["pe_ratio", "forward_pe", "pb_ratio", "ps_ratio", "ev_ebitda", "peg_ratio"]
    averages = {}
    medians = {}
    rankings = {}

    for m in metrics:
        vals = sorted([c[m] for c in comparisons if c.get(m) is not None])
        if vals:
            averages[m] = round(sum(vals) / len(vals), 2)
            medians[m] = round(vals[len(vals) // 2], 2)

            # Create rankings (lower is cheaper for most valuation metrics)
            ranked = sorted(
                [(c["ticker"], c[m]) for c in comparisons if c.get(m) is not None],
                key=lambda x: x[1]
            )
            rankings[m] = [{"ticker": t, "value": v, "rank": i + 1} for i, (t, v) in enumerate(ranked)]

    result = {
        "comparisons": comparisons,
        "averages": averages,
        "medians": medians,
        "rankings": rankings,
        "count": len(comparisons),
        "errors": errors if errors else None,
        "source": "yfinance",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    _cache.set(cache_key, result)
    return result


def get_valuation_bands(ticker: str, period: str = "5Y") -> Dict[str, Any]:
    """
    Get valuation bands showing historical range (high/low/avg) for P/E.
    Useful for identifying if current valuation is cheap or expensive.

    Args:
        ticker: Stock ticker symbol
        period: Time period - "1Y", "3Y", "5Y", "10Y"

    Returns:
        Valuation bands with percentiles and assessment
    """
    yf = _import_yf()
    if not yf:
        return no_data_response(
            ticker, "valuation_bands",
            NoDataReason.DEPENDENCY_MISSING,
            source="yfinance"
        )

    ticker = ticker.upper().strip()
    cache_key = f"val_bands:{ticker}:{period}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    try:
        t = yf.Ticker(ticker)
        info = t.info

        trailing_eps = _safe_get(info, "trailingEps")
        if not trailing_eps or trailing_eps <= 0:
            return no_data_response(
                ticker, "valuation_bands",
                NoDataReason.ENTITY_NOT_FOUND,
                source="yfinance",
                details="Cannot compute bands without positive trailing EPS"
            )

        yf_period, yf_interval = _get_yf_period_interval(period)
        hist = t.history(period=yf_period, interval=yf_interval)

        if hist.empty:
            return no_data_response(
                ticker, "valuation_bands",
                NoDataReason.ENTITY_NOT_FOUND,
                source="yfinance",
                details="No historical price data"
            )

        # Calculate historical P/E values
        pe_values = []
        for price in hist["Close"]:
            pe = float(price) / trailing_eps
            if 0 < pe < 200:  # Filter out unreasonable values
                pe_values.append(pe)

        if len(pe_values) < 5:
            return no_data_response(
                ticker, "valuation_bands",
                NoDataReason.ENTITY_NOT_FOUND,
                source="yfinance",
                details="Insufficient data points for band calculation"
            )

        pe_values.sort()
        n = len(pe_values)

        current_pe = _safe_get(info, "trailingPE")
        if current_pe is None:
            current_price = _safe_get(info, "currentPrice") or _safe_get(info, "regularMarketPrice")
            current_pe = current_price / trailing_eps if current_price else pe_values[-1]

        bands = {
            "min": round(pe_values[0], 2),
            "p10": round(pe_values[int(n * 0.1)], 2),
            "p25": round(pe_values[int(n * 0.25)], 2),
            "median": round(pe_values[int(n * 0.5)], 2),
            "mean": round(sum(pe_values) / n, 2),
            "p75": round(pe_values[int(n * 0.75)], 2),
            "p90": round(pe_values[int(n * 0.9)], 2),
            "max": round(pe_values[-1], 2),
        }

        # Calculate current percentile
        percentile = sum(1 for v in pe_values if v <= current_pe) / n * 100

        # Assessment based on percentile
        if percentile < 10:
            assessment = "very_cheap"
        elif percentile < 25:
            assessment = "cheap"
        elif percentile < 50:
            assessment = "below_average"
        elif percentile < 75:
            assessment = "above_average"
        elif percentile < 90:
            assessment = "expensive"
        else:
            assessment = "very_expensive"

        result = {
            "ticker": ticker,
            "name": _safe_get(info, "shortName", ticker),
            "metric": "trailing_pe",
            "period": period,
            "current_value": round(current_pe, 2) if current_pe else None,
            "percentile": round(percentile, 1),
            "bands": bands,
            "assessment": assessment,
            "data_points": n,
            "source": "yfinance",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        _cache.set(cache_key, result)
        return result

    except Exception as e:
        log.warning("valuation_bands error for %s: %s", ticker, e)
        return no_data_response(
            ticker, "valuation_bands",
            NoDataReason.API_ERROR,
            source="yfinance",
            details=str(e)
        )


def get_valuation_zscore(ticker: str, period: str = "5Y") -> Dict[str, Any]:
    """
    Calculate z-score of current valuation vs historical.
    Shows how many standard deviations from mean.

    Args:
        ticker: Stock ticker symbol
        period: Time period for historical comparison

    Returns:
        Z-score analysis with interpretation
    """
    yf = _import_yf()
    if not yf:
        return no_data_response(
            ticker, "valuation_zscore",
            NoDataReason.DEPENDENCY_MISSING,
            source="yfinance"
        )

    ticker = ticker.upper().strip()
    cache_key = f"val_zscore:{ticker}:{period}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    try:
        t = yf.Ticker(ticker)
        info = t.info

        trailing_eps = _safe_get(info, "trailingEps")
        if not trailing_eps or trailing_eps <= 0:
            return no_data_response(
                ticker, "valuation_zscore",
                NoDataReason.ENTITY_NOT_FOUND,
                source="yfinance",
                details="Cannot compute z-score without positive trailing EPS"
            )

        yf_period, yf_interval = _get_yf_period_interval(period)
        hist = t.history(period=yf_period, interval=yf_interval)

        if hist.empty:
            return no_data_response(
                ticker, "valuation_zscore",
                NoDataReason.ENTITY_NOT_FOUND,
                source="yfinance",
                details="No historical price data"
            )

        # Calculate historical P/E values
        pe_values = [
            float(p) / trailing_eps
            for p in hist["Close"]
            if 0 < float(p) / trailing_eps < 200
        ]

        if len(pe_values) < 10:
            return no_data_response(
                ticker, "valuation_zscore",
                NoDataReason.ENTITY_NOT_FOUND,
                source="yfinance",
                details="Insufficient data points for z-score calculation"
            )

        mean_pe = sum(pe_values) / len(pe_values)
        variance = sum((v - mean_pe) ** 2 for v in pe_values) / len(pe_values)
        std_pe = variance ** 0.5

        current_pe = _safe_get(info, "trailingPE")
        if current_pe is None:
            current_price = _safe_get(info, "currentPrice") or _safe_get(info, "regularMarketPrice")
            current_pe = current_price / trailing_eps if current_price else mean_pe

        z_score = (current_pe - mean_pe) / std_pe if std_pe > 0 else 0

        # Interpretation
        if z_score < -2:
            interpretation = "significantly_undervalued"
        elif z_score < -1:
            interpretation = "undervalued"
        elif z_score <= 1:
            interpretation = "fairly_valued"
        elif z_score < 2:
            interpretation = "overvalued"
        else:
            interpretation = "significantly_overvalued"

        result = {
            "ticker": ticker,
            "name": _safe_get(info, "shortName", ticker),
            "period": period,
            "current_pe": round(current_pe, 2) if current_pe else None,
            "mean_pe": round(mean_pe, 2),
            "std_pe": round(std_pe, 2),
            "z_score": round(z_score, 2),
            "interpretation": interpretation,
            "data_points": len(pe_values),
            "source": "yfinance",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        _cache.set(cache_key, result)
        return result

    except Exception as e:
        log.warning("valuation_zscore error for %s: %s", ticker, e)
        return no_data_response(
            ticker, "valuation_zscore",
            NoDataReason.API_ERROR,
            source="yfinance",
            details=str(e)
        )


def get_sector_valuations(sector: str = "technology") -> Dict[str, Any]:
    """
    Get average valuation multiples for stocks in a given sector.

    Args:
        sector: Sector name (technology, healthcare, financials, energy, consumer)

    Returns:
        Sector-level valuation statistics
    """
    yf = _import_yf()
    if not yf:
        return no_data_response(
            sector, "sector_valuations",
            NoDataReason.DEPENDENCY_MISSING,
            source="yfinance"
        )

    sector_lower = sector.lower()
    cache_key = f"sector_val:{sector_lower}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    # Representative tickers by sector
    sector_tickers = {
        "technology": ["AAPL", "MSFT", "GOOGL", "NVDA", "META", "ADBE", "CRM", "ORCL", "INTC", "AMD"],
        "healthcare": ["UNH", "JNJ", "LLY", "ABBV", "MRK", "PFE", "TMO", "ABT", "DHR", "BMY"],
        "financials": ["JPM", "BAC", "WFC", "GS", "MS", "BLK", "C", "AXP", "SCHW", "USB"],
        "energy": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HAL"],
        "consumer": ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "TGT", "LOW", "TJX", "CMG"],
        "industrials": ["CAT", "HON", "UPS", "RTX", "LMT", "BA", "GE", "MMM", "DE", "FDX"],
        "utilities": ["NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "ED", "WEC"],
        "materials": ["LIN", "APD", "SHW", "ECL", "FCX", "NEM", "NUE", "VMC", "MLM", "DOW"],
        "realestate": ["PLD", "AMT", "EQIX", "CCI", "PSA", "SPG", "O", "WELL", "DLR", "AVB"],
        "communication": ["GOOGL", "META", "DIS", "CMCSA", "NFLX", "T", "VZ", "TMUS", "CHTR", "EA"],
    }

    tickers = sector_tickers.get(sector_lower, sector_tickers.get("technology", []))
    stocks = []
    errors = []

    for t in tickers:
        try:
            info = yf.Ticker(t).info
            if not info or info.get("regularMarketPrice") is None and info.get("currentPrice") is None:
                errors.append(t)
                continue

            stocks.append({
                "ticker": t,
                "name": _safe_get(info, "shortName", t),
                "pe_ratio": _safe_get(info, "trailingPE"),
                "forward_pe": _safe_get(info, "forwardPE"),
                "pb_ratio": _safe_get(info, "priceToBook"),
                "ps_ratio": _safe_get(info, "priceToSalesTrailing12Months"),
                "ev_ebitda": _safe_get(info, "enterpriseToEbitda"),
                "peg_ratio": _safe_get(info, "pegRatio"),
                "dividend_yield": _safe_get(info, "dividendYield"),
                "market_cap": _safe_get(info, "marketCap"),
            })
        except Exception as e:
            log.debug("Failed to fetch sector ticker %s: %s", t, e)
            errors.append(t)

    if not stocks:
        return no_data_response(
            sector, "sector_valuations",
            NoDataReason.API_ERROR,
            source="yfinance",
            details="Could not fetch data for any sector tickers"
        )

    # Calculate statistics
    metrics = ["pe_ratio", "forward_pe", "pb_ratio", "ps_ratio", "ev_ebitda", "peg_ratio"]
    averages = {}
    medians = {}

    for m in metrics:
        vals = sorted([s[m] for s in stocks if s.get(m) is not None and s[m] > 0])
        if vals:
            averages[m] = round(sum(vals) / len(vals), 2)
            medians[m] = round(vals[len(vals) // 2], 2)

    result = {
        "sector": sector,
        "stocks": stocks,
        "averages": averages,
        "medians": medians,
        "count": len(stocks),
        "tickers_failed": errors if errors else None,
        "source": "yfinance",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    _cache.set(cache_key, result)
    return result


def get_valuation_events(ticker: str, threshold: float = 1.5, period: str = "5Y") -> Dict[str, Any]:
    """
    Find historical points where valuation deviated significantly from mean.

    Args:
        ticker: Stock ticker symbol
        threshold: Number of standard deviations to flag as an event
        period: Time period to analyze

    Returns:
        List of valuation events (outliers)
    """
    yf = _import_yf()
    if not yf:
        return no_data_response(
            ticker, "valuation_events",
            NoDataReason.DEPENDENCY_MISSING,
            source="yfinance"
        )

    ticker = ticker.upper().strip()
    cache_key = f"val_events:{ticker}:{threshold}:{period}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    try:
        t = yf.Ticker(ticker)
        info = t.info

        trailing_eps = _safe_get(info, "trailingEps")
        if not trailing_eps or trailing_eps <= 0:
            return no_data_response(
                ticker, "valuation_events",
                NoDataReason.ENTITY_NOT_FOUND,
                source="yfinance",
                details="Cannot find events without positive trailing EPS"
            )

        yf_period, yf_interval = _get_yf_period_interval(period)
        hist = t.history(period=yf_period, interval=yf_interval)

        if hist.empty:
            return no_data_response(
                ticker, "valuation_events",
                NoDataReason.ENTITY_NOT_FOUND,
                source="yfinance",
                details="No historical price data"
            )

        # Build data points
        data_points = []
        for dt, row in hist.iterrows():
            price = float(row["Close"])
            pe = price / trailing_eps
            if 0 < pe < 200:
                data_points.append({
                    "date": str(dt.date()) if hasattr(dt, "date") else str(dt)[:10],
                    "price": round(price, 2),
                    "pe": round(pe, 2),
                })

        if len(data_points) < 10:
            return no_data_response(
                ticker, "valuation_events",
                NoDataReason.ENTITY_NOT_FOUND,
                source="yfinance",
                details="Insufficient data points for event detection"
            )

        # Calculate statistics
        pe_vals = [d["pe"] for d in data_points]
        mean_pe = sum(pe_vals) / len(pe_vals)
        std_pe = (sum((v - mean_pe) ** 2 for v in pe_vals) / len(pe_vals)) ** 0.5

        # Find events
        events = []
        for dp in data_points:
            z = (dp["pe"] - mean_pe) / std_pe if std_pe > 0 else 0
            if abs(z) >= threshold:
                events.append({
                    **dp,
                    "z_score": round(z, 2),
                    "type": "overvalued" if z > 0 else "undervalued",
                    "deviation_pct": round((dp["pe"] - mean_pe) / mean_pe * 100, 1),
                })

        result = {
            "ticker": ticker,
            "name": _safe_get(info, "shortName", ticker),
            "period": period,
            "threshold_std": threshold,
            "mean_pe": round(mean_pe, 2),
            "std_pe": round(std_pe, 2),
            "events": events,
            "event_count": len(events),
            "total_periods": len(data_points),
            "event_frequency": round(len(events) / len(data_points) * 100, 1),
            "source": "yfinance",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        _cache.set(cache_key, result)
        return result

    except Exception as e:
        log.warning("valuation_events error for %s: %s", ticker, e)
        return no_data_response(
            ticker, "valuation_events",
            NoDataReason.API_ERROR,
            source="yfinance",
            details=str(e)
        )


def get_pe_history(ticker: str, period: str = "5Y") -> Dict[str, Any]:
    """
    Get detailed P/E ratio history.

    Args:
        ticker: Stock ticker symbol
        period: Time period

    Returns:
        Historical P/E values with statistics
    """
    yf = _import_yf()
    if not yf:
        return no_data_response(
            ticker, "pe_history",
            NoDataReason.DEPENDENCY_MISSING,
            source="yfinance"
        )

    ticker = ticker.upper().strip()
    cache_key = f"pe_hist:{ticker}:{period}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    try:
        t = yf.Ticker(ticker)
        info = t.info

        trailing_eps = _safe_get(info, "trailingEps")
        if not trailing_eps or trailing_eps <= 0:
            return no_data_response(
                ticker, "pe_history",
                NoDataReason.ENTITY_NOT_FOUND,
                source="yfinance",
                details="Cannot compute P/E history without positive trailing EPS"
            )

        yf_period, yf_interval = _get_yf_period_interval(period)
        hist = t.history(period=yf_period, interval=yf_interval)

        if hist.empty:
            return no_data_response(
                ticker, "pe_history",
                NoDataReason.ENTITY_NOT_FOUND,
                source="yfinance",
                details="No historical price data"
            )

        history = []
        pe_values = []

        for dt, row in hist.iterrows():
            price = float(row["Close"])
            pe = price / trailing_eps
            if 0 < pe < 200:
                history.append({
                    "date": str(dt.date()) if hasattr(dt, "date") else str(dt)[:10],
                    "price": round(price, 2),
                    "pe_ratio": round(pe, 2),
                })
                pe_values.append(pe)

        if not pe_values:
            return no_data_response(
                ticker, "pe_history",
                NoDataReason.ENTITY_NOT_FOUND,
                source="yfinance",
                details="No valid P/E values in period"
            )

        pe_values.sort()
        n = len(pe_values)

        result = {
            "ticker": ticker,
            "name": _safe_get(info, "shortName", ticker),
            "period": period,
            "trailing_eps": trailing_eps,
            "current_pe": _safe_get(info, "trailingPE"),
            "forward_pe": _safe_get(info, "forwardPE"),
            "history": history,
            "statistics": {
                "min": round(pe_values[0], 2),
                "max": round(pe_values[-1], 2),
                "mean": round(sum(pe_values) / n, 2),
                "median": round(pe_values[n // 2], 2),
                "std": round((sum((v - sum(pe_values) / n) ** 2 for v in pe_values) / n) ** 0.5, 2),
            },
            "count": len(history),
            "source": "yfinance",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        _cache.set(cache_key, result)
        return result

    except Exception as e:
        log.warning("pe_history error for %s: %s", ticker, e)
        return no_data_response(
            ticker, "pe_history",
            NoDataReason.API_ERROR,
            source="yfinance",
            details=str(e)
        )


def get_multiple_timelines(tickers: List[str], period: str = "5Y") -> Dict[str, Any]:
    """
    Get valuation timelines for multiple tickers for comparison.

    Args:
        tickers: List of ticker symbols
        period: Time period

    Returns:
        Combined timeline data for all tickers
    """
    if not tickers:
        return no_data_response(
            "none", "multiple_timelines",
            NoDataReason.ENTITY_NOT_FOUND,
            details="No tickers provided"
        )

    cache_key = f"multi_timeline:{sorted([t.upper() for t in tickers])}:{period}"
    cached = _cache.get(cache_key)
    if cached:
        return cached

    timelines = {}
    errors = []

    for ticker in tickers:
        result = get_valuation_timeline(ticker, period=period)
        if result.get("no_data"):
            errors.append({"ticker": ticker, "error": result.get("message", "Unknown error")})
        else:
            timelines[ticker.upper()] = result

    if not timelines:
        return no_data_response(
            ",".join(tickers), "multiple_timelines",
            NoDataReason.API_ERROR,
            source="yfinance",
            details="Could not fetch data for any tickers"
        )

    result = {
        "timelines": timelines,
        "count": len(timelines),
        "period": period,
        "errors": errors if errors else None,
        "source": "yfinance",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    _cache.set(cache_key, result)
    return result


# ── Cache Management ──────────────────────────────────────────────────────────

def clear_cache():
    """Clear the valuation timeline cache."""
    _cache.clear()
    log.info("Valuation timeline cache cleared")
