"""
AI Answer Visibility Tracking API
Band A Priority #11: Track Google AI Overview citations
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.session import get_db
import uuid

router = APIRouter(prefix="/ai-visibility", tags=["ai-visibility"])


# ─── Models ─────────────────────────────────────────────────────────────────

class CitationRecord(BaseModel):
    query: str
    ai_platform: str  # google_ai_overview, bing_copilot, perplexity, chatgpt
    our_url_cited: bool
    our_position: Optional[int]  # Position in citations if cited
    competitor_urls: List[str]
    screenshot_url: Optional[str]
    detected_at: str


class TrackingTarget(BaseModel):
    url: str
    keywords: List[str]
    check_frequency_hours: int = 24


# ─── In-Memory Storage ──────────────────────────────────────────────────────

_citations: List[dict] = []
_tracking_targets: Dict[str, dict] = {}
_visibility_scores: Dict[str, List[dict]] = {}  # url -> [daily scores]


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.post("/record")
def record_citation(citation: CitationRecord):
    """Record an AI citation observation."""
    citation_id = f"cite-{uuid.uuid4().hex[:8]}"

    record = {
        "id": citation_id,
        "query": citation.query,
        "ai_platform": citation.ai_platform,
        "our_url_cited": citation.our_url_cited,
        "our_position": citation.our_position,
        "competitor_urls": citation.competitor_urls,
        "screenshot_url": citation.screenshot_url,
        "detected_at": citation.detected_at or datetime.utcnow().isoformat(),
    }

    _citations.append(record)

    return {"id": citation_id, "recorded": True}


@router.get("/citations")
def list_citations(
    ai_platform: Optional[str] = None,
    cited_only: bool = False,
    days: int = 30,
    limit: int = 100,
):
    """List recent AI citations."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()

    results = [c for c in _citations if c["detected_at"] >= cutoff]

    if ai_platform:
        results = [c for c in results if c["ai_platform"] == ai_platform]

    if cited_only:
        results = [c for c in results if c["our_url_cited"]]

    # Sort by date descending
    results.sort(key=lambda x: x["detected_at"], reverse=True)

    return {"citations": results[:limit], "total": len(results)}


@router.post("/targets")
def add_tracking_target(target: TrackingTarget):
    """Add a URL to track for AI citations."""
    target_id = f"target-{uuid.uuid4().hex[:8]}"

    _tracking_targets[target_id] = {
        "id": target_id,
        "url": target.url,
        "keywords": target.keywords,
        "check_frequency_hours": target.check_frequency_hours,
        "created_at": datetime.utcnow().isoformat(),
        "last_checked": None,
        "status": "active",
    }

    return {"id": target_id, "status": "active"}


@router.get("/targets")
def list_tracking_targets():
    """List all tracking targets."""
    return {"targets": list(_tracking_targets.values())}


@router.delete("/targets/{target_id}")
def remove_tracking_target(target_id: str):
    """Remove a tracking target."""
    if target_id not in _tracking_targets:
        raise HTTPException(404, "Target not found")

    del _tracking_targets[target_id]
    return {"deleted": True}


@router.get("/dashboard")
def get_visibility_dashboard(days: int = 30):
    """Get AI visibility dashboard metrics."""
    cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
    recent_citations = [c for c in _citations if c["detected_at"] >= cutoff]

    # Calculate metrics
    total_checks = len(recent_citations)
    citations_found = sum(1 for c in recent_citations if c["our_url_cited"])

    # By platform
    by_platform = {}
    for c in recent_citations:
        platform = c["ai_platform"]
        if platform not in by_platform:
            by_platform[platform] = {"total": 0, "cited": 0}
        by_platform[platform]["total"] += 1
        if c["our_url_cited"]:
            by_platform[platform]["cited"] += 1

    # Calculate citation rates
    for platform in by_platform:
        total = by_platform[platform]["total"]
        cited = by_platform[platform]["cited"]
        by_platform[platform]["rate"] = round(cited / total * 100, 1) if total > 0 else 0

    # Position distribution
    positions = [c["our_position"] for c in recent_citations if c["our_position"]]
    avg_position = round(sum(positions) / len(positions), 1) if positions else None

    # Top competitors
    competitor_counts = {}
    for c in recent_citations:
        for url in c.get("competitor_urls", []):
            domain = url.split("/")[2] if "/" in url else url
            competitor_counts[domain] = competitor_counts.get(domain, 0) + 1

    top_competitors = sorted(competitor_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    # Trend (last 7 days vs previous 7 days)
    week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
    two_weeks_ago = (datetime.utcnow() - timedelta(days=14)).isoformat()

    this_week = [c for c in recent_citations if c["detected_at"] >= week_ago]
    last_week = [c for c in recent_citations if week_ago > c["detected_at"] >= two_weeks_ago]

    this_week_rate = sum(1 for c in this_week if c["our_url_cited"]) / len(this_week) * 100 if this_week else 0
    last_week_rate = sum(1 for c in last_week if c["our_url_cited"]) / len(last_week) * 100 if last_week else 0

    trend = round(this_week_rate - last_week_rate, 1)

    return {
        "period_days": days,
        "total_checks": total_checks,
        "citations_found": citations_found,
        "citation_rate": round(citations_found / total_checks * 100, 1) if total_checks > 0 else 0,
        "average_position": avg_position,
        "by_platform": by_platform,
        "top_competitors": [{"domain": d, "count": c} for d, c in top_competitors],
        "trend": {
            "this_week_rate": round(this_week_rate, 1),
            "last_week_rate": round(last_week_rate, 1),
            "change": trend,
            "direction": "up" if trend > 0 else "down" if trend < 0 else "flat",
        },
    }


@router.get("/queries")
def get_query_performance(limit: int = 50):
    """Get performance by query/keyword."""
    query_stats = {}

    for c in _citations:
        query = c["query"].lower().strip()
        if query not in query_stats:
            query_stats[query] = {"total": 0, "cited": 0, "positions": []}

        query_stats[query]["total"] += 1
        if c["our_url_cited"]:
            query_stats[query]["cited"] += 1
            if c["our_position"]:
                query_stats[query]["positions"].append(c["our_position"])

    # Calculate rates and sort
    results = []
    for query, stats in query_stats.items():
        results.append({
            "query": query,
            "total_checks": stats["total"],
            "times_cited": stats["cited"],
            "citation_rate": round(stats["cited"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0,
            "avg_position": round(sum(stats["positions"]) / len(stats["positions"]), 1) if stats["positions"] else None,
        })

    # Sort by citation rate descending
    results.sort(key=lambda x: (-x["citation_rate"], -x["total_checks"]))

    return {"queries": results[:limit]}


@router.get("/opportunities")
def get_optimization_opportunities():
    """Get suggestions for improving AI visibility."""
    opportunities = []

    # Find queries where we're not cited but competitors are
    uncited = [c for c in _citations if not c["our_url_cited"] and c["competitor_urls"]]

    # Group by query
    query_gaps = {}
    for c in uncited:
        query = c["query"]
        if query not in query_gaps:
            query_gaps[query] = {"count": 0, "competitors": set()}
        query_gaps[query]["count"] += 1
        for url in c["competitor_urls"]:
            domain = url.split("/")[2] if "/" in url else url
            query_gaps[query]["competitors"].add(domain)

    for query, data in sorted(query_gaps.items(), key=lambda x: x[1]["count"], reverse=True)[:10]:
        opportunities.append({
            "type": "content_gap",
            "query": query,
            "frequency": data["count"],
            "competing_domains": list(data["competitors"])[:5],
            "suggestion": f"Create or improve content targeting '{query}'",
        })

    # Find queries where we're cited but in low positions
    low_positions = [c for c in _citations if c["our_url_cited"] and c["our_position"] and c["our_position"] > 3]

    position_issues = {}
    for c in low_positions:
        query = c["query"]
        if query not in position_issues:
            position_issues[query] = []
        position_issues[query].append(c["our_position"])

    for query, positions in sorted(position_issues.items(), key=lambda x: sum(x[1])/len(x[1]), reverse=True)[:5]:
        avg_pos = sum(positions) / len(positions)
        opportunities.append({
            "type": "position_improvement",
            "query": query,
            "current_avg_position": round(avg_pos, 1),
            "suggestion": f"Improve content quality/authority for '{query}' to move from position {round(avg_pos)} to top 3",
        })

    return {"opportunities": opportunities}
