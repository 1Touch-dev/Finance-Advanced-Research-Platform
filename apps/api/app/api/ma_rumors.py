"""
M&A Rumor Tracking API (Band C #39)
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from app.services import ma_rumor_service

router = APIRouter(prefix="/ma-rumors", tags=["M&A Rumors"])


@router.get("/active")
def get_active_rumors(
    days: int = Query(30, ge=1, le=180, description="Days to look back"),
    status: Optional[str] = Query(None, description="Filter by status: rumor, confirmed, denied"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    min_probability: float = Query(0.0, ge=0, le=100, description="Minimum probability score"),
):
    """Get active M&A rumors"""
    rumors = ma_rumor_service.get_active_rumors(
        days=days,
        status=status,
        sector=sector,
        min_probability=min_probability,
    )
    return {
        "rumors": rumors,
        "count": len(rumors),
        "filters": {
            "days": days,
            "status": status,
            "sector": sector,
            "min_probability": min_probability,
        },
    }


@router.get("/rumor/{rumor_id}")
def get_rumor_by_id(rumor_id: str):
    """Get rumor details by ID"""
    rumor = ma_rumor_service.get_rumor_by_id(rumor_id)
    if not rumor:
        raise HTTPException(status_code=404, detail=f"Rumor not found: {rumor_id}")
    return {"rumor": rumor}


@router.get("/ticker/{ticker}")
def get_rumors_by_ticker(ticker: str):
    """Get all rumors involving a ticker (as target or acquirer)"""
    rumors = ma_rumor_service.get_rumors_by_ticker(ticker)
    return {
        "ticker": ticker.upper(),
        "rumors": rumors,
        "count": len(rumors),
    }


@router.get("/high-probability")
def get_high_probability_rumors(
    min_score: float = Query(40.0, ge=0, le=100, description="Minimum probability score"),
):
    """Get rumors with high probability scores"""
    rumors = ma_rumor_service.get_high_probability_rumors(min_score=min_score)
    return {
        "rumors": rumors,
        "count": len(rumors),
        "min_probability": min_score,
    }


@router.get("/confirmed")
def get_confirmed_deals():
    """Get confirmed M&A deals"""
    deals = ma_rumor_service.get_confirmed_deals()
    return {
        "deals": deals,
        "count": len(deals),
    }


@router.get("/by-type/{deal_type}")
def get_rumors_by_deal_type(deal_type: str):
    """Get rumors by deal type (acquisition, merger, hostile_takeover, spinoff, divestiture)"""
    valid_types = ["acquisition", "merger", "hostile_takeover", "spinoff", "divestiture"]
    if deal_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid deal type. Must be one of: {', '.join(valid_types)}",
        )
    rumors = ma_rumor_service.get_rumors_by_deal_type(deal_type)
    return {
        "deal_type": deal_type,
        "rumors": rumors,
        "count": len(rumors),
    }


@router.get("/largest")
def get_largest_deals(
    limit: int = Query(10, ge=1, le=50, description="Number of deals to return"),
):
    """Get largest rumored deals by value"""
    deals = ma_rumor_service.get_largest_deals(limit=limit)
    return {
        "deals": deals,
        "count": len(deals),
    }


@router.get("/stats")
def get_ma_stats():
    """Get M&A market statistics"""
    stats = ma_rumor_service.get_ma_stats()
    return stats


@router.get("/search")
def search_rumors(q: str = Query(..., min_length=1, description="Search query")):
    """Search rumors by company name, ticker, or headline"""
    results = ma_rumor_service.search_rumors(q)
    return {
        "results": results,
        "count": len(results),
        "query": q,
    }


@router.get("/updates")
def get_recent_updates(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
):
    """Get rumors with recent updates"""
    updates = ma_rumor_service.get_recent_updates(hours=hours)
    return {
        "updates": updates,
        "count": len(updates),
        "hours_back": hours,
    }
