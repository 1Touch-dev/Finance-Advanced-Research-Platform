"""
Legal Proceedings & Litigation Reserves API (Band C #50-51)
────────────────────────────────────────────────────────────────────────────────
Endpoints:
- GET /legal/{ticker}/proceedings - Extract legal proceedings from 10-K (#50)
- GET /legal/{ticker}/reserves - Get litigation reserves (#51)
- GET /legal/{ticker}/reserve-history - Historical reserve data (#51)
- GET /legal/{ticker}/reserve-adequacy - Reserve adequacy analysis (#51)
- GET /legal/{ticker}/reserve-ratios - Reserve to financial ratios (#51)
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import logging

from app.services.legal_proceedings_service import (
    extract_legal_proceedings,
    get_litigation_reserve_history,
    analyze_reserve_adequacy,
    get_reserve_to_financial_ratios,
    CaseType,
    CaseStatus,
    MaterialityAssessment,
)

router = APIRouter(prefix="/legal", tags=["legal"])
logger = logging.getLogger(__name__)


# ── Reference Endpoints (MUST come before parameterized routes) ───────────────


@router.get("/types/case-types")
def list_case_types():
    """List available case type classifications."""
    return {
        "case_types": [
            {"value": t.value, "name": t.name}
            for t in CaseType
        ],
    }


@router.get("/types/case-statuses")
def list_case_statuses():
    """List available case status values."""
    return {
        "case_statuses": [
            {"value": s.value, "name": s.name}
            for s in CaseStatus
        ],
    }


@router.get("/types/materiality-assessments")
def list_materiality_assessments():
    """List materiality assessment categories."""
    return {
        "materiality_assessments": [
            {"value": m.value, "name": m.name}
            for m in MaterialityAssessment
        ],
    }


# ── #50: Legal Proceedings Extraction ─────────────────────────────────────────


@router.get("/{ticker}/proceedings")
def get_ticker_proceedings(
    ticker: str,
    include_contingencies: bool = Query(True, description="Include contingencies note"),
    case_type: Optional[str] = Query(None, description="Filter by case type"),
    case_status: Optional[str] = Query(None, description="Filter by case status"),
):
    """
    Extract legal proceedings from 10-K filing (#50).

    Parses Item 103 (Legal Proceedings) and contingency notes
    to extract structured information about pending litigation.
    """
    ticker_upper = ticker.upper()

    # Validate filters before processing
    ct = None
    cs = None

    if case_type:
        try:
            ct = CaseType(case_type.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid case type: {case_type}")

    if case_status:
        try:
            cs = CaseStatus(case_status.lower())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid case status: {case_status}")

    try:
        report = extract_legal_proceedings(
            ticker=ticker_upper,
            include_contingencies=include_contingencies,
        )

        # Apply filters
        proceedings = report.proceedings

        if ct:
            proceedings = [p for p in proceedings if p.case_type == ct]

        if cs:
            proceedings = [p for p in proceedings if p.case_status == cs]

        result = report.to_dict()
        result["proceedings"] = [p.to_dict() for p in proceedings]
        result["filtered_count"] = len(proceedings)

        return result

    except Exception as e:
        logger.error(f"Error extracting proceedings for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Failed to extract legal proceedings")


@router.get("/{ticker}/proceedings/summary")
def get_ticker_proceedings_summary(ticker: str):
    """
    Get summary of legal proceedings for a company (#50).

    Returns aggregated statistics without full proceeding details.
    """
    ticker_upper = ticker.upper()

    try:
        report = extract_legal_proceedings(ticker=ticker_upper)

        return {
            "ticker": ticker_upper,
            "company_name": report.company_name,
            "filing_date": report.filing_date,
            "total_proceedings": report.total_proceedings,
            "active_proceedings": report.active_proceedings,
            "total_exposure": report.total_exposure,
            "total_accrued": report.total_accrued,
            "by_type": report.by_type,
            "by_status": report.by_status,
            "has_securities_litigation": report.has_securities_litigation,
            "has_government_investigation": report.has_government_investigation,
            "has_material_matters": report.has_material_matters,
            "management_overall_assessment": report.management_overall_assessment,
        }

    except Exception as e:
        logger.error(f"Error getting proceedings summary for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get proceedings summary")


# ── #51: Litigation Reserves ──────────────────────────────────────────────────


@router.get("/{ticker}/reserves")
def get_ticker_reserves(ticker: str):
    """
    Get current litigation reserves for a company (#51).

    Returns the most recent litigation reserve/accrual amount.
    """
    ticker_upper = ticker.upper()

    try:
        report = extract_legal_proceedings(ticker=ticker_upper)

        if report.reserves:
            return report.reserves.to_dict()
        else:
            return {
                "ticker": ticker_upper,
                "message": "No litigation reserves found in financial statements",
                "total_reserve": 0.0,
                "total_accrued_from_notes": report.total_accrued,
            }

    except Exception as e:
        logger.error(f"Error getting reserves for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get litigation reserves")


@router.get("/{ticker}/reserve-history")
def get_ticker_reserve_history(
    ticker: str,
    periods: int = Query(8, ge=2, le=20, description="Number of periods"),
):
    """
    Get historical litigation reserve data (#51).

    Returns time series of reserves for trend analysis
    and Sloan accrual computations.
    """
    ticker_upper = ticker.upper()

    try:
        history = get_litigation_reserve_history(
            ticker=ticker_upper,
            periods=periods,
        )

        return history.to_dict()

    except Exception as e:
        logger.error(f"Error getting reserve history for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get reserve history")


@router.get("/{ticker}/reserve-adequacy")
def get_ticker_reserve_adequacy(ticker: str):
    """
    Analyze litigation reserve adequacy (#51).

    Compares reserves against total exposure to assess
    whether the company is adequately reserved.
    """
    ticker_upper = ticker.upper()

    try:
        analysis = analyze_reserve_adequacy(ticker=ticker_upper)
        return analysis

    except Exception as e:
        logger.error(f"Error analyzing reserve adequacy for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Failed to analyze reserve adequacy")


@router.get("/{ticker}/reserve-ratios")
def get_ticker_reserve_ratios(ticker: str):
    """
    Get litigation reserve ratios vs financials (#51).

    Returns reserve as percentage of:
    - Revenue
    - Total assets
    - Equity
    - Operating income

    Useful for Sloan accrual analysis.
    """
    ticker_upper = ticker.upper()

    try:
        ratios = get_reserve_to_financial_ratios(ticker=ticker_upper)
        return ratios

    except Exception as e:
        logger.error(f"Error getting reserve ratios for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get reserve ratios")
