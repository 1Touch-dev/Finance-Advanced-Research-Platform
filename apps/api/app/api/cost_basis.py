"""
Cost Basis Tracking API (#42)
"""

from fastapi import APIRouter, Query, Depends
from app.auth.security import get_current_user
from typing import Optional

router = APIRouter(prefix="/cost-basis", tags=["Cost Basis"])

try:
    from ..services.cost_basis_service import (
        get_user_positions,
        get_ticker_cost_basis,
        add_position,
        get_portfolio_summary,
        get_gains_by_holding_period,
        calculate_realized_gain,
        get_tax_lot_comparison,
        CostBasisMethod,
    )
    SERVICE_AVAILABLE = True
except ImportError:
    SERVICE_AVAILABLE = False


@router.get("/positions")
def api_get_positions(
    user_id: str = Query(default="demo_user"),
    ticker: Optional[str] = None,
):
    """Get all positions for a user"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return {"positions": get_user_positions(user_id, ticker)}


@router.get("/positions/{ticker}")
def api_get_position_detail(
    ticker: str,
    user_id: str = Query(default="demo_user"),
):
    """Get detailed position for a ticker"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_ticker_cost_basis(user_id, ticker)


@router.post("/positions")
def api_add_position(
    ticker: str,
    shares: float,
    cost_per_share: float,
    purchase_date: str,
    user_id: str = Query(default="demo_user"),
    current_user: dict = Depends(get_current_user),
):
    """Add a new position"""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return add_position(user_id, ticker, shares, cost_per_share, purchase_date)


@router.get("/summary")
def api_get_portfolio_summary(
    user_id: str = Query(default="demo_user"),
):
    """Get portfolio summary with gains/losses"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_portfolio_summary(user_id)


@router.get("/realized-gains")
def api_get_realized_gains(
    user_id: str = Query(default="demo_user"),
    year: Optional[int] = None,
):
    """Get realized gains by holding period"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_gains_by_holding_period(user_id)


@router.post("/calculate-sale")
def api_calculate_realized_gain(
    ticker: str,
    shares: float,
    method: str = Query(default="fifo"),
    user_id: str = Query(default="demo_user"),
    current_user: dict = Depends(get_current_user),
):
    """Calculate realized gain for a potential sale"""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    try:
        method_enum = CostBasisMethod(method)
    except ValueError:
        method_enum = CostBasisMethod.FIFO
    return calculate_realized_gain(user_id, ticker, shares, method_enum)


@router.get("/tax-lot-comparison/{ticker}")
def api_get_tax_lot_comparison(
    ticker: str,
    shares: float = Query(default=10),
    user_id: str = Query(default="demo_user"),
):
    """Compare tax lot methods for a sale"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_tax_lot_comparison(user_id, ticker, shares)


@router.get("/history/{ticker}")
def api_get_cost_basis_history(
    ticker: str,
    user_id: str = Query(default="demo_user"),
):
    """Get cost basis details for a ticker"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_ticker_cost_basis(user_id, ticker)
