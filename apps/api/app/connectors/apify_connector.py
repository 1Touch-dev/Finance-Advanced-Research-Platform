"""
Apify connector — LinkedIn profiles, PitchBook company data, Google News.

Actors used:
  - automation-lab/linkedin-profile-scraper  (~$0.003/profile, education + experience)
  - mdataset/pitchbook-scraper               (~$0.0035/lookup, company funding/investors)
  - brilliant_gum/google-news-scraper        (~$0.03/article, person/company news timeline)

All actors run synchronously (waitForFinish=120s) on Apify's cloud.
Results are returned as structured dicts and merged into the intelligence service.
"""
import os
import time
import logging
import requests
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

APIFY_TOKEN = os.getenv("APIFY_API_TOKEN", "")
APIFY_BASE  = "https://api.apify.com/v2"


def _run_actor(actor_id: str, input_data: dict, wait_secs: int = 120) -> List[dict]:
    """
    Start an Apify actor run synchronously, return dataset items.
    actor_id format: 'owner~name'  (tilde-separated, NOT slash)
    """
    if not APIFY_TOKEN:
        logger.warning("APIFY_API_TOKEN not set — skipping Apify enrichment")
        return []

    # Convert slash notation to tilde for the URL
    actor_id_url = actor_id.replace("/", "~")

    try:
        run_resp = requests.post(
            f"{APIFY_BASE}/acts/{actor_id_url}/runs",
            params={"token": APIFY_TOKEN, "waitForFinish": wait_secs},
            json=input_data,
            timeout=wait_secs + 30,
        )
        if not run_resp.ok:
            if "platform-feature-disabled" in run_resp.text or "hard limit" in run_resp.text.lower():
                logger.warning("Apify monthly credits exhausted — top up at console.apify.com to re-enable enrichment")
            else:
                logger.warning("Apify run failed (%s): %s", run_resp.status_code, run_resp.text[:300])
            return []

        run_data = run_resp.json().get("data", run_resp.json())
        dataset_id = run_data.get("defaultDatasetId")
        if not dataset_id:
            logger.warning("Apify: no datasetId in response: %s", str(run_data)[:200])
            return []

        items_resp = requests.get(
            f"{APIFY_BASE}/datasets/{dataset_id}/items",
            params={"token": APIFY_TOKEN, "clean": "true", "format": "json"},
            timeout=30,
        )
        if not items_resp.ok:
            logger.warning("Apify dataset fetch failed (%s)", items_resp.status_code)
            return []

        items = items_resp.json()
        return items if isinstance(items, list) else []

    except Exception as exc:
        logger.warning("Apify connector error (%s): %s", actor_id, exc)
        return []


# ── LinkedIn profile scraper ──────────────────────────────────────────────────

def fetch_linkedin_profile(linkedin_url: str) -> Dict[str, Any]:
    """
    Fetch a single LinkedIn public profile.
    Returns structured dict with name, headline, about, education[], experience[].
    """
    result = {
        "name": None, "headline": None, "about": None,
        "location": None, "education": [], "experience": [],
        "follower_count": None, "profile_url": linkedin_url,
        "source": "Apify/LinkedIn",
    }
    items = _run_actor("automation-lab/linkedin-profile-scraper",
                       {"profileUrls": [linkedin_url]})
    if not items:
        return result

    p = items[0]
    result["name"]           = p.get("name") or p.get("fullName")
    result["headline"]       = p.get("headline")
    result["about"]          = p.get("about") or p.get("summary")
    result["location"]       = p.get("location") or p.get("geoRegion")
    result["follower_count"] = p.get("followerCount") or p.get("followers")

    # Education — normalize varying field names
    for ed in (p.get("education") or p.get("educations") or []):
        result["education"].append({
            "school":  ed.get("schoolName") or ed.get("school") or ed.get("institutionName"),
            "degree":  ed.get("degree") or ed.get("degreeName"),
            "field":   ed.get("fieldOfStudy"),
            "start":   ed.get("startYear") or (ed.get("dateRange") or {}).get("start", {}).get("year"),
            "end":     ed.get("endYear")   or (ed.get("dateRange") or {}).get("end",   {}).get("year"),
        })

    # Experience
    for ex in (p.get("experience") or p.get("positions") or []):
        result["experience"].append({
            "company":   ex.get("companyName") or ex.get("company"),
            "title":     ex.get("title"),
            "location":  ex.get("location") or ex.get("geo"),
            "start":     ex.get("startDate") or ex.get("startYear"),
            "end":       ex.get("endDate")   or ex.get("endYear") or "Present",
        })

    return result


def fetch_linkedin_by_name(person_name: str, company_hint: str = "") -> Dict[str, Any]:
    """
    Best-effort LinkedIn lookup by name. Tries common URL patterns.
    Falls back gracefully if not found.
    """
    # Try most common slug patterns
    slug_variants = [
        person_name.lower().replace(" ", "-"),
        person_name.lower().replace(" ", ""),
        person_name.split()[0].lower() + person_name.split()[-1].lower() if len(person_name.split()) >= 2 else None,
    ]
    slug_variants = [s for s in slug_variants if s]

    for slug in slug_variants[:3]:
        url = f"https://www.linkedin.com/in/{slug}/"
        result = fetch_linkedin_profile(url)
        if result.get("headline") or result.get("education") or result.get("experience"):
            return result

    return {
        "name": person_name, "headline": None, "about": None,
        "education": [], "experience": [], "source": "Apify/LinkedIn",
        "note": "Profile not found via URL slug — LinkedIn URL needed for exact lookup",
    }


# ── PitchBook scraper ─────────────────────────────────────────────────────────

def fetch_pitchbook_company(company_name: str) -> Dict[str, Any]:
    """
    Fetch PitchBook public company profile data.
    Returns funding history, investors, description, stage.
    """
    result = {
        "company_name": company_name,
        "description": None,
        "stage": None,
        "total_raised": None,
        "employees": None,
        "founded": None,
        "investors": [],
        "funding_rounds": [],
        "competitors": [],
        "source": "Apify/PitchBook",
    }
    items = _run_actor("mdataset/pitchbook-scraper",
                       {"startUrls": [{"url": f"https://pitchbook.com/profiles/company/search?q={company_name.replace(' ', '+')}&limit=1"}]})

    # mdataset actor can also be called with a search query
    if not items:
        # Try with direct search query format
        items = _run_actor("mdataset/pitchbook-scraper",
                           {"queries": [company_name]})

    if not items:
        return result

    p = items[0]
    result["company_name"]  = p.get("company_name") or company_name
    result["description"]   = p.get("description") or p.get("about")
    result["stage"]         = p.get("stage") or p.get("financing_status")
    result["total_raised"]  = p.get("total_raised") or p.get("totalFundingAmount")
    result["employees"]     = p.get("employees") or p.get("employeeCount")
    result["founded"]       = p.get("founded") or p.get("foundingYear")

    # Investors
    for inv in (p.get("investors") or p.get("investor_list") or []):
        name = inv.get("name") or inv.get("investor_name") or (inv if isinstance(inv, str) else None)
        if name:
            result["investors"].append(name)

    # Funding rounds
    for rnd in (p.get("financing_rounds") or p.get("fundingRounds") or []):
        result["funding_rounds"].append({
            "type":   rnd.get("round_type") or rnd.get("type"),
            "amount": rnd.get("amount") or rnd.get("raised"),
            "date":   rnd.get("date") or rnd.get("announcedDate"),
        })

    # Competitors
    for c in (p.get("competitors") or [])[:5]:
        name = c.get("company_name") or c.get("name") or (c if isinstance(c, str) else None)
        if name:
            result["competitors"].append(name)

    return result


# ── Google News scraper ───────────────────────────────────────────────────────

def fetch_news(query: str, max_articles: int = 8) -> List[Dict[str, Any]]:
    """
    Fetch recent news articles about a person or company.
    Returns list of {title, url, published, source, snippet}.
    """
    items = _run_actor("brilliant_gum/google-news-scraper",
                       {"query": query, "maxItems": max_articles, "language": "en"})
    articles = []
    for item in items:
        articles.append({
            "title":     item.get("title"),
            "url":       item.get("link") or item.get("url"),
            "published": item.get("date") or item.get("publishedAt"),
            "source":    item.get("source") or item.get("publisher"),
            "snippet":   (item.get("snippet") or item.get("description") or "")[:300],
        })
    return articles
