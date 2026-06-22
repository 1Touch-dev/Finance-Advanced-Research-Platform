"""
Layer 1 Intelligence Report API
POST /intelligence/generate  — run connectors for an entity, build graph, generate cited dossier
GET  /intelligence/{report_id} — retrieve a generated intelligence report
GET  /intelligence/            — list recent intelligence reports
"""
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, Dict, Any, List
from app.db.session import get_db
from app.services.intelligence_service import generate_intelligence_report, get_intelligence_report, list_intelligence_reports

try:
    from app.connectors.browser_research_agent import research_entity_browser, detect_jurisdiction
    _BROWSER_AVAILABLE = True
except ImportError:
    _BROWSER_AVAILABLE = False

router = APIRouter(prefix="/intelligence")


@router.post("/generate")
def generate_report(
    entity_name: str,
    entity_type: str = "org",
    ticker: Optional[str] = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
):
    """
    Kick off a Layer 1 Entity Network Intelligence Report.
    Runs connectors (SEC, FEC, FARA, USASpending, LDA, OFAC, CourtListener),
    writes relationships + evidence, assembles report JSON, generates GPT narrative.
    Returns report_id immediately; report builds synchronously for demo.
    """
    report = generate_intelligence_report(db, entity_name=entity_name, entity_type=entity_type, ticker=ticker)
    return report


@router.post("/browser-research")
def browser_research(
    entity_name: str,
    jurisdiction: Optional[str] = None,
    context: str = "",
    deep_dive: bool = False,
):
    """
    Run browser-based research on an entity using public registries, news, and
    government sources for any jurisdiction (used as fallback for non-US entities
    or for deep dives on holding companies, vehicles, financials).

    Examples:
      POST /intelligence/browser-research?entity_name=Aeropuertos+Argentina+2000&jurisdiction=argentina
      POST /intelligence/browser-research?entity_name=Mercado+Libre&deep_dive=true
    """
    if not _BROWSER_AVAILABLE:
        raise HTTPException(503, "Browser research agent not available")
    detected_jur = jurisdiction or detect_jurisdiction(entity_name, context)
    result = research_entity_browser(
        entity_name,
        jurisdiction=detected_jur,
        context=context,
        max_sources=6 if deep_dive else 4,
        deep_dive=deep_dive,
    )
    return result


@router.get("/")
def list_reports(limit: int = 20, db: Session = Depends(get_db)):
    return list_intelligence_reports(db, limit=limit)


@router.get("/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = get_intelligence_report(db, report_id)
    if not report:
        raise HTTPException(404, "Intelligence report not found")
    return report
