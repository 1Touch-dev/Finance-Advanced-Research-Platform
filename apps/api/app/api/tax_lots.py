"""
Tax Lot Optimization API (#45)
"""

from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter(prefix="/tax-lots", tags=["Tax Lots"])

try:
    from ..services.tax_lot_service import (
        get_tax_lots,
        get_lot_by_id,
        optimize_sale,
        compare_methods,
        get_tax_loss_harvesting_opportunities,
        get_approaching_long_term,
    )
    SERVICE_AVAILABLE = True
except ImportError:
    SERVICE_AVAILABLE = False


@router.get("/")
def api_get_tax_lots(
    user_id: str = Query(default="demo_user"),
    ticker: Optional[str] = None,
):
    """Get all tax lots"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return {"lots": get_tax_lots(user_id, ticker)}


@router.get("/lot/{lot_id}")
def api_get_lot(
    lot_id: str,
    user_id: str = Query(default="demo_user"),
):
    """Get specific tax lot"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    lot = get_lot_by_id(user_id, lot_id)
    return lot if lot else {"error": "Lot not found"}


@router.get("/optimize")
def api_optimize_sale(
    ticker: str,
    shares: float,
    goal: str = Query(default="minimize_tax"),
    user_id: str = Query(default="demo_user"),
):
    """Optimize lot selection for sale"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return optimize_sale(user_id, ticker, shares, goal)


@router.get("/compare-methods")
def api_compare_methods(
    ticker: str,
    shares: float,
    user_id: str = Query(default="demo_user"),
):
    """Compare tax lot selection methods"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return compare_methods(user_id, ticker, shares)


@router.get("/harvesting-opportunities")
def api_get_harvesting(
    user_id: str = Query(default="demo_user"),
    min_loss: float = Query(default=500),
):
    """Get tax loss harvesting opportunities"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return {"opportunities": get_tax_loss_harvesting_opportunities(user_id, min_loss)}


@router.get("/approaching-long-term")
def api_get_approaching_long_term(
    user_id: str = Query(default="demo_user"),
    days_threshold: int = Query(default=30),
):
    """Get lots approaching long-term status"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return {"lots": get_approaching_long_term(user_id, days_threshold)}
