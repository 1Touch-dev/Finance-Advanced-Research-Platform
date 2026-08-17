"""
Crawl4AI connector — self-hosted, free replacement for Apify (F-07).

Scope (Phase 1, per docs/features/F07_CRAWL4AI_INTEGRATION.md):
  - crawl_news()           replaces Apify's brilliant_gum/google-news-scraper
  - crawl_company_intel()  replaces Apify's website-content-crawler /
                            linkedin-company-scraper for about/leadership/IR pages
  - crawl_linkedin_company() experimental, proxy-gated, OFF by default (§11.2 —
                              LinkedIn/PitchBook stay on the Apify fallback until
                              a residential proxy budget is approved)

Design notes:
  - `crawl_news()` uses Google News RSS (static XML, no JS/anti-bot risk) via
    plain HTTP instead of spinning up a browser — this is the Day-2 "no
    anti-bot risk, quick win" item from the architecture doc. Crawl4AI's
    browser is reserved for the harder job: JS-heavy company/IR pages.
  - Every public function follows the codebase's standard degrade-never-raise
    pattern (see apify_connector.py / intelligence_service.py): on any error,
    log a warning and return an empty dict/list rather than raising, so a
    Crawl4AI outage never breaks the intelligence report pipeline.
  - Redis caching and per-domain rate limiting are both optional/best-effort —
    if redis is unreachable, we just skip the cache and crawl directly.
"""
import os
import time
import asyncio
import logging
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional

import requests

logger = logging.getLogger(__name__)

# ── Crawl4AI (browser engine) — import-wrapped per §6.1 ──────────────────────
try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False
    AsyncWebCrawler = None  # type: ignore
    BrowserConfig = None    # type: ignore
    CrawlerRunConfig = None  # type: ignore

# ── Redis (optional caching layer, §12.1) ─────────────────────────────────────
try:
    from redis import Redis
    _redis_client: Optional["Redis"] = None
except ImportError:
    Redis = None  # type: ignore
    _redis_client = None

PROXY_URL = os.getenv("PROXY_URL", "")
PROXY_ENABLED = os.getenv("PROXY_ENABLED", "false").lower() == "true"
CRAWL_CACHE_TTL = int(os.getenv("CRAWL4AI_CACHE_TTL", "3600"))

_last_request: Dict[str, float] = {}


def _rate_limit(domain: str, delay: float = 1.0) -> None:
    """Per-domain throttle, mirrors the pattern used elsewhere for gov/SEC connectors (§12.2)."""
    elapsed = time.time() - _last_request.get(domain, 0)
    if elapsed < delay:
        time.sleep(delay - elapsed)
    _last_request[domain] = time.time()


def _get_redis() -> Optional["Redis"]:
    global _redis_client
    if Redis is None:
        return None
    if _redis_client is None:
        try:
            url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379")
            _redis_client = Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
            _redis_client.ping()
        except Exception:
            _redis_client = False  # sentinel: tried once, unreachable — don't retry every call
    return _redis_client or None


def _cache_get(key: str) -> Optional[str]:
    client = _get_redis()
    if not client:
        return None
    try:
        val = client.get(f"crawl4ai:{key}")
        return val.decode("utf-8") if val else None
    except Exception:
        return None


def _cache_set(key: str, value: str, ttl: int = CRAWL_CACHE_TTL) -> None:
    client = _get_redis()
    if not client:
        return
    try:
        client.setex(f"crawl4ai:{key}", ttl, value)
    except Exception:
        pass


def _domain_of(url: str) -> str:
    return url.split("//")[-1].split("/")[0]


# ── Google News RSS (Day 2 — news scraping, zero anti-bot risk) ──────────────

def crawl_news(query: str, max_articles: int = 8) -> List[Dict[str, Any]]:
    """
    Fetch recent news articles about a person or company via Google News RSS.
    Same return shape as apify_connector.fetch_news() so callers can swap freely:
    [{title, url, published, source, snippet}]
    """
    if not query:
        return []
    try:
        _rate_limit("news.google.com", delay=1.0)
        resp = requests.get(
            "https://news.google.com/rss/search",
            params={"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"},
            timeout=15,
            headers={"User-Agent": "Mozilla/5.0 (Finance-Platform Crawl4AI/1.0)"},
        )
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        articles = []
        for item in root.findall("./channel/item")[:max_articles]:
            title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            pub_date = (item.findtext("pubDate") or "").strip()
            source_el = item.find("source")
            source = source_el.text if source_el is not None else None
            description = (item.findtext("description") or "")[:300]
            articles.append({
                "title": title,
                "url": link,
                "published": pub_date,
                "source": source,
                "snippet": description,
                "fetched_via": "Crawl4AI/Google News RSS",
            })
        return articles
    except Exception as e:
        logger.warning("Crawl4AI news fetch failed for %r: %s", query, e)
        return []


# ── Company IR / about / leadership pages (Day 3) ────────────────────────────

_INTEL_PATHS = ["", "/about", "/about-us", "/leadership", "/investors", "/news"]


async def _crawl_company_intel_async(domain: str, word_count_threshold: int = 80) -> Dict[str, Any]:
    browser_config = BrowserConfig(
        headless=True,
        enable_stealth=True,
        user_agent_mode="random",
        accept_downloads=False,
        verbose=False,
    )
    run_config = CrawlerRunConfig(
        word_count_threshold=word_count_threshold,
        exclude_external_links=True,
        page_timeout=15000,  # ms per page — without this, a slow/hung page can block indefinitely
        verbose=False,
    )
    urls = [f"https://{domain}{path}" for path in _INTEL_PATHS]

    # NOTE: deliberately NOT using arun_many() here. Its default
    # MemoryAdaptiveDispatcher has memory_wait_timeout=600s — if the host is
    # under memory pressure it silently stalls for up to 10 minutes despite
    # page_timeout being set (confirmed: arun_many hung 90s+ on a real domain
    # while sequential arun() calls for the same 6 URLs completed in ~24s
    # total). One browser context, sequential arun() per page, is faster in
    # practice and has no such hidden wait.
    pages: Dict[str, str] = {}
    async with AsyncWebCrawler(config=browser_config) as crawler:
        for url in urls:
            try:
                r = await asyncio.wait_for(crawler.arun(url=url, config=run_config), timeout=18)
                if getattr(r, "success", False) and getattr(r, "markdown", None):
                    pages[url] = r.markdown[:4000]
            except Exception as e:
                logger.debug("Crawl4AI page skipped %s: %s", url, e)
                continue

    combined = "\n\n---\n\n".join(pages.values())
    return {
        "domain": domain,
        "pages_crawled": len(pages),
        "pages": pages,
        "combined_markdown": combined[:12000],
        "source": "Crawl4AI",
    }


def crawl_company_intel(domain: str) -> Dict[str, Any]:
    """
    Crawl a company's public site (homepage, about, leadership, investors, news)
    and return clean Markdown, ready to feed an LLM for structured extraction.
    Replaces Apify's website-content-crawler for this use case.
    """
    if not domain:
        return {}
    if not CRAWL4AI_AVAILABLE:
        logger.info("Crawl4AI not installed — skipping company intel crawl for %s", domain)
        return {}

    cache_key = f"company_intel:{domain}"
    cached = _cache_get(cache_key)
    if cached:
        import json
        try:
            return json.loads(cached)
        except Exception:
            pass

    try:
        _rate_limit(domain, delay=1.0)
        # Sequential per-page crawl (see note above on why not arun_many) with
        # a hard ceiling belt-and-suspenders on top of the per-page timeout —
        # so this can never block the request thread indefinitely (§6.1).
        result = asyncio.run(asyncio.wait_for(_crawl_company_intel_async(domain), timeout=60))
        if result.get("pages_crawled"):
            import json
            _cache_set(cache_key, json.dumps(result))
        return result
    except asyncio.TimeoutError:
        logger.warning("Crawl4AI company intel crawl timed out for %s", domain)
        return {}
    except Exception as e:
        logger.warning("Crawl4AI company intel crawl failed for %s: %s", domain, e)
        return {}


async def _crawl_single_async(url: str, word_count_threshold: int = 50, use_proxy: bool = False) -> Optional[str]:
    browser_config = BrowserConfig(
        headless=True,
        enable_stealth=True,
        user_agent_mode="random",
        proxy=PROXY_URL if (use_proxy and PROXY_ENABLED and PROXY_URL) else None,
    )
    run_config = CrawlerRunConfig(
        word_count_threshold=word_count_threshold,
        page_timeout=15000,
        verbose=False,
    )
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(url=url, config=run_config)
    return result.markdown if getattr(result, "success", False) else None


def crawl_url(url: str, use_proxy: bool = False) -> Optional[str]:
    """Crawl a single URL, return clean Markdown (or None on failure). General-purpose helper."""
    if not url or not CRAWL4AI_AVAILABLE:
        return None
    try:
        domain = _domain_of(url)
        cached = _cache_get(f"url:{url}")
        if cached:
            return cached
        _rate_limit(domain, delay=1.0)
        markdown = asyncio.run(asyncio.wait_for(_crawl_single_async(url, use_proxy=use_proxy), timeout=30))
        if markdown:
            _cache_set(f"url:{url}", markdown)
        return markdown
    except asyncio.TimeoutError:
        logger.warning("Crawl4AI single-URL crawl timed out for %s", url)
        return None
    except Exception as e:
        logger.warning("Crawl4AI single-URL crawl failed for %s: %s", url, e)
        return None


# ── LinkedIn (experimental, proxy-gated — §11.2, Day 5) ───────────────────────

def crawl_linkedin_company(company_slug: str) -> Dict[str, Any]:
    """
    Experimental LinkedIn company crawl via residential proxy.
    Disabled by default (PROXY_ENABLED=false) — stealth mode alone does not
    reliably bypass LinkedIn's bot detection (confirmed in architecture doc §11.2).
    Until a proxy budget is approved, LinkedIn/PitchBook stay on the Apify
    fallback (apify_connector.fetch_linkedin_by_name / fetch_pitchbook_company).
    """
    if not (CRAWL4AI_AVAILABLE and PROXY_ENABLED and PROXY_URL):
        return {"source": "Crawl4AI/LinkedIn", "note": "disabled — PROXY_ENABLED=false or PROXY_URL unset, using Apify fallback"}
    try:
        url = f"https://www.linkedin.com/company/{company_slug}/"
        markdown = crawl_url(url, use_proxy=True)
        return {"source": "Crawl4AI/LinkedIn", "url": url, "markdown": markdown or ""}
    except Exception as e:
        logger.warning("Crawl4AI LinkedIn crawl failed for %s: %s", company_slug, e)
        return {"source": "Crawl4AI/LinkedIn", "note": f"crawl failed: {e}"}
