"""
Portfolio Analytics API (D1-D11)
Advanced portfolio analytics features
"""
from fastapi import APIRouter, Query, Body, Depends
from typing import List, Dict, Any, Optional

from app.auth.security import get_current_user

from app.services.portfolio_analytics_service import (
    get_factor_decomposition,
    get_rebalancing_suggestions,
    get_model_portfolios,
    get_risk_parity_allocation,
    run_scenario_analysis,
    get_drawdown_analytics,
    get_correlation_matrix,
    get_sector_rotation_signals,
    get_factor_timing_signals,
    create_custom_benchmark,
    get_performance_attribution,
)

router = APIRouter(prefix="/portfolio-analytics", tags=["Portfolio Analytics"])


@router.get("/factor-decomposition")
def factor_decomposition(user_id: str = Query(..., description="User ID")):
    """D1: Get multi-factor risk attribution."""
    return get_factor_decomposition(user_id)


@router.post("/rebalancing")
def rebalancing_suggestions(
    user_id: Optional[str] = Query(None, description="User ID"),
    target_allocation: Optional[Dict[str, float]] = Body(None, description="Target allocation"),
    current_user: dict = Depends(get_current_user),
):
    """D2: Get rebalancing suggestions to target weights."""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    return get_rebalancing_suggestions(user_id, target_allocation)


@router.get("/model-portfolios")
def model_portfolios():
    """D3: Get pre-built portfolio templates."""
    return get_model_portfolios()


@router.get("/risk-parity")
def risk_parity(user_id: str = Query(..., description="User ID")):
    """D4: Get risk-weighted allocation."""
    return get_risk_parity_allocation(user_id)


@router.post("/scenario-analysis")
def scenario_analysis(
    user_id: Optional[str] = Query(None, description="User ID"),
    scenarios: Optional[List[str]] = Body(None, description="Scenarios to analyze"),
    current_user: dict = Depends(get_current_user),
):
    """D5: Run what-if portfolio simulations."""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    return run_scenario_analysis(user_id, scenarios)


@router.get("/drawdown")
def drawdown_analytics(user_id: str = Query(..., description="User ID")):
    """D6: Get max drawdown and recovery analysis."""
    return get_drawdown_analytics(user_id)


@router.get("/correlation-matrix")
def correlation_matrix(
    user_id: Optional[str] = Query(None, description="User ID"),
    tickers: Optional[List[str]] = Query(None, description="Tickers to include")
):
    """D7: Get asset correlation heatmap data."""
    return get_correlation_matrix(user_id, tickers)


@router.get("/sector-rotation")
def sector_rotation(user_id: str = Query(..., description="User ID")):
    """D8: Get sector momentum signals."""
    return get_sector_rotation_signals(user_id)


@router.get("/factor-timing")
def factor_timing():
    """D9: Get factor exposure timing signals."""
    return get_factor_timing_signals()


@router.post("/custom-benchmark")
def custom_benchmark(
    user_id: Optional[str] = Query(None, description="User ID"),
    components: List[Dict[str, Any]] = Body(..., description="Benchmark components"),
    current_user: dict = Depends(get_current_user),
):
    """D10: Create custom benchmark blend."""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    return create_custom_benchmark(user_id, components)


@router.get("/performance-attribution")
def performance_attribution(user_id: str = Query(..., description="User ID")):
    """D11: Get Brinson performance attribution."""
    return get_performance_attribution(user_id)
