"""
IPO Calendar API (Band C #38)
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from app.services import ipo_calendar_service

router = APIRouter(prefix="/ipo", tags=["IPO Calendar"])


@router.get("/upcoming")
def get_upcoming_ipos(
    days: int = Query(30, ge=1, le=90, description="Days to look ahead"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
):
    """Get upcoming IPOs"""
    ipos = ipo_calendar_service.get_upcoming_ipos(days=days, sector=sector)
    return {
        "upcoming": ipos,
        "count": len(ipos),
        "days_ahead": days,
        "sector_filter": sector,
    }


@router.get("/recent")
def get_recent_ipos(
    days: int = Query(30, ge=1, le=180, description="Days to look back"),
    limit: int = Query(20, ge=1, le=100),
):
    """Get recently priced IPOs"""
    ipos = ipo_calendar_service.get_recent_ipos(days=days, limit=limit)
    return {
        "recent": ipos,
        "count": len(ipos),
        "days_back": days,
    }


@router.get("/ticker/{ticker}")
def get_ipo_by_ticker(ticker: str):
    """Get IPO details by ticker"""
    ipo = ipo_calendar_service.get_ipo_by_ticker(ticker)
    if not ipo:
        raise HTTPException(status_code=404, detail=f"IPO not found for ticker {ticker}")
    return {"ipo": ipo}


@router.get("/lockups")
def get_lockup_expirations(
    days: int = Query(30, ge=1, le=180, description="Days to look ahead"),
):
    """Get upcoming lockup expirations"""
    expirations = ipo_calendar_service.get_lockup_expirations(days=days)
    return {
        "lockup_expirations": expirations,
        "count": len(expirations),
        "days_ahead": days,
    }


@router.get("/week")
def get_ipo_calendar_week():
    """Get IPO calendar for the current week"""
    calendar = ipo_calendar_service.get_ipo_calendar_week()
    return {"calendar": calendar}


@router.get("/performance")
def get_ipo_performance(
    days: int = Query(90, ge=1, le=365, description="Days since IPO"),
):
    """Get IPO performance stats"""
    performance = ipo_calendar_service.get_ipo_performance(days=days)
    return {
        "performance": performance,
        "count": len(performance),
    }


@router.get("/stats")
def get_ipo_stats():
    """Get IPO market statistics"""
    stats = ipo_calendar_service.get_ipo_stats()
    return stats


@router.get("/search")
def search_ipos(q: str = Query(..., min_length=1, description="Search query")):
    """Search IPOs by company name or ticker"""
    results = ipo_calendar_service.search_ipos(q)
    return {
        "results": results,
        "count": len(results),
        "query": q,
    }


@router.get("/sector/{sector}")
def get_ipos_by_sector(sector: str):
    """Get all IPOs in a specific sector"""
    ipos = ipo_calendar_service.get_ipos_by_sector(sector)
    return {
        "sector": sector,
        "ipos": ipos,
        "count": len(ipos),
    }
