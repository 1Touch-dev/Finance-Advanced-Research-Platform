"""
Custom Formula & Expression Charting API (Band B #26)

Endpoints:
- POST /formula/evaluate - Evaluate a formula
- POST /formula/validate - Validate formula syntax
- GET /formula/list - List saved formulas
- POST /formula/save - Save a formula
- DELETE /formula/{id} - Delete a formula
- GET /formula/metrics - Get available metrics
- GET /formula/functions - Get available functions
"""

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from app.services.formula_service import get_formula_service

router = APIRouter(prefix="/formula", tags=["formula"])


# ── Request/Response Models ──────────────────────────────────────────────────

class EvaluateRequest(BaseModel):
    formula: str
    tickers: Optional[List[str]] = None
    days: int = 252


class SaveFormulaRequest(BaseModel):
    name: str
    formula: str
    description: str = ""
    category: str = "custom"
    tickers: Optional[List[str]] = None


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/evaluate")
async def evaluate_formula(request: EvaluateRequest):
    """Evaluate a formula and return chart data."""
    service = get_formula_service()

    result = service.evaluate_formula(
        formula=request.formula,
        tickers=request.tickers,
        days=request.days
    )

    return result.to_dict()


@router.get("/validate")
async def validate_formula(formula: str = Query(...)):
    """Validate formula syntax without evaluating."""
    service = get_formula_service()
    validation = service.validate_formula(formula)
    return validation.to_dict()


@router.get("/list")
async def list_formulas(category: Optional[str] = None):
    """List all saved formulas."""
    service = get_formula_service()
    formulas = service.list_formulas(category=category)
    return {
        "formulas": [f.to_dict() for f in formulas],
        "count": len(formulas),
    }


@router.post("/save")
async def save_formula(request: SaveFormulaRequest):
    """Save a custom formula."""
    service = get_formula_service()

    # Validate first
    validation = service.validate_formula(request.formula)
    if not validation.valid:
        raise HTTPException(status_code=400, detail={"errors": validation.errors})

    saved = service.save_formula(
        name=request.name,
        formula=request.formula,
        description=request.description,
        category=request.category,
        tickers=request.tickers,
    )

    return saved.to_dict()


@router.get("/{formula_id}")
async def get_formula(formula_id: str):
    """Get a saved formula by ID."""
    service = get_formula_service()
    formula = service.get_formula(formula_id)

    if not formula:
        raise HTTPException(status_code=404, detail="Formula not found")

    return formula.to_dict()


@router.delete("/{formula_id}")
async def delete_formula(formula_id: str):
    """Delete a saved formula."""
    service = get_formula_service()
    success = service.delete_formula(formula_id)

    if not success:
        raise HTTPException(status_code=404, detail="Formula not found or is a preset")

    return {"deleted": True, "id": formula_id}


@router.get("/reference/metrics")
async def get_available_metrics():
    """Get list of available metrics for formulas."""
    service = get_formula_service()
    return {
        "metrics": service.get_available_metrics(),
    }


@router.get("/reference/functions")
async def get_available_functions():
    """Get list of available functions for formulas."""
    service = get_formula_service()
    return {
        "functions": service.get_available_functions(),
    }
