"""
Finnhub Earnings Calendar Connector

Fetches real earnings calendar data from Finnhub's free API.
Source: https://finnhub.io/docs/api/earnings-calendar

Features:
- Upcoming earnings dates
- Historical earnings
- EPS estimates and actuals
- Revenue estimates
- Earnings surprises
"""

import os
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from functools import lru_cache

log = logging.getLogger(__name__)

FINNHUB_KEY = os.getenv("FINNHUB_API_KEY", "")
FINNHUB_BASE = "https://finnhub.io/api/v1"

# Cache timeout (5 minutes for earnings data)
CACHE_TIMEOUT = 300
_cache: Dict[str, Any] = {}
_cache_time: Dict[str, datetime] = {}

_TIMEOUT = 12


def _get_cached(key: str) -> Optional[Any]:
    """Check cache and return if valid."""
    if key in _cache and key in _cache_time:
        if datetime.utcnow() - _cache_time[key] < timedelta(seconds=CACHE_TIMEOUT):
            return _cache[key]
    return None


def _set_cache(key: str, value: Any) -> None:
    """Set cache value."""
    _cache[key] = value
    _cache_time[key] = datetime.utcnow()


def _get_finnhub(endpoint: str, params: Dict = None) -> Optional[Any]:
    """Make GET request to Finnhub API."""
    if not FINNHUB_KEY:
        log.warning("FINNHUB_API_KEY not set")
        return None

    try:
        params = params or {}
        params["token"] = FINNHUB_KEY
        url = f"{FINNHUB_BASE}{endpoint}"

        r = requests.get(url, params=params, timeout=_TIMEOUT)
        if r.status_code == 200:
            return r.json()
        log.warning("Finnhub API returned %s: %s", r.status_code, r.text[:200])
    except Exception as e:
        log.warning("Finnhub API request failed: %s", e)
    return None


def get_earnings_calendar(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    symbol: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get earnings calendar for a date range.

    Args:
        from_date: Start date (YYYY-MM-DD), defaults to today
        to_date: End date (YYYY-MM-DD), defaults to 7 days from now
        symbol: Optional ticker to filter by

    Returns:
        List of earnings events
    """
    if not from_date:
        from_date = datetime.utcnow().strftime("%Y-%m-%d")
    if not to_date:
        to_date = (datetime.utcnow() + timedelta(days=7)).strftime("%Y-%m-%d")

    cache_key = f"earnings_calendar_{from_date}_{to_date}_{symbol or 'all'}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    params = {
        "from": from_date,
        "to": to_date,
    }
    if symbol:
        params["symbol"] = symbol.upper()

    data = _get_finnhub("/calendar/earnings", params)
    if not data or "earningsCalendar" not in data:
        return []

    results = []
    for event in data["earningsCalendar"]:
        results.append(_parse_earnings_event(event))

    _set_cache(cache_key, results)
    return results


def get_upcoming_earnings(
    days_ahead: int = 7,
    importance: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get upcoming earnings for the next N days.

    Args:
        days_ahead: Number of days to look ahead
        importance: Filter by importance (high, medium, low)

    Returns:
        List of upcoming earnings events
    """
    from_date = datetime.utcnow().strftime("%Y-%m-%d")
    to_date = (datetime.utcnow() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    events = get_earnings_calendar(from_date, to_date)

    if importance:
        events = [e for e in events if _get_importance(e) == importance]

    # Sort by date
    events.sort(key=lambda x: x["earnings_date"])
    return events


def get_ticker_earnings(
    ticker: str,
    include_historical: bool = True,
) -> Dict[str, Any]:
    """
    Get earnings data for a specific ticker.

    Returns both upcoming and historical earnings.
    """
    cache_key = f"ticker_earnings_{ticker}_{include_historical}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    result = {
        "ticker": ticker.upper(),
        "upcoming": [],
        "historical": [],
    }

    # Get upcoming (next 90 days)
    from_date = datetime.utcnow().strftime("%Y-%m-%d")
    to_date = (datetime.utcnow() + timedelta(days=90)).strftime("%Y-%m-%d")
    upcoming = get_earnings_calendar(from_date, to_date, ticker)
    result["upcoming"] = upcoming

    if include_historical:
        # Get historical (past 2 years)
        historical_from = (datetime.utcnow() - timedelta(days=730)).strftime("%Y-%m-%d")
        historical_to = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        historical = get_earnings_calendar(historical_from, historical_to, ticker)
        result["historical"] = historical

    _set_cache(cache_key, result)
    return result


def get_earnings_surprises(
    min_surprise_percent: float = 5.0,
    days_back: int = 30,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Get recent earnings surprises above a threshold.

    Args:
        min_surprise_percent: Minimum surprise percentage (absolute)
        days_back: Number of days to look back
        limit: Maximum results

    Returns:
        List of earnings surprises sorted by magnitude
    """
    from_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    to_date = datetime.utcnow().strftime("%Y-%m-%d")

    events = get_earnings_calendar(from_date, to_date)

    surprises = []
    for event in events:
        surprise = event.get("surprise_percent")
        if surprise is not None and abs(surprise) >= min_surprise_percent:
            surprises.append(event)

    # Sort by absolute surprise
    surprises.sort(key=lambda x: abs(x.get("surprise_percent", 0)), reverse=True)
    return surprises[:limit]


def get_earnings_estimates(ticker: str) -> Dict[str, Any]:
    """
    Get analyst estimates for a ticker.

    Returns EPS and revenue estimates.
    """
    cache_key = f"estimates_{ticker}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    # Get EPS estimates
    eps_data = _get_finnhub("/stock/eps-estimate", {"symbol": ticker.upper()})

    # Get revenue estimates
    rev_data = _get_finnhub("/stock/revenue-estimate", {"symbol": ticker.upper()})

    result = {
        "ticker": ticker.upper(),
        "eps_estimates": [],
        "revenue_estimates": [],
        "source": "Finnhub",
    }

    if eps_data and "data" in eps_data:
        for est in eps_data["data"]:
            result["eps_estimates"].append({
                "period": est.get("period"),
                "estimate": est.get("epsAvg"),
                "high": est.get("epsHigh"),
                "low": est.get("epsLow"),
                "num_analysts": est.get("numberAnalysts"),
            })

    if rev_data and "data" in rev_data:
        for est in rev_data["data"]:
            result["revenue_estimates"].append({
                "period": est.get("period"),
                "estimate": est.get("revenueAvg"),
                "high": est.get("revenueHigh"),
                "low": est.get("revenueLow"),
                "num_analysts": est.get("numberAnalysts"),
            })

    _set_cache(cache_key, result)
    return result


def get_earnings_calendar_week(start_date: Optional[str] = None) -> Dict[str, List[Dict]]:
    """
    Get earnings calendar for a week, grouped by date.

    Args:
        start_date: Week start date (defaults to current Monday)

    Returns:
        Dict mapping dates to earnings events
    """
    if start_date:
        week_start = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        today = datetime.utcnow()
        week_start = today - timedelta(days=today.weekday())  # Monday

    week_end = week_start + timedelta(days=4)  # Friday

    events = get_earnings_calendar(
        week_start.strftime("%Y-%m-%d"),
        week_end.strftime("%Y-%m-%d")
    )

    # Group by date
    calendar = {}
    for i in range(5):  # Mon-Fri
        day = week_start + timedelta(days=i)
        date_str = day.strftime("%Y-%m-%d")
        calendar[date_str] = []

    for event in events:
        date = event.get("earnings_date")
        if date in calendar:
            calendar[date].append(event)

    return calendar


def _parse_earnings_event(event: Dict) -> Dict[str, Any]:
    """Parse Finnhub earnings event into standardized format."""
    eps_actual = event.get("epsActual")
    eps_estimate = event.get("epsEstimate")

    surprise_percent = None
    if eps_actual is not None and eps_estimate is not None and eps_estimate != 0:
        surprise_percent = round(((eps_actual - eps_estimate) / abs(eps_estimate)) * 100, 2)

    # Determine session (before/after market)
    hour = event.get("hour", "")
    if hour == "bmo":
        session = "pre_market"
    elif hour == "amc":
        session = "after_hours"
    else:
        session = "unknown"

    return {
        "ticker": event.get("symbol", ""),
        "company_name": event.get("symbol", ""),  # Finnhub doesn't return company name
        "earnings_date": event.get("date", ""),
        "session": session,
        "fiscal_quarter": f"Q{event.get('quarter', 0)}",
        "fiscal_year": event.get("year", 0),
        "eps_estimate": eps_estimate,
        "eps_actual": eps_actual,
        "revenue_estimate": event.get("revenueEstimate"),
        "revenue_actual": event.get("revenueActual"),
        "surprise_percent": surprise_percent,
        "source": "Finnhub",
    }


def _get_importance(event: Dict) -> str:
    """Determine importance level of an earnings event."""
    # Could be enhanced with market cap lookup
    # For now, use a simple heuristic
    high_importance_tickers = {
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
        "JPM", "BAC", "WFC", "GS", "MS",
        "JNJ", "UNH", "PFE", "MRK",
    }

    ticker = event.get("ticker", "").upper()
    if ticker in high_importance_tickers:
        return "high"

    return "medium"


# Fallback to yfinance
def get_earnings_fallback(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Fallback to yfinance for earnings data.
    """
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)

        # Get earnings dates
        calendar = stock.calendar
        earnings_date = None
        if calendar is not None and not calendar.empty:
            if "Earnings Date" in calendar.index:
                earnings_date = calendar.loc["Earnings Date"].iloc[0]
                if hasattr(earnings_date, "strftime"):
                    earnings_date = earnings_date.strftime("%Y-%m-%d")

        # Get earnings history
        earnings = stock.earnings_history
        history = []
        if earnings is not None and not earnings.empty:
            for _, row in earnings.iterrows():
                history.append({
                    "quarter": str(row.name) if hasattr(row, "name") else "",
                    "eps_estimate": row.get("epsEstimate"),
                    "eps_actual": row.get("epsActual"),
                    "surprise_percent": row.get("surprisePercent"),
                })

        return {
            "ticker": ticker.upper(),
            "next_earnings_date": earnings_date,
            "history": history,
            "source": "Yahoo Finance (fallback)",
        }
    except Exception as e:
        log.warning("yfinance earnings fallback failed for %s: %s", ticker, e)
        return None


def get_finnhub_data_info() -> Dict[str, Any]:
    """Get information about Finnhub data availability."""
    return {
        "source": "Finnhub",
        "api_url": f"{FINNHUB_BASE}/calendar/earnings",
        "api_key_set": bool(FINNHUB_KEY),
        "update_frequency": "Real-time",
        "cost": "FREE (with rate limits)",
        "documentation": "https://finnhub.io/docs/api/earnings-calendar",
        "features": [
            "Upcoming earnings dates",
            "Historical earnings",
            "EPS estimates",
            "Revenue estimates",
            "Earnings surprises",
        ],
    }
