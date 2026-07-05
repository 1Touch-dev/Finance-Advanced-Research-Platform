"""
API routes for financial data, news aggregation, and international registry lookups.
All endpoints are free-tier and gracefully degrade when keys are missing.
"""
import os
from fastapi import APIRouter, Query
from typing import Optional
from app.connectors.financial_news_connector import (
    finnhub_quote, finnhub_company_profile, finnhub_financials,
    finnhub_insider_transactions, fmp_income_statement, fmp_balance_sheet,
    fmp_cash_flow, fmp_key_metrics, compute_beneish_mscore, compute_altman_zscore,
    fred_macro_data, aggregate_news, newsapi_search, guardian_search,
    nyt_search, gdelt_search, ukch_search, ukch_officers, icij_search, aleph_search,
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


@router.get("/rss/sources")
def get_rss_sources():
    """List all 50 registered RSS sources with status."""
    from sqlalchemy import text
    engine = _get_rss_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT id, name, url, category, region, active, last_polled, article_count, error_count
            FROM rss_sources ORDER BY category, name
        """)).mappings().all()
    return {"sources": [dict(r) for r in rows]}


@router.get("/rss/articles")
def get_rss_articles(
    category: Optional[str] = None,
    region: Optional[str] = None,
    entity: Optional[str] = None,
    limit: int = Query(40, le=200),
    offset: int = 0,
):
    """
    Fetch RSS articles with optional filters.
    - category: finance | macro | news | tech | crypto | government | policy
    - region: us | global | europe | asia | india | mena | latam
    - entity: match against matched_entities array (e.g. 'Apple', 'Tesla')
    """
    from sqlalchemy import text
    engine = _get_rss_engine()
    filters = []
    params: dict = {"limit": limit, "offset": offset}
    if category:
        filters.append("category = :category")
        params["category"] = category
    if region:
        filters.append("region = :region")
        params["region"] = region
    if entity:
        filters.append(":entity = ANY(matched_entities)")
        params["entity"] = entity
    where = ("WHERE " + " AND ".join(filters)) if filters else ""
    with engine.connect() as conn:
        rows = conn.execute(text(f"""
            SELECT id, source_name, title, url, summary, published_at,
                   category, region, matched_entities, sentiment_label
            FROM rss_articles
            {where}
            ORDER BY published_at DESC NULLS LAST
            LIMIT :limit OFFSET :offset
        """), params).mappings().all()
        total = conn.execute(text(f"SELECT COUNT(*) FROM rss_articles {where}"), params).scalar()
    return {"total": total, "articles": [dict(r) for r in rows]}


@router.get("/rss/entity-feed")
def get_entity_rss_feed(entity: str, limit: int = 20):
    """Articles that mention a specific entity by name (auto-matched on ingest)."""
    from sqlalchemy import text
    engine = _get_rss_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT source_name, title, url, summary, published_at, category, region
            FROM rss_articles
            WHERE :entity = ANY(matched_entities)
            ORDER BY published_at DESC NULLS LAST
            LIMIT :limit
        """), {"entity": entity, "limit": limit}).mappings().all()
    return {"entity": entity, "articles": [dict(r) for r in rows]}


@router.get("/rss/digest")
def get_rss_digest(hours: int = 24):
    """
    Top news digest: latest unique articles per category for the last N hours.
    Grouped by category for a quick intelligence overview.
    """
    from sqlalchemy import text
    engine = _get_rss_engine()
    with engine.connect() as conn:
        rows = conn.execute(text("""
            SELECT category, source_name, title, url, summary, published_at, matched_entities
            FROM (
                SELECT *,
                    ROW_NUMBER() OVER (PARTITION BY category ORDER BY published_at DESC NULLS LAST) AS rn
                FROM rss_articles
                WHERE published_at > NOW() - INTERVAL '1 hour' * :hours
            ) sub
            WHERE rn <= 10
            ORDER BY category, published_at DESC
        """), {"hours": hours}).mappings().all()
    digest: dict = {}
    for r in rows:
        cat = r["category"] or "general"
        digest.setdefault(cat, []).append({
            "source": r["source_name"],
            "title": r["title"],
            "url": r["url"],
            "summary": r["summary"],
            "published_at": str(r["published_at"]) if r["published_at"] else None,
            "entities": r["matched_entities"] or [],
        })
    return {"hours": hours, "digest": digest}


@router.post("/rss/poll")
def trigger_rss_poll():
    """Manually trigger one RSS poll cycle (all 50 sources). Returns stats."""
    from app.connectors.rss_worker import run_poll_cycle
    stats = run_poll_cycle()
    return {"status": "ok", "stats": stats}


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
    """Company OSINT report: domain intel + UK Companies House + LinkedIn."""
    from app.connectors.osint_connector import company_osint_report
    return company_osint_report(company, domain=domain or None)
