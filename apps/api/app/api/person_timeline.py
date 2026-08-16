"""
Person Timeline API (James J1)
"""

from fastapi import APIRouter, Query
from typing import Optional, List

router = APIRouter(prefix="/persons", tags=["Persons"])

try:
    from ..services.person_timeline_service import (
        search_persons,
        get_person,
        get_person_timeline,
        get_timeline_with_prices,
        get_person_news,
        get_person_trades,
        get_person_filings,
        compare_persons,
    )
    SERVICE_AVAILABLE = True
except ImportError:
    SERVICE_AVAILABLE = False


@router.get("/search")
def api_search_persons(query: str):
    """Search for persons by name or company"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return {"persons": search_persons(query)}


@router.get("/{person_id}")
def api_get_person(person_id: str):
    """Get person details"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    person = get_person(person_id)
    return person if person else {"error": "Person not found"}


@router.get("/{person_id}/timeline")
def api_get_timeline(
    person_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    event_types: Optional[str] = None,
):
    """Get timeline for a person"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    types = event_types.split(",") if event_types else None
    return get_person_timeline(person_id, start_date, end_date, types)


@router.get("/{person_id}/timeline-with-prices")
def api_get_timeline_with_prices(
    person_id: str,
    days: int = Query(default=365),
):
    """Get timeline with stock price overlay"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_timeline_with_prices(person_id, days)


@router.get("/{person_id}/news")
def api_get_news(
    person_id: str,
    limit: int = Query(default=20),
):
    """Get news about a person"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_person_news(person_id, limit)


@router.get("/{person_id}/trades")
def api_get_trades(
    person_id: str,
    days: int = Query(default=365),
):
    """Get insider trades by person"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_person_trades(person_id, days)


@router.get("/{person_id}/filings")
def api_get_filings(person_id: str):
    """Get SEC filings involving person"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_person_filings(person_id)


@router.get("/compare/multiple")
def api_compare_persons(
    person_ids: str = Query(description="Comma-separated person IDs"),
):
    """Compare timelines of multiple persons"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    ids = [p.strip() for p in person_ids.split(",")]
    return compare_persons(ids)
