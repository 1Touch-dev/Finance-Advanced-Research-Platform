"""
Autonomous Agent API (J6)
Auto-discover subsidiaries/family entities
"""
from fastapi import APIRouter, Query
from typing import List, Optional

from app.services.autonomous_agent_service import (
    start_discovery_job,
    get_job_status,
    get_discovered_entities,
    get_entity_graph,
    discover_subsidiaries,
    discover_investments,
    discover_board_connections,
    get_family_tree,
)

router = APIRouter(prefix="/agent", tags=["Autonomous Agent"])


@router.post("/discover")
async def start_discovery(
    ticker: str = Query(..., description="Stock ticker"),
    depth: int = Query(2, description="Discovery depth (1-5)"),
    entity_types: Optional[List[str]] = Query(None, description="Entity types to discover")
):
    """Start autonomous entity discovery job."""
    return start_discovery_job(ticker, depth, entity_types)


@router.get("/jobs/{job_id}")
async def job_status(job_id: str):
    """Get status of discovery job."""
    return get_job_status(job_id)


@router.get("/entities/{ticker}")
async def get_entities(ticker: str):
    """Get all discovered entities for a ticker."""
    return get_discovered_entities(ticker)


@router.get("/graph/{ticker}")
async def entity_graph(
    ticker: str,
    depth: int = Query(2, description="Graph depth")
):
    """Get entity relationship graph for visualization."""
    return get_entity_graph(ticker, depth)


@router.get("/subsidiaries/{ticker}")
async def subsidiaries(ticker: str):
    """Discover subsidiaries from SEC filings."""
    return discover_subsidiaries(ticker)


@router.get("/investments/{ticker}")
async def investments(ticker: str):
    """Discover investment holdings."""
    return discover_investments(ticker)


@router.get("/board-connections/{ticker}")
async def board_connections(ticker: str):
    """Discover board member connections."""
    return discover_board_connections(ticker)


@router.get("/family-tree/{ticker}")
async def family_tree(ticker: str):
    """Get corporate family tree structure."""
    return get_family_tree(ticker)
