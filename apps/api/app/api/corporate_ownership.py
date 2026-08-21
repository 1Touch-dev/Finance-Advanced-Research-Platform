"""
Corporate Ownership Structure API — GLEIF/OpenCorporates/UK PSC Integration
─────────────────────────────────────────────────────────────────────────────
Endpoints for corporate ownership chain traversal, UBO detection, and
multi-registry cross-referencing.

Features:
- Ownership chain traversal (GLEIF LEI hierarchy)
- Corporate network graph building
- Ultimate Beneficial Owner (UBO) detection
- Cross-registry ownership reconciliation
- Private company intelligence aggregation
"""

from fastapi import APIRouter, Query
from typing import Optional

from app.connectors.private_company_connector import (
    search_gleif,
    fetch_gleif_relationships,
    fetch_gleif_entity_details,
    traverse_ownership_chain,
    build_corporate_network_graph,
    detect_ultimate_beneficial_owners,
    cross_reference_ownership,
    search_opencorporates,
    enrich_opencorporates,
    search_uk_companies,
    enrich_uk_company,
    fetch_private_company_intel_full,
)

router = APIRouter(prefix="/corporate-ownership", tags=["Corporate Ownership"])


# ── GLEIF LEI Endpoints ──────────────────────────────────────────────────────


@router.get("/gleif/search")
async def gleif_search(
    entity_name: str = Query(..., description="Entity name to search"),
    limit: int = Query(5, description="Maximum results"),
):
    """Search GLEIF for Legal Entity Identifiers matching the name."""
    results = search_gleif(entity_name, limit=limit)
    return {
        "entity_name": entity_name,
        "matches": results,
        "count": len(results),
    }


@router.get("/gleif/entity/{lei}")
async def gleif_entity_details(lei: str):
    """Get full entity details from GLEIF by LEI."""
    entity = fetch_gleif_entity_details(lei)
    if not entity:
        return {"error": f"Entity not found for LEI: {lei}"}
    return entity


@router.get("/gleif/relationships/{lei}")
async def gleif_relationships(lei: str):
    """Get parent/child/ultimate-parent relationships for a LEI."""
    return fetch_gleif_relationships(lei)


# ── Ownership Chain & Network Graph ──────────────────────────────────────────


@router.get("/chain/{lei}")
async def ownership_chain(
    lei: str,
    max_depth: int = Query(5, description="Maximum chain depth"),
):
    """
    Traverse the ownership chain upward from a LEI to find all parent
    entities up to the ultimate parent.
    """
    return traverse_ownership_chain(lei, max_depth=max_depth)


@router.get("/network/{lei}")
async def corporate_network(
    lei: str,
    include_children: bool = Query(True, description="Include subsidiaries"),
    max_depth: int = Query(3, description="Maximum traversal depth"),
):
    """
    Build a network graph of corporate relationships around an entity.
    Returns nodes (entities) and edges (relationships) for visualization.
    """
    return build_corporate_network_graph(
        lei,
        include_children=include_children,
        max_depth=max_depth
    )


@router.get("/chain/by-name")
async def ownership_chain_by_name(
    entity_name: str = Query(..., description="Entity name to search"),
    max_depth: int = Query(5, description="Maximum chain depth"),
):
    """
    Find LEI by name, then traverse ownership chain to ultimate parent.
    """
    gleif_results = search_gleif(entity_name, limit=1)
    if not gleif_results:
        return {
            "error": f"No GLEIF records found for: {entity_name}",
            "entity_name": entity_name,
        }

    lei = gleif_results[0]["lei"]
    chain = traverse_ownership_chain(lei, max_depth=max_depth)
    chain["search_entity_name"] = entity_name
    chain["matched_lei"] = lei
    return chain


# ── Ultimate Beneficial Owner (UBO) Detection ────────────────────────────────


@router.get("/ubo/{entity_name}")
async def detect_ubo(
    entity_name: str,
    jurisdiction: str = Query("", description="Jurisdiction code (e.g., 'uk', 'us')"),
):
    """
    Detect Ultimate Beneficial Owners by combining GLEIF, UK PSC,
    and OpenCorporates data.

    UBOs are natural persons who ultimately control an entity through
    direct or indirect ownership of 25%+ or other control mechanisms.
    """
    return detect_ultimate_beneficial_owners(entity_name, jurisdiction=jurisdiction)


# ── Cross-Registry Reconciliation ────────────────────────────────────────────


@router.get("/cross-reference/{entity_name}")
async def cross_reference(
    entity_name: str,
    jurisdiction: str = Query("", description="Jurisdiction code"),
):
    """
    Cross-reference ownership data across multiple registries (GLEIF,
    OpenCorporates, UK Companies House) to build a comprehensive
    ownership picture with confidence scores.
    """
    return cross_reference_ownership(entity_name, jurisdiction=jurisdiction)


# ── Private Company Intelligence ─────────────────────────────────────────────


@router.get("/private-intel/{entity_name}")
async def private_company_intel(
    entity_name: str,
    jurisdiction: str = Query("", description="Jurisdiction code"),
):
    """
    Full private company intelligence aggregation from all sources:
    OpenCorporates, GLEIF, UK Companies House, SEC Form D, FinCEN.
    """
    return fetch_private_company_intel_full(entity_name, jurisdiction=jurisdiction)


# ── OpenCorporates Endpoints ─────────────────────────────────────────────────


@router.get("/opencorporates/search")
async def opencorporates_search(
    company_name: str = Query(..., description="Company name to search"),
    jurisdiction: str = Query("", description="Jurisdiction code (e.g., 'us_de', 'gb')"),
    limit: int = Query(5, description="Maximum results"),
):
    """Search OpenCorporates global company registry."""
    results = search_opencorporates(company_name, jurisdiction=jurisdiction, limit=limit)
    return {
        "company_name": company_name,
        "jurisdiction": jurisdiction,
        "matches": results,
        "count": len(results),
    }


@router.get("/opencorporates/company/{jurisdiction}/{company_number}")
async def opencorporates_enrich(
    jurisdiction: str,
    company_number: str,
):
    """Get full company details from OpenCorporates including officers and filings."""
    return enrich_opencorporates(company_number, jurisdiction)


# ── UK Companies House Endpoints ─────────────────────────────────────────────


@router.get("/uk-companies-house/search")
async def uk_companies_search(
    company_name: str = Query(..., description="Company name to search"),
    limit: int = Query(5, description="Maximum results"),
):
    """Search UK Companies House registry."""
    results = search_uk_companies(company_name, limit=limit)
    return {
        "company_name": company_name,
        "matches": results,
        "count": len(results),
    }


@router.get("/uk-companies-house/company/{company_number}")
async def uk_company_details(company_number: str):
    """
    Get full UK company details including officers, filings, and
    Persons with Significant Control (PSC).
    """
    return enrich_uk_company(company_number)


@router.get("/uk-companies-house/psc/{company_number}")
async def uk_company_psc(company_number: str):
    """Get only the Persons with Significant Control for a UK company."""
    details = enrich_uk_company(company_number)
    return {
        "company_number": company_number,
        "company_name": details.get("name", ""),
        "persons_with_significant_control": details.get("persons_with_significant_control", []),
        "psc_count": len(details.get("persons_with_significant_control", [])),
    }


# ── Aggregate Analysis Endpoints ─────────────────────────────────────────────


@router.get("/full-analysis/{entity_name}")
async def full_ownership_analysis(
    entity_name: str,
    jurisdiction: str = Query("", description="Jurisdiction code"),
    include_network: bool = Query(True, description="Include network graph"),
):
    """
    Comprehensive ownership analysis combining all capabilities:
    - Private company intelligence
    - Ownership chain traversal
    - UBO detection
    - Cross-registry reconciliation
    - Network graph (optional)
    """
    # Get private company intel
    intel = fetch_private_company_intel_full(entity_name, jurisdiction=jurisdiction)

    # Get UBOs
    ubos = detect_ultimate_beneficial_owners(entity_name, jurisdiction=jurisdiction)

    # Get cross-reference data
    cross_ref = cross_reference_ownership(entity_name, jurisdiction=jurisdiction)

    # Get network graph if LEI found
    network = None
    if include_network and intel.get("gleif_matches"):
        lei = intel["gleif_matches"][0]["lei"]
        network = build_corporate_network_graph(lei, include_children=True, max_depth=2)

    return {
        "entity_name": entity_name,
        "jurisdiction": jurisdiction,
        "private_company_intel": intel,
        "ultimate_beneficial_owners": ubos,
        "cross_registry_analysis": cross_ref,
        "corporate_network": network,
        "summary": {
            "sources_found": cross_ref.get("sources_matched", 0),
            "confidence_score": cross_ref.get("confidence_score", 0),
            "ubo_count": ubos.get("ubo_count", 0),
            "has_gleif_record": bool(intel.get("gleif_matches")),
            "has_opencorporates": bool(intel.get("opencorporates_matches")),
            "has_uk_companies_house": bool(intel.get("uk_companies_house_matches")),
            "has_sec_form_d": bool(intel.get("sec_form_d_filings")),
        },
    }
