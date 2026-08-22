"""
Point-in-Time Rolling Consensus Service (Band B #19-#21, #23)
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from app.core.no_data import no_data_response, NoDataReason


def get_consensus_snapshot(ticker: str, estimate_type: str = "eps", fiscal_year: Optional[int] = None, fiscal_period: str = "FY", as_of_date=None) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(ticker, "consensus_snapshot", NoDataReason.API_UNAVAILABLE, details="Consensus estimates require premium data provider")}


def get_rolling_consensus(ticker: str, estimate_type: str = "eps", fiscal_year: Optional[int] = None, fiscal_period: str = "FY", lookback_days: int = 180) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(ticker, "rolling_consensus", NoDataReason.API_UNAVAILABLE, details="Consensus estimates require premium data provider")}


def get_consensus_revisions(ticker: str, estimate_type: str = "eps", fiscal_year: Optional[int] = None, fiscal_period: str = "FY", days: int = 90) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(ticker, "consensus_revisions", NoDataReason.API_UNAVAILABLE, details="Consensus estimates require premium data provider")}


def get_consensus_momentum(ticker: str, estimate_type: str = "eps", fiscal_year: Optional[int] = None, fiscal_period: str = "FY") -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(ticker, "consensus_momentum", NoDataReason.API_UNAVAILABLE, details="Consensus estimates require premium data provider")}


def get_estimate_dispersion(ticker: str, estimate_type: str = "eps", fiscal_year: Optional[int] = None, fiscal_period: str = "FY") -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(ticker, "estimate_dispersion", NoDataReason.API_UNAVAILABLE, details="Consensus estimates require premium data provider")}


def get_earnings_surprise(ticker: str, fiscal_year: int, fiscal_period: str) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(ticker, "earnings_surprise", NoDataReason.API_UNAVAILABLE, details="Consensus estimates require premium data provider")}


def get_surprise_history(ticker: str, quarters: int = 12) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(ticker, "surprise_history", NoDataReason.API_UNAVAILABLE, details="Consensus estimates require premium data provider")}


def get_forward_multiples(ticker: str, fiscal_year: Optional[int] = None) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(ticker, "forward_multiples", NoDataReason.API_UNAVAILABLE, details="Consensus estimates require premium data provider")}
