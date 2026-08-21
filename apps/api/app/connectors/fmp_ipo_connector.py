"""
FMP (Financial Modeling Prep) IPO Calendar Connector

Fetches real IPO calendar data from FMP's free API.
Source: https://financialmodelingprep.com/developer/docs/ipo-calendar

Features:
- Upcoming IPOs
- Recent IPO listings
- IPO pricing and performance
- Lockup expirations
"""

import os
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

log = logging.getLogger(__name__)

FMP_KEY = os.getenv("FMP_API_KEY", "")
FMP_BASE = "https://financialmodelingprep.com/api/v3"

# Cache timeout (30 minutes for IPO data)
CACHE_TIMEOUT = 1800
_cache: Dict[str, Any] = {}
_cache_time: Dict[str, datetime] = {}

_TIMEOUT = 15


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


def _get_fmp(endpoint: str, params: Dict = None) -> Optional[Any]:
    """Make GET request to FMP API."""
    if not FMP_KEY:
        log.warning("FMP_API_KEY not set")
        return None

    try:
        params = params or {}
        params["apikey"] = FMP_KEY
        url = f"{FMP_BASE}{endpoint}"

        r = requests.get(url, params=params, timeout=_TIMEOUT)
        if r.status_code == 200:
            return r.json()
        log.warning("FMP API returned %s: %s", r.status_code, r.text[:200])
    except Exception as e:
        log.warning("FMP API request failed: %s", e)
    return None


def get_ipo_calendar(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get IPO calendar for a date range.

    Args:
        from_date: Start date (YYYY-MM-DD), defaults to today
        to_date: End date (YYYY-MM-DD), defaults to 30 days from now

    Returns:
        List of IPO events
    """
    if not from_date:
        from_date = datetime.utcnow().strftime("%Y-%m-%d")
    if not to_date:
        to_date = (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")

    cache_key = f"ipo_calendar_{from_date}_{to_date}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    params = {
        "from": from_date,
        "to": to_date,
    }

    data = _get_fmp("/ipo_calendar", params)
    if not data:
        return []

    results = [_parse_ipo_event(event) for event in data]

    # Sort by date
    results.sort(key=lambda x: x.get("ipo_date", ""))
    _set_cache(cache_key, results)
    return results


def get_upcoming_ipos(
    days_ahead: int = 30,
    sector: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Get upcoming IPOs for the next N days.

    Args:
        days_ahead: Number of days to look ahead
        sector: Optional sector filter

    Returns:
        List of upcoming IPOs
    """
    from_date = datetime.utcnow().strftime("%Y-%m-%d")
    to_date = (datetime.utcnow() + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    events = get_ipo_calendar(from_date, to_date)

    # Filter by status (expected only)
    events = [e for e in events if e.get("status") == "expected"]

    if sector:
        events = [e for e in events if e.get("sector", "").lower() == sector.lower()]

    return events


def get_recent_ipos(
    days_back: int = 30,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Get recently priced IPOs.

    Args:
        days_back: Number of days to look back
        limit: Maximum results

    Returns:
        List of recent IPOs with performance data
    """
    cache_key = f"recent_ipos_{days_back}_{limit}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    from_date = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
    to_date = datetime.utcnow().strftime("%Y-%m-%d")

    events = get_ipo_calendar(from_date, to_date)

    # Filter to priced only
    priced = [e for e in events if e.get("status") == "priced"]

    # Sort by date descending
    priced.sort(key=lambda x: x.get("ipo_date", ""), reverse=True)

    result = priced[:limit]
    _set_cache(cache_key, result)
    return result


def get_ipo_by_ticker(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Get IPO details for a specific ticker.

    Searches both upcoming and recent IPOs.
    """
    cache_key = f"ipo_ticker_{ticker}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    # Search in upcoming (next 60 days)
    upcoming = get_ipo_calendar(
        datetime.utcnow().strftime("%Y-%m-%d"),
        (datetime.utcnow() + timedelta(days=60)).strftime("%Y-%m-%d")
    )

    for ipo in upcoming:
        if ipo.get("ticker", "").upper() == ticker.upper():
            _set_cache(cache_key, ipo)
            return ipo

    # Search in recent (past 180 days)
    recent = get_ipo_calendar(
        (datetime.utcnow() - timedelta(days=180)).strftime("%Y-%m-%d"),
        datetime.utcnow().strftime("%Y-%m-%d")
    )

    for ipo in recent:
        if ipo.get("ticker", "").upper() == ticker.upper():
            # Enhance with current price data
            ipo = _enhance_ipo_with_price(ipo)
            _set_cache(cache_key, ipo)
            return ipo

    return None


def get_ipo_calendar_week(start_date: Optional[str] = None) -> Dict[str, List[Dict]]:
    """
    Get IPO calendar for a week, grouped by date.

    Args:
        start_date: Week start date (defaults to current Monday)

    Returns:
        Dict mapping dates to IPO events
    """
    if start_date:
        week_start = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        today = datetime.utcnow()
        week_start = today - timedelta(days=today.weekday())  # Monday

    week_end = week_start + timedelta(days=6)  # Sunday

    events = get_ipo_calendar(
        week_start.strftime("%Y-%m-%d"),
        week_end.strftime("%Y-%m-%d")
    )

    # Group by date
    calendar = {}
    for i in range(7):
        day = week_start + timedelta(days=i)
        date_str = day.strftime("%Y-%m-%d")
        day_name = day.strftime("%A")
        calendar[f"{day_name} ({date_str})"] = []

    for event in events:
        date = event.get("ipo_date", "")
        try:
            event_dt = datetime.strptime(date, "%Y-%m-%d")
            day_name = event_dt.strftime("%A")
            key = f"{day_name} ({date})"
            if key in calendar:
                calendar[key].append(event)
        except ValueError:
            pass

    return calendar


def get_lockup_expirations(days_ahead: int = 30) -> List[Dict[str, Any]]:
    """
    Get upcoming lockup expirations.

    IPO lockup periods are typically 180 days.
    """
    cache_key = f"lockup_expirations_{days_ahead}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    # Look at IPOs from ~210 to ~150 days ago (lockups expiring soon)
    search_from = (datetime.utcnow() - timedelta(days=210)).strftime("%Y-%m-%d")
    search_to = (datetime.utcnow() - timedelta(days=150)).strftime("%Y-%m-%d")

    past_ipos = get_ipo_calendar(search_from, search_to)

    expirations = []
    for ipo in past_ipos:
        if ipo.get("status") != "priced":
            continue

        # Calculate lockup expiry (180 days from IPO)
        try:
            ipo_date = datetime.strptime(ipo.get("ipo_date", ""), "%Y-%m-%d")
            lockup_expiry = ipo_date + timedelta(days=180)
            days_until = (lockup_expiry - datetime.utcnow()).days

            if 0 <= days_until <= days_ahead:
                ipo["lockup_expiry"] = lockup_expiry.strftime("%Y-%m-%d")
                ipo["days_until_lockup_expiry"] = days_until
                expirations.append(ipo)
        except ValueError:
            pass

    # Sort by expiry date
    expirations.sort(key=lambda x: x.get("days_until_lockup_expiry", 999))
    _set_cache(cache_key, expirations)
    return expirations


def get_ipo_performance(days_back: int = 90) -> List[Dict[str, Any]]:
    """
    Get IPO performance stats for recent IPOs.
    """
    recent = get_recent_ipos(days_back, limit=50)

    performance = []
    for ipo in recent:
        if ipo.get("offer_price") and ipo.get("current_price"):
            total_return = (
                (ipo["current_price"] - ipo["offer_price"]) / ipo["offer_price"]
            ) * 100
            ipo["total_return"] = round(total_return, 2)

            try:
                ipo_date = datetime.strptime(ipo.get("ipo_date", ""), "%Y-%m-%d")
                ipo["days_since_ipo"] = (datetime.utcnow() - ipo_date).days
            except ValueError:
                ipo["days_since_ipo"] = 0

            performance.append(ipo)

    # Sort by total return
    performance.sort(key=lambda x: x.get("total_return", 0), reverse=True)
    return performance


def get_ipo_stats() -> Dict[str, Any]:
    """Get IPO market statistics."""
    upcoming = get_upcoming_ipos(days_ahead=30)
    recent = get_recent_ipos(days_back=30)

    # Calculate stats
    total_upcoming_size = sum(ipo.get("deal_size", 0) for ipo in upcoming)
    total_recent_size = sum(ipo.get("deal_size", 0) for ipo in recent)

    # Average first day return
    first_day_returns = [
        ipo.get("first_day_return", 0)
        for ipo in recent
        if ipo.get("first_day_return") is not None
    ]
    avg_first_day_return = (
        sum(first_day_returns) / len(first_day_returns)
        if first_day_returns else 0
    )

    # Count by sector
    sector_counts = {}
    for ipo in upcoming + recent:
        sector = ipo.get("sector", "Unknown")
        sector_counts[sector] = sector_counts.get(sector, 0) + 1

    return {
        "upcoming_count": len(upcoming),
        "recent_count": len(recent),
        "total_upcoming_deal_size": total_upcoming_size,
        "total_recent_deal_size": total_recent_size,
        "avg_first_day_return": round(avg_first_day_return, 2),
        "by_sector": sector_counts,
        "next_ipo": upcoming[0] if upcoming else None,
        "source": "FMP",
        "last_updated": datetime.utcnow().isoformat(),
    }


def search_ipos(query: str) -> List[Dict[str, Any]]:
    """Search IPOs by company name or ticker."""
    query_lower = query.lower()

    # Search in both upcoming and recent
    upcoming = get_upcoming_ipos(days_ahead=60)
    recent = get_recent_ipos(days_back=180)

    results = []
    for ipo in upcoming + recent:
        if (
            query_lower in ipo.get("ticker", "").lower() or
            query_lower in ipo.get("company_name", "").lower()
        ):
            results.append(ipo)

    return results


def _parse_ipo_event(event: Dict) -> Dict[str, Any]:
    """Parse FMP IPO event into standardized format."""
    # FMP returns different fields depending on the endpoint
    price_range = event.get("priceRange", "")
    price_low = None
    price_high = None

    if price_range and "-" in price_range:
        try:
            parts = price_range.replace("$", "").split("-")
            price_low = float(parts[0].strip())
            price_high = float(parts[1].strip())
        except (ValueError, IndexError):
            pass

    offer_price = event.get("price") or event.get("ipoPrice")
    if isinstance(offer_price, str):
        try:
            offer_price = float(offer_price.replace("$", ""))
        except ValueError:
            offer_price = None

    # Determine status
    ipo_date_str = event.get("date", "")
    status = "expected"
    try:
        ipo_date = datetime.strptime(ipo_date_str, "%Y-%m-%d")
        if ipo_date < datetime.utcnow():
            status = "priced" if offer_price else "unknown"
    except ValueError:
        pass

    return {
        "ticker": event.get("symbol", ""),
        "company_name": event.get("company", event.get("name", "")),
        "exchange": event.get("exchange", ""),
        "ipo_date": ipo_date_str,
        "price_range_low": price_low,
        "price_range_high": price_high,
        "offer_price": offer_price,
        "shares_offered": event.get("numberOfShares", 0),
        "deal_size": event.get("totalSharesValue", 0),
        "lead_underwriters": event.get("marketMaker", "").split(",") if event.get("marketMaker") else [],
        "sector": event.get("sector", ""),
        "industry": event.get("industry", ""),
        "status": status,
        "actions": event.get("actions", ""),
        "source": "FMP",
    }


def _enhance_ipo_with_price(ipo: Dict) -> Dict:
    """Add current price data to IPO using yfinance."""
    try:
        import yfinance as yf
        ticker = ipo.get("ticker", "")
        if not ticker:
            return ipo

        stock = yf.Ticker(ticker)
        info = stock.info

        ipo["current_price"] = info.get("currentPrice") or info.get("regularMarketPrice")

        # Calculate first day return if we have the data
        if ipo.get("offer_price") and ipo.get("current_price"):
            ipo["total_return_from_offer"] = round(
                ((ipo["current_price"] - ipo["offer_price"]) / ipo["offer_price"]) * 100,
                2
            )

        return ipo
    except Exception as e:
        log.warning("Failed to enhance IPO with price data: %s", e)
        return ipo


def get_fmp_data_info() -> Dict[str, Any]:
    """Get information about FMP data availability."""
    return {
        "source": "Financial Modeling Prep (FMP)",
        "api_url": f"{FMP_BASE}/ipo_calendar",
        "api_key_set": bool(FMP_KEY),
        "update_frequency": "Daily",
        "cost": "FREE (with rate limits)",
        "documentation": "https://financialmodelingprep.com/developer/docs/ipo-calendar",
        "features": [
            "Upcoming IPO dates",
            "IPO pricing and deal size",
            "Recent IPO performance",
            "IPO by sector",
        ],
    }
