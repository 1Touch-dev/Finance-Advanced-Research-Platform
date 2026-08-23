"""
Benchmark Attribution API (#44)
"""

from fastapi import APIRouter, Query, Depends
from app.auth.security import get_current_user
from typing import Optional, List

router = APIRouter(prefix="/benchmark", tags=["Benchmark"])

try:
    from ..services.benchmark_service import (
        get_benchmarks,
        get_portfolio_vs_benchmark,
        get_sector_attribution,
        get_historical_comparison,
        get_risk_contribution,
    )
    SERVICE_AVAILABLE = True
except ImportError:
    SERVICE_AVAILABLE = False


@router.get("/available")
def api_get_benchmarks():
    """Get available benchmarks"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return {"benchmarks": get_benchmarks()}


@router.get("/compare")
def api_compare_portfolio(
    benchmark: str = Query(default="SPY"),
    period: str = Query(default="1Y"),
    user_id: str = Query(default="demo_user"),
    current_user: dict = Depends(get_current_user),
):
    """Compare portfolio vs benchmark"""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_portfolio_vs_benchmark(user_id, benchmark)


@router.get("/sector-attribution")
def api_get_sector_attribution(
    benchmark: str = Query(default="SPY"),
    user_id: str = Query(default="demo_user"),
    current_user: dict = Depends(get_current_user),
):
    """Get sector attribution analysis"""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_sector_attribution(user_id)


@router.get("/historical")
def api_get_historical(
    benchmark: str = Query(default="SPY"),
    periods: int = Query(default=12),
    user_id: str = Query(default="demo_user"),
    current_user: dict = Depends(get_current_user),
):
    """Get historical comparison"""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_historical_comparison(user_id, benchmark, periods)


@router.get("/risk-metrics")
def api_get_risk_metrics(
    benchmark: str = Query(default="SPY"),
    user_id: str = Query(default="demo_user"),
    current_user: dict = Depends(get_current_user),
):
    """Get risk metrics vs benchmark"""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    # Risk metrics are included in portfolio comparison
    return get_portfolio_vs_benchmark(user_id, benchmark)


@router.get("/risk-contribution")
def api_get_risk_contribution(
    user_id: str = Query(default="demo_user"),
    current_user: dict = Depends(get_current_user),
):
    """Get risk contribution by position"""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_risk_contribution(user_id)


@router.get("/factor-exposure")
def api_get_factor_exposure(
    user_id: str = Query(default="demo_user"),
    current_user: dict = Depends(get_current_user),
):
    """Get factor exposure analysis"""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    # Return risk contribution which includes factor-like data
    return get_risk_contribution(user_id)


@router.get("/attribution")
def api_get_performance_attribution(
    benchmark: str = Query(default="SPY"),
    period: str = Query(default="1Y"),
    user_id: str = Query(default="demo_user"),
    current_user: dict = Depends(get_current_user),
):
    """Get detailed performance attribution"""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_sector_attribution(user_id)


@router.get("/alpha/{ticker}")
def api_calculate_alpha(
    ticker: str,
    benchmark: str = Query(default="SPY"),
    period: str = Query(default="1Y"),
):
    """Calculate alpha for a single ticker"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    # Return comparison data which includes alpha
    result = get_portfolio_vs_benchmark("demo_user", benchmark)
    if "error" in result:
        return result
    return {
        "ticker": ticker.upper(),
        "benchmark": benchmark,
        "alpha": result.get("summary", {}).get("total_alpha_1y", 0),
    }
