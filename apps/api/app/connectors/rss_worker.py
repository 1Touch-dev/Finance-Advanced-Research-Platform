"""
RSS Global News Intelligence — Phase 1
=======================================
• 50 curated global RSS feeds across Finance, Macro, News, Tech, Policy
• feedparser polling worker (runs on cron via PM2)
• crawl4ai fallback for non-RSS / JS-heavy sites
• Entity keyword matching → auto-links articles to tracked entities
• Stores in Postgres: rss_sources, rss_articles tables

Usage:
    python rss_worker.py          # one full poll cycle
    python rss_worker.py --loop   # continuous (used by PM2)
"""

import os
import logging
import hashlib
import re
import time
import json
from datetime import datetime, timezone
from typing import Optional
import feedparser
import requests
from sqlalchemy import create_engine, text

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://user:password@127.0.0.1:5433/mydb"
)
_engine = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL)
    return _engine


# ─── 50 Core RSS Feeds ────────────────────────────────────────────────────────

CORE_FEEDS = [
    # Finance / Markets
    {"name": "Bloomberg Markets",        "url": "https://feeds.bloomberg.com/markets/news.rss",                    "category": "finance",   "region": "global"},
    {"name": "MarketWatch Top Stories",  "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories",     "category": "finance",   "region": "us"},
    {"name": "Yahoo Finance",            "url": "https://finance.yahoo.com/news/rssindex",                         "category": "finance",   "region": "us"},
    {"name": "Seeking Alpha",            "url": "https://seekingalpha.com/feed.xml",                               "category": "finance",   "region": "us"},
    {"name": "Investing.com",            "url": "https://www.investing.com/rss/news.rss",                          "category": "finance",   "region": "global"},
    {"name": "ZeroHedge",               "url": "https://feeds.feedburner.com/zerohedge/feed",                     "category": "finance",   "region": "us"},
    {"name": "Nasdaq News",             "url": "https://www.nasdaq.com/feed/rssoutbound",                         "category": "finance",   "region": "us"},

    # Central Banks / Macro
    {"name": "Federal Reserve",         "url": "https://www.federalreserve.gov/feeds/press_all.xml",              "category": "macro",     "region": "us"},
    {"name": "FRED Blog",               "url": "https://fredblog.stlouisfed.org/feed/",                           "category": "macro",     "region": "us"},
    {"name": "BIS",                     "url": "https://www.bis.org/rss/index.htm",                               "category": "macro",     "region": "global"},
    {"name": "IMF News",                "url": "https://www.imf.org/en/News/RSS",                                  "category": "macro",     "region": "global"},
    {"name": "World Bank",              "url": "https://www.worldbank.org/en/news/all/rss",                        "category": "macro",     "region": "global"},
    {"name": "OECD",                    "url": "https://www.oecd.org/newsroom/rss.xml",                           "category": "macro",     "region": "global"},
    {"name": "ECB",                     "url": "https://www.ecb.europa.eu/rss/html/index.en.html",                "category": "macro",     "region": "europe"},

    # General News (Finance angle)
    {"name": "BBC Business",            "url": "http://feeds.bbci.co.uk/news/business/rss.xml",                   "category": "news",      "region": "global"},
    {"name": "BBC World",               "url": "http://feeds.bbci.co.uk/news/world/rss.xml",                      "category": "news",      "region": "global"},
    {"name": "Reuters Top News",        "url": "https://feeds.reuters.com/reuters/topNews",                       "category": "news",      "region": "global"},
    {"name": "Reuters Business",        "url": "https://feeds.reuters.com/reuters/businessNews",                  "category": "news",      "region": "global"},
    {"name": "AP Top News",             "url": "https://feeds.apnews.com/rss/apf-topnews",                        "category": "news",      "region": "global"},
    {"name": "The Guardian Business",   "url": "https://www.theguardian.com/uk/business/rss",                     "category": "news",      "region": "global"},
    {"name": "The Guardian World",      "url": "https://www.theguardian.com/world/rss",                           "category": "news",      "region": "global"},

    # US Government / Policy
    {"name": "SEC Press Releases",      "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcurrent&type=&dateb=&owner=include&count=40&search_text=&output=atom", "category": "government", "region": "us"},
    {"name": "Treasury Press",          "url": "https://home.treasury.gov/news/press-releases.xml",               "category": "government", "region": "us"},
    {"name": "CFTC",                    "url": "https://www.cftc.gov/PressRoom/PressReleases/rss.xml",             "category": "government", "region": "us"},
    {"name": "BLS News",                "url": "https://www.bls.gov/feed/bls_latest.rss",                         "category": "government", "region": "us"},
    {"name": "EIA Today in Energy",     "url": "https://www.eia.gov/rss/todayinenergy.xml",                       "category": "government", "region": "us"},
    {"name": "WTO News",                "url": "https://www.wto.org/english/news_e/news_e.rss",                   "category": "government", "region": "global"},

    # Tech / AI
    {"name": "TechCrunch",             "url": "https://techcrunch.com/feed/",                                     "category": "tech",      "region": "us"},
    {"name": "The Verge",              "url": "https://www.theverge.com/rss/index.xml",                           "category": "tech",      "region": "us"},
    {"name": "Hacker News",            "url": "https://news.ycombinator.com/rss",                                 "category": "tech",      "region": "global"},
    {"name": "VentureBeat",           "url": "https://venturebeat.com/feed/",                                    "category": "tech",      "region": "us"},
    {"name": "OpenAI News",           "url": "https://openai.com/news/rss.xml",                                  "category": "tech",      "region": "global"},

    # Crypto / DeFi
    {"name": "CoinDesk",              "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",                   "category": "crypto",    "region": "global"},
    {"name": "Cointelegraph",         "url": "https://cointelegraph.com/rss",                                     "category": "crypto",    "region": "global"},
    {"name": "Decrypt",               "url": "https://decrypt.co/feed",                                           "category": "crypto",    "region": "global"},

    # Asia / International
    {"name": "Nikkei Asia",           "url": "https://news.google.com/rss/search?q=site:asia.nikkei.com",         "category": "news",      "region": "asia"},
    {"name": "SCMP Business",         "url": "https://news.google.com/rss/search?q=site:scmp.com+business",       "category": "news",      "region": "asia"},
    {"name": "Economic Times India",  "url": "https://economictimes.indiatimes.com/rssfeedstopstories.cms",        "category": "news",      "region": "india"},
    {"name": "Business Standard India","url": "https://www.business-standard.com/rss/latest.rss",                 "category": "news",      "region": "india"},
    {"name": "Nikkei Japan (GNews)",  "url": "https://news.google.com/rss/search?q=site:nikkei.com",              "category": "news",      "region": "asia"},

    # Europe
    {"name": "City A.M.",             "url": "https://www.cityam.com/feed/",                                      "category": "finance",   "region": "europe"},
    {"name": "Irish Times Business",  "url": "https://www.irishtimes.com/cmlink/the-irish-times-business-news-1.1072480", "category": "news", "region": "europe"},
    {"name": "FT (GNews fallback)",   "url": "https://news.google.com/rss/search?q=site:ft.com+finance",          "category": "finance",   "region": "global"},
    {"name": "WSJ (GNews fallback)",  "url": "https://news.google.com/rss/search?q=site:wsj.com+finance",         "category": "finance",   "region": "us"},

    # MENA / Africa / LATAM
    {"name": "Al Jazeera Economy",    "url": "https://www.aljazeera.com/xml/rss/all.xml",                         "category": "news",      "region": "mena"},
    {"name": "Bloomberg Línea (GNews)","url": "https://news.google.com/rss/search?q=site:bloomberglinea.com",     "category": "finance",   "region": "latam"},
    {"name": "Gulf Business (GNews)", "url": "https://news.google.com/rss/search?q=site:gulfbusiness.com",        "category": "finance",   "region": "mena"},

    # Policy / Geopolitics
    {"name": "Foreign Affairs (GNews)","url": "https://news.google.com/rss/search?q=site:foreignaffairs.com",    "category": "policy",    "region": "global"},
    {"name": "Brookings",             "url": "https://www.brookings.edu/feed/",                                   "category": "policy",    "region": "global"},
    {"name": "Calculated Risk",       "url": "https://feeds.feedburner.com/CalculatedRisk",                      "category": "macro",     "region": "us"},
]


# ─── DB Setup ────────────────────────────────────────────────────────────────

SCHEMA_SQL_POSTGRES = """
CREATE TABLE IF NOT EXISTS rss_sources (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    url         TEXT NOT NULL UNIQUE,
    category    TEXT DEFAULT 'general',
    region      TEXT DEFAULT 'global',
    active      BOOLEAN DEFAULT TRUE,
    last_polled TIMESTAMPTZ,
    article_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rss_articles (
    id              SERIAL PRIMARY KEY,
    source_id       INTEGER REFERENCES rss_sources(id),
    source_name     TEXT,
    title           TEXT NOT NULL,
    url             TEXT NOT NULL UNIQUE,
    summary         TEXT,
    content         TEXT,
    published_at    TIMESTAMPTZ,
    fetched_at      TIMESTAMPTZ DEFAULT NOW(),
    category        TEXT,
    region          TEXT,
    content_hash    TEXT,
    matched_entities TEXT[],
    sentiment_label TEXT,
    perspective_tags TEXT[]
);

CREATE INDEX IF NOT EXISTS idx_rss_articles_published ON rss_articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_rss_articles_source ON rss_articles(source_id);
CREATE INDEX IF NOT EXISTS idx_rss_articles_entities ON rss_articles USING GIN(matched_entities);
CREATE INDEX IF NOT EXISTS idx_rss_articles_category ON rss_articles(category);
"""

# SQLite equivalent for local dev (see apps/api/app/core/settings.py — local
# runs default to sqlite:///./local.db). SQLite has no SERIAL/TIMESTAMPTZ/
# TEXT[]/GIN — matched_entities is stored as a JSON-encoded TEXT column
# instead and (de)serialized in Python (see _json_list helpers below).
# Table/column names are identical to the Postgres schema so every query in
# this module and in app/api/market.py works unmodified against either DB.
SCHEMA_SQL_SQLITE = """
CREATE TABLE IF NOT EXISTS rss_sources (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    url         TEXT NOT NULL UNIQUE,
    category    TEXT DEFAULT 'general',
    region      TEXT DEFAULT 'global',
    active      BOOLEAN DEFAULT 1,
    last_polled TIMESTAMP,
    article_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rss_articles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id       INTEGER REFERENCES rss_sources(id),
    source_name     TEXT,
    title           TEXT NOT NULL,
    url             TEXT NOT NULL UNIQUE,
    summary         TEXT,
    content         TEXT,
    published_at    TIMESTAMP,
    fetched_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    category        TEXT,
    region          TEXT,
    content_hash    TEXT,
    matched_entities TEXT,
    sentiment_label TEXT,
    perspective_tags TEXT
);

CREATE INDEX IF NOT EXISTS idx_rss_articles_published ON rss_articles(published_at);
CREATE INDEX IF NOT EXISTS idx_rss_articles_source ON rss_articles(source_id);
CREATE INDEX IF NOT EXISTS idx_rss_articles_category ON rss_articles(category);
"""


def _is_sqlite(engine) -> bool:
    return engine.dialect.name == "sqlite"


def bootstrap_schema():
    """Create tables if not exist and seed sources. Dialect-aware: uses the
    Postgres schema (with TEXT[]/GIN) on Postgres, and a SQLite-compatible
    schema locally — see SCHEMA_SQL_SQLITE above for why this split exists.

    SQLite's DBAPI (unlike psycopg) refuses to execute multiple ';'-separated
    statements in one call ("You can only execute one statement at a time"),
    so on SQLite each CREATE TABLE/INDEX is run individually.
    """
    engine = get_engine()
    sqlite = _is_sqlite(engine)
    with engine.begin() as conn:
        if sqlite:
            for statement in filter(None, (s.strip() for s in SCHEMA_SQL_SQLITE.split(";"))):
                conn.execute(text(statement))
        else:
            conn.execute(text(SCHEMA_SQL_POSTGRES))
        for feed in CORE_FEEDS:
            if sqlite:
                conn.execute(text("""
                    INSERT OR IGNORE INTO rss_sources (name, url, category, region)
                    VALUES (:name, :url, :category, :region)
                """), feed)
            else:
                conn.execute(text("""
                    INSERT INTO rss_sources (name, url, category, region)
                    VALUES (:name, :url, :category, :region)
                    ON CONFLICT (url) DO NOTHING
                """), feed)
    log.info("RSS schema bootstrapped with %d sources (%s)", len(CORE_FEEDS),
              "sqlite" if sqlite else "postgres")


# ─── Article parsing ──────────────────────────────────────────────────────────

def _content_hash(title: str, url: str) -> str:
    return hashlib.md5(f"{url}:{title}".encode()).hexdigest()


def _parse_date(entry) -> Optional[datetime]:
    for field in ("published_parsed", "updated_parsed", "created_parsed"):
        val = getattr(entry, field, None)
        if val:
            try:
                return datetime(*val[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return datetime.now(timezone.utc)


_HTML_TAG_RE = re.compile(r"<[^>]+>")
_URL_RE = re.compile(r"https?://\S+")


def _extract_entities(title: str, summary: str) -> list:
    """Simple keyword match against common finance entities.

    Strips HTML tags and URLs first: several GNews-proxy feeds (see
    CORE_FEEDS "(GNews fallback)" entries) return a summary that's just an
    `<a href="https://news.google.com/rss/articles/...">` wrapper — matching
    keywords against the raw HTML let the literal domain "google" (or base64
    URL-path noise) spuriously "match" entities like Google/Meta on articles
    that never mention them.
    """
    raw = f"{title} {summary or ''}"
    cleaned = _URL_RE.sub(" ", _HTML_TAG_RE.sub(" ", raw))
    text_lower = cleaned.lower()
    ENTITY_KEYWORDS = {
        "Apple": ["apple", "aapl", "apple inc"],
        "Microsoft": ["microsoft", "msft", "azure", "openai"],
        "Google": ["google", "alphabet", "googl", "deepmind"],
        "Amazon": ["amazon", "amzn", "aws", "whole foods"],
        "Tesla": ["tesla", "tsla", "elon musk", "spacex"],
        "Meta": ["meta", "facebook", "fb", "instagram", "whatsapp", "zuckerberg"],
        "Nvidia": ["nvidia", "nvda", "jensen huang"],
        "JPMorgan": ["jpmorgan", "jp morgan", "jpm", "jamie dimon"],
        "Goldman Sachs": ["goldman sachs", "goldman", "gs "],
        "Federal Reserve": ["federal reserve", "the fed", "fomc", "powell", "jerome powell"],
        "ECB": ["ecb", "european central bank", "lagarde", "christine lagarde"],
        "IMF": ["imf", "international monetary fund"],
        "World Bank": ["world bank"],
        "Bitcoin": ["bitcoin", "btc", "satoshi"],
        "Ethereum": ["ethereum", "eth ", "vitalik"],
        "Palantir": ["palantir", "pltr"],
        "OpenAI": ["openai", "chatgpt", "gpt-4", "gpt-5", "sam altman"],
        "Berkshire Hathaway": ["berkshire", "warren buffett", "charlie munger"],
        "BlackRock": ["blackrock", "larry fink"],
        "TSMC": ["tsmc", "taiwan semiconductor"],
        "Samsung": ["samsung"],
        "Alibaba": ["alibaba", "baba", "jack ma"],
        "Tencent": ["tencent"],
        "BYD": ["byd"],
        "Shell": ["shell", "royal dutch"],
        "ExxonMobil": ["exxon", "exxonmobil", "xom"],
        "Saudi Aramco": ["aramco", "saudi aramco"],
        "US Treasury": ["us treasury", "yellen", "janet yellen", "bessent"],
        "SEC": ["sec ", "securities and exchange", "gary gensler"],
        "OPEC": ["opec", "oil cartel"],
        "Trump": ["trump", "donald trump", "mar-a-lago"],
        "China": ["china", "beijing", "prc", "xi jinping", "pboc"],
        "EU": ["european union", "brussels", "ursula von der leyen"],
        "UK": ["bank of england", "boe ", "chancellor"],
    }
    matched = []
    for entity, keywords in ENTITY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            matched.append(entity)
    return matched


# ─── Feed Polling ────────────────────────────────────────────────────────────

def _poll_feed_feedparser(source: dict) -> list:
    """Poll a single RSS feed using feedparser."""
    articles = []
    try:
        feed = feedparser.parse(source["url"], request_headers={"User-Agent": "Mozilla/5.0 Finance-Platform/1.0"})
        if feed.bozo and not feed.entries:
            log.warning("Feed bozo error for %s", source["name"])
            return articles
        for entry in feed.entries[:30]:
            title = getattr(entry, "title", "").strip()
            url   = getattr(entry, "link",  "").strip()
            if not title or not url:
                continue
            summary = getattr(entry, "summary", "") or ""
            summary = summary[:1000]
            articles.append({
                "source_id":     source["id"],
                "source_name":   source["name"],
                "title":         title,
                "url":           url,
                "summary":       summary,
                "published_at":  _parse_date(entry),
                "category":      source["category"],
                "region":        source["region"],
                "content_hash":  _content_hash(title, url),
                "matched_entities": _extract_entities(title, summary),
            })
    except Exception as e:
        log.warning("feedparser error for %s: %s", source["name"], e)
    return articles


def _poll_feed_gnews_fallback(source: dict) -> list:
    """Fallback: fetch via Google News RSS (for sites without direct feeds)."""
    # Same as feedparser — Google News RSS URLs are standard
    return _poll_feed_feedparser(source)


def persist_articles(articles: list) -> int:
    """Upsert articles; returns count of newly inserted."""
    if not articles:
        return 0
    engine = get_engine()
    sqlite = _is_sqlite(engine)
    inserted = 0
    with engine.begin() as conn:
        for a in articles:
            try:
                entities = a.get("matched_entities", [])
                # SQLite has no array type — matched_entities travels as a
                # JSON-encoded TEXT column there (see SCHEMA_SQL_SQLITE);
                # readers (event_clustering.fetch_recent_articles) parse it
                # back into a list. Postgres keeps the native TEXT[] bind.
                if sqlite:
                    entities = json.dumps(entities or [])
                result = conn.execute(text("""
                    INSERT INTO rss_articles
                        (source_id, source_name, title, url, summary, published_at,
                         category, region, content_hash, matched_entities)
                    VALUES
                        (:source_id, :source_name, :title, :url, :summary, :published_at,
                         :category, :region, :content_hash, :matched_entities)
                    ON CONFLICT (url) DO NOTHING
                """), {**a, "matched_entities": entities})
                if result.rowcount > 0:
                    inserted += 1
            except Exception as e:
                log.debug("Insert skip: %s", e)
    return inserted


def run_poll_cycle() -> dict:
    """Poll all active sources once. Returns summary stats.

    Bootstraps the schema first (idempotent — CREATE TABLE IF NOT EXISTS) so
    this also works when triggered ad-hoc via POST /market/rss/poll, not just
    from the `--loop` PM2 entrypoint that used to be the only caller of
    bootstrap_schema(). Without this, a fresh local DB (or a fresh Postgres
    one) 500s on the very first manual poll with "no such table: rss_sources".
    """
    bootstrap_schema()
    engine = get_engine()
    with engine.connect() as conn:
        sources = conn.execute(text(
            "SELECT id, name, url, category, region FROM rss_sources WHERE active = TRUE"
        )).mappings().all()
        sources = [dict(s) for s in sources]

    stats = {"sources": len(sources), "articles_new": 0, "errors": 0}
    now_sql = "CURRENT_TIMESTAMP" if _is_sqlite(engine) else "NOW()"
    for source in sources:
        log.info("Polling: %s", source["name"])
        try:
            articles = _poll_feed_feedparser(source)
            new_count = persist_articles(articles)
            stats["articles_new"] += new_count
            # Update last_polled + article_count
            with engine.begin() as conn:
                conn.execute(text(f"""
                    UPDATE rss_sources
                    SET last_polled = {now_sql},
                        article_count = article_count + :new_count
                    WHERE id = :id
                """), {"id": source["id"], "new_count": new_count})
            log.info("  → %d/%d new (%s)", new_count, len(articles), source["name"])
        except Exception as e:
            stats["errors"] += 1
            log.warning("Error polling %s: %s", source["name"], e)
            with engine.begin() as conn:
                conn.execute(text(
                    "UPDATE rss_sources SET error_count = error_count + 1 WHERE id = :id"
                ), {"id": source["id"]})
        time.sleep(0.3)  # polite delay between requests

    log.info("Poll cycle complete: %d new articles from %d sources (%d errors)",
             stats["articles_new"], stats["sources"], stats["errors"])
    return stats


# ─── Entrypoint ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    bootstrap_schema()
    if "--loop" in sys.argv:
        log.info("Starting continuous RSS poll loop (every 15 minutes)")
        while True:
            run_poll_cycle()
            time.sleep(900)  # 15 minutes
    else:
        run_poll_cycle()
