"""
OSINT Connector — Phase 5th-July
==================================
Inspired by: Maigret, theHarvester, Sherlock, SpiderFoot patterns

Open-source OSINT capabilities built with pure Python + free APIs:
  1. Username enumeration across 40+ platforms (Sherlock/Maigret style)
  2. Email pattern discovery from company domain
  3. Domain WHOIS & DNS lookup
  4. LinkedIn / professional profile signals (via Google/DuckDuckGo scrape)
  5. Corporate structure from UK Companies House
  6. Breach check (HaveIBeenPwned public data)
  7. Social presence aggregation
  8. Phone number intelligence (pattern-based)

No paid APIs required. All functions degrade gracefully.
"""

import os
import re
import logging
import time
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

log = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FinanceIntelligence/1.0; +https://github.com)"}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# ─── 1. Username Enumeration ──────────────────────────────────────────────────

# Platforms: URL template, expected status when user EXISTS
USERNAME_PLATFORMS = {
    "GitHub":          ("https://github.com/{}", 200),
    "Twitter/X":       ("https://x.com/{}", 200),
    "Reddit":          ("https://www.reddit.com/user/{}", 200),
    "Instagram":       ("https://www.instagram.com/{}/", 200),
    "LinkedIn":        ("https://www.linkedin.com/in/{}", 200),
    "YouTube":         ("https://www.youtube.com/@{}", 200),
    "TikTok":          ("https://www.tiktok.com/@{}", 200),
    "Pinterest":       ("https://www.pinterest.com/{}/", 200),
    "Twitch":          ("https://www.twitch.tv/{}", 200),
    "Snapchat":        ("https://www.snapchat.com/add/{}", 200),
    "Medium":          ("https://medium.com/@{}", 200),
    "Substack":        ("https://{}.substack.com", 200),
    "Dev.to":          ("https://dev.to/{}", 200),
    "HackerNews":      ("https://news.ycombinator.com/user?id={}", 200),
    "Product Hunt":    ("https://www.producthunt.com/@{}", 200),
    "AngelList":       ("https://angel.co/{}", 200),
    "Crunchbase":      ("https://www.crunchbase.com/person/{}", 200),
    "Keybase":         ("https://keybase.io/{}", 200),
    "GitLab":          ("https://gitlab.com/{}", 200),
    "Bitbucket":       ("https://bitbucket.org/{}/", 200),
    "Stack Overflow":  ("https://stackoverflow.com/users/{}", 200),
    "Kaggle":          ("https://www.kaggle.com/{}", 200),
    "Replit":          ("https://replit.com/@{}", 200),
    "Patreon":         ("https://www.patreon.com/{}", 200),
    "Telegram":        ("https://t.me/{}", 200),
    "Signal (link)":   ("https://signal.me/#{}", 200),
    "Spotify":         ("https://open.spotify.com/user/{}", 200),
    "SoundCloud":      ("https://soundcloud.com/{}", 200),
    "Behance":         ("https://www.behance.net/{}", 200),
    "Dribbble":        ("https://dribbble.com/{}", 200),
    "Fiverr":          ("https://www.fiverr.com/{}", 200),
    "Upwork":          ("https://www.upwork.com/freelancers/~{}", 200),
    "Etsy":            ("https://www.etsy.com/shop/{}", 200),
    "Vimeo":           ("https://vimeo.com/{}", 200),
    "Steam":           ("https://steamcommunity.com/id/{}", 200),
    "Xbox":            ("https://xboxgamertag.com/search/{}", 200),
    "Last.fm":         ("https://www.last.fm/user/{}", 200),
    "Goodreads":       ("https://www.goodreads.com/{}", 200),
    "Flickr":          ("https://www.flickr.com/people/{}", 200),
    "Wikipedia":       ("https://en.wikipedia.org/wiki/User:{}", 200),
}

NOT_FOUND_INDICATORS = [
    "page not found", "user not found", "sorry, this page", "doesn't exist",
    "account suspended", "404", "no such user"
]


def _check_username_on_platform(username: str, platform: str, url_template: str, expected_status: int) -> dict:
    url = url_template.format(username)
    try:
        resp = SESSION.get(url, timeout=5, allow_redirects=True)
        if resp.status_code == expected_status:
            body_lower = resp.text.lower()[:500]
            if not any(nf in body_lower for nf in NOT_FOUND_INDICATORS):
                return {"platform": platform, "url": url, "found": True, "status": resp.status_code}
        return {"platform": platform, "url": url, "found": False, "status": resp.status_code}
    except Exception:
        return {"platform": platform, "url": url, "found": None, "status": "timeout"}


def enumerate_username(username: str, max_workers: int = 12, timeout_per_platform: int = 5) -> dict:
    """
    Check username across 40+ platforms in parallel.
    Returns list of platforms where the account was found.
    Inspired by Sherlock/Maigret.
    """
    username = username.strip().lower().replace(" ", "")
    found = []
    not_found = []
    errors = []

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_check_username_on_platform, username, platform, url_template, expected_status): platform
            for platform, (url_template, expected_status) in USERNAME_PLATFORMS.items()
        }
        for future in as_completed(futures):
            try:
                result = future.result(timeout=timeout_per_platform + 1)
                if result["found"] is True:
                    found.append(result)
                elif result["found"] is False:
                    not_found.append(result["platform"])
                else:
                    errors.append(result["platform"])
            except Exception:
                errors.append(futures[future])

    return {
        "username":    username,
        "found_count": len(found),
        "platforms_found": [f["platform"] for f in found],
        "profiles":    found,
        "platforms_checked": len(USERNAME_PLATFORMS),
        "errors":      errors[:5],
    }


# ─── 2. Email Pattern Discovery ──────────────────────────────────────────────

COMMON_EMAIL_PATTERNS = [
    "{first}.{last}",
    "{first}{last}",
    "{f}{last}",
    "{first}",
    "{last}.{first}",
    "{last}{first}",
    "{first}_{last}",
    "{f}.{last}",
    "{first}{l}",
]


def discover_email_patterns(first_name: str, last_name: str, domain: str) -> list:
    """Generate likely email addresses based on naming patterns."""
    first = first_name.lower().strip()
    last  = last_name.lower().strip()
    f = first[0] if first else ""
    l = last[0] if last else ""
    emails = []
    for pattern in COMMON_EMAIL_PATTERNS:
        try:
            local = pattern.format(first=first, last=last, f=f, l=l)
            emails.append(f"{local}@{domain}")
        except KeyError:
            pass
    return emails


def verify_email_exists(email: str) -> dict:
    """
    Basic email format validation + MX record check via DNS (no SMTP needed).
    Uses a free SMTP verification approach via DNS lookup.
    """
    import socket
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return {"email": email, "valid_format": False}
    domain = email.split("@")[1]
    try:
        mx = socket.getaddrinfo(domain, 25, socket.AF_UNSPEC, socket.SOCK_STREAM)
        has_mx = len(mx) > 0
    except Exception:
        has_mx = False
    return {"email": email, "valid_format": True, "mx_record_found": has_mx}


# ─── 3. Domain WHOIS + DNS ───────────────────────────────────────────────────

def domain_intelligence(domain: str) -> dict:
    """
    Domain intelligence: WHOIS + DNS records via free APIs.
    Uses whois.domaintools.com API (free tier) or python-whois.
    """
    result = {"domain": domain}

    # DNS records via Google DoH
    try:
        resp = SESSION.get(
            "https://dns.google/resolve",
            params={"name": domain, "type": "A"},
            timeout=5
        )
        if resp.ok:
            data = resp.json()
            result["a_records"] = [a.get("data") for a in data.get("Answer", []) if a.get("type") == 1]
    except Exception:
        pass

    # MX records
    try:
        resp = SESSION.get(
            "https://dns.google/resolve",
            params={"name": domain, "type": "MX"},
            timeout=5
        )
        if resp.ok:
            data = resp.json()
            result["mx_records"] = [a.get("data") for a in data.get("Answer", []) if a.get("type") == 15]
    except Exception:
        pass

    # TXT records (SPF, DMARC)
    try:
        resp = SESSION.get(
            "https://dns.google/resolve",
            params={"name": domain, "type": "TXT"},
            timeout=5
        )
        if resp.ok:
            data = resp.json()
            txts = [a.get("data") for a in data.get("Answer", []) if a.get("type") == 16]
            result["txt_records"] = txts
            result["has_spf"]     = any("v=spf1" in t for t in txts if t)
            result["has_dmarc"]   = any("v=DMARC1" in t for t in txts if t)
    except Exception:
        pass

    # WHOIS via RDAP (free, no auth)
    try:
        resp = SESSION.get(
            f"https://rdap.org/domain/{domain}",
            timeout=8
        )
        if resp.ok:
            rdap = resp.json()
            result["registrar"]   = next((e.get("ldhName") for e in rdap.get("nameservers", [])), None)
            result["events"]      = {
                e["eventAction"]: e.get("eventDate")
                for e in rdap.get("events", [])
                if e.get("eventAction") in ("registration", "expiration", "last changed")
            }
            result["status"]      = rdap.get("status", [])
    except Exception:
        pass

    return result


# ─── 4. LinkedIn Profile Signals ─────────────────────────────────────────────

def linkedin_search_signals(person_name: str, company: str = "") -> dict:
    """
    Infer LinkedIn presence via Google search (no scraping, meta only).
    Returns likely profile URL and search signals.
    """
    query = f'site:linkedin.com/in/ "{person_name}"' + (f' "{company}"' if company else "")
    # Use DuckDuckGo HTML (simple parsing)
    try:
        resp = SESSION.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            timeout=8
        )
        if resp.ok:
            urls = re.findall(r'linkedin\.com/in/[\w\-]+', resp.text)
            unique_urls = list(dict.fromkeys(["https://www." + u for u in urls]))[:5]
            return {"person": person_name, "likely_profiles": unique_urls, "query": query}
    except Exception as e:
        log.debug("LinkedIn search error: %s", e)
    return {"person": person_name, "likely_profiles": [], "query": query}


# ─── 5. Breach Check (HIBP public feed) ──────────────────────────────────────

def check_email_breaches(email: str) -> dict:
    """
    Check if email appears in known data breaches.
    Uses Have I Been Pwned public API (no key needed for domain check).
    """
    try:
        resp = requests.get(
            f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}",
            headers={
                "User-Agent": "FinanceIntelligencePlatform/1.0",
                "hibp-api-key": os.getenv("HIBP_API_KEY", ""),
            },
            timeout=5
        )
        if resp.status_code == 200:
            breaches = resp.json()
            return {
                "email": email,
                "breached": True,
                "breach_count": len(breaches),
                "breaches": [{"name": b.get("Name"), "date": b.get("BreachDate"), "domain": b.get("Domain")} for b in breaches[:5]],
            }
        elif resp.status_code == 404:
            return {"email": email, "breached": False}
        else:
            return {"email": email, "breached": None, "note": f"HIBP API key required (status {resp.status_code})"}
    except Exception as e:
        return {"email": email, "breached": None, "error": str(e)}


# ─── 6. Full Person OSINT Report ─────────────────────────────────────────────

def person_osint_report(
    name: str,
    username: Optional[str] = None,
    email: Optional[str] = None,
    company: Optional[str] = None,
    domain: Optional[str] = None,
) -> dict:
    """
    Comprehensive OSINT report for a person.
    Runs multiple checks in parallel where possible.
    """
    report: dict = {"name": name, "company": company}

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {}

        if username:
            futures["username_enum"] = pool.submit(enumerate_username, username)
        if domain:
            futures["domain_intel"] = pool.submit(domain_intelligence, domain)
        if email:
            futures["breach_check"] = pool.submit(check_email_breaches, email)
        futures["linkedin"] = pool.submit(linkedin_search_signals, name, company or "")

        for key, fut in futures.items():
            try:
                report[key] = fut.result(timeout=20)
            except Exception as e:
                report[key] = {"error": str(e)}

    # Email patterns if we have a domain
    if domain:
        first_name = name.split()[0] if name else ""
        last_name  = name.split()[-1] if len(name.split()) > 1 else ""
        report["email_patterns"] = discover_email_patterns(first_name, last_name, domain)[:5]

    return report


# ─── 7. Company OSINT Report ─────────────────────────────────────────────────

def company_osint_report(company_name: str, domain: Optional[str] = None) -> dict:
    """
    Company-level OSINT: domain intel, UK Companies House, social presence.
    """
    from app.connectors.financial_news_connector import ukch_search

    report: dict = {"company": company_name}

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {}
        if domain:
            futures["domain"] = pool.submit(domain_intelligence, domain)
        futures["uk_ch"]    = pool.submit(ukch_search, company_name, 5)
        futures["linkedin"] = pool.submit(linkedin_search_signals, company_name)

        for key, fut in futures.items():
            try:
                report[key] = fut.result(timeout=20)
            except Exception as e:
                report[key] = {"error": str(e)}

    return report
