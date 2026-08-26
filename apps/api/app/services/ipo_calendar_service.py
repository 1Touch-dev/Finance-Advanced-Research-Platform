"""
IPO Calendar Service (Band C #38)
Tracks upcoming IPOs, pricing, lockup expiry dates

Data Sources:
  - Primary: Finnhub (FREE, working)
  - Fallback: FMP (deprecated endpoint as of Aug 2025)

NO MOCK DATA - uses no_data_response when real data unavailable.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging

# Import real data connectors
from app.connectors.fmp_ipo_connector import (
    get_upcoming_ipos as fmp_get_upcoming,
    get_recent_ipos as fmp_get_recent,
    get_ipo_by_ticker as fmp_get_ticker,
    get_lockup_expirations as fmp_get_lockups,
    get_ipo_calendar_week as fmp_get_week,
    get_ipo_performance as fmp_get_performance,
    get_ipo_stats as fmp_get_stats,
    search_ipos as fmp_search,
    get_fmp_data_info,
)

# Finnhub IPO calendar (primary source - working)
from app.connectors.financial_news_connector import finnhub_ipo_calendar

# No-data contract (S0-C Mock Ban)
from app.core.no_data import no_data_response, NoDataReason

log = logging.getLogger(__name__)


@dataclass
class IPO:
    """IPO listing data"""
    ticker: str
    company_name: str
    exchange: str
    ipo_date: str
    price_range_low: float
    price_range_high: float
    offer_price: Optional[float] = None
    shares_offered: int = 0
    deal_size: float = 0.0
    lead_underwriters: List[str] = field(default_factory=list)
    sector: str = ""
    industry: str = ""
    status: str = "expected"  # expected, priced, withdrawn, postponed
    lockup_expiry: Optional[str] = None
    first_day_close: Optional[float] = None
    first_day_return: Optional[float] = None
    current_price: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "exchange": self.exchange,
            "ipo_date": self.ipo_date,
            "price_range_low": self.price_range_low,
            "price_range_high": self.price_range_high,
            "offer_price": self.offer_price,
            "shares_offered": self.shares_offered,
            "deal_size": self.deal_size,
            "lead_underwriters": self.lead_underwriters,
            "sector": self.sector,
            "industry": self.industry,
            "status": self.status,
            "lockup_expiry": self.lockup_expiry,
            "first_day_close": self.first_day_close,
            "first_day_return": self.first_day_return,
            "current_price": self.current_price,
        }


# NO MOCK DATA - Mock ban contract (S0-C)
# Previously had MOCK_IPOS list here - REMOVED per mock ban


def get_upcoming_ipos(days: int = 30, sector: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get upcoming IPOs within the specified number of days.

    Data sources (in priority order):
    1. Finnhub IPO Calendar (working)
    2. FMP IPO Calendar (deprecated endpoint - may fail)

    Returns empty list with no_data info if all sources fail.
    """
    # Try Finnhub first (primary, working)
    try:
        from_date = datetime.now().strftime("%Y-%m-%d")
        to_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        finnhub_ipos = finnhub_ipo_calendar(from_date, to_date)
        if finnhub_ipos:
            # Filter by sector if specified
            if sector:
                finnhub_ipos = [i for i in finnhub_ipos if i.get("sector", "").lower() == sector.lower()]
            # Sort by date
            finnhub_ipos.sort(key=lambda x: x.get("ipo_date", ""))
            return finnhub_ipos
    except Exception as e:
        log.warning("Finnhub IPO fetch failed: %s", e)

    # Try FMP as fallback
    try:
        real_ipos = fmp_get_upcoming(days_ahead=days, sector=sector)
        if real_ipos:
            return real_ipos
    except Exception as e:
        log.warning("FMP IPO fetch failed: %s", e)

    # Both sources failed - return empty list (no mock data per S0-C)
    log.info("IPO calendar: no data available from Finnhub or FMP")
    return []


def get_recent_ipos(days: int = 30, limit: int = 20) -> List[Dict[str, Any]]:
    """Get recently priced IPOs.

    Data sources: Finnhub (primary), FMP (fallback).
    NO MOCK DATA per S0-C.
    """
    # Try Finnhub first
    try:
        from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        to_date = datetime.now().strftime("%Y-%m-%d")
        finnhub_ipos = finnhub_ipo_calendar(from_date, to_date)
        if finnhub_ipos:
            # Sort by date descending
            finnhub_ipos.sort(key=lambda x: x.get("ipo_date", ""), reverse=True)
            return finnhub_ipos[:limit]
    except Exception as e:
        log.warning("Finnhub recent IPOs fetch failed: %s", e)

    # Try FMP as fallback
    try:
        real_ipos = fmp_get_recent(days_back=days, limit=limit)
        if real_ipos:
            return real_ipos
    except Exception as e:
        log.warning("FMP recent IPOs fetch failed: %s", e)

    # No data available - return empty (no mock)
    return []


def get_ipo_by_ticker(ticker: str) -> Optional[Dict[str, Any]]:
    """Get IPO details by ticker.

    Data sources: FMP (has ticker search).
    NO MOCK DATA per S0-C.
    """
    try:
        real_ipo = fmp_get_ticker(ticker)
        if real_ipo:
            return real_ipo
    except Exception as e:
        log.warning("FMP IPO ticker fetch failed: %s", e)

    return None


def get_lockup_expirations(days: int = 30) -> List[Dict[str, Any]]:
    """Get upcoming lockup expirations.

    Data sources: FMP.
    NO MOCK DATA per S0-C.
    """
    try:
        real_lockups = fmp_get_lockups(days_ahead=days)
        if real_lockups:
            return real_lockups
    except Exception as e:
        log.warning("FMP lockup expirations fetch failed: %s", e)

    return []


def get_ipo_calendar_week() -> Dict[str, List[Dict[str, Any]]]:
    """Get IPO calendar for the current week.

    Data sources: Finnhub (primary), FMP (fallback).
    NO MOCK DATA per S0-C.
    """
    # Try Finnhub first
    try:
        today = datetime.now()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        finnhub_ipos = finnhub_ipo_calendar(
            start_of_week.strftime("%Y-%m-%d"),
            end_of_week.strftime("%Y-%m-%d")
        )

        if finnhub_ipos:
            # Group by date
            calendar = {}
            for i in range(7):
                day = start_of_week + timedelta(days=i)
                day_str = day.strftime("%Y-%m-%d")
                day_name = day.strftime("%A")
                calendar[f"{day_name} ({day_str})"] = []

            for ipo in finnhub_ipos:
                ipo_date = ipo.get("ipo_date", "")
                try:
                    ipo_dt = datetime.strptime(ipo_date, "%Y-%m-%d")
                    day_name = ipo_dt.strftime("%A")
                    key = f"{day_name} ({ipo_date})"
                    if key in calendar:
                        calendar[key].append(ipo)
                except ValueError as e:
                    log.debug("Failed to parse IPO date '%s': %s", ipo_date, e)

            return calendar
    except Exception as e:
        log.warning("Finnhub week calendar fetch failed: %s", e)

    # Try FMP as fallback
    try:
        real_week = fmp_get_week()
        if real_week:
            return real_week
    except Exception as e:
        log.warning("FMP week calendar fetch failed: %s", e)

    # Return empty calendar structure (no mock)
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    calendar = {}
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        day_name = day.strftime("%A")
        calendar[f"{day_name} ({day_str})"] = []
    return calendar


def get_ipo_performance(days: int = 90) -> List[Dict[str, Any]]:
    """Get IPO performance stats for recent IPOs.

    Data sources: FMP.
    NO MOCK DATA per S0-C.
    """
    try:
        real_perf = fmp_get_performance(days_back=days)
        if real_perf:
            return real_perf
    except Exception as e:
        log.warning("FMP IPO performance fetch failed: %s", e)

    return []


def get_ipo_stats() -> Dict[str, Any]:
    """Get IPO market statistics.

    Data sources: Finnhub + FMP.
    NO MOCK DATA per S0-C.
    """
    # Try FMP stats first (has more data)
    try:
        real_stats = fmp_get_stats()
        if real_stats:
            return real_stats
    except Exception as e:
        log.warning("FMP IPO stats fetch failed: %s", e)

    # Build stats from Finnhub data
    try:
        upcoming = get_upcoming_ipos(days=30)
        recent = get_recent_ipos(days=30)

        return {
            "upcoming_count": len(upcoming),
            "recent_count": len(recent),
            "total_upcoming_deal_size": sum(i.get("deal_size", 0) for i in upcoming),
            "total_recent_deal_size": sum(i.get("deal_size", 0) for i in recent),
            "next_ipo": upcoming[0] if upcoming else None,
            "source": "Finnhub",
        }
    except Exception as e:
        log.warning("IPO stats calculation failed: %s", e)

    return {"error": "IPO stats unavailable"}


def search_ipos(query: str) -> List[Dict[str, Any]]:
    """Search IPOs by company name or ticker.

    Data sources: FMP.
    NO MOCK DATA per S0-C.
    """
    try:
        real_results = fmp_search(query)
        if real_results:
            return real_results
    except Exception as e:
        log.warning("FMP IPO search failed: %s", e)

    return []


def get_ipos_by_sector(sector: str) -> List[Dict[str, Any]]:
    """Get all IPOs in a specific sector.

    NO MOCK DATA per S0-C.
    """
    return get_upcoming_ipos(days=60, sector=sector)
