"""
Earnings Calendar Service (Band C #36)

Provides earnings calendar data with:
- Upcoming earnings dates by ticker or date range
- Historical earnings dates
- Earnings estimate and surprise data
- Conference call schedules
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import random


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


# ── Mock Data ─────────────────────────────────────────────────────────────────

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


def _generate_mock_earnings(ticker: str, date: datetime, reported: bool = False) -> EarningsEvent:
    """Generate mock earnings data for testing."""
    company_name, importance = COMPANIES.get(ticker, (f"{ticker} Corp.", "low"))
    
    eps_estimate = round(random.uniform(0.5, 5.0), 2)
    revenue_estimate = round(random.uniform(10, 100), 2)  # In billions
    
    eps_actual = None
    revenue_actual = None
    surprise = None
    
    if reported:
        surprise_pct = random.uniform(-0.15, 0.20)
        eps_actual = round(eps_estimate * (1 + surprise_pct), 2)
        revenue_actual = round(revenue_estimate * (1 + random.uniform(-0.05, 0.10)), 2)
        surprise = round(surprise_pct * 100, 1)
    
    quarter = ((date.month - 1) // 3) + 1
    
    return EarningsEvent(
        ticker=ticker,
        company_name=company_name,
        earnings_date=date.strftime("%Y-%m-%d"),
        session=random.choice(["pre_market", "after_hours"]),
        fiscal_quarter=f"Q{quarter}",
        fiscal_year=date.year,
        eps_estimate=eps_estimate,
        revenue_estimate=revenue_estimate,
        eps_actual=eps_actual,
        revenue_actual=revenue_actual,
        surprise_percent=surprise,
        conference_call_time=f"{random.randint(8, 17):02d}:00 ET",
        importance=importance,
        confirmed=random.random() > 0.2,
    )


# ── Service Functions ─────────────────────────────────────────────────────────


def get_upcoming_earnings(
    days_ahead: int = 7,
    tickers: Optional[List[str]] = None,
    importance: Optional[str] = None,
) -> List[EarningsEvent]:
    """Get earnings events for the next N days."""
    today = datetime.utcnow().date()
    events = []
    
    target_tickers = tickers if tickers else list(COMPANIES.keys())
    
    for ticker in target_tickers:
        # Random date in the range
        days_offset = random.randint(0, days_ahead)
        event_date = today + timedelta(days=days_offset)
        event = _generate_mock_earnings(ticker, datetime.combine(event_date, datetime.min.time()))
        
        if importance and event.importance != importance:
            continue
            
        events.append(event)
    
    # Sort by date
    events.sort(key=lambda e: e.earnings_date)
    return events


def get_earnings_by_date(date: str) -> List[EarningsEvent]:
    """Get all earnings events for a specific date."""
    target_date = datetime.strptime(date, "%Y-%m-%d")
    events = []
    
    # Generate 3-8 random earnings for the date
    sample_tickers = random.sample(list(COMPANIES.keys()), random.randint(3, 8))
    
    for ticker in sample_tickers:
        events.append(_generate_mock_earnings(ticker, target_date))
    
    return events


def get_ticker_earnings_history(
    ticker: str,
    quarters: int = 8,
) -> List[EarningsEvent]:
    """Get historical earnings for a ticker."""
    events = []
    today = datetime.utcnow()
    
    for i in range(quarters):
        # Go back i quarters
        quarter_date = today - timedelta(days=90 * (i + 1))
        event = _generate_mock_earnings(ticker, quarter_date, reported=True)
        events.append(event)
    
    events.reverse()  # Oldest first
    return events


def get_earnings_calendar_week(start_date: Optional[str] = None) -> Dict[str, List[EarningsEvent]]:
    """Get earnings calendar for a week, grouped by date."""
    if start_date:
        week_start = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        week_start = datetime.utcnow()
        # Adjust to Monday
        week_start = week_start - timedelta(days=week_start.weekday())
    
    calendar = {}
    
    for day_offset in range(5):  # Mon-Fri
        day = week_start + timedelta(days=day_offset)
        date_str = day.strftime("%Y-%m-%d")
        events = get_earnings_by_date(date_str)
        calendar[date_str] = events
    
    return calendar


def get_earnings_surprises(
    min_surprise: float = 5.0,
    days_back: int = 30,
) -> List[EarningsEvent]:
    """Get recent earnings surprises above a threshold."""
    events = []
    today = datetime.utcnow()
    
    for ticker in COMPANIES.keys():
        days_ago = random.randint(1, days_back)
        event_date = today - timedelta(days=days_ago)
        event = _generate_mock_earnings(ticker, event_date, reported=True)
        
        if event.surprise_percent and abs(event.surprise_percent) >= min_surprise:
            events.append(event)
    
    # Sort by surprise magnitude (descending)
    events.sort(key=lambda e: abs(e.surprise_percent or 0), reverse=True)
    return events


def search_earnings(
    query: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    importance: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    """Search earnings calendar with filters."""
    all_events = []
    
    start = datetime.strptime(start_date, "%Y-%m-%d") if start_date else datetime.utcnow() - timedelta(days=30)
    end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.utcnow() + timedelta(days=30)
    
    for ticker, (name, imp) in COMPANIES.items():
        if query and query.upper() not in ticker and query.lower() not in name.lower():
            continue
        if importance and imp != importance:
            continue
        
        # Generate a random event in the date range
        days_range = (end - start).days
        if days_range > 0:
            event_date = start + timedelta(days=random.randint(0, days_range))
            reported = event_date < datetime.utcnow()
            all_events.append(_generate_mock_earnings(ticker, event_date, reported))
    
    all_events.sort(key=lambda e: e.earnings_date)
    
    return {
        "events": [e.to_dict() for e in all_events[:limit]],
        "total": len(all_events),
        "filters": {
            "query": query,
            "start_date": start_date,
            "end_date": end_date,
            "importance": importance,
        },
    }


def get_earnings_stats() -> Dict[str, Any]:
    """Get earnings calendar statistics."""
    today = datetime.utcnow()
    
    return {
        "this_week": random.randint(80, 150),
        "next_week": random.randint(50, 100),
        "reported_today": random.randint(5, 20),
        "beats_this_week": random.randint(60, 80),
        "misses_this_week": random.randint(10, 30),
        "avg_surprise_percent": round(random.uniform(2, 8), 1),
        "high_importance_upcoming": random.randint(10, 25),
        "last_updated": today.isoformat(),
    }
