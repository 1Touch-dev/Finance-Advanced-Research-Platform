"""
Government Data API endpoints.
Covers: BEA (economic data), SAM.gov (contracts), Regulations.gov, GovInfo.
"""
from fastapi import APIRouter

from app.connectors.government_precedent_connector import (
    bea_get_data, bea_gdp, bea_state_income,
    sam_search_opportunities, sam_entity_search,
    regulations_search, regulations_docket,
    govinfo_search,
)

router = APIRouter(prefix="/government", tags=["Government Data"])


# ── BEA (Bureau of Economic Analysis) ─────────────────────────────────────────

@router.get("/bea/data")
def get_bea_data(dataset: str = "NIPA", table: str = "T10101",
                 frequency: str = "A", year: str = "2020,2021,2022,2023,2024"):
    """
    Fetch BEA economic data.

    Args:
        dataset: NIPA (national accounts), Regional, etc.
        table: T10101 (GDP), SAINC1 (state income), etc.
        frequency: A=Annual, Q=Quarterly
        year: Years (comma-separated or LAST5)
    """
    return bea_get_data(dataset, table, frequency, year)


@router.get("/bea/gdp")
def get_bea_gdp(years: str = "2020,2021,2022,2023,2024"):
    """Fetch GDP data from BEA."""
    return bea_gdp(years)


@router.get("/bea/state-income")
def get_bea_state_income(year: str = "LAST5"):
    """Fetch state personal income from BEA."""
    return bea_state_income(year)


# ── SAM.gov (System for Award Management) ─────────────────────────────────────

@router.get("/sam/opportunities")
def get_sam_opportunities(keywords: str = "", limit: int = 20, days_back: int = 30):
    """
    Search SAM.gov for federal contract opportunities.

    Args:
        keywords: Search keywords
        limit: Max results (default 20)
        days_back: Look back period in days (default 30)
    """
    return sam_search_opportunities(keywords, limit, days_back)


@router.get("/sam/entities")
def get_sam_entities(name: str, limit: int = 10):
    """
    Search for registered entities in SAM.gov.

    Args:
        name: Entity/company name to search
        limit: Max results
    """
    return sam_entity_search(name, limit)


# ── Regulations.gov ───────────────────────────────────────────────────────────

@router.get("/regulations/search")
def search_regulations(query: str = "", agency: str = "", limit: int = 20):
    """
    Search Regulations.gov for federal regulations and proposed rules.

    Args:
        query: Search keywords
        agency: Filter by agency (e.g., "EPA", "SEC", "FDA")
        limit: Max results
    """
    return regulations_search(query, agency, limit)


@router.get("/regulations/docket/{docket_id}")
def get_regulations_docket(docket_id: str):
    """Get details about a specific regulatory docket."""
    return regulations_docket(docket_id)


# ── GovInfo (Government Publishing Office) ────────────────────────────────────

@router.get("/govinfo/search")
def search_govinfo(query: str, collection: str = "FR", limit: int = 20):
    """
    Search GovInfo for federal government documents.

    Args:
        query: Search keywords
        collection: Document collection (FR=Federal Register, CFR, BILLS, etc.)
        limit: Max results
    """
    return govinfo_search(query, collection, limit)
