"""
Recursive Entity Discovery API (J7)
Deep recursive entity graph building
"""
from fastapi import APIRouter, Query, Depends
from app.auth.security import get_current_user

from app.services.recursive_entity_service import (
    recursive_discover,
    build_entity_graph,
    find_shortest_path,
    get_entity_clusters,
    detect_circular_ownership,
    get_ownership_chain,
    compare_entity_networks,
)

router = APIRouter(prefix="/recursive", tags=["Recursive Entity Discovery"])


@router.post("/discover/{ticker}")
def discover_recursively(
    ticker: str,
    max_depth: int = Query(3, description="Maximum recursion depth"),
    current_user: dict = Depends(get_current_user),
):
    """Recursively discover related entities."""
    return recursive_discover(ticker, max_depth)


@router.get("/graph/{ticker}")
def entity_graph(
    ticker: str,
    max_depth: int = Query(3, description="Maximum graph depth")
):
    """Build complete entity relationship graph."""
    return build_entity_graph(ticker, max_depth)


@router.get("/path")
def shortest_path(
    source: str = Query(..., description="Source entity"),
    target: str = Query(..., description="Target entity")
):
    """Find shortest path between two entities."""
    return find_shortest_path(source, target)


@router.get("/clusters/{ticker}")
def entity_clusters(ticker: str):
    """Identify clusters of related entities."""
    return get_entity_clusters(ticker)


@router.get("/circular/{ticker}")
def circular_ownership(ticker: str):
    """Detect circular ownership patterns."""
    return detect_circular_ownership(ticker)


@router.get("/chain/{ticker}")
def ownership_chain(ticker: str):
    """Get ownership chain to ultimate parent."""
    return get_ownership_chain(ticker)


@router.get("/compare")
def compare_networks(
    ticker1: str = Query(..., description="First ticker"),
    ticker2: str = Query(..., description="Second ticker")
):
    """Compare entity networks of two companies."""
    return compare_entity_networks(ticker1, ticker2)
