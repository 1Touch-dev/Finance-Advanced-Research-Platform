"""
Intelligence Graph API Router
══════════════════════════════════════════════════════════════════════════════

Exposes the Entity Graph Store and Recursion Engine via REST API.

Endpoints:
- POST /intelligence/graph/entity - Add an entity
- POST /intelligence/graph/edge - Add an edge with evidence
- GET /intelligence/graph/explore/{entity_id} - Explore network from seed
- GET /intelligence/graph/connect - Find paths between two entities
- GET /intelligence/graph/resolve - Resolve entity by identifier
- GET /intelligence/graph/stats - Graph statistics
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services import entity_graph_service as graph
from app.services import paypal_mafia_loader as paypal_loader
from app.services import graph_ingestion_service as ingestion

router = APIRouter(prefix="/intelligence/graph", tags=["Intelligence Graph"])


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# REQUEST/RESPONSE MODELS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class EvidenceRefRequest(BaseModel):
    """Evidence reference for a claim."""
    document_id: str = Field(..., description="SHA256 or source native ID")
    source_name: str = Field(..., description="e.g., 'SEC EDGAR', 'FEC'")
    source_url: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    excerpt: Optional[str] = Field(None, description="Quoted text supporting claim")


class AddEntityRequest(BaseModel):
    """Request to add an entity."""
    entity_id: str = Field(..., description="Unique entity ID")
    kind: str = Field(..., description="person|org|fund|agency|pac|case")
    name: str = Field(..., description="Display name")
    identifiers: Optional[Dict[str, str]] = Field(
        default=None,
        description="Identifiers: CIK, LEI, EIN, FEC, etc."
    )
    aliases: Optional[List[str]] = Field(default=None, description="Alternative names")
    meta: Optional[Dict[str, Any]] = None


class AddEdgeRequest(BaseModel):
    """
    Request to add an edge with evidence.

    Per A5 Audit: evidence_refs MUST be non-empty.
    """
    edge_id: str = Field(..., description="Unique edge ID")
    src_entity_id: str
    dst_entity_id: str
    relationship_type: str = Field(
        ...,
        description="From closed vocabulary: owns, invested_in, employed_at, etc."
    )
    confidence_tier: str = Field(
        ...,
        description="CONFIRMED|REPORTED|INFERRED|SPECULATIVE"
    )
    evidence_refs: List[EvidenceRefRequest] = Field(
        ...,
        min_length=1,
        description="At least one evidence reference required (A5 compliance)"
    )
    as_of: Optional[datetime] = Field(None, description="When relationship started")
    valid_to: Optional[datetime] = Field(None, description="When it ended (null=active)")
    source_name: Optional[str] = Field(None, description="Data source name")
    meta: Optional[Dict[str, Any]] = None


class ExploreResponse(BaseModel):
    """Response from network exploration."""
    seed: Dict[str, Any]
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    depth_reached: int
    nodes_explored: int
    cost_spent: float
    config: Dict[str, Any]


class PathResponse(BaseModel):
    """A path through the graph."""
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    depth: int
    confidence_floor: str


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENDPOINTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/entity", summary="Add an entity to the graph")
def add_entity(request: AddEntityRequest) -> Dict[str, Any]:
    """
    Add an entity to the intelligence graph.

    Entities are the nodes in the graph: people, organizations, funds, etc.
    """
    entity = graph.add_entity(
        entity_id=request.entity_id,
        kind=request.kind,
        name=request.name,
        identifiers=request.identifiers,
        aliases=request.aliases,
        meta=request.meta,
    )
    return {
        "id": entity.id,
        "kind": entity.kind,
        "name": entity.name,
        "identifiers": entity.identifiers,
        "aliases": entity.aliases,
    }


@router.post("/edge", summary="Add an edge with evidence")
def add_edge(request: AddEdgeRequest) -> Dict[str, Any]:
    """
    Add an edge (relationship) to the intelligence graph.

    **A5 Compliance**: Every edge MUST have at least one evidence_ref.
    This ensures every claim in the graph is backed by a source document.
    """
    try:
        evidence_dicts = [ref.model_dump() for ref in request.evidence_refs]
        edge = graph.add_edge(
            edge_id=request.edge_id,
            src_entity_id=request.src_entity_id,
            dst_entity_id=request.dst_entity_id,
            relationship_type=request.relationship_type,
            confidence_tier=request.confidence_tier,
            evidence_refs=evidence_dicts,
            as_of=request.as_of,
            valid_to=request.valid_to,
            source_name=request.source_name,
            meta=request.meta,
        )
        return {
            "id": edge.id,
            "src": edge.src_entity_id,
            "dst": edge.dst_entity_id,
            "type": edge.relationship_type,
            "confidence": edge.confidence_tier.value,
            "evidence_count": len(edge.evidence_refs),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get(
    "/explore/{entity_id}",
    response_model=ExploreResponse,
    summary="Explore network from seed entity"
)
def explore_network(
    entity_id: str,
    max_depth: int = Query(3, ge=1, le=5, description="Maximum BFS depth"),
    max_nodes: int = Query(500, ge=10, le=2000, description="Maximum nodes to explore"),
    min_confidence: str = Query("INFERRED", description="Minimum confidence tier"),
    relationship_types: Optional[str] = Query(
        None,
        description="Comma-separated relationship types to include"
    ),
) -> Dict[str, Any]:
    """
    Explore the network from a seed entity using BFS.

    This implements James's "Follow the Money" use case:
    - Start from a person or company
    - Recursively explore connections
    - Track depth and cost
    - Filter by confidence tier
    """
    types_list = relationship_types.split(",") if relationship_types else None

    result = graph.explore_network(
        seed_entity_id=entity_id,
        max_depth=max_depth,
        max_nodes=max_nodes,
        min_confidence=min_confidence,
        relationship_types=types_list,
    )

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/connect", summary="Find paths between two entities")
def find_connection(
    src: str = Query(..., description="Source entity ID"),
    dst: str = Query(..., description="Destination entity ID"),
    max_depth: int = Query(3, ge=1, le=5, description="Maximum path length"),
    min_confidence: str = Query("INFERRED", description="Minimum confidence tier"),
) -> Dict[str, Any]:
    """
    Find all paths connecting two entities.

    Returns paths sorted by depth (shortest first).
    Each path includes the confidence floor (lowest confidence edge).
    """
    paths = graph.find_connection(
        src_entity_id=src,
        dst_entity_id=dst,
        max_depth=max_depth,
        min_confidence=min_confidence,
    )

    return {
        "src": src,
        "dst": dst,
        "paths_found": len(paths),
        "paths": paths,
    }


@router.get("/resolve", summary="Resolve entity by identifier")
def resolve_entity(
    scheme: str = Query(..., description="Identifier scheme: CIK, LEI, EIN, FEC, etc."),
    value: str = Query(..., description="Identifier value"),
) -> Dict[str, Any]:
    """
    Resolve an entity by its identifier.

    Supports deterministic ID matching via:
    - CIK (SEC)
    - LEI (Legal Entity Identifier)
    - EIN (IRS)
    - FEC (Federal Election Commission)
    - DUNS (D&B)
    - Bioguide (Congress)
    - And more...
    """
    entity = graph.resolve_entity(scheme, value)
    if not entity:
        raise HTTPException(
            status_code=404,
            detail=f"No entity found with {scheme}={value}"
        )
    return entity


@router.get("/stats", summary="Get graph statistics")
def get_stats() -> Dict[str, Any]:
    """
    Get statistics about the intelligence graph.

    Returns:
    - Total entities
    - Total edges
    - Indexed identifiers count
    """
    stats = graph.get_graph_stats()
    return {
        **stats,
        "source": "Entity Graph Store",
        "version": "1.0.0",
    }


@router.get("/relationship-types", summary="List valid relationship types")
def list_relationship_types() -> Dict[str, Any]:
    """
    List all valid relationship types in the closed vocabulary.

    Per A5 Audit: Edge types must be from a closed vocabulary, no free text.
    """
    from app.services.entity_graph_service import RelationshipType

    types = []
    for rt in RelationshipType:
        types.append({
            "value": rt.value,
            "name": rt.name,
        })

    return {
        "relationship_types": types,
        "count": len(types),
    }


@router.get("/confidence-tiers", summary="List confidence tiers with accuracy targets")
def list_confidence_tiers() -> Dict[str, Any]:
    """
    List confidence tiers and their accuracy targets.

    Per A7 Audit: Each tier has a calibrated accuracy target.
    """
    return {
        "tiers": [
            {
                "value": "CONFIRMED",
                "description": "Primary source document, directly asserted",
                "accuracy_target": "≥99%",
            },
            {
                "value": "REPORTED",
                "description": "≥2 credible secondary sources agreeing",
                "accuracy_target": "≥90%",
            },
            {
                "value": "INFERRED",
                "description": "Derived from ≥2 confirmed facts, method stated",
                "accuracy_target": "≥70%",
            },
            {
                "value": "SPECULATIVE",
                "description": "Single weak source or pattern-based",
                "accuracy_target": "≥40%",
            },
        ],
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PAYPAL MAFIA DEMONSTRATION ENDPOINTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/paypal-mafia/load", summary="Load PayPal Mafia seed data")
def load_paypal_mafia() -> Dict[str, Any]:
    """
    Load the PayPal Mafia demonstration dataset into the graph.

    This seeds the graph with:
    - 21 PayPal Mafia members (people)
    - ~25 companies and funds
    - 60+ relationships with evidence

    Use this to demonstrate "Follow the Money" network exploration.
    """
    stats = paypal_loader.load_paypal_mafia_graph()
    return {
        "status": "loaded",
        "entities_loaded": stats["entities_loaded"],
        "entities_failed": stats["entities_failed"],
        "edges_loaded": stats["edges_loaded"],
        "edges_failed": stats["edges_failed"],
        "errors": stats["errors"][:10] if stats["errors"] else [],
    }


@router.get("/paypal-mafia/stats", summary="Get PayPal Mafia dataset stats")
def get_paypal_mafia_stats() -> Dict[str, Any]:
    """
    Get statistics about the PayPal Mafia dataset and graph state.
    """
    return paypal_loader.get_paypal_mafia_stats()


@router.get("/paypal-mafia/explore", summary="Explore PayPal Mafia network")
def explore_paypal_mafia(
    seed: str = Query(
        "person:peter-thiel",
        description="Seed entity ID to explore from"
    ),
    max_depth: int = Query(3, ge=1, le=5, description="Maximum BFS depth"),
    max_nodes: int = Query(500, ge=10, le=2000, description="Maximum nodes"),
) -> Dict[str, Any]:
    """
    Explore the PayPal Mafia network from a seed person.

    Default seed is Peter Thiel as the most connected member.

    Example seeds:
    - person:peter-thiel
    - person:elon-musk
    - person:reid-hoffman
    - org:paypal
    """
    result = paypal_loader.explore_paypal_mafia(
        seed_person=seed,
        max_depth=max_depth,
        max_nodes=max_nodes,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/paypal-mafia/connect", summary="Find connection between two members")
def find_paypal_connection(
    person_a: str = Query(..., description="First entity ID"),
    person_b: str = Query(..., description="Second entity ID"),
    max_depth: int = Query(4, ge=1, le=6, description="Maximum path length"),
) -> Dict[str, Any]:
    """
    Find connections between two PayPal Mafia entities.

    Examples:
    - person:peter-thiel → person:steve-chen (YouTube founder)
    - person:elon-musk → org:affirm
    - fund:sequoia → org:palantir
    """
    return paypal_loader.find_paypal_connection(
        person_a=person_a,
        person_b=person_b,
        max_depth=max_depth,
    )


@router.get("/paypal-mafia/queries", summary="Get interesting pre-defined queries")
def get_paypal_queries() -> Dict[str, Any]:
    """
    Get pre-defined interesting network queries.

    These demonstrate the "Follow the Money" use case.
    """
    queries = paypal_loader.get_interesting_queries()
    return {
        "queries": queries,
        "count": len(queries),
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DATA INGESTION ENDPOINTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class IngestEntityRequest(BaseModel):
    """Request to ingest an entity from multiple sources."""
    entity_name: str = Field(..., description="Company/entity name")
    cik: Optional[str] = Field(None, description="SEC CIK (10 digits)")
    include_sec: bool = Field(True, description="Ingest SEC EDGAR data")
    include_fec: bool = Field(True, description="Ingest FEC political data")
    include_contracts: bool = Field(True, description="Ingest USASpending contracts")


@router.post("/ingest/entity", summary="Ingest entity from public data sources")
def ingest_entity(request: IngestEntityRequest) -> Dict[str, Any]:
    """
    Ingest an entity and its network from multiple public data sources.

    Sources:
    - **SEC EDGAR**: Company info, officers, directors, insider transactions
    - **FEC**: Political contributions, PAC donations
    - **USASpending**: Federal government contracts

    This automatically expands the intelligence graph with real data.
    """
    stats = ingestion.ingest_entity_full(
        entity_name=request.entity_name,
        cik=request.cik,
        include_sec=request.include_sec,
        include_fec=request.include_fec,
        include_contracts=request.include_contracts,
    )
    return stats


@router.post("/ingest/sec/{cik}", summary="Ingest SEC company data")
def ingest_sec_company(
    cik: str,
    company_name: Optional[str] = Query(None, description="Company name override"),
) -> Dict[str, Any]:
    """
    Ingest a single company from SEC EDGAR.

    Extracts officers, directors, and insider transactions.
    """
    stats = ingestion.ingest_sec_company(cik, company_name)
    return {
        "cik": cik,
        "source": "SEC EDGAR",
        **stats,
    }


@router.post("/ingest/fec", summary="Ingest FEC political contribution data")
def ingest_fec_contributions(
    entity_name: str = Query(..., description="Entity name to search"),
    cycle: int = Query(2024, description="Election cycle year"),
) -> Dict[str, Any]:
    """
    Ingest FEC political contribution data for an entity.

    Includes PAC contributions and individual executive donations.
    """
    entity_id = f"org:{ingestion._normalize_id(entity_name)}"
    stats = ingestion.ingest_fec_contributions(entity_name, entity_id, cycle)
    return {
        "entity_name": entity_name,
        "cycle": cycle,
        "source": "FEC",
        **stats,
    }


@router.post("/ingest/contracts", summary="Ingest government contract data")
def ingest_government_contracts(
    entity_name: str = Query(..., description="Entity name to search"),
) -> Dict[str, Any]:
    """
    Ingest federal government contracts from USASpending.gov.

    Creates agency entities and contract award relationships.
    """
    entity_id = f"org:{ingestion._normalize_id(entity_name)}"
    stats = ingestion.ingest_government_contracts(entity_name, entity_id)
    return {
        "entity_name": entity_name,
        "source": "USASpending.gov",
        **stats,
    }


@router.post("/ingest/demo", summary="Ingest demo companies")
def ingest_demo_companies() -> Dict[str, Any]:
    """
    Ingest demonstration companies for testing.

    Includes major tech companies: Tesla, NVIDIA, Apple, Microsoft, etc.
    """
    stats = ingestion.ingest_demo_companies()
    return stats


@router.get("/ingest/targets", summary="List available ingestion targets")
def list_ingestion_targets() -> Dict[str, Any]:
    """
    Get list of pre-defined companies available for ingestion.
    """
    return {
        "targets": ingestion.DEMO_COMPANIES,
        "count": len(ingestion.DEMO_COMPANIES),
    }
