"""
Tax Lot Optimization Service (Band C #45)
FIFO/LIFO/specific lot selection for tax optimization
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.core.no_data import no_data_response, NoDataReason


def get_tax_lots(user_id: str, ticker: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all tax lots for a user"""
    return {"status": "not_available", "reason": "Tax lot tracking requires brokerage integration", **no_data_response(user_id, "tax_lots", NoDataReason.DEPENDENCY_MISSING, details="Tax lot tracking requires brokerage integration")}


def get_lot_by_id(user_id: str, lot_id: str) -> Optional[Dict[str, Any]]:
    """Get specific tax lot"""
    return {"status": "not_available", "reason": "Tax lot tracking requires brokerage integration", **no_data_response(lot_id, "tax_lot", NoDataReason.DEPENDENCY_MISSING, details="Tax lot tracking requires brokerage integration")}


def optimize_sale(
    user_id: str,
    ticker: str,
    shares_to_sell: float,
    goal: str = "minimize_tax",
) -> Dict[str, Any]:
    """Find optimal lots to sell based on tax goal"""
    return {"status": "not_available", "reason": "Tax lot tracking requires brokerage integration", **no_data_response(ticker, "optimize_sale", NoDataReason.DEPENDENCY_MISSING, details="Tax lot tracking requires brokerage integration")}


def compare_methods(user_id: str, ticker: str, shares_to_sell: float) -> Dict[str, Any]:
    """Compare different tax lot selection methods"""
    return {"status": "not_available", "reason": "Tax lot tracking requires brokerage integration", **no_data_response(ticker, "compare_methods", NoDataReason.DEPENDENCY_MISSING, details="Tax lot tracking requires brokerage integration")}


def get_tax_loss_harvesting_opportunities(user_id: str, min_loss: float = 500) -> List[Dict[str, Any]]:
    """Find opportunities for tax loss harvesting"""
    return {"status": "not_available", "reason": "Tax lot tracking requires brokerage integration", **no_data_response(user_id, "tax_loss_harvesting", NoDataReason.DEPENDENCY_MISSING, details="Tax lot tracking requires brokerage integration")}


def get_approaching_long_term(user_id: str, days_threshold: int = 30) -> List[Dict[str, Any]]:
    """Find lots approaching long-term holding status"""
    return {"status": "not_available", "reason": "Tax lot tracking requires brokerage integration", **no_data_response(user_id, "approaching_long_term", NoDataReason.DEPENDENCY_MISSING, details="Tax lot tracking requires brokerage integration")}
