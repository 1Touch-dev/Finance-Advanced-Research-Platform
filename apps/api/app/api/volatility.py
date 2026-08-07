"""
Implied Volatility Surface API (Band B #27)

Endpoints:
- GET /volatility/surface/{ticker} - Get IV surface
- GET /volatility/snapshot/{ticker} - Get IV snapshot
- GET /volatility/history/{ticker} - Get IV history
- GET /volatility/skew/{ticker} - Get skew analysis
- GET /volatility/screen - Screen by IV criteria
"""

from fastapi import APIRouter, Query
from typing import List, Optional

from app.services.volatility_service import get_volatility_service

router = APIRouter(prefix="/volatility", tags=["volatility"])


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/surface/{ticker}")
async def get_volatility_surface(ticker: str):
    """
    Get full implied volatility surface for a ticker.

    Returns IV data across strikes and expirations, term structure,
    and skew metrics. Data is delayed EOD (no OPRA license required).
    """
    service = get_volatility_service()
    surface = service.get_volatility_surface(ticker.upper())
    return surface.to_dict()


@router.get("/snapshot/{ticker}")
async def get_volatility_snapshot(ticker: str):
    """
    Get quick IV snapshot for a ticker.

    Returns key metrics: IV by term, IV rank/percentile,
    HV comparison, and put-call skew.
    """
    service = get_volatility_service()
    snapshot = service.get_volatility_snapshot(ticker.upper())
    return snapshot.to_dict()


@router.get("/history/{ticker}")
async def get_volatility_history(
    ticker: str,
    days: int = Query(252, ge=30, le=756)
):
    """
    Get historical IV data for a ticker.

    Returns daily IV readings, 52-week high/low, and current IV rank.
    """
    service = get_volatility_service()
    history = service.get_volatility_history(ticker.upper(), days=days)
    return history.to_dict()


@router.get("/skew/{ticker}")
async def get_skew_analysis(
    ticker: str,
    expiry: Optional[str] = None
):
    """
    Get detailed skew analysis for a ticker.

    Returns 25-delta and 10-delta skew, IV by strike,
    skew percentile vs history, and interpretation.
    """
    service = get_volatility_service()
    skew = service.get_skew_analysis(ticker.upper(), expiry=expiry)
    return skew.to_dict()


@router.get("/screen")
async def screen_volatility(
    min_iv_rank: float = Query(0, ge=0, le=100),
    max_iv_rank: float = Query(100, ge=0, le=100),
    min_iv_hv_spread: float = Query(-1, ge=-2, le=2),
    tickers: Optional[str] = None
):
    """
    Screen stocks by volatility criteria.

    Filter by IV rank, IV-HV spread, etc.
    """
    service = get_volatility_service()

    ticker_list = None
    if tickers:
        ticker_list = [t.strip().upper() for t in tickers.split(',')]

    results = service.screen_volatility(
        min_iv_rank=min_iv_rank,
        max_iv_rank=max_iv_rank,
        min_iv_hv_spread=min_iv_hv_spread,
        tickers=ticker_list,
    )

    return {
        "results": results,
        "count": len(results),
        "filters": {
            "min_iv_rank": min_iv_rank,
            "max_iv_rank": max_iv_rank,
            "min_iv_hv_spread": min_iv_hv_spread,
        },
        "data_note": "Delayed EOD data - typically 15-20 minutes"
    }


@router.get("/term-structure/{ticker}")
async def get_term_structure(ticker: str):
    """
    Get ATM implied volatility term structure.

    Shows IV curve across expirations for contango/backwardation analysis.
    """
    service = get_volatility_service()
    surface = service.get_volatility_surface(ticker.upper())

    return {
        "ticker": ticker.upper(),
        "underlying_price": surface.underlying_price,
        "term_structure": surface.term_structure,
        "as_of_date": surface.as_of_date,
        "data_delay_minutes": surface.data_delay_minutes,
    }
