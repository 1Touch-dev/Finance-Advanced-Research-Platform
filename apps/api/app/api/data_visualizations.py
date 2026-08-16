"""
Data Visualizations API (James J2)
"""

from fastapi import APIRouter, Query
from typing import Optional, List

router = APIRouter(prefix="/visualizations", tags=["Visualizations"])

try:
    from ..services.data_visualization_service import (
        get_sector_breakdown,
        get_performance_comparison,
        get_time_series,
        get_correlation_matrix,
        get_treemap_data,
        get_scatter_plot,
        get_candlestick_data,
        get_area_chart,
        get_radar_chart,
        get_histogram,
        get_gauge_chart,
        get_waterfall_chart,
    )
    SERVICE_AVAILABLE = True
except ImportError:
    SERVICE_AVAILABLE = False


@router.get("/sector-breakdown")
def api_get_sector_breakdown(
    tickers: Optional[str] = None,
):
    """Get sector breakdown pie chart data"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    ticker_list = [t.strip() for t in tickers.split(",")] if tickers else None
    return get_sector_breakdown(ticker_list)


@router.get("/performance-comparison")
def api_get_performance(
    tickers: str = Query(description="Comma-separated tickers"),
    period: str = Query(default="1Y"),
):
    """Get performance comparison bar chart"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    ticker_list = [t.strip() for t in tickers.split(",")]
    return get_performance_comparison(ticker_list, period)


@router.get("/time-series/{ticker}")
def api_get_time_series(
    ticker: str,
    period: str = Query(default="1Y"),
    interval: str = Query(default="daily"),
):
    """Get time series line chart data"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_time_series(ticker, period, interval)


@router.get("/correlation")
def api_get_correlation(
    tickers: str = Query(description="Comma-separated tickers"),
):
    """Get correlation matrix heatmap"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    ticker_list = [t.strip() for t in tickers.split(",")]
    return get_correlation_matrix(ticker_list)


@router.get("/treemap")
def api_get_treemap(
    group_by: str = Query(default="sector"),
):
    """Get treemap data"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_treemap_data(group_by)


@router.get("/scatter")
def api_get_scatter(
    x_metric: str = Query(default="market_cap"),
    y_metric: str = Query(default="pe_ratio"),
    tickers: Optional[str] = None,
):
    """Get scatter plot data"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    ticker_list = [t.strip() for t in tickers.split(",")] if tickers else None
    return get_scatter_plot(x_metric, y_metric, ticker_list)


@router.get("/candlestick/{ticker}")
def api_get_candlestick(
    ticker: str,
    period: str = Query(default="3M"),
):
    """Get candlestick chart data"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_candlestick_data(ticker, period)


@router.get("/area")
def api_get_area(
    tickers: str = Query(description="Comma-separated tickers"),
    stacked: bool = Query(default=True),
    period: str = Query(default="1Y"),
):
    """Get stacked area chart data"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    ticker_list = [t.strip() for t in tickers.split(",")]
    return get_area_chart(ticker_list, stacked, period)


@router.get("/radar/{ticker}")
def api_get_radar(ticker: str):
    """Get radar chart for factor analysis"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_radar_chart(ticker)


@router.get("/histogram")
def api_get_histogram(
    metric: str = Query(default="returns"),
    period: str = Query(default="1Y"),
):
    """Get histogram for distribution analysis"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_histogram(metric, period)


@router.get("/gauge")
def api_get_gauge(
    metric: str = Query(default="portfolio_health"),
    value: Optional[float] = None,
):
    """Get gauge chart data"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_gauge_chart(metric, value)


@router.get("/waterfall/{ticker}")
def api_get_waterfall(ticker: str):
    """Get waterfall chart for performance attribution"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_waterfall_chart(ticker)
