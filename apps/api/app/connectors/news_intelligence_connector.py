"""
News, retail sentiment and the open web (G-05).

Asked for on 14, 21, 30 and 31 July and never built. The existing
`rss_worker` is a Postgres-backed cron process that fills a table for the
platform; it cannot be called inline while a report renders, which is why the
report has carried zero articles. This connector is the report-time path.

Five sources, four of them free or on keys the pipeline already holds:

* **Google News RSS** — unauthenticated, no quota, and the widest net. It is
  an index of other outlets rather than a publisher, so it is used for
  discovery and every item keeps its originating outlet.
* **Finnhub company-news** — ticker-scoped and already keyed.
* **NYT Article Search** and **Guardian Content** — keyed, and both are
  archives rather than wires, which is what makes a multi-year timeline
  possible at all.
* **Reddit** — the public JSON endpoint. Retail sentiment is not evidence of
  anything about the business and is labelled as sentiment, not news.

The hard part is not fetching, it is deciding what counts as being about the
issuer. "Apple" matches an orchard and "Micron" matches a unit of length, so
every item is resolved against the entity before it is kept, and the rule that
did the keeping is recorded on the item. An article we cannot tie to the
issuer is dropped rather than included with a low score — a report that pads a
news section with loosely-matched items is worse than one with a short section.
"""

from __future__ import annotations

import html
import logging
import os
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set
from urllib.parse import quote_plus

import requests

logger = logging.getLogger(__name__)

_TIMEOUT = 20
_UA = "Mozilla/5.0 (compatible; FinanceResearchPlatform/1.0)"


def _key(name: str) -> str:
    """Read a key at call time, not at import.

    The report script loads its .env after importing connectors, so a
    module-level `os.getenv` captures an empty string and the source silently
    reports itself as failed. That cost three of five news sources on the
    first run of this connector.
    """
    return os.getenv(name, "")

GOOGLE_NEWS = "https://news.google.com/rss/search"
NYT_SEARCH = "https://api.nytimes.com/svc/search/v2/articlesearch.json"
GUARDIAN_SEARCH = "https://content.guardianapis.com/search"
REDDIT_SEARCH = "https://www.reddit.com/search.json"
FINNHUB_NEWS = "https://finnhub.io/api/v1/company-news"

# Themes worth separating. An article about an export licence and one about a
# product launch are both "news" and belong in different rows of the analysis.
_THEMES = {
    "regulatory": ("antitrust", "regulator", "ftc", "sec ", "doj",
                   "investigation", "probe", "subpoena", "export control",
                   "sanction", "licence", "license", "compliance", "fine"),
    "litigation": ("lawsuit", "sue", "sued", "court", "judge", "settlement",
                   "class action", "patent", "infringement", "verdict"),
    "governance": ("resign", "steps down", "appoint", "named ceo", "board",
                   "chairman", "successor", "departure", "hire", "chief"),
    "capital": ("buyback", "repurchase", "dividend", "raise", "offering",
                "debt", "notes", "acquisition", "acquire", "merger", "stake",
                "invest", "funding"),
    "operations": ("factory", "fab", "plant", "capacity", "supply", "shortage",
                   "production", "layoff", "hiring", "expansion", "data center",
                   "datacenter"),
    "results": ("earnings", "revenue", "guidance", "quarter", "forecast",
                "beat", "miss", "outlook", "results"),
    "policy": ("tariff", "congress", "senate", "white house", "bill",
               "legislation", "lobby", "government", "administration"),
}

_POSITIVE = ("beat", "record", "surge", "soar", "growth", "win", "wins",
             "upgrade", "strong", "expand", "breakthrough", "approval")
_NEGATIVE = ("miss", "fall", "plunge", "slump", "probe", "lawsuit", "fine",
             "downgrade", "weak", "layoff", "recall", "delay", "warning",
             "loss", "cut", "halt", "ban")


def _get(url: str, params: dict = None, headers: dict = None):
    try:
        response = requests.get(
            url, params=params, timeout=_TIMEOUT,
            headers={"User-Agent": _UA, **(headers or {})})
        if response.status_code == 200:
            return response
        logger.debug("GET %s -> %s", url, response.status_code)
    except Exception as error:
        logger.debug("GET %s failed: %s", url, error)
    return None


def _clean(text: str) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(text.split())


def _iso(value: Any) -> Optional[str]:
    """A date string as YYYY-MM-DD, whatever shape it arrived in."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc).strftime("%Y-%m-%d")
        except (ValueError, OSError):
            return None
    text = str(value)
    for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%a, %d %b %Y %H:%M:%S %z",
                "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    match = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    return match.group(0) if match else None


# ---------------------------------------------------------------------------
# Entity resolution
# ---------------------------------------------------------------------------

_CORPORATE_NOISE = re.compile(
    r"\b(inc|corp|corporation|company|co|ltd|limited|plc|holdings|"
    r"group|technologies|technology|systems|international|the)\b\.?",
    re.IGNORECASE)


def entity_tokens(entity_name: str, ticker: str = "") -> Dict[str, Any]:
    """The strings that mean this issuer, strongest first."""
    stem = _CORPORATE_NOISE.sub(" ", entity_name or "")
    stem = " ".join(stem.split())
    return {
        "full": (entity_name or "").strip(),
        "stem": stem,
        "ticker": (ticker or "").upper(),
        # A one-word stem is the risky case ("Micron", "Apple"); it needs a
        # second corroborating token in the text before an item is kept.
        "ambiguous": len(stem.split()) <= 1,
    }


_CONTEXT_WORDS = ("stock", "shares", "nasdaq", "nyse", "earnings", "ceo",
                  "chip", "company", "quarterly", "investor", "revenue",
                  "market cap", "analyst", "sec filing")


def resolves_to_entity(title: str, summary: str,
                       tokens: Dict[str, Any]) -> Optional[str]:
    """The rule under which this item is about the issuer, or None.

    Returning the rule rather than a boolean means the report can state why an
    article was included, which is the difference between a news section a
    reader trusts and one they skim.
    """
    text = f"{title} {summary}".lower()
    if not text.strip():
        return None

    if tokens["full"] and tokens["full"].lower() in text:
        return "full legal name in headline or summary"

    ticker = tokens["ticker"]
    if ticker and re.search(rf"\b{re.escape(ticker.lower())}\b", text):
        return f"ticker {ticker} as a standalone word"

    stem = (tokens["stem"] or "").lower()
    if stem and re.search(rf"\b{re.escape(stem)}\b", text):
        if not tokens["ambiguous"]:
            return "company short name"
        if any(word in text for word in _CONTEXT_WORDS):
            return "company short name alongside a market or corporate term"
        return None
    return None


def classify_theme(title: str, summary: str) -> List[str]:
    text = f"{title} {summary}".lower()
    return [theme for theme, words in _THEMES.items()
            if any(word in text for word in words)] or ["general"]


def tone_of(title: str) -> str:
    """Headline tone. Not sentiment analysis and not labelled as such."""
    lowered = (title or "").lower()
    up = sum(1 for w in _POSITIVE if w in lowered)
    down = sum(1 for w in _NEGATIVE if w in lowered)
    if up > down:
        return "positive"
    if down > up:
        return "negative"
    return "neutral"


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

def _parse_rss(xml_text: str, default_source: str) -> List[Dict[str, Any]]:
    """Items out of an RSS body without taking a feedparser dependency."""
    items = []
    for block in re.findall(r"<item>(.*?)</item>", xml_text, re.DOTALL):
        def field(tag):
            match = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", block, re.DOTALL)
            return _clean(match.group(1)) if match else ""

        title = field("title")
        if not title:
            continue
        # Google prefixes the outlet onto the title and repeats it in <source>.
        outlet = field("source") or default_source
        items.append({
            "title": re.sub(rf"\s*-\s*{re.escape(outlet)}$", "", title),
            "url": field("link"),
            "summary": field("description"),
            "date": _iso(field("pubDate")),
            "outlet": outlet,
            "source": default_source,
        })
    return items


def google_news(query: str, limit: int = 40) -> List[Dict[str, Any]]:
    response = _get(f"{GOOGLE_NEWS}?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en")
    if not response:
        return []
    return _parse_rss(response.text, "Google News")[:limit]


def google_news_windowed(query: str, years: int = 5,
                         per_window: int = 20) -> List[Dict[str, Any]]:
    """Google News across several years rather than the last week.

    An unqualified RSS query returns roughly seven days, which is why the
    first run of this connector produced a "timeline" spanning six days.
    Google honours `after:` and `before:` inside the query, so the window is
    walked a year at a time and the results concatenated. This is the
    difference between a news feed and the multi-year chronology James asked
    for on 30 July.
    """
    today = datetime.now(timezone.utc).date()
    out: List[Dict[str, Any]] = []
    for offset in range(years):
        end = today.replace(year=today.year - offset)
        start = today.replace(year=today.year - offset - 1)
        scoped = f"{query} after:{start.isoformat()} before:{end.isoformat()}"
        rows = google_news(scoped, limit=per_window)
        for row in rows:
            # An item returned inside a dated window but carrying no pubDate
            # still belongs to that window; without this the oldest years
            # drop out of the chronology entirely.
            row.setdefault("window", str(start.year))
            if not row.get("date"):
                row["date"] = f"{start.year}-01-01"
                row["date_is_window"] = True
        out.extend(rows)
        time.sleep(0.3)
    return out


def finnhub_company_news(ticker: str, days: int = 365,
                         limit: int = 60) -> List[Dict[str, Any]]:
    key = _key("FINNHUB_API_KEY")
    if not key or not ticker:
        return []
    today = datetime.now(timezone.utc).date()
    response = _get(FINNHUB_NEWS, {
        "symbol": ticker,
        "from": (today - timedelta(days=days)).isoformat(),
        "to": today.isoformat(),
        "token": key,
    })
    if not response:
        return []
    try:
        payload = response.json()
    except ValueError:
        return []
    return [{
        "title": _clean(row.get("headline")),
        "url": row.get("url"),
        "summary": _clean(row.get("summary")),
        "date": _iso(row.get("datetime")),
        "outlet": row.get("source") or "Finnhub",
        "source": "Finnhub",
        # The query was scoped to the ticker, so the provider has already made
        # the entity decision. Re-deriving it from the headline throws away
        # every item whose headline names the sector rather than the company.
        "ticker_scoped": True,
    } for row in (payload if isinstance(payload, list) else [])][:limit]


def nyt_articles(query: str, limit: int = 30) -> List[Dict[str, Any]]:
    key = _key("NYT_API_KEY")
    if not key:
        return []
    out = []
    for page in range(0, 2):
        response = _get(NYT_SEARCH, {
            "q": query, "api-key": key, "page": page,
            "sort": "newest",
        })
        time.sleep(1.2)   # NYT rate-limits hard at 5/min
        if not response:
            break
        try:
            docs = (response.json().get("response") or {}).get("docs") or []
        except ValueError:
            break
        for doc in docs:
            out.append({
                "title": _clean((doc.get("headline") or {}).get("main")),
                "url": doc.get("web_url"),
                "summary": _clean(doc.get("abstract") or doc.get("snippet")),
                "date": _iso(doc.get("pub_date")),
                "outlet": "The New York Times",
                "source": "NYT Article Search",
            })
        if len(out) >= limit:
            break
    return out[:limit]


def guardian_articles(query: str, limit: int = 30) -> List[Dict[str, Any]]:
    key = _key("GUARDIAN_API_KEY")
    if not key:
        return []
    response = _get(GUARDIAN_SEARCH, {
        "q": query, "api-key": key, "page-size": min(50, limit),
        "order-by": "newest", "show-fields": "trailText",
    })
    if not response:
        return []
    try:
        results = (response.json().get("response") or {}).get("results") or []
    except ValueError:
        return []
    return [{
        "title": _clean(row.get("webTitle")),
        "url": row.get("webUrl"),
        "summary": _clean((row.get("fields") or {}).get("trailText")),
        "date": _iso(row.get("webPublicationDate")),
        "outlet": "The Guardian",
        "source": "Guardian Content API",
    } for row in results][:limit]


_REDDIT_UA = "python:finance-research-platform:1.0 (by /u/research)"


def _reddit_token() -> Optional[str]:
    """An OAuth token from a script-type app, or None.

    Reddit closed unauthenticated access to the .json endpoints in 2023 — the
    old public URLs now return 403 from every datacentre address. The
    replacement is free but needs an app registered at
    reddit.com/prefs/apps, which yields a client id and secret. No token, no
    Reddit: the connector says so rather than reporting silence as an absence
    of chatter.
    """
    client_id = _key("REDDIT_CLIENT_ID")
    secret = _key("REDDIT_CLIENT_SECRET")
    if not client_id or not secret:
        return None
    try:
        response = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=(client_id, secret),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": _REDDIT_UA},
            timeout=_TIMEOUT)
        if response.status_code == 200:
            return response.json().get("access_token")
    except Exception as error:
        logger.debug("Reddit token failed: %s", error)
    return None


def reddit_mentions(query: str, limit: int = 40) -> List[Dict[str, Any]]:
    """Reddit search. Retail chatter, labelled as chatter and not as news."""
    token = _reddit_token()
    if not token:
        raise RuntimeError(
            "Reddit needs REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET. "
            "Registration is free at reddit.com/prefs/apps; the public JSON "
            "endpoints have returned 403 since 2023.")

    response = _get("https://oauth.reddit.com/search", {
        "q": query, "sort": "top", "t": "year", "limit": limit,
    }, headers={"Authorization": f"Bearer {token}",
                "User-Agent": _REDDIT_UA})
    if not response:
        return []
    try:
        children = (response.json().get("data") or {}).get("children") or []
    except ValueError:
        return []
    out = []
    for child in children:
        post = child.get("data") or {}
        out.append({
            "title": _clean(post.get("title")),
            "url": f"https://reddit.com{post.get('permalink', '')}",
            "summary": _clean(post.get("selftext"))[:400],
            "date": _iso(post.get("created_utc")),
            "outlet": f"r/{post.get('subreddit', '')}",
            "source": "Reddit",
            "score": post.get("score"),
            "comments": post.get("num_comments"),
        })
    return out


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def _dedupe(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """One story per headline. Wires are syndicated many times over."""
    seen: Dict[str, Dict[str, Any]] = {}
    for item in items:
        key = re.sub(r"[^a-z0-9]", "", (item.get("title") or "").lower())[:70]
        if not key:
            continue
        existing = seen.get(key)
        if existing:
            existing.setdefault("also_carried_by", set()).add(item.get("outlet"))
            continue
        seen[key] = item
    out = []
    for item in seen.values():
        carried = item.pop("also_carried_by", set())
        item["syndication"] = len(carried)
        out.append(item)
    return out


def get_news_intelligence(entity_name: str, ticker: str = "",
                          people: Optional[List[str]] = None,
                          include_reddit: bool = True,
                          years: int = 5,
                          max_items: int = 250) -> Dict[str, Any]:
    """Everything published about the issuer that we can tie to it."""
    tokens = entity_tokens(entity_name, ticker)
    short = tokens["stem"] or entity_name

    result: Dict[str, Any] = {
        "entity_name": entity_name,
        "ticker": ticker,
        "articles": [],
        "reddit": [],
        "sources_queried": [],
        "sources_failed": [],
        "people_mentions": [],
    }

    harvested: List[Dict[str, Any]] = []
    for label, call in (
        ("Google News", lambda: google_news(f'"{entity_name}" OR "{short}"')),
        ("Google News archive",
         lambda: google_news_windowed(f'"{short}"', years=years)),
        ("Finnhub", lambda: finnhub_company_news(ticker)),
        ("NYT", lambda: nyt_articles(short)),
        ("Guardian", lambda: guardian_articles(short)),
    ):
        try:
            rows = call() or []
        except Exception as error:
            logger.warning("News source %s failed: %s", label, error)
            result["sources_failed"].append(label)
            continue
        if rows:
            result["sources_queried"].append({"source": label, "returned": len(rows)})
            harvested.extend(rows)
        else:
            result["sources_failed"].append(label)

    kept = []
    dropped = 0
    for item in _dedupe(harvested):
        rule = resolves_to_entity(item.get("title", ""),
                                  item.get("summary", ""), tokens)
        if not rule and item.get("ticker_scoped"):
            rule = (f"returned by a query scoped to {tokens['ticker']}; the "
                    f"headline names the sector rather than the company")
        if not rule:
            dropped += 1
            continue
        item["matched_on"] = rule
        item["themes"] = classify_theme(item.get("title", ""),
                                        item.get("summary", ""))
        item["tone"] = tone_of(item.get("title", ""))
        kept.append(item)

    kept.sort(key=lambda i: (i.get("date") or ""), reverse=True)
    result["articles"] = kept[:max_items]
    result["resolved"] = len(kept)
    result["dropped_unresolved"] = dropped

    # Named insiders in coverage. This is the join between the news feed and
    # the filings — an article about the issuer that also names a director is
    # worth more than one that does not.
    if people:
        mentions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for item in result["articles"]:
            blob = f"{item.get('title', '')} {item.get('summary', '')}".lower()
            for person in people:
                parts = [p for p in re.split(r"[\s,]+", person) if len(p) > 2]
                if not parts:
                    continue
                if all(p.lower() in blob for p in parts[:2]):
                    mentions[person].append({
                        "title": item["title"], "url": item.get("url"),
                        "date": item.get("date"),
                    })
        result["people_mentions"] = sorted(
            ({"person": k, "articles": v, "count": len(v)}
             for k, v in mentions.items()),
            key=lambda r: -r["count"])

    if include_reddit:
        try:
            posts = reddit_mentions(f'"{short}" OR {ticker}' if ticker else short)
            result["reddit"] = [
                p for p in posts
                if resolves_to_entity(p.get("title", ""), p.get("summary", ""), tokens)
            ][:25]
            if result["reddit"]:
                result["sources_queried"].append(
                    {"source": "Reddit", "returned": len(result["reddit"])})
        except Exception as error:
            logger.info("Reddit OAuth unavailable (%s), trying Apify fallback", error)
            # Fallback: use Apify Reddit scraper (no API key needed)
            try:
                from app.connectors.apify_connector import fetch_reddit_posts
                query = f'"{short}" {ticker}' if ticker else short
                apify_posts = fetch_reddit_posts(query, max_posts=25)
                result["reddit"] = [
                    {
                        "title": p.get("title", ""),
                        "summary": p.get("body", "")[:200],
                        "score": p.get("score", 0),
                        "url": p.get("url", ""),
                        "outlet": f"r/{p.get('subreddit', '')}",
                        "source": "Reddit (Apify)",
                        "published": p.get("created"),
                    }
                    for p in apify_posts
                    if resolves_to_entity(p.get("title", ""), p.get("body", ""), tokens)
                ][:25]
                if result["reddit"]:
                    result["sources_queried"].append(
                        {"source": "Reddit (Apify)", "returned": len(result["reddit"])})
                else:
                    result["sources_failed"].append("Reddit")
                    result["reddit_unavailable_reason"] = "Apify returned no matching posts"
            except Exception as apify_err:
                logger.info("Reddit Apify fallback also failed: %s", apify_err)
                result["sources_failed"].append("Reddit")
                result["reddit_unavailable_reason"] = str(error)

    result["summary"] = _summarise(result)
    return result


def _summarise(result: Dict[str, Any]) -> Dict[str, Any]:
    articles = result.get("articles") or []
    themes = Counter()
    outlets = Counter()
    tone = Counter()
    by_month: Dict[str, int] = defaultdict(int)

    for item in articles:
        for theme in item.get("themes") or []:
            themes[theme] += 1
        outlets[item.get("outlet") or "Unattributed"] += 1
        tone[item.get("tone") or "neutral"] += 1
        date = item.get("date")
        if date:
            by_month[date[:7]] += 1

    reddit = result.get("reddit") or []
    return {
        "article_count": len(articles),
        "themes": themes.most_common(),
        "top_outlets": outlets.most_common(10),
        "tone": dict(tone),
        "by_month": sorted(by_month.items()),
        "date_range": ([articles[-1].get("date"), articles[0].get("date")]
                       if articles else None),
        "reddit_posts": len(reddit),
        "reddit_top_score": max((p.get("score") or 0 for p in reddit), default=0),
        "people_named": len(result.get("people_mentions") or []),
    }
