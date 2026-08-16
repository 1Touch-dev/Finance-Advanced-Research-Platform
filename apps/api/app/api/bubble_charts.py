"""
Interactive Bubble Charts API (James J5)
"""

from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter(prefix="/bubble-charts", tags=["Bubble Charts"])

try:
    from ..services.bubble_chart_service import (
        get_bubble_chart,
        get_bubble_presets,
        get_animated_bubble_data,
        get_sector_bubble_chart,
        get_comparison_bubble_chart,
        get_bubble_metrics,
        get_portfolio_bubble_chart,
    )
    SERVICE_AVAILABLE = True
except ImportError:
    SERVICE_AVAILABLE = False


@router.get("/")
def api_get_bubble_chart(
    x_metric: str = Query(default="market_cap"),
    y_metric: str = Query(default="pe_ratio"),
    size_metric: str = Query(default="revenue"),
    color_by: str = Query(default="sector"),
    tickers: Optional[str] = None,
):
    """Get bubble chart with configurable metrics"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    ticker_list = [t.strip() for t in tickers.split(",")] if tickers else None
    return get_bubble_chart(x_metric, y_metric, size_metric, color_by, ticker_list)


@router.get("/presets")
def api_get_presets():
    """Get preset bubble chart configurations"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return {"presets": get_bubble_presets()}


@router.get("/animated/{ticker}")
def api_get_animated(
    ticker: str,
    periods: int = Query(default=12),
    interval: str = Query(default="quarterly"),
):
    """Get animated bubble chart data over time"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_animated_bubble_data(ticker, periods, interval)


@router.get("/sectors")
def api_get_sector_bubbles(
    sector: Optional[str] = None,
):
    """Get bubble chart grouped by sector"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_sector_bubble_chart(sector)


@router.get("/compare")
def api_compare_bubbles(
    ticker1: str,
    ticker2: str,
    periods: int = Query(default=8),
):
    """Compare two tickers over time"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_comparison_bubble_chart(ticker1, ticker2, periods)


@router.get("/metrics")
def api_get_metrics():
    """Get available metrics for bubble charts"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return {"metrics": get_bubble_metrics()}


@router.get("/portfolio")
def api_get_portfolio_bubbles(
    user_id: str = Query(default="demo_user"),
):
    """Get bubble chart for user's portfolio"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_portfolio_bubble_chart(user_id)
