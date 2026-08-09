"""
API routes for financial data, news aggregation, and international registry lookups.
All endpoints are free-tier and gracefully degrade when keys are missing.
"""
from datetime import date
import os
import xml.etree.ElementTree as ET

import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from typing import Optional
from app.connectors.financial_news_connector import (
    finnhub_quote, finnhub_company_profile, finnhub_financials,
    finnhub_insider_transactions, fmp_income_statement, fmp_balance_sheet,
    fmp_cash_flow, fmp_key_metrics, compute_beneish_mscore, compute_altman_zscore,
    fred_macro_data, aggregate_news, newsapi_search, guardian_search,
    nyt_search, gdelt_search, ukch_search, ukch_officers, icij_search, aleph_search,
)
from app.db.session import get_db
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
    from app.connectors.gov_trading_connector import get_trades_by_ticker
    trades = get_trades_by_ticker(ticker, days=days)
    return {"ticker": ticker.upper(), "trades": trades, "count": len(trades)}


@router.get("/gov-trading/member")
def gov_trading_by_member(name: str):
    """All trades by a specific congressional member."""
    from app.connectors.gov_trading_connector import get_trades_by_member
    trades = get_trades_by_member(name)
    return {"name": name, "trades": trades, "count": len(trades)}


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
def company_private_intel(entity_name: str, jurisdiction: str = ""):
    """
    Full private company intelligence: OpenCorporates + GLEIF + FinCEN + FDIC.
    Includes contracts, funding, and corporate registration data.
    """
    from app.connectors.private_company_connector import fetch_private_company_intel

    # Get private company data
    private_data = fetch_private_company_intel(entity_name, jurisdiction=jurisdiction)

    # Add contracts and funding
    contracts = company_contracts(entity_name, limit=10)
    funding = company_funding(entity_name)

    return {
        "entity_name": entity_name,
        "registration": private_data,
        "contracts": contracts,
        "funding": funding,
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
