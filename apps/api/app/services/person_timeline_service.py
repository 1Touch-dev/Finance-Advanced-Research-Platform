"""
Person Timeline Service (James J1)
Person events + stock price + news overlay
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import random


@dataclass
class TimelineEvent:
    """An event on a person's timeline"""
    event_id: str
    event_type: str  # appointment, departure, trade, filing, news, company_event
    date: str
    title: str
    description: str
    ticker: Optional[str] = None
    value: Optional[float] = None
    source: Optional[str] = None
    url: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "date": self.date,
            "title": self.title,
            "description": self.description,
            "ticker": self.ticker,
            "value": self.value,
            "source": self.source,
            "url": self.url,
        }


@dataclass
class StockPrice:
    """Stock price data point"""
    date: str
    ticker: str
    open: float
    high: float
    low: float
    close: float
    volume: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date,
            "ticker": self.ticker,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
        }


# Mock person data
MOCK_PERSONS = {
    "jensen_huang": {
        "person_id": "jensen_huang",
        "name": "Jensen Huang",
        "title": "CEO",
        "company": "NVIDIA Corp",
        "ticker": "NVDA",
        "image_url": None,
    },
    "elon_musk": {
        "person_id": "elon_musk",
        "name": "Elon Musk",
        "title": "CEO",
        "company": "Tesla Inc",
        "ticker": "TSLA",
        "image_url": None,
    },
    "satya_nadella": {
        "person_id": "satya_nadella",
        "name": "Satya Nadella",
        "title": "CEO",
        "company": "Microsoft Corp",
        "ticker": "MSFT",
        "image_url": None,
    },
    "tim_cook": {
        "person_id": "tim_cook",
        "name": "Tim Cook",
        "title": "CEO",
        "company": "Apple Inc",
        "ticker": "AAPL",
        "image_url": None,
    },
}

# Mock events
MOCK_EVENTS = {
    "jensen_huang": [
        TimelineEvent("E001", "appointment", "2024-06-15", "Re-elected Chairman", "Jensen Huang re-elected as Chairman of the Board at annual meeting", "NVDA"),
        TimelineEvent("E002", "trade", "2024-05-20", "Stock Sale", "Sold 100,000 shares at $115.50", "NVDA", 11550000, "Form 4"),
        TimelineEvent("E003", "company_event", "2024-05-22", "GTC Keynote", "Delivered keynote at GPU Technology Conference announcing Blackwell architecture", "NVDA"),
        TimelineEvent("E004", "news", "2024-04-10", "AI Leadership Recognition", "Named one of TIME's most influential people in AI", "NVDA", None, "TIME"),
        TimelineEvent("E005", "filing", "2024-03-15", "10-K Filing", "Annual report filed with SEC", "NVDA", None, "SEC"),
        TimelineEvent("E006", "trade", "2024-02-28", "Option Exercise", "Exercised options for 50,000 shares", "NVDA", 4500000, "Form 4"),
        TimelineEvent("E007", "company_event", "2024-02-21", "Earnings Call", "Q4 2024 earnings call - record revenue announced", "NVDA"),
        TimelineEvent("E008", "news", "2024-01-08", "CES Keynote", "Announced new gaming GPUs and AI partnerships at CES", "NVDA", None, "Various"),
    ],
    "elon_musk": [
        TimelineEvent("E101", "trade", "2024-07-15", "Stock Sale", "Sold 5 million shares at $250", "TSLA", 1250000000, "Form 4"),
        TimelineEvent("E102", "company_event", "2024-06-13", "Shareholder Vote", "Compensation package approved by shareholders", "TSLA"),
        TimelineEvent("E103", "news", "2024-05-20", "xAI Funding", "Raised $6B for xAI startup", None, 6000000000, "Bloomberg"),
        TimelineEvent("E104", "filing", "2024-04-23", "10-Q Filing", "Quarterly report filed", "TSLA", None, "SEC"),
        TimelineEvent("E105", "news", "2024-03-15", "Cybertruck Delivery", "First mass Cybertruck deliveries announced", "TSLA", None, "Reuters"),
    ],
}


def search_persons(query: str) -> List[Dict[str, Any]]:
    """Search for persons by name"""
    query = query.lower()
    results = []
    for person_id, person in MOCK_PERSONS.items():
        if query in person["name"].lower() or query in person.get("company", "").lower():
            results.append(person)
    return results


def get_person(person_id: str) -> Optional[Dict[str, Any]]:
    """Get person details"""
    return MOCK_PERSONS.get(person_id)


def get_person_timeline(
    person_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    event_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Get timeline for a person"""
    person = MOCK_PERSONS.get(person_id)
    if not person:
        return {"error": "Person not found"}

    events = MOCK_EVENTS.get(person_id, [])

    # Filter by date range
    if start_date:
        events = [e for e in events if e.date >= start_date]
    if end_date:
        events = [e for e in events if e.date <= end_date]

    # Filter by event type
    if event_types:
        events = [e for e in events if e.event_type in event_types]

    # Sort by date
    events = sorted(events, key=lambda e: e.date, reverse=True)

    return {
        "person": person,
        "events": [e.to_dict() for e in events],
        "event_count": len(events),
    }


def get_timeline_with_prices(
    person_id: str,
    days: int = 365,
) -> Dict[str, Any]:
    """Get timeline with stock price overlay"""
    person = MOCK_PERSONS.get(person_id)
    if not person:
        return {"error": "Person not found"}

    ticker = person.get("ticker")
    if not ticker:
        return {"error": "No associated ticker"}

    events = MOCK_EVENTS.get(person_id, [])

    # Generate mock price data
    prices = []
    base_price = 100.0
    base_date = datetime.now() - timedelta(days=days)

    for i in range(days):
        date = base_date + timedelta(days=i)
        # Add some randomness and trend
        change = random.uniform(-3, 3.5)
        base_price = max(50, base_price + change)

        prices.append({
            "date": date.strftime("%Y-%m-%d"),
            "close": round(base_price, 2),
            "volume": random.randint(10000000, 50000000),
        })

    # Mark events on price chart
    event_dates = {e.date: e.to_dict() for e in events}

    return {
        "person": person,
        "ticker": ticker,
        "prices": prices,
        "events": [e.to_dict() for e in events],
        "event_dates": list(event_dates.keys()),
    }


def get_person_news(
    person_id: str,
    limit: int = 20,
) -> Dict[str, Any]:
    """Get news articles about a person"""
    person = MOCK_PERSONS.get(person_id)
    if not person:
        return {"error": "Person not found"}

    # Mock news articles
    news = [
        {
            "headline": f"{person['name']} Discusses AI Future at Conference",
            "source": "Bloomberg",
            "date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
            "sentiment": "positive",
        },
        {
            "headline": f"{person['company']} Stock Rises on {person['name']} Comments",
            "source": "Reuters",
            "date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
            "sentiment": "positive",
        },
        {
            "headline": f"Analysts React to {person['name']}'s Strategy Update",
            "source": "CNBC",
            "date": (datetime.now() - timedelta(days=8)).strftime("%Y-%m-%d"),
            "sentiment": "neutral",
        },
        {
            "headline": f"{person['name']} on {person['company']}'s Growth Plans",
            "source": "WSJ",
            "date": (datetime.now() - timedelta(days=12)).strftime("%Y-%m-%d"),
            "sentiment": "positive",
        },
    ]

    return {
        "person": person,
        "news": news[:limit],
        "total": len(news),
    }


def get_person_trades(
    person_id: str,
    days: int = 365,
) -> Dict[str, Any]:
    """Get insider trades by person"""
    person = MOCK_PERSONS.get(person_id)
    if not person:
        return {"error": "Person not found"}

    events = MOCK_EVENTS.get(person_id, [])
    trades = [e.to_dict() for e in events if e.event_type == "trade"]

    total_value = sum(e.value or 0 for e in events if e.event_type == "trade")

    return {
        "person": person,
        "trades": trades,
        "trade_count": len(trades),
        "total_value": total_value,
    }


def get_person_filings(person_id: str) -> Dict[str, Any]:
    """Get SEC filings involving person"""
    person = MOCK_PERSONS.get(person_id)
    if not person:
        return {"error": "Person not found"}

    events = MOCK_EVENTS.get(person_id, [])
    filings = [e.to_dict() for e in events if e.event_type == "filing"]

    return {
        "person": person,
        "filings": filings,
        "filing_count": len(filings),
    }


def compare_persons(person_ids: List[str]) -> Dict[str, Any]:
    """Compare timelines of multiple persons"""
    comparisons = []

    for person_id in person_ids[:5]:  # Limit to 5
        person = MOCK_PERSONS.get(person_id)
        if person:
            events = MOCK_EVENTS.get(person_id, [])
            comparisons.append({
                "person": person,
                "event_count": len(events),
                "trade_count": len([e for e in events if e.event_type == "trade"]),
                "latest_event": events[0].to_dict() if events else None,
            })

    return {
        "comparisons": comparisons,
        "count": len(comparisons),
    }
