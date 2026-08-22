"""
Economics / Macro Service — wraps FRED connector with 1-hour caching.
Provides: get_macro_indicators(), get_series(), get_economic_calendar().
All data is REAL from the FRED API (https://api.stlouisfed.org).
"""
import time
import logging
from typing import Optional

from app.connectors.financial_news_connector import (
    fred_macro_data,
    fred_macro_dashboard,
    fred_series_info,
    fred_search,
    fred_vintage_data,
    FRED_SERIES,
    FRED_KEY,
    _get,
)

log = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 3600  # 1 hour

_cache: dict[str, tuple[float, any]] = {}


def _from_cache(key: str):
    entry = _cache.get(key)
    if entry and (time.time() - entry[0]) < CACHE_TTL_SECONDS:
        return entry[1]
    return None


def _to_cache(key: str, value):
    _cache[key] = (time.time(), value)
    return value


# ─── Key series grouped by economic category ────────────────────────────────

MACRO_INDICATORS = {
    "gdp": {
        "series_id": "GDP",
        "name": "Gross Domestic Product",
        "category": "Growth",
        "units": "Billions USD",
        "frequency": "Quarterly",
    },
    "unemployment": {
        "series_id": "UNRATE",
        "name": "Unemployment Rate",
        "category": "Employment",
        "units": "Percent",
        "frequency": "Monthly",
    },
    "cpi": {
        "series_id": "CPIAUCSL",
        "name": "Consumer Price Index (All Urban)",
        "category": "Inflation",
        "units": "Index 1982-84=100",
        "frequency": "Monthly",
    },
    "fed_funds": {
        "series_id": "FEDFUNDS",
        "name": "Federal Funds Effective Rate",
        "category": "Interest Rates",
        "units": "Percent",
        "frequency": "Monthly",
    },
    "treasury_10y": {
        "series_id": "DGS10",
        "name": "10-Year Treasury Constant Maturity",
        "category": "Interest Rates",
        "units": "Percent",
        "frequency": "Daily",
    },
    "sp500": {
        "series_id": "SP500",
        "name": "S&P 500 Index",
        "category": "Markets",
        "units": "Index",
        "frequency": "Daily",
    },
    "m2_money_supply": {
        "series_id": "M2SL",
        "name": "M2 Money Stock",
        "category": "Money Supply",
        "units": "Billions USD",
        "frequency": "Monthly",
    },
    "consumer_sentiment": {
        "series_id": "UMCSENT",
        "name": "University of Michigan Consumer Sentiment",
        "category": "Consumer",
        "units": "Index 1966=100",
        "frequency": "Monthly",
    },
}


def get_macro_indicators(limit: int = 5) -> dict:
    """
    Fetch latest values for the 8 key macro indicators.
    Cached for 1 hour.
    """
    cache_key = f"macro_indicators_{limit}"
    cached = _from_cache(cache_key)
    if cached:
        return cached

    indicators = {}
    for key, meta in MACRO_INDICATORS.items():
        series_id = meta["series_id"]
        observations = fred_macro_data(series_id, limit)
        latest = observations[0] if observations else None
        indicators[key] = {
            **meta,
            "latest_value": latest["value"] if latest else None,
            "latest_date": latest["date"] if latest else None,
            "history": observations,
        }

    result = {
        "indicators": indicators,
        "source": "FRED (Federal Reserve Economic Data)",
        "cache_ttl_seconds": CACHE_TTL_SECONDS,
    }
    return _to_cache(cache_key, result)


def get_series(series_id: str, limit: int = 30, start_date: Optional[str] = None) -> dict:
    """
    Fetch observations for any FRED series by ID.
    Cached per series_id+limit combo for 1 hour.
    """
    cache_key = f"series_{series_id}_{limit}_{start_date}"
    cached = _from_cache(cache_key)
    if cached:
        return cached

    observations = fred_macro_data(series_id, limit)
    info = fred_series_info(series_id)
    meta = FRED_SERIES.get(series_id, {})

    result = {
        "series_id": series_id,
        "name": info.get("title") or meta.get("name", series_id),
        "units": info.get("units") or meta.get("units", "N/A"),
        "frequency": info.get("frequency") or meta.get("frequency", "N/A"),
        "seasonal_adjustment": info.get("seasonal_adjustment"),
        "last_updated": info.get("last_updated"),
        "observation_start": info.get("observation_start"),
        "observation_end": info.get("observation_end"),
        "observations": observations,
        "count": len(observations),
        "source": "FRED",
    }
    return _to_cache(cache_key, result)


def get_economic_calendar() -> dict:
    """
    Build an economic release calendar from FRED series metadata.
    Shows when each key series was last updated and approximate next release.
    Cached for 1 hour.
    """
    cache_key = "economic_calendar"
    cached = _from_cache(cache_key)
    if cached:
        return cached

    calendar_entries = []
    for key, meta in MACRO_INDICATORS.items():
        series_id = meta["series_id"]
        info = fred_series_info(series_id)
        if not info:
            continue
        calendar_entries.append({
            "indicator": key,
            "series_id": series_id,
            "name": info.get("title") or meta["name"],
            "frequency": info.get("frequency") or meta["frequency"],
            "last_updated": info.get("last_updated"),
            "observation_end": info.get("observation_end"),
            "units": info.get("units") or meta["units"],
        })

    # Also fetch FRED release calendar if available
    releases = _fetch_fred_releases()

    result = {
        "indicators": calendar_entries,
        "upcoming_releases": releases,
        "source": "FRED",
        "note": "Release dates are approximate based on historical frequency",
    }
    return _to_cache(cache_key, result)


def _fetch_fred_releases(limit: int = 20) -> list:
    """Fetch upcoming/recent FRED data releases."""
    if not FRED_KEY:
        return []
    data = _get(
        "https://api.stlouisfed.org/fred/releases",
        params={
            "api_key": FRED_KEY,
            "file_type": "json",
            "limit": limit,
            "sort_order": "desc",
            "order_by": "press_release",
        },
    )
    if not data or "releases" not in data:
        return []
    return [
        {
            "id": r.get("id"),
            "name": r.get("name"),
            "press_release": r.get("press_release"),
            "link": r.get("link"),
        }
        for r in data["releases"][:limit]
    ]


def get_full_dashboard() -> dict:
    """
    Full macro dashboard (delegates to connector's fred_macro_dashboard).
    Cached for 1 hour.
    """
    cache_key = "full_dashboard"
    cached = _from_cache(cache_key)
    if cached:
        return cached

    dashboard = fred_macro_dashboard()

    # Enrich with series metadata for frontend display
    series_display = {}
    for sid, meta in FRED_SERIES.items():
        obs = fred_macro_data(sid, 1)
        latest = obs[0] if obs else None
        category = _categorize_series(sid)
        series_display[sid] = {
            "name": meta["name"],
            "units": meta.get("units", ""),
            "frequency": meta.get("frequency", ""),
            "category": category,
            "latest_value": latest["value"] if latest else None,
            "latest_date": latest["date"] if latest else None,
        }

    dashboard["series"] = series_display
    return _to_cache(cache_key, dashboard)


def _categorize_series(series_id: str) -> str:
    """Map a FRED series ID to a display category."""
    categories = {
        "Growth": ["GDP", "GDPC1", "A191RL1Q225SBEA"],
        "Inflation": ["CPIAUCSL", "CPILFESL", "PCEPI", "T10YIE"],
        "Employment": ["UNRATE", "PAYEMS", "ICSA"],
        "Interest Rates": ["FEDFUNDS", "DFF", "DGS10", "DGS2", "T10Y2Y", "BAMLH0A0HYM2"],
        "Money Supply": ["M2SL", "WALCL"],
        "Housing": ["HOUST", "CSUSHPINSA"],
        "Consumer": ["UMCSENT", "INDPRO", "RSXFS"],
    }
    for cat, ids in categories.items():
        if series_id in ids:
            return cat
    return "Other"


def search_series(query: str, limit: int = 10) -> dict:
    """Search FRED series by keyword. Cached for 1 hour."""
    cache_key = f"search_{query}_{limit}"
    cached = _from_cache(cache_key)
    if cached:
        return cached

    results = fred_search(query, limit)
    result = {"query": query, "results": results, "count": len(results)}
    return _to_cache(cache_key, result)


def get_vintage(series_id: str, vintage_date: str, limit: int = 10) -> dict:
    """ALFRED point-in-time vintage data. Cached for 1 hour."""
    cache_key = f"vintage_{series_id}_{vintage_date}_{limit}"
    cached = _from_cache(cache_key)
    if cached:
        return cached

    data = fred_vintage_data(series_id, vintage_date, limit)
    result = {
        "series_id": series_id,
        "vintage_date": vintage_date,
        "data": data,
        "count": len(data),
    }
    return _to_cache(cache_key, result)


def clear_cache():
    """Clear the entire economics cache (useful for admin/debug)."""
    _cache.clear()
    return {"status": "cache_cleared"}
