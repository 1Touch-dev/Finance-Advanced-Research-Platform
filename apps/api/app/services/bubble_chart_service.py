"""
Interactive Bubble Charts Service (James J5)
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from app.core.no_data import no_data_response, NoDataReason


def get_bubble_chart(x_metric: str = "market_cap", y_metric: str = "pe_ratio", size_metric: str = "revenue", color_by: str = "sector", tickers: Optional[List[str]] = None) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response("bubble_chart", "bubble_chart_data", NoDataReason.DEPENDENCY_MISSING, details="Bubble chart data requires market data integration")}


def get_bubble_presets() -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response("bubble_chart", "bubble_presets", NoDataReason.DEPENDENCY_MISSING, details="Bubble chart data requires market data integration")}


def get_animated_bubble_data(ticker: str, periods: int = 12, interval: str = "quarterly") -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(ticker, "animated_bubble_data", NoDataReason.DEPENDENCY_MISSING, details="Bubble chart data requires market data integration")}


def get_sector_bubble_chart(sector: Optional[str] = None) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(sector or "all", "sector_bubble_chart", NoDataReason.DEPENDENCY_MISSING, details="Bubble chart data requires market data integration")}


def get_comparison_bubble_chart(ticker1: str, ticker2: str, periods: int = 8) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(f"{ticker1}_vs_{ticker2}", "comparison_bubble_chart", NoDataReason.DEPENDENCY_MISSING, details="Bubble chart data requires market data integration")}


def get_bubble_metrics() -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response("bubble_chart", "bubble_metrics", NoDataReason.DEPENDENCY_MISSING, details="Bubble chart data requires market data integration")}


def get_portfolio_bubble_chart(user_id: str) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(user_id, "portfolio_bubble_chart", NoDataReason.DEPENDENCY_MISSING, details="Bubble chart data requires market data integration")}
