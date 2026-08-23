"""
Filing Comparison API Routes (Band B #15)
────────────────────────────────────────────────────────────────────────────
Provides endpoints for:
  - Filing-to-filing comparison (10-K, 10-Q, 8-K)
  - Redline HTML generation
  - Table extraction for Excel export
  - Material change detection
"""

import os
import tempfile
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from typing import Optional

from app.services.filing_diff_service import (
    get_filing_diff,
    generate_redline_html,
    export_diff_to_excel,
    diff_result_to_dict,
    FilingDiffResult,
)

router = APIRouter(prefix="/filings")


@router.get("/compare")
def compare_filings(
    ticker: str = Query(..., description="Stock ticker symbol"),
    form_type: str = Query("10-K", description="SEC form type (10-K, 10-Q, 8-K)"),
    base_period: Optional[str] = Query(None, description="Base period (e.g., 2024)"),
    compare_period: Optional[str] = Query(None, description="Compare period (e.g., 2023)"),
):
    """
    Compare two filing periods and return structured diff results.

    Returns:
        JSON with financial changes, narrative changes, material flags, and summary
    """
    try:
        result = get_filing_diff(
            ticker=ticker.upper(),
            form_type=form_type,
            base_period=base_period,
            compare_period=compare_period,
        )
        return diff_result_to_dict(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating diff: {str(e)}")


@router.get("/compare/redline", response_class=HTMLResponse)
def get_redline_html(
    ticker: str = Query(..., description="Stock ticker symbol"),
    form_type: str = Query("10-K", description="SEC form type"),
    base_period: Optional[str] = Query(None, description="Base period"),
    compare_period: Optional[str] = Query(None, description="Compare period"),
):
    """
    Generate a standalone HTML redline comparison document.

    Returns:
        HTML document with visual diff markup
    """
    try:
        result = get_filing_diff(
            ticker=ticker.upper(),
            form_type=form_type,
            base_period=base_period,
            compare_period=compare_period,
        )
        html = generate_redline_html(result)
        return HTMLResponse(content=html, media_type="text/html")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating redline: {str(e)}")


@router.get("/compare/excel")
def get_excel_export(
    ticker: str = Query(..., description="Stock ticker symbol"),
    form_type: str = Query("10-K", description="SEC form type"),
    base_period: Optional[str] = Query(None, description="Base period"),
    compare_period: Optional[str] = Query(None, description="Compare period"),
):
    """
    Export filing comparison to Excel workbook.

    Returns:
        XLSX file download
    """
    try:
        result = get_filing_diff(
            ticker=ticker.upper(),
            form_type=form_type,
            base_period=base_period,
            compare_period=compare_period,
        )

        # Create temp file for Excel
        with tempfile.NamedTemporaryFile(
            suffix=".xlsx",
            prefix=f"{ticker}_comparison_",
            delete=False
        ) as tmp:
            filepath = export_diff_to_excel(result, tmp.name)

        filename = f"{ticker}_{form_type}_comparison.xlsx"
        return FileResponse(
            path=filepath,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail="Excel export requires openpyxl. Install with: pip install openpyxl"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating Excel: {str(e)}")


@router.get("/history")
def get_filing_history(
    ticker: str = Query(..., description="Stock ticker symbol"),
    form_type: str = Query("10-K", description="SEC form type"),
    limit: int = Query(10, description="Number of filings to return"),
):
    """
    Get filing history for a ticker to enable period selection.

    Returns:
        List of available filings with dates and accession numbers
    """
    from app.connectors.sec_edgar_connector import get_filer_cik, get_company_submissions

    try:
        cik = get_filer_cik(ticker.upper())
        if not cik:
            raise HTTPException(status_code=404, detail=f"Could not resolve ticker: {ticker}")

        submissions = get_company_submissions(cik)
        if not submissions or not isinstance(submissions, dict):
            raise HTTPException(status_code=404, detail=f"No submissions found for: {ticker}")

        filings_section = submissions.get("filings", {})
        if not isinstance(filings_section, dict):
            raise HTTPException(status_code=404, detail=f"No submissions found for: {ticker}")
        filings_data = filings_section.get("recent", {})
        if not isinstance(filings_data, dict):
            raise HTTPException(status_code=404, detail=f"No submissions found for: {ticker}")
        forms = filings_data.get("form", [])
        dates = filings_data.get("filingDate", [])
        accessions = filings_data.get("accessionNumber", [])
        documents = filings_data.get("primaryDocument", [])

        # Filter and format
        filings = []
        for i, form in enumerate(forms):
            if form == form_type and len(filings) < limit:
                filings.append({
                    "form": form,
                    "filing_date": dates[i] if i < len(dates) else None,
                    "accession": accessions[i] if i < len(accessions) else None,
                    "document": documents[i] if i < len(documents) else None,
                    "url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type={form_type}&dateb=&owner=include&count=40",
                })

        return {
            "ticker": ticker.upper(),
            "company_name": submissions.get("name", ticker),
            "cik": cik,
            "form_type": form_type,
            "filings": filings,
            "total_available": len([f for f in forms if f == form_type]),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")


@router.get("/material-changes")
def get_material_changes(
    ticker: str = Query(..., description="Stock ticker symbol"),
    form_type: str = Query("10-K", description="SEC form type"),
):
    """
    Get only material changes between the two most recent filings.

    Returns:
        List of high-materiality changes with context
    """
    try:
        result = get_filing_diff(
            ticker=ticker.upper(),
            form_type=form_type,
        )

        return {
            "ticker": ticker.upper(),
            "company_name": result.company_name,
            "form_type": form_type,
            "base_period": result.summary.get("base_period"),
            "compare_period": result.summary.get("compare_period"),
            "material_changes": [
                {
                    "section": c.section,
                    "field": c.field,
                    "context": c.context,
                    "old_value": c.old_value,
                    "new_value": c.new_value,
                    "delta_pct": c.delta_pct,
                }
                for c in result.material_changes
            ],
            "high_materiality_count": result.summary.get("high_materiality_changes", 0),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing changes: {str(e)}")


@router.get("/search")
def search_filings(
    query: str = Query(..., description="Search query"),
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    form_type: Optional[str] = Query(None, description="Filter by form type"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(20, description="Maximum results"),
):
    """
    Full-text search across SEC filings.

    Returns:
        Matching filings with snippets
    """
    try:
        from app.connectors.sec_edgar_connector import search_filings as sec_search
    except ImportError:
        return {
            "query": query,
            "results": [],
            "count": 0,
            "message": "Full-text filing search not yet available",
        }

    try:
        results = sec_search(
            query=query,
            ticker=ticker.upper() if ticker else None,
            form_types=[form_type] if form_type else None,
            start_date=start_date,
            end_date=end_date,
            max_results=limit,
        )

        return {
            "query": query,
            "filters": {
                "ticker": ticker,
                "form_type": form_type,
                "start_date": start_date,
                "end_date": end_date,
            },
            "results": results,
            "count": len(results) if results else 0,
        }
    except Exception as e:
        return {
            "query": query,
            "results": [],
            "count": 0,
            "error": str(e)[:200],
        }


# ── Company Ontology & KPI Routes ────────────────────────────────────────────────

@router.get("/ontology")
def get_company_ontology(
    ticker: str = Query(..., description="Stock ticker symbol"),
    include_kpis: bool = Query(True, description="Include KPI definitions"),
    include_entities: bool = Query(True, description="Include entity concepts"),
    include_terminology: bool = Query(True, description="Include terminology mapping"),
):
    """
    Get the complete ontology for a company.

    Returns:
        Company ontology with entities, KPIs, and terminology
    """
    from app.services.company_ontology_service import (
        build_company_ontology,
        ontology_to_dict,
    )

    try:
        ontology = build_company_ontology(
            ticker=ticker.upper(),
            include_kpis=include_kpis,
            include_entities=include_entities,
            include_terminology=include_terminology,
        )
        return ontology_to_dict(ontology)
    except (ValueError, ImportError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        return {
            "ticker": ticker.upper(),
            "ontology": {},
            "error": str(e)[:200],
            "message": "Ontology construction requires SEC filing data",
        }


@router.get("/kpis")
def get_company_kpis(
    ticker: str = Query(..., description="Stock ticker symbol"),
):
    """
    Get KPI dashboard for a company.

    Returns:
        All KPIs calculated with current values
    """
    from app.services.company_ontology_service import get_kpi_dashboard

    try:
        dashboard = get_kpi_dashboard(ticker.upper())
        return dashboard
    except (ValueError, ImportError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        return {
            "ticker": ticker.upper(),
            "kpis": [],
            "error": str(e)[:200],
            "message": "KPI calculation requires SEC filing data",
        }


# ── Docket-to-Disclosure Reconciliation Routes (L-series) ───────────────────────

@router.get("/litigation/reconcile")
def reconcile_litigation(
    ticker: str = Query(..., description="Stock ticker symbol"),
    lookback_years: int = Query(3, description="Years of litigation to analyze"),
):
    """
    Reconcile court dockets against SEC disclosures.

    THE KEY L-SERIES FEATURE: Identifies cases in public dockets
    that may not be properly disclosed in 10-K filings.

    Returns:
        Reconciliation report with findings and risk scores
    """
    from app.services.docket_disclosure_service import (
        reconcile_litigation as run_reconciliation,
        report_to_dict,
    )

    try:
        report = run_reconciliation(
            ticker=ticker.upper(),
            lookback_years=lookback_years,
        )
        return report_to_dict(report)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reconciling litigation: {str(e)}")


@router.get("/litigation/undisclosed")
def get_undisclosed_litigation(
    ticker: str = Query(..., description="Stock ticker symbol"),
):
    """
    Get potentially undisclosed litigation for a company.

    Returns only high-risk findings where court cases may not
    be properly disclosed in SEC filings.
    """
    from app.services.docket_disclosure_service import (
        reconcile_litigation as run_reconciliation,
        DisclosureStatus,
    )

    try:
        report = run_reconciliation(ticker=ticker.upper())

        # Filter to undisclosed or partial only
        undisclosed = [
            f for f in report.findings
            if f.disclosure_status in [DisclosureStatus.UNDISCLOSED, DisclosureStatus.PARTIAL]
            and f.risk_score >= 50
        ]

        return {
            "ticker": report.ticker,
            "company_name": report.company_name,
            "analysis_date": report.analysis_date,
            "undisclosed_findings": [
                {
                    "id": f.id,
                    "title": f.title,
                    "description": f.description,
                    "risk_score": f.risk_score,
                    "materiality": f.materiality.value,
                    "case_name": f.docket_case.case_name if f.docket_case else None,
                    "filed_date": f.docket_case.filed_date if f.docket_case else None,
                    "amount_claimed": f.docket_case.amount_claimed if f.docket_case else None,
                    "recommendations": f.recommendations,
                }
                for f in undisclosed
            ],
            "total_undisclosed": len(undisclosed),
            "overall_risk_score": report.risk_score,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing litigation: {str(e)}")


@router.get("/litigation/risk-score")
def get_litigation_risk_score(
    ticker: str = Query(..., description="Stock ticker symbol"),
):
    """
    Get quick litigation disclosure risk score for a company.

    Returns a 0-100 score indicating the risk of undisclosed
    or improperly disclosed litigation.
    """
    from app.services.docket_disclosure_service import (
        reconcile_litigation as run_reconciliation,
    )

    try:
        report = run_reconciliation(ticker=ticker.upper())

        return {
            "ticker": report.ticker,
            "company_name": report.company_name,
            "risk_score": report.risk_score,
            "risk_level": _get_risk_level(report.risk_score),
            "summary": report.summary,
            "analysis_date": report.analysis_date,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating risk: {str(e)}")


def _get_risk_level(score: float) -> str:
    """Convert risk score to level."""
    if score >= 80:
        return "CRITICAL"
    elif score >= 60:
        return "HIGH"
    elif score >= 40:
        return "MEDIUM"
    elif score >= 20:
        return "LOW"
    else:
        return "MINIMAL"
