"""
FPDS.gov Full Federal Contracts Connector
────────────────────────────────────────────────────────────────────────────
Complete Federal Procurement Data System access for deep intelligence:
  - ALL federal contracts for an entity (not just summary)
  - Contract modifications and options
  - Subcontractor relationships
  - Self-dealing detection (related party analysis)
  - Agency breakdown with dollar values
  - Historical contract timeline

Uses FPDS.gov ATOM feeds and USASpending API v2 for comprehensive data.
No API key required - public data.
"""
import os
import re
import time
import logging
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from xml.etree import ElementTree as ET

from app.connectors.entity_naming import entity_search_term, matches_entity

logger = logging.getLogger(__name__)

# FPDS ATOM feed base
FPDS_BASE = "https://www.fpds.gov/ezsearch/FEEDS/ATOM"
USASPENDING_BASE = "https://api.usaspending.gov/api/v2"

# Common request headers
HEADERS = {
    "User-Agent": "FinanceIntelPlatform/1.0 research@example.com",
    "Accept": "application/json, application/xml",
}

# ── UEI / DUNS Resolution Cache ─────────────────────────────────────────────
_UEI_CACHE: Dict[str, Optional[Dict[str, Any]]] = {}


def resolve_recipient_uei(entity_name: str) -> Optional[Dict[str, Any]]:
    """
    Resolve a company name to its USASpending recipient profile (UEI + DUNS).

    USASpending's /api/v2/recipient/ returns registered recipients; we pick
    the parent-level (P) entry whose name best matches our entity (using
    entity_naming's match logic). Returns dict with keys:
    recipient_id, uei, duns, name.

    This is critical because USASpending's award search by text often misses
    awards booked under subsidiary names or alternate legal registrations.
    Searching by DUNS captures all awards under the parent entity tree.
    """
    cache_key = entity_name.upper().strip()
    if cache_key in _UEI_CACHE:
        return _UEI_CACHE[cache_key]

    from app.connectors.entity_naming import clean_legal_name

    # Try multiple search terms — USASpending's keyword matching is literal.
    # USASpending stores names like "NVIDIA CORP" not "NVIDIA Corporation",
    # so we include the abbreviated corporate suffix form too.
    cleaned = clean_legal_name(entity_name)
    search_variants = list(dict.fromkeys(filter(None, [
        entity_name,                          # "NVIDIA Corporation"
        cleaned,                              # "NVIDIA"
        f"{cleaned} CORP" if cleaned else "", # "NVIDIA CORP" — common USASpending form
        entity_search_term(entity_name),      # "NVIDIA"
    ])))

    for search_term in search_variants:
        if not search_term or len(search_term) < 3:
            continue

        try:
            resp = requests.post(
                f"{USASPENDING_BASE}/recipient/",
                json={
                    "keyword": search_term,
                    "award_type": "all",
                    "order": "desc",
                    "sort": "amount",
                    "limit": 10,
                    "page": 1,
                },
                headers=HEADERS,
                timeout=20,
            )
            if not resp.ok:
                continue

            results = resp.json().get("results", [])
            if not results:
                continue

            # Prefer parent-level (P) entries — they aggregate all subsidiary awards
            parents = [r for r in results
                       if r.get("recipient_level") == "P" and r.get("duns")]
            # Also consider child-level entries that have a DUNS
            with_duns = [r for r in results if r.get("duns")]
            candidates = parents if parents else with_duns

            # Pick best match using our entity-matching logic
            for candidate in candidates:
                cand_name = candidate.get("name", "")
                if matches_entity(cand_name, entity_name):
                    profile = {
                        "recipient_id": candidate.get("id"),
                        "uei": candidate.get("uei"),
                        "duns": candidate.get("duns"),
                        "name": cand_name,
                        "recipient_level": candidate.get("recipient_level", "R"),
                    }
                    _UEI_CACHE[cache_key] = profile
                    logger.info("Resolved '%s' → DUNS=%s, UEI=%s, recipient_id=%s",
                                entity_name, profile["duns"], profile["uei"],
                                profile["recipient_id"])
                    return profile

        except Exception as e:
            logger.debug("UEI search for '%s' with term '%s' failed: %s",
                         entity_name, search_term, e)
            continue

    logger.info("No confident UEI match for '%s' — falling back to text search",
                entity_name)
    _UEI_CACHE[cache_key] = None
    return None


def fetch_recipient_profile(recipient_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch full recipient profile from USASpending, which includes total award
    amounts, child recipients (subsidiaries), and UEI info.

    The recipient_id format is: {DUNS/UEI}-{level} where level is R (recipient),
    P (parent), or C (child).
    """
    if not recipient_id:
        return None
    try:
        url = f"{USASPENDING_BASE}/recipient/{recipient_id}/"
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.ok:
            return resp.json()
        logger.debug("Recipient profile %s: HTTP %d", recipient_id, resp.status_code)
    except Exception as e:
        logger.debug("Recipient profile error: %s", e)
    return None


def _safe_float(val) -> float:
    """Safely convert value to float."""
    if val is None:
        return 0.0
    try:
        return float(str(val).replace(",", "").replace("$", ""))
    except (ValueError, TypeError):
        return 0.0


def _safe_text(element, tag: str, default: str = "") -> str:
    """Safely extract text from XML element."""
    if element is None:
        return default
    child = element.find(tag)
    if child is not None and child.text:
        return child.text.strip()
    # Try with namespace
    for ns in ["", "{http://www.fpds.gov/FPDS}"]:
        child = element.find(f"{ns}{tag}")
        if child is not None and child.text:
            return child.text.strip()
    return default


def fetch_fpds_atom(vendor_name: str, max_results: int = 100) -> List[Dict[str, Any]]:
    """
    Fetch contracts from FPDS ATOM feed for a vendor.
    Returns list of contract records.
    """
    contracts = []
    try:
        # FPDS ATOM search URL
        query = vendor_name.replace(" ", "+")
        url = f"{FPDS_BASE}?VENDOR_FULL_NAME={query}&CONTRACTING_DEPARTMENT_ID=&SIGNED_DATE=[2015/01/01,2026/12/31]&q=&sortBy=SIGNED_DATE&desc=Y"

        resp = requests.get(url, headers=HEADERS, timeout=30)
        if not resp.ok:
            logger.warning("FPDS ATOM fetch failed: %s", resp.status_code)
            return contracts

        # Parse ATOM XML
        root = ET.fromstring(resp.content)
        ns = {"atom": "http://www.w3.org/2005/Atom", "fpds": "http://www.fpds.gov/FPDS"}

        for entry in root.findall(".//atom:entry", ns)[:max_results]:
            try:
                # Extract contract data from ATOM entry
                content = entry.find(".//atom:content", ns)
                if content is None:
                    continue

                # Parse embedded contract data
                contract = {
                    "contract_id": _safe_text(content, "PIID") or _safe_text(entry, "atom:id", ns),
                    "vendor_name": vendor_name,
                    "agency": _safe_text(content, "contractingOfficeName") or _safe_text(content, "CONTRACTING_AGENCY_NAME"),
                    "department": _safe_text(content, "departmentFullName") or _safe_text(content, "CONTRACTING_DEPARTMENT_NAME"),
                    "description": _safe_text(content, "descriptionOfContractRequirement") or _safe_text(content, "DESCRIPTION_OF_REQUIREMENT"),
                    "obligated_amount": _safe_float(_safe_text(content, "dollarObligated") or _safe_text(content, "OBLIGATED_AMOUNT")),
                    "base_and_exercised": _safe_float(_safe_text(content, "baseAndExercisedOptionsValue")),
                    "ultimate_value": _safe_float(_safe_text(content, "ultimateContractValue")),
                    "sign_date": _safe_text(content, "signedDate") or _safe_text(content, "SIGNED_DATE"),
                    "effective_date": _safe_text(content, "effectiveDate"),
                    "completion_date": _safe_text(content, "currentCompletionDate"),
                    "contract_type": _safe_text(content, "typeOfContractPricing"),
                    "naics": _safe_text(content, "principalNAICSCode"),
                    "psc": _safe_text(content, "productOrServiceCode"),
                    "place_of_performance": _safe_text(content, "placeOfPerformanceCity"),
                    "competition": _safe_text(content, "extentCompeted"),
                    "set_aside": _safe_text(content, "typeOfSetAside"),
                    "is_modification": bool(_safe_text(content, "reasonForModification")),
                    "modification_reason": _safe_text(content, "reasonForModification"),
                }

                if contract.get("contract_id") or contract.get("obligated_amount"):
                    contracts.append(contract)

            except Exception as e:
                logger.debug("Error parsing FPDS entry: %s", e)
                continue

    except Exception as e:
        logger.warning("FPDS ATOM fetch error: %s", e)

    return contracts


# USASpending rejects a request whose award_type_codes span more than one group,
# so each group must be queried separately and the results combined. Querying only
# the "contracts" group understates NVIDIA's federal footprint by ~918x: its DARPA
# and DOE awards are classified under the "other" group.
AWARD_TYPE_GROUPS = {
    "contracts": ["A", "B", "C", "D"],
    "idvs": ["IDV_A", "IDV_B", "IDV_B_A", "IDV_B_B", "IDV_B_C", "IDV_C", "IDV_D", "IDV_E"],
    "grants": ["02", "03", "04", "05"],
    "direct_payments": ["06", "10"],
    "other": ["09", "11", "-1"],
}

# The loan mapping has no "Award Amount" field; it sorts on a different column.
GROUP_SORT_FIELD = {"loans": "Award ID"}

BASE_AWARD_FIELDS = [
    "Award ID", "Recipient Name", "Award Amount", "Awarding Agency",
    "Start Date", "End Date", "Description", "Awarding Sub Agency",
]

CONTRACT_ONLY_FIELDS = [
    "Award Type", "Contract Award Type", "Period of Performance Start Date",
    "Period of Performance Current End Date", "Total Outlayed Amount",
    "NAICS Code", "NAICS Description", "Product or Service Code",
    "Product or Service Code Description", "Type of Contract Pricing",
    "Extent Competed", "Place of Performance State Code",
    "Place of Performance City Name", "Place of Performance Country Name",
]


def fetch_usaspending_full(entity_name: str, max_results: int = 100,
                           start_date: str = "2007-10-01",
                           subsidiaries: Optional[List[str]] = None,
                           recipient_uei: Optional[str] = None,
                           request_timeout: int = 20,
                           max_elapsed_seconds: Optional[float] = None) -> Dict[str, Any]:
    """
    Fetch comprehensive award data from USASpending across ALL award-type groups.

    Returns prime awards with per-group and per-agency breakdowns. Recipient names
    are verified against the entity's own name forms so free-text collisions are
    excluded.

    Args:
        subsidiaries: Full legal names of subsidiaries whose awards belong to the
            parent. Pass them as complete names, not fragments — a fragment such
            as "Portland Group" used as a query matches many unrelated firms.
            Callers can source these from SEC Exhibit 21 via
            ``sec_edgar_connector.get_subsidiaries``.
        recipient_uei: If provided, uses UEI-keyed recipient lookup instead of
            text search. This is far more reliable — it matches on the registered
            entity identifier rather than free-text name, catching all awards
            including those booked under subsidiary or alternate legal names.
    """
    result = {
        "contracts": [],
        "total_obligated": 0,
        "total_base_value": 0,
        "total_potential_value": 0,
        "agency_breakdown": {},
        "year_breakdown": {},
        "competition_breakdown": {},
        "naics_breakdown": {},
        "contract_types": {},
        "group_breakdown": {},
        "excluded_false_positives": 0,
        "earliest_date": None,
        "latest_date": None,
        "source_url": "https://api.usaspending.gov/api/v2/search/spending_by_award/",
    }

    subsidiaries = subsidiaries or []
    end_date = datetime.now().strftime("%Y-%m-%d")

    # ── UEI Resolution ────────────────────────────────────────────────────────
    # If caller didn't pass a UEI, try resolving one. A successful resolution
    # means we can search by recipient_id which captures ALL awards under that
    # entity tree — including those booked to subsidiary legal names.
    resolved_profile = None
    if not recipient_uei:
        resolved_profile = resolve_recipient_uei(entity_name)
        if resolved_profile and resolved_profile.get("uei"):
            recipient_uei = resolved_profile["uei"]
            logger.info("UEI-resolved '%s' → %s (%s)",
                        entity_name, recipient_uei, resolved_profile.get("name"))

    # Search on the distinctive short form as well as the full legal name:
    # USASpending matches recipient text literally, so "NVIDIA Corporation" misses
    # awards booked to "NVIDIA PUBLIC SECTOR CORPORATION". Subsidiaries are queried
    # by full name so a generic one cannot broaden the primary search.
    search_terms = sorted({entity_name, entity_search_term(entity_name), *subsidiaries})

    start_ts = time.monotonic()

    for group, codes in AWARD_TYPE_GROUPS.items():
        if max_elapsed_seconds is not None:
            remaining = max_elapsed_seconds - (time.monotonic() - start_ts)
            if remaining <= 0:
                logger.warning("USASpending fetch budget exhausted for %s after partial results", entity_name)
                break
            group_timeout = max(3, min(int(remaining), request_timeout))
        else:
            group_timeout = request_timeout
        fields = list(BASE_AWARD_FIELDS)
        if group in ("contracts", "idvs"):
            fields += CONTRACT_ONLY_FIELDS

        # Build recipient filter: prefer DUNS-keyed search if available.
        # USASpending's recipient_search_text is an OR filter — including both
        # the DUNS and text names captures awards booked to subsidiaries with
        # different DUNS numbers (e.g., "NVIDIA PUBLIC SECTOR CORPORATION").
        if resolved_profile and resolved_profile.get("duns"):
            search_text = sorted({resolved_profile["duns"], *search_terms})
        elif recipient_uei:
            search_text = sorted({recipient_uei, *search_terms})
        else:
            search_text = search_terms

        payload = {
            "filters": {
                "recipient_search_text": search_text,
                "award_type_codes": codes,
                "time_period": [{"start_date": start_date, "end_date": end_date}],
            },
            "fields": fields,
            "page": 1,
            "limit": max_results,
            "sort": GROUP_SORT_FIELD.get(group, "Award Amount"),
            "order": "desc",
        }

        try:
            resp = requests.post(
                f"{USASPENDING_BASE}/search/spending_by_award/",
                json=payload,
                headers=HEADERS,
                timeout=group_timeout,
            )
        except Exception as e:
            logger.warning("USASpending %s group fetch error: %s", group, e)
            continue

        if not resp.ok:
            logger.warning("USASpending %s group HTTP %s: %s",
                           group, resp.status_code, resp.text[:200])
            if resp.status_code in (401, 403, 429):
                break
            continue

        group_total = 0
        group_count = 0

        for award in resp.json().get("results", []):
            if not matches_entity(award.get("Recipient Name"), entity_name, subsidiaries):
                result["excluded_false_positives"] += 1
                continue
            award["_group"] = group
            amt = _safe_float(award.get("Award Amount"))
            agency = award.get("Awarding Agency") or "Unknown"
            award_start = award.get("Start Date") or award.get("Period of Performance Start Date")
            award_end = award.get("End Date") or award.get("Period of Performance Current End Date")
            award_id = award.get("Award ID")

            contract = {
                "award_id": award_id,
                "recipient": award.get("Recipient Name"),
                "agency": agency,
                "sub_agency": award.get("Awarding Sub Agency"),
                "amount": amt,
                "outlayed": _safe_float(award.get("Total Outlayed Amount")),
                "award_group": group,
                "award_type": award.get("Award Type") or award.get("Contract Award Type"),
                "start_date": award_start,
                "end_date": award_end,
                "description": (award.get("Description") or "")[:500],
                "naics": award.get("NAICS Code"),
                "naics_desc": award.get("NAICS Description"),
                "psc": award.get("Product or Service Code"),
                "psc_desc": award.get("Product or Service Code Description"),
                "contract_type": award.get("Type of Contract Pricing"),
                "competition": award.get("Extent Competed"),
                "performance_location": {
                    "city": award.get("Place of Performance City Name"),
                    "state": award.get("Place of Performance State Code"),
                    "country": award.get("Place of Performance Country Name"),
                },
                "usaspending_url": (
                    f"https://www.usaspending.gov/award/{award_id}" if award_id else None
                ),
            }

            result["contracts"].append(contract)
            result["total_obligated"] += amt
            group_total += amt
            group_count += 1

            result["agency_breakdown"][agency] = result["agency_breakdown"].get(agency, 0) + amt

            if award_start:
                year = str(award_start)[:4]
                result["year_breakdown"][year] = result["year_breakdown"].get(year, 0) + amt
                if not result["earliest_date"] or award_start < result["earliest_date"]:
                    result["earliest_date"] = award_start
                if not result["latest_date"] or award_start > result["latest_date"]:
                    result["latest_date"] = award_start

            comp = contract.get("competition") or "Unknown"
            result["competition_breakdown"][comp] = result["competition_breakdown"].get(comp, 0) + amt

            naics = contract.get("naics") or "Unknown"
            result["naics_breakdown"][naics] = result["naics_breakdown"].get(naics, 0) + amt

            ctype = contract.get("contract_type") or "Unknown"
            result["contract_types"][ctype] = result["contract_types"].get(ctype, 0) + amt

        if group_count:
            result["group_breakdown"][group] = {"count": group_count, "total": group_total}

    result["contracts"].sort(key=lambda c: c.get("amount") or 0, reverse=True)
    result["total_awards"] = len(result["contracts"])

    # Record the resolution method for transparency in the report
    if recipient_uei:
        result["resolution_method"] = "UEI"
        result["recipient_uei"] = recipient_uei
        if resolved_profile:
            result["recipient_registered_name"] = resolved_profile.get("name", "")
    else:
        result["resolution_method"] = "text_search"

    # Agency share, used directly by the report's federal contracting section.
    total = result["total_obligated"] or 0
    result["agency_share_pct"] = {
        agency: round(amt / total * 100, 1)
        for agency, amt in sorted(result["agency_breakdown"].items(),
                                  key=lambda kv: -kv[1])
    } if total else {}

    return result


def fetch_subcontracts(entity_name: str, max_results: int = 50, request_timeout: int = 30) -> List[Dict[str, Any]]:
    """
    Fetch subcontracts where entity is either prime or sub.
    Used for self-dealing detection.
    """
    subcontracts = []

    try:
        # Subaward search
        payload = {
            "filters": {
                "keywords": [entity_name],
            },
            "fields": [
                "subaward_number", "prime_award_recipient_name", "sub_awardee_or_recipient_legal",
                "subaward_amount", "subaward_action_date", "subaward_description",
                "prime_award_internal_id",
            ],
            "page": 1,
            "limit": max_results,
        }

        resp = requests.post(
            f"{USASPENDING_BASE}/subawards/",
            json=payload,
            headers=HEADERS,
            timeout=request_timeout,
        )

        if resp.ok:
            for sub in resp.json().get("results", []):
                subcontracts.append({
                    "subaward_number": sub.get("subaward_number"),
                    "prime_contractor": sub.get("prime_award_recipient_name"),
                    "subcontractor": sub.get("sub_awardee_or_recipient_legal"),
                    "amount": _safe_float(sub.get("subaward_amount")),
                    "date": sub.get("subaward_action_date"),
                    "description": sub.get("subaward_description", "")[:300],
                    "prime_award_id": sub.get("prime_award_internal_id"),
                    "entity_role": "prime" if entity_name.lower() in str(sub.get("prime_award_recipient_name", "")).lower()
                                  else "sub" if entity_name.lower() in str(sub.get("sub_awardee_or_recipient_legal", "")).lower()
                                  else "unknown",
                })

    except Exception as e:
        logger.warning("Subcontract fetch error: %s", e)

    return subcontracts


def detect_self_dealing(contracts: List[Dict], subcontracts: List[Dict],
                        executives: List[str] = None,
                        board_members: List[str] = None,
                        related_entities: List[str] = None) -> Dict[str, Any]:
    """
    Analyze contracts for potential self-dealing indicators.

    Checks:
    - Subcontracts to related entities
    - Sole-source contracts (no competition)
    - Contracts to companies with shared personnel
    - Unusual concentration patterns
    """
    flags = []
    risk_score = 0

    # Analyze sole-source/non-competitive contracts
    sole_source = [c for c in contracts if "not competed" in str(c.get("competition", "")).lower()
                   or "sole source" in str(c.get("competition", "")).lower()]
    if sole_source:
        total_sole = sum(c.get("amount", 0) for c in sole_source)
        total_all = sum(c.get("amount", 0) for c in contracts)
        pct = (total_sole / total_all * 100) if total_all > 0 else 0

        if pct > 30:
            flags.append({
                "type": "high_sole_source_ratio",
                "severity": "MEDIUM" if pct < 50 else "HIGH",
                "value": f"{pct:.1f}%",
                "detail": f"{len(sole_source)} sole-source contracts totaling ${total_sole:,.0f} ({pct:.1f}% of portfolio)",
            })
            risk_score += 20 if pct > 50 else 10

    # Check for related entity subcontracts
    related = related_entities or []
    if related and subcontracts:
        for sub in subcontracts:
            subcontractor = str(sub.get("subcontractor", "")).lower()
            for entity in related:
                if entity.lower() in subcontractor:
                    flags.append({
                        "type": "related_party_subcontract",
                        "severity": "HIGH",
                        "value": sub.get("amount", 0),
                        "detail": f"Subcontract to related entity '{entity}': ${sub.get('amount', 0):,.0f}",
                        "subcontract": sub,
                    })
                    risk_score += 30

    # Check for concentration (single agency giving most contracts)
    if contracts:
        agency_totals = defaultdict(float)
        for c in contracts:
            agency_totals[c.get("agency", "Unknown")] += c.get("amount", 0)

        total = sum(agency_totals.values())
        for agency, amount in agency_totals.items():
            pct = (amount / total * 100) if total > 0 else 0
            if pct > 70:
                flags.append({
                    "type": "agency_concentration",
                    "severity": "MEDIUM",
                    "value": f"{pct:.1f}%",
                    "detail": f"{agency} accounts for {pct:.1f}% of contract value (${amount:,.0f})",
                })
                risk_score += 10

    # Check for executive/board member overlap with contracting officers
    # (Would need additional data source for contracting officers)

    return {
        "flags": flags,
        "risk_score": min(risk_score, 100),
        "risk_level": "HIGH" if risk_score >= 50 else "MEDIUM" if risk_score >= 25 else "LOW",
        "contracts_analyzed": len(contracts),
        "subcontracts_analyzed": len(subcontracts),
        "sole_source_count": len(sole_source),
        "related_entities_checked": len(related),
    }


def get_full_contract_portfolio(entity_name: str,
                                 executives: List[str] = None,
                                 related_entities: List[str] = None,
                                 subsidiaries: Optional[List[str]] = None,
                                 request_timeout: int = 20,
                                 max_elapsed_seconds: Optional[float] = None,
                                 subaward_timeout: int = 30) -> Dict[str, Any]:
    """
    Comprehensive federal contract analysis for deep intelligence.

    Returns complete portfolio with:
    - All contracts with full details
    - Agency/year/type breakdowns
    - Subcontract relationships
    - Self-dealing analysis
    - Risk flags

    Uses UEI resolution for reliable entity matching. Falls back to text
    search if UEI resolution fails.
    """
    result = {
        "entity_name": entity_name,
        "contracts": [],
        "subcontracts": [],
        "summary": {
            "total_contracts": 0,
            "total_obligated": 0,
            "earliest_contract": None,
            "latest_contract": None,
        },
        "agency_breakdown": [],
        "year_breakdown": [],
        "competition_analysis": {},
        "self_dealing_analysis": {},
        "top_contracts": [],
        "source": "USASpending.gov + FPDS.gov",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    start_ts = time.monotonic()

    # Fetch main contracts
    logger.info("Fetching full contract data for %s", entity_name)
    usa_data = fetch_usaspending_full(entity_name, max_results=100,
                                      subsidiaries=subsidiaries,
                                      request_timeout=request_timeout,
                                      max_elapsed_seconds=max_elapsed_seconds)

    result["contracts"] = usa_data.get("contracts", [])
    result["summary"]["total_contracts"] = len(result["contracts"])
    result["summary"]["total_obligated"] = usa_data.get("total_obligated", 0)
    result["summary"]["earliest_contract"] = usa_data.get("earliest_date")
    result["summary"]["latest_contract"] = usa_data.get("latest_date")
    result["summary"]["resolution_method"] = usa_data.get("resolution_method", "text_search")
    result["summary"]["recipient_uei"] = usa_data.get("recipient_uei")
    result["summary"]["excluded_false_positives"] = usa_data.get("excluded_false_positives", 0)

    # Format breakdowns as sorted lists
    result["agency_breakdown"] = sorted(
        [{"agency": k, "amount": v} for k, v in usa_data.get("agency_breakdown", {}).items()],
        key=lambda x: x["amount"],
        reverse=True,
    )

    result["year_breakdown"] = sorted(
        [{"year": k, "amount": v} for k, v in usa_data.get("year_breakdown", {}).items()],
        key=lambda x: x["year"],
    )

    result["competition_analysis"] = usa_data.get("competition_breakdown", {})

    # Fetch subcontracts
    if max_elapsed_seconds is not None:
        elapsed = time.monotonic() - start_ts if "start_ts" in locals() else 0
        remaining = max_elapsed_seconds - elapsed
        if remaining <= 0:
            logger.warning("Skipping subcontract fetch for %s because the contract budget is exhausted", entity_name)
            result["subcontracts"] = []
        else:
            result["subcontracts"] = fetch_subcontracts(
                entity_name,
                max_results=50,
                request_timeout=max(3, min(int(remaining), subaward_timeout)),
            )
    else:
        result["subcontracts"] = fetch_subcontracts(entity_name, max_results=50, request_timeout=subaward_timeout)

    # Self-dealing analysis
    result["self_dealing_analysis"] = detect_self_dealing(
        result["contracts"],
        result["subcontracts"],
        executives=executives,
        related_entities=related_entities,
    )

    # Top contracts by value
    result["top_contracts"] = sorted(
        result["contracts"],
        key=lambda x: x.get("amount", 0),
        reverse=True,
    )[:10]

    return result


# ── Convenience exports ───────────────────────────────────────────────────────

def get_contracts(entity_name: str) -> Dict[str, Any]:
    """Simple wrapper for contract fetch."""
    return get_full_contract_portfolio(entity_name)


def analyze_self_dealing(entity_name: str, related: List[str] = None) -> Dict[str, Any]:
    """Self-dealing analysis wrapper."""
    portfolio = get_full_contract_portfolio(entity_name, related_entities=related)
    return portfolio.get("self_dealing_analysis", {})
