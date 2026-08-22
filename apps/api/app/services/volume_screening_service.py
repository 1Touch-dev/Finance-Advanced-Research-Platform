"""
Unusual Volume Screening Service (Band B #28)
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from app.core.no_data import no_data_response, NoDataReason


def get_volume_bar(ticker: str, bar_date=None) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(ticker, "volume_bar", NoDataReason.API_UNAVAILABLE, details="Volume screening requires real-time market data")}


def get_volume_history(ticker: str, days: int = 30) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(ticker, "volume_history", NoDataReason.API_UNAVAILABLE, details="Volume screening requires real-time market data")}


def screen_unusual_volume(min_ratio: float = 2.0, tickers: Optional[List[str]] = None, sector: Optional[str] = None) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response("screener", "unusual_volume_screen", NoDataReason.API_UNAVAILABLE, details="Volume screening requires real-time market data")}


def get_ticker_volume_profile(ticker: str) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(ticker, "volume_profile", NoDataReason.API_UNAVAILABLE, details="Volume screening requires real-time market data")}


def get_sector_volume_flow(sector: str) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(sector, "sector_volume_flow", NoDataReason.API_UNAVAILABLE, details="Volume screening requires real-time market data")}
