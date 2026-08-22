"""
Whisper Estimates + Buy/Sell-Side Split Service (Band B #25)
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from app.core.no_data import no_data_response, NoDataReason


class WhisperEstimatesService:
    """Service for whisper estimates and buy/sell-side analysis."""

    def get_whisper_estimate(self, ticker: str, period: str = "next_quarter", metric: str = "eps") -> Dict[str, Any]:
        return {"status": "not_available", **no_data_response(ticker, "whisper_estimate", NoDataReason.API_UNAVAILABLE, details="Whisper estimates require premium data feed")}

    def get_side_split_analysis(self, ticker: str, period: str = "next_quarter", metric: str = "eps") -> Dict[str, Any]:
        return {"status": "not_available", **no_data_response(ticker, "side_split_analysis", NoDataReason.API_UNAVAILABLE, details="Whisper estimates require premium data feed")}

    def get_whisper_history(self, ticker: str, metric: str = "eps", periods: int = 8) -> Dict[str, Any]:
        return {"status": "not_available", **no_data_response(ticker, "whisper_history", NoDataReason.API_UNAVAILABLE, details="Whisper estimates require premium data feed")}

    def get_dispersion_by_side(self, ticker: str, period: str = "next_quarter", metric: str = "eps") -> Dict[str, Any]:
        return {"status": "not_available", **no_data_response(ticker, "dispersion_by_side", NoDataReason.API_UNAVAILABLE, details="Whisper estimates require premium data feed")}

    def get_whisper_snapshot(self, ticker: str) -> Dict[str, Any]:
        return {"status": "not_available", **no_data_response(ticker, "whisper_snapshot", NoDataReason.API_UNAVAILABLE, details="Whisper estimates require premium data feed")}

    def get_estimates_by_type(self, ticker: str, analyst_type: str = "sell_side", period: str = "next_quarter", metric: str = "eps") -> Dict[str, Any]:
        return {"status": "not_available", **no_data_response(ticker, "estimates_by_type", NoDataReason.API_UNAVAILABLE, details="Whisper estimates require premium data feed")}


_service_instance = None


def get_whisper_service() -> WhisperEstimatesService:
    global _service_instance
    if _service_instance is None:
        _service_instance = WhisperEstimatesService()
    return _service_instance
