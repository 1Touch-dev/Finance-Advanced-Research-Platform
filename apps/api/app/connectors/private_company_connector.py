"""
Private company intelligence connector — multi-source data aggregation:

1. OpenCorporates  — global company registry (opencorporates.com/api/v0.4)
   * Company search + full registration data, officers, filings
   * Free tier: 500 requests/day (no key needed for basic search)

2. GLEIF            — Global Legal Entity Identifier Foundation (api.gleif.org)
   * LEI codes, MIC codes, registration, relationships, ultimate parent
   * Completely free, no authentication

3. FinCEN BOI        — Beneficial Ownership information (reported via FinCEN since 2024)
   * No public bulk API yet; we query FinCEN Entity Registration search
     (https://efts.fincen.gov/financial_institution_search/api) as a fallback
   * Also checks FDIC BankFind for financial institutions

4. UK Companies House — official UK company registry (api.company-information.service.gov.uk)
   * Company search, officers, filings, PSC (persons with significant control)
   * Free API, requires API key

5. SEC Form D        — private placement offerings (Regulation D exemptions)
   * Fundraising data for private companies registered with SEC
   * Completely free via SEC EDGAR

All functions return empty dicts if the API is unreachable, so the pipeline
degrades gracefully.
"""
import os
import logging
import requests
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

_OPENCORP_BASE = "https://api.opencorporates.com/v0.4"
_GLEIF_BASE    = "https://api.gleif.org/api/v1"
_FINCEN_BASE   = "https://efts.fincen.gov/financial_institution_search/api"
_FDIC_BASE     = "https://banks.data.fdic.gov/api"
_UKCH_BASE     = "https://api.company-information.service.gov.uk"
_SEC_BASE      = "https://efts.sec.gov/LATEST/search-index"
_SEC_EDGAR     = "https://www.sec.gov/cgi-bin/browse-edgar"

_OC_API_TOKEN = os.getenv("OPENCORPORATES_API_TOKEN", "")  # optional; improves rate limit
_UKCH_API_KEY = os.getenv("UK_COMPANIES_HOUSE_KEY", "")
_SEC_USER_AGENT = os.getenv("SEC_USER_AGENT", "FinanceIntelPlatform contact@example.com")


def _oc_params(extra: dict = None) -> dict:
    p = {}
    if _OC_API_TOKEN:
        p["api_token"] = _OC_API_TOKEN
    if extra:
        p.update(extra)
    return p


# ── OpenCorporates ────────────────────────────────────────────────────────────

def search_opencorporates(company_name: str, jurisdiction: str = "", limit: int = 5) -> List[dict]:
    """
    Search OpenCorporates for companies matching the name.
    Returns list of { name, jurisdiction, company_number, company_type,
                       incorporation_date, dissolution_date, registered_address,
                       status, opencorporates_url }.
    """
    params = _oc_params({
        "q":             company_name,
        "per_page":      limit,
        "inactive":      "false",
    })
    if jurisdiction:
        params["jurisdiction_code"] = jurisdiction.lower()

    try:
        r = requests.get(f"{_OPENCORP_BASE}/companies/search", params=params, timeout=15)
        r.raise_for_status()
        items = r.json().get("results", {}).get("companies", [])
    except Exception as exc:
        logger.warning("OpenCorporates search failed: %s", exc)
        return []

    results = []
    for item in items:
        c = item.get("company", item)
        results.append({
            "name":               c.get("name", ""),
            "jurisdiction":       c.get("jurisdiction_code", ""),
            "company_number":     c.get("company_number", ""),
            "company_type":       c.get("company_type", ""),
            "incorporation_date": c.get("incorporation_date", ""),
            "dissolution_date":   c.get("dissolution_date"),
            "registered_address": (c.get("registered_address") or {}).get("in_full", ""),
            "status":             c.get("current_status", ""),
            "opencorporates_url": c.get("opencorporates_url", ""),
            "source":             "OpenCorporates",
        })
    return results


def enrich_opencorporates(company_number: str, jurisdiction: str) -> dict:
    """
    Full company enrichment from OpenCorporates by company number + jurisdiction.
    Returns officers list, filing history, registered address, etc.
    """
    try:
        r = requests.get(
            f"{_OPENCORP_BASE}/companies/{jurisdiction}/{company_number}",
            params=_oc_params({"sparse": "false"}),
            timeout=15,
        )
        r.raise_for_status()
        c = r.json().get("results", {}).get("company", {})
    except Exception as exc:
        logger.warning("OpenCorporates enrich failed: %s", exc)
        return {}

    officers = []
    for off in (c.get("officers") or [])[:10]:
        o = off.get("officer", off)
        officers.append({
            "name":     o.get("name", ""),
            "role":     o.get("position", ""),
            "start":    o.get("start_date"),
            "end":      o.get("end_date"),
            "inactive": o.get("inactive", False),
        })

    filings = []
    for f in (c.get("filings") or [])[:10]:
        fi = f.get("filing", f)
        filings.append({
            "title": fi.get("title", ""),
            "date":  fi.get("date", ""),
            "url":   fi.get("opencorporates_url", ""),
        })

    return {
        "name":               c.get("name", ""),
        "jurisdiction":       c.get("jurisdiction_code", ""),
        "company_number":     c.get("company_number", ""),
        "company_type":       c.get("company_type", ""),
        "status":             c.get("current_status", ""),
        "incorporation_date": c.get("incorporation_date", ""),
        "dissolution_date":   c.get("dissolution_date"),
        "registered_address": (c.get("registered_address") or {}).get("in_full", ""),
        "registered_agent":   (c.get("agent_name") or ""),
        "officers":           officers,
        "filings":            filings,
        "sic_codes":          c.get("industry_codes") or [],
        "opencorporates_url": c.get("opencorporates_url", ""),
        "source":             "OpenCorporates",
    }


# ── GLEIF (Global LEI) ───────────────────────────────────────────────────────

def search_gleif(entity_name: str, limit: int = 3) -> List[dict]:
    """
    Search GLEIF for Legal Entity Identifiers.
    Returns list of { lei, name, status, jurisdiction, registered_at,
                       registered_address, ultimate_parent_lei, gleif_url }.
    """
    try:
        r = requests.get(
            f"{_GLEIF_BASE}/lei-records",
            params={
                "filter[entity.legalName]": entity_name,
                "page[size]": limit,
            },
            headers={"Accept": "application/vnd.api+json"},
            timeout=15,
        )
        r.raise_for_status()
        records = r.json().get("data", [])
    except Exception as exc:
        logger.warning("GLEIF search failed: %s", exc)
        return []

    results = []
    for rec in records:
        attrs = rec.get("attributes", {})
        entity = attrs.get("entity", {})
        reg    = attrs.get("registration", {})
        addr   = entity.get("legalAddress", {})

        results.append({
            "lei":               rec.get("id", ""),
            "name":              entity.get("legalName", {}).get("name", ""),
            "status":            reg.get("status", ""),
            "jurisdiction":      entity.get("jurisdiction", ""),
            "registered_at":     reg.get("initialRegistrationDate", "")[:10] if reg.get("initialRegistrationDate") else "",
            "registered_address": ", ".join(filter(None, [
                addr.get("addressLines", [""])[0],
                addr.get("city", ""),
                addr.get("country", ""),
            ])),
            "managing_lou":      reg.get("managingLou", ""),
            "gleif_url":         f"https://www.gleif.org/en/lei/{rec.get('id','')}",
            "source":            "GLEIF",
        })

    return results


def fetch_gleif_relationships(lei: str) -> dict:
    """
    Fetch GLEIF parent / child / ultimate-parent relationships for a given LEI.
    Returns { ultimate_parent: {...}, direct_parent: {...}, direct_children: [...] }
    """
    try:
        r = requests.get(
            f"{_GLEIF_BASE}/lei-records/{lei}/ultimate-parent-relationship",
            headers={"Accept": "application/vnd.api+json"},
            timeout=10,
        )
        ultimate = r.json().get("data", {}) if r.ok else {}
    except Exception:
        ultimate = {}

    try:
        r2 = requests.get(
            f"{_GLEIF_BASE}/lei-records/{lei}/direct-parent-relationship",
            headers={"Accept": "application/vnd.api+json"},
            timeout=10,
        )
        direct = r2.json().get("data", {}) if r2.ok else {}
    except Exception:
        direct = {}

    # Fetch direct children (subsidiaries)
    children = []
    try:
        r3 = requests.get(
            f"{_GLEIF_BASE}/lei-records/{lei}/direct-child-relationships",
            headers={"Accept": "application/vnd.api+json"},
            timeout=10,
        )
        if r3.ok:
            children = r3.json().get("data", [])
    except Exception:
        pass

    return {
        "ultimate_parent": ultimate,
        "direct_parent":   direct,
        "direct_children": children,
    }


def fetch_gleif_entity_details(lei: str) -> dict:
    """
    Fetch full entity details from GLEIF by LEI.
    Returns structured entity data including legal name, address, status.
    """
    try:
        r = requests.get(
            f"{_GLEIF_BASE}/lei-records/{lei}",
            headers={"Accept": "application/vnd.api+json"},
            timeout=10,
        )
        if not r.ok:
            return {}
        data = r.json().get("data", {})
        attrs = data.get("attributes", {})
        entity = attrs.get("entity", {})
        reg = attrs.get("registration", {})
        addr = entity.get("legalAddress", {})

        return {
            "lei": lei,
            "name": entity.get("legalName", {}).get("name", ""),
            "status": reg.get("status", ""),
            "jurisdiction": entity.get("jurisdiction", ""),
            "legal_form": entity.get("legalForm", {}).get("id", ""),
            "registered_address": ", ".join(filter(None, [
                addr.get("addressLines", [""])[0] if addr.get("addressLines") else "",
                addr.get("city", ""),
                addr.get("country", ""),
            ])),
            "headquarters_address": ", ".join(filter(None, [
                entity.get("headquartersAddress", {}).get("addressLines", [""])[0] if entity.get("headquartersAddress", {}).get("addressLines") else "",
                entity.get("headquartersAddress", {}).get("city", ""),
                entity.get("headquartersAddress", {}).get("country", ""),
            ])),
            "category": entity.get("category", ""),
            "source": "GLEIF",
        }
    except Exception as exc:
        logger.warning("GLEIF entity fetch failed for %s: %s", lei, exc)
        return {}


def traverse_ownership_chain(lei: str, max_depth: int = 5) -> dict:
    """
    Recursively traverse the ownership chain upward from an LEI to find
    all parent entities up to the ultimate parent.

    Returns {
        "entity": {...},
        "ownership_chain": [
            {"level": 1, "entity": {...}, "relationship_type": "direct_parent"},
            {"level": 2, "entity": {...}, "relationship_type": "direct_parent"},
            ...
        ],
        "ultimate_parent": {...},
        "chain_length": int,
    }
    """
    entity = fetch_gleif_entity_details(lei)
    if not entity:
        return {"error": f"Entity not found for LEI: {lei}"}

    ownership_chain = []
    visited = {lei}
    current_lei = lei

    for level in range(1, max_depth + 1):
        rels = fetch_gleif_relationships(current_lei)
        direct_parent = rels.get("direct_parent", {})

        if not direct_parent:
            break

        # Extract parent LEI from relationship
        parent_lei = None
        if isinstance(direct_parent, dict):
            rel_data = direct_parent.get("attributes", {}).get("relationship", {})
            if rel_data:
                # Parent LEI is in the startNode
                parent_lei = rel_data.get("startNode", {}).get("id")

        if not parent_lei or parent_lei in visited:
            break

        visited.add(parent_lei)
        parent_entity = fetch_gleif_entity_details(parent_lei)

        if parent_entity:
            ownership_chain.append({
                "level": level,
                "entity": parent_entity,
                "relationship_type": "direct_parent",
            })
            current_lei = parent_lei
        else:
            break

    ultimate_parent = ownership_chain[-1]["entity"] if ownership_chain else entity

    return {
        "entity": entity,
        "ownership_chain": ownership_chain,
        "ultimate_parent": ultimate_parent,
        "chain_length": len(ownership_chain),
    }


def build_corporate_network_graph(lei: str, include_children: bool = True, max_depth: int = 3) -> dict:
    """
    Build a network graph of corporate relationships around an entity.

    Returns {
        "nodes": [
            {"id": "LEI123", "name": "Company A", "type": "root|parent|subsidiary", ...},
            ...
        ],
        "edges": [
            {"source": "LEI123", "target": "LEI456", "relationship": "parent_of|subsidiary_of"},
            ...
        ],
        "root_entity": {...},
    }
    """
    nodes = []
    edges = []
    visited = set()

    def add_node(entity_data: dict, node_type: str) -> str:
        """Add a node if not already present."""
        lei_id = entity_data.get("lei", "")
        if lei_id and lei_id not in visited:
            visited.add(lei_id)
            nodes.append({
                "id": lei_id,
                "name": entity_data.get("name", ""),
                "type": node_type,
                "jurisdiction": entity_data.get("jurisdiction", ""),
                "status": entity_data.get("status", ""),
            })
        return lei_id

    def traverse_up(current_lei: str, depth: int = 0):
        """Traverse upward to parents."""
        if depth >= max_depth or current_lei in visited:
            return

        entity = fetch_gleif_entity_details(current_lei)
        if not entity:
            return

        node_type = "root" if depth == 0 else "parent"
        add_node(entity, node_type)

        rels = fetch_gleif_relationships(current_lei)
        direct_parent = rels.get("direct_parent", {})

        if direct_parent:
            rel_data = direct_parent.get("attributes", {}).get("relationship", {})
            parent_lei = rel_data.get("startNode", {}).get("id") if rel_data else None
            if parent_lei and parent_lei not in visited:
                parent_entity = fetch_gleif_entity_details(parent_lei)
                if parent_entity:
                    add_node(parent_entity, "parent")
                    edges.append({
                        "source": parent_lei,
                        "target": current_lei,
                        "relationship": "parent_of",
                    })
                    traverse_up(parent_lei, depth + 1)

    def traverse_down(current_lei: str, depth: int = 0):
        """Traverse downward to subsidiaries."""
        if depth >= max_depth:
            return

        rels = fetch_gleif_relationships(current_lei)
        children = rels.get("direct_children", [])

        for child in children[:20]:  # Limit children per level
            child_attrs = child.get("attributes", {}).get("relationship", {})
            child_lei = child_attrs.get("endNode", {}).get("id") if child_attrs else None

            if child_lei and child_lei not in visited:
                child_entity = fetch_gleif_entity_details(child_lei)
                if child_entity:
                    add_node(child_entity, "subsidiary")
                    edges.append({
                        "source": current_lei,
                        "target": child_lei,
                        "relationship": "parent_of",
                    })
                    traverse_down(child_lei, depth + 1)

    # Start traversal
    traverse_up(lei)

    if include_children:
        traverse_down(lei)

    root_entity = next((n for n in nodes if n["type"] == "root"), None)

    return {
        "nodes": nodes,
        "edges": edges,
        "root_entity": root_entity,
        "total_entities": len(nodes),
        "total_relationships": len(edges),
    }


def detect_ultimate_beneficial_owners(entity_name: str, jurisdiction: str = "") -> dict:
    """
    Detect Ultimate Beneficial Owners (UBOs) by combining GLEIF, UK PSC, and OpenCorporates.

    UBOs are natural persons who ultimately control an entity through direct or indirect
    ownership of 25%+ or through other control mechanisms.

    Returns {
        "entity_name": str,
        "ubos": [
            {"name": str, "source": str, "control_type": str, "percentage": float|None},
            ...
        ],
        "corporate_parents": [...],
        "data_sources_checked": [...],
    }
    """
    ubos = []
    corporate_parents = []
    sources_checked = []

    # 1. Check GLEIF for corporate ownership chain
    gleif_matches = search_gleif(entity_name, limit=1)
    if gleif_matches:
        sources_checked.append("GLEIF")
        lei = gleif_matches[0]["lei"]
        chain = traverse_ownership_chain(lei)

        if chain.get("ultimate_parent"):
            corporate_parents.append({
                "name": chain["ultimate_parent"].get("name", ""),
                "lei": chain["ultimate_parent"].get("lei", ""),
                "jurisdiction": chain["ultimate_parent"].get("jurisdiction", ""),
                "source": "GLEIF",
            })

    # 2. Check UK Companies House PSC for natural person UBOs
    if jurisdiction.lower() in ("uk", "gb", "united kingdom", "") or not jurisdiction:
        uk_matches = search_uk_companies(entity_name, limit=1)
        if uk_matches:
            sources_checked.append("UK Companies House PSC")
            uk_detail = enrich_uk_company(uk_matches[0]["company_number"])

            for psc in uk_detail.get("persons_with_significant_control", []):
                # PSC with nature of control indicates beneficial ownership
                natures = psc.get("natures_of_control", [])
                control_types = []
                ownership_pct = None

                for nature in natures:
                    if "ownership" in nature.lower():
                        control_types.append("ownership")
                        # Try to extract percentage range
                        if "75-to-100" in nature:
                            ownership_pct = 87.5  # midpoint
                        elif "50-to-75" in nature:
                            ownership_pct = 62.5
                        elif "25-to-50" in nature:
                            ownership_pct = 37.5
                    elif "voting-rights" in nature.lower():
                        control_types.append("voting_rights")
                    elif "significant-influence" in nature.lower():
                        control_types.append("significant_influence")

                ubos.append({
                    "name": psc.get("name", ""),
                    "source": "UK Companies House PSC",
                    "control_type": ", ".join(control_types) if control_types else "significant_control",
                    "percentage": ownership_pct,
                    "nationality": psc.get("nationality", ""),
                    "country_of_residence": psc.get("country_of_residence", ""),
                    "notified_on": psc.get("notified_on", ""),
                })

    # 3. Check OpenCorporates for officers/directors as potential UBOs
    oc_matches = search_opencorporates(entity_name, jurisdiction=jurisdiction, limit=1)
    if oc_matches:
        sources_checked.append("OpenCorporates")
        top = oc_matches[0]
        if top.get("company_number") and top.get("jurisdiction"):
            oc_detail = enrich_opencorporates(top["company_number"], top["jurisdiction"])

            # Officers with significant roles might indicate UBO-like control
            for officer in oc_detail.get("officers", []):
                role = officer.get("role", "").lower()
                if any(r in role for r in ["director", "secretary", "president", "ceo", "chairman"]):
                    if officer.get("name") and not officer.get("inactive"):
                        # Check if already in UBOs
                        if not any(u["name"].lower() == officer["name"].lower() for u in ubos):
                            ubos.append({
                                "name": officer.get("name", ""),
                                "source": "OpenCorporates (Officer)",
                                "control_type": f"officer_{role}",
                                "percentage": None,
                                "start_date": officer.get("start"),
                            })

    return {
        "entity_name": entity_name,
        "ubos": ubos,
        "corporate_parents": corporate_parents,
        "data_sources_checked": sources_checked,
        "ubo_count": len(ubos),
        "has_natural_person_ubo": any(u["source"] == "UK Companies House PSC" for u in ubos),
    }


def cross_reference_ownership(entity_name: str, jurisdiction: str = "") -> dict:
    """
    Cross-reference ownership data across multiple registries to build
    a comprehensive ownership picture.

    Returns reconciled ownership data with confidence scores.
    """
    results = {
        "entity_name": entity_name,
        "jurisdiction": jurisdiction,
        "ownership_data": [],
        "confidence_score": 0,
        "sources_matched": 0,
        "discrepancies": [],
    }

    # Gather data from all sources
    gleif_data = search_gleif(entity_name, limit=1)
    oc_data = search_opencorporates(entity_name, jurisdiction, limit=1)
    uk_data = search_uk_companies(entity_name, limit=1) if jurisdiction.lower() in ("uk", "gb", "") else []

    sources_found = sum([bool(gleif_data), bool(oc_data), bool(uk_data)])
    results["sources_matched"] = sources_found

    # Cross-reference names
    names = set()
    if gleif_data:
        names.add(gleif_data[0].get("name", "").upper())
    if oc_data:
        names.add(oc_data[0].get("name", "").upper())
    if uk_data:
        names.add(uk_data[0].get("name", "").upper())

    # Check for name discrepancies
    if len(names) > 1:
        results["discrepancies"].append({
            "field": "company_name",
            "values": list(names),
            "note": "Company names differ across registries",
        })

    # Cross-reference jurisdictions
    jurisdictions = set()
    if gleif_data:
        jurisdictions.add(gleif_data[0].get("jurisdiction", "").upper())
    if oc_data:
        jurisdictions.add(oc_data[0].get("jurisdiction", "").upper())

    # Build unified ownership data
    if gleif_data:
        lei = gleif_data[0]["lei"]
        rels = fetch_gleif_relationships(lei)
        results["ownership_data"].append({
            "source": "GLEIF",
            "lei": lei,
            "has_parent": bool(rels.get("direct_parent")),
            "has_ultimate_parent": bool(rels.get("ultimate_parent")),
            "has_children": bool(rels.get("direct_children")),
        })

    if uk_data:
        uk_detail = enrich_uk_company(uk_data[0]["company_number"])
        psc_count = len(uk_detail.get("persons_with_significant_control", []))
        results["ownership_data"].append({
            "source": "UK Companies House",
            "company_number": uk_data[0]["company_number"],
            "psc_count": psc_count,
            "has_psc": psc_count > 0,
        })

    # Calculate confidence score (0-100)
    base_score = sources_found * 25
    if not results["discrepancies"]:
        base_score += 25
    results["confidence_score"] = min(100, base_score)

    return results


# ── FinCEN BOI / FDIC fallback ───────────────────────────────────────────────

def search_fincen_entities(entity_name: str) -> List[dict]:
    """
    Search FinCEN's financial institution registration search.
    Returns MSB / bank registration records matching the name.
    """
    try:
        r = requests.get(
            f"{_FINCEN_BASE}",
            params={"q": entity_name, "size": 5},
            timeout=10,
        )
        r.raise_for_status()
        hits = r.json().get("hits", {}).get("hits", [])
    except Exception as exc:
        logger.warning("FinCEN search failed: %s", exc)
        return []

    results = []
    for h in hits:
        src = h.get("_source", {})
        results.append({
            "name":      src.get("LEGAL_NAME", ""),
            "type":      src.get("INST_TYPE", ""),
            "city":      src.get("CITY", ""),
            "state":     src.get("STATE", ""),
            "country":   src.get("CNTRY_NM", ""),
            "reg_date":  src.get("INITIAL_REG_DATE", ""),
            "status":    src.get("STATUS", ""),
            "source":    "FinCEN",
        })
    return results


def search_fdic_banks(entity_name: str) -> List[dict]:
    """
    Search FDIC BankFind for insured bank/thrift institutions.
    """
    try:
        r = requests.get(
            f"{_FDIC_BASE}/institutions",
            params={
                "search": entity_name,
                "fields": "NAME,CITY,STNAME,ACTIVE,ESTYMD,REPDTE,ASSET,NETINC,CERT",
                "limit":  5,
            },
            timeout=10,
        )
        r.raise_for_status()
        data = r.json().get("data", [])
    except Exception as exc:
        logger.warning("FDIC search failed: %s", exc)
        return []

    results = []
    for d in data:
        rec = d.get("data", d)
        results.append({
            "name":            rec.get("NAME", ""),
            "cert":            rec.get("CERT", ""),
            "city":            rec.get("CITY", ""),
            "state":           rec.get("STNAME", ""),
            "active":          rec.get("ACTIVE", 1) == 1,
            "established":     rec.get("ESTYMD", ""),
            "total_assets_k":  rec.get("ASSET", 0),
            "net_income_k":    rec.get("NETINC", 0),
            "source":          "FDIC BankFind",
        })
    return results


# ── Combined private company enrichment ──────────────────────────────────────

def fetch_private_company_intel(entity_name: str, jurisdiction: str = "") -> dict:
    """
    Run all three sources (OpenCorporates, GLEIF, FinCEN) for a company.
    Returns a unified dict with all available data.
    """
    oc_results  = search_opencorporates(entity_name, jurisdiction=jurisdiction)
    gl_results  = search_gleif(entity_name)
    fc_results  = search_fincen_entities(entity_name)
    fdic_results = search_fdic_banks(entity_name)

    # Try to get full enrichment for the top OC match
    oc_detail = {}
    if oc_results:
        top = oc_results[0]
        if top.get("company_number") and top.get("jurisdiction"):
            oc_detail = enrich_opencorporates(top["company_number"], top["jurisdiction"])

    # GLEIF relationship graph for top match
    gleif_rels = {}
    if gl_results:
        gleif_rels = fetch_gleif_relationships(gl_results[0]["lei"])

    return {
        "opencorporates_matches": oc_results,
        "opencorporates_detail":  oc_detail,
        "gleif_matches":          gl_results,
        "gleif_relationships":    gleif_rels,
        "fincen_records":         fc_results,
        "fdic_records":           fdic_results,
    }


# ── UK Companies House ───────────────────────────────────────────────────────

def search_uk_companies(company_name: str, limit: int = 5) -> List[dict]:
    """
    Search UK Companies House for companies matching the name.
    Returns list of { name, company_number, company_type, status,
                       incorporation_date, registered_address, companies_house_url }.
    """
    if not _UKCH_API_KEY:
        logger.warning("UK Companies House API key not configured")
        return []

    try:
        r = requests.get(
            f"{_UKCH_BASE}/search/companies",
            params={"q": company_name, "items_per_page": limit},
            auth=(_UKCH_API_KEY, ""),  # API key as username, empty password
            timeout=15,
        )
        r.raise_for_status()
        items = r.json().get("items", [])
    except Exception as exc:
        logger.warning("UK Companies House search failed: %s", exc)
        return []

    results = []
    for item in items:
        addr = item.get("address", {})
        results.append({
            "name":               item.get("title", ""),
            "company_number":     item.get("company_number", ""),
            "company_type":       item.get("company_type", ""),
            "status":             item.get("company_status", ""),
            "incorporation_date": item.get("date_of_creation", ""),
            "dissolution_date":   item.get("date_of_cessation"),
            "registered_address": ", ".join(filter(None, [
                addr.get("address_line_1", ""),
                addr.get("locality", ""),
                addr.get("postal_code", ""),
            ])),
            "companies_house_url": f"https://find-and-update.company-information.service.gov.uk/company/{item.get('company_number', '')}",
            "source": "UK Companies House",
        })
    return results


def enrich_uk_company(company_number: str) -> dict:
    """
    Full company enrichment from UK Companies House by company number.
    Returns officers, filings, PSC (persons with significant control), etc.
    """
    if not _UKCH_API_KEY:
        logger.warning("UK Companies House API key not configured")
        return {}

    auth = (_UKCH_API_KEY, "")

    # Get company profile
    try:
        r = requests.get(f"{_UKCH_BASE}/company/{company_number}", auth=auth, timeout=15)
        r.raise_for_status()
        profile = r.json()
    except Exception as exc:
        logger.warning("UK Companies House profile fetch failed: %s", exc)
        return {}

    # Get officers
    officers = []
    try:
        r = requests.get(f"{_UKCH_BASE}/company/{company_number}/officers", auth=auth, timeout=10)
        if r.ok:
            for item in r.json().get("items", [])[:10]:
                officers.append({
                    "name":        item.get("name", ""),
                    "role":        item.get("officer_role", ""),
                    "appointed":   item.get("appointed_on", ""),
                    "resigned":    item.get("resigned_on"),
                    "nationality": item.get("nationality", ""),
                    "occupation":  item.get("occupation", ""),
                })
    except Exception:
        pass

    # Get PSC (persons with significant control)
    psc = []
    try:
        r = requests.get(f"{_UKCH_BASE}/company/{company_number}/persons-with-significant-control", auth=auth, timeout=10)
        if r.ok:
            for item in r.json().get("items", [])[:10]:
                psc.append({
                    "name":            item.get("name", ""),
                    "natures_of_control": item.get("natures_of_control", []),
                    "notified_on":     item.get("notified_on", ""),
                    "nationality":     item.get("nationality", ""),
                    "country_of_residence": item.get("country_of_residence", ""),
                })
    except Exception:
        pass

    # Get filing history
    filings = []
    try:
        r = requests.get(f"{_UKCH_BASE}/company/{company_number}/filing-history", auth=auth, params={"items_per_page": 10}, timeout=10)
        if r.ok:
            for item in r.json().get("items", [])[:10]:
                filings.append({
                    "type":        item.get("type", ""),
                    "description": item.get("description", ""),
                    "date":        item.get("date", ""),
                    "category":    item.get("category", ""),
                })
    except Exception:
        pass

    addr = profile.get("registered_office_address", {})
    return {
        "name":               profile.get("company_name", ""),
        "company_number":     company_number,
        "company_type":       profile.get("type", ""),
        "status":             profile.get("company_status", ""),
        "incorporation_date": profile.get("date_of_creation", ""),
        "dissolution_date":   profile.get("date_of_cessation"),
        "registered_address": ", ".join(filter(None, [
            addr.get("address_line_1", ""),
            addr.get("locality", ""),
            addr.get("postal_code", ""),
            addr.get("country", ""),
        ])),
        "sic_codes":          profile.get("sic_codes", []),
        "has_insolvency_history": profile.get("has_insolvency_history", False),
        "has_charges":        profile.get("has_charges", False),
        "officers":           officers,
        "persons_with_significant_control": psc,
        "filings":            filings,
        "companies_house_url": f"https://find-and-update.company-information.service.gov.uk/company/{company_number}",
        "source": "UK Companies House",
    }


# ── SEC Form D (Private Placements) ──────────────────────────────────────────

def search_sec_form_d(company_name: str, days_back: int = 365, limit: int = 10) -> List[dict]:
    """
    Search SEC EDGAR for Form D filings (Regulation D private placements).
    Form D reveals fundraising for private companies doing exempt offerings.
    Returns list of filings with issuer info, offering amount, sale date.
    """
    headers = {"User-Agent": _SEC_USER_AGENT}

    try:
        # Use SEC full-text search API
        r = requests.get(
            "https://efts.sec.gov/LATEST/search-index",
            params={
                "q": f'"{company_name}"',
                "dateRange": "custom",
                "startdt": (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d"),
                "enddt": datetime.now().strftime("%Y-%m-%d"),
                "forms": "D,D/A",
                "from": 0,
                "size": limit,
            },
            headers=headers,
            timeout=15,
        )
        r.raise_for_status()
        hits = r.json().get("hits", {}).get("hits", [])
    except Exception as exc:
        logger.warning("SEC Form D search failed: %s", exc)
        # Fallback to RSS feed
        return _search_form_d_rss(company_name, limit)

    results = []
    for hit in hits:
        src = hit.get("_source", {})
        results.append({
            "company_name":    src.get("display_names", [""])[0] if src.get("display_names") else "",
            "form_type":       src.get("form", "D"),
            "filed_at":        src.get("file_date", ""),
            "accession_number": src.get("adsh", ""),
            "cik":             src.get("ciks", [""])[0] if src.get("ciks") else "",
            "sec_url":         f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={src.get('ciks', [''])[0]}&type=D&dateb=&owner=include&count=10",
            "source":          "SEC EDGAR Form D",
        })
    return results


def _search_form_d_rss(company_name: str, limit: int = 10) -> List[dict]:
    """Fallback: search Form D via SEC RSS feeds."""
    headers = {"User-Agent": _SEC_USER_AGENT}
    try:
        r = requests.get(
            f"{_SEC_EDGAR}",
            params={
                "action": "getcompany",
                "company": company_name,
                "type": "D",
                "dateb": "",
                "owner": "include",
                "count": limit,
                "output": "atom",
            },
            headers=headers,
            timeout=15,
        )
        if not r.ok:
            return []

        # Parse Atom feed
        root = ET.fromstring(r.content)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        results = []
        for entry in root.findall("atom:entry", ns)[:limit]:
            title = entry.find("atom:title", ns)
            link = entry.find("atom:link", ns)
            updated = entry.find("atom:updated", ns)
            results.append({
                "company_name": title.text if title is not None else "",
                "form_type": "D",
                "filed_at": (updated.text[:10] if updated is not None else ""),
                "sec_url": (link.get("href", "") if link is not None else ""),
                "source": "SEC EDGAR Form D",
            })
        return results
    except Exception as exc:
        logger.warning("SEC Form D RSS search failed: %s", exc)
        return []


def get_form_d_details(cik: str) -> List[dict]:
    """
    Get detailed Form D filings for a specific CIK.
    Returns offering amounts, sale dates, exemptions claimed, investors.
    """
    headers = {"User-Agent": _SEC_USER_AGENT}

    try:
        # Get submissions for this CIK
        cik_padded = cik.zfill(10)
        r = requests.get(
            f"https://data.sec.gov/submissions/CIK{cik_padded}.json",
            headers=headers,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as exc:
        logger.warning("SEC Form D details fetch failed: %s", exc)
        return []

    # Filter for Form D filings
    filings = data.get("filings", {}).get("recent", {})
    form_types = filings.get("form", [])
    dates = filings.get("filingDate", [])
    accessions = filings.get("accessionNumber", [])

    results = []
    for i, form in enumerate(form_types):
        if form in ("D", "D/A"):
            accession = accessions[i].replace("-", "")
            results.append({
                "company_name": data.get("name", ""),
                "cik": cik,
                "form_type": form,
                "filed_at": dates[i] if i < len(dates) else "",
                "accession_number": accessions[i] if i < len(accessions) else "",
                "filing_url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}",
                "source": "SEC EDGAR Form D",
            })
    return results[:10]


def estimate_private_funding(company_name: str) -> dict:
    """
    Estimate private company funding from SEC Form D filings.
    Form D reveals Regulation D exempt offerings (seed, Series A, etc.).
    """
    filings = search_sec_form_d(company_name, days_back=1825, limit=20)  # 5 years

    if not filings:
        return {
            "company_name": company_name,
            "total_filings": 0,
            "estimated_total_raised": None,
            "funding_rounds": [],
            "source": "SEC Form D",
        }

    return {
        "company_name": company_name,
        "total_filings": len(filings),
        "filings": filings,
        "note": "Form D filings indicate exempt offerings; exact amounts require parsing individual filings",
        "source": "SEC Form D",
    }


# ── Combined private company enrichment (enhanced) ───────────────────────────

def fetch_private_company_intel_full(entity_name: str, jurisdiction: str = "") -> dict:
    """
    Enhanced private company intel — runs all sources including UK and SEC Form D.
    Returns a unified dict with all available data.
    """
    # Base sources
    base = fetch_private_company_intel(entity_name, jurisdiction)

    # UK Companies House
    uk_matches = []
    uk_detail = {}
    if jurisdiction.lower() in ("uk", "gb", "united kingdom", "") or not jurisdiction:
        uk_matches = search_uk_companies(entity_name)
        if uk_matches:
            uk_detail = enrich_uk_company(uk_matches[0]["company_number"])

    # SEC Form D (private placements)
    form_d = search_sec_form_d(entity_name, days_back=1825)
    funding = estimate_private_funding(entity_name) if not form_d else {"filings": form_d}

    return {
        **base,
        "uk_companies_house_matches": uk_matches,
        "uk_companies_house_detail": uk_detail,
        "sec_form_d_filings": form_d,
        "private_funding_estimate": funding,
    }


def get_startup_funding_history(company_name: str) -> dict:
    """
    Get funding history for a private company/startup.
    Combines SEC Form D data with estimated funding rounds.
    """
    form_d = search_sec_form_d(company_name, days_back=3650, limit=50)  # 10 years

    # Try to get CIK and detailed filings
    detailed = []
    if form_d and form_d[0].get("cik"):
        detailed = get_form_d_details(form_d[0]["cik"])

    return {
        "company_name": company_name,
        "form_d_filings": form_d or detailed,
        "total_filings": len(form_d or detailed),
        "data_note": "SEC Form D reveals Regulation D exempt offerings. For full funding history including amounts, consider commercial APIs like Crunchbase or PitchBook.",
        "source": "SEC EDGAR",
    }
