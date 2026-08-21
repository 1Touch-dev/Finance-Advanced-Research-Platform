"""
Graph Ingestion Service
══════════════════════════════════════════════════════════════════════════════

Extracts entities and relationships from existing data sources and loads
them into the Intelligence Graph Store.

Sources:
- SEC EDGAR: Companies, executives, board members, insider transactions
- FEC (via OpenSecrets connector): Political donations, PACs
- USASpending/FPDS: Government contracts, awards

This implements the "automatic graph expansion" James envisioned.
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.services import entity_graph_service as graph
from app.connectors.sec_edgar_connector import (
    get_company_submissions,
    get_insider_transactions,
)
from app.connectors.opensecrets_connector import (
    get_pac_contributions,
    get_executive_donations,
)
from app.connectors.fpds_connector import (
    resolve_recipient_uei,
    fetch_usaspending_full,
)

log = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SEC EDGAR INGESTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def ingest_sec_company(cik: str, company_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Ingest a company and its network from SEC EDGAR.

    Extracts:
    - Company entity
    - Insider transactions (ownership edges from Form 4)
    """
    stats = {
        "entities_added": 0,
        "edges_added": 0,
        "errors": [],
    }

    cik = cik.zfill(10)

    try:
        # Get company info from SEC
        submissions = get_company_submissions(cik)
        company_name = company_name or submissions.get("name", f"Company {cik}")
        ticker = submissions.get("tickers", [""])[0] if submissions.get("tickers") else None

        # Create company entity
        company_id = f"org:sec-{cik}"
        identifiers = {"CIK": cik}
        if ticker:
            identifiers["ticker"] = ticker

        graph.add_entity(
            entity_id=company_id,
            kind="org",
            name=company_name,
            identifiers=identifiers,
            meta={
                "source": "SEC EDGAR",
                "sic": submissions.get("sic", ""),
                "ein": submissions.get("ein", ""),
            },
        )
        stats["entities_added"] += 1

        # Get insider transactions (Form 4 filings)
        try:
            insiders = get_insider_transactions(cik, max_filings=50)
            for txn in insiders.get("transactions", []):
                person_name = txn.get("owner_name", "Unknown")
                person_id = _create_person_id(person_name)

                # Ensure person exists
                if not graph.get_entity(person_id):
                    graph.add_entity(
                        entity_id=person_id,
                        kind="person",
                        name=person_name,
                        meta={"source": "SEC Form 4"},
                    )
                    stats["entities_added"] += 1

                # Add ownership relationship
                if txn.get("transaction_type") in ["P", "A"]:  # Purchase or Award
                    edge_id = f"edge:{person_id}-owns-{company_id}-{txn.get('filing_date', '')}"
                    try:
                        graph.add_edge(
                            edge_id=edge_id,
                            src_entity_id=person_id,
                            dst_entity_id=company_id,
                            relationship_type="owns",
                            confidence_tier="CONFIRMED",
                            evidence_refs=[{
                                "document_id": f"sec-form4-{txn.get('filing_date', '')}",
                                "source_name": "SEC Form 4",
                                "source_url": txn.get("filing_url", ""),
                            }],
                            as_of=datetime.strptime(txn.get("filing_date", "2000-01-01"), "%Y-%m-%d"),
                            source_name="SEC EDGAR",
                            meta={
                                "shares": txn.get("shares", 0),
                                "price": txn.get("price", 0),
                            },
                        )
                        stats["edges_added"] += 1
                    except ValueError as e:
                        pass  # Edge might already exist

        except Exception as e:
            stats["errors"].append(f"Insider transactions: {str(e)}")

    except Exception as e:
        stats["errors"].append(f"Company {cik}: {str(e)}")
        log.error("Error ingesting SEC company %s: %s", cik, e)

    return stats


def ingest_sec_network(ciks: List[str]) -> Dict[str, Any]:
    """Ingest multiple SEC companies."""
    total_stats = {
        "companies_processed": 0,
        "entities_added": 0,
        "edges_added": 0,
        "errors": [],
    }

    for cik in ciks:
        stats = ingest_sec_company(cik)
        total_stats["companies_processed"] += 1
        total_stats["entities_added"] += stats["entities_added"]
        total_stats["edges_added"] += stats["edges_added"]
        total_stats["errors"].extend(stats["errors"])

    return total_stats


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FEC / POLITICAL INGESTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def ingest_fec_contributions(
    entity_name: str,
    entity_id: Optional[str] = None,
    cycle: int = 2024,
) -> Dict[str, Any]:
    """
    Ingest FEC political contributions for an entity.

    Creates donation edges between people/PACs and candidates/committees.
    """
    stats = {
        "entities_added": 0,
        "edges_added": 0,
        "total_contributions": 0,
        "errors": [],
    }

    entity_id = entity_id or f"org:{_normalize_id(entity_name)}"

    try:
        # Get PAC contributions for the company
        pac_contribs = get_pac_contributions(entity_name, cycle)

        for contrib in pac_contribs.get("contributions", []):
            # Create recipient entity (candidate/committee)
            recipient_id = f"pac:fec-{contrib.get('committee_id', 'unknown')}"

            if not graph.get_entity(recipient_id):
                graph.add_entity(
                    entity_id=recipient_id,
                    kind="pac",
                    name=contrib.get("committee_name", "Unknown Committee"),
                    identifiers={"FEC": contrib.get("committee_id", "")},
                    meta={"source": "FEC"},
                )
                stats["entities_added"] += 1

            # Create donation edge
            edge_id = f"edge:{entity_id}-donates_to-{recipient_id}-{contrib.get('date', '')}"
            try:
                graph.add_edge(
                    edge_id=edge_id,
                    src_entity_id=entity_id,
                    dst_entity_id=recipient_id,
                    relationship_type="donates_to",
                    confidence_tier="CONFIRMED",
                    evidence_refs=[{
                        "document_id": f"fec-{contrib.get('fec_id', '')}",
                        "source_name": "FEC Disclosure",
                        "source_url": f"https://www.fec.gov/data/receipts/?committee_id={contrib.get('committee_id', '')}",
                    }],
                    as_of=datetime.strptime(contrib.get("date", "2000-01-01"), "%Y-%m-%d") if contrib.get("date") else None,
                    source_name="FEC",
                    meta={
                        "amount": contrib.get("amount", 0),
                        "cycle": cycle,
                    },
                )
                stats["edges_added"] += 1
                stats["total_contributions"] += contrib.get("amount", 0)
            except ValueError:
                pass  # Edge exists

    except Exception as e:
        stats["errors"].append(str(e))
        log.error("Error ingesting FEC data for %s: %s", entity_name, e)

    return stats


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# USASPENDING / GOVERNMENT CONTRACTS INGESTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def ingest_government_contracts(
    entity_name: str,
    entity_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ingest federal government contracts for an entity.

    Creates:
    - Agency entities
    - Contract award edges (awarded_to)
    """
    stats = {
        "entities_added": 0,
        "edges_added": 0,
        "total_awards": 0,
        "total_value": 0.0,
        "errors": [],
    }

    entity_id = entity_id or f"org:{_normalize_id(entity_name)}"

    try:
        # Resolve UEI/DUNS
        recipient = resolve_recipient_uei(entity_name)
        if not recipient:
            log.info("No USASpending recipient found for %s", entity_name)
            return stats

        # Get awards using USASpending API
        awards_data = fetch_usaspending_full(entity_name, max_results=100)

        for award in awards_data.get("contracts", []):
            # Create agency entity
            agency_name = award.get("awarding_agency", "Unknown Agency")
            agency_id = f"agency:{_normalize_id(agency_name)}"

            if not graph.get_entity(agency_id):
                graph.add_entity(
                    entity_id=agency_id,
                    kind="agency",
                    name=agency_name,
                    meta={
                        "sub_agency": award.get("awarding_sub_agency", ""),
                        "source": "USASpending",
                    },
                )
                stats["entities_added"] += 1

            # Create contract award edge
            contract_id = award.get("award_id", "unknown")
            edge_id = f"edge:{agency_id}-awarded_to-{entity_id}-{contract_id}"

            try:
                graph.add_edge(
                    edge_id=edge_id,
                    src_entity_id=agency_id,
                    dst_entity_id=entity_id,
                    relationship_type="awarded_to",
                    confidence_tier="CONFIRMED",
                    evidence_refs=[{
                        "document_id": f"usaspending-{contract_id}",
                        "source_name": "USASpending.gov",
                        "source_url": f"https://www.usaspending.gov/award/{contract_id}",
                    }],
                    as_of=datetime.strptime(award.get("start_date", "2000-01-01"), "%Y-%m-%d") if award.get("start_date") else None,
                    valid_to=datetime.strptime(award.get("end_date", "2100-01-01"), "%Y-%m-%d") if award.get("end_date") else None,
                    source_name="USASpending",
                    meta={
                        "award_type": award.get("award_type", ""),
                        "description": award.get("description", ""),
                        "total_value": award.get("total_value", 0),
                        "naics": award.get("naics_code", ""),
                    },
                )
                stats["edges_added"] += 1
                stats["total_awards"] += 1
                stats["total_value"] += award.get("total_value", 0)
            except ValueError:
                pass  # Edge exists

    except Exception as e:
        stats["errors"].append(str(e))
        log.error("Error ingesting government contracts for %s: %s", entity_name, e)

    return stats


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COMBINED INGESTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def ingest_entity_full(
    entity_name: str,
    cik: Optional[str] = None,
    include_sec: bool = True,
    include_fec: bool = True,
    include_contracts: bool = True,
) -> Dict[str, Any]:
    """
    Perform full ingestion of an entity from all available sources.

    This is the main entry point for populating the graph with an entity's
    complete network.
    """
    entity_id = f"org:{_normalize_id(entity_name)}"

    total_stats = {
        "entity_id": entity_id,
        "entity_name": entity_name,
        "sec": None,
        "fec": None,
        "contracts": None,
        "total_entities": 0,
        "total_edges": 0,
        "errors": [],
    }

    # Ensure base entity exists
    if not graph.get_entity(entity_id):
        graph.add_entity(
            entity_id=entity_id,
            kind="org",
            name=entity_name,
            identifiers={"CIK": cik} if cik else {},
        )
        total_stats["total_entities"] += 1

    # SEC ingestion
    if include_sec and cik:
        sec_stats = ingest_sec_company(cik, entity_name)
        total_stats["sec"] = sec_stats
        total_stats["total_entities"] += sec_stats["entities_added"]
        total_stats["total_edges"] += sec_stats["edges_added"]
        total_stats["errors"].extend(sec_stats["errors"])

    # FEC ingestion
    if include_fec:
        fec_stats = ingest_fec_contributions(entity_name, entity_id)
        total_stats["fec"] = fec_stats
        total_stats["total_entities"] += fec_stats["entities_added"]
        total_stats["total_edges"] += fec_stats["edges_added"]
        total_stats["errors"].extend(fec_stats["errors"])

    # Government contracts
    if include_contracts:
        contract_stats = ingest_government_contracts(entity_name, entity_id)
        total_stats["contracts"] = contract_stats
        total_stats["total_entities"] += contract_stats["entities_added"]
        total_stats["total_edges"] += contract_stats["edges_added"]
        total_stats["errors"].extend(contract_stats["errors"])

    return total_stats


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELPER FUNCTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _normalize_id(name: str) -> str:
    """Normalize a name to create an ID-safe string."""
    import re
    # Remove special characters, convert to lowercase, replace spaces with hyphens
    clean = re.sub(r'[^\w\s-]', '', name.lower())
    clean = re.sub(r'[\s_]+', '-', clean)
    return clean.strip('-')


def _create_person_id(name: str) -> str:
    """Create a person ID from a name."""
    return f"person:{_normalize_id(name)}"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EXAMPLE INGESTION TARGETS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Major tech companies for demonstration
DEMO_COMPANIES = [
    {"name": "Tesla, Inc.", "cik": "0001318605"},
    {"name": "NVIDIA Corporation", "cik": "0001045810"},
    {"name": "Apple Inc.", "cik": "0000320193"},
    {"name": "Microsoft Corporation", "cik": "0000789019"},
    {"name": "Amazon.com, Inc.", "cik": "0001018724"},
    {"name": "Alphabet Inc.", "cik": "0001652044"},
    {"name": "Meta Platforms, Inc.", "cik": "0001326801"},
    {"name": "Palantir Technologies Inc.", "cik": "0001321655"},
    {"name": "SpaceX", "cik": None},  # Private
]


def ingest_demo_companies() -> Dict[str, Any]:
    """Ingest demo companies for testing the graph."""
    results = []
    for company in DEMO_COMPANIES:
        stats = ingest_entity_full(
            entity_name=company["name"],
            cik=company["cik"],
            include_sec=bool(company["cik"]),
            include_fec=True,
            include_contracts=True,
        )
        results.append(stats)

    return {
        "companies_ingested": len(results),
        "results": results,
    }
