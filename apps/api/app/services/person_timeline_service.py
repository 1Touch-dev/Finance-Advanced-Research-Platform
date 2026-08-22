"""
Person Timeline Service (James J1)
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from app.core.no_data import no_data_response, NoDataReason


def search_persons(query: str) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(query, "person_search", NoDataReason.API_UNAVAILABLE, details="Person timeline requires entity graph data")}


def get_person(person_id: str) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(person_id, "person_detail", NoDataReason.API_UNAVAILABLE, details="Person timeline requires entity graph data")}


def get_person_timeline(person_id: str, start_date: Optional[str] = None, end_date: Optional[str] = None, event_types: Optional[List[str]] = None) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(person_id, "person_timeline", NoDataReason.API_UNAVAILABLE, details="Person timeline requires entity graph data")}


def get_timeline_with_prices(person_id: str, days: int = 365) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(person_id, "timeline_with_prices", NoDataReason.API_UNAVAILABLE, details="Person timeline requires entity graph data")}


def get_person_news(person_id: str, limit: int = 20) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(person_id, "person_news", NoDataReason.API_UNAVAILABLE, details="Person timeline requires entity graph data")}


def get_person_trades(person_id: str, days: int = 365) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(person_id, "person_trades", NoDataReason.API_UNAVAILABLE, details="Person timeline requires entity graph data")}


def get_person_filings(person_id: str) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response(person_id, "person_filings", NoDataReason.API_UNAVAILABLE, details="Person timeline requires entity graph data")}


def compare_persons(person_ids: List[str]) -> Dict[str, Any]:
    return {"status": "not_available", **no_data_response("persons", "person_comparison", NoDataReason.API_UNAVAILABLE, details="Person timeline requires entity graph data")}
