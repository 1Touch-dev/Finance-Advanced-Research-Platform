"""
IPO Calendar Service (Band C #38)
Tracks upcoming IPOs, pricing, lockup expiry dates

Data Source: FMP (FREE) with fallback to mock data
API: https://financialmodelingprep.com/developer/docs/ipo-calendar
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import random
import logging

# Import real data connector
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

log = logging.getLogger(__name__)

# Feature flag: set to True to use real FMP data
USE_REAL_DATA = True


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


# Mock IPO data
MOCK_IPOS = [
    IPO(
        ticker="AIML",
        company_name="AI Machine Learning Corp",
        exchange="NASDAQ",
        ipo_date=(datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"),
        price_range_low=18.0,
        price_range_high=21.0,
        shares_offered=12000000,
        deal_size=240000000,
        lead_underwriters=["Goldman Sachs", "Morgan Stanley"],
        sector="Technology",
        industry="Artificial Intelligence",
        status="expected",
    ),
    IPO(
        ticker="GRNE",
        company_name="GreenEnergy Solutions",
        exchange="NYSE",
        ipo_date=(datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
        price_range_low=14.0,
        price_range_high=16.0,
        shares_offered=20000000,
        deal_size=300000000,
        lead_underwriters=["JPMorgan", "Bank of America"],
        sector="Energy",
        industry="Renewable Energy",
        status="expected",
    ),
    IPO(
        ticker="HLTH",
        company_name="HealthTech Innovations",
        exchange="NASDAQ",
        ipo_date=(datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d"),
        price_range_low=22.0,
        price_range_high=25.0,
        shares_offered=8000000,
        deal_size=188000000,
        lead_underwriters=["Citigroup", "Credit Suisse"],
        sector="Healthcare",
        industry="Health Technology",
        status="expected",
    ),
    IPO(
        ticker="FINX",
        company_name="FinanceX Platform",
        exchange="NYSE",
        ipo_date=(datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
        price_range_low=28.0,
        price_range_high=32.0,
        offer_price=30.0,
        shares_offered=15000000,
        deal_size=450000000,
        lead_underwriters=["Goldman Sachs", "Barclays"],
        sector="Financials",
        industry="Fintech",
        status="priced",
        lockup_expiry=(datetime.now() + timedelta(days=175)).strftime("%Y-%m-%d"),
        first_day_close=38.50,
        first_day_return=28.33,
        current_price=42.15,
    ),
    IPO(
        ticker="CYBR",
        company_name="CyberShield Security",
        exchange="NASDAQ",
        ipo_date=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
        price_range_low=16.0,
        price_range_high=18.0,
        offer_price=17.0,
        shares_offered=10000000,
        deal_size=170000000,
        lead_underwriters=["Morgan Stanley"],
        sector="Technology",
        industry="Cybersecurity",
        status="priced",
        lockup_expiry=(datetime.now() + timedelta(days=150)).strftime("%Y-%m-%d"),
        first_day_close=22.80,
        first_day_return=34.12,
        current_price=25.40,
    ),
    IPO(
        ticker="EVMO",
        company_name="EV Motors Inc",
        exchange="NASDAQ",
        ipo_date=(datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"),
        price_range_low=24.0,
        price_range_high=28.0,
        offer_price=26.0,
        shares_offered=18000000,
        deal_size=468000000,
        lead_underwriters=["JPMorgan", "Goldman Sachs", "Deutsche Bank"],
        sector="Consumer Discretionary",
        industry="Electric Vehicles",
        status="priced",
        lockup_expiry=(datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d"),
        first_day_close=31.20,
        first_day_return=20.0,
        current_price=28.75,
    ),
    IPO(
        ticker="SPCE2",
        company_name="SpaceTech Ventures",
        exchange="NYSE",
        ipo_date=(datetime.now() + timedelta(days=21)).strftime("%Y-%m-%d"),
        price_range_low=35.0,
        price_range_high=40.0,
        shares_offered=25000000,
        deal_size=937500000,
        lead_underwriters=["Goldman Sachs", "Morgan Stanley", "Citigroup"],
        sector="Industrials",
        industry="Aerospace",
        status="expected",
    ),
    IPO(
        ticker="RXMD",
        company_name="RxMedicine Digital",
        exchange="NASDAQ",
        ipo_date=(datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d"),
        price_range_low=12.0,
        price_range_high=14.0,
        shares_offered=6000000,
        deal_size=78000000,
        lead_underwriters=["Jefferies"],
        sector="Healthcare",
        industry="Digital Health",
        status="expected",
    ),
]


def get_upcoming_ipos(days: int = 30, sector: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get upcoming IPOs within the specified number of days.

    Uses FMP real data when available, falls back to mock data.
    """
    if USE_REAL_DATA:
        try:
            real_ipos = fmp_get_upcoming(days_ahead=days, sector=sector)
            if real_ipos:
                return real_ipos
        except Exception as e:
            log.warning("FMP IPO fetch failed, using mock: %s", e)

    # Fallback to mock data
    cutoff_date = datetime.now() + timedelta(days=days)
    today = datetime.now()

    upcoming = []
    for ipo in MOCK_IPOS:
        ipo_date = datetime.strptime(ipo.ipo_date, "%Y-%m-%d")
        if ipo_date >= today and ipo_date <= cutoff_date and ipo.status == "expected":
            if sector is None or ipo.sector.lower() == sector.lower():
                upcoming.append(ipo.to_dict())

    # Sort by date
    upcoming.sort(key=lambda x: x["ipo_date"])
    return upcoming


def get_recent_ipos(days: int = 30, limit: int = 20) -> List[Dict[str, Any]]:
    """Get recently priced IPOs.

    Uses FMP real data when available, falls back to mock data.
    """
    if USE_REAL_DATA:
        try:
            real_ipos = fmp_get_recent(days_back=days, limit=limit)
            if real_ipos:
                return real_ipos
        except Exception as e:
            log.warning("FMP recent IPOs fetch failed, using mock: %s", e)

    # Fallback to mock data
    cutoff_date = datetime.now() - timedelta(days=days)

    recent = []
    for ipo in MOCK_IPOS:
        ipo_date = datetime.strptime(ipo.ipo_date, "%Y-%m-%d")
        if ipo_date >= cutoff_date and ipo.status == "priced":
            recent.append(ipo.to_dict())

    # Sort by date descending
    recent.sort(key=lambda x: x["ipo_date"], reverse=True)
    return recent[:limit]


def get_ipo_by_ticker(ticker: str) -> Optional[Dict[str, Any]]:
    """Get IPO details by ticker.

    Uses FMP real data when available, falls back to mock data.
    """
    if USE_REAL_DATA:
        try:
            real_ipo = fmp_get_ticker(ticker)
            if real_ipo:
                return real_ipo
        except Exception as e:
            log.warning("FMP IPO ticker fetch failed, using mock: %s", e)

    # Fallback to mock data
    for ipo in MOCK_IPOS:
        if ipo.ticker.upper() == ticker.upper():
            return ipo.to_dict()
    return None


def get_lockup_expirations(days: int = 30) -> List[Dict[str, Any]]:
    """Get upcoming lockup expirations.

    Uses FMP real data when available, falls back to mock data.
    """
    if USE_REAL_DATA:
        try:
            real_lockups = fmp_get_lockups(days_ahead=days)
            if real_lockups:
                return real_lockups
        except Exception as e:
            log.warning("FMP lockup expirations fetch failed, using mock: %s", e)

    # Fallback to mock data
    cutoff_date = datetime.now() + timedelta(days=days)
    today = datetime.now()

    expirations = []
    for ipo in MOCK_IPOS:
        if ipo.lockup_expiry:
            expiry_date = datetime.strptime(ipo.lockup_expiry, "%Y-%m-%d")
            if expiry_date >= today and expiry_date <= cutoff_date:
                days_until = (expiry_date - today).days
                expirations.append({
                    **ipo.to_dict(),
                    "days_until_lockup_expiry": days_until,
                })

    # Sort by expiry date
    expirations.sort(key=lambda x: x["lockup_expiry"])
    return expirations


def get_ipo_calendar_week() -> Dict[str, List[Dict[str, Any]]]:
    """Get IPO calendar for the current week.

    Uses FMP real data when available, falls back to mock data.
    """
    if USE_REAL_DATA:
        try:
            real_week = fmp_get_week()
            if real_week:
                return real_week
        except Exception as e:
            log.warning("FMP week calendar fetch failed, using mock: %s", e)

    # Fallback to mock data
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())

    calendar = {}
    for i in range(7):
        day = start_of_week + timedelta(days=i)
        day_str = day.strftime("%Y-%m-%d")
        day_name = day.strftime("%A")
        calendar[f"{day_name} ({day_str})"] = []

    for ipo in MOCK_IPOS:
        ipo_date = datetime.strptime(ipo.ipo_date, "%Y-%m-%d")
        if start_of_week <= ipo_date < start_of_week + timedelta(days=7):
            day_name = ipo_date.strftime("%A")
            day_str = ipo_date.strftime("%Y-%m-%d")
            key = f"{day_name} ({day_str})"
            if key in calendar:
                calendar[key].append(ipo.to_dict())

    return calendar


def get_ipo_performance(days: int = 90) -> List[Dict[str, Any]]:
    """Get IPO performance stats for recent IPOs.

    Uses FMP real data when available, falls back to mock data.
    """
    if USE_REAL_DATA:
        try:
            real_perf = fmp_get_performance(days_back=days)
            if real_perf:
                return real_perf
        except Exception as e:
            log.warning("FMP IPO performance fetch failed, using mock: %s", e)

    # Fallback to mock data
    cutoff_date = datetime.now() - timedelta(days=days)

    performance = []
    for ipo in MOCK_IPOS:
        if ipo.status == "priced" and ipo.offer_price and ipo.current_price:
            ipo_date = datetime.strptime(ipo.ipo_date, "%Y-%m-%d")
            if ipo_date >= cutoff_date:
                total_return = ((ipo.current_price - ipo.offer_price) / ipo.offer_price) * 100
                performance.append({
                    **ipo.to_dict(),
                    "total_return": round(total_return, 2),
                    "days_since_ipo": (datetime.now() - ipo_date).days,
                })

    # Sort by total return descending
    performance.sort(key=lambda x: x["total_return"], reverse=True)
    return performance


def get_ipo_stats() -> Dict[str, Any]:
    """Get IPO market statistics.

    Uses FMP real data when available, falls back to mock data.
    """
    if USE_REAL_DATA:
        try:
            real_stats = fmp_get_stats()
            if real_stats:
                return real_stats
        except Exception as e:
            log.warning("FMP IPO stats fetch failed, using mock: %s", e)

    # Fallback to mock data
    upcoming = [ipo for ipo in MOCK_IPOS if ipo.status == "expected"]
    priced = [ipo for ipo in MOCK_IPOS if ipo.status == "priced"]

    total_deal_size_upcoming = sum(ipo.deal_size for ipo in upcoming)
    total_deal_size_priced = sum(ipo.deal_size for ipo in priced)

    avg_first_day_return = 0
    priced_with_returns = [ipo for ipo in priced if ipo.first_day_return]
    if priced_with_returns:
        avg_first_day_return = sum(ipo.first_day_return for ipo in priced_with_returns) / len(priced_with_returns)

    # Count by sector
    sector_counts = {}
    for ipo in MOCK_IPOS:
        sector_counts[ipo.sector] = sector_counts.get(ipo.sector, 0) + 1

    return {
        "upcoming_count": len(upcoming),
        "priced_count": len(priced),
        "total_deal_size_upcoming": total_deal_size_upcoming,
        "total_deal_size_priced": total_deal_size_priced,
        "avg_first_day_return": round(avg_first_day_return, 2),
        "by_sector": sector_counts,
        "next_ipo": upcoming[0].to_dict() if upcoming else None,
    }


def search_ipos(query: str) -> List[Dict[str, Any]]:
    """Search IPOs by company name or ticker.

    Uses FMP real data when available, falls back to mock data.
    """
    if USE_REAL_DATA:
        try:
            real_results = fmp_search(query)
            if real_results:
                return real_results
        except Exception as e:
            log.warning("FMP IPO search failed, using mock: %s", e)

    # Fallback to mock data
    query = query.lower()
    results = []

    for ipo in MOCK_IPOS:
        if query in ipo.ticker.lower() or query in ipo.company_name.lower():
            results.append(ipo.to_dict())

    return results


def get_ipos_by_sector(sector: str) -> List[Dict[str, Any]]:
    """Get all IPOs in a specific sector"""
    results = []
    for ipo in MOCK_IPOS:
        if ipo.sector.lower() == sector.lower():
            results.append(ipo.to_dict())

    results.sort(key=lambda x: x["ipo_date"], reverse=True)
    return results
