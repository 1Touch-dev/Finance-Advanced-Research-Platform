"""
Model & Idea Leaderboards API (Band B #30)

Endpoints:
- GET /leaderboard/predictions - Get prediction leaderboard
- GET /leaderboard/ideas - Get idea leaderboard
- POST /leaderboard/predict - Submit a prediction
- POST /leaderboard/idea - Submit an idea
- GET /leaderboard/user/{user_id} - Get user score
- GET /leaderboard/calibration/{user_id} - Get user calibration
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from app.services.leaderboard_service import get_leaderboard_service
from app.auth.security import get_current_user

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


# ── Request Models ───────────────────────────────────────────────────────────

class PredictionRequest(BaseModel):
    user_id: str
    ticker: str
    prediction_type: str  # 'earnings_beat', 'price_target', 'direction'
    predicted_value: float
    confidence: float  # 0-1
    target_date: str  # YYYY-MM-DD


class IdeaRequest(BaseModel):
    user_id: str
    ticker: str
    direction: str  # 'long', 'short'
    thesis: str
    entry_price: float
    target_price: float
    stop_price: float
    time_horizon_days: int = 30


class ResolvePredictionRequest(BaseModel):
    prediction_id: str
    actual_value: float


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/predictions")
def get_prediction_leaderboard(
    metric: str = Query("brier", enum=["brier", "accuracy", "calibration"]),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None
):
    """
    Get prediction leaderboard.

    Ranks users by:
    - brier: Brier score (probabilistic accuracy)
    - accuracy: Simple accuracy rate
    - calibration: How well-calibrated predictions are
    """
    service = get_leaderboard_service()
    leaderboard = service.get_leaderboard(
        metric=metric,
        limit=limit,
        category=category
    )

    return {
        "leaderboard": [e.to_dict() for e in leaderboard],
        "metric": metric,
        "count": len(leaderboard),
    }


@router.get("/ideas")
def get_idea_leaderboard(
    limit: int = Query(20, ge=1, le=100)
):
    """
    Get trading idea leaderboard.

    Ranks ideas by P&L performance.
    """
    service = get_leaderboard_service()
    ideas = service.get_idea_leaderboard(limit=limit)

    return {
        "ideas": ideas,
        "count": len(ideas),
    }


@router.post("/predict")
def submit_prediction(request: PredictionRequest, current_user: dict = Depends(get_current_user)):
    """
    Submit a new prediction.

    Predictions are scored when resolved using Brier scoring.
    """
    service = get_leaderboard_service()

    if not 0 < request.confidence < 1:
        raise HTTPException(
            status_code=400,
            detail="Confidence must be between 0 and 1 (exclusive)"
        )

    prediction = service.submit_prediction(
        user_id=request.user_id,
        ticker=request.ticker,
        prediction_type=request.prediction_type,
        predicted_value=request.predicted_value,
        confidence=request.confidence,
        target_date=request.target_date,
    )

    return prediction.to_dict()


@router.post("/resolve")
def resolve_prediction(request: ResolvePredictionRequest, current_user: dict = Depends(get_current_user)):
    """
    Resolve a pending prediction with actual outcome.
    """
    service = get_leaderboard_service()

    prediction = service.resolve_prediction(
        prediction_id=request.prediction_id,
        actual_value=request.actual_value,
    )

    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")

    return prediction.to_dict()


@router.post("/idea")
def submit_idea(request: IdeaRequest, current_user: dict = Depends(get_current_user)):
    """
    Submit a trading idea.

    Ideas are tracked and scored based on price movement
    relative to entry, target, and stop prices.
    """
    service = get_leaderboard_service()

    if request.direction not in ['long', 'short']:
        raise HTTPException(
            status_code=400,
            detail="Direction must be 'long' or 'short'"
        )

    idea = service.submit_idea(
        user_id=request.user_id,
        ticker=request.ticker,
        direction=request.direction,
        thesis=request.thesis,
        entry_price=request.entry_price,
        target_price=request.target_price,
        stop_price=request.stop_price,
        time_horizon_days=request.time_horizon_days,
    )

    return idea.to_dict()


@router.get("/user/{user_id}")
def get_user_score(user_id: str):
    """
    Get aggregated score for a user.

    Returns accuracy, Brier score, calibration, tier, badges, and streaks.
    """
    service = get_leaderboard_service()
    score = service.get_user_score(user_id)

    if not score:
        raise HTTPException(status_code=404, detail="User not found")

    return score.to_dict()


@router.get("/calibration/{user_id}")
def get_user_calibration(user_id: str):
    """
    Get calibration analysis for a user.

    Shows how well user's confidence levels match actual outcomes.
    Perfect calibration means 70% confident predictions
    are correct 70% of the time.
    """
    service = get_leaderboard_service()
    calibration = service.get_user_calibration(user_id)

    return calibration.to_dict()


@router.get("/tiers")
def get_tier_definitions():
    """
    Get tier definitions and thresholds.
    """
    return {
        "tiers": [
            {
                "name": "elite",
                "threshold": 0.90,
                "description": "Top performers with exceptional accuracy and calibration"
            },
            {
                "name": "expert",
                "threshold": 0.75,
                "description": "Highly skilled predictors with consistent track record"
            },
            {
                "name": "proficient",
                "threshold": 0.50,
                "description": "Solid performers showing reliable judgment"
            },
            {
                "name": "novice",
                "threshold": 0.00,
                "description": "Building track record - keep predicting!"
            },
        ],
        "scoring": {
            "brier": "Lower is better (0 = perfect, 1 = worst)",
            "accuracy": "Percentage of correct predictions",
            "calibration": "How well confidence matches outcomes",
        },
        "minimum_predictions": 10,
    }
