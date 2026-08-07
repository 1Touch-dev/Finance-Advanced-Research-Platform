"""
Volume Screening API Routes (Band B #28)
────────────────────────────────────────────────────────────────────────────
Provides endpoints for:
  - Unusual volume screening
  - Volume history and profiles
  - Sector volume flow analysis
  - Volume-price pattern detection

Note: Uses delayed EOD data. Honest delayed > wrong live.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List

from app.services.volume_screening_service import (
    get_volume_bar,
    get_volume_history,
    screen_unusual_volume,
    get_ticker_volume_profile,
    get_sector_volume_flow,
    volume_bar_to_dict,
    alert_to_dict,
    screen_to_dict,
    profile_to_dict,
    sector_flow_to_dict,
)

router = APIRouter(prefix="/volume")


@router.get("/screen")
def screen_volume(
    min_ratio: float = Query(2.0, description="Minimum volume ratio threshold"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    tickers: Optional[str] = Query(None, description="Comma-separated tickers"),
):
    """
    Screen for unusual volume across the market.

    Returns tickers with volume significantly above average.
    Uses delayed EOD data for accuracy.
    """
    ticker_list = None
    if tickers:
        ticker_list = [t.strip() for t in tickers.split(",")]

    try:
        screen = screen_unusual_volume(
            min_ratio=min_ratio,
            tickers=ticker_list,
            sector=sector,
        )
        return screen_to_dict(screen)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Screening error: {str(e)}")


@router.get("/profile/{ticker}")
def get_volume_profile(ticker: str):
    """
    Get comprehensive volume profile for a ticker.

    Includes averages, spike history, and trend analysis.
    """
    try:
        profile = get_ticker_volume_profile(ticker)
        return profile_to_dict(profile)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Profile error: {str(e)}")


@router.get("/history/{ticker}")
def get_ticker_volume_history(
    ticker: str,
    days: int = Query(30, description="Number of trading days"),
):
    """
    Get historical volume data for a ticker.

    Returns daily volume bars with price context.
    """
    try:
        bars = get_volume_history(ticker, days=days)
        return {
            "ticker": ticker.upper(),
            "days": days,
            "bars": [volume_bar_to_dict(b) for b in bars],
            "count": len(bars),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"History error: {str(e)}")


@router.get("/latest/{ticker}")
def get_latest_volume(ticker: str):
    """
    Get latest volume data for a ticker.
    """
    try:
        bar = get_volume_bar(ticker)
        return volume_bar_to_dict(bar)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/sector/{sector}")
def get_sector_flow(sector: str):
    """
    Get sector-level volume flow analysis.

    Shows aggregate volume and flow direction.
    """
    try:
        flow = get_sector_volume_flow(sector)
        return sector_flow_to_dict(flow)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sector flow error: {str(e)}")


@router.get("/alerts")
def get_volume_alerts(
    min_ratio: float = Query(2.5, description="Minimum ratio for alert"),
    limit: int = Query(10, description="Maximum alerts"),
):
    """
    Get current volume alerts across the market.

    Higher threshold than full screen for significant moves only.
    """
    try:
        screen = screen_unusual_volume(min_ratio=min_ratio)
        alerts = screen.alerts[:limit]

        return {
            "alert_count": len(alerts),
            "threshold": min_ratio,
            "alerts": [alert_to_dict(a) for a in alerts],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Alert error: {str(e)}")


@router.get("/compare")
def compare_volume(
    tickers: str = Query(..., description="Comma-separated tickers"),
):
    """
    Compare volume profiles across multiple tickers.
    """
    ticker_list = [t.strip().upper() for t in tickers.split(",")]

    if len(ticker_list) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 tickers")

    results = []
    for ticker in ticker_list:
        try:
            profile = get_ticker_volume_profile(ticker)
            results.append({
                "ticker": ticker,
                "company_name": profile.company_name,
                "avg_volume_20d": profile.avg_volume_20d,
                "latest_ratio": profile.latest_ratio,
                "latest_signal": profile.latest_signal.value,
                "spikes_30d": profile.spikes_30d,
                "volume_trend": profile.volume_trend,
            })
        except Exception:
            results.append({
                "ticker": ticker,
                "error": "Failed to fetch profile",
            })

    return {
        "comparison": results,
        "most_active": max(results, key=lambda x: x.get("latest_ratio", 0))["ticker"] if results else None,
    }
