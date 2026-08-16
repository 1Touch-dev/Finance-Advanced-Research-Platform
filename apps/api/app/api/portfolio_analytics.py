"""
Portfolio Analytics API (D1-D11)
Advanced portfolio analytics features
"""
from fastapi import APIRouter, Query, Body
from typing import List, Dict, Any, Optional

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
async def factor_decomposition(user_id: str = Query(..., description="User ID")):
    """D1: Get multi-factor risk attribution."""
    return get_factor_decomposition(user_id)


@router.post("/rebalancing")
async def rebalancing_suggestions(
    user_id: str = Query(..., description="User ID"),
    target_allocation: Optional[Dict[str, float]] = Body(None, description="Target allocation")
):
    """D2: Get rebalancing suggestions to target weights."""
    return get_rebalancing_suggestions(user_id, target_allocation)


@router.get("/model-portfolios")
async def model_portfolios():
    """D3: Get pre-built portfolio templates."""
    return get_model_portfolios()


@router.get("/risk-parity")
async def risk_parity(user_id: str = Query(..., description="User ID")):
    """D4: Get risk-weighted allocation."""
    return get_risk_parity_allocation(user_id)


@router.post("/scenario-analysis")
async def scenario_analysis(
    user_id: str = Query(..., description="User ID"),
    scenarios: Optional[List[str]] = Body(None, description="Scenarios to analyze")
):
    """D5: Run what-if portfolio simulations."""
    return run_scenario_analysis(user_id, scenarios)


@router.get("/drawdown")
async def drawdown_analytics(user_id: str = Query(..., description="User ID")):
    """D6: Get max drawdown and recovery analysis."""
    return get_drawdown_analytics(user_id)


@router.get("/correlation-matrix")
async def correlation_matrix(
    user_id: str = Query(..., description="User ID"),
    tickers: Optional[List[str]] = Query(None, description="Tickers to include")
):
    """D7: Get asset correlation heatmap data."""
    return get_correlation_matrix(user_id, tickers)


@router.get("/sector-rotation")
async def sector_rotation(user_id: str = Query(..., description="User ID")):
    """D8: Get sector momentum signals."""
    return get_sector_rotation_signals(user_id)


@router.get("/factor-timing")
async def factor_timing():
    """D9: Get factor exposure timing signals."""
    return get_factor_timing_signals()


@router.post("/custom-benchmark")
async def custom_benchmark(
    user_id: str = Query(..., description="User ID"),
    components: List[Dict[str, Any]] = Body(..., description="Benchmark components")
):
    """D10: Create custom benchmark blend."""
    return create_custom_benchmark(user_id, components)


@router.get("/performance-attribution")
async def performance_attribution(user_id: str = Query(..., description="User ID")):
    """D11: Get Brinson performance attribution."""
    return get_performance_attribution(user_id)
