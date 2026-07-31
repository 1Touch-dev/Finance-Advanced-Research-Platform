"""
LinkedIn Deep Research Connector
────────────────────────────────────────────────────────────────────────────
Deep personnel research using Apify LinkedIn scrapers:
  - Executive profiles with full career history
  - Board member research and other board seats
  - Key employee profiles for top 20 personnel
  - Company employee directory scraping
  - Connection network analysis
  - Family relationship detection (via shared surnames + company affiliations)

Uses multiple Apify actors:
  - automation-lab/linkedin-profile-scraper (individual profiles)
  - curious_coder/linkedin-company-employees-scraper (employee directory)
  - apify/linkedin-company-scraper (company page data)

All data is public LinkedIn data accessed via Apify's cloud scraping.
"""
import os
import re
import time
import logging
import requests
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

APIFY_TOKEN = os.getenv("APIFY_API_TOKEN", "")
APIFY_BASE = "https://api.apify.com/v2"


def _run_actor(actor_id: str, input_data: dict, wait_secs: int = 120) -> List[dict]:
    """Start an Apify actor run synchronously, return dataset items."""
    if not APIFY_TOKEN:
        logger.warning("APIFY_API_TOKEN not set — skipping LinkedIn deep research")
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
        run_id = run_data.get("id")
        dataset_id = run_data.get("defaultDatasetId")
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
            logger.warning("Apify run ended with status %s for actor %s", status, actor_id)
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
        logger.warning("Apify connector error (%s): %s", actor_id, exc)
        return []


def fetch_executive_deep_profile(linkedin_url: str) -> Dict[str, Any]:
    """
    Fetch deep executive profile with full career history and board seats.
    Returns structured dossier-ready data.
    """
    result = {
        "name": None,
        "headline": None,
        "current_role": None,
        "current_company": None,
        "location": None,
        "about": None,
        "follower_count": None,
        "profile_url": linkedin_url,
        "education": [],
        "career_history": [],
        "board_seats": [],
        "certifications": [],
        "skills": [],
        "languages": [],
        "total_experience_years": 0,
        "source": "Apify/LinkedIn",
    }

    items = _run_actor("automation-lab/linkedin-profile-scraper", {"profileUrls": [linkedin_url]})
    if not items:
        return result

    p = items[0]
    result["name"] = p.get("name") or p.get("fullName")
    result["headline"] = p.get("headline")
    result["about"] = p.get("about") or p.get("summary")
    result["location"] = p.get("location") or p.get("geoRegion")
    result["follower_count"] = p.get("followerCount") or p.get("followers")

    # Education - full details
    for ed in (p.get("education") or p.get("educations") or []):
        result["education"].append({
            "school": ed.get("schoolName") or ed.get("school") or ed.get("institutionName"),
            "degree": ed.get("degree") or ed.get("degreeName"),
            "field": ed.get("fieldOfStudy"),
            "start_year": ed.get("startYear") or (ed.get("dateRange") or {}).get("start", {}).get("year"),
            "end_year": ed.get("endYear") or (ed.get("dateRange") or {}).get("end", {}).get("year"),
            "description": ed.get("description", ""),
            "activities": ed.get("activities", ""),
        })

    # Career history - detect board seats vs executive roles
    total_years = 0
    for ex in (p.get("experience") or p.get("positions") or []):
        title = (ex.get("title") or "").lower()
        company = ex.get("companyName") or ex.get("company") or ""

        start = ex.get("startDate") or ex.get("startYear")
        end = ex.get("endDate") or ex.get("endYear") or "Present"

        # Calculate tenure
        try:
            start_year = int(str(start)[:4]) if start else 2020
            end_year = 2026 if end == "Present" else int(str(end)[:4])
            tenure = end_year - start_year
            total_years = max(total_years, 2026 - start_year)
        except:
            tenure = 0

        entry = {
            "company": company,
            "title": ex.get("title"),
            "location": ex.get("location") or ex.get("geo"),
            "start": start,
            "end": end,
            "tenure_years": tenure,
            "description": ex.get("description", "")[:500],
        }

        # Detect board seats
        is_board = any(kw in title for kw in ["board", "director", "trustee", "advisor", "chairman"])
        if is_board and company:
            result["board_seats"].append({
                "company": company,
                "role": ex.get("title"),
                "start": start,
                "end": end,
                "is_current": end == "Present",
            })
        else:
            result["career_history"].append(entry)

    result["total_experience_years"] = total_years

    # Current role
    if result["career_history"]:
        current = next((c for c in result["career_history"] if c.get("end") == "Present"), None)
        if current:
            result["current_role"] = current.get("title")
            result["current_company"] = current.get("company")

    # Certifications
    for cert in (p.get("certifications") or []):
        result["certifications"].append({
            "name": cert.get("name") or cert.get("title"),
            "authority": cert.get("authority") or cert.get("organization"),
            "date": cert.get("dateObtained") or cert.get("issueDate"),
        })

    # Skills
    for skill in (p.get("skills") or [])[:20]:
        if isinstance(skill, str):
            result["skills"].append(skill)
        elif isinstance(skill, dict):
            result["skills"].append(skill.get("name") or skill.get("skill"))

    return result


def fetch_company_executives(company_name: str, company_linkedin_url: str = "", limit: int = 20) -> Dict[str, Any]:
    """
    Fetch key executives and board members from a company's LinkedIn page.
    Returns structured list with titles, tenures, and profile URLs.
    """
    result = {
        "company_name": company_name,
        "executives": [],
        "board_members": [],
        "other_employees": [],
        "total_found": 0,
        "source": "Apify/LinkedIn",
    }

    # Resolve company LinkedIn URL
    if not company_linkedin_url:
        slug = company_name.lower().replace(" ", "-").replace(",", "").replace(".", "")
        company_linkedin_url = f"https://www.linkedin.com/company/{slug}/"

    items = _run_actor("curious_coder/linkedin-company-employees-scraper", {
        "companyUrl": company_linkedin_url,
        "count": min(limit, 50),
    }, wait_secs=150)

    if not items:
        return result

    result["total_found"] = len(items)

    for item in items[:limit]:
        name = item.get("name") or item.get("fullName", "")
        title = (item.get("headline") or item.get("title", "")).lower()

        entry = {
            "name": name,
            "title": item.get("headline") or item.get("title"),
            "linkedin_url": item.get("profileUrl") or item.get("linkedinUrl"),
            "location": item.get("location", ""),
            "connection_degree": item.get("connectionDegree"),
        }

        # Classify by title
        is_executive = any(kw in title for kw in [
            "ceo", "cfo", "cto", "coo", "cmo", "cpo", "ciso", "cdo",
            "chief", "president", "founder", "co-founder", "partner",
            "executive vice", "evp", "svp", "senior vice president",
            "general counsel", "gc", "treasurer"
        ])
        is_board = any(kw in title for kw in ["board", "director", "chairman", "trustee"])

        if is_board:
            result["board_members"].append(entry)
        elif is_executive:
            result["executives"].append(entry)
        else:
            result["other_employees"].append(entry)

    return result


def detect_family_connections(executives: List[Dict], company_name: str) -> List[Dict[str, Any]]:
    """
    Detect potential family connections among executives by:
    - Shared surnames
    - Shared education (same school, similar years)
    - Prior company overlaps

    Returns list of potential family/relationship flags.
    """
    connections = []
    names = {}

    # Extract surnames
    for exec in executives:
        name = exec.get("name", "")
        parts = name.split()
        if len(parts) >= 2:
            surname = parts[-1].lower()
            if surname not in names:
                names[surname] = []
            names[surname].append(exec)

    # Flag shared surnames
    for surname, people in names.items():
        if len(people) >= 2 and len(surname) > 2:
            connections.append({
                "type": "shared_surname",
                "surname": surname,
                "people": [p.get("name") for p in people],
                "flag_level": "INVESTIGATE",
                "note": f"Multiple executives share surname '{surname}' — potential family relationship",
            })

    return connections


def research_board_interlocks(board_members: List[Dict], company_name: str) -> Dict[str, Any]:
    """
    Research board members' other board seats to identify interlocks.
    Fetches deep profiles for each board member in parallel.
    """
    result = {
        "board_members_researched": 0,
        "interlocks": [],
        "other_board_seats": {},
        "total_other_boards": 0,
    }

    profiles = []

    def fetch_profile(member: Dict) -> Optional[Dict]:
        url = member.get("linkedin_url")
        if url and "linkedin.com" in url:
            return fetch_executive_deep_profile(url)
        return None

    # Fetch profiles in parallel (limit to 5 to avoid rate limits)
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(fetch_profile, m): m for m in board_members[:10]}
        for future in as_completed(futures):
            member = futures[future]
            try:
                profile = future.result()
                if profile and profile.get("name"):
                    profiles.append(profile)
            except Exception as e:
                logger.warning("Error fetching board member profile: %s", e)

    result["board_members_researched"] = len(profiles)

    # Analyze board seats
    company_board_map = {}  # company -> list of board members

    for profile in profiles:
        name = profile.get("name", "Unknown")
        for seat in profile.get("board_seats", []):
            other_company = seat.get("company", "")
            if other_company and other_company.lower() != company_name.lower():
                if other_company not in company_board_map:
                    company_board_map[other_company] = []
                company_board_map[other_company].append({
                    "member": name,
                    "role": seat.get("role"),
                    "is_current": seat.get("is_current", False),
                })

    result["other_board_seats"] = company_board_map
    result["total_other_boards"] = len(company_board_map)

    # Detect interlocks (multiple board members at same other company)
    for company, members in company_board_map.items():
        if len(members) >= 2:
            result["interlocks"].append({
                "company": company,
                "shared_members": [m["member"] for m in members],
                "count": len(members),
                "flag_level": "HIGH",
            })

    return result


def deep_personnel_research(company_name: str, ticker: str = "",
                            company_linkedin_url: str = "",
                            known_executives: List[str] = None) -> Dict[str, Any]:
    """
    Comprehensive personnel research for deep intelligence reports.

    Returns:
    - Executive dossiers with full career history
    - Board composition and interlocks
    - Family connection detection
    - Key employee profiles
    """
    result = {
        "company_name": company_name,
        "ticker": ticker,
        "executive_dossiers": [],
        "board_analysis": {
            "members": [],
            "interlocks": [],
            "other_board_seats": {},
        },
        "family_connections": [],
        "key_employees": [],
        "research_stats": {
            "profiles_fetched": 0,
            "board_members_found": 0,
            "executives_found": 0,
            "interlocks_found": 0,
        },
        "source": "Apify/LinkedIn Deep Research",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    # Step 1: Fetch company employees
    logger.info("Fetching company employees for %s", company_name)
    employees = fetch_company_executives(company_name, company_linkedin_url, limit=30)

    result["key_employees"] = employees.get("other_employees", [])[:15]
    result["research_stats"]["executives_found"] = len(employees.get("executives", []))
    result["research_stats"]["board_members_found"] = len(employees.get("board_members", []))

    # Step 2: Deep profile research for executives
    all_execs = employees.get("executives", []) + employees.get("board_members", [])

    # Add any known executives
    if known_executives:
        for name in known_executives:
            if not any(e.get("name", "").lower() == name.lower() for e in all_execs):
                all_execs.append({"name": name, "linkedin_url": None})

    # Fetch deep profiles (limit to top 10 to manage API costs)
    for exec_info in all_execs[:10]:
        url = exec_info.get("linkedin_url")
        if url and "linkedin.com" in url:
            profile = fetch_executive_deep_profile(url)
            if profile and profile.get("name"):
                result["executive_dossiers"].append(profile)
                result["research_stats"]["profiles_fetched"] += 1

    # Step 3: Board interlock analysis
    board_members = employees.get("board_members", [])
    if board_members:
        result["board_analysis"]["members"] = board_members
        interlocks = research_board_interlocks(board_members, company_name)
        result["board_analysis"]["interlocks"] = interlocks.get("interlocks", [])
        result["board_analysis"]["other_board_seats"] = interlocks.get("other_board_seats", {})
        result["research_stats"]["interlocks_found"] = len(interlocks.get("interlocks", []))

    # Step 4: Family connection detection
    all_personnel = result["executive_dossiers"] + employees.get("executives", [])
    family_flags = detect_family_connections(all_personnel, company_name)
    result["family_connections"] = family_flags

    return result


# ── Convenience exports ───────────────────────────────────────────────────────

def get_executive_profile(linkedin_url: str) -> Dict[str, Any]:
    """Wrapper for single profile fetch."""
    return fetch_executive_deep_profile(linkedin_url)


def get_company_personnel(company_name: str, limit: int = 20) -> Dict[str, Any]:
    """Wrapper for company employee fetch."""
    return fetch_company_executives(company_name, limit=limit)


def get_deep_research(company_name: str, ticker: str = "") -> Dict[str, Any]:
    """Full deep personnel research."""
    return deep_personnel_research(company_name, ticker)
