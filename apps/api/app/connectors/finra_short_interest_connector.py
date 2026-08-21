"""
FINRA Short Interest Connector

Fetches real short interest data from FINRA's free public API.
Source: https://api.finra.org/data/group/otcMarket/name/EquityShortInterest

FINRA publishes short interest data twice monthly (mid-month and end-of-month).
Data includes:
- Short interest (number of shares)
- Days to cover
- Settlement dates
- 5-year rolling history
"""

import os
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from functools import lru_cache

log = logging.getLogger(__name__)

# FINRA API endpoints
FINRA_API_BASE = "https://api.finra.org/data/group"
FINRA_SHORT_INTEREST_ENDPOINT = f"{FINRA_API_BASE}/otcMarket/name/EquityShortInterest"

# Cache timeout (15 minutes - short interest updates bi-weekly)
CACHE_TIMEOUT = 900
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


def _post_finra(payload: Dict) -> Optional[List[Dict]]:
    """Make POST request to FINRA API."""
    try:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        r = requests.post(
            FINRA_SHORT_INTEREST_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=_TIMEOUT
        )
        if r.status_code == 200:
            return r.json()
        log.warning("FINRA API returned %s: %s", r.status_code, r.text[:200])
    except Exception as e:
        log.warning("FINRA API request failed: %s", e)
    return None


def get_short_interest_by_ticker(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Get current short interest for a specific ticker.

    Returns:
        Dict with short interest data or None if not found
    """
    cache_key = f"short_interest_{ticker.upper()}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    # FINRA API requires settlementDate as partition key for sorting
    # First get without sorting, filter by ticker
    payload = {
        "quoteValues": False,
        "delimiter": "|",
        "limit": 10,  # Get recent records for this ticker
        "compareFilters": [
            {
                "fieldName": "issueSymbolIdentifier",
                "fieldValue": ticker.upper(),
                "compareType": "EQUAL"
            }
        ]
    }

    data = _post_finra(payload)
    if not data or len(data) == 0:
        log.info("No FINRA data found for ticker: %s", ticker)
        return None

    # Sort by settlement date to get most recent
    data.sort(key=lambda x: x.get("settlementDate", ""), reverse=True)
    record = data[0]
    result = _parse_finra_record(record)
    _set_cache(cache_key, result)
    return result


def get_short_interest_history(
    ticker: str,
    periods: int = 12
) -> List[Dict[str, Any]]:
    """
    Get historical short interest for a ticker.

    Args:
        ticker: Stock symbol
        periods: Number of settlement periods to fetch (max ~60 for 5 years)

    Returns:
        List of historical short interest records
    """
    cache_key = f"short_history_{ticker.upper()}_{periods}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    # FINRA API requires settlementDate partition key for sorting
    # Get more records and sort client-side
    payload = {
        "quoteValues": False,
        "delimiter": "|",
        "limit": periods * 2,  # Get extra in case of gaps
        "compareFilters": [
            {
                "fieldName": "issueSymbolIdentifier",
                "fieldValue": ticker.upper(),
                "compareType": "EQUAL"
            }
        ]
    }

    data = _post_finra(payload)
    if not data:
        return []

    # Sort by settlement date descending
    data.sort(key=lambda x: x.get("settlementDate", ""), reverse=True)

    # Take only requested periods
    history = [_parse_finra_record(record) for record in data[:periods]]
    history.reverse()  # Oldest first
    _set_cache(cache_key, history)
    return history


def get_most_shorted_stocks(
    min_short_interest: int = 1_000_000,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get most heavily shorted stocks.

    Args:
        min_short_interest: Minimum number of shares short
        limit: Maximum results to return

    Returns:
        List of most shorted stocks sorted by short interest
    """
    cache_key = f"most_shorted_{min_short_interest}_{limit}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    # Get data without settlement date filter (FINRA API limitation)
    # Then filter and sort client-side
    payload = {
        "quoteValues": False,
        "delimiter": "|",
        "limit": limit * 5,  # Get more to filter
        "compareFilters": [
            {
                "fieldName": "currentShortShareNumber",
                "fieldValue": str(min_short_interest),
                "compareType": "GREATER"
            }
        ]
    }

    data = _post_finra(payload)
    if not data:
        # Fallback: try yfinance for most shorted
        return _get_most_shorted_yfinance(limit)

    # Group by ticker, take most recent for each
    ticker_data = {}
    for record in data:
        ticker = record.get("issueSymbolIdentifier", "")
        settlement = record.get("settlementDate", "")
        if ticker not in ticker_data or settlement > ticker_data[ticker].get("settlementDate", ""):
            ticker_data[ticker] = record

    # Sort by short interest descending
    sorted_data = sorted(
        ticker_data.values(),
        key=lambda x: x.get("currentShortShareNumber", 0),
        reverse=True
    )

    result = [_parse_finra_record(record) for record in sorted_data[:limit]]
    _set_cache(cache_key, result)
    return result


def _get_most_shorted_yfinance(limit: int = 50) -> List[Dict[str, Any]]:
    """Fallback to yfinance for most shorted stocks."""
    try:
        import yfinance as yf

        # Common heavily shorted tickers to check (exclude bankrupt/delisted)
        tickers = [
            "GME", "AMC", "KOSS", "BB", "NOK", "PLTR", "SOFI", "HOOD",
            "RIVN", "LCID", "CVNA", "UPST", "BYND", "SPCE",
            "TLRY", "SNDL", "MVIS", "WKHS", "NKLA", "QS", "LAZR", "OPEN",
            "AAPL", "TSLA", "NVDA", "AMD", "INTC", "META", "GOOGL", "MSFT"
        ]

        results = []
        for ticker in tickers[:limit]:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                shares_short = info.get("sharesShort", 0)
                if shares_short and shares_short > 1_000_000:
                    results.append({
                        "ticker": ticker,
                        "company_name": info.get("shortName", f"{ticker} Inc."),
                        "short_interest": shares_short,
                        "short_percent_float": round(info.get("shortPercentOfFloat", 0) * 100, 2),
                        "prior_short_interest": info.get("sharesShortPriorMonth", 0),
                        "change_percent": 0,
                        "days_to_cover": info.get("shortRatio", 0),
                        "avg_daily_volume": info.get("averageVolume", 0),
                        "settlement_date": info.get("dateShortInterest", ""),
                        "source": "Yahoo Finance (fallback)",
                        "data_freshness": "delayed",
                    })
            except Exception:
                continue

        # Sort by short interest
        results.sort(key=lambda x: x.get("short_interest", 0), reverse=True)
        return results

    except Exception as e:
        log.warning("yfinance most shorted fallback failed: %s", e)
        return []


def get_short_interest_changes(
    min_change_percent: float = 10.0,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get stocks with significant short interest changes.

    Note: FINRA doesn't directly provide change %, so we calculate it
    by fetching current and prior period data.
    """
    cache_key = f"short_changes_{min_change_percent}_{limit}"
    cached = _get_cached(cache_key)
    if cached:
        return cached

    # Get top shorted stocks and calculate changes
    most_shorted = get_most_shorted_stocks(limit=100)

    changes = []
    for stock in most_shorted:
        if stock.get("change_percent") and abs(stock["change_percent"]) >= min_change_percent:
            changes.append(stock)

    # Sort by absolute change
    changes.sort(key=lambda x: abs(x.get("change_percent", 0)), reverse=True)
    result = changes[:limit]
    _set_cache(cache_key, result)
    return result


def _parse_finra_record(record: Dict) -> Dict[str, Any]:
    """Parse FINRA API record into standardized format."""
    # Updated field names for current FINRA API (2024+)
    current_short = record.get("currentShortShareNumber", 0) or record.get("currentShortPositionQuantity", 0)
    prior_short = record.get("previousShortShareNumber", 0) or record.get("previousShortPositionQuantity", 0)
    days_to_cover = record.get("daysToCoverNumber", 0)
    change_percent = record.get("changePercent", 0) or record.get("percentageChangefromPreviousShort", 0)

    # Avg volume might not be directly available - estimate from days to cover
    avg_volume = record.get("averageShortShareNumber", 0) or record.get("averageDailyVolumeQuantity", 0)
    if avg_volume == 0 and days_to_cover > 0 and current_short > 0:
        avg_volume = int(current_short / days_to_cover) if days_to_cover < 999 else 0

    # Calculate change percent if not provided
    if change_percent == 0 and prior_short > 0:
        change_percent = ((current_short - prior_short) / prior_short) * 100

    return {
        "ticker": record.get("issueSymbolIdentifier", "") or record.get("symbolCode", ""),
        "company_name": record.get("issueName", ""),
        "short_interest": current_short,
        "prior_short_interest": prior_short,
        "change_percent": round(change_percent, 2) if change_percent else 0,
        "avg_daily_volume": avg_volume,
        "days_to_cover": round(days_to_cover, 2) if days_to_cover and days_to_cover < 999 else 0,
        "settlement_date": record.get("settlementDate", ""),
        "market": record.get("marketCategoryCode", "") or record.get("marketClassCode", ""),
        "market_description": record.get("marketCategoryDescription", ""),
        "source": "FINRA",
        "data_freshness": "bi-weekly",
    }


def get_finra_data_info() -> Dict[str, Any]:
    """Get information about FINRA data availability."""
    # Get latest settlement date
    payload = {
        "quoteValues": False,
        "limit": 1,
        "sortFields": ["-settlementDate"],
    }

    latest = _post_finra(payload)

    return {
        "source": "FINRA",
        "api_url": FINRA_SHORT_INTEREST_ENDPOINT,
        "update_frequency": "Bi-weekly (mid-month and end-of-month)",
        "latest_settlement_date": latest[0].get("settlementDate") if latest else None,
        "data_coverage": "All exchange-listed and OTC equity securities",
        "cost": "FREE",
        "documentation": "https://www.finra.org/finra-data/browse-catalog/equity-short-interest",
    }


# Fallback to yfinance if FINRA doesn't have data
def get_short_interest_fallback(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Fallback to yfinance for short interest data.
    Used when FINRA doesn't have data for a ticker.
    """
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        info = stock.info

        short_percent = info.get("shortPercentOfFloat", 0)
        shares_short = info.get("sharesShort", 0)
        shares_short_prior = info.get("sharesShortPriorMonth", 0)
        short_ratio = info.get("shortRatio", 0)  # Days to cover

        if not shares_short:
            return None

        change_pct = 0
        if shares_short_prior > 0:
            change_pct = ((shares_short - shares_short_prior) / shares_short_prior) * 100

        return {
            "ticker": ticker.upper(),
            "company_name": info.get("shortName", f"{ticker} Inc."),
            "short_interest": shares_short,
            "short_percent_float": round(short_percent * 100, 2) if short_percent else 0,
            "prior_short_interest": shares_short_prior,
            "change_percent": round(change_pct, 2),
            "days_to_cover": round(short_ratio, 2) if short_ratio else 0,
            "avg_daily_volume": info.get("averageVolume", 0),
            "settlement_date": info.get("dateShortInterest", ""),
            "source": "Yahoo Finance (fallback)",
            "data_freshness": "delayed",
        }
    except Exception as e:
        log.warning("yfinance fallback failed for %s: %s", ticker, e)
        return None


def get_short_interest(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Get short interest with automatic fallback.
    Tries FINRA first, falls back to yfinance.
    """
    # Try FINRA first
    result = get_short_interest_by_ticker(ticker)
    if result:
        return result

    # Fallback to yfinance
    return get_short_interest_fallback(ticker)
