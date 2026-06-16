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


@router.get("/")
def list_reports(limit: int = 20, db: Session = Depends(get_db)):
    return list_intelligence_reports(db, limit=limit)


@router.get("/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = get_intelligence_report(db, report_id)
    if not report:
        raise HTTPException(404, "Intelligence report not found")
    return report
