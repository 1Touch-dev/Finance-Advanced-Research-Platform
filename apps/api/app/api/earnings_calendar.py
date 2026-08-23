"""
Earnings Calendar API (Band C #36)
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List

from app.services.earnings_calendar_service import (
    get_upcoming_earnings,
    get_earnings_by_date,
    get_ticker_earnings_history,
    get_earnings_calendar_week,
    get_earnings_surprises,
    search_earnings,
    get_earnings_stats,
)

router = APIRouter(prefix="/earnings", tags=["earnings-calendar"])


@router.get("/upcoming")
def upcoming_earnings(
    days: int = Query(7, ge=1, le=30, description="Days ahead to look"),
    tickers: Optional[str] = Query(None, description="Comma-separated tickers"),
    importance: Optional[str] = Query(None, description="Filter by importance: high, medium, low"),
):
    """Get upcoming earnings events."""
    ticker_list = [t.strip().upper() for t in tickers.split(",")] if tickers else None
    events = get_upcoming_earnings(days, ticker_list, importance)
    return {
        "events": [e.to_dict() for e in events],
        "count": len(events),
        "days_ahead": days,
    }


@router.get("/date/{date}")
def earnings_by_date(
    date: str,
):
    """Get all earnings for a specific date (YYYY-MM-DD)."""
    try:
        events = get_earnings_by_date(date)
        return {
            "date": date,
            "events": [e.to_dict() for e in events],
            "count": len(events),
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")


@router.get("/ticker/{ticker}")
def ticker_earnings(
    ticker: str,
    quarters: int = Query(8, ge=1, le=20, description="Number of quarters"),
):
    """Get earnings history for a ticker."""
    events = get_ticker_earnings_history(ticker.upper(), quarters)
    return {
        "ticker": ticker.upper(),
        "history": [e.to_dict() for e in events],
        "quarters": len(events),
    }


@router.get("/week")
def earnings_week(
    start_date: Optional[str] = Query(None, description="Week start date (YYYY-MM-DD)"),
):
    """Get earnings calendar for a week."""
    calendar = get_earnings_calendar_week(start_date)
    return {
        "calendar": {
            date: [e.to_dict() for e in events]
            for date, events in calendar.items()
        },
        "total_events": sum(len(events) for events in calendar.values()),
    }


@router.get("/surprises")
def earnings_surprises(
    min_surprise: float = Query(5.0, description="Minimum surprise % (absolute)"),
    days_back: int = Query(30, ge=1, le=90, description="Days to look back"),
):
    """Get recent earnings surprises."""
    events = get_earnings_surprises(min_surprise, days_back)
    return {
        "surprises": [e.to_dict() for e in events],
        "count": len(events),
        "min_surprise_threshold": min_surprise,
    }


@router.get("/search")
def search_earnings_calendar(
    query: Optional[str] = Query(None, description="Search query (ticker or company)"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    importance: Optional[str] = Query(None, description="Filter by importance"),
    limit: int = Query(50, ge=1, le=200),
):
    """Search earnings calendar."""
    return search_earnings(query, start_date, end_date, importance, limit)


@router.get("/stats")
def earnings_stats():
    """Get earnings calendar statistics."""
    return get_earnings_stats()
