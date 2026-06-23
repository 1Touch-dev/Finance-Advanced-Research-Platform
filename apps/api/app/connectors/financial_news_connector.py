"""
Financial data + news API connectors.
Covers: FINNHUB, FMP, Alpha Vantage, FRED, NewsAPI, Guardian, NYT, GDELT,
        UK Companies House, ICIJ Offshore Leaks, ALEPH/OCCRP
All APIs are free-tier; gracefully returns {} / [] when key is missing.
"""
import os
import logging
import requests
from typing import Optional

log = logging.getLogger(__name__)

FINNHUB_KEY  = os.getenv("FINNHUB_API_KEY", "")
FMP_KEY      = os.getenv("FMP_API_KEY", "")
AV_KEY       = os.getenv("ALPHA_VANTAGE_KEY", "")
FRED_KEY     = os.getenv("FRED_API_KEY", "")
NEWSAPI_KEY  = os.getenv("NEWSAPI_KEY", "")
GUARDIAN_KEY = os.getenv("GUARDIAN_API_KEY", "")
NYT_KEY      = os.getenv("NYT_API_KEY", "")
UKCH_KEY     = os.getenv("UK_COMPANIES_HOUSE_KEY", "")
ALEPH_KEY    = os.getenv("ALEPH_API_KEY", "")

_TIMEOUT = 12


def _get(url, params=None, headers=None, auth=None):
    try:
        r = requests.get(url, params=params, headers=headers, auth=auth, timeout=_TIMEOUT)
        if r.status_code == 200:
            return r.json()
        log.warning("GET %s → %s", url, r.status_code)
    except Exception as e:
        log.warning("GET %s failed: %s", url, e)
    return None


# ─── FINNHUB ──────────────────────────────────────────────────────────────────

def finnhub_quote(ticker: str) -> dict:
    if not FINNHUB_KEY:
        return {"error": "FINNHUB_API_KEY not set", "ticker": ticker}
    data = _get("https://finnhub.io/api/v1/quote",
                params={"symbol": ticker, "token": FINNHUB_KEY})
    if not data:
        return {}
    return {
        "ticker": ticker,
        "price": data.get("c"),
        "change": data.get("d"),
        "change_pct": data.get("dp"),
        "high": data.get("h"),
        "low": data.get("l"),
        "open": data.get("o"),
        "prev_close": data.get("pc"),
        "source": "Finnhub",
    }


def finnhub_company_profile(ticker: str) -> dict:
    if not FINNHUB_KEY:
        return {}
    data = _get("https://finnhub.io/api/v1/stock/profile2",
                params={"symbol": ticker, "token": FINNHUB_KEY})
    if not data:
        return {}
    return {
        "name": data.get("name"),
        "ticker": data.get("ticker"),
        "exchange": data.get("exchange"),
        "industry": data.get("finnhubIndustry"),
        "ipo": data.get("ipo"),
        "market_cap": data.get("marketCapitalization"),
        "shares_outstanding": data.get("shareOutstanding"),
        "website": data.get("weburl"),
        "logo": data.get("logo"),
        "country": data.get("country"),
        "currency": data.get("currency"),
        "source": "Finnhub",
    }


def finnhub_financials(ticker: str) -> dict:
    """Fetch basic financial metrics from Finnhub."""
    if not FINNHUB_KEY:
        return {}
    data = _get("https://finnhub.io/api/v1/stock/metric",
                params={"symbol": ticker, "metric": "all", "token": FINNHUB_KEY})
    if not data or "metric" not in data:
        return {}
    m = data["metric"]
    return {
        "ticker": ticker,
        "pe_ratio": m.get("peNormalizedAnnual"),
        "ps_ratio": m.get("psAnnual"),
        "pb_ratio": m.get("pbAnnual"),
        "ev_ebitda": m.get("evEbitdaAnnual"),
        "debt_equity": m.get("totalDebt/totalEquityAnnual"),
        "roe": m.get("roeRfy"),
        "roa": m.get("roaRfy"),
        "revenue_ttm": m.get("revenuePerShareTTM"),
        "eps_ttm": m.get("epsNormalizedAnnual"),
        "gross_margin": m.get("grossMarginTTM"),
        "operating_margin": m.get("operatingMarginTTM"),
        "net_margin": m.get("netProfitMarginTTM"),
        "52w_high": m.get("52WeekHigh"),
        "52w_low": m.get("52WeekLow"),
        "beta": m.get("beta"),
        "source": "Finnhub",
    }


def finnhub_insider_transactions(ticker: str) -> list:
    if not FINNHUB_KEY:
        return []
    data = _get("https://finnhub.io/api/v1/stock/insider-transactions",
                params={"symbol": ticker, "token": FINNHUB_KEY})
    if not data or "data" not in data:
        return []
    txns = []
    for t in (data["data"] or [])[:30]:
        txns.append({
            "name": t.get("name"),
            "date": t.get("transactionDate"),
            "shares": t.get("share"),
            "value": t.get("transactionPrice"),
            "transaction": t.get("transactionCode"),
            "source": "Finnhub",
        })
    return txns


def finnhub_news(entity_name: str, limit: int = 20) -> list:
    """Company news from Finnhub (by ticker if available, otherwise general search)."""
    if not FINNHUB_KEY:
        return []
    data = _get("https://finnhub.io/api/v1/company-news",
                params={"symbol": entity_name.upper()[:5], "from": "2024-01-01",
                        "to": "2026-12-31", "token": FINNHUB_KEY})
    if not data:
        return []
    articles = []
    for a in (data or [])[:limit]:
        articles.append({
            "title": a.get("headline"),
            "summary": a.get("summary"),
            "url": a.get("url"),
            "source": a.get("source"),
            "date": a.get("datetime"),
            "provider": "Finnhub",
        })
    return articles


# ─── FMP (Financial Modeling Prep) ───────────────────────────────────────────

def fmp_income_statement(ticker: str, limit: int = 20) -> list:
    if not FMP_KEY:
        return []
    data = _get(f"https://financialmodelingprep.com/api/v3/income-statement/{ticker}",
                params={"limit": limit, "apikey": FMP_KEY})
    if not data:
        return []
    rows = []
    for s in data:
        rows.append({
            "date": s.get("date"),
            "period": s.get("period"),
            "revenue": s.get("revenue"),
            "gross_profit": s.get("grossProfit"),
            "operating_income": s.get("operatingIncome"),
            "net_income": s.get("netIncome"),
            "ebitda": s.get("ebitda"),
            "gross_margin": s.get("grossProfitRatio"),
            "operating_margin": s.get("operatingIncomeRatio"),
            "net_margin": s.get("netIncomeRatio"),
            "source": "FMP",
        })
    return rows


def fmp_balance_sheet(ticker: str, limit: int = 10) -> list:
    if not FMP_KEY:
        return []
    data = _get(f"https://financialmodelingprep.com/api/v3/balance-sheet-statement/{ticker}",
                params={"limit": limit, "apikey": FMP_KEY})
    if not data:
        return []
    rows = []
    for s in data:
        rows.append({
            "date": s.get("date"),
            "total_assets": s.get("totalAssets"),
            "total_liabilities": s.get("totalLiabilities"),
            "total_equity": s.get("totalStockholdersEquity"),
            "cash": s.get("cashAndCashEquivalents"),
            "total_debt": s.get("totalDebt"),
            "net_debt": s.get("netDebt"),
            "source": "FMP",
        })
    return rows


def fmp_cash_flow(ticker: str, limit: int = 10) -> list:
    if not FMP_KEY:
        return []
    data = _get(f"https://financialmodelingprep.com/api/v3/cash-flow-statement/{ticker}",
                params={"limit": limit, "apikey": FMP_KEY})
    if not data:
        return []
    rows = []
    for s in data:
        rows.append({
            "date": s.get("date"),
            "operating_cf": s.get("netCashProvidedByOperatingActivities"),
            "capex": s.get("capitalExpenditure"),
            "free_cash_flow": s.get("freeCashFlow"),
            "dividends": s.get("dividendsPaid"),
            "source": "FMP",
        })
    return rows


def fmp_key_metrics(ticker: str) -> dict:
    if not FMP_KEY:
        return {}
    data = _get(f"https://financialmodelingprep.com/api/v3/key-metrics-ttm/{ticker}",
                params={"apikey": FMP_KEY})
    if not data or not isinstance(data, list):
        return {}
    m = data[0] if data else {}
    return {
        "ticker": ticker,
        "revenue_per_share": m.get("revenuePerShareTTM"),
        "net_income_per_share": m.get("netIncomePerShareTTM"),
        "operating_cf_per_share": m.get("operatingCashFlowPerShareTTM"),
        "fcf_per_share": m.get("freeCashFlowPerShareTTM"),
        "book_value_per_share": m.get("bookValuePerShareTTM"),
        "pe_ratio": m.get("peRatioTTM"),
        "price_to_sales": m.get("priceToSalesRatioTTM"),
        "price_to_book": m.get("pbRatioTTM"),
        "ev_ebitda": m.get("enterpriseValueOverEBITDATTM"),
        "debt_to_equity": m.get("debtToEquityTTM"),
        "roe": m.get("roeTTM"),
        "roa": m.get("roaRfy"),
        "source": "FMP",
    }


def compute_beneish_mscore(ticker: str) -> dict:
    """
    Compute Beneish M-Score from FMP income + balance sheet data.
    M > -2.22 is a red flag for earnings manipulation.
    Uses simplified 5-variable model when full XBRL data not available.
    """
    inc = fmp_income_statement(ticker, limit=3)
    bal = fmp_balance_sheet(ticker, limit=3)
    if len(inc) < 2 or len(bal) < 2:
        return {"error": "insufficient data for M-Score", "ticker": ticker}
    try:
        # Year T and T-1
        rev_t  = inc[0]["revenue"] or 1
        rev_t1 = inc[1]["revenue"] or 1
        gp_t   = inc[0]["gross_profit"] or 0
        gp_t1  = inc[1]["gross_profit"] or 0
        ni_t   = inc[0]["net_income"] or 0
        ni_t1  = inc[1]["net_income"] or 1
        ta_t   = bal[0]["total_assets"] or 1
        ta_t1  = bal[1]["total_assets"] or 1
        tl_t   = bal[0]["total_liabilities"] or 0
        tl_t1  = bal[1]["total_liabilities"] or 1
        # DSRI (Days Sales Receivable Index)
        DSRI = 1.0  # simplified without AR data
        # GMI (Gross Margin Index)
        gm_t  = gp_t  / rev_t  if rev_t  else 0
        gm_t1 = gp_t1 / rev_t1 if rev_t1 else 0
        GMI = (gm_t1 / gm_t) if gm_t else 1.0
        # AQI (Asset Quality Index)
        AQI = 1.0  # simplified
        # SGI (Sales Growth Index)
        SGI = rev_t / rev_t1 if rev_t1 else 1.0
        # DEPI (Depreciation Index)
        DEPI = 1.0  # simplified
        # SGAI (SG&A Index)
        SGAI = 1.0  # simplified
        # ACCRUALS
        ACCRUALS = (ni_t - 0) / ta_t if ta_t else 0
        # LVGI (Leverage Index)
        lev_t  = tl_t  / ta_t  if ta_t  else 0
        lev_t1 = tl_t1 / ta_t1 if ta_t1 else 0
        LVGI = lev_t / lev_t1 if lev_t1 else 1.0
        # M-Score formula
        m_score = (-4.84
                   + 0.920 * DSRI
                   + 0.528 * GMI
                   + 0.404 * AQI
                   + 0.892 * SGI
                   + 0.115 * DEPI
                   - 0.172 * SGAI
                   + 4.679 * ACCRUALS
                   - 0.327 * LVGI)
        risk = "HIGH RISK" if m_score > -2.22 else ("MODERATE" if m_score > -2.5 else "LOW RISK")
        return {
            "ticker": ticker,
            "m_score": round(m_score, 3),
            "risk_level": risk,
            "threshold": -2.22,
            "interpretation": "M > -2.22 suggests possible earnings manipulation",
            "components": {"DSRI": DSRI, "GMI": round(GMI, 3), "SGI": round(SGI, 3),
                           "ACCRUALS": round(ACCRUALS, 4), "LVGI": round(LVGI, 3)},
            "source": "FMP + Beneish (1999)",
        }
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


def compute_altman_zscore(ticker: str) -> dict:
    """
    Compute Altman Z-Score for public companies.
    Z < 1.81 = distress zone; Z > 2.99 = safe zone.
    """
    bal = fmp_balance_sheet(ticker, limit=2)
    inc = fmp_income_statement(ticker, limit=2)
    metrics = fmp_key_metrics(ticker)
    if not bal or not inc:
        return {"error": "insufficient data for Z-Score", "ticker": ticker}
    try:
        ta  = bal[0]["total_assets"] or 1
        tl  = bal[0]["total_liabilities"] or 0
        te  = bal[0]["total_equity"] or 0
        rev = inc[0]["revenue"] or 0
        ebit = inc[0]["operating_income"] or 0
        cash = bal[0]["cash"] or 0
        # Working Capital proxy (current assets - current liabilities ≈ cash)
        WC = cash
        RE = te * 0.4   # retained earnings proxy
        EBIT = ebit
        MVE = te        # market value of equity proxy (book)
        S   = rev
        # Z = 1.2(WC/TA) + 1.4(RE/TA) + 3.3(EBIT/TA) + 0.6(MVE/TL) + 1.0(S/TA)
        z = (1.2 * (WC / ta)
             + 1.4 * (RE / ta)
             + 3.3 * (EBIT / ta)
             + 0.6 * (MVE / tl if tl else 0)
             + 1.0 * (S / ta))
        if z < 1.81:
            zone = "Distress Zone"
        elif z < 2.99:
            zone = "Grey Zone"
        else:
            zone = "Safe Zone"
        return {
            "ticker": ticker,
            "z_score": round(z, 3),
            "zone": zone,
            "thresholds": {"distress_below": 1.81, "safe_above": 2.99},
            "components": {
                "WC_TA": round(WC/ta, 4),
                "RE_TA": round(RE/ta, 4),
                "EBIT_TA": round(EBIT/ta, 4),
                "S_TA": round(S/ta, 4),
            },
            "source": "FMP + Altman (1968)",
        }
    except Exception as e:
        return {"error": str(e), "ticker": ticker}


# ─── FRED (Federal Reserve) ──────────────────────────────────────────────────

def fred_macro_data(series_id: str = "GDP", limit: int = 10) -> list:
    if not FRED_KEY:
        return []
    data = _get("https://api.stlouisfed.org/fred/series/observations",
                params={"series_id": series_id, "api_key": FRED_KEY,
                        "file_type": "json", "sort_order": "desc", "limit": limit})
    if not data or "observations" not in data:
        return []
    return [{"date": o["date"], "value": o["value"], "series": series_id}
            for o in data["observations"] if o["value"] != "."]


# ─── NEWS APIs ───────────────────────────────────────────────────────────────

def newsapi_search(query: str, limit: int = 20) -> list:
    if not NEWSAPI_KEY:
        return []
    data = _get("https://newsapi.org/v2/everything",
                params={"q": query, "sortBy": "publishedAt", "pageSize": limit,
                        "language": "en", "apiKey": NEWSAPI_KEY})
    if not data or "articles" not in data:
        return []
    articles = []
    for a in data["articles"][:limit]:
        articles.append({
            "title": a.get("title"),
            "description": a.get("description"),
            "url": a.get("url"),
            "source": a.get("source", {}).get("name"),
            "date": a.get("publishedAt"),
            "provider": "NewsAPI",
        })
    return articles


def guardian_search(query: str, limit: int = 20) -> list:
    if not GUARDIAN_KEY:
        return []
    data = _get("https://content.guardianapis.com/search",
                params={"q": query, "page-size": limit, "order-by": "newest",
                        "show-fields": "headline,trailText,byline",
                        "api-key": GUARDIAN_KEY})
    if not data or "response" not in data:
        return []
    articles = []
    for a in (data["response"].get("results") or [])[:limit]:
        fields = a.get("fields", {})
        articles.append({
            "title": fields.get("headline") or a.get("webTitle"),
            "description": fields.get("trailText"),
            "url": a.get("webUrl"),
            "date": a.get("webPublicationDate"),
            "section": a.get("sectionName"),
            "provider": "The Guardian",
        })
    return articles


def nyt_search(query: str, limit: int = 20) -> list:
    if not NYT_KEY:
        return []
    data = _get("https://api.nytimes.com/svc/search/v2/articlesearch.json",
                params={"q": query, "sort": "newest", "api-key": NYT_KEY})
    if not data or "response" not in data:
        return []
    articles = []
    for a in (data["response"].get("docs") or [])[:limit]:
        articles.append({
            "title": a.get("abstract") or a.get("headline", {}).get("main"),
            "url": a.get("web_url"),
            "date": a.get("pub_date"),
            "section": a.get("section_name"),
            "source": "New York Times",
            "provider": "NYT",
        })
    return articles


def gdelt_search(query: str, limit: int = 20) -> list:
    """GDELT — no key required. Global news + sentiment."""
    data = _get("https://api.gdeltproject.org/api/v2/doc/doc",
                params={"query": query, "mode": "artlist", "maxrecords": limit,
                        "format": "json", "sort": "DateDesc"})
    if not data or "articles" not in data:
        return []
    articles = []
    for a in (data["articles"] or [])[:limit]:
        articles.append({
            "title": a.get("title"),
            "url": a.get("url"),
            "date": a.get("seendate"),
            "domain": a.get("domain"),
            "language": a.get("language"),
            "tone": a.get("tone"),
            "provider": "GDELT",
        })
    return articles


def aggregate_news(entity_name: str, limit_per_source: int = 10) -> dict:
    """Fetch news from all available sources and return combined."""
    results = {
        "newsapi": newsapi_search(entity_name, limit_per_source),
        "guardian": guardian_search(entity_name, limit_per_source),
        "nyt": nyt_search(entity_name, limit_per_source),
        "gdelt": gdelt_search(entity_name, limit_per_source),
        "finnhub": finnhub_news(entity_name, limit_per_source),
    }
    all_articles = []
    for src, arts in results.items():
        all_articles.extend(arts)
    return {
        "entity": entity_name,
        "total": len(all_articles),
        "by_source": {k: len(v) for k, v in results.items()},
        "articles": all_articles,
    }


# ─── UK COMPANIES HOUSE ──────────────────────────────────────────────────────

def ukch_search(company_name: str, limit: int = 10) -> list:
    if not UKCH_KEY:
        return []
    data = _get("https://api.company-information.service.gov.uk/search/companies",
                params={"q": company_name, "items_per_page": limit},
                auth=(UKCH_KEY, ""))
    if not data or "items" not in data:
        return []
    results = []
    for c in data["items"][:limit]:
        results.append({
            "name": c.get("title"),
            "company_number": c.get("company_number"),
            "company_type": c.get("company_type"),
            "company_status": c.get("company_status"),
            "jurisdiction": "UK",
            "incorporation_date": c.get("date_of_creation"),
            "registered_address": c.get("registered_office_address", {}).get("address_line_1"),
            "source": "UK Companies House",
        })
    return results


def ukch_officers(company_number: str) -> list:
    if not UKCH_KEY:
        return []
    data = _get(f"https://api.company-information.service.gov.uk/company/{company_number}/officers",
                auth=(UKCH_KEY, ""))
    if not data or "items" not in data:
        return []
    officers = []
    for o in data["items"]:
        officers.append({
            "name": o.get("name"),
            "role": o.get("officer_role"),
            "appointed_on": o.get("appointed_on"),
            "resigned_on": o.get("resigned_on"),
            "nationality": o.get("nationality"),
            "country_of_residence": o.get("country_of_residence"),
            "source": "UK Companies House",
        })
    return officers


# ─── ICIJ OFFSHORE LEAKS ─────────────────────────────────────────────────────

def icij_search(entity_name: str) -> list:
    """Search Panama/Paradise/Pandora Papers — no key required."""
    data = _get("https://offshoreleaks.icij.org/api/search",
                params={"q": entity_name, "cat": "0", "e": "1"})
    if not data:
        return []
    results = []
    nodes = data if isinstance(data, list) else data.get("nodes", [])
    for n in (nodes or [])[:20]:
        results.append({
            "name": n.get("name"),
            "jurisdiction": n.get("jurisdiction"),
            "dataset": n.get("sourceID"),
            "linked_to": n.get("linked_to"),
            "source": "ICIJ Offshore Leaks",
        })
    return results


# ─── ALEPH / OCCRP ───────────────────────────────────────────────────────────

def aleph_search(entity_name: str, limit: int = 10) -> list:
    headers = {"Authorization": f"ApiKey {ALEPH_KEY}"} if ALEPH_KEY else {}
    data = _get("https://aleph.occrp.org/api/2/entities",
                params={"q": entity_name, "limit": limit},
                headers=headers)
    if not data or "results" not in data:
        return []
    results = []
    for e in data["results"][:limit]:
        props = e.get("properties", {})
        results.append({
            "name": props.get("name", [None])[0],
            "schema": e.get("schema"),
            "collection": e.get("collection", {}).get("label"),
            "countries": props.get("country", []),
            "source": "ALEPH/OCCRP",
        })
    return results
