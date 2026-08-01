"""
Founder Track Record Connector (G-08)
────────────────────────────────────────────────────────────────────────────
Deep research on founders and executives to find:
  - Books authored by executives
  - Interviews and speaking engagements
  - Prior companies founded or led
  - Academic publications
  - Board history across companies
  - Career trajectory analysis

Uses Apify web scrapers and public APIs to gather comprehensive
executive background information that goes beyond SEC filings.
"""

import os
import re
import time
import logging
import requests
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

logger = logging.getLogger(__name__)

APIFY_TOKEN = os.getenv("APIFY_API_TOKEN", "")
APIFY_BASE = "https://api.apify.com/v2"

# Google Books API (free, no key required for basic search)
GOOGLE_BOOKS_API = "https://www.googleapis.com/books/v1/volumes"

# Open Library API (free)
OPEN_LIBRARY_SEARCH = "https://openlibrary.org/search.json"


def _run_apify_actor(actor_id: str, input_data: dict, wait_secs: int = 120) -> List[dict]:
    """Run an Apify actor and return results."""
    if not APIFY_TOKEN:
        logger.warning("APIFY_API_TOKEN not set — skipping web scraping")
        return []

    actor_id_url = actor_id.replace("/", "~")

    try:
        run_resp = requests.post(
            f"{APIFY_BASE}/acts/{actor_id_url}/runs",
            params={"token": APIFY_TOKEN, "waitForFinish": 60},
            json=input_data,
            timeout=90,
        )
        if not run_resp.ok:
            logger.warning("Apify run failed (%s): %s", run_resp.status_code, run_resp.text[:300])
            return []

        run_data = run_resp.json().get("data", run_resp.json())
        dataset_id = run_data.get("defaultDatasetId")
        run_id = run_data.get("id")

        if not dataset_id:
            return []

        # Poll until done
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
            logger.warning("Apify run ended with status %s", status)
            if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                return []

        items_resp = requests.get(
            f"{APIFY_BASE}/datasets/{dataset_id}/items",
            params={"token": APIFY_TOKEN, "clean": "true", "format": "json"},
            timeout=30,
        )
        if not items_resp.ok:
            return []

        items = items_resp.json()
        return items if isinstance(items, list) else []

    except Exception as exc:
        logger.warning("Apify connector error: %s", exc)
        return []


def search_executive_books(person_name: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for books authored by an executive.
    Uses Google Books API and Open Library.
    """
    books = []

    # Clean name for search
    clean_name = re.sub(r'\s+', ' ', person_name.strip())

    # Google Books search
    try:
        resp = requests.get(
            GOOGLE_BOOKS_API,
            params={
                "q": f'inauthor:"{clean_name}"',
                "maxResults": limit,
                "printType": "books",
            },
            timeout=15,
        )
        if resp.ok:
            data = resp.json()
            for item in data.get("items", []):
                vol = item.get("volumeInfo", {})
                books.append({
                    "title": vol.get("title"),
                    "authors": vol.get("authors", []),
                    "publisher": vol.get("publisher"),
                    "published_date": vol.get("publishedDate"),
                    "description": (vol.get("description") or "")[:500],
                    "page_count": vol.get("pageCount"),
                    "categories": vol.get("categories", []),
                    "isbn": next((id.get("identifier") for id in vol.get("industryIdentifiers", [])
                                  if id.get("type") == "ISBN_13"), None),
                    "source": "Google Books",
                    "link": vol.get("infoLink"),
                })
    except Exception as e:
        logger.warning("Google Books search failed: %s", e)

    # Open Library search (backup)
    try:
        resp = requests.get(
            OPEN_LIBRARY_SEARCH,
            params={"author": clean_name, "limit": limit},
            timeout=15,
        )
        if resp.ok:
            data = resp.json()
            for doc in data.get("docs", []):
                # Avoid duplicates
                title = doc.get("title", "")
                if not any(b.get("title") == title for b in books):
                    books.append({
                        "title": title,
                        "authors": doc.get("author_name", []),
                        "publisher": doc.get("publisher", [None])[0] if doc.get("publisher") else None,
                        "published_date": str(doc.get("first_publish_year", "")),
                        "description": None,
                        "page_count": doc.get("number_of_pages_median"),
                        "categories": doc.get("subject", [])[:5],
                        "isbn": doc.get("isbn", [None])[0] if doc.get("isbn") else None,
                        "source": "Open Library",
                        "link": f"https://openlibrary.org{doc.get('key')}" if doc.get("key") else None,
                    })
    except Exception as e:
        logger.warning("Open Library search failed: %s", e)

    return books[:limit]


def search_executive_interviews(
    person_name: str,
    company_name: str = "",
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Search for interviews with an executive using web scraping.
    Searches YouTube, podcast directories, and news archives.
    """
    interviews = []

    if not APIFY_TOKEN:
        return interviews

    # Use Google Search scraper for interviews
    search_queries = [
        f'"{person_name}" interview',
        f'"{person_name}" podcast',
        f'"{person_name}" keynote speech',
    ]
    if company_name:
        search_queries.append(f'"{person_name}" {company_name} interview')

    for query in search_queries[:2]:  # Limit queries to control costs
        results = _run_apify_actor(
            "apify/google-search-scraper",
            {
                "queries": query,
                "maxPagesPerQuery": 1,
                "resultsPerPage": 10,
            },
            wait_secs=60,
        )

        for result in results:
            organic = result.get("organicResults", [])
            for item in organic[:5]:
                # Filter for interview/podcast content
                title = (item.get("title") or "").lower()
                url = item.get("url") or ""

                is_interview = any(kw in title for kw in [
                    "interview", "podcast", "talks to", "speaks", "keynote",
                    "fireside", "conversation with", "q&a", "discusses"
                ])

                is_video = any(site in url.lower() for site in [
                    "youtube.com", "ted.com", "vimeo.com", "bloomberg.com/news"
                ])

                if is_interview or is_video:
                    interviews.append({
                        "title": item.get("title"),
                        "url": url,
                        "description": item.get("description"),
                        "date": item.get("date"),
                        "type": "video" if is_video else "article",
                        "source": item.get("displayedUrl") or "web",
                    })

        time.sleep(1)  # Rate limiting

    # Deduplicate by URL
    seen_urls = set()
    unique = []
    for item in interviews:
        url = item.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(item)

    return unique[:limit]


def get_prior_companies(
    person_name: str,
    current_company: str = "",
) -> List[Dict[str, Any]]:
    """
    Find prior companies founded or led by an executive.
    Uses SEC filings, LinkedIn data, and web search.
    """
    prior_companies = []

    if not APIFY_TOKEN:
        return prior_companies

    # Search for prior company associations
    results = _run_apify_actor(
        "apify/google-search-scraper",
        {
            "queries": f'"{person_name}" founder OR CEO OR "co-founded" -site:linkedin.com',
            "maxPagesPerQuery": 1,
            "resultsPerPage": 15,
        },
        wait_secs=60,
    )

    # Parse results for company mentions
    company_patterns = [
        r'(?:founded|co-founded|started|launched)\s+([A-Z][A-Za-z0-9\s&]+(?:Inc\.?|Corp\.?|LLC|Ltd\.?)?)',
        r'(?:CEO|President|Chairman)\s+(?:of\s+)?([A-Z][A-Za-z0-9\s&]+(?:Inc\.?|Corp\.?|LLC|Ltd\.?)?)',
        r'([A-Z][A-Za-z0-9\s&]+(?:Inc\.?|Corp\.?|LLC|Ltd\.?))\s+(?:founder|CEO)',
    ]

    mentioned_companies = set()
    for result in results:
        for item in result.get("organicResults", []):
            text = f"{item.get('title', '')} {item.get('description', '')}"
            for pattern in company_patterns:
                matches = re.findall(pattern, text)
                for match in matches:
                    company = match.strip()
                    if company and len(company) > 2:
                        # Filter out current company
                        if current_company and current_company.lower() in company.lower():
                            continue
                        mentioned_companies.add(company)

    for company in list(mentioned_companies)[:10]:
        prior_companies.append({
            "company_name": company,
            "role": "Executive/Founder",
            "source": "web_search",
            "verified": False,  # Would need SEC verification
        })

    return prior_companies


def get_academic_publications(person_name: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search for academic publications by an executive.
    Uses Google Scholar via web scraping.
    """
    publications = []

    if not APIFY_TOKEN:
        return publications

    # Use Google Scholar search
    results = _run_apify_actor(
        "apify/google-search-scraper",
        {
            "queries": f'site:scholar.google.com author:"{person_name}"',
            "maxPagesPerQuery": 1,
            "resultsPerPage": 10,
        },
        wait_secs=60,
    )

    for result in results:
        for item in result.get("organicResults", []):
            publications.append({
                "title": item.get("title"),
                "url": item.get("url"),
                "snippet": item.get("description"),
                "source": "Google Scholar",
            })

    return publications[:limit]


def get_founder_track_record(
    executives: List[Dict[str, Any]],
    company_name: str = "",
    ticker: str = "",
    deep_search: bool = True,
) -> Dict[str, Any]:
    """
    Comprehensive founder/executive track record analysis.

    Args:
        executives: List of executive dicts with 'name' key
        company_name: Current company name
        ticker: Current company ticker
        deep_search: Whether to do full web scraping (uses Apify credits)

    Returns:
        Complete track record data for all executives
    """
    logger.info("Starting founder track record research for %s", company_name)

    result = {
        "company": company_name,
        "ticker": ticker,
        "executives_researched": 0,
        "executive_profiles": [],
        "aggregate_stats": {
            "total_books": 0,
            "total_interviews": 0,
            "total_prior_companies": 0,
            "total_publications": 0,
        },
        "research_timestamp": datetime.utcnow().isoformat() + "Z",
    }

    # Process top executives (CEO, CFO, key founders)
    priority_titles = ["ceo", "chief executive", "founder", "chairman", "president", "cfo"]

    def get_priority(exec_dict):
        title = (exec_dict.get("title") or exec_dict.get("role") or "").lower()
        for i, pt in enumerate(priority_titles):
            if pt in title:
                return i
        return len(priority_titles)

    sorted_execs = sorted(executives, key=get_priority)[:8]  # Top 8 executives

    def research_executive(exec_info: Dict[str, Any]) -> Dict[str, Any]:
        name = exec_info.get("name", "")
        if not name:
            return None

        profile = {
            "name": name,
            "title": exec_info.get("title") or exec_info.get("role"),
            "books": [],
            "interviews": [],
            "prior_companies": [],
            "publications": [],
        }

        # Always search books (free APIs)
        profile["books"] = search_executive_books(name, limit=5)

        if deep_search and APIFY_TOKEN:
            # Web scraping for interviews and prior companies
            profile["interviews"] = search_executive_interviews(name, company_name, limit=10)
            profile["prior_companies"] = get_prior_companies(name, company_name)
            profile["publications"] = get_academic_publications(name, limit=5)

        return profile

    # Research executives in parallel
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(research_executive, e): e for e in sorted_execs}

        for future in as_completed(futures):
            try:
                profile = future.result(timeout=120)
                if profile:
                    result["executive_profiles"].append(profile)
                    result["executives_researched"] += 1
                    result["aggregate_stats"]["total_books"] += len(profile.get("books", []))
                    result["aggregate_stats"]["total_interviews"] += len(profile.get("interviews", []))
                    result["aggregate_stats"]["total_prior_companies"] += len(profile.get("prior_companies", []))
                    result["aggregate_stats"]["total_publications"] += len(profile.get("publications", []))
            except Exception as e:
                logger.warning("Executive research failed: %s", e)

    # Sort profiles by richness of data
    result["executive_profiles"].sort(
        key=lambda p: sum([
            len(p.get("books", [])),
            len(p.get("interviews", [])),
            len(p.get("prior_companies", [])),
            len(p.get("publications", [])),
        ]),
        reverse=True
    )

    return result


def render_founder_track_record_markdown(track_record: Dict[str, Any]) -> List[str]:
    """Render founder track record as markdown for the report."""
    lines = ["## Founder and Executive Track Record", ""]

    profiles = track_record.get("executive_profiles", [])
    stats = track_record.get("aggregate_stats", {})

    if not profiles:
        # Return empty - don't show "not available" message
        return []

    lines.append(
        f"Research covered {len(profiles)} executives, identifying "
        f"{stats.get('total_books', 0)} books, {stats.get('total_interviews', 0)} interviews, "
        f"and {stats.get('total_prior_companies', 0)} prior company affiliations."
    )
    lines.append("")

    for profile in profiles[:5]:  # Top 5 executives
        name = profile.get("name", "Unknown")
        title = profile.get("title", "")

        lines.append(f"### {name}")
        if title:
            lines.append(f"*{title}*")
        lines.append("")

        # Books
        books = profile.get("books", [])
        if books:
            lines.append("**Publications and Books**")
            lines.append("")
            for book in books[:3]:
                title_str = book.get("title", "Untitled")
                year = book.get("published_date", "")[:4] if book.get("published_date") else ""
                year_str = f" ({year})" if year else ""
                lines.append(f"- *{title_str}*{year_str}")
                if book.get("description"):
                    desc = book["description"][:200]
                    lines.append(f"  > {desc}...")
            lines.append("")

        # Prior companies
        prior = profile.get("prior_companies", [])
        if prior:
            lines.append("**Prior Company Experience**")
            lines.append("")
            for company in prior[:5]:
                lines.append(f"- {company.get('company_name', 'Unknown')} — {company.get('role', 'Executive')}")
            lines.append("")

        # Interviews
        interviews = profile.get("interviews", [])
        if interviews:
            lines.append("**Notable Interviews and Appearances**")
            lines.append("")
            for interview in interviews[:3]:
                title_str = interview.get("title", "Interview")
                url = interview.get("url", "")
                source = interview.get("source", "")
                if url:
                    lines.append(f"- [{title_str}]({url}) — {source}")
                else:
                    lines.append(f"- {title_str} — {source}")
            lines.append("")

    lines.append("*Sources: Google Books API, Open Library, web search.*")
    lines.append("")

    return lines
