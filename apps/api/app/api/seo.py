"""
SEO & Internal Linking API
Band A Priority #5: Internal linking across generated pages
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.auth.security import get_current_user
import re

router = APIRouter(prefix="/seo", tags=["seo"])


# ─── Models ─────────────────────────────────────────────────────────────────

class LinkSuggestion(BaseModel):
    anchor_text: str
    target_url: str
    target_title: str
    relevance_score: float
    link_type: str  # hub, related, definition, entity


class PageMetadata(BaseModel):
    url: str
    title: str
    page_type: str  # company, stock, intelligence, crypto, gov-trading, etc.
    entities: List[str]  # Entity IDs mentioned
    keywords: List[str]
    last_updated: str


class SitemapEntry(BaseModel):
    loc: str
    lastmod: str
    changefreq: str
    priority: float


# ─── Hub Pages (canonical landing pages for topic clusters) ────────────────

HUB_PAGES = {
    "markets": {
        "url": "/stock",
        "title": "Stock Analysis",
        "description": "Real-time stock analysis, valuations, and technical indicators",
        "children": ["/valuation", "/expert-analysis", "/compare"],
    },
    "intelligence": {
        "url": "/intelligence",
        "title": "Intelligence Reports",
        "description": "Multi-source entity intelligence dossiers",
        "children": ["/search", "/timeline", "/saved"],
    },
    "institutional": {
        "url": "/institutional",
        "title": "Institutional Tracking",
        "description": "13F filings and institutional ownership analysis",
        "children": ["/gov-trading"],
    },
    "crypto": {
        "url": "/crypto",
        "title": "Crypto Intelligence",
        "description": "Cryptocurrency market analysis and wallet tracking",
        "children": [],
    },
    "tools": {
        "url": "/registry",
        "title": "Entity Registry",
        "description": "OSINT entity database and enrichment",
        "children": ["/graph", "/tracking", "/tracking/alerts", "/skills"],
    },
}


# ─── In-Memory Page Registry (replace with DB in production) ───────────────

_page_registry: Dict[str, dict] = {}
_entity_pages: Dict[str, List[str]] = {}  # entity_id -> [page_urls]


# ─── Helper Functions ───────────────────────────────────────────────────────

def _extract_entities_from_content(content: str) -> List[str]:
    """Extract entity mentions from page content."""
    # Simple pattern matching for tickers and company names
    # In production, use NER model
    tickers = re.findall(r'\b[A-Z]{1,5}\b', content)
    return list(set(tickers))


def _calculate_relevance(source_page: dict, target_page: dict) -> float:
    """Calculate relevance score between two pages."""
    score = 0.0

    # Same page type
    if source_page.get("page_type") == target_page.get("page_type"):
        score += 0.2

    # Shared entities
    source_entities = set(source_page.get("entities", []))
    target_entities = set(target_page.get("entities", []))
    shared = source_entities & target_entities
    if shared:
        score += min(len(shared) * 0.1, 0.4)

    # Shared keywords
    source_keywords = set(source_page.get("keywords", []))
    target_keywords = set(target_page.get("keywords", []))
    shared_keywords = source_keywords & target_keywords
    if shared_keywords:
        score += min(len(shared_keywords) * 0.05, 0.2)

    # Hub page bonus
    for hub in HUB_PAGES.values():
        if target_page.get("url") == hub["url"]:
            score += 0.2
            break

    return min(score, 1.0)


def _get_hub_for_page(page_url: str) -> Optional[dict]:
    """Find the hub page for a given page URL."""
    for hub_id, hub in HUB_PAGES.items():
        if page_url == hub["url"] or page_url in hub["children"]:
            return hub
    return None


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.post("/register-page")
def register_page(page: PageMetadata, current_user: dict = Depends(get_current_user)):
    """Register a page for internal linking."""
    _page_registry[page.url] = {
        "url": page.url,
        "title": page.title,
        "page_type": page.page_type,
        "entities": page.entities,
        "keywords": page.keywords,
        "last_updated": page.last_updated,
    }

    # Update entity -> page index
    for entity_id in page.entities:
        if entity_id not in _entity_pages:
            _entity_pages[entity_id] = []
        if page.url not in _entity_pages[entity_id]:
            _entity_pages[entity_id].append(page.url)

    return {"registered": True, "url": page.url}


@router.get("/suggest-links")
def suggest_links(
    page_url: str,
    max_suggestions: int = 5,
) -> List[LinkSuggestion]:
    """
    Suggest internal links for a page.
    This is the core SEO feature - automatically links orphan pages to hubs.
    """
    source_page = _page_registry.get(page_url)

    suggestions = []

    # 1. Always link to parent hub if exists
    hub = _get_hub_for_page(page_url)
    if hub and page_url != hub["url"]:
        suggestions.append(LinkSuggestion(
            anchor_text=hub["title"],
            target_url=hub["url"],
            target_title=hub["title"],
            relevance_score=1.0,
            link_type="hub",
        ))

    # 2. Link to sibling pages in same hub
    if hub:
        for sibling_url in hub["children"]:
            if sibling_url != page_url:
                sibling = _page_registry.get(sibling_url)
                if sibling:
                    suggestions.append(LinkSuggestion(
                        anchor_text=sibling["title"],
                        target_url=sibling_url,
                        target_title=sibling["title"],
                        relevance_score=0.8,
                        link_type="related",
                    ))

    # 3. Link to pages with shared entities
    if source_page:
        for entity_id in source_page.get("entities", [])[:5]:  # Limit entity checks
            related_urls = _entity_pages.get(entity_id, [])
            for related_url in related_urls:
                if related_url != page_url:
                    related_page = _page_registry.get(related_url)
                    if related_page:
                        relevance = _calculate_relevance(source_page, related_page)
                        if relevance > 0.3:
                            suggestions.append(LinkSuggestion(
                                anchor_text=related_page["title"],
                                target_url=related_url,
                                target_title=related_page["title"],
                                relevance_score=relevance,
                                link_type="entity",
                            ))

    # 4. Deduplicate and sort by relevance
    seen_urls = set()
    unique_suggestions = []
    for s in suggestions:
        if s.target_url not in seen_urls:
            seen_urls.add(s.target_url)
            unique_suggestions.append(s)

    unique_suggestions.sort(key=lambda s: s.relevance_score, reverse=True)

    return unique_suggestions[:max_suggestions]


@router.get("/orphan-pages")
def find_orphan_pages():
    """Find pages with no inbound links (SEO problem)."""
    # In production, this would analyze the link graph
    # For now, return pages not in any hub

    orphans = []
    hub_urls = set()
    for hub in HUB_PAGES.values():
        hub_urls.add(hub["url"])
        hub_urls.update(hub["children"])

    for url, page in _page_registry.items():
        if url not in hub_urls:
            orphans.append({
                "url": url,
                "title": page["title"],
                "suggestion": "Add to a hub or create links from related pages",
            })

    return {"orphan_pages": orphans, "count": len(orphans)}


@router.get("/sitemap.xml")
def generate_sitemap():
    """Generate XML sitemap for search engines."""
    now = datetime.utcnow().strftime("%Y-%m-%d")

    entries = []

    # Static pages
    static_pages = [
        ("/", 1.0, "daily"),
        ("/pricing", 0.8, "weekly"),
        ("/status", 0.6, "hourly"),
        ("/support", 0.5, "monthly"),
    ]

    for url, priority, changefreq in static_pages:
        entries.append(SitemapEntry(
            loc=f"https://enterprise-intel.com{url}",
            lastmod=now,
            changefreq=changefreq,
            priority=priority,
        ))

    # Hub pages
    for hub in HUB_PAGES.values():
        entries.append(SitemapEntry(
            loc=f"https://enterprise-intel.com{hub['url']}",
            lastmod=now,
            changefreq="daily",
            priority=0.9,
        ))
        for child_url in hub["children"]:
            entries.append(SitemapEntry(
                loc=f"https://enterprise-intel.com{child_url}",
                lastmod=now,
                changefreq="daily",
                priority=0.7,
            ))

    # Dynamic pages from registry
    for url, page in _page_registry.items():
        if not any(url == e.loc.split(".com")[1] for e in entries if ".com" in e.loc):
            entries.append(SitemapEntry(
                loc=f"https://enterprise-intel.com{url}",
                lastmod=page.get("last_updated", now)[:10],
                changefreq="weekly",
                priority=0.5,
            ))

    # Generate XML
    xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_lines.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    for entry in entries:
        xml_lines.append("  <url>")
        xml_lines.append(f"    <loc>{entry.loc}</loc>")
        xml_lines.append(f"    <lastmod>{entry.lastmod}</lastmod>")
        xml_lines.append(f"    <changefreq>{entry.changefreq}</changefreq>")
        xml_lines.append(f"    <priority>{entry.priority}</priority>")
        xml_lines.append("  </url>")

    xml_lines.append("</urlset>")

    return "\n".join(xml_lines)


@router.get("/hubs")
def list_hubs():
    """List all hub pages for the site structure."""
    return {
        "hubs": [
            {
                "id": hub_id,
                "url": hub["url"],
                "title": hub["title"],
                "description": hub["description"],
                "children": hub["children"],
                "child_count": len(hub["children"]),
            }
            for hub_id, hub in HUB_PAGES.items()
        ]
    }


@router.post("/analyze-page")
def analyze_page_seo(url: str, content: str, title: str, current_user: dict = Depends(get_current_user)):
    """Analyze a page for SEO issues and suggestions."""
    issues = []
    suggestions = []

    # Title length
    if len(title) < 30:
        issues.append("Title too short (< 30 chars)")
    elif len(title) > 60:
        issues.append("Title too long (> 60 chars)")

    # Content length
    word_count = len(content.split())
    if word_count < 300:
        issues.append(f"Content too thin ({word_count} words, recommend 300+)")

    # Extract entities for linking
    entities = _extract_entities_from_content(content)

    # Check for orphan status
    hub = _get_hub_for_page(url)
    if not hub:
        suggestions.append("Page is orphaned - add to a hub or create inbound links")

    # Get link suggestions
    link_suggestions = suggest_links(url)
    if link_suggestions:
        suggestions.append(f"Add {len(link_suggestions)} internal links to improve connectivity")

    return {
        "url": url,
        "title_length": len(title),
        "word_count": word_count,
        "entities_found": entities[:10],
        "is_orphan": hub is None,
        "hub": hub["url"] if hub else None,
        "issues": issues,
        "suggestions": suggestions,
        "recommended_links": link_suggestions,
    }
