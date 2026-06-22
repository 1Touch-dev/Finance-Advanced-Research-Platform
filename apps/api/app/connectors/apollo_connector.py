"""
Apollo.io connector — people search, email enrichment, org chart, domain intel.

Apollo.io provides:
  - /people/search  → find people by name + org
  - /people/match   → enrich a person by email/name/org
  - /organizations/search → company search with employee count, revenue, SIC, etc.
  - /organizations/enrich → domain-based company enrichment

APOLLO_API_KEY must be in .env.  If missing, all functions return empty dicts
so the rest of the intelligence pipeline degrades gracefully.
"""
import os
import logging
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_APOLLO_BASE = "https://api.apollo.io/v1"
_API_KEY = os.getenv("APOLLO_API_KEY", "")


def _headers() -> dict:
    return {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
        "X-Api-Key": _API_KEY,
    }


def _post(endpoint: str, payload: dict) -> dict:
    if not _API_KEY:
        logger.warning("APOLLO_API_KEY not set — skipping Apollo call")
        return {}
    try:
        r = requests.post(f"{_APOLLO_BASE}{endpoint}", json=payload, headers=_headers(), timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        logger.warning("Apollo %s failed: %s", endpoint, exc)
        return {}


# ── Organization enrichment ──────────────────────────────────────────────────

def enrich_organization(domain: str = "", name: str = "") -> dict:
    """
    Enrich a company by domain or name.
    Returns: { name, website, industry, founded_year, headcount, revenue_range,
               technologies, short_description, linkedin_url }
    Domain-based enrichment is always preferred — much more accurate.
    """
    payload = {}
    if domain:
        payload["domain"] = domain
    elif name:
        # Try to derive a domain from the name as a best-effort
        slug = name.lower().replace(" ", "").replace(".", "").replace(",", "")
        payload["domain"] = f"{slug}.com"
    else:
        return {}

    data = _post("/organizations/enrich", payload)
    org = data.get("organization") or {}

    # If domain-based failed, fall back to name-based
    if not org and name and not domain:
        payload = {"name": name}
        data = _post("/organizations/enrich", payload)
        org = data.get("organization") or {}

    if not org:
        return {}

    return {
        "name":              org.get("name", ""),
        "website":           org.get("website_url", "") or org.get("primary_domain", ""),
        "industry":          org.get("industry", ""),
        "founded_year":      org.get("founded_year"),
        "headcount":         org.get("num_employees", 0),
        "headcount_range":   org.get("employee_count") or org.get("estimated_num_employees", ""),
        "revenue_range":     org.get("revenue_range", ""),
        "annual_revenue":    org.get("annual_revenue"),
        "technologies":      [t.get("name","") for t in (org.get("technologies") or [])[:15]],
        "short_description": org.get("short_description", ""),
        "linkedin_url":      org.get("linkedin_url", ""),
        "keywords":          org.get("keywords") or [],
        "country":           org.get("country", ""),
        "city":              org.get("city", ""),
        "state":             org.get("state", ""),
        "alexa_rank":        org.get("alexa_ranking"),
        "seo_description":   org.get("seo_description", ""),
        "facebook_url":      org.get("facebook_url", ""),
        "twitter_url":       org.get("twitter_url", ""),
        "source":            "Apollo.io",
    }


def search_organization(name: str) -> dict:
    """
    Search Apollo for an org by name. Returns the top matching org's profile.
    Preferred over domain-guessing for accuracy.
    NOTE: Returns search result directly — no domain re-enrichment to avoid mismatches.
    """
    data = _post("/organizations/search", {
        "q_organization_name": name,
        "page": 1,
        "per_page": 1,
    })
    orgs = data.get("organizations") or []

    # Free plan error handling
    if data.get("error") and "free plan" in str(data.get("error", "")).lower():
        logger.info("Apollo org search requires paid plan")
        return {}

    if not orgs:
        return {}
    top = orgs[0]

    # Return search result fields directly (don't re-enrich — it can match wrong domain)
    return {
        "name":              top.get("name", ""),
        "website":           top.get("website_url", ""),
        "industry":          top.get("industry", ""),
        "founded_year":      top.get("founded_year"),
        "headcount":         top.get("num_employees") or top.get("estimated_num_employees") or 0,
        "headcount_range":   top.get("estimated_num_employees") or "",
        "revenue_range":     top.get("revenue_range", "") or "",
        "annual_revenue":    top.get("annual_revenue"),
        "technologies":      [t.get("name","") for t in (top.get("technologies") or [])[:15]],
        "short_description": top.get("short_description", ""),
        "linkedin_url":      top.get("linkedin_url", ""),
        "keywords":          top.get("keywords") or [],
        "country":           top.get("country", ""),
        "city":              top.get("city", ""),
        "state":             top.get("state", ""),
        "alexa_rank":        top.get("alexa_ranking"),
        "seo_description":   top.get("seo_description", ""),
        "facebook_url":      top.get("facebook_url", ""),
        "twitter_url":       top.get("twitter_url", ""),
        "source":            "Apollo.io",
    }


# ── People search / enrichment ───────────────────────────────────────────────

def search_people(
    name: str = "",
    organization: str = "",
    title_keywords: Optional[list] = None,
    limit: int = 10,
) -> list:
    """
    Search for people at an organization.
    Returns a list of { name, title, email, linkedin, seniority, department }.
    NOTE: /people/search requires Apollo paid plan. Returns [] on free tier with a note.
    """
    payload = {
        "page": 1,
        "per_page": min(limit, 25),
    }
    if name:
        payload["q_keywords"] = name
    if organization:
        payload["q_organization_name"] = organization
    if title_keywords:
        payload["person_titles"] = title_keywords

    data = _post("/people/search", payload)

    # Free plan returns an error — surface it gracefully
    if data.get("error") and "free plan" in str(data.get("error", "")).lower():
        logger.info("Apollo people search requires paid plan — returning empty list")
        return []

    people = data.get("people") or []

    results = []
    for p in people:
        email = None
        for acct in (p.get("account") or {}).get("contacts") or []:
            if acct.get("email"):
                email = acct["email"]
                break
        if not email:
            email = p.get("email") or ""

        results.append({
            "name":       p.get("name", ""),
            "first_name": p.get("first_name", ""),
            "last_name":  p.get("last_name", ""),
            "title":      p.get("title", ""),
            "seniority":  p.get("seniority", ""),
            "department": p.get("departments", [None])[0] if p.get("departments") else "",
            "email":      email,
            "linkedin":   p.get("linkedin_url", ""),
            "city":       p.get("city", ""),
            "country":    p.get("country", ""),
            "headline":   p.get("headline", ""),
            "photo_url":  p.get("photo_url", ""),
        })

    return results


def enrich_person(
    name: str = "",
    email: str = "",
    organization: str = "",
    domain: str = "",
) -> dict:
    """
    Match / enrich a single person.
    """
    payload = {}
    if name:
        payload["name"] = name
    if email:
        payload["email"] = email
    if organization:
        payload["organization_name"] = organization
    if domain:
        payload["domain"] = domain
    if not payload:
        return {}

    data = _post("/people/match", payload)
    p = data.get("person") or {}
    if not p:
        return {}

    return {
        "name":       p.get("name", ""),
        "title":      p.get("title", ""),
        "seniority":  p.get("seniority", ""),
        "email":      p.get("email", ""),
        "linkedin":   p.get("linkedin_url", ""),
        "city":       p.get("city", ""),
        "country":    p.get("country", ""),
        "headline":   p.get("headline", ""),
        "education":  [{"degree": e.get("degree", ""), "school": e.get("school", {}).get("name", "")}
                       for e in (p.get("education_history") or [])[:3]],
        "employment": [{"title": e.get("title", ""), "org": e.get("organization_name", ""),
                        "start": e.get("start_date", "")}
                       for e in (p.get("employment_history") or [])[:5]],
    }


# ── Key-executive org chart ──────────────────────────────────────────────────

_EXEC_TITLES = [
    "CEO", "CFO", "COO", "CTO", "CMO", "CLO", "CPO", "President",
    "Founder", "Co-Founder", "Managing Director", "General Counsel",
    "Chief of Staff", "VP", "Partner",
]

def fetch_org_chart(organization: str) -> list:
    """
    Fetch C-suite + VP-level people at an org using Apollo people search.
    Returns list of { name, title, email, linkedin }.
    """
    return search_people(
        organization=organization,
        title_keywords=_EXEC_TITLES,
        limit=20,
    )
