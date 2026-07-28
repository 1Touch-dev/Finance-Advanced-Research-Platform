"""
API routes for financial data, news aggregation, and international registry lookups.
All endpoints are free-tier and gracefully degrade when keys are missing.
"""
from datetime import date
import xml.etree.ElementTree as ET

import requests
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

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
