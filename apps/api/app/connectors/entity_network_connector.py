"""
Entity Network & Swarm Intelligence Connector
────────────────────────────────────────────────────────────────────────────
Deep entity network analysis for investigative research:
  - Recursive entity discovery ("swarm" research)
  - Family network mapping (spouses, children, holding companies)
  - Cross-firm employee/board/advisor analysis
  - Corporate entity resolution (subsidiaries, DBAs, holding cos)
  - Related party transaction detection
  - Multi-hop relationship mapping

This connector implements James's vision:
  "For every entity discovered, find related entities"
  "Understand that families use their wives, kids, etc to create
   other corporate entities or investments"
  "Analyze all employees that have worked at multiple top firms"

Usage:
    from app.connectors.entity_network_connector import (
        build_entity_network,
        discover_family_network,
        find_cross_firm_connections,
    )
    network = build_entity_network("Jensen Huang", entity_type="person", depth=2)
"""
import os
import re
import time
import logging
import requests
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# SEC EDGAR headers
SEC_HEADERS = {"User-Agent": os.getenv("SEC_USER_AGENT", "FinanceIntelPlatform/1.0 research@example.com")}

# Common family relationship indicators
FAMILY_INDICATORS = [
    "spouse", "wife", "husband", "son", "daughter", "child", "parent",
    "mother", "father", "brother", "sister", "sibling", "cousin",
    "in-law", "mother-in-law", "father-in-law", "family", "relative",
    "trust", "estate", "heir", "beneficiary",
]

# Corporate entity type indicators
HOLDING_INDICATORS = [
    "holdings", "holding", "investments", "capital", "ventures",
    "partners", "partnership", "llc", "lp", "trust", "foundation",
    "family office", "management", "advisors", "associates",
]

# Top firms for cross-firm analysis
TOP_FIRMS = [
    "Goldman Sachs", "Morgan Stanley", "JP Morgan", "JPMorgan",
    "BlackRock", "Blackstone", "KKR", "Carlyle", "Apollo",
    "Berkshire Hathaway", "Citadel", "Two Sigma", "DE Shaw",
    "Bridgewater", "Renaissance", "Point72", "Millennium",
    "McKinsey", "Bain", "BCG", "Boston Consulting",
    "Google", "Apple", "Microsoft", "Amazon", "Meta", "Facebook",
    "NVIDIA", "Tesla", "Intel", "AMD", "Qualcomm", "Broadcom",
    "Sequoia", "Andreessen Horowitz", "a16z", "Accel", "Kleiner Perkins",
    "Greylock", "Benchmark", "GV", "Tiger Global", "Coatue",
]


def _normalize_name(name: str) -> str:
    """Normalize a person or company name for matching."""
    if not name:
        return ""
    normalized = name.lower().strip()
    # Remove common suffixes
    for suffix in [" jr", " jr.", " sr", " sr.", " ii", " iii", " iv",
                   " inc", " inc.", " corp", " corp.", " llc", " lp",
                   " ltd", " ltd.", " co", " co.", " & co", " & co."]:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)].strip()
    return normalized


def _extract_surname(full_name: str) -> str:
    """Extract likely surname from a full name."""
    parts = full_name.strip().split()
    if not parts:
        return ""
    # Handle "LastName, FirstName" format
    if "," in full_name:
        return parts[0].replace(",", "").lower()
    # Otherwise assume last word is surname
    return parts[-1].lower()


def _detect_family_relationship(name1: str, name2: str, context: str = "") -> Dict[str, Any]:
    """
    Detect potential family relationship between two names.

    Returns dict with relationship type and confidence if detected.
    """
    surname1 = _extract_surname(name1)
    surname2 = _extract_surname(name2)

    result = {
        "detected": False,
        "relationship_type": None,
        "confidence": 0.0,
        "reason": "",
    }

    # Same surname check
    if surname1 and surname2 and surname1 == surname2:
        result["detected"] = True
        result["relationship_type"] = "same_surname"
        result["confidence"] = 0.5
        result["reason"] = f"Shared surname: {surname1}"

    # Check context for family indicators
    context_lower = context.lower()
    for indicator in FAMILY_INDICATORS:
        if indicator in context_lower:
            result["detected"] = True
            result["relationship_type"] = indicator
            result["confidence"] = 0.8
            result["reason"] = f"Context contains '{indicator}'"
            break

    return result


def _detect_holding_company(entity_name: str, related_person: str = "") -> Dict[str, Any]:
    """
    Detect if an entity is likely a personal holding company.

    Checks for patterns like:
    - [Surname] Holdings LLC
    - [Name] Family Trust
    - [Initials] Capital Partners
    """
    name_lower = entity_name.lower()

    result = {
        "is_holding_company": False,
        "holding_type": None,
        "confidence": 0.0,
        "linked_to_person": None,
    }

    # Check for holding indicators
    for indicator in HOLDING_INDICATORS:
        if indicator in name_lower:
            result["is_holding_company"] = True
            result["holding_type"] = indicator
            result["confidence"] = 0.6

            # Check if it contains a person's surname
            if related_person:
                surname = _extract_surname(related_person)
                if surname and surname in name_lower:
                    result["linked_to_person"] = related_person
                    result["confidence"] = 0.9

            break

    return result


def _search_sec_efts(query: str, forms: str = "", limit: int = 50) -> List[Dict[str, Any]]:
    """
    Search SEC EDGAR EFTS for entities and filings.

    Args:
        query: Search query (company or person name)
        forms: Comma-separated form types (e.g., "4,SC 13D,SC 13G")
        limit: Maximum results

    Returns:
        List of search results with filing metadata.
    """
    results = []

    try:
        params = {
            "q": f'"{query}"',
            "dateRange": "custom",
            "startdt": "2015-01-01",
            "enddt": datetime.now().strftime("%Y-%m-%d"),
        }
        if forms:
            params["forms"] = forms

        resp = requests.get(
            "https://efts.sec.gov/LATEST/search-index",
            params=params,
            headers=SEC_HEADERS,
            timeout=20,
        )

        if resp.ok:
            data = resp.json()
            hits = data.get("hits", {}).get("hits", [])[:limit]

            for hit in hits:
                src = hit.get("_source", {})
                names = src.get("display_names", [])

                results.append({
                    "entity_name": names[0].split("(CIK")[0].strip() if names else query,
                    "cik": src.get("ciks", [""])[0] if src.get("ciks") else "",
                    "form_type": src.get("form", ""),
                    "filing_date": src.get("file_date", ""),
                    "description": src.get("file_description", ""),
                    "accession": hit.get("_id", ""),
                })

    except Exception as e:
        logger.warning("SEC EFTS search failed for '%s': %s", query, e)

    return results


def _search_related_filings(entity_name: str, entity_type: str = "person") -> Dict[str, Any]:
    """
    Search for SEC filings that mention or relate to an entity.

    For persons: Form 4, Schedule 13D/G, DEF 14A proxy statements
    For companies: 10-K, 10-Q, 8-K, proxy statements
    """
    result = {
        "entity_name": entity_name,
        "entity_type": entity_type,
        "direct_filings": [],
        "mentioned_in": [],
        "related_entities_found": [],
    }

    if entity_type == "person":
        # Person: look for Form 4, beneficial ownership, proxy mentions
        forms = "4,SC 13D,SC 13G,DEF 14A"
    else:
        # Company: look for key filings
        forms = "10-K,10-Q,8-K,DEF 14A,SC 13D"

    filings = _search_sec_efts(entity_name, forms=forms, limit=100)

    for filing in filings:
        # Check if entity is the filer or just mentioned
        filer_name = _normalize_name(filing.get("entity_name", ""))
        search_name = _normalize_name(entity_name)

        if search_name in filer_name or filer_name in search_name:
            result["direct_filings"].append(filing)
        else:
            result["mentioned_in"].append(filing)
            # Extract the other entity as related
            if filing.get("entity_name"):
                result["related_entities_found"].append({
                    "name": filing["entity_name"],
                    "relationship": f"mentioned_in_{filing.get('form_type', 'filing')}",
                    "filing_date": filing.get("filing_date", ""),
                })

    return result


def discover_family_network(
    person_name: str,
    known_associations: List[str] = None,
    search_depth: int = 1,
) -> Dict[str, Any]:
    """
    Discover family network for a person.

    Searches for:
    - Same surname entities in SEC filings
    - Family trusts and holding companies
    - Beneficial ownership connections
    - Proxy statement disclosures

    Args:
        person_name: Full name of the person to research
        known_associations: List of known company associations
        search_depth: How many hops to follow (1-3)

    Returns:
        Family network map with relationships and entities.
    """
    known_associations = known_associations or []
    surname = _extract_surname(person_name)

    result = {
        "subject": person_name,
        "surname": surname,
        "family_members": [],
        "family_entities": [],  # Trusts, holding companies
        "beneficial_ownership": [],
        "related_party_transactions": [],
        "network_stats": {
            "family_members_found": 0,
            "family_entities_found": 0,
            "total_network_size": 0,
        },
    }

    if not surname or len(surname) < 3:
        result["error"] = "Could not extract valid surname"
        return result

    # 1. Search for same-surname filers
    logger.info("Searching for family network: %s (%s)", person_name, surname)

    surname_filings = _search_sec_efts(surname, forms="4,SC 13D,SC 13G", limit=200)

    seen_names: Set[str] = {_normalize_name(person_name)}

    for filing in surname_filings:
        filer = filing.get("entity_name", "")
        filer_surname = _extract_surname(filer)
        normalized = _normalize_name(filer)

        if normalized in seen_names:
            continue

        # Check if same surname
        if filer_surname == surname and normalized != _normalize_name(person_name):
            seen_names.add(normalized)

            # Is this a person or entity?
            holding_check = _detect_holding_company(filer, person_name)

            if holding_check["is_holding_company"]:
                result["family_entities"].append({
                    "entity_name": filer,
                    "entity_type": holding_check["holding_type"],
                    "confidence": holding_check["confidence"],
                    "linked_to": holding_check.get("linked_to_person"),
                    "first_seen": filing.get("filing_date", ""),
                    "filing_context": f"{filing.get('form_type', '')} filing",
                })
            else:
                # Likely a family member
                result["family_members"].append({
                    "name": filer,
                    "relationship": "same_surname",
                    "confidence": 0.5,
                    "first_seen": filing.get("filing_date", ""),
                    "filing_context": f"{filing.get('form_type', '')} filing",
                    "cik": filing.get("cik", ""),
                })

    # 2. Search for trusts/holdings with surname
    trust_searches = [
        f"{surname} trust",
        f"{surname} family",
        f"{surname} holdings",
        f"{surname} capital",
        f"{surname} investments",
    ]

    for search_term in trust_searches:
        trust_filings = _search_sec_efts(search_term, forms="SC 13D,SC 13G,4", limit=50)

        for filing in trust_filings:
            filer = filing.get("entity_name", "")
            normalized = _normalize_name(filer)

            if normalized in seen_names:
                continue

            holding_check = _detect_holding_company(filer, person_name)
            if holding_check["is_holding_company"]:
                seen_names.add(normalized)
                result["family_entities"].append({
                    "entity_name": filer,
                    "entity_type": holding_check["holding_type"],
                    "confidence": holding_check["confidence"],
                    "linked_to": holding_check.get("linked_to_person"),
                    "first_seen": filing.get("filing_date", ""),
                    "filing_context": f"{filing.get('form_type', '')} filing",
                })

    # 3. Look for related party disclosures in proxy statements
    if known_associations:
        for company in known_associations[:3]:  # Limit to top 3
            proxy_filings = _search_sec_efts(company, forms="DEF 14A", limit=5)
            for filing in proxy_filings:
                result["related_party_transactions"].append({
                    "company": company,
                    "filing_date": filing.get("filing_date", ""),
                    "accession": filing.get("accession", ""),
                    "note": "Proxy may contain related party transaction disclosures",
                })

    # Update stats
    result["network_stats"]["family_members_found"] = len(result["family_members"])
    result["network_stats"]["family_entities_found"] = len(result["family_entities"])
    result["network_stats"]["total_network_size"] = (
        len(result["family_members"]) + len(result["family_entities"])
    )

    return result


def find_cross_firm_connections(
    persons: List[str],
    target_firms: List[str] = None,
) -> Dict[str, Any]:
    """
    Find people who have worked at multiple top firms.

    Identifies the "revolving door" between major companies,
    PE firms, and government.

    Args:
        persons: List of person names to analyze
        target_firms: Optional list of specific firms to check

    Returns:
        Cross-firm connection analysis.
    """
    target_firms = target_firms or TOP_FIRMS

    result = {
        "persons_analyzed": persons,
        "target_firms": target_firms[:20],  # Limit display
        "cross_firm_connections": [],
        "firm_overlap_matrix": defaultdict(lambda: defaultdict(list)),
        "key_connectors": [],  # People at 3+ top firms
        "summary": {
            "total_analyzed": len(persons),
            "with_cross_firm": 0,
            "avg_firms_per_person": 0,
        },
    }

    person_firms: Dict[str, List[Dict[str, Any]]] = {}

    for person in persons:
        logger.info("Analyzing cross-firm connections for: %s", person)
        firms_found = []

        # Search SEC for this person's filings
        filings = _search_sec_efts(person, forms="4,DEF 14A,SC 13D", limit=100)

        for filing in filings:
            filer = filing.get("entity_name", "")

            # Check if filer matches any target firm
            filer_lower = filer.lower()
            for firm in target_firms:
                if firm.lower() in filer_lower or filer_lower in firm.lower():
                    firms_found.append({
                        "firm": firm,
                        "role_context": filer,
                        "filing_type": filing.get("form_type", ""),
                        "filing_date": filing.get("filing_date", ""),
                    })
                    break

        # Deduplicate firms
        seen_firms: Set[str] = set()
        unique_firms = []
        for f in firms_found:
            if f["firm"] not in seen_firms:
                seen_firms.add(f["firm"])
                unique_firms.append(f)

        if len(unique_firms) >= 2:
            person_firms[person] = unique_firms
            result["cross_firm_connections"].append({
                "person": person,
                "firms": unique_firms,
                "firm_count": len(unique_firms),
            })

            # Update overlap matrix
            for i, f1 in enumerate(unique_firms):
                for f2 in unique_firms[i+1:]:
                    result["firm_overlap_matrix"][f1["firm"]][f2["firm"]].append(person)

    # Identify key connectors (3+ firms)
    result["key_connectors"] = [
        conn for conn in result["cross_firm_connections"]
        if conn["firm_count"] >= 3
    ]
    result["key_connectors"].sort(key=lambda x: x["firm_count"], reverse=True)

    # Summary stats
    result["summary"]["with_cross_firm"] = len(result["cross_firm_connections"])
    if persons:
        total_firms = sum(len(pf) for pf in person_firms.values())
        result["summary"]["avg_firms_per_person"] = round(
            total_firms / len(person_firms) if person_firms else 0, 1
        )

    return result


def build_entity_network(
    seed_entity: str,
    entity_type: str = "person",  # "person" or "org"
    depth: int = 2,
    max_nodes: int = 100,
    known_associations: List[str] = None,
) -> Dict[str, Any]:
    """
    Build comprehensive entity network using swarm discovery.

    Starting from a seed entity, recursively discover and map
    all related entities up to specified depth.

    Args:
        seed_entity: Starting person or organization name
        entity_type: "person" or "org"
        depth: How many hops to follow (1-3)
        max_nodes: Maximum entities to include
        known_associations: Known company/person associations

    Returns:
        Complete entity network with nodes and edges.
    """
    known_associations = known_associations or []

    result = {
        "seed_entity": seed_entity,
        "entity_type": entity_type,
        "depth": depth,
        "nodes": [],
        "edges": [],
        "clusters": {},  # Grouped by relationship type
        "family_network": {},
        "cross_firm_analysis": {},
        "holding_companies": [],
        "network_stats": {
            "total_nodes": 0,
            "total_edges": 0,
            "depth_reached": 0,
            "persons_found": 0,
            "orgs_found": 0,
        },
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    # Track visited entities to avoid cycles
    visited: Set[str] = set()
    node_list: List[Dict[str, Any]] = []
    edge_list: List[Dict[str, Any]] = []

    # Queue for BFS traversal: (entity_name, entity_type, current_depth, parent_name)
    queue: List[Tuple[str, str, int, Optional[str]]] = [
        (seed_entity, entity_type, 0, None)
    ]

    # Add seed as first node
    node_list.append({
        "id": _normalize_name(seed_entity),
        "name": seed_entity,
        "type": entity_type,
        "depth": 0,
        "is_seed": True,
    })
    visited.add(_normalize_name(seed_entity))

    while queue and len(node_list) < max_nodes:
        current_entity, current_type, current_depth, parent = queue.pop(0)

        if current_depth >= depth:
            continue

        logger.info("Swarm discovering at depth %d: %s", current_depth, current_entity)

        # Search for related filings
        related = _search_related_filings(current_entity, current_type)

        for rel_entity in related.get("related_entities_found", []):
            rel_name = rel_entity.get("name", "")
            rel_normalized = _normalize_name(rel_name)

            if rel_normalized in visited or not rel_name:
                continue
            if len(node_list) >= max_nodes:
                break

            visited.add(rel_normalized)

            # Determine entity type
            holding_check = _detect_holding_company(rel_name)
            rel_type = "holding_company" if holding_check["is_holding_company"] else "unknown"

            # Add node
            node_list.append({
                "id": rel_normalized,
                "name": rel_name,
                "type": rel_type,
                "depth": current_depth + 1,
                "discovered_via": rel_entity.get("relationship", ""),
            })

            # Add edge
            edge_list.append({
                "source": _normalize_name(current_entity),
                "target": rel_normalized,
                "relationship": rel_entity.get("relationship", "related"),
                "filing_date": rel_entity.get("filing_date", ""),
            })

            # Queue for further exploration if not at max depth
            if current_depth + 1 < depth:
                queue.append((rel_name, rel_type, current_depth + 1, current_entity))

        result["network_stats"]["depth_reached"] = max(
            result["network_stats"]["depth_reached"], current_depth + 1
        )

    # If seed is a person, also run family network discovery
    if entity_type == "person":
        result["family_network"] = discover_family_network(
            seed_entity, known_associations
        )

        # Add family members to network
        for member in result["family_network"].get("family_members", []):
            member_norm = _normalize_name(member.get("name", ""))
            if member_norm not in visited:
                visited.add(member_norm)
                node_list.append({
                    "id": member_norm,
                    "name": member.get("name"),
                    "type": "family_member",
                    "depth": 1,
                    "relationship": member.get("relationship"),
                })
                edge_list.append({
                    "source": _normalize_name(seed_entity),
                    "target": member_norm,
                    "relationship": "family",
                })

        # Add family entities
        for entity in result["family_network"].get("family_entities", []):
            entity_norm = _normalize_name(entity.get("entity_name", ""))
            if entity_norm not in visited:
                visited.add(entity_norm)
                node_list.append({
                    "id": entity_norm,
                    "name": entity.get("entity_name"),
                    "type": "family_entity",
                    "entity_subtype": entity.get("entity_type"),
                    "depth": 1,
                })
                edge_list.append({
                    "source": _normalize_name(seed_entity),
                    "target": entity_norm,
                    "relationship": "controls",
                })
                result["holding_companies"].append(entity)

    # Finalize results
    result["nodes"] = node_list
    result["edges"] = edge_list
    result["network_stats"]["total_nodes"] = len(node_list)
    result["network_stats"]["total_edges"] = len(edge_list)
    result["network_stats"]["persons_found"] = len([
        n for n in node_list if n.get("type") in ("person", "family_member")
    ])
    result["network_stats"]["orgs_found"] = len([
        n for n in node_list if n.get("type") in ("org", "holding_company", "family_entity")
    ])

    # Cluster by relationship type
    for edge in edge_list:
        rel_type = edge.get("relationship", "other")
        if rel_type not in result["clusters"]:
            result["clusters"][rel_type] = []
        result["clusters"][rel_type].append({
            "source": edge["source"],
            "target": edge["target"],
        })

    return result


def analyze_board_interlocks(
    company_boards: Dict[str, List[str]],
) -> Dict[str, Any]:
    """
    Analyze board member overlaps across multiple companies.

    Args:
        company_boards: Dict mapping company name to list of board member names

    Returns:
        Board interlock analysis with shared directors.
    """
    result = {
        "companies_analyzed": list(company_boards.keys()),
        "interlocks": [],
        "interlock_matrix": {},
        "key_connectors": [],  # People on 3+ boards
        "summary": {
            "total_unique_directors": 0,
            "directors_on_multiple_boards": 0,
            "max_boards_per_person": 0,
        },
    }

    # Normalize and track directors
    director_boards: Dict[str, List[str]] = defaultdict(list)

    for company, directors in company_boards.items():
        for director in directors:
            normalized = _normalize_name(director)
            director_boards[normalized].append(company)

    # Find interlocks
    for director, companies in director_boards.items():
        if len(companies) >= 2:
            result["interlocks"].append({
                "director": director,
                "companies": companies,
                "board_count": len(companies),
            })

    # Sort by number of boards
    result["interlocks"].sort(key=lambda x: x["board_count"], reverse=True)

    # Key connectors (3+ boards)
    result["key_connectors"] = [
        i for i in result["interlocks"] if i["board_count"] >= 3
    ]

    # Build interlock matrix (company x company)
    companies = list(company_boards.keys())
    for i, co1 in enumerate(companies):
        result["interlock_matrix"][co1] = {}
        for co2 in companies:
            if co1 == co2:
                result["interlock_matrix"][co1][co2] = len(company_boards.get(co1, []))
            else:
                shared = []
                for director in director_boards.values():
                    if co1 in director and co2 in director:
                        shared.append(director)
                result["interlock_matrix"][co1][co2] = len(shared)

    # Summary
    result["summary"]["total_unique_directors"] = len(director_boards)
    result["summary"]["directors_on_multiple_boards"] = len([
        d for d, cos in director_boards.items() if len(cos) >= 2
    ])
    if director_boards:
        result["summary"]["max_boards_per_person"] = max(
            len(cos) for cos in director_boards.values()
        )

    return result


def detect_related_party_entities(
    person_name: str,
    company_name: str,
) -> Dict[str, Any]:
    """
    Detect entities that may be related parties for SEC disclosure purposes.

    Searches for:
    - Family member entities
    - Personal holding companies
    - Entities with similar names
    - Entities appearing in same filings

    Args:
        person_name: Person to analyze
        company_name: Their primary company association

    Returns:
        Related party analysis.
    """
    result = {
        "person": person_name,
        "company": company_name,
        "potential_related_parties": [],
        "holding_companies": [],
        "family_controlled_entities": [],
        "flags": [],
    }

    surname = _extract_surname(person_name)

    # Search for surname-based entities
    searches = [
        f"{surname} holdings",
        f"{surname} investments",
        f"{surname} family",
        f"{surname} trust",
        f"{surname} capital",
        f"{surname} ventures",
        f"{surname} partners",
    ]

    seen: Set[str] = set()

    for search in searches:
        filings = _search_sec_efts(search, forms="SC 13D,SC 13G,4", limit=30)

        for filing in filings:
            entity = filing.get("entity_name", "")
            normalized = _normalize_name(entity)

            if normalized in seen:
                continue
            seen.add(normalized)

            holding_check = _detect_holding_company(entity, person_name)

            if holding_check["is_holding_company"]:
                entry = {
                    "entity_name": entity,
                    "entity_type": holding_check["holding_type"],
                    "confidence": holding_check["confidence"],
                    "first_filing": filing.get("filing_date", ""),
                    "filing_type": filing.get("form_type", ""),
                }

                if holding_check.get("linked_to_person"):
                    result["family_controlled_entities"].append(entry)
                    result["flags"].append({
                        "severity": "HIGH",
                        "detail": f"Potential family-controlled entity: {entity}",
                    })
                else:
                    result["holding_companies"].append(entry)

                result["potential_related_parties"].append(entry)

    return result


# ── Convenience Exports ──────────────────────────────────────────────────────

def build_network(seed: str, entity_type: str = "person", depth: int = 2) -> Dict[str, Any]:
    """Build entity network from seed."""
    return build_entity_network(seed, entity_type=entity_type, depth=depth)


def family_network(person: str, associations: List[str] = None) -> Dict[str, Any]:
    """Discover family network for a person."""
    return discover_family_network(person, known_associations=associations)


def cross_firm_analysis(persons: List[str], firms: List[str] = None) -> Dict[str, Any]:
    """Analyze cross-firm connections."""
    return find_cross_firm_connections(persons, target_firms=firms)


def board_interlocks(boards: Dict[str, List[str]]) -> Dict[str, Any]:
    """Analyze board interlocks."""
    return analyze_board_interlocks(boards)
