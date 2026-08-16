"""
Valuation Timeline API (James J3)
"""

from fastapi import APIRouter, Query
from typing import Optional, List

router = APIRouter(prefix="/valuation", tags=["Valuation"])

try:
    from ..services.valuation_timeline_service import (
        get_valuation_timeline,
        compare_valuations,
        get_valuation_bands,
        get_valuation_zscore,
        get_sector_valuations,
        get_valuation_events,
    )
    SERVICE_AVAILABLE = True
except ImportError:
    SERVICE_AVAILABLE = False


@router.get("/timeline/{ticker}")
def api_get_timeline(
    ticker: str,
    periods: int = Query(default=20),
    interval: str = Query(default="quarterly"),
):
    """Get valuation timeline for a ticker"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_valuation_timeline(ticker, periods, interval)


@router.get("/compare")
def api_compare_valuations(
    tickers: str = Query(description="Comma-separated tickers"),
):
    """Compare valuations across tickers"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    ticker_list = [t.strip().upper() for t in tickers.split(",")]
    return compare_valuations(ticker_list)


@router.get("/bands/{ticker}")
def api_get_bands(
    ticker: str,
    periods: int = Query(default=20),
):
    """Get valuation bands for a ticker"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_valuation_bands(ticker, periods)


@router.get("/zscore/{ticker}")
def api_get_zscore(ticker: str):
    """Get valuation z-score"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_valuation_zscore(ticker)


@router.get("/sector/{sector}")
def api_get_sector_valuations(sector: str):
    """Get valuations for a sector"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_sector_valuations(sector)


@router.get("/events/{ticker}")
def api_get_events(
    ticker: str,
    threshold: float = Query(default=1.5),
):
    """Get notable valuation events"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return {"events": get_valuation_events(ticker, threshold)}
