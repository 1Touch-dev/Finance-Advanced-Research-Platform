"""
Apify connector — LinkedIn profiles, PitchBook company data, Google News.

Actors used:
  - automation-lab/linkedin-profile-scraper      (~$0.003/profile, education + experience)
  - mdataset/pitchbook-realtime-scraper          (~$0.004/lookup, company funding/investors)
  - brilliant_gum/google-news-scraper            (~$0.03/article, person/company news timeline)

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
    Uses short-poll strategy: start run, waitForFinish=60, then poll up to wait_secs total.
    """
    if not APIFY_TOKEN:
        logger.warning("APIFY_API_TOKEN not set — skipping Apify enrichment")
        return []

    # Convert slash notation to tilde for the URL
    actor_id_url = actor_id.replace("/", "~")

    try:
        run_resp = requests.post(
            f"{APIFY_BASE}/acts/{actor_id_url}/runs",
            params={"token": APIFY_TOKEN, "waitForFinish": 60},
            json=input_data,
            timeout=90,
        )
        if not run_resp.ok:
            if "platform-feature-disabled" in run_resp.text or "hard limit" in run_resp.text.lower():
                logger.warning("Apify monthly credits exhausted — top up at console.apify.com to re-enable enrichment")
            else:
                logger.warning("Apify run failed (%s): %s", run_resp.status_code, run_resp.text[:300])
            return []

        run_data = run_resp.json().get("data", run_resp.json())
        run_id = run_data.get("id")
        dataset_id = run_data.get("defaultDatasetId")
        if not dataset_id:
            logger.warning("Apify: no datasetId in response: %s", str(run_data)[:200])
            return []

        # If run is still going after initial 60s wait, poll until done or time-out
        status = run_data.get("status", "")
        elapsed = 60
        poll_interval = 10
        while status not in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT") and elapsed < wait_secs and run_id:
            time.sleep(poll_interval)
            elapsed += poll_interval
            poll_resp = requests.get(
                f"{APIFY_BASE}/actor-runs/{run_id}",
                params={"token": APIFY_TOKEN},
                timeout=15,
            )
            if poll_resp.ok:
                status = poll_resp.json().get("data", {}).get("status", status)

        if status not in ("SUCCEEDED", "READY"):
            logger.warning("Apify run ended with status %s for actor %s", status, actor_id)
            if status in ("FAILED", "ABORTED", "TIMED-OUT"):
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

# Known PitchBook company IDs for common demo entities (avoids a search round-trip)
_PITCHBOOK_ID_CACHE: Dict[str, str] = {
    "palantir technologies": "43117-84",
    "palantir": "43117-84",
    "anduril industries": "304997-97",
    "anduril": "304997-97",
    "spacex": "13513-68",
    "openai": "239338-91",
    "anthropic": "539632-90",
    "founders fund": "11460-99",
    "peter thiel": "43117-84",  # Thiel → Palantir as closest company profile
}


def _search_pitchbook_id(company_name: str) -> Optional[str]:
    """
    Try to find the PitchBook company ID by scraping the PitchBook search page
    via Google News actor as a lightweight proxy search, or return from cache.
    """
    key = company_name.lower().strip()
    if key in _PITCHBOOK_ID_CACHE:
        return _PITCHBOOK_ID_CACHE[key]
    return None


def fetch_pitchbook_company(company_name: str) -> Dict[str, Any]:
    """
    Fetch PitchBook public company profile data using the realtime scraper.
    Requires a known PitchBook profile URL or company ID.
    Falls back gracefully if company ID is unknown.
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

    # Resolve PitchBook company ID
    pb_id = _search_pitchbook_id(company_name)
    if not pb_id:
        logger.info("PitchBook: no cached ID for '%s' — skipping (add to cache or provide URL)", company_name)
        result["note"] = f"PitchBook ID not cached for '{company_name}' — add to _PITCHBOOK_ID_CACHE"
        return result

    pb_url = f"https://pitchbook.com/profiles/company/{pb_id}"
    items = _run_actor(
        "mdataset/pitchbook-realtime-scraper",
        {"startUrls": [{"url": pb_url}], "allowCachedProfiles": True},
        wait_secs=130,
    )

    if not items:
        return result

    p = items[0]
    result["company_name"]  = p.get("company_name") or company_name
    result["description"]   = p.get("description") or p.get("about")
    result["stage"]         = p.get("status") or p.get("stage") or p.get("financing_status")
    result["total_raised"]  = p.get("total_raised") or p.get("latest_deal_amount") or p.get("totalFundingAmount")
    result["employees"]     = p.get("employees") or p.get("employee_count") or p.get("employeeCount")
    result["founded"]       = p.get("year_founded") or p.get("founded") or p.get("foundingYear")
    result["latest_deal"]   = p.get("latest_deal_type")
    result["pitchbook_url"] = p.get("url") or pb_url

    # investors/financing_rounds may be counts (int) or arrays depending on plan
    raw_investors = p.get("all_investments") or p.get("investors")
    if isinstance(raw_investors, list):
        for inv in raw_investors:
            name = inv.get("name") or inv.get("investor_name") or (inv if isinstance(inv, str) else None)
            if name:
                result["investors"].append(name)
    elif isinstance(raw_investors, int):
        result["investor_count"] = raw_investors

    raw_rounds = p.get("financing_rounds") or p.get("funding_rounds") or p.get("fundingRounds")
    if isinstance(raw_rounds, list):
        for rnd in raw_rounds:
            result["funding_rounds"].append({
                "type":   rnd.get("round_type") or rnd.get("type"),
                "amount": rnd.get("amount") or rnd.get("raised"),
                "date":   rnd.get("date") or rnd.get("announcedDate"),
            })
    elif isinstance(raw_rounds, int):
        result["financing_rounds_count"] = raw_rounds

    # Competitors
    for c in (p.get("competitors") or [])[:5]:
        name = c.get("company_name") or c.get("name") or (c if isinstance(c, str) else None)
        if name:
            result["competitors"].append(name)

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
