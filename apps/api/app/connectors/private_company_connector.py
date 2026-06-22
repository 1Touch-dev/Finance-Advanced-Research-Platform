"""
Private company intelligence connector — three free public data sources:

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

All functions return empty dicts if the API is unreachable, so the pipeline
degrades gracefully.
"""
import os
import logging
import requests
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

_OPENCORP_BASE = "https://api.opencorporates.com/v0.4"
_GLEIF_BASE    = "https://api.gleif.org/api/v1"
_FINCEN_BASE   = "https://efts.fincen.gov/financial_institution_search/api"
_FDIC_BASE     = "https://banks.data.fdic.gov/api"

_OC_API_TOKEN = os.getenv("OPENCORPORATES_API_TOKEN", "")  # optional; improves rate limit


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

    return {
        "ultimate_parent": ultimate,
        "direct_parent":   direct,
    }


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
