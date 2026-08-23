"""
Short Interest API (Band C #40)
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from app.services.short_interest_service import (
    get_short_interest,
    get_short_interest_history,
    get_most_shorted,
    get_short_squeeze_candidates,
    get_short_changes,
    get_sector_short_summary,
    get_short_stats,
)

router = APIRouter(prefix="/short-interest", tags=["short-interest"])


@router.get("/ticker/{ticker}")
def ticker_short_interest(
    ticker: str,
):
    """Get current short interest for a ticker."""
    data = get_short_interest(ticker.upper())
    if not data:
        raise HTTPException(status_code=404, detail="Ticker not found")
    return {"data": data.to_dict()}


@router.get("/ticker/{ticker}/history")
def ticker_short_history(
    ticker: str,
    periods: int = Query(12, ge=1, le=24, description="Number of bi-weekly periods"),
):
    """Get short interest history for a ticker."""
    history = get_short_interest_history(ticker.upper(), periods)
    return {
        "ticker": ticker.upper(),
        "history": history,
        "periods": len(history),
    }


@router.get("/most-shorted")
def most_shorted(
    min_short_percent: float = Query(10.0, ge=0, description="Minimum short % of float"),
    limit: int = Query(20, ge=1, le=100),
):
    """Get most heavily shorted stocks."""
    stocks = get_most_shorted(min_short_percent, limit)
    return {
        "stocks": [s.to_dict() for s in stocks],
        "count": len(stocks),
        "min_threshold": min_short_percent,
    }


@router.get("/squeeze-candidates")
def squeeze_candidates(
    min_score: float = Query(50.0, ge=0, le=100, description="Minimum squeeze score"),
    limit: int = Query(20, ge=1, le=100),
):
    """Get potential short squeeze candidates."""
    candidates = get_short_squeeze_candidates(min_score, limit)
    return {
        "candidates": [c.to_dict() for c in candidates],
        "count": len(candidates),
        "min_squeeze_score": min_score,
    }


@router.get("/changes")
def short_changes(
    min_change: float = Query(10.0, ge=0, description="Minimum change %"),
    direction: str = Query("both", description="up, down, or both"),
    limit: int = Query(20, ge=1, le=100),
):
    """Get stocks with significant short interest changes."""
    if direction not in ("up", "down", "both"):
        raise HTTPException(status_code=400, detail="Direction must be up, down, or both")
    
    changes = get_short_changes(min_change, direction, limit)
    return {
        "stocks": [s.to_dict() for s in changes],
        "count": len(changes),
        "direction_filter": direction,
    }


@router.get("/sectors")
def sector_summary():
    """Get short interest summary by sector."""
    summary = get_sector_short_summary()
    return {
        "sectors": summary,
        "count": len(summary),
    }


@router.get("/stats")
def short_stats():
    """Get overall short interest statistics."""
    return get_short_stats()


@router.get("/compare")
def compare_tickers(
    tickers: str = Query(..., description="Comma-separated tickers"),
):
    """Compare short interest across multiple tickers."""
    ticker_list = [t.strip().upper() for t in tickers.split(",")]
    
    comparison = []
    for ticker in ticker_list[:10]:  # Limit to 10
        data = get_short_interest(ticker)
        if data:
            comparison.append(data.to_dict())
    
    return {
        "comparison": comparison,
        "count": len(comparison),
    }
