"""
Company-Specific Ontology + KPI Schema API (Band B #16)

Endpoints:
- GET /ontology/{ticker} - Get company ontology
- GET /ontology/{ticker}/kpis - Get company KPIs
- GET /ontology/{ticker}/kpi/{kpi_id} - Calculate specific KPI
- GET /ontology/{ticker}/entities - Get extracted entities
- GET /ontology/industries - Get available industry templates
- GET /ontology/industries/{industry}/kpis - Get industry KPI templates
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
import logging

from app.services.company_ontology_service import (
    build_company_ontology,
    get_kpi_dashboard,
    calculate_kpi,
    ontology_to_dict,
    UpstreamUnavailable,
    INDUSTRY_KPI_TEMPLATES,
    SIC_TO_INDUSTRY,
)

router = APIRouter(prefix="/ontology", tags=["ontology"])
logger = logging.getLogger(__name__)


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/{ticker}")
def get_company_ontology(
    ticker: str,
    include_kpis: bool = True,
    include_entities: bool = True,
    include_terminology: bool = False
):
    """
    Get full ontology for a company.

    Extracts:
    - KPI definitions and values
    - Entity concepts (segments, products, regions)
    - Company-specific terminology mapping
    """
    try:
        ontology = build_company_ontology(
            ticker=ticker.upper(),
            include_kpis=include_kpis,
            include_entities=include_entities,
            include_terminology=include_terminology,
        )
        return ontology_to_dict(ontology)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UpstreamUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Error building ontology for %s", ticker)
        raise HTTPException(status_code=500, detail=f"Failed to build ontology: {e}")


@router.get("/{ticker}/kpis")
def get_company_kpis(ticker: str):
    """
    Get KPI dashboard for a company.

    Returns all tracked KPIs with current values and trends.
    """
    try:
        dashboard = get_kpi_dashboard(ticker.upper())
        return dashboard
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UpstreamUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Error getting KPIs for %s", ticker)
        raise HTTPException(status_code=500, detail=f"Failed to get KPIs: {e}")


@router.get("/{ticker}/kpi/{kpi_id}")
def calculate_company_kpi(
    ticker: str,
    kpi_id: str,
    period: Optional[str] = Query(None, description="Fiscal period (e.g., '2024Q4', '2024FY')")
):
    """
    Calculate a specific KPI for a company.
    """
    try:
        # calculate_kpi() takes a resolved KPIDefinition plus the financial data;
        # it was previously called as calculate_kpi(ticker, kpi_id), which raised
        # "'str' object has no attribute 'formula'" on every request.
        ontology = build_company_ontology(
            ticker=ticker.upper(),
            include_kpis=True,
            include_entities=False,
            include_terminology=False,
        )
        kpi = next((k for k in ontology.kpis if k.id == kpi_id), None)
        if kpi is None:
            raise HTTPException(
                status_code=404,
                detail=f"KPI {kpi_id!r} not defined for {ticker.upper()}; "
                       f"see GET /ontology/{ticker.upper()}/kpis",
            )

        from app.connectors.sec_edgar_connector import (
            get_company_facts,
            extract_financial_statements,
        )
        # extract_financial_statements() takes XBRL company facts, not a CIK.
        facts = get_company_facts(ontology.cik) or {}
        financial_data = extract_financial_statements(facts) or {}

        result = calculate_kpi(kpi, financial_data, period=period or "latest")
        if result is None:
            return {
                "ticker": ontology.ticker,
                "kpi_id": kpi_id,
                "value": None,
                "no_data": True,
                "reason": "KPI has neither a formula nor XBRL concepts, "
                          "or the required facts are absent from the filing",
            }
        return result
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UpstreamUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Error calculating KPI %s for %s", kpi_id, ticker)
        raise HTTPException(status_code=500, detail=f"Failed to calculate KPI: {e}")


@router.get("/{ticker}/entities")
def get_company_entities(ticker: str):
    """
    Get extracted entity concepts for a company.

    Includes segments, products, regions, customers, competitors, etc.
    """
    try:
        ontology = build_company_ontology(
            ticker=ticker.upper(),
            include_kpis=False,
            include_entities=True,
            include_terminology=False,
        )
        return {
            "ticker": ontology.ticker,
            "company_name": ontology.company_name,
            "entities": [
                {
                    "id": e.id,
                    "name": e.name,
                    "aliases": e.aliases,
                    "entity_type": e.entity_type,
                    "attributes": e.attributes,
                    "confidence": e.confidence,
                }
                for e in ontology.entities
            ],
            "total": len(ontology.entities),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except UpstreamUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception("Error getting entities for %s", ticker)
        raise HTTPException(status_code=500, detail=f"Failed to get entities: {e}")


@router.get("/reference/industries")
def list_industries():
    """
    Get list of available industry templates with KPI counts.
    """
    industries = []
    for industry, kpis in INDUSTRY_KPI_TEMPLATES.items():
        industries.append({
            "industry": industry,
            "kpi_count": len(kpis),
            "kpi_names": [k.name for k in kpis],
        })

    return {
        "industries": industries,
        "total": len(industries),
        "sic_mappings": SIC_TO_INDUSTRY,
    }


@router.get("/reference/industries/{industry}/kpis")
def get_industry_kpi_templates(industry: str):
    """
    Get KPI templates for a specific industry.
    """
    industry_lower = industry.lower()
    if industry_lower not in INDUSTRY_KPI_TEMPLATES:
        raise HTTPException(
            status_code=404,
            detail=f"Industry '{industry}' not found. Available: {list(INDUSTRY_KPI_TEMPLATES.keys())}"
        )

    kpis = INDUSTRY_KPI_TEMPLATES[industry_lower]
    return {
        "industry": industry_lower,
        "kpis": [
            {
                "id": k.id,
                "name": k.name,
                "description": k.description,
                "metric_type": k.metric_type.value,
                "unit": k.unit,
                "frequency": k.frequency.value,
                "higher_is_better": k.higher_is_better,
                "industry_benchmark": k.industry_benchmark,
                "formula": k.formula,
            }
            for k in kpis
        ],
        "total": len(kpis),
    }
