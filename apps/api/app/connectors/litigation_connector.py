"""
Litigation & Regulatory Docket Intelligence Connector
────────────────────────────────────────────────────────────────────────────
Track and analyze legal/regulatory proceedings for deep intelligence:
  - SEC enforcement actions and investigations
  - Federal court cases (via CourtListener/RECAP)
  - FTC proceedings and consent decrees
  - Patent litigation (PTAB, ITC)
  - Class action securities lawsuits
  - Antitrust investigations
  - Government contract disputes (GAO, COFC)

Critical for understanding:
  - Regulatory risk exposure
  - Material litigation contingencies
  - Patent portfolio defense/offense
  - Government enforcement trends

Usage:
    from app.connectors.litigation_connector import (
        get_litigation_intelligence,
        track_sec_enforcement,
        search_federal_cases,
    )
    litigation = get_litigation_intelligence("NVIDIA Corporation")
"""
import os
import re
import time
import logging
import requests
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from bs4 import BeautifulSoup

from app.connectors.entity_naming import (
    entity_in_caption,
    entity_search_term,
    matches_entity,
)

logger = logging.getLogger(__name__)

# API configurations
SEC_HEADERS = {"User-Agent": os.getenv("SEC_USER_AGENT", "FinanceIntelPlatform/1.0 research@example.com")}
# The token is stored as COURTLISTENER_API_TOKEN; the older _API_KEY name is
# still accepted so existing deployments keep working.
COURTLISTENER_TOKEN = (
    os.getenv("COURTLISTENER_API_TOKEN") or os.getenv("COURTLISTENER_API_KEY") or ""
)
# v3 was retired and now returns HTTP 403 for every request, which silently
# emptied the entire litigation section.
COURTLISTENER_SEARCH_URL = "https://www.courtlistener.com/api/rest/v4/search/"

# Court identifiers for federal district courts
FEDERAL_COURTS = [
    "dcd",   # District of Columbia
    "cand",  # Northern District of California
    "casd",  # Southern District of California
    "cacd",  # Central District of California
    "txnd",  # Northern District of Texas
    "txsd",  # Southern District of Texas
    "nysd",  # Southern District of New York
    "nyed",  # Eastern District of New York
    "deld",  # District of Delaware
    "ilnd",  # Northern District of Illinois
]

# Case type classifications
CASE_TYPES = {
    "securities": ["10b-5", "securities fraud", "shareholder derivative", "class action"],
    "antitrust": ["antitrust", "sherman act", "monopoly", "price fixing"],
    "patent": ["patent infringement", "trade secret", "misappropriation"],
    "employment": ["discrimination", "wrongful termination", "wage", "labor"],
    "product": ["product liability", "defect", "injury", "recall"],
    "regulatory": ["sec", "ftc", "doj", "enforcement", "consent decree"],
    "contract": ["breach of contract", "tortious interference"],
    "ip": ["trademark", "copyright", "trade dress"],
}


def _search_courtlistener(
    query: str,
    filed_after: str = "",
    court: str = "",
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Search CourtListener for federal court cases.

    CourtListener provides free access to PACER/RECAP data.

    Args:
        query: Search query (company name, case number, etc.)
        filed_after: Filter by filing date (YYYY-MM-DD)
        court: Court ID filter
        limit: Maximum results

    Returns:
        List of case summaries.
    """
    cases = []

    try:
        headers = {"Authorization": f"Token {COURTLISTENER_TOKEN}"} if COURTLISTENER_TOKEN else {}

        params = {
            "q": query,
            "order_by": "dateFiled desc",
            "type": "o",  # opinions
        }

        if filed_after:
            params["filed_after"] = filed_after
        if court:
            params["court"] = court

        # Search opinions
        resp = requests.get(
            COURTLISTENER_SEARCH_URL,
            params=params,
            headers=headers,
            timeout=30,
        )

        if resp.ok:
            data = resp.json()
            results = data.get("results", [])[:limit]

            for result in results:
                cases.append({
                    "case_name": result.get("caseName", ""),
                    "docket_number": result.get("docketNumber", ""),
                    "court": result.get("court", ""),
                    "date_filed": result.get("dateFiled", ""),
                    "date_argued": result.get("dateArgued", ""),
                    "date_decided": result.get("date_created", ""),
                    "status": result.get("status", ""),
                    "citation": result.get("citation", []),
                    "absolute_url": result.get("absolute_url", ""),
                    "snippet": result.get("snippet", ""),
                })

    except Exception as e:
        logger.warning("CourtListener search failed for '%s': %s", query, e)

    return cases


def _search_courtlistener_dockets(
    query: str,
    filed_after: str = "",
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Search CourtListener dockets."""
    dockets = []

    try:
        headers = {"Authorization": f"Token {COURTLISTENER_TOKEN}"} if COURTLISTENER_TOKEN else {}

        params = {
            "q": query,
            "order_by": "dateFiled desc",
            "type": "r",  # RECAP dockets
        }

        if filed_after:
            params["filed_after"] = filed_after

        resp = requests.get(
            COURTLISTENER_SEARCH_URL,
            params=params,
            headers=headers,
            timeout=30,
        )

        if resp.ok:
            data = resp.json()
            results = data.get("results", [])[:limit]

            for result in results:
                dockets.append({
                    "case_name": result.get("caseName", ""),
                    "docket_number": result.get("docketNumber", ""),
                    "court": result.get("court", ""),
                    "date_filed": result.get("dateFiled", ""),
                    "date_terminated": result.get("dateTerminated", ""),
                    "assigned_to": result.get("assignedTo", ""),
                    "referred_to": result.get("referredTo", ""),
                    "cause": result.get("cause", ""),
                    "nature_of_suit": result.get("suitNature", ""),
                    "jury_demand": result.get("juryDemand", ""),
                    "absolute_url": result.get("absolute_url", ""),
                })

    except Exception as e:
        logger.warning("CourtListener docket search failed for '%s': %s", query, e)

    return dockets


def _classify_case(case_name: str, cause: str = "", nature_of_suit: str = "") -> str:
    """Classify a case into case type categories."""
    text = f"{case_name} {cause} {nature_of_suit}".lower()

    for case_type, keywords in CASE_TYPES.items():
        for keyword in keywords:
            if keyword in text:
                return case_type

    return "other"


def _search_sec_enforcement(
    entity_name: str,
    years: int = 5,
) -> List[Dict[str, Any]]:
    """
    Search SEC enforcement actions and litigation releases.

    The SEC publishes:
    - Litigation Releases (LRs)
    - Administrative Proceedings (APs)
    - Trading Suspensions
    - Stop Orders
    """
    actions = []

    try:
        # Search SEC EFTS for enforcement-related filings
        params = {
            "q": f'"{entity_name}"',
            "dateRange": "custom",
            "startdt": (datetime.now() - timedelta(days=years*365)).strftime("%Y-%m-%d"),
            "enddt": datetime.now().strftime("%Y-%m-%d"),
        }

        resp = requests.get(
            "https://efts.sec.gov/LATEST/search-index",
            params=params,
            headers=SEC_HEADERS,
            timeout=20,
        )

        if resp.ok:
            data = resp.json()
            hits = data.get("hits", {}).get("hits", [])

            for hit in hits:
                src = hit.get("_source", {})
                form = src.get("form", "")

                # Filter for enforcement-related forms
                if any(kw in form for kw in ["LR", "AP", "AAER", "34-"]):
                    names = src.get("display_names", [])

                    actions.append({
                        "title": src.get("file_description", ""),
                        "form_type": form,
                        "filing_date": src.get("file_date", ""),
                        "entity": names[0] if names else entity_name,
                        "accession": hit.get("_id", ""),
                        "source": "SEC Enforcement",
                    })

    except Exception as e:
        logger.warning("SEC enforcement search failed for '%s': %s", entity_name, e)

    # Also search SEC litigation releases page
    try:
        resp = requests.get(
            "https://www.sec.gov/litigation/litreleases.htm",
            headers=SEC_HEADERS,
            timeout=20,
        )

        if resp.ok:
            soup = BeautifulSoup(resp.text, "html.parser")
            entity_lower = entity_name.lower()

            # Find links mentioning entity
            for link in soup.find_all("a"):
                text = link.get_text().lower()
                if entity_lower in text or any(
                    word in text for word in entity_name.lower().split()[:2]
                ):
                    href = link.get("href", "")
                    if "/litigation/litrelease" in href:
                        actions.append({
                            "title": link.get_text(strip=True)[:200],
                            "form_type": "LR",
                            "filing_date": "",  # Would need to parse from page
                            "entity": entity_name,
                            "url": f"https://www.sec.gov{href}" if href.startswith("/") else href,
                            "source": "SEC Litigation Release",
                        })

    except Exception as e:
        logger.warning("SEC litigation release search failed: %s", e)

    return actions


# Navigation links and editorial content the FTC listing page renders inside the
# same markup as real matters. Counting these inflated the litigation total and
# fed a spurious "material litigation exposure" risk into the register.
FTC_BOILERPLATE_TITLES = {
    "cases and proceedings", "press release", "press releases", "blog post",
    "advocacy", "public statement", "event", "speech", "testimony",
    "refunds", "competition matters", "consumer protection matters",
}


def _entity_is_party(case_name: str, entity_name: str) -> bool:
    """
    True when the entity appears in the case caption rather than only in the
    opinion text. Full-text search returns both, and conflating them overstates
    litigation exposure — a patent suit between two other firms that cites the
    company is not a matter against it.
    """
    return entity_in_caption(case_name, entity_name)


def _is_real_ftc_matter(title: str, entity_name: str) -> bool:
    """A genuine matter names the entity and is not site boilerplate."""
    clean = (title or "").strip()
    if not clean or clean.lower() in FTC_BOILERPLATE_TITLES:
        return False
    # FTC titles read as captions ("FTC v. <Company>", "<Company>, In the
    # Matter of"), so match party-wise rather than against the whole string.
    return entity_in_caption(clean.replace(", In the Matter of", ""), entity_name)


def _search_ftc_proceedings(entity_name: str) -> List[Dict[str, Any]]:
    """
    Search FTC for antitrust and consumer protection proceedings.

    FTC data sources:
    - Cases and Proceedings
    - Consent Decrees
    - Merger Reviews (HSR)
    """
    proceedings = []

    try:
        # FTC cases API
        resp = requests.get(
            "https://www.ftc.gov/enforcement/cases-proceedings",
            params={"search_api_fulltext": entity_name},
            headers={"User-Agent": SEC_HEADERS["User-Agent"]},
            timeout=20,
        )

        if resp.ok:
            soup = BeautifulSoup(resp.text, "html.parser")

            # Parse case listings
            for case in soup.select(".view-content .views-row")[:20]:
                title_elem = case.select_one("a")
                date_elem = case.select_one(".date-display-single")

                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)
                if not _is_real_ftc_matter(title, entity_name):
                    continue
                proceedings.append({
                    "title": title,
                    "url": title_elem.get("href", ""),
                    "date": date_elem.get_text(strip=True) if date_elem else "",
                    "agency": "FTC",
                    "type": "enforcement",
                })

    except Exception as e:
        logger.warning("FTC search failed for '%s': %s", entity_name, e)

    return proceedings


def _search_doj_antitrust(entity_name: str) -> List[Dict[str, Any]]:
    """Search DOJ Antitrust Division for cases."""
    cases = []

    try:
        # DOJ Antitrust case search
        resp = requests.get(
            "https://www.justice.gov/atr/case/search",
            params={"keyword": entity_name},
            headers={"User-Agent": SEC_HEADERS["User-Agent"]},
            timeout=20,
        )

        if resp.ok:
            soup = BeautifulSoup(resp.text, "html.parser")

            for case in soup.select(".view-atr-case-search .views-row")[:20]:
                title_elem = case.select_one("a")
                if title_elem:
                    cases.append({
                        "title": title_elem.get_text(strip=True),
                        "url": f"https://www.justice.gov{title_elem.get('href', '')}",
                        "agency": "DOJ Antitrust",
                        "type": "antitrust",
                    })

    except Exception as e:
        logger.warning("DOJ Antitrust search failed for '%s': %s", entity_name, e)

    return cases


def _search_ptab(entity_name: str) -> List[Dict[str, Any]]:
    """
    Search Patent Trial and Appeal Board proceedings.

    PTAB handles:
    - Inter Partes Review (IPR)
    - Post-Grant Review (PGR)
    - Covered Business Method Review (CBM)
    """
    proceedings = []

    # Note: PTAB API requires registration
    # This is a placeholder for the structure
    logger.info("PTAB search for '%s' - requires PTAB API access", entity_name)

    return proceedings


def _search_itc(entity_name: str) -> List[Dict[str, Any]]:
    """
    Search International Trade Commission Section 337 investigations.

    ITC handles patent/IP cases involving imports.
    """
    investigations = []

    try:
        resp = requests.get(
            "https://www.usitc.gov/intellectual_property/337_702_tab_702.htm",
            headers={"User-Agent": SEC_HEADERS["User-Agent"]},
            timeout=20,
        )

        if resp.ok:
            soup = BeautifulSoup(resp.text, "html.parser")
            entity_lower = entity_name.lower()

            # Parse investigation table
            for row in soup.select("table tr"):
                text = row.get_text().lower()
                if entity_lower in text or any(
                    word in text for word in entity_name.lower().split()[:2]
                ):
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        investigations.append({
                            "investigation": cells[0].get_text(strip=True),
                            "description": cells[1].get_text(strip=True)[:200],
                            "agency": "ITC",
                            "type": "section_337",
                        })

    except Exception as e:
        logger.warning("ITC search failed for '%s': %s", entity_name, e)

    return investigations


def search_federal_cases(
    entity_name: str,
    years: int = 5,
    case_types: List[str] = None,
) -> Dict[str, Any]:
    """
    Search for federal court cases involving an entity.

    Args:
        entity_name: Company or person name
        years: How many years back to search
        case_types: Filter by case type (securities, antitrust, patent, etc.)

    Returns:
        Federal case search results.
    """
    case_types = case_types or []
    filed_after = (datetime.now() - timedelta(days=years*365)).strftime("%Y-%m-%d")

    result = {
        "entity": entity_name,
        "search_period_years": years,
        "cases": [],
        "by_type": defaultdict(list),
        "by_court": defaultdict(list),
        "summary": {
            "total_cases": 0,
            "active_cases": 0,
            "terminated_cases": 0,
        },
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    # Quote the search term so CourtListener matches the phrase rather than the
    # individual words. Unquoted, a company named for an everyday word pulls in
    # every opinion that happens to use it: searching Target returned "United
    # States v. Lopez" and "Intel Corp v. Nvidia Corp".
    query = f'"{entity_search_term(entity_name)}"'
    opinions = _search_courtlistener(query, filed_after=filed_after, limit=100)
    dockets = _search_courtlistener_dockets(query, filed_after=filed_after, limit=100)

    # Combine and deduplicate
    seen_docket_numbers = set()

    for docket in dockets:
        docket_num = docket.get("docket_number", "")
        if docket_num in seen_docket_numbers:
            continue
        seen_docket_numbers.add(docket_num)

        # Classify the case
        case_type = _classify_case(
            docket.get("case_name", ""),
            docket.get("cause", ""),
            docket.get("nature_of_suit", ""),
        )

        # Filter by case type if specified
        if case_types and case_type not in case_types:
            continue

        case_entry = {
            **docket,
            "case_type": case_type,
            "entity_is_party": _entity_is_party(docket.get("case_name", ""), entity_name),
            "source": "CourtListener/RECAP",
        }

        result["cases"].append(case_entry)
        result["by_type"][case_type].append(case_entry)
        result["by_court"][docket.get("court", "unknown")].append(case_entry)

        # Track status
        if docket.get("date_terminated"):
            result["summary"]["terminated_cases"] += 1
        else:
            result["summary"]["active_cases"] += 1

    # Add opinions that aren't in dockets
    for opinion in opinions:
        docket_num = opinion.get("docket_number", "")
        if docket_num and docket_num in seen_docket_numbers:
            continue

        case_type = _classify_case(opinion.get("case_name", ""))

        if case_types and case_type not in case_types:
            continue

        case_entry = {
            **opinion,
            "case_type": case_type,
            "entity_is_party": _entity_is_party(opinion.get("case_name", ""), entity_name),
            "source": "CourtListener Opinion",
        }

        result["cases"].append(case_entry)
        result["by_type"][case_type].append(case_entry)

    # Full-text search also returns matters that merely cite the entity. Sort
    # cases where it is an actual party first and count them separately, so the
    # headline figure reflects real exposure rather than search recall.
    result["cases"].sort(key=lambda c: (not c.get("entity_is_party"),
                                        c.get("date_filed") or ""), reverse=False)
    result["cases"].sort(key=lambda c: not c.get("entity_is_party"))
    result["summary"]["total_cases"] = len(result["cases"])
    result["summary"]["cases_as_party"] = sum(
        1 for c in result["cases"] if c.get("entity_is_party")
    )
    result["summary"]["cases_mentioning_only"] = (
        result["summary"]["total_cases"] - result["summary"]["cases_as_party"]
    )

    return result


def track_sec_enforcement(
    entity_name: str,
    years: int = 5,
) -> Dict[str, Any]:
    """
    Track SEC enforcement actions against an entity.

    Args:
        entity_name: Company name
        years: Years to search back

    Returns:
        SEC enforcement action summary.
    """
    result = {
        "entity": entity_name,
        "search_period_years": years,
        "enforcement_actions": [],
        "litigation_releases": [],
        "administrative_proceedings": [],
        "summary": {
            "total_actions": 0,
            "by_type": {},
        },
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    actions = _search_sec_enforcement(entity_name, years)

    for action in actions:
        form_type = action.get("form_type", "")

        if "LR" in form_type:
            result["litigation_releases"].append(action)
        elif "AP" in form_type or "AAER" in form_type:
            result["administrative_proceedings"].append(action)
        else:
            result["enforcement_actions"].append(action)

    result["summary"]["total_actions"] = len(actions)
    result["summary"]["by_type"] = {
        "litigation_releases": len(result["litigation_releases"]),
        "administrative_proceedings": len(result["administrative_proceedings"]),
        "other_enforcement": len(result["enforcement_actions"]),
    }

    return result


def get_litigation_intelligence(
    entity_name: str,
    ticker: str = "",
    years: int = 5,
) -> Dict[str, Any]:
    """
    Comprehensive litigation and regulatory intelligence.

    Aggregates:
    - Federal court cases
    - SEC enforcement
    - FTC proceedings
    - DOJ Antitrust
    - ITC investigations
    - PTAB proceedings

    Args:
        entity_name: Company name
        ticker: Stock ticker (optional, for additional searches)
        years: Years to search back

    Returns:
        Complete litigation intelligence payload.
    """
    result = {
        "entity": entity_name,
        "ticker": ticker,
        "search_period_years": years,
        "federal_cases": {},
        "sec_enforcement": {},
        "ftc_proceedings": [],
        "doj_antitrust": [],
        "itc_investigations": [],
        "ptab_proceedings": [],
        "risk_assessment": {
            "overall_risk": "UNKNOWN",
            "litigation_exposure": "UNKNOWN",
            "regulatory_risk": "UNKNOWN",
            "patent_risk": "UNKNOWN",
        },
        "flags": [],
        "summary": {
            "total_matters": 0,
            "active_matters": 0,
            "high_risk_matters": 0,
        },
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    # Federal court cases
    logger.info("Searching federal cases for '%s'", entity_name)
    result["federal_cases"] = search_federal_cases(entity_name, years)

    # SEC enforcement
    logger.info("Searching SEC enforcement for '%s'", entity_name)
    result["sec_enforcement"] = track_sec_enforcement(entity_name, years)

    # FTC proceedings
    logger.info("Searching FTC for '%s'", entity_name)
    result["ftc_proceedings"] = _search_ftc_proceedings(entity_name)

    # DOJ Antitrust
    logger.info("Searching DOJ Antitrust for '%s'", entity_name)
    result["doj_antitrust"] = _search_doj_antitrust(entity_name)

    # ITC investigations
    logger.info("Searching ITC for '%s'", entity_name)
    result["itc_investigations"] = _search_itc(entity_name)

    # PTAB (placeholder)
    result["ptab_proceedings"] = _search_ptab(entity_name)

    # Calculate totals
    total_matters = (
        result["federal_cases"].get("summary", {}).get("total_cases", 0) +
        result["sec_enforcement"].get("summary", {}).get("total_actions", 0) +
        len(result["ftc_proceedings"]) +
        len(result["doj_antitrust"]) +
        len(result["itc_investigations"]) +
        len(result["ptab_proceedings"])
    )

    active_matters = (
        result["federal_cases"].get("summary", {}).get("active_cases", 0) +
        # Assume SEC actions are active unless clearly historical
        len(result["sec_enforcement"].get("enforcement_actions", [])) +
        len(result["ftc_proceedings"]) +
        len(result["doj_antitrust"])
    )

    result["summary"]["total_matters"] = total_matters
    result["summary"]["active_matters"] = active_matters

    # Risk assessment
    sec_count = result["sec_enforcement"].get("summary", {}).get("total_actions", 0)
    antitrust_count = len(result["doj_antitrust"]) + len(result["ftc_proceedings"])
    securities_cases = len(result["federal_cases"].get("by_type", {}).get("securities", []))

    # Litigation exposure
    if total_matters > 20:
        result["risk_assessment"]["litigation_exposure"] = "HIGH"
    elif total_matters > 10:
        result["risk_assessment"]["litigation_exposure"] = "MEDIUM"
    else:
        result["risk_assessment"]["litigation_exposure"] = "LOW"

    # Regulatory risk
    if sec_count >= 3 or antitrust_count >= 2:
        result["risk_assessment"]["regulatory_risk"] = "HIGH"
        result["flags"].append({
            "type": "high_regulatory_risk",
            "severity": "HIGH",
            "detail": f"Multiple regulatory actions: {sec_count} SEC, {antitrust_count} antitrust",
        })
    elif sec_count >= 1 or antitrust_count >= 1:
        result["risk_assessment"]["regulatory_risk"] = "MEDIUM"
    else:
        result["risk_assessment"]["regulatory_risk"] = "LOW"

    # Patent risk
    patent_matters = (
        len(result["federal_cases"].get("by_type", {}).get("patent", [])) +
        len(result["itc_investigations"]) +
        len(result["ptab_proceedings"])
    )
    if patent_matters > 10:
        result["risk_assessment"]["patent_risk"] = "HIGH"
    elif patent_matters > 5:
        result["risk_assessment"]["patent_risk"] = "MEDIUM"
    else:
        result["risk_assessment"]["patent_risk"] = "LOW"

    # Overall risk
    high_risks = sum(1 for v in result["risk_assessment"].values() if v == "HIGH")
    if high_risks >= 2:
        result["risk_assessment"]["overall_risk"] = "HIGH"
    elif high_risks >= 1 or result["risk_assessment"]["litigation_exposure"] == "MEDIUM":
        result["risk_assessment"]["overall_risk"] = "MEDIUM"
    else:
        result["risk_assessment"]["overall_risk"] = "LOW"

    # Generate flags for specific issues
    if securities_cases > 3:
        result["flags"].append({
            "type": "securities_litigation",
            "severity": "HIGH",
            "detail": f"{securities_cases} securities-related cases found",
        })
        result["summary"]["high_risk_matters"] += securities_cases

    if result["sec_enforcement"].get("litigation_releases"):
        result["flags"].append({
            "type": "sec_litigation_release",
            "severity": "HIGH",
            "detail": f"{len(result['sec_enforcement']['litigation_releases'])} SEC litigation releases",
        })

    return result


def generate_legal_timeline(
    litigation_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Generate chronological timeline of legal events.

    Args:
        litigation_data: Output from get_litigation_intelligence

    Returns:
        Sorted list of legal events with dates.
    """
    events = []

    # Federal cases
    for case in litigation_data.get("federal_cases", {}).get("cases", []):
        if case.get("date_filed"):
            events.append({
                "date": case["date_filed"],
                "event_type": "case_filed",
                "case_type": case.get("case_type", ""),
                "title": case.get("case_name", ""),
                "court": case.get("court", ""),
                "source": "Federal Court",
            })
        if case.get("date_terminated"):
            events.append({
                "date": case["date_terminated"],
                "event_type": "case_terminated",
                "case_type": case.get("case_type", ""),
                "title": case.get("case_name", ""),
                "court": case.get("court", ""),
                "source": "Federal Court",
            })

    # SEC actions
    for action in litigation_data.get("sec_enforcement", {}).get("enforcement_actions", []):
        if action.get("filing_date"):
            events.append({
                "date": action["filing_date"],
                "event_type": "sec_action",
                "title": action.get("title", ""),
                "form_type": action.get("form_type", ""),
                "source": "SEC",
            })

    for lr in litigation_data.get("sec_enforcement", {}).get("litigation_releases", []):
        if lr.get("filing_date"):
            events.append({
                "date": lr["filing_date"],
                "event_type": "sec_litigation_release",
                "title": lr.get("title", ""),
                "source": "SEC",
            })

    # Sort by date descending
    events.sort(key=lambda x: x.get("date", ""), reverse=True)

    return events


# ── Convenience Exports ──────────────────────────────────────────────────────

def get_federal_cases(entity: str, years: int = 5) -> Dict[str, Any]:
    """Search federal court cases."""
    return search_federal_cases(entity, years)


def get_sec_enforcement(entity: str, years: int = 5) -> Dict[str, Any]:
    """Track SEC enforcement actions."""
    return track_sec_enforcement(entity, years)


def get_full_litigation(entity: str, ticker: str = "", years: int = 5) -> Dict[str, Any]:
    """Get comprehensive litigation intelligence."""
    return get_litigation_intelligence(entity, ticker, years)


def get_legal_timeline(entity: str, years: int = 5) -> List[Dict[str, Any]]:
    """Get chronological legal event timeline."""
    litigation = get_litigation_intelligence(entity, years=years)
    return generate_legal_timeline(litigation)
