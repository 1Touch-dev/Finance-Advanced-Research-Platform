"""
Earnings Calendar Service (Band C #36)

Provides earnings calendar data with:
- Upcoming earnings dates by ticker or date range
- Historical earnings dates
- Earnings estimate and surprise data
- Conference call schedules

Data Source: Finnhub (FREE)
API: https://finnhub.io/docs/api/earnings-calendar
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import logging

# Import real data connector
from app.connectors.finnhub_earnings_connector import (
    get_earnings_calendar as finnhub_get_calendar,
    get_upcoming_earnings as finnhub_get_upcoming,
    get_ticker_earnings as finnhub_get_ticker_earnings,
    get_earnings_surprises as finnhub_get_surprises,
    get_earnings_calendar_week as finnhub_get_week,
    get_finnhub_data_info,
)

log = logging.getLogger(__name__)


class EarningsSession(str, Enum):
    PRE_MARKET = "pre_market"
    AFTER_HOURS = "after_hours"
    DURING_MARKET = "during_market"
    UNKNOWN = "unknown"


class EarningsImportance(str, Enum):
    HIGH = "high"      # Major index components, high volume
    MEDIUM = "medium"  # Mid-cap, notable stocks
    LOW = "low"        # Small-cap, less followed


@dataclass
class EarningsEvent:
    ticker: str
    company_name: str
    earnings_date: str
    session: str
    fiscal_quarter: str
    fiscal_year: int
    eps_estimate: Optional[float]
    revenue_estimate: Optional[float]
    eps_actual: Optional[float]  # None if not yet reported
    revenue_actual: Optional[float]
    surprise_percent: Optional[float]
    conference_call_time: Optional[str]
    importance: str
    confirmed: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "earnings_date": self.earnings_date,
            "session": self.session,
            "fiscal_quarter": self.fiscal_quarter,
            "fiscal_year": self.fiscal_year,
            "eps_estimate": self.eps_estimate,
            "revenue_estimate": self.revenue_estimate,
            "eps_actual": self.eps_actual,
            "revenue_actual": self.revenue_actual,
            "surprise_percent": self.surprise_percent,
            "conference_call_time": self.conference_call_time,
            "importance": self.importance,
            "confirmed": self.confirmed,
        }


# Ticker importance lookup for classification
COMPANIES = {
    "AAPL": ("Apple Inc.", "high"),
    "MSFT": ("Microsoft Corp.", "high"),
    "GOOGL": ("Alphabet Inc.", "high"),
    "AMZN": ("Amazon.com Inc.", "high"),
    "NVDA": ("NVIDIA Corp.", "high"),
    "META": ("Meta Platforms Inc.", "high"),
    "TSLA": ("Tesla Inc.", "high"),
    "JPM": ("JPMorgan Chase & Co.", "high"),
    "V": ("Visa Inc.", "medium"),
    "JNJ": ("Johnson & Johnson", "medium"),
    "WMT": ("Walmart Inc.", "medium"),
    "PG": ("Procter & Gamble Co.", "medium"),
    "UNH": ("UnitedHealth Group Inc.", "medium"),
    "HD": ("Home Depot Inc.", "medium"),
    "CRM": ("Salesforce Inc.", "medium"),
    "COST": ("Costco Wholesale Corp.", "medium"),
    "NFLX": ("Netflix Inc.", "medium"),
    "AMD": ("Advanced Micro Devices", "medium"),
    "PYPL": ("PayPal Holdings Inc.", "low"),
    "INTC": ("Intel Corp.", "low"),
}


def _dict_to_event(e: Dict[str, Any]) -> EarningsEvent:
    """Convert a connector dict to an EarningsEvent dataclass."""
    ticker = e.get("ticker", "")
    return EarningsEvent(
        ticker=ticker,
        company_name=e.get("company_name", ticker),
        earnings_date=e.get("earnings_date", ""),
        session=e.get("session", "unknown"),
        fiscal_quarter=e.get("fiscal_quarter", ""),
        fiscal_year=e.get("fiscal_year", 0),
        eps_estimate=e.get("eps_estimate"),
        revenue_estimate=e.get("revenue_estimate"),
        eps_actual=e.get("eps_actual"),
        revenue_actual=e.get("revenue_actual"),
        surprise_percent=e.get("surprise_percent"),
        conference_call_time=None,
        importance=_get_importance_from_ticker(ticker),
        confirmed=True,
    )


# ── Service Functions ─────────────────────────────────────────────────────────


def get_upcoming_earnings(
    days_ahead: int = 7,
    tickers: Optional[List[str]] = None,
    importance: Optional[str] = None,
) -> List[EarningsEvent]:
    """Get earnings events for the next N days."""
    try:
        real_events = finnhub_get_upcoming(days_ahead=days_ahead, importance=importance)
        if not real_events:
            return []

        events = []
        for e in real_events:
            if tickers and e.get("ticker") not in [t.upper() for t in tickers]:
                continue
            events.append(_dict_to_event(e))

        events.sort(key=lambda x: x.earnings_date)
        return events
    except Exception as ex:
        log.warning("Finnhub earnings fetch failed: %s", ex)
        return []


def _get_importance_from_ticker(ticker: str) -> str:
    """Determine importance from ticker."""
    _, imp = COMPANIES.get(ticker.upper(), (ticker, "medium"))
    return imp


def get_earnings_by_date(date: str) -> List[EarningsEvent]:
    """Get all earnings events for a specific date."""
    try:
        real_events = finnhub_get_calendar(from_date=date, to_date=date)
        if not real_events:
            return []
        return [_dict_to_event(e) for e in real_events]
    except Exception as ex:
        log.warning("Finnhub earnings by date failed: %s", ex)
        return []


def get_ticker_earnings_history(
    ticker: str,
    quarters: int = 8,
) -> List[EarningsEvent]:
    """Get historical earnings for a ticker."""
    try:
        result = finnhub_get_ticker_earnings(ticker, include_historical=True)
        if not result:
            return []

        historical = result.get("historical", [])
        events = [_dict_to_event(e) for e in historical]
        events.sort(key=lambda x: x.earnings_date)
        return events[-quarters:]
    except Exception as ex:
        log.warning("Finnhub ticker earnings history failed: %s", ex)
        return []


def get_earnings_calendar_week(start_date: Optional[str] = None) -> Dict[str, List[EarningsEvent]]:
    """Get earnings calendar for a week, grouped by date."""
    try:
        week_data = finnhub_get_week(start_date=start_date)
        if not week_data:
            return {}

        calendar = {}
        for date_str, events_list in week_data.items():
            calendar[date_str] = [_dict_to_event(e) for e in events_list]
        return calendar
    except Exception as ex:
        log.warning("Finnhub earnings week failed: %s", ex)
        return {}


def get_earnings_surprises(
    min_surprise: float = 5.0,
    days_back: int = 30,
) -> List[EarningsEvent]:
    """Get recent earnings surprises above a threshold."""
    try:
        real_surprises = finnhub_get_surprises(
            min_surprise_percent=min_surprise,
            days_back=days_back,
        )
        if not real_surprises:
            return []

        events = [_dict_to_event(e) for e in real_surprises]
        events.sort(key=lambda e: abs(e.surprise_percent or 0), reverse=True)
        return events
    except Exception as ex:
        log.warning("Finnhub earnings surprises failed: %s", ex)
        return []


def search_earnings(
    query: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    importance: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """Search earnings calendar with filters."""
    try:
        from_d = start_date or (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
        to_d = end_date or (datetime.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")

        # If query looks like a ticker, pass as symbol filter
        symbol = query.upper() if query and len(query) <= 5 and query.isalpha() else None
        real_events = finnhub_get_calendar(from_date=from_d, to_date=to_d, symbol=symbol)
        if not real_events:
            return {
                "events": [],
                "total": 0,
                "filters": {"query": query, "start_date": start_date, "end_date": end_date, "importance": importance},
            }

        all_events = []
        for e in real_events:
            ticker = e.get("ticker", "")
            name = e.get("company_name", "")
            imp = _get_importance_from_ticker(ticker)

            if query and not symbol:
                if query.upper() not in ticker and query.lower() not in name.lower():
                    continue
            if importance and imp != importance:
                continue

            all_events.append(_dict_to_event(e))

        all_events.sort(key=lambda ev: ev.earnings_date)

        return {
            "events": [ev.to_dict() for ev in all_events[:limit]],
            "total": len(all_events),
            "filters": {
                "query": query,
                "start_date": start_date,
                "end_date": end_date,
                "importance": importance,
            },
        }
    except Exception as ex:
        log.warning("Finnhub search_earnings failed: %s", ex)
        return {
            "events": [],
            "total": 0,
            "filters": {"query": query, "start_date": start_date, "end_date": end_date, "importance": importance},
        }


def get_earnings_stats() -> Dict[str, Any]:
    """Get earnings calendar statistics from real data."""
    try:
        today = datetime.utcnow()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=4)
        next_week_start = week_end + timedelta(days=3)
        next_week_end = next_week_start + timedelta(days=4)

        this_week = finnhub_get_calendar(
            from_date=week_start.strftime("%Y-%m-%d"),
            to_date=week_end.strftime("%Y-%m-%d"),
        ) or []

        next_week = finnhub_get_calendar(
            from_date=next_week_start.strftime("%Y-%m-%d"),
            to_date=next_week_end.strftime("%Y-%m-%d"),
        ) or []

        today_events = finnhub_get_calendar(
            from_date=today.strftime("%Y-%m-%d"),
            to_date=today.strftime("%Y-%m-%d"),
        ) or []

        beats = [e for e in this_week if (e.get("surprise_percent") or 0) > 0]
        misses = [e for e in this_week if (e.get("surprise_percent") or 0) < 0]
        surprises = [e.get("surprise_percent", 0) for e in this_week if e.get("surprise_percent") is not None]
        avg_surprise = round(sum(surprises) / len(surprises), 1) if surprises else 0.0

        high_upcoming = [e for e in this_week if _get_importance_from_ticker(e.get("ticker", "")) == "high"]

        return {
            "this_week": len(this_week),
            "next_week": len(next_week),
            "reported_today": len([e for e in today_events if e.get("eps_actual") is not None]),
            "beats_this_week": len(beats),
            "misses_this_week": len(misses),
            "avg_surprise_percent": avg_surprise,
            "high_importance_upcoming": len(high_upcoming),
            "last_updated": today.isoformat(),
        }
    except Exception as ex:
        log.warning("Finnhub earnings stats failed: %s", ex)
        return {
            "this_week": 0,
            "next_week": 0,
            "reported_today": 0,
            "beats_this_week": 0,
            "misses_this_week": 0,
            "avg_surprise_percent": 0.0,
            "high_importance_upcoming": 0,
            "last_updated": datetime.utcnow().isoformat(),
        }
