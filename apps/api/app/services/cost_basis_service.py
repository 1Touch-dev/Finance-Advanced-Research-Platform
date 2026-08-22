"""
Cost Basis Tracking Service (Band C #42)
Track purchase prices, calculate gains/losses
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.core.no_data import no_data_response, NoDataReason


def get_user_positions(user_id: str, ticker: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all positions for a user"""
    return {"status": "not_available", "reason": "Cost basis requires brokerage sync", **no_data_response(user_id, "user_positions", NoDataReason.DEPENDENCY_MISSING, details="Cost basis requires brokerage sync")}


def get_position_by_lot(user_id: str, lot_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific lot"""
    return {"status": "not_available", "reason": "Cost basis requires brokerage sync", **no_data_response(lot_id, "position_lot", NoDataReason.DEPENDENCY_MISSING, details="Cost basis requires brokerage sync")}


def get_portfolio_summary(user_id: str) -> Dict[str, Any]:
    """Get portfolio cost basis summary"""
    return {"status": "not_available", "reason": "Cost basis requires brokerage sync", **no_data_response(user_id, "portfolio_summary", NoDataReason.DEPENDENCY_MISSING, details="Cost basis requires brokerage sync")}


def get_ticker_cost_basis(user_id: str, ticker: str) -> Dict[str, Any]:
    """Get cost basis details for a specific ticker"""
    return {"status": "not_available", "reason": "Cost basis requires brokerage sync", **no_data_response(ticker, "ticker_cost_basis", NoDataReason.DEPENDENCY_MISSING, details="Cost basis requires brokerage sync")}


def calculate_realized_gain(
    user_id: str,
    ticker: str,
    shares_to_sell: float,
    method: str = "fifo",
    specific_lots: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Calculate realized gain for a potential sale"""
    return {"status": "not_available", "reason": "Cost basis requires brokerage sync", **no_data_response(ticker, "realized_gain", NoDataReason.DEPENDENCY_MISSING, details="Cost basis requires brokerage sync")}


def get_tax_lot_comparison(user_id: str, ticker: str, shares_to_sell: float) -> Dict[str, Any]:
    """Compare different cost basis methods for tax planning"""
    return {"status": "not_available", "reason": "Cost basis requires brokerage sync", **no_data_response(ticker, "tax_lot_comparison", NoDataReason.DEPENDENCY_MISSING, details="Cost basis requires brokerage sync")}


def get_gains_by_holding_period(user_id: str) -> Dict[str, Any]:
    """Get unrealized gains grouped by holding period"""
    return {"status": "not_available", "reason": "Cost basis requires brokerage sync", **no_data_response(user_id, "gains_by_period", NoDataReason.DEPENDENCY_MISSING, details="Cost basis requires brokerage sync")}


def add_position(
    user_id: str,
    ticker: str,
    shares: float,
    purchase_price: float,
    purchase_date: str,
) -> Dict[str, Any]:
    """Add a new position/lot"""
    return {"status": "not_available", "reason": "Cost basis requires brokerage sync", **no_data_response(ticker, "add_position", NoDataReason.DEPENDENCY_MISSING, details="Cost basis requires brokerage sync")}
