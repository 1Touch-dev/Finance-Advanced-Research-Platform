"""
M&A Rumor Tracking Service (Band C #39)
Uses real news data from NewsAPI via financial_news_connector.
"""

import hashlib
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone

from app.connectors.financial_news_connector import newsapi_search

log = logging.getLogger(__name__)

# ─── Cache ────────────────────────────────────────────────────────────────────

_cache: Dict[str, Any] = {}
_CACHE_TTL = 1800  # 30 minutes

MA_KEYWORDS = [
    "merger", "acquisition", "takeover", "buyout",
    "deal", "acquires", "merges with",
]

_MA_QUERY = " OR ".join(MA_KEYWORDS)


def _cache_get(key: str):
    entry = _cache.get(key)
    if entry and (time.time() - entry["ts"]) < _CACHE_TTL:
        return entry["data"]
    return None


def _cache_set(key: str, data: Any):
    _cache[key] = {"data": data, "ts": time.time()}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _classify_deal_type(title: str, description: str) -> str:
    text = f"{title} {description}".lower()
    if "hostile" in text or "takeover bid" in text or "unsolicited" in text:
        return "hostile_takeover"
    if "merger" in text or "merges with" in text or "merge" in text:
        return "merger"
    if "spinoff" in text or "spin off" in text or "spin-off" in text:
        return "spinoff"
    if "divestiture" in text or "divest" in text or "sells" in text or "sell unit" in text:
        return "divestiture"
    return "acquisition"


def _estimate_probability(title: str, description: str) -> float:
    """Heuristic probability score based on language strength."""
    text = f"{title} {description}".lower()
    score = 30.0
    if any(w in text for w in ["confirmed", "announces", "completed", "closed", "approved"]):
        score = 85.0
    elif any(w in text for w in ["agrees to", "signs deal", "definitive agreement"]):
        score = 75.0
    elif any(w in text for w in ["in talks", "exploring", "considering", "nearing"]):
        score = 55.0
    elif any(w in text for w in ["rumor", "rumour", "reportedly", "sources say", "could"]):
        score = 35.0
    return score


def _determine_status(title: str, description: str) -> str:
    text = f"{title} {description}".lower()
    if any(w in text for w in ["confirmed", "completed", "closes", "approved", "finalizes"]):
        return "confirmed"
    if any(w in text for w in ["denied", "walks away", "collapses", "rejected", "terminated"]):
        return "denied"
    return "rumor"


def _article_to_rumor(article: dict) -> dict:
    title = article.get("title") or ""
    description = article.get("description") or ""
    url = article.get("url") or ""
    source = article.get("source") or "Unknown"
    published = article.get("date") or ""

    rumor_id = hashlib.md5(f"{title}{url}".encode()).hexdigest()[:12]
    deal_type = _classify_deal_type(title, description)
    probability = _estimate_probability(title, description)
    status = _determine_status(title, description)

    return {
        "id": rumor_id,
        "headline": title,
        "summary": description,
        "source": source,
        "url": url,
        "published_at": published,
        "deal_type": deal_type,
        "probability": probability,
        "status": status,
        "sector": "Unknown",
        "target": None,
        "acquirer": None,
        "estimated_value": None,
        "provider": "NewsAPI",
    }


def _fetch_ma_news(limit: int = 50) -> List[dict]:
    """Fetch and transform M&A news into rumor format. Cached 30 min."""
    cached = _cache_get("ma_news_all")
    if cached is not None:
        return cached

    articles = newsapi_search(_MA_QUERY, limit=limit)
    if not articles:
        return []

    rumors = [_article_to_rumor(a) for a in articles if a.get("title")]
    _cache_set("ma_news_all", rumors)
    return rumors


# ─── Public API (signatures match what the route calls) ───────────────────────

def get_active_rumors(
    days: int = 30,
    status: Optional[str] = None,
    sector: Optional[str] = None,
    min_probability: float = 0.0,
) -> List[dict]:
    rumors = _fetch_ma_news()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    filtered = []
    for r in rumors:
        pub = r.get("published_at", "")
        if pub:
            try:
                pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                if pub_dt < cutoff:
                    continue
            except (ValueError, TypeError):
                pass

        if status and r.get("status") != status:
            continue
        if sector and sector.lower() != "unknown" and r.get("sector", "").lower() != sector.lower():
            continue
        if r.get("probability", 0) < min_probability:
            continue
        filtered.append(r)

    return filtered


def get_rumor_by_id(rumor_id: str) -> Optional[dict]:
    rumors = _fetch_ma_news()
    for r in rumors:
        if r.get("id") == rumor_id:
            return r
    return None


def get_rumors_by_ticker(ticker: str) -> List[dict]:
    cache_key = f"ticker_{ticker.upper()}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    articles = newsapi_search(f"{ticker} acquisition OR merger OR takeover", limit=20)
    if not articles:
        return []

    rumors = [_article_to_rumor(a) for a in articles if a.get("title")]
    _cache_set(cache_key, rumors)
    return rumors


def get_high_probability_rumors(min_score: float = 40.0) -> List[dict]:
    rumors = _fetch_ma_news()
    return [r for r in rumors if r.get("probability", 0) >= min_score]


def get_confirmed_deals() -> List[dict]:
    rumors = _fetch_ma_news()
    return [r for r in rumors if r.get("status") == "confirmed"]


def get_rumors_by_deal_type(deal_type: str) -> List[dict]:
    rumors = _fetch_ma_news()
    return [r for r in rumors if r.get("deal_type") == deal_type]


def get_largest_deals(limit: int = 10) -> List[dict]:
    rumors = _fetch_ma_news()
    sorted_rumors = sorted(rumors, key=lambda r: r.get("probability", 0), reverse=True)
    return sorted_rumors[:limit]


def get_ma_stats() -> Dict[str, Any]:
    rumors = _fetch_ma_news()
    if not rumors:
        return {
            "total_rumors": 0,
            "by_status": {},
            "by_deal_type": {},
            "avg_probability": 0,
            "source": "NewsAPI",
        }

    by_status: Dict[str, int] = {}
    by_type: Dict[str, int] = {}
    total_prob = 0.0

    for r in rumors:
        s = r.get("status", "rumor")
        by_status[s] = by_status.get(s, 0) + 1
        dt = r.get("deal_type", "acquisition")
        by_type[dt] = by_type.get(dt, 0) + 1
        total_prob += r.get("probability", 0)

    return {
        "total_rumors": len(rumors),
        "by_status": by_status,
        "by_deal_type": by_type,
        "avg_probability": round(total_prob / len(rumors), 1) if rumors else 0,
        "source": "NewsAPI",
    }


def search_rumors(query: str) -> List[dict]:
    cache_key = f"search_{query.lower()}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    search_q = f"{query} acquisition OR merger OR takeover OR buyout"
    articles = newsapi_search(search_q, limit=20)
    if not articles:
        return []

    rumors = [_article_to_rumor(a) for a in articles if a.get("title")]
    _cache_set(cache_key, rumors)
    return rumors


def get_recent_updates(hours: int = 24) -> List[dict]:
    rumors = _fetch_ma_news()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    recent = []
    for r in rumors:
        pub = r.get("published_at", "")
        if pub:
            try:
                pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                if pub_dt >= cutoff:
                    recent.append(r)
            except (ValueError, TypeError):
                pass
    return recent
