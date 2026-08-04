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
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from app.services.person_disambiguation import (
    author_matches_person,
    birth_year_from_age,
    clean_company_name,
    company_core_name,
    extract_bio_companies,
    is_valid_company_name,
    plausible_authorship,
    publication_year,
)

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


def _corroboration_terms(company_name: str, title: str,
                         biography: str) -> List[str]:
    """Names that would place a publication in this person's working life.

    Drawn from the person's employer and the organisations their own biography
    names, so the test is specific to the person being researched. Every
    capitalised word in the biography is deliberately *not* used: a term list
    that wide matches on ordinary words and admits an unrelated namesake's
    novel.
    """
    terms = set()
    for source in (company_name, title):
        for word in re.findall(r"[A-Za-z]{5,}", source or ""):
            lowered = word.lower()
            if lowered not in {"corporation", "incorporated", "company",
                               "holdings", "group", "former", "chief",
                               "officer", "director", "executive", "president"}:
                terms.add(lowered)

    for entry in extract_bio_companies(biography):
        core = company_core_name(entry["company"])
        if len(core) >= 5:
            terms.add(core)
            # The leading word of a multi-word employer identifies it too.
            head = core.split()[0]
            if len(head) >= 5:
                terms.add(head)

    return sorted(terms)


def _volume_is_corroborated(volume: Dict[str, Any], terms: List[str]) -> bool:
    """Whether a volume's subject matter connects to the person's working life.

    Author name and publication date together are still not enough to attribute
    a book: a living namesake defeats both. Searching for the NFL's former chief
    marketing officer returned science-teaching workbooks credited to exactly
    "Dawn Hudson", which passed a name check and a lifespan check and was wrong.
    Positive corroboration is therefore required, and a volume that cannot be
    connected to the person is left out rather than published with a caveat.
    """
    if not terms:
        return False
    haystack = " ".join(str(part).lower() for part in (
        volume.get("title") or "",
        volume.get("description") or "",
        volume.get("publisher") or "",
        " ".join(volume.get("categories") or []),
    ))
    return any(term in haystack for term in terms)


def search_executive_books(
    person_name: str,
    limit: int = 10,
    birth_year: Optional[int] = None,
    corroboration_terms: Optional[List[str]] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Search for books authored by an executive.
    Uses Google Books API and Open Library.

    Both catalogues match on strings rather than on people, and both rank by
    how published a name is rather than by who is being asked about. Searching
    them for a sitting director named Tench Coxe returns the eighteenth-century
    political economist of the same name, and an unfiltered search credited *The
    Federalist* to an NVIDIA board member in a delivered report. Every candidate
    is therefore checked against the credited author list and against the
    person's own lifespan, and the count of rejects is returned so the report can
    disclose that a search ran and found nothing attributable.
    """
    books: List[Dict[str, Any]] = []
    audit = {"considered": 0, "rejected_author": 0, "rejected_lifespan": 0,
             "rejected_unattributable": 0}

    # Clean name for search
    clean_name = re.sub(r'\s+', ' ', person_name.strip())

    def accept(candidate: Dict[str, Any]) -> None:
        """Admit a volume only if it can be tied to this person."""
        audit["considered"] += 1
        if not author_matches_person(candidate.get("authors") or [], person_name):
            audit["rejected_author"] += 1
            return
        year = publication_year(candidate.get("published_date"))
        if not plausible_authorship(year, birth_year):
            audit["rejected_lifespan"] += 1
            return
        if not _volume_is_corroborated(candidate, corroboration_terms or []):
            audit["rejected_unattributable"] += 1
            return
        if any(b.get("title") == candidate.get("title") for b in books):
            return
        books.append(candidate)

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
                accept({
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
                accept({
                    "title": doc.get("title", ""),
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

    return books[:limit], audit


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
    biography: str = "",
    known_people: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Find prior companies founded or led by an executive.

    Two sources, ranked. The proxy biography is the person's own filed account
    and is treated as authoritative. Search snippets are prose about anyone the
    query happened to surface, and reading employers out of them with a regex
    published "Biden" as a prior company of a Caltech professor and "Jensen" as
    one of a venture capitalist. A snippet-derived company is therefore only
    admitted when the biography corroborates it, which leaves the web layer doing
    what it can support — confirming and dating what a filing already says.
    """
    prior_companies: List[Dict[str, Any]] = []
    seen: Dict[str, Dict[str, Any]] = {}

    def add(name: str, role: str, source: str, verified: bool,
            year: Optional[int] = None) -> None:
        cleaned = clean_company_name(name)
        if not cleaned:
            return
        if not is_valid_company_name(cleaned, known_people, current_company):
            return
        # Deduplicate on the distinctive core so that "Tensilica" and
        # "Tensilica Inc" are one employer rather than two.
        key = company_core_name(cleaned) or cleaned.lower()
        existing = seen.get(key)
        if existing is not None:
            # Keep the fuller rendering of the same name.
            if len(cleaned) > len(existing["company_name"]):
                existing["company_name"] = cleaned
            if year and not existing.get("year"):
                existing["year"] = year
            return
        entry = {
            "company_name": cleaned,
            "role": role,
            "year": year,
            "source": source,
            "verified": verified,
        }
        seen[key] = entry
        prior_companies.append(entry)

    # Source 1 — the biography the issuer filed.
    for entry in extract_bio_companies(biography, current_company, known_people):
        add(entry["company"], entry.get("role") or "Executive/Founder",
            "proxy_biography", True, entry.get("year"))

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

    bio_lower = (biography or "").lower()
    for result in results:
        for item in result.get("organicResults", []):
            text = f"{item.get('title', '')} {item.get('description', '')}"
            # A snippet that never names this person says nothing about them.
            if person_name and not _snippet_names_person(text, person_name):
                continue
            for pattern in company_patterns:
                for match in re.findall(pattern, text):
                    cleaned = clean_company_name(match)
                    if not cleaned:
                        continue
                    # Corroboration requirement: the filed biography has to
                    # mention the company for a snippet to be publishable.
                    if not bio_lower or cleaned.lower() not in bio_lower:
                        continue
                    add(cleaned, "Executive/Founder", "web_search_corroborated",
                        True)

    return prior_companies[:10]


def _snippet_names_person(text: str, person_name: str) -> bool:
    """Whether a search snippet actually refers to the person searched for."""
    from app.services.person_disambiguation import person_name_parts
    first, _, last = person_name_parts(person_name)
    lowered = (text or "").lower()
    if last and last not in lowered:
        return False
    return bool(first and first in lowered) or bool(last)




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
        # Candidates a catalogue returned that could not be tied to the person
        # named. Reported so a thin section reads as a search that found nothing
        # attributable rather than as a search that was never run.
        "attribution_audit": {
            "considered": 0,
            "rejected_author": 0,
            "rejected_lifespan": 0,
            "rejected_unattributable": 0,
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

    # Every person in the cohort, so that a company name that is really one of
    # their names can be recognised as such.
    cohort_names = [e.get("name", "") for e in executives if e.get("name")]

    def research_executive(exec_info: Dict[str, Any]) -> Dict[str, Any]:
        name = exec_info.get("name", "")
        if not name:
            return None

        biography = (exec_info.get("biography") or exec_info.get("background")
                     or exec_info.get("bio") or "")
        birth_year = (exec_info.get("birth_year")
                      or birth_year_from_age(exec_info.get("age")))

        profile = {
            "name": name,
            "title": exec_info.get("title") or exec_info.get("role"),
            "birth_year": birth_year,
            "books": [],
            "interviews": [],
            "prior_companies": [],
            "publications": [],
            "attribution_audit": {},
        }

        # Always search books (free APIs)
        profile["books"], profile["attribution_audit"] = search_executive_books(
            name, limit=5, birth_year=birth_year,
            corroboration_terms=_corroboration_terms(
                company_name, profile["title"] or "", biography))

        # The biography is available with or without a scraping budget, so the
        # prior-company list is no longer empty when Apify is unavailable.
        profile["prior_companies"] = get_prior_companies(
            name, company_name, biography=biography, known_people=cohort_names)

        if deep_search and APIFY_TOKEN:
            # Web scraping for interviews and prior companies
            profile["interviews"] = search_executive_interviews(name, company_name, limit=10)
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
                    for key, count in (profile.get("attribution_audit") or {}).items():
                        if key in result["attribution_audit"]:
                            result["attribution_audit"][key] += count
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
    audit = track_record.get("attribution_audit", {}) or {}

    if not profiles:
        # Return empty - don't show "not available" message
        return []

    lines.append(
        f"Research covered {len(profiles)} executives, identifying "
        f"{stats.get('total_books', 0)} books, {stats.get('total_interviews', 0)} interviews, "
        f"and {stats.get('total_prior_companies', 0)} prior company affiliations."
    )
    lines.append("")

    # A name search returns the most published holder of a name, not the person
    # asked about. Stating how many candidates were discarded is what separates a
    # cohort that has written nothing from a search that was never run.
    discarded = (audit.get("rejected_author", 0)
                 + audit.get("rejected_lifespan", 0)
                 + audit.get("rejected_unattributable", 0))
    if discarded:
        detail = []
        if audit.get("rejected_author"):
            detail.append(f"{audit['rejected_author']} credited to a different "
                          f"author of the same name")
        if audit.get("rejected_lifespan"):
            detail.append(f"{audit['rejected_lifespan']} published outside the "
                          f"person's lifetime")
        if audit.get("rejected_unattributable"):
            detail.append(f"{audit['rejected_unattributable']} on a subject with "
                          f"no connection to the person's working life")
        lines.append(
            f"Of {audit.get('considered', 0)} catalogue matches on these names, "
            f"{discarded} were rejected — {'; '.join(detail)}. A book is "
            f"attributed only where the credited author names the person, the "
            f"publication date falls within their lifetime, and the subject "
            f"connects to their career; a name search alone returns the most "
            f"published holder of a name rather than the person asked about."
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
                name_str = company.get("company_name", "Unknown")
                role = company.get("role") or "Executive"
                year = company.get("year")
                suffix = f", from {year}" if year else ""
                # Where a company came from matters: a filed biography is the
                # person's own account, a corroborated snippet is not.
                origin = ("filed biography"
                          if company.get("source") == "proxy_biography"
                          else "web, corroborated against the biography")
                lines.append(f"- {name_str} — {role}{suffix} *({origin})*")
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
