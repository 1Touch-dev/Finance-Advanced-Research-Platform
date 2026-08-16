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
    INDUSTRY_KPI_TEMPLATES,
    SIC_TO_INDUSTRY,
)

router = APIRouter(prefix="/ontology", tags=["ontology"])
logger = logging.getLogger(__name__)


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/{ticker}")
async def get_company_ontology(
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
    except Exception as e:
        logger.error(f"Error building ontology for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Failed to build ontology")


@router.get("/{ticker}/kpis")
async def get_company_kpis(ticker: str):
    """
    Get KPI dashboard for a company.

    Returns all tracked KPIs with current values and trends.
    """
    try:
        dashboard = get_kpi_dashboard(ticker.upper())
        return dashboard
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting KPIs for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get KPIs")


@router.get("/{ticker}/kpi/{kpi_id}")
async def calculate_company_kpi(
    ticker: str,
    kpi_id: str,
    period: Optional[str] = Query(None, description="Fiscal period (e.g., '2024Q4', '2024FY')")
):
    """
    Calculate a specific KPI for a company.
    """
    try:
        result = calculate_kpi(ticker.upper(), kpi_id, period=period)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error calculating KPI {kpi_id} for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Failed to calculate KPI")


@router.get("/{ticker}/entities")
async def get_company_entities(ticker: str):
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
    except Exception as e:
        logger.error(f"Error getting entities for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get entities")


@router.get("/reference/industries")
async def list_industries():
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
async def get_industry_kpi_templates(industry: str):
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
