"""
Docket-to-Disclosure Reconciliation API (Band B #31)
--------------------------------------------------------------------------------
Provides endpoints for:
  - /docket/{ticker}/reconcile - Run reconciliation
  - /docket/{ticker}/findings - Get findings for a company
  - /docket/{ticker}/cases - Get docket cases
  - /docket/finding/{id} - Get specific finding details
  - /docket/report/{ticker} - Generate full report
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import logging

from app.services.docket_disclosure_service import (
    reconcile_litigation,
    report_to_dict,
    ReconciliationReport,
    ReconciliationFinding,
    DocketCase,
    DisclosedLitigation,
    DivergenceType,
    DisclosureStatus,
    MaterialityLevel,
)

router = APIRouter(prefix="/docket", tags=["docket"])
logger = logging.getLogger(__name__)

# In-memory cache for reconciliation reports (would use Redis in production)
_report_cache: dict[str, ReconciliationReport] = {}


@router.get("/{ticker}/reconcile")
def reconcile_docket_disclosure(
    ticker: str,
    lookback_years: int = Query(3, ge=1, le=10, description="Years of litigation to analyze"),
    refresh: bool = Query(False, description="Force refresh even if cached"),
):
    """
    Reconcile court dockets against SEC disclosures for a company.

    This is the core L-series feature that compares:
    - Public court dockets (CourtListener)
    - SEC filing disclosures (10-K Item 3, contingencies)

    Returns findings where litigation may be undisclosed or misrepresented.
    """
    ticker_upper = ticker.upper()

    # Check cache
    if not refresh and ticker_upper in _report_cache:
        report = _report_cache[ticker_upper]
        return {
            "cached": True,
            "report": report_to_dict(report),
        }

    try:
        report = reconcile_litigation(ticker_upper, lookback_years=lookback_years)
        _report_cache[ticker_upper] = report

        return {
            "cached": False,
            "report": report_to_dict(report),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error reconciling docket for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Reconciliation failed")


@router.get("/{ticker}/findings")
def get_findings(
    ticker: str,
    min_risk: Optional[float] = Query(None, ge=0, le=100, description="Minimum risk score"),
    divergence_type: Optional[str] = Query(None, description="Filter by divergence type"),
    materiality: Optional[str] = Query(None, description="Filter by materiality level"),
    limit: int = Query(50, ge=1, le=200, description="Maximum findings to return"),
):
    """
    Get reconciliation findings for a company.

    Findings represent divergences between court dockets and SEC disclosures.
    """
    ticker_upper = ticker.upper()

    # Get or create report
    if ticker_upper not in _report_cache:
        try:
            report = reconcile_litigation(ticker_upper)
            _report_cache[ticker_upper] = report
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error getting findings for {ticker}: {e}")
            raise HTTPException(status_code=500, detail="Failed to get findings")
    else:
        report = _report_cache[ticker_upper]

    # Filter findings
    findings = report.findings

    if min_risk is not None:
        findings = [f for f in findings if f.risk_score >= min_risk]

    if divergence_type:
        try:
            div_type = DivergenceType(divergence_type.lower())
            findings = [f for f in findings if f.divergence_type == div_type]
        except ValueError:
            pass

    if materiality:
        try:
            mat_level = MaterialityLevel(materiality.lower())
            findings = [f for f in findings if f.materiality == mat_level]
        except ValueError:
            pass

    # Limit
    findings = findings[:limit]

    return {
        "ticker": ticker_upper,
        "company_name": report.company_name,
        "total_findings": len(report.findings),
        "filtered_count": len(findings),
        "findings": [
            {
                "id": f.id,
                "divergence_type": f.divergence_type.value,
                "disclosure_status": f.disclosure_status.value,
                "materiality": f.materiality.value,
                "title": f.title,
                "description": f.description,
                "risk_score": f.risk_score,
                "recommendations": f.recommendations,
            }
            for f in findings
        ],
    }


@router.get("/{ticker}/cases")
def get_docket_cases(
    ticker: str,
    status: Optional[str] = Query(None, description="Filter by case status (open/closed/settled)"),
    limit: int = Query(50, ge=1, le=200, description="Maximum cases to return"),
):
    """
    Get court docket cases for a company.

    Returns cases found in public court records.
    """
    ticker_upper = ticker.upper()

    # Get or create report
    if ticker_upper not in _report_cache:
        try:
            report = reconcile_litigation(ticker_upper)
            _report_cache[ticker_upper] = report
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error getting cases for {ticker}: {e}")
            raise HTTPException(status_code=500, detail="Failed to get cases")
    else:
        report = _report_cache[ticker_upper]

    cases = report.docket_cases

    # Filter by status
    if status:
        cases = [c for c in cases if c.status.lower() == status.lower()]

    cases = cases[:limit]

    return {
        "ticker": ticker_upper,
        "company_name": report.company_name,
        "total_cases": len(report.docket_cases),
        "filtered_count": len(cases),
        "cases": [
            {
                "case_id": c.case_id,
                "case_name": c.case_name,
                "court": c.court,
                "docket_number": c.docket_number,
                "filed_date": c.filed_date,
                "status": c.status,
                "nature_of_suit": c.nature_of_suit,
                "amount_claimed": c.amount_claimed,
                "source_url": c.source_url,
            }
            for c in cases
        ],
    }


@router.get("/{ticker}/disclosures")
def get_disclosures(
    ticker: str,
    filing_type: Optional[str] = Query(None, description="Filter by filing type (10-K/10-Q/8-K)"),
    limit: int = Query(50, ge=1, le=200, description="Maximum disclosures to return"),
):
    """
    Get litigation disclosures from SEC filings for a company.
    """
    ticker_upper = ticker.upper()

    # Get or create report
    if ticker_upper not in _report_cache:
        try:
            report = reconcile_litigation(ticker_upper)
            _report_cache[ticker_upper] = report
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error getting disclosures for {ticker}: {e}")
            raise HTTPException(status_code=500, detail="Failed to get disclosures")
    else:
        report = _report_cache[ticker_upper]

    disclosures = report.disclosed_litigation

    # Filter by filing type
    if filing_type:
        disclosures = [d for d in disclosures if d.filing_type.upper() == filing_type.upper()]

    disclosures = disclosures[:limit]

    return {
        "ticker": ticker_upper,
        "company_name": report.company_name,
        "total_disclosures": len(report.disclosed_litigation),
        "filtered_count": len(disclosures),
        "disclosures": [
            {
                "filing_type": d.filing_type,
                "filing_date": d.filing_date,
                "accession_number": d.accession_number,
                "description": d.description[:200] if d.description else None,
                "amount_disclosed": d.amount_disclosed,
                "management_assessment": d.management_assessment,
                "section": d.section,
            }
            for d in disclosures
        ],
    }


@router.get("/{ticker}/summary")
def get_reconciliation_summary(ticker: str):
    """
    Get reconciliation summary for a company.

    Returns high-level metrics and risk assessment.
    """
    ticker_upper = ticker.upper()

    # Get or create report
    if ticker_upper not in _report_cache:
        try:
            report = reconcile_litigation(ticker_upper)
            _report_cache[ticker_upper] = report
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            logger.error(f"Error getting summary for {ticker}: {e}")
            raise HTTPException(status_code=500, detail="Failed to get summary")
    else:
        report = _report_cache[ticker_upper]

    return {
        "ticker": ticker_upper,
        "company_name": report.company_name,
        "cik": report.cik,
        "analysis_date": report.analysis_date,
        "risk_score": report.risk_score,
        "summary": report.summary,
        "generated_at": report.generated_at,
    }


@router.get("/finding/{finding_id}")
def get_finding_detail(finding_id: str):
    """
    Get detailed information about a specific finding.
    """
    # Search all cached reports for this finding
    for report in _report_cache.values():
        for finding in report.findings:
            if finding.id == finding_id:
                return {
                    "ticker": report.ticker,
                    "company_name": report.company_name,
                    "finding": {
                        "id": finding.id,
                        "divergence_type": finding.divergence_type.value,
                        "disclosure_status": finding.disclosure_status.value,
                        "materiality": finding.materiality.value,
                        "title": finding.title,
                        "description": finding.description,
                        "risk_score": finding.risk_score,
                        "evidence": finding.evidence,
                        "recommendations": finding.recommendations,
                        "created_at": finding.created_at,
                        "docket_case": {
                            "case_id": finding.docket_case.case_id,
                            "case_name": finding.docket_case.case_name,
                            "court": finding.docket_case.court,
                            "docket_number": finding.docket_case.docket_number,
                            "filed_date": finding.docket_case.filed_date,
                            "status": finding.docket_case.status,
                            "amount_claimed": finding.docket_case.amount_claimed,
                        } if finding.docket_case else None,
                        "disclosed_litigation": {
                            "filing_type": finding.disclosed_litigation.filing_type,
                            "filing_date": finding.disclosed_litigation.filing_date,
                            "description": finding.disclosed_litigation.description[:300],
                            "amount_disclosed": finding.disclosed_litigation.amount_disclosed,
                        } if finding.disclosed_litigation else None,
                    },
                }

    raise HTTPException(status_code=404, detail=f"Finding {finding_id} not found")


@router.get("/types/divergence")
def list_divergence_types():
    """
    List available divergence types for filtering.
    """
    return {
        "divergence_types": [
            {
                "value": t.value,
                "description": _DIVERGENCE_DESCRIPTIONS.get(t, ""),
            }
            for t in DivergenceType
        ],
    }


@router.get("/types/materiality")
def list_materiality_levels():
    """
    List materiality levels for filtering.
    """
    return {
        "materiality_levels": [
            {
                "value": m.value,
                "description": _MATERIALITY_DESCRIPTIONS.get(m, ""),
            }
            for m in MaterialityLevel
        ],
    }


# -- Reference data ----------------------------------------------------------

_DIVERGENCE_DESCRIPTIONS = {
    DivergenceType.MISSING_DISCLOSURE: "Case exists in court records but not disclosed in SEC filings",
    DivergenceType.AMOUNT_MISMATCH: "Amounts claimed differ between docket and disclosure",
    DivergenceType.TIMING_GAP: "Significant delay between case filing and disclosure",
    DivergenceType.STATUS_MISMATCH: "Different case status reported",
    DivergenceType.PARTY_MISMATCH: "Different parties named in disclosure vs docket",
    DivergenceType.MINIMIZATION: "Disclosure appears to downplay case severity",
    DivergenceType.OUTCOME_NOT_UPDATED: "Settlement or resolution not reflected in disclosure",
}

_MATERIALITY_DESCRIPTIONS = {
    MaterialityLevel.CRITICAL: ">10% of market cap or criminal matter",
    MaterialityLevel.HIGH: ">5% of market cap or significant regulatory",
    MaterialityLevel.MEDIUM: "1-5% of market cap",
    MaterialityLevel.LOW: "<1% of market cap",
    MaterialityLevel.UNKNOWN: "Amount not determinable",
}
