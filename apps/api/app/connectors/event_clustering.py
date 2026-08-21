"""
Event clustering — F-08 RSS Phase 2, step 1 (§4.1 of the design doc).

Groups recently-ingested rss_articles rows into "events": articles from
different sources that are almost certainly covering the same real-world
story, published within a tight time window of each other.

Degrade-never-raise: every public function returns an empty/partial result on
any failure (missing table, missing API key, network error) rather than
raising, so a clustering outage never breaks the RSS module that already
works today. This mirrors the pattern used throughout this codebase (see
apify_connector.py / crawl4ai_connector.py / news_intelligence_connector.py).
"""
from __future__ import annotations

import logging
import json
import math
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

_TIMEOUT = 20
_EMBED_MODEL = "text-embedding-3-small"

# ── US-finance focus (per platform mandate: this is a US stock-market research
# platform, not a general/global news reader) ────────────────────────────────
#
# Two layers, both default-on and both overridable via function args / API
# query params (see api/market.py's /rss/events/run categories|regions|
# us_finance_only):
#
#  1. Source-level: only pull articles whose rss_articles.category/region were
#     tagged finance/macro/government (stocks, Fed policy, SEC/Treasury — all
#     market-moving) and us/global (global wires like Bloomberg/Investing.com/
#     WSJ/FT cover US markets too — excluding them would gut the feed).
#     This alone removes general "news" category noise (world politics,
#     regional stories) and other-country-only sources (India, MENA, Asia).
#
#  2. Content-level: even within finance/global sources, broad wire feeds
#     (e.g. Bloomberg's "markets" RSS also carries geopolitics video segments)
#     can slip through layer 1. _is_finance_relevant() requires a stock/market
#     keyword hit or a matched-entity hit (tracked companies/tickers) before
#     an article counts as in-scope.
DEFAULT_FINANCE_CATEGORIES = ("finance", "macro", "government")
DEFAULT_US_REGIONS = ("us", "global")

_FINANCE_SIGNAL_RE = re.compile(
    r"\b("
    r"stock|stocks|share|shares|shareholder|equity|equities|"
    r"earnings|revenue|profit|margin|guidance|forecast|outlook|"
    r"ipo|dividend|buyback|merger|acquisition|acquire|takeover|buyout|"
    r"nasdaq|nyse|s&p|dow jones|"
    r"federal reserve|rate hike|rate cut|interest rate|inflation|"
    r"treasury yield|bond yield|sec filing|10-k|10-q|quarterly (?:earnings|report|results)|"
    r"market cap|valuation|ticker symbol|hedge fund|private equity|"
    r"stock analyst|market analyst|analyst rating|price target|upgrade[ds]? (?:to|from)|downgrade[ds]?|"
    r"bull market|bear market|market rally|selloff|sell-off|market correction|"
    r"stock split|short seller|insider trading|"
    r"\$\d"  # dollar amounts
    r")\b",
    re.IGNORECASE,
)


def _is_finance_relevant(article: Dict[str, Any]) -> bool:
    """Layer 2 content check — see module docstring above.

    Official government/macro feeds (Fed, Treasury, SEC, CFTC, BLS, EIA) are
    curated press-release feeds that are ~100% in-scope by construction, so
    they skip the keyword gate entirely — applying it there risks dropping
    legitimate releases that just don't happen to contain one of our keywords
    (e.g. "Powell speaks at Jackson Hole"). The gate exists for the noisier
    'finance' category (broad wire feeds like Bloomberg/Investing.com that
    also carry non-market video/opinion content, e.g. a Gaza ceasefire
    segment tagged 'finance' just because it ran on Bloomberg Markets).

    An article passes if it has a matched company/entity hit OR its
    title+summary contains a stock/market-relevant keyword.
    """
    if article.get("category") in ("macro", "government"):
        return True
    if article.get("matched_entities"):
        return True
    text_ = f"{article.get('title','')} {article.get('summary','') or ''}"
    return bool(_FINANCE_SIGNAL_RE.search(text_))


def _get_rss_engine():
    """Same helper as app.api.market._get_rss_engine — kept local to avoid a
    circular import between the API layer and this connector."""
    from sqlalchemy import create_engine
    db_url = os.getenv("DATABASE_URL", "postgresql+psycopg://user:password@127.0.0.1:5433/mydb")
    return create_engine(db_url)


def fetch_recent_articles(hours: int = 48, limit: int = 300,
                           categories: Optional[List[str]] = None,
                           regions: Optional[List[str]] = None,
                           us_finance_only: bool = True) -> List[Dict[str, Any]]:
    """Recent rss_articles rows, oldest-safe (returns [] if the table isn't
    there yet — e.g. the RSS poller hasn't run in this environment).

    By default (us_finance_only=True, categories/regions unset), scoped to
    DEFAULT_FINANCE_CATEGORIES + DEFAULT_US_REGIONS plus the content-level
    _is_finance_relevant() check — see module docstring. Pass
    us_finance_only=False (or explicit categories/regions) to widen scope,
    e.g. for a future non-US or general-news view.
    """
    from sqlalchemy import text
    effective_categories = categories or (list(DEFAULT_FINANCE_CATEGORIES) if us_finance_only else None)
    effective_regions = regions or (list(DEFAULT_US_REGIONS) if us_finance_only else None)
    try:
        engine = _get_rss_engine()
        params: Dict[str, Any] = {
            "cutoff": datetime.now(timezone.utc) - timedelta(hours=hours),
            "limit": limit,
        }
        filters = ["published_at > :cutoff"]
        if effective_categories:
            placeholders = []
            for i, cat in enumerate(effective_categories):
                key = f"cat{i}"
                params[key] = cat
                placeholders.append(f":{key}")
            filters.append(f"category IN ({', '.join(placeholders)})")
        if effective_regions:
            placeholders = []
            for i, reg in enumerate(effective_regions):
                key = f"reg{i}"
                params[key] = reg
                placeholders.append(f":{key}")
            filters.append(f"region IN ({', '.join(placeholders)})")
        where = " AND ".join(filters)
        with engine.connect() as conn:
            rows = conn.execute(text(f"""
                SELECT id, source_name, title, url, summary, published_at,
                       category, region, matched_entities
                FROM rss_articles
                WHERE {where}
                ORDER BY published_at DESC
                LIMIT :limit
            """), params).mappings().all()
        articles = [dict(r) for r in rows]
        # On SQLite, matched_entities is stored as a JSON-encoded TEXT column
        # (no native array type) — see rss_worker.SCHEMA_SQL_SQLITE. Postgres
        # already returns a native list via TEXT[], so only normalize the
        # string case here.
        for a in articles:
            entities = a.get("matched_entities")
            if isinstance(entities, str):
                try:
                    a["matched_entities"] = json.loads(entities)
                except Exception:
                    a["matched_entities"] = []
        if us_finance_only:
            articles = [a for a in articles if _is_finance_relevant(a)]
        return articles
    except Exception as e:
        logger.info("fetch_recent_articles: rss_articles unavailable (%s) — 0 articles", e)
        return []


# ── Text similarity ───────────────────────────────────────────────────────────

_STOPWORDS = set(
    "a an the of to in on for and or is are was were be been being with as at by "
    "from into over after before this that these those its it their his her our "
    "we you they i not no new say says said report reports reported will".split()
)


def _tokenize(text_: str) -> set:
    words = re.findall(r"[a-z0-9]+", (text_ or "").lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 2}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _openai_embeddings(texts: List[str]) -> Optional[List[List[float]]]:
    """OpenAI embeddings for a batch of texts, or None if no key / call fails.
    Cheap (~$0.02 / 1M tokens) — see docs/features/F08_..._INTELLIGENCE.md §7."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or not texts:
        return None
    try:
        resp = requests.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": _EMBED_MODEL, "input": texts},
            timeout=_TIMEOUT,
        )
        if not resp.ok:
            logger.info("OpenAI embeddings call failed: %s", resp.status_code)
            return None
        data = resp.json().get("data", [])
        return [row["embedding"] for row in data]
    except Exception as e:
        logger.info("OpenAI embeddings error: %s", e)
        return None


def _cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


# ── Clustering ────────────────────────────────────────────────────────────────

_SIMILARITY_THRESHOLD_EMBED = 0.82      # cosine, when OpenAI embeddings are available
_SIMILARITY_THRESHOLD_JACCARD = 0.30    # keyword-overlap fallback, no API key needed
_MAX_HOURS_APART = 30                   # same "event" shouldn't span more than ~1.25 days


def cluster_articles(articles: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """
    Group articles into events. Each returned list is one event (1+ articles).

    Two modes, chosen automatically:
    - Embedding mode (OPENAI_API_KEY set): cosine similarity over
      text-embedding-3-small vectors — catches paraphrased headlines
      ("Fed holds rates" vs "Federal Reserve keeps rates unchanged").
    - Keyword-overlap mode (no key / API unavailable): Jaccard similarity over
      tokenized title+summary — cruder but zero-cost and zero-dependency, so
      clustering still works when no OpenAI key is configured locally.

    Both modes additionally require articles to be within _MAX_HOURS_APART of
    each other — two similar headlines a week apart are not the same event.
    """
    if not articles:
        return []

    texts = [f"{a.get('title','')} {a.get('summary','') or ''}" for a in articles]
    embeddings = _openai_embeddings(texts)
    use_embeddings = embeddings is not None and len(embeddings) == len(articles)

    token_sets = None if use_embeddings else [_tokenize(t) for t in texts]

    def _same_event(i: int, j: int) -> bool:
        pub_i, pub_j = articles[i].get("published_at"), articles[j].get("published_at")
        if pub_i and pub_j:
            try:
                delta = abs((_as_dt(pub_i) - _as_dt(pub_j)).total_seconds()) / 3600
                if delta > _MAX_HOURS_APART:
                    return False
            except Exception:
                pass  # missing/odd timestamps shouldn't block clustering entirely
        if use_embeddings:
            return _cosine(embeddings[i], embeddings[j]) >= _SIMILARITY_THRESHOLD_EMBED
        return _jaccard(token_sets[i], token_sets[j]) >= _SIMILARITY_THRESHOLD_JACCARD

    n = len(articles)
    parent = list(range(n))

    def _find(x):
        while parent[x] != x:
            x = parent[x]
        return x

    def _union(x, y):
        rx, ry = _find(x), _find(y)
        if rx != ry:
            parent[rx] = ry

    for i in range(n):
        for j in range(i + 1, n):
            if _same_event(i, j):
                _union(i, j)

    groups: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for idx, article in enumerate(articles):
        groups[_find(idx)].append(article)

    clusters = list(groups.values())
    clusters.sort(key=lambda c: (len(c), max((a.get("published_at") or "") for a in c)), reverse=True)
    return clusters


def _as_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


_SAME_SOURCE_DEDUPE_JACCARD = 0.5


def _dedupe_same_source(cluster: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Collapse near-duplicate articles from the *same* outlet within one
    cluster — e.g. a wire story picked up by two different feed URLs (direct
    RSS + a GNews-proxy re-syndication) lands as two rss_articles rows with
    slightly different titles. Left uncollapsed, enrichment would double-count
    that outlet's facts/perspective, and worse, contradiction detection would
    compare the outlet's own two articles against each other and flag a false
    "cross-source" conflict (e.g. a preliminary vs. final vote count from the
    same wire, mislabeled as two sources disagreeing).

    Keeps the earliest-published copy of each near-duplicate pair.
    """
    kept: List[Dict[str, Any]] = []
    for a in cluster:
        title_tokens = _tokenize(a.get("title", ""))
        is_dup = False
        for k in kept:
            if k.get("source_name") != a.get("source_name"):
                continue
            if _jaccard(title_tokens, _tokenize(k.get("title", ""))) >= _SAME_SOURCE_DEDUPE_JACCARD:
                is_dup = True
                break
        if not is_dup:
            kept.append(a)
    return kept


def articles_by_ids(article_ids: List[int]) -> List[Dict[str, Any]]:
    """Fetch specific rss_articles rows by id, normalized the same way as
    fetch_recent_articles (matched_entities parsed to a list on SQLite).

    Used to retroactively re-check whether an already-persisted rss_events
    row still satisfies the current US-finance filter — see
    event_is_us_finance_relevant() / api/market.py's GET /rss/events.
    """
    if not article_ids:
        return []
    from sqlalchemy import text
    try:
        engine = _get_rss_engine()
        placeholders = ", ".join(f":id{i}" for i in range(len(article_ids)))
        params = {f"id{i}": aid for i, aid in enumerate(article_ids)}
        with engine.connect() as conn:
            rows = conn.execute(text(f"""
                SELECT id, category, region, title, summary, matched_entities
                FROM rss_articles WHERE id IN ({placeholders})
            """), params).mappings().all()
        articles = [dict(r) for r in rows]
        for a in articles:
            entities = a.get("matched_entities")
            if isinstance(entities, str):
                try:
                    a["matched_entities"] = json.loads(entities)
                except Exception:
                    a["matched_entities"] = []
        return articles
    except Exception as e:
        logger.info("articles_by_ids: lookup failed (%s)", e)
        return []


def event_is_us_finance_relevant(article_ids: List[int]) -> bool:
    """Retroactive US-finance check for an already-persisted rss_events row.

    Events are never deleted on their own, so a row created before this
    filter existed (or created with us_finance_only=False) would otherwise
    linger forever in the default "US finance only" view. Returns True if
    ANY of the event's source articles currently satisfy the finance/macro/
    government + us/global + keyword gate, so a mixed-source event with at
    least one qualifying article still shows.
    """
    for a in articles_by_ids(article_ids):
        if (a.get("category") in DEFAULT_FINANCE_CATEGORIES and
                a.get("region") in DEFAULT_US_REGIONS and
                _is_finance_relevant(a)):
            return True
    return False


def build_event_candidates(hours: int = 48, article_limit: int = 300,
                            max_events: int = 25,
                            categories: Optional[List[str]] = None,
                            regions: Optional[List[str]] = None,
                            us_finance_only: bool = True) -> List[Dict[str, Any]]:
    """
    Fetch recent articles, cluster them, and shape each cluster into the
    lightweight "candidate" dict the enrichment step (event_intelligence_service)
    consumes. Multi-source clusters are surfaced first since those are the ones
    where fact/contradiction/perspective analysis is actually possible.

    Defaults to US-stock-market-relevant content only (us_finance_only=True)
    — see the DEFAULT_FINANCE_CATEGORIES / DEFAULT_US_REGIONS / 
    _is_finance_relevant() docs above. Pass us_finance_only=False to widen
    scope back to the full 50-source global feed.
    """
    articles = fetch_recent_articles(
        hours=hours, limit=article_limit,
        categories=categories, regions=regions, us_finance_only=us_finance_only,
    )
    if not articles:
        return []
    clusters = cluster_articles(articles)

    candidates = []
    for cluster in clusters[:max_events]:
        cluster = _dedupe_same_source(cluster)
        cluster_sorted = sorted(cluster, key=lambda a: a.get("published_at") or "", reverse=True)
        headline = cluster_sorted[0].get("title", "")
        entities: set = set()
        for a in cluster:
            entities.update(a.get("matched_entities") or [])
        candidates.append({
            "headline": headline,
            "topic_entity": next(iter(entities), None),
            "article_ids": [a["id"] for a in cluster],
            "source_count": len({a.get("source_name") for a in cluster}),
            "articles": cluster_sorted,
        })
    return candidates
