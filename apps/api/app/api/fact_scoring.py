"""
Fact Scoring API — Source Reliability & Credibility Endpoints
"""

from fastapi import APIRouter, Query, Body, Depends
from typing import List, Optional
from pydantic import BaseModel

from app.auth.security import get_current_user
from app.services.fact_scoring_service import (
    get_source_reliability,
    score_fact,
    score_report,
    validate_claim,
    list_sources,
    get_tier_summary,
)

router = APIRouter(prefix="/fact-scoring", tags=["Fact Scoring"])


class FactScoreRequest(BaseModel):
    claim: str
    sources: List[str]
    data_age_hours: Optional[float] = None
    cross_references: int = 0
    has_primary_source: bool = False


class ReportSection(BaseModel):
    name: str
    content: str
    sources: List[str]
    data_age_hours: Optional[float] = None
    cross_references: int = 0
    has_primary_source: bool = False


class ReportScoreRequest(BaseModel):
    sections: List[ReportSection]


class ClaimValidationRequest(BaseModel):
    claim: str
    expected_sources: List[str]
    actual_data: dict


@router.get("/source/{source}")
def get_source_info(source: str):
    """Get reliability information for a specific data source."""
    return get_source_reliability(source)


@router.post("/score-fact")
def score_single_fact(request: FactScoreRequest, current_user: dict = Depends(get_current_user)):
    """Score the reliability of a single fact/claim based on its sources."""
    return score_fact(
        claim=request.claim,
        sources=request.sources,
        data_age_hours=request.data_age_hours,
        cross_references=request.cross_references,
        has_primary_source=request.has_primary_source,
    )


@router.post("/score-report")
def score_full_report(request: ReportScoreRequest, current_user: dict = Depends(get_current_user)):
    """Score an entire report's reliability based on all sections."""
    sections = [
        {
            "name": s.name,
            "content": s.content,
            "sources": s.sources,
            "data_age_hours": s.data_age_hours,
            "cross_references": s.cross_references,
            "has_primary_source": s.has_primary_source,
        }
        for s in request.sections
    ]
    return score_report(sections)


@router.post("/validate-claim")
def validate_single_claim(request: ClaimValidationRequest, current_user: dict = Depends(get_current_user)):
    """Validate a claim against actual data."""
    return validate_claim(
        claim=request.claim,
        expected_sources=request.expected_sources,
        actual_data=request.actual_data,
    )


@router.get("/sources")
def list_all_sources():
    """List all registered data sources with their reliability profiles."""
    return {"sources": list_sources()}


@router.get("/tiers")
def get_source_tiers():
    """Get summary of sources grouped by reliability tier."""
    return get_tier_summary()


@router.get("/quick-score")
def quick_score(
    sources: str = Query(..., description="Comma-separated list of sources"),
    data_age_hours: Optional[float] = Query(None, description="Age of data in hours"),
):
    """Quick reliability score based on sources used."""
    source_list = [s.strip() for s in sources.split(",")]
    return score_fact(
        claim="Quick score query",
        sources=source_list,
        data_age_hours=data_age_hours,
    )
