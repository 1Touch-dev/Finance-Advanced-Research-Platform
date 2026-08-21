"""
API routes for financial data, news aggregation, and international registry lookups.
All endpoints are free-tier and gracefully degrade when keys are missing.
"""
import json
import os
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, Optional
import xml.etree.ElementTree as ET

import requests
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.connectors.financial_news_connector import (
    finnhub_quote, finnhub_company_profile, finnhub_financials,
    finnhub_insider_transactions, fmp_income_statement, fmp_balance_sheet,
    fmp_cash_flow, fmp_key_metrics, compute_beneish_mscore, compute_altman_zscore,
    fred_macro_data, aggregate_news, newsapi_search, guardian_search,
    nyt_search, gdelt_search, ukch_search, ukch_officers, icij_search, aleph_search,
)
from app.db.session import get_db, SessionLocal
from app.models.base import Base
from app.models.market_13f_schemas import (
    PositionDiffFilterStatus,
    PositionDiffRequest,
    PositionDiffResponse,
    PositionDiffSortField,
    SortDirection,
)
from app.services.sec_13f_service import (
    PositionAmbiguityError,
    get_institutional_position_diff,
)

router = APIRouter(prefix="/market")


# ── Financial: quote + profile ───────────────────────────────────────────────

@router.get("/quote")
def get_quote(ticker: str):
    return finnhub_quote(ticker)


@router.get("/profile")
def get_profile(ticker: str):
    return finnhub_company_profile(ticker)


@router.get("/metrics")
def get_metrics(ticker: str):
    return finnhub_financials(ticker)


@router.get("/insider-transactions")
def get_insider_transactions(ticker: str):
    return {"ticker": ticker, "transactions": finnhub_insider_transactions(ticker)}


# ── Financial statements (FMP) ────────────────────────────────────────────────

@router.get("/income-statement")
def get_income_statement(ticker: str, limit: int = 20):
    return {"ticker": ticker, "statements": fmp_income_statement(ticker, limit)}


@router.get("/balance-sheet")
def get_balance_sheet(ticker: str, limit: int = 10):
    return {"ticker": ticker, "statements": fmp_balance_sheet(ticker, limit)}


@router.get("/cash-flow")
def get_cash_flow(ticker: str, limit: int = 10):
    return {"ticker": ticker, "statements": fmp_cash_flow(ticker, limit)}


@router.get("/key-metrics")
def get_key_metrics(ticker: str):
    return fmp_key_metrics(ticker)


# ── Financial health scores ───────────────────────────────────────────────────

@router.get("/beneish-mscore")
def get_beneish_mscore(ticker: str):
    """Beneish M-Score: earnings manipulation detector. M > -2.22 = red flag."""
    return compute_beneish_mscore(ticker)


@router.get("/altman-zscore")
def get_altman_zscore(ticker: str):
    """Altman Z-Score: bankruptcy predictor. Z < 1.81 = distress zone."""
    return compute_altman_zscore(ticker)


@router.get("/financial-summary")
def get_financial_summary(ticker: str):
    """Combined financial health summary: quote + metrics + M-Score + Z-Score."""
    return {
        "ticker": ticker,
        "quote": finnhub_quote(ticker),
        "profile": finnhub_company_profile(ticker),
        "metrics": finnhub_financials(ticker),
        "key_metrics": fmp_key_metrics(ticker),
        "beneish_mscore": compute_beneish_mscore(ticker),
        "altman_zscore": compute_altman_zscore(ticker),
    }


# ── FRED macro data ───────────────────────────────────────────────────────────

@router.get("/macro")
def get_macro(series_id: str = "GDP", limit: int = 10):
    return {"series_id": series_id, "data": fred_macro_data(series_id, limit)}


# ── News aggregation ──────────────────────────────────────────────────────────

@router.get("/news")
def get_news(entity: str, limit: int = 10):
    """Aggregate news from NewsAPI + Guardian + NYT + GDELT + Finnhub."""
    return aggregate_news(entity, limit)


@router.get("/news/newsapi")
def get_newsapi(query: str, limit: int = 20):
    return {"articles": newsapi_search(query, limit)}


@router.get("/news/guardian")
def get_guardian(query: str, limit: int = 20):
    return {"articles": guardian_search(query, limit)}


@router.get("/news/nyt")
def get_nyt(query: str, limit: int = 20):
    return {"articles": nyt_search(query, limit)}


@router.get("/news/gdelt")
def get_gdelt(query: str, limit: int = 20):
    return {"articles": gdelt_search(query, limit)}


# ── International registries ──────────────────────────────────────────────────

@router.get("/uk/companies")
def search_uk_companies(q: str, limit: int = 10):
    return {"results": ukch_search(q, limit)}


@router.get("/uk/officers")
def get_uk_officers(company_number: str):
    return {"company_number": company_number, "officers": ukch_officers(company_number)}


@router.get("/icij/search")
def search_icij(q: str):
    """Search ICIJ Offshore Leaks — Panama/Paradise/Pandora Papers. No key needed."""
    return {"query": q, "results": icij_search(q)}


@router.get("/aleph/search")
def search_aleph(q: str, limit: int = 10):
    """Search ALEPH/OCCRP leaked document datasets."""
    return {"query": q, "results": aleph_search(q, limit)}


# ── RSS Global News Intelligence ──────────────────────────────────────────────

def _get_rss_engine():
    from sqlalchemy import create_engine
    db_url = os.getenv("DATABASE_URL", "postgresql+psycopg://user:password@127.0.0.1:5433/mydb")
    return create_engine(db_url)


@router.get("/rss/stats")
def get_rss_stats():
    """RSS intelligence statistics for dashboard display."""
    from sqlalchemy import text
    try:
        engine = _get_rss_engine()
        with engine.connect() as conn:
            total_articles = conn.execute(text("SELECT COUNT(*) FROM rss_articles")).scalar() or 0
            active_sources = conn.execute(text("SELECT COUNT(*) FROM rss_sources WHERE active = true")).scalar() or 50
            if engine.dialect.name == "sqlite":
                # SQLite has no unnest()/array type — matched_entities is a
                # JSON-encoded TEXT column there (see rss_worker.py
                # SCHEMA_SQL_SQLITE), so count distinct entities in Python.
                rows = conn.execute(text(
                    "SELECT matched_entities FROM rss_articles WHERE matched_entities IS NOT NULL"
                )).scalars().all()
                seen = set()
                for raw in rows:
                    try:
                        seen.update(json.loads(raw) or [])
                    except Exception:
                        continue
                entities_count = len(seen) or 15
            else:
                entities_count = conn.execute(text("""
                    SELECT COUNT(DISTINCT unnest(matched_entities)) FROM rss_articles
                    WHERE matched_entities IS NOT NULL AND array_length(matched_entities, 1) > 0
                """)).scalar() or 15
        return {
            "total_articles": total_articles,
            "active_sources": active_sources,
            "entities_count": entities_count,
        }
    except Exception as e:
        # Return defaults if database not available
        return {
            "total_articles": 0,
            "active_sources": 50,
            "entities_count": 15,
            "error": str(e),
        }


@router.get("/rss/sources")
def get_rss_sources():
    """List all 50 registered RSS sources with status."""
    from sqlalchemy import text
    try:
        engine = _get_rss_engine()
        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT id, name, url, category, region, active, last_polled, article_count, error_count
                FROM rss_sources ORDER BY category, name
            """)).mappings().all()
        return {"sources": [dict(r) for r in rows]}
    except Exception as e:
        return {"sources": [], "error": str(e)}


@router.get("/rss/articles")
def get_rss_articles(
    category: Optional[str] = None,
    region: Optional[str] = None,
    entity: Optional[str] = None,
    limit: int = Query(40, le=200),
    offset: int = 0,
    us_finance_only: Optional[bool] = Query(
        None,
        description="Scope to US stock-market-relevant content (finance/macro/government + us/global sources). "
                     "Defaults to true only when category/region/entity aren't explicitly set, so an explicit "
                     "filter pick (e.g. category=tech or region=india) still works as an opt-in override.",
    ),
):
    """
    Fetch RSS articles with optional filters.
    - category: finance | macro | news | tech | crypto | government | policy
    - region: us | global | europe | asia | india | mena | latam
    - entity: match against matched_entities array (e.g. 'Apple', 'Tesla')
    - us_finance_only: see param description — on by default for the unfiltered "browse" view.
    """
    from app.connectors.event_clustering import DEFAULT_FINANCE_CATEGORIES, DEFAULT_US_REGIONS, _is_finance_relevant
    from sqlalchemy import text
    engine = _get_rss_engine()
    sqlite = engine.dialect.name == "sqlite"

    apply_finance_default = us_finance_only if us_finance_only is not None else not (category or region or entity)

    filters = []
    params: dict = {"limit": limit, "offset": offset}
    if category:
        filters.append("category = :category")
        params["category"] = category
    elif apply_finance_default:
        placeholders = []
        for i, cat in enumerate(DEFAULT_FINANCE_CATEGORIES):
            key = f"cat{i}"
            params[key] = cat
            placeholders.append(f":{key}")
        filters.append(f"category IN ({', '.join(placeholders)})")
    if region:
        filters.append("region = :region")
        params["region"] = region
    elif apply_finance_default:
        placeholders = []
        for i, reg in enumerate(DEFAULT_US_REGIONS):
            key = f"reg{i}"
            params[key] = reg
            placeholders.append(f":{key}")
        filters.append(f"region IN ({', '.join(placeholders)})")
    if entity:
        # SQLite stores matched_entities as JSON-encoded TEXT (no array type
        # — see rss_worker.py SCHEMA_SQL_SQLITE), so a LIKE on the quoted
        # name is the equivalent of Postgres's `entity = ANY(matched_entities)`.
        if sqlite:
            filters.append("matched_entities LIKE :entity_like")
            params["entity_like"] = f'%"{entity}"%'
        else:
            filters.append(":entity = ANY(matched_entities)")
            params["entity"] = entity
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    order_by = "ORDER BY published_at DESC" if sqlite else "ORDER BY published_at DESC NULLS LAST"
    # Over-fetch a bit when the content-level keyword filter will run below,
    # since it's applied in Python after the SQL LIMIT — see note there.
    fetch_limit = limit * 3 if apply_finance_default and not category else limit
    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT id, source_name, title, url, summary, published_at,
                   category, region, matched_entities, sentiment_label
            FROM rss_articles
            {where}
            {order_by}
            LIMIT :fetch_limit OFFSET :offset
        """), {**params, "fetch_limit": fetch_limit}).mappings().all()
        total = conn.execute(text(f"SELECT COUNT(*) FROM rss_articles {where}"), params).scalar()
    articles = [dict(r) for r in rows]
    if sqlite:
        for a in articles:
            if isinstance(a.get("matched_entities"), str):
                try:
                    a["matched_entities"] = json.loads(a["matched_entities"])
                except Exception:
                    a["matched_entities"] = []
    if apply_finance_default and not category:
        # Layer 2: content-level keyword/entity check (same heuristic used by
        # the event-intelligence pipeline) — catches broad-wire noise (e.g. a
        # geopolitics video on a "finance" category feed) that the source-level
        # category/region filter alone can't. Only applied on the true default
        # "browse everything" view, never when the caller picked an explicit
        # category, so opting into finance content directly stays literal.
        articles = [a for a in articles if _is_finance_relevant(a)]
    return {"total": total, "articles": articles[:limit]}


@router.get("/rss/entity-feed")
def get_entity_rss_feed(entity: str, limit: int = 20):
    """Articles that mention a specific entity by name (auto-matched on ingest)."""
    from sqlalchemy import text
    engine = _get_rss_engine()
    sqlite = engine.dialect.name == "sqlite"
    with engine.connect() as conn:
        if sqlite:
            rows = conn.execute(text("""
                SELECT source_name, title, url, summary, published_at, category, region
                FROM rss_articles
                WHERE matched_entities LIKE :entity_like
                ORDER BY published_at DESC
                LIMIT :limit
            """), {"entity_like": f'%"{entity}"%', "limit": limit}).mappings().all()
        else:
            rows = conn.execute(text("""
                SELECT source_name, title, url, summary, published_at, category, region
                FROM rss_articles
                WHERE :entity = ANY(matched_entities)
                ORDER BY published_at DESC NULLS LAST
                LIMIT :limit
            """), {"entity": entity, "limit": limit}).mappings().all()
    return {"entity": entity, "articles": [dict(r) for r in rows]}


@router.get("/rss/digest")
def get_rss_digest(hours: int = 24, us_finance_only: bool = Query(
    True, description="Scope to US stock-market-relevant categories (finance/macro/government) + us/global sources. "
                       "Set false to see the full category breakdown across all 50 sources/regions.",
)):
    """
    Top news digest: latest unique articles per category for the last N hours.
    Grouped by category for a quick intelligence overview.
    """
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import text
    from app.connectors.event_clustering import DEFAULT_FINANCE_CATEGORIES, DEFAULT_US_REGIONS, _is_finance_relevant
    engine = _get_rss_engine()
    sqlite = engine.dialect.name == "sqlite"
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    order_null = "ORDER BY published_at DESC" if sqlite else "ORDER BY published_at DESC NULLS LAST"
    params: dict = {"cutoff": cutoff}
    scope_filter = ""
    if us_finance_only:
        cat_placeholders, reg_placeholders = [], []
        for i, cat in enumerate(DEFAULT_FINANCE_CATEGORIES):
            params[f"cat{i}"] = cat
            cat_placeholders.append(f":cat{i}")
        for i, reg in enumerate(DEFAULT_US_REGIONS):
            params[f"reg{i}"] = reg
            reg_placeholders.append(f":reg{i}")
        scope_filter = f" AND category IN ({', '.join(cat_placeholders)}) AND region IN ({', '.join(reg_placeholders)})"
    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT category, source_name, title, url, summary, published_at, matched_entities
            FROM (
                SELECT *,
                    ROW_NUMBER() OVER (PARTITION BY category {order_null}) AS rn
                FROM rss_articles
                WHERE published_at > :cutoff{scope_filter}
            ) sub
            WHERE rn <= {20 if us_finance_only else 10}
            ORDER BY category, published_at DESC
        """), params).mappings().all()
    digest: dict = {}
    for r in rows:
        cat = r["category"] or "general"
        entities = r["matched_entities"] or []
        if sqlite and isinstance(entities, str):
            try:
                entities = json.loads(entities)
            except Exception:
                entities = []
        digest.setdefault(cat, []).append({
            "source": r["source_name"],
            "title": r["title"],
            "url": r["url"],
            "summary": r["summary"],
            "published_at": str(r["published_at"]) if r["published_at"] else None,
            "entities": entities,
        })
    if us_finance_only:
        # Layer 2 content check (see event_clustering.py) — trims broad-wire
        # noise the source-level category/region filter alone lets through,
        # then caps back down to 10/category to match the non-scoped default.
        for cat in list(digest.keys()):
            filtered = [item for item in digest[cat]
                        if _is_finance_relevant({"title": item["title"], "summary": item["summary"],
                                                  "matched_entities": item["entities"]})]
            digest[cat] = (filtered or digest[cat])[:10]
    return {"hours": hours, "digest": digest}


@router.post("/rss/poll")
def trigger_rss_poll():
    """Manually trigger one RSS poll cycle (all 50 sources). Returns stats."""
    from app.connectors.rss_worker import run_poll_cycle
    stats = run_poll_cycle()
    return {"status": "ok", "stats": stats}


# ── F-08: RSS Phase 2 — Event Intelligence ────────────────────────────────────
# Clustering + fact extraction + contradiction detection + perspective
# labeling on top of the Phase-1 rss_articles feed. See
# docs/features/F08_RSS_PHASE2_EVENT_INTELLIGENCE.md for the full design.
#
# Enrichment calls GPT-4o and (optionally) Crawl4AI per event, which can take
# from seconds to a few minutes depending on cluster size — so this follows
# the exact same "kick off a background job, poll for status" pattern already
# used for the tracking digest (apps/api/app/api/tracking.py) rather than
# holding the HTTP request open, which is what caused the "Failed to fetch"
# digest timeout bug fixed earlier in this codebase.

_EVENT_JOBS: Dict[str, Dict[str, Any]] = {}


def _run_event_intelligence_job(job_id: str, hours: int, max_events: int, min_sources: int,
                                 us_finance_only: bool):
    from app.services.event_intelligence_service import run_event_intelligence_job
    db = SessionLocal()
    try:
        _EVENT_JOBS[job_id]["status"] = "running"
        result = run_event_intelligence_job(
            db, hours=hours, max_events=max_events, min_sources_for_enrichment=min_sources,
            us_finance_only=us_finance_only,
        )
        _EVENT_JOBS[job_id].update({
            "status": "failed" if result.get("error") else "completed",
            "result": result,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:
        _EVENT_JOBS[job_id].update({
            "status": "failed",
            "error": str(exc),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })
    finally:
        db.close()


@router.post("/rss/events/run")
def trigger_event_intelligence(
    background_tasks: BackgroundTasks,
    hours: int = Query(48, description="How far back to pull articles for clustering"),
    max_events: int = Query(15, le=50, description="Max event clusters to build/enrich per run"),
    min_sources: int = Query(1, description="Only run fact/contradiction/perspective enrichment on clusters with at least this many distinct sources (1 = enrich everything, including single-source stories)"),
    us_finance_only: bool = Query(True, description="Scope to US stock-market-relevant articles only (finance/macro/government categories, US/global sources, plus a stock-keyword content filter). Set false to widen to the full global RSS feed."),
):
    """
    Start the event-clustering + enrichment pipeline in the background and
    return a job_id immediately. Poll GET /market/rss/events/job/{job_id}.
    """
    job_id = str(uuid.uuid4())[:8]
    _EVENT_JOBS[job_id] = {
        "job_id": job_id, "status": "started",
        "hours": hours, "max_events": max_events, "min_sources": min_sources,
        "us_finance_only": us_finance_only,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "result": None, "error": None,
    }
    background_tasks.add_task(_run_event_intelligence_job, job_id, hours, max_events, min_sources, us_finance_only)
    return {"job_id": job_id, "status": "started"}


@router.get("/rss/events/job/{job_id}")
def event_intelligence_job_status(job_id: str):
    job = _EVENT_JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "Event intelligence job not found")
    out = {
        "job_id": job["job_id"], "status": job["status"],
        "started_at": job.get("started_at"), "completed_at": job.get("completed_at"),
        "error": job.get("error"),
    }
    if job.get("result"):
        out.update(job["result"])
    return out


@router.get("/rss/events")
def list_rss_events(
    limit: int = Query(30, le=100),
    entity: Optional[str] = None,
    min_sources: Optional[int] = None,
    us_finance_only: bool = Query(
        True,
        description="Scope to US stock-market-relevant events only. Re-checked against each event's "
                     "source articles at read time (not just at generation time), so older events "
                     "persisted before this filter existed (or generated with the global scope) are "
                     "hidden from the default view instead of lingering forever. Set false to see everything.",
    ),
    db: Session = Depends(get_db),
):
    """List clustered/enriched events, most recent first."""
    from app.connectors.event_clustering import event_is_us_finance_relevant
    from app.models.news_events import RssEvent
    try:
        Base.metadata.create_all(bind=db.get_bind())
        q = db.query(RssEvent)
        if entity:
            q = q.filter(RssEvent.topic_entity == entity)
        if min_sources:
            q = q.filter(RssEvent.source_count >= min_sources)
        # Over-fetch since the finance re-check below runs in Python — see
        # event_is_us_finance_relevant() docstring for why this is needed.
        rows = q.order_by(RssEvent.updated_at.desc()).limit(limit * 3 if us_finance_only else limit).all()
        if us_finance_only:
            rows = [r for r in rows if event_is_us_finance_relevant(r.article_ids or [])]
        rows = rows[:limit]
        return {"events": [_event_to_dict(r) for r in rows], "total": len(rows)}
    except Exception as e:
        return {"events": [], "total": 0, "error": str(e)}


@router.get("/rss/events/{event_id}")
def get_rss_event(event_id: int, db: Session = Depends(get_db)):
    from app.models.news_events import RssEvent
    row = db.query(RssEvent).filter(RssEvent.id == event_id).first()
    if not row:
        raise HTTPException(404, f"Event {event_id} not found")
    return _event_to_dict(row)


def _event_to_dict(row) -> dict:
    return {
        "id": row.id,
        "topic_entity": row.topic_entity,
        "headline": row.headline,
        "article_ids": row.article_ids or [],
        "sources": row.sources or [],
        "source_count": row.source_count,
        "confirmed_facts": row.confirmed_facts or [],
        "unconfirmed_claims": row.unconfirmed_claims or [],
        "conflicts": row.conflicts or [],
        "perspectives": row.perspectives or [],
        "key_quotes": row.key_quotes or [],
        "market_impact": row.market_impact,
        "enrichment_status": row.enrichment_status,
        "enrichment_error": row.enrichment_error,
        "created_at": str(row.created_at) if row.created_at else None,
        "updated_at": str(row.updated_at) if row.updated_at else None,
    }


# ── yfinance market data ──────────────────────────────────────────────────────

@router.get("/yf/snapshot")
def get_yf_snapshot(ticker: str):
    """Full yfinance snapshot: company + fundamentals + 1y price history."""
    from app.connectors.yfinance_connector import yf_snapshot
    return yf_snapshot(ticker)


@router.get("/yf/history")
def get_yf_history(ticker: str, period: str = "1y", interval: str = "1d"):
    """OHLCV price history. period: 1d 5d 1mo 3mo 6mo 1y 2y 5y max"""
    from app.connectors.yfinance_connector import yf_price_history
    return {"ticker": ticker, "period": period, "interval": interval,
            "bars": yf_price_history(ticker, period, interval)}


@router.get("/yf/fundamentals")
def get_yf_fundamentals(ticker: str):
    """Key fundamentals: P/E, P/B, margins, EPS, debt/equity, etc."""
    from app.connectors.yfinance_connector import yf_fundamentals
    return {"ticker": ticker, "fundamentals": yf_fundamentals(ticker)}


@router.get("/yf/company")
def get_yf_company(ticker: str):
    """Company profile: name, sector, industry, employees, website."""
    from app.connectors.yfinance_connector import yf_company_info
    return yf_company_info(ticker)


@router.get("/yf/dividends")
def get_yf_dividends(ticker: str):
    """Historical dividend payments."""
    from app.connectors.yfinance_connector import yf_dividends, yf_splits
    return {"ticker": ticker, "dividends": yf_dividends(ticker), "splits": yf_splits(ticker)}


@router.get("/yf/options")
def get_yf_options(ticker: str):
    """Nearest-expiry options chain (calls + puts)."""
    from app.connectors.yfinance_connector import yf_options
    return {"ticker": ticker, **yf_options(ticker)}


@router.get("/yf/holders")
def get_yf_holders(ticker: str):
    """Top institutional holders."""
    from app.connectors.yfinance_connector import yf_institutional_holders
    return {"ticker": ticker, "holders": yf_institutional_holders(ticker)}


# ── Technical Indicators (pure-Python, no TA-Lib dependency) ─────────────────

@router.get("/technicals")
def get_technicals(ticker: str, period: str = "1y"):
    """
    Technical analysis: SMA, EMA, RSI, MACD, Bollinger Bands, ATR, OBV.
    Computed from yfinance OHLCV data using pure Python (no TA-Lib required).
    """
    from app.connectors.technicals_connector import compute_technicals
    return compute_technicals(ticker, period)


# ── Multi-Agent Intelligence ──────────────────────────────────────────────────

@router.get("/intelligence/report")
def get_intelligence_report(ticker: str, company: str = ""):
    """
    Full multi-agent investment intelligence report.
    Runs 4 specialist agents in parallel: Fundamentals, Technical, Sentiment, Risk.
    Returns composite score (0-100), recommendation (BUY/HOLD/SELL), and thesis.
    """
    from app.connectors.multi_agent_intelligence import run_investment_intelligence
    return run_investment_intelligence(ticker, company)


@router.get("/intelligence/fundamentals")
def get_fundamentals_agent(ticker: str):
    """Fundamentals agent only: valuation ratios, margins, revenue trend."""
    from app.connectors.multi_agent_intelligence import fundamentals_agent
    return fundamentals_agent(ticker)


@router.get("/intelligence/technical")
def get_technical_agent(ticker: str):
    """Technical agent only: trend, momentum, support/resistance."""
    from app.connectors.multi_agent_intelligence import technical_agent
    return technical_agent(ticker)


@router.get("/intelligence/risk")
def get_risk_agent(ticker: str):
    """Risk agent: Beneish M-score, Altman Z-score, debt, beta, short interest."""
    from app.connectors.multi_agent_intelligence import risk_agent
    return risk_agent(ticker)


# ── OSINT Intelligence ────────────────────────────────────────────────────────

@router.get("/osint/username")
def osint_username(username: str):
    """
    Enumerate username across 40+ platforms (Sherlock/Maigret-style).
    Returns list of platforms where the account exists.
    """
    from app.connectors.osint_connector import enumerate_username
    return enumerate_username(username)


@router.get("/osint/domain")
def osint_domain(domain: str):
    """Domain intelligence: A/MX/TXT DNS records + RDAP WHOIS."""
    from app.connectors.osint_connector import domain_intelligence
    return domain_intelligence(domain)


@router.get("/osint/email-patterns")
def osint_email_patterns(first_name: str, last_name: str, domain: str):
    """Generate likely email addresses for a person at a company domain."""
    from app.connectors.osint_connector import discover_email_patterns
    return {"patterns": discover_email_patterns(first_name, last_name, domain)}


@router.get("/osint/linkedin")
def osint_linkedin(person: str, company: str = ""):
    """Find likely LinkedIn profile URLs via DuckDuckGo search."""
    from app.connectors.osint_connector import linkedin_search_signals
    return linkedin_search_signals(person, company)


@router.get("/osint/person")
def osint_person_report(name: str, username: str = "", email: str = "", company: str = "", domain: str = ""):
    """Full person OSINT report: username enum + LinkedIn + domain + breach check."""
    from app.connectors.osint_connector import person_osint_report
    return person_osint_report(
        name,
        username=username or None,
        email=email or None,
        company=company or None,
        domain=domain or None,
    )


@router.get("/osint/company")
def osint_company_report(company: str, domain: str = ""):
    """Company OSINT report: domain intel + UK Companies House + LinkedIn + Crawl4AI web intel."""
    from app.connectors.osint_connector import company_osint_report
    report = company_osint_report(company, domain=domain or None)

    # Crawl4AI: crawl the company's own site (about/leadership/investors) for
    # free, self-hosted web intel — additive, replaces nothing here (F-07)
    if domain:
        try:
            from app.connectors.crawl4ai_connector import crawl_company_intel
            report["web_intel"] = crawl_company_intel(domain)
        except Exception:
            report["web_intel"] = {}

    return report


# ══════════════════════════════════════════════════════════════════════════════
# CRYPTO INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/crypto/dashboard")
def crypto_dashboard():
    """Global crypto market dashboard: prices, trending, whale alerts."""
    from app.connectors.crypto_connector import crypto_dashboard
    return crypto_dashboard()


@router.get("/crypto/prices")
def crypto_prices(coins: str = ""):
    """Current prices for top cryptocurrencies."""
    from app.connectors.crypto_connector import get_crypto_prices
    coin_list = [c.strip() for c in coins.split(",") if c.strip()] if coins else None
    return get_crypto_prices(coin_list)


@router.get("/crypto/coin/{coin_id}")
def crypto_coin_detail(coin_id: str):
    """Detailed profile for a specific coin (use CoinGecko id e.g. bitcoin, ethereum)."""
    from app.connectors.crypto_connector import get_coin_detail
    return get_coin_detail(coin_id)


@router.get("/crypto/trending")
def crypto_trending():
    """Top trending cryptocurrencies (most searched in 24h)."""
    from app.connectors.crypto_connector import get_trending_cryptos
    return {"trending": get_trending_cryptos()}


@router.get("/crypto/global")
def crypto_global_market():
    """Global crypto market statistics and dominance."""
    from app.connectors.crypto_connector import get_global_market, get_defi_overview
    return {"market": get_global_market(), "defi": get_defi_overview()}


@router.get("/crypto/whales")
def crypto_whale_alerts(min_usd: float = 500_000_000, limit: int = 20):
    """Large-cap cryptocurrency movement / whale alerts."""
    from app.connectors.crypto_connector import get_whale_alerts
    return {"alerts": get_whale_alerts(min_usd=min_usd, limit=limit)}


@router.get("/crypto/wallet/eth/{address}")
def eth_wallet_profile(address: str):
    """Ethereum wallet profile: balance, tokens, recent transactions."""
    from app.connectors.crypto_connector import get_eth_wallet
    return get_eth_wallet(address)


@router.get("/crypto/wallet/btc/{address}")
def btc_wallet_profile(address: str):
    """Bitcoin wallet profile: balance, total received/sent, recent transactions."""
    from app.connectors.crypto_connector import get_btc_wallet
    return get_btc_wallet(address)


@router.get("/crypto/flow/{coin_id}")
def crypto_token_flow(coin_id: str):
    """Exchange inflow/outflow signal for a coin."""
    from app.connectors.crypto_connector import get_token_flow
    return get_token_flow(coin_id)


# ══════════════════════════════════════════════════════════════════════════════
# GOVERNMENT TRADING INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/gov-trading/summary")
def gov_trading_summary_route(days: int = 90):
    """Full government trading intelligence: congress trades, top tickers, active members."""
    from app.connectors.gov_trading_connector import gov_trading_summary
    return gov_trading_summary(days=days)


@router.get("/gov-trading/recent")
def gov_trading_recent(days: int = 30, limit: int = 50):
    """Recent congressional stock trades (House + Senate)."""
    from app.connectors.gov_trading_connector import get_recent_congress_trades
    trades = get_recent_congress_trades(days=days, limit=limit)
    return {"trades": trades, "count": len(trades), "period_days": days}


@router.get("/gov-trading/ticker/{ticker}")
def gov_trading_by_ticker(ticker: str, days: int = 365):
    """All congressional trades for a specific stock."""
    import math
    from app.connectors.gov_trading_connector import get_trades_by_ticker

    def _clean_nan(obj):
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        if isinstance(obj, dict):
            return {k: _clean_nan(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [_clean_nan(v) for v in obj]
        return obj

    trades = _clean_nan(get_trades_by_ticker(ticker, days=days))
    return {"ticker": ticker.upper(), "trades": trades, "count": len(trades)}


@router.get("/gov-trading/member")
def gov_trading_by_member(name: str, chamber: str = "auto"):
    """
    All trades by a congressional member.
    chamber: 'house' | 'senate' | 'auto' (default — checks both, returns whichever has data)
    """
    from app.connectors.gov_trading_connector import (
        get_trades_by_member, get_senate_trades_by_member
    )
    ch = chamber.lower()
    if ch == "senate":
        trades = get_senate_trades_by_member(name)
    elif ch == "house":
        trades = get_trades_by_member(name)
    else:  # auto
        house_trades = get_trades_by_member(name)
        senate_trades = get_senate_trades_by_member(name)
        trades = senate_trades if senate_trades else house_trades
        ch = "senate" if senate_trades else "house"
    return {"name": name, "chamber": ch, "trades": trades, "count": len(trades)}


@router.get("/gov-trading/senate/member")
def gov_trading_senate_member(name: str):
    """All Senate eFD PTR trades for a named senator (via senate-stock-watcher)."""
    from app.connectors.gov_trading_connector import get_senate_trades_by_member
    trades = get_senate_trades_by_member(name)
    return {"name": name, "chamber": "senate", "trades": trades, "count": len(trades)}


@router.get("/gov-trading/top-tickers")
def gov_trading_top_tickers(days: int = 90, top_n: int = 20):
    """Most-traded tickers in Congress with buy/sell sentiment."""
    from app.connectors.gov_trading_connector import get_most_traded_tickers
    return {"period_days": days, "tickers": get_most_traded_tickers(days=days, top_n=top_n)}


@router.get("/gov-trading/most-active")
def gov_trading_most_active(days: int = 90, top_n: int = 20):
    """Most active congressional traders."""
    from app.connectors.gov_trading_connector import get_most_active_members
    return {"period_days": days, "members": get_most_active_members(days=days, top_n=top_n)}


@router.get("/gov-trading/filtered")
def gov_trading_filtered(
    days: int = 90,
    ticker: Optional[str] = None,
    company: Optional[str] = None,
    trend: Optional[str] = None,
    chamber: Optional[str] = None,
    limit: int = 100,
):
    """
    Filter congressional trades by company (ticker or name substring) and/or
    trend (buy/sell) — James ask, Task 2.3 "filter by company/trend".
    """
    from app.connectors.gov_trading_connector import get_congress_trades_filtered
    trades = get_congress_trades_filtered(
        days=days, ticker=ticker, company=company, trend=trend, chamber=chamber, limit=limit,
    )
    return {"trades": trades, "count": len(trades), "filters": {
        "days": days, "ticker": ticker, "company": company, "trend": trend, "chamber": chamber,
    }}


@router.get("/gov-trading/whale-tracker")
def gov_trading_whale_tracker(days: int = 90, min_amount: float = 50_000, limit: int = 50):
    """
    Largest disclosed congressional trades in the window — James ask,
    Task 2.3 "whale tracker". Ranked by the top of the STOCK Act disclosure
    amount bucket (exact dollar figures aren't required by law).
    """
    from app.connectors.gov_trading_connector import get_whale_trades
    whales = get_whale_trades(days=days, min_amount=min_amount, limit=limit)
    return {"whales": whales, "count": len(whales), "min_amount": min_amount, "period_days": days}


@router.get("/gov-trading/trending-tickers")
def gov_trading_trending_tickers(days: int = 30, top_n: int = 15):
    """Tickers with the most congressional trading activity recently, with buy/sell sentiment."""
    from app.connectors.gov_trading_connector import get_trending_tickers
    return {"period_days": days, "tickers": get_trending_tickers(days=days, top_n=top_n)}


@router.get("/gov-trading/reddit-buzz")
def gov_trading_reddit_buzz(query: str, limit: int = 25):
    """
    Retail Reddit chatter about a politician's name or a ticker they've
    traded — James ask, Task 2.3 "Reddit tracker". Needs REDDIT_CLIENT_ID/
    REDDIT_CLIENT_SECRET in .env; degrades gracefully (available=False) if unset.
    """
    from app.connectors.gov_trading_connector import get_reddit_buzz
    return get_reddit_buzz(query=query, limit=limit)


# ══════════════════════════════════════════════════════════════════════════════
# DEEP COMPANY INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/company/info/{ticker}")
def company_info(ticker: str):
    """Company information from SEC EDGAR."""
    from app.connectors.company_deep_connector import get_company_info
    return get_company_info(ticker.upper())


@router.get("/company/filings/{ticker}")
def company_filings(ticker: str, forms: str = "10-K,10-Q,8-K", limit: int = 10):
    """Recent SEC filings (10-K, 10-Q, 8-K, etc.)."""
    from app.connectors.company_deep_connector import get_recent_filings
    form_list = [f.strip() for f in forms.split(",") if f.strip()]
    return {"ticker": ticker.upper(), "filings": get_recent_filings(ticker.upper(), form_list, limit)}


@router.get("/company/financials/{ticker}")
def company_quarterly_financials(ticker: str):
    """Quarterly financial metrics from SEC EDGAR XBRL (revenue, EPS, net income, etc.)."""
    from app.connectors.company_deep_connector import get_quarterly_financials
    return get_quarterly_financials(ticker.upper())


@router.get("/company/cap-table/{ticker}")
def company_cap_table(ticker: str):
    """Cap table: major shareholders, institutional + mutual fund holders, ownership %."""
    from app.connectors.company_deep_connector import get_cap_table
    return get_cap_table(ticker.upper())


@router.get("/company/insider-trades/{ticker}")
def company_insider_trades(ticker: str, limit: int = 30):
    """Recent insider transactions (Form 4 disclosures) via yfinance."""
    from app.connectors.company_deep_connector import get_insider_trades
    trades = get_insider_trades(ticker.upper(), limit=limit)
    return {"ticker": ticker.upper(), "trades": trades, "count": len(trades)}


@router.get("/company/big-trades/{ticker}")
def company_big_institutional_trades(ticker: str):
    """Significant institutional positions ($100M+) and 13F signals."""
    from app.connectors.company_deep_connector import get_institutional_big_trades
    return get_institutional_big_trades(ticker.upper())


@router.get("/company/analyst-ratings/{ticker}")
def company_analyst_ratings(ticker: str):
    """Analyst consensus, price targets, upgrade/downgrade history, earnings estimates."""
    from app.connectors.company_deep_connector import get_analyst_ratings
    return get_analyst_ratings(ticker.upper())


@router.get("/company/earnings/{ticker}")
def company_earnings_history(ticker: str):
    """Earnings history (actual vs estimate, EPS surprise) and next earnings date."""
    from app.connectors.company_deep_connector import get_earnings_history
    return get_earnings_history(ticker.upper())


@router.get("/company/deep-report/{ticker}")
def company_deep_report(ticker: str, company: str = ""):
    """
    Full deep-dive company report: SEC filings, quarterly financials,
    cap table, insider trades, analyst ratings, earnings, and news.
    """
    from app.connectors.company_deep_connector import deep_company_report
    return deep_company_report(ticker.upper(), company_name=company)


# ─── Government Contracts (USASpending) ───────────────────────────────────────

def _normalize_company_name(name: str) -> str:
    """Normalize company name for matching."""
    import re
    # Remove common suffixes and normalize
    name = name.upper().strip()
    for suffix in [", INC.", ", INC", " INC.", " INC", ", LLC", " LLC", ", LP", " LP",
                   ", CORP.", ", CORP", " CORP.", " CORP", " CORPORATION", ", LTD", " LTD",
                   " COMPANY", " CO.", " CO"]:
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip()
    # Remove extra whitespace
    name = re.sub(r'\s+', ' ', name)
    return name


def _name_matches(query: str, recipient: str, strict: bool = True) -> bool:
    """
    Check if recipient name matches the query.
    For strict=True: recipient must be essentially the same company (exact or with suffix variations).
    For strict=False: query must be a significant part of recipient name.
    """
    q_norm = _normalize_company_name(query)
    r_norm = _normalize_company_name(recipient)

    # Exact match after normalization
    if q_norm == r_norm:
        return True

    if strict:
        # In strict mode, one name should be a subset of the other
        # e.g., "LOCKHEED MARTIN" matches "LOCKHEED MARTIN CORPORATION"
        # but "APPLE" should NOT match "APPLE CONSTRUCTION" or "BIG APPLE"

        # Query contains full recipient name (e.g., "LOCKHEED MARTIN CORP" vs "LOCKHEED MARTIN")
        if q_norm in r_norm and len(q_norm) >= len(r_norm) * 0.7:
            return True
        # Recipient contains full query name
        if r_norm in q_norm and len(r_norm) >= len(q_norm) * 0.7:
            return True

        # Check if they share the same primary company name (first 2+ significant words)
        q_words = q_norm.split()
        r_words = r_norm.split()

        # Need at least 2 matching words at the start for short company names
        min_words = min(2, len(q_words), len(r_words))
        if min_words >= 2 and q_words[:min_words] == r_words[:min_words]:
            return True

        # For single-word queries, require exact match only
        return False

    # For non-strict: check if query is a significant standalone word
    import re
    words = re.findall(r'\b' + re.escape(q_norm) + r'\b', r_norm)
    return len(words) > 0


@router.get("/company/contracts/{entity_name}")
def company_contracts(entity_name: str, ticker: str = "", limit: int = 30, strict: bool = True):
    """
    Fetch government contracts from USASpending for a company.

    Args:
        entity_name: Company name to search
        ticker: Optional stock ticker to look up exact legal name
        limit: Max results to return
        strict: If True, only return exact matches (default). If False, return partial matches.

    Returns contracts where the company is a RECIPIENT of government funds.
    """
    import requests as req

    # Try to get exact legal name for public companies via ticker
    search_names = []
    legal_name = None

    if ticker:
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker.upper())
            info = stock.info
            legal_name = info.get("longName") or info.get("shortName")
            if legal_name:
                search_names.append(legal_name)
        except Exception:
            pass

    # Add the provided entity name
    if entity_name and entity_name not in search_names:
        search_names.append(entity_name)

    result = {
        "entity_name": entity_name,
        "legal_name": legal_name,
        "search_names": search_names,
        "as_recipient": [],
        "total_received": 0,
        "top_agencies": [],
        "match_mode": "strict" if strict else "partial",
    }

    try:
        # Search USASpending for contracts
        # Use exact phrase search by searching each name
        all_results = []
        seen_awards = set()

        for search_name in search_names:
            payload = {
                "filters": {
                    "recipient_search_text": [search_name],  # Regular search, filter strictly after
                    "award_type_codes": ["A", "B", "C", "D"],  # Contracts only
                },
                "fields": ["Award ID", "Recipient Name", "Award Amount", "Awarding Agency",
                           "Award Type", "Start Date", "End Date", "Description"],
                "page": 1, "limit": 100, "sort": "Award Amount", "order": "desc"
            }
            resp = req.post("https://api.usaspending.gov/api/v2/search/spending_by_award/",
                            json=payload, timeout=25)
            if resp.ok:
                for a in resp.json().get("results", []):
                    award_id = a.get("Award ID")
                    if award_id in seen_awards:
                        continue
                    seen_awards.add(award_id)

                    recipient = a.get("Recipient Name") or ""

                    # Filter: only include if recipient name actually matches
                    matches = False
                    for name in search_names:
                        if _name_matches(name, recipient, strict=strict):
                            matches = True
                            break

                    if not matches:
                        continue

                    amt = float(a.get("Award Amount") or 0)
                    all_results.append({
                        "award_id": award_id,
                        "recipient": recipient,
                        "amount": amt,
                        "agency": a.get("Awarding Agency") or "Unknown Agency",
                        "type": a.get("Award Type"),
                        "start_date": a.get("Start Date"),
                        "end_date": a.get("End Date"),
                        "description": (a.get("Description") or "")[:200],
                    })

        # Sort by amount and take top results
        all_results.sort(key=lambda x: x["amount"], reverse=True)
        result["as_recipient"] = all_results[:limit]
        result["total_received"] = sum(r["amount"] for r in all_results)

        # Calculate top agencies
        agency_counts = {}
        for r in all_results:
            agency = r["agency"]
            agency_counts[agency] = agency_counts.get(agency, 0) + r["amount"]
        result["top_agencies"] = sorted(agency_counts.items(), key=lambda x: -x[1])[:5]

        result["total_matches"] = len(all_results)

    except Exception as e:
        result["error"] = str(e)

    return result


@router.get("/company/funding/{entity_name}")
def company_funding(entity_name: str, ticker: str = ""):
    """
    Fetch funding/capital raised data for a company.
    Uses FundedAPI (free) + SEC Form D filings.
    """
    import requests as req

    # Build search names (like contracts endpoint)
    search_names = []
    legal_name = None
    if ticker:
        try:
            import yfinance as yf
            stock = yf.Ticker(ticker.upper())
            info = stock.info
            legal_name = info.get("longName") or info.get("shortName")
            if legal_name:
                search_names.append(legal_name)
        except Exception:
            pass
    if entity_name and entity_name not in search_names:
        search_names.append(entity_name)

    result = {
        "entity_name": entity_name,
        "legal_name": legal_name,
        "search_names": search_names,
        "funding_rounds": [],
        "total_raised": 0,
        "investors": [],
        "sec_form_d_filings": [],
    }

    # 1. FundedAPI (free startup funding data)
    try:
        resp = req.get(
            "https://fundedapi.com/v1/startups",
            params={"q": entity_name, "limit": 10},
            timeout=12)
        if resp.ok:
            data = resp.json()
            startups = data.get("startups", data.get("data", []))
            for s in startups:
                name = s.get("name", "")
                # Use strict matching
                matches = any(_name_matches(sn, name, strict=True) for sn in search_names)
                if matches:
                    round_info = {
                        "company": name,
                        "round": s.get("fundingRound") or s.get("round"),
                        "amount": float(s.get("fundingAmount") or 0),
                        "investors": s.get("investors", []),
                        "date": (s.get("scrapedAt") or "")[:10],
                    }
                    result["funding_rounds"].append(round_info)
                    result["total_raised"] += round_info["amount"]
                    result["investors"].extend(s.get("investors", []))
    except Exception:
        pass

    # 2. SEC Form D filings (private placements) - use legal name if available
    search_term = legal_name or entity_name
    try:
        headers = {"User-Agent": "FinancePlatform research@example.com"}
        resp = req.get(
            "https://efts.sec.gov/LATEST/search-index",
            headers=headers,
            params={
                "q": f'"{search_term}"',
                "forms": "D",
                "dateRange": "custom",
                "startdt": "2015-01-01",
                "enddt": "2030-01-01",
            },
            timeout=15)
        if resp.ok:
            hits = resp.json().get("hits", {}).get("hits", [])
            for h in hits[:20]:
                src = h.get("_source", {})
                display = src.get("display_names", [""])[0]
                # Filter: only include if issuer name matches
                matches = any(_name_matches(sn, display, strict=True) for sn in search_names)
                if matches:
                    result["sec_form_d_filings"].append({
                        "issuer": display,
                        "filed_date": src.get("file_date"),
                        "form": src.get("form", "Form D"),
                        "description": src.get("file_description", ""),
                    })
    except Exception:
        pass

    # Dedupe investors
    result["investors"] = list(set(result["investors"]))[:15]

    return result


@router.get("/company/private-intel/{entity_name}")
def company_private_intel(entity_name: str, jurisdiction: str = "", domain: str = ""):
    """
    Full private company intelligence: OpenCorporates + GLEIF + FinCEN + FDIC.
    Includes contracts, funding, and corporate registration data.
    If `domain` is provided, also crawls the company's public site (about,
    leadership, investors, news pages) via Crawl4AI for free web intel (F-07) —
    replaces the Apify website-content-crawler actor for this use case.
    """
    from app.connectors.private_company_connector import fetch_private_company_intel

    # Get private company data
    private_data = fetch_private_company_intel(entity_name, jurisdiction=jurisdiction)

    # Add contracts and funding
    contracts = company_contracts(entity_name, limit=10)
    funding = company_funding(entity_name)

    web_intel = {}
    if domain:
        try:
            from app.connectors.crawl4ai_connector import crawl_company_intel
            web_intel = crawl_company_intel(domain)
        except Exception:
            web_intel = {}

    return {
        "entity_name": entity_name,
        "registration": private_data,
        "contracts": contracts,
        "funding": funding,
        "web_intel": web_intel,
    }


# ─── Valuation Routes ─────────────────────────────────────────────────────────

@router.get("/company/dcf-valuation/{ticker}")
def company_dcf_valuation(ticker: str):
    """
    DCF intrinsic valuation: 5-year FCF projection, WACC (CAPM),
    terminal value, bull/base/bear scenarios, vs current market price.
    """
    from app.connectors.valuation_connector import build_dcf_valuation
    return build_dcf_valuation(ticker.upper())


@router.get("/company/filing-analysis/{ticker}")
def company_filing_analysis(ticker: str):
    """
    Parse 10-K/10-Q text for MD&A, forward guidance, risk factors,
    and key metrics extracted from management's narrative.
    """
    from app.connectors.valuation_connector import get_filing_analysis
    return get_filing_analysis(ticker.upper())


@router.get("/company/full-valuation/{ticker}")
def company_full_valuation(ticker: str):
    """
    Complete valuation report: DCF model + SEC filing text analysis + synthesis.
    Bull/bear/base scenarios with intrinsic value vs market price.
    """
    from app.connectors.valuation_connector import full_valuation_report
    return full_valuation_report(ticker.upper())


# ─── Expert Analysis Routes ───────────────────────────────────────────────────

@router.get("/company/expert-analysis/{ticker}")
def company_expert_analysis(ticker: str, company: str = ""):
    """
    Expert analysis aggregator: analyst upgrade/downgrade timeline,
    news sentiment over time, key themes, bullish/bearish article split.
    """
    from app.connectors.expert_analysis_connector import expert_analysis_report
    return expert_analysis_report(ticker.upper(), company_name=company)


@router.get("/company/analyst-timeline/{ticker}")
def company_analyst_timeline(ticker: str, months: int = 12):
    """Analyst upgrade/downgrade history with sentiment classification."""
    from app.connectors.expert_analysis_connector import get_analyst_timeline
    events = get_analyst_timeline(ticker.upper(), months=months)
    return {"ticker": ticker.upper(), "events": events, "count": len(events)}


# ─── Institutional (13F) Routes ───────────────────────────────────────────────

@router.get("/company/institutional-changes/{ticker}")
def company_institutional_changes(ticker: str):
    """
    Institutional position analysis: mega/large holders, mutual funds,
    13F filers, notable institution positions, ownership summary.
    """
    from app.connectors.institutional_tracker import get_institutional_13f_changes
    return get_institutional_13f_changes(ticker.upper())


@router.get("/institution/holdings/{name}")
def institution_holdings(name: str):
    """
    Top holdings for a named institution (e.g. 'Berkshire Hathaway', 'BlackRock')
    parsed directly from their latest SEC 13F-HR filing.
    """
    from app.connectors.institutional_tracker import get_top_institution_holdings
    return get_top_institution_holdings(name)


@router.get("/institution/list")
def institution_list():
    """List of tracked institutions with their CIK numbers."""
    from app.connectors.institutional_tracker import TOP_INSTITUTIONS
    return {"institutions": [{"name": k, "cik": v} for k, v in TOP_INSTITUTIONS.items()]}


# ─── Government Figure Trading Routes ─────────────────────────────────────────

@router.get("/gov-trading/politician/{politician_id}")
def gov_politician_profile(politician_id: str):
    """
    Full trading profile for a named politician: PTR filings, sponsored legislation,
    cross-reference between trading activity and legislative agenda.
    """
    from app.connectors.gov_trading_connector import get_politician_profile
    return get_politician_profile(politician_id)


@router.get("/gov-trading/politicians/summary")
def gov_politicians_summary():
    """Trading activity summary for all tracked politicians (PTR count, latest filing)."""
    from app.connectors.gov_trading_connector import get_all_politicians_summary
    return {"politicians": get_all_politicians_summary()}


@router.get("/gov-trading/politicians/list")
def gov_politicians_list():
    """List of tracked politicians."""
    from app.connectors.gov_trading_connector import TRACKED_POLITICIANS
    return {"politicians": [{"id": k, **v} for k, v in TRACKED_POLITICIANS.items()]}


@router.get("/institutional/position-diff", response_model=PositionDiffResponse)
def get_institutional_position_diff_api(
    institution_cik: str = Query(..., description="10-digit SEC CIK, digits accepted with or without leading zeroes."),
    current_period: date | None = Query(None, description="Quarter-end date, e.g. 2026-03-31."),
    previous_period: date | None = Query(None, description="Earlier quarter-end date, e.g. 2025-12-31."),
    status: PositionDiffFilterStatus = Query(PositionDiffFilterStatus.CHANGED),
    ticker: str | None = Query(None),
    cusip: str | None = Query(None),
    sort_by: PositionDiffSortField = Query(PositionDiffSortField.REPORTED_VALUE_DIFF_USD),
    sort_dir: SortDirection = Query(SortDirection.DESC),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    Base.metadata.create_all(bind=db.get_bind())
    try:
        request = PositionDiffRequest(
            institution_cik=institution_cik,
            current_period=current_period,
            previous_period=previous_period,
            status=status,
            ticker=ticker,
            cusip=cusip,
            sort_by=sort_by,
            sort_dir=sort_dir,
            limit=limit,
            offset=offset,
        )
        return get_institutional_position_diff(db, request)
    except requests.RequestException:
        raise HTTPException(status_code=503, detail="SEC unavailable and no usable cache.")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Database error.")
    except ET.ParseError:
        raise HTTPException(status_code=502, detail="Malformed SEC filing.")
    except PositionAmbiguityError:
        raise HTTPException(status_code=409, detail="Unsupported comparison or ambiguous filing data.")
    except ValueError as exc:
        message = str(exc)
        if "No 13F" in message or "not available in SEC submissions" in message:
            raise HTTPException(status_code=404, detail=message)
        if "XML" in message or "filing archive" in message or "amendmentType" in message:
            raise HTTPException(status_code=502, detail=message)
        raise HTTPException(status_code=422, detail=message)
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error.")


# ─── F-05: Congress.gov Full Legislation Routes ───────────────────────────────
# See docs/api/CONGRESS_GOV_LEGISLATION_UPGRADE.md and
# docs/api/CONGRESS_GOV_IMPLEMENTATION_PLAN_WITH_GAP_FIXES.md for the full proposal.

@router.get("/gov-trading/legislation/search")
def gov_legislation_search(
    query: str,
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    limit: int = 20,
):
    """Free-text bill search — e.g. 'AI regulation', 'banking', 'crypto'. 20-min cached."""
    from app.connectors.gov_trading_connector import search_bills
    return {"query": query, "bills": search_bills(query, from_date=from_date, to_date=to_date, limit=limit)}


@router.get("/gov-trading/legislation/bill/{congress}/{bill_type}/{bill_number}")
def gov_legislation_bill_detail(congress: int, bill_type: str, bill_number: int):
    """
    Full bill detail — sponsors, latest action, cosponsor/summary counts, text link.

    Graceful-degrade to 200 with an {"error": ...} payload when the bill isn't
    found, rather than raising 404 — matches the connector's own no-raise
    contract (get_bill_details() never throws, only returns None) and the
    frontend's existing billDetail?.error handling in gov-trading.js.
    (Task 2.1 — resolves the 404-vs-200 mismatch flagged in the lead review.)
    """
    from app.connectors.gov_trading_connector import get_bill_details
    bill = get_bill_details(congress, bill_type, bill_number)
    if not bill:
        return {"error": f"Bill {bill_type.upper()} {bill_number} not found in congress {congress}"}
    return bill


@router.get("/gov-trading/legislation/bill/{congress}/{bill_type}/{bill_number}/text")
def gov_legislation_bill_text(congress: int, bill_type: str, bill_number: int):
    """Bill text version links (XML/PDF/HTML) — full text is external, not inline."""
    from app.connectors.gov_trading_connector import get_bill_text
    return {"versions": get_bill_text(congress, bill_type, bill_number)}


@router.get("/gov-trading/legislation/bill/{congress}/{bill_type}/{bill_number}/cosponsors")
def gov_legislation_bill_cosponsors(congress: int, bill_type: str, bill_number: int, limit: int = 20):
    """Members who co-signed a bill."""
    from app.connectors.gov_trading_connector import get_bill_cosponsors
    return {"cosponsors": get_bill_cosponsors(congress, bill_type, bill_number, limit=limit)}


@router.get("/gov-trading/legislation/laws/{congress}")
def gov_legislation_recent_laws(congress: int, limit: int = 20):
    """Bills that became actual laws in a given congress (e.g. 118)."""
    from app.connectors.gov_trading_connector import get_recent_laws
    return {"congress": congress, "laws": get_recent_laws(congress, limit=limit)}


@router.get("/gov-trading/legislation/committee/{chamber}/{committee_code}")
def gov_legislation_committee_bills(chamber: str, committee_code: str, limit: int = 20):
    """All bills assigned to a committee (e.g. chamber='senate', code='ssba' = Banking)."""
    from app.connectors.gov_trading_connector import get_committee_bills
    return {"chamber": chamber, "committee": committee_code, "bills": get_committee_bills(chamber, committee_code, limit=limit)}


@router.get("/gov-trading/legislation/crs-reports")
def gov_legislation_crs_reports(limit: int = 20):
    """Congressional Research Service non-partisan policy analysis reports."""
    from app.connectors.gov_trading_connector import get_crs_reports
    return {"reports": get_crs_reports(limit=limit)}


@router.get("/gov-trading/legislation/committee-codes")
def gov_legislation_committee_codes():
    """Return the known-good committee system codes to use with the committee bills endpoint."""
    from app.connectors.gov_trading_connector import COMMITTEE_CODES
    return {"committee_codes": COMMITTEE_CODES, "note": "Pass the value (e.g. 'ssbk00') as committee_code to /committee/{chamber}/{committee_code}"}


@router.get("/gov-trading/politician/{politician_id}/votes")
def gov_politician_votes(politician_id: str, limit: int = 20):
    """
    Sponsored + cosponsored legislation for a tracked politician, tagged by role.
    (Congress.gov v3 does not expose per-member roll-call vote positions directly —
    see 'What Congress.gov API Can NOT Do' in the feature proposal.)
    """
    from app.connectors.gov_trading_connector import TRACKED_POLITICIANS, get_bioguide_id, get_member_votes
    info = TRACKED_POLITICIANS.get(politician_id.lower().replace(" ", "_"))
    if not info:
        for pid, pinfo in TRACKED_POLITICIANS.items():
            if politician_id.lower() in pinfo["name"].lower():
                info = pinfo
                break
    if not info:
        return {"error": f"Politician '{politician_id}' not found", "available": list(TRACKED_POLITICIANS.keys())}

    bioguide_id = get_bioguide_id(info["name"])
    if not bioguide_id:
        return {"politician": info["name"], "votes": [], "note": "Could not resolve bioguideId for this member"}

    return {"politician": info["name"], "bioguide_id": bioguide_id, "votes": get_member_votes(bioguide_id, limit=limit)}
