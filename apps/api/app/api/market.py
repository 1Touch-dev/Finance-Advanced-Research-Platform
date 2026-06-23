"""
API routes for financial data, news aggregation, and international registry lookups.
All endpoints are free-tier and gracefully degrade when keys are missing.
"""
from fastapi import APIRouter
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
