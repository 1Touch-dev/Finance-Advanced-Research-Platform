"""
Per-Analyst Accuracy Scoring Service (Band B #24)
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from app.core.no_data import no_data_response, NoDataReason


def get_analyst_profile(analyst_id: str) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(analyst_id, "analyst_profile", NoDataReason.API_UNAVAILABLE, details="Analyst ratings require premium data provider")}


def search_analysts(firm: Optional[str] = None, sector: Optional[str] = None, ticker: Optional[str] = None, name: Optional[str] = None) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(firm or sector or ticker or "analysts", "analyst_search", NoDataReason.API_UNAVAILABLE, details="Analyst ratings require premium data provider")}


def calculate_analyst_accuracy(analyst_id: str) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(analyst_id, "analyst_accuracy", NoDataReason.API_UNAVAILABLE, details="Analyst ratings require premium data provider")}


def get_analyst_ranking(sector: Optional[str] = None, firm: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(sector or firm or "all", "analyst_ranking", NoDataReason.API_UNAVAILABLE, details="Analyst ratings require premium data provider")}


def get_firm_ranking() -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response("firms", "firm_ranking", NoDataReason.API_UNAVAILABLE, details="Analyst ratings require premium data provider")}


def get_sector_ranking(sector: str) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(sector, "sector_analyst_ranking", NoDataReason.API_UNAVAILABLE, details="Analyst ratings require premium data provider")}


def get_ticker_analysts(ticker: str) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(ticker, "ticker_analysts", NoDataReason.API_UNAVAILABLE, details="Analyst ratings require premium data provider")}


def get_analyst_estimates_history(analyst_id: str, limit: int = 20) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(analyst_id, "analyst_estimates_history", NoDataReason.API_UNAVAILABLE, details="Analyst ratings require premium data provider")}


def compare_analysts(analyst_ids: List[str]) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response("analysts", "analyst_comparison", NoDataReason.API_UNAVAILABLE, details="Analyst ratings require premium data provider")}


def get_rating_changes(ticker: str, days: int = 90) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(ticker, "rating_changes", NoDataReason.API_UNAVAILABLE, details="Analyst ratings require premium data provider")}


def get_price_target_history(ticker: str) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(ticker, "price_target_history", NoDataReason.API_UNAVAILABLE, details="Analyst ratings require premium data provider")}


def get_rating_distribution(ticker: str) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(ticker, "rating_distribution", NoDataReason.API_UNAVAILABLE, details="Analyst ratings require premium data provider")}


def get_analyst_rating_history(analyst_id: str, limit: int = 20) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(analyst_id, "analyst_rating_history", NoDataReason.API_UNAVAILABLE, details="Analyst ratings require premium data provider")}
