"""
Estimate Revision Screener API (Band C #37)
────────────────────────────────────────────────────────────────────────────────
Endpoints:
- POST /revisions/screen - Screen companies by revision criteria
- GET /revisions/top-upward - Top upward revisions
- GET /revisions/top-downward - Top downward revisions
- GET /revisions/accelerating - Accelerating revisions
- GET /revisions/alerts - Revision alerts
- GET /revisions/summary - Revision summary statistics
"""

from fastapi import APIRouter, Query, HTTPException, Depends
from typing import Optional, List
import logging
from app.auth.security import get_current_user

from app.services.revision_screener_service import (
    screen_by_revisions,
    get_top_upward_revisions,
    get_top_downward_revisions,
    get_accelerating_revisions,
    get_revision_alerts,
    get_revision_summary,
    RevisionTrend,
    ScreenerSortBy,
)
from app.services.consensus_service import (
    EstimateType,
    PeriodType,
)

router = APIRouter(prefix="/revisions", tags=["revisions"])
logger = logging.getLogger(__name__)


# ── Reference Endpoints (MUST come before parameterized routes) ───────────────


@router.get("/types/estimate-types")
def list_estimate_types():
    """List available estimate types for screening."""
    return {
        "estimate_types": [
            {"value": t.value, "name": t.name}
            for t in EstimateType
        ],
    }


@router.get("/types/periods")
def list_periods():
    """List available fiscal periods."""
    return {
        "periods": [
            {"value": p.value, "name": p.name}
            for p in PeriodType
        ],
    }


@router.get("/types/trends")
def list_trend_classifications():
    """List revision trend classifications."""
    return {
        "trend_classifications": [
            {"value": t.value, "name": t.name}
            for t in RevisionTrend
        ],
    }


@router.get("/types/sort-options")
def list_sort_options():
    """List available sort options for screener."""
    return {
        "sort_options": [
            {"value": s.value, "name": s.name}
            for s in ScreenerSortBy
        ],
    }


# ── Screener Endpoints ─────────────────────────────────────────────────────────


@router.post("/screen")
def screen_revisions(
    tickers: Optional[List[str]] = Query(None, description="Tickers to screen (default: all)"),
    estimate_type: str = Query("eps", description="Estimate type (eps, revenue, ebitda, etc.)"),
    fiscal_period: str = Query("FY", description="Fiscal period (Q1-Q4, FY)"),
    # Momentum filters
    min_momentum_7d: Optional[float] = Query(None, description="Minimum 7-day momentum %"),
    max_momentum_7d: Optional[float] = Query(None, description="Maximum 7-day momentum %"),
    min_momentum_30d: Optional[float] = Query(None, description="Minimum 30-day momentum %"),
    max_momentum_30d: Optional[float] = Query(None, description="Maximum 30-day momentum %"),
    min_momentum_90d: Optional[float] = Query(None, description="Minimum 90-day momentum %"),
    max_momentum_90d: Optional[float] = Query(None, description="Maximum 90-day momentum %"),
    # Trend filter
    trend_classification: Optional[str] = Query(None, description="Trend classification filter"),
    # Signal strength
    min_signal_strength: Optional[float] = Query(None, ge=0, le=100, description="Minimum signal strength"),
    # Revision counts
    min_revisions_up: Optional[int] = Query(None, ge=0, description="Minimum upward revisions (30d)"),
    min_revisions_down: Optional[int] = Query(None, ge=0, description="Minimum downward revisions (30d)"),
    # Dispersion
    include_dispersion: bool = Query(False, description="Include dispersion metrics"),
    # Sort and limit
    sort_by: str = Query("momentum_30d", description="Sort field"),
    sort_ascending: bool = Query(False, description="Sort ascending"),
    limit: int = Query(50, ge=1, le=500, description="Maximum results"),
):
    """
    Screen companies by estimate revision criteria (#37).

    Filters companies based on consensus momentum, revision counts,
    trend classification, and signal strength.
    """
    # Parse estimate type
    try:
        est_type = EstimateType(estimate_type.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid estimate type: {estimate_type}")

    # Parse fiscal period
    try:
        period = PeriodType(fiscal_period.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid fiscal period: {fiscal_period}")

    # Parse trend classification if provided
    trend_classifications = None
    if trend_classification:
        try:
            trend_classifications = [RevisionTrend(trend_classification.lower())]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid trend classification: {trend_classification}")

    # Parse sort_by
    try:
        sort_field = ScreenerSortBy(sort_by.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid sort field: {sort_by}")

    try:
        result = screen_by_revisions(
            tickers=[t.upper() for t in tickers] if tickers else None,
            estimate_type=est_type,
            fiscal_period=period,
            min_momentum_7d=min_momentum_7d,
            max_momentum_7d=max_momentum_7d,
            min_momentum_30d=min_momentum_30d,
            max_momentum_30d=max_momentum_30d,
            min_momentum_90d=min_momentum_90d,
            max_momentum_90d=max_momentum_90d,
            trend_classifications=trend_classifications,
            min_signal_strength=min_signal_strength,
            min_revisions_up_30d=min_revisions_up,
            min_revisions_down_30d=min_revisions_down,
            include_dispersion=include_dispersion,
            sort_by=sort_field,
            sort_ascending=sort_ascending,
            limit=limit,
        )

        return result.to_dict()

    except Exception as e:
        logger.error(f"Error screening revisions: {e}")
        raise HTTPException(status_code=500, detail="Failed to screen revisions")


@router.get("/top-upward")
def get_top_upward(
    estimate_type: str = Query("eps", description="Estimate type"),
    fiscal_period: str = Query("FY", description="Fiscal period"),
    limit: int = Query(10, ge=1, le=100, description="Number of results"),
):
    """
    Get companies with strongest upward estimate revisions (#37).

    Returns companies ranked by positive 30-day momentum.
    """
    # Parse estimate type
    try:
        est_type = EstimateType(estimate_type.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid estimate type: {estimate_type}")

    # Parse fiscal period
    try:
        period = PeriodType(fiscal_period.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid fiscal period: {fiscal_period}")

    try:
        result = get_top_upward_revisions(
            estimate_type=est_type,
            fiscal_period=period,
            limit=limit,
        )
        return result.to_dict()

    except Exception as e:
        logger.error(f"Error getting top upward revisions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get top upward revisions")


@router.get("/top-downward")
def get_top_downward(
    estimate_type: str = Query("eps", description="Estimate type"),
    fiscal_period: str = Query("FY", description="Fiscal period"),
    limit: int = Query(10, ge=1, le=100, description="Number of results"),
):
    """
    Get companies with strongest downward estimate revisions (#37).

    Returns companies ranked by negative 30-day momentum.
    """
    # Parse estimate type
    try:
        est_type = EstimateType(estimate_type.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid estimate type: {estimate_type}")

    # Parse fiscal period
    try:
        period = PeriodType(fiscal_period.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid fiscal period: {fiscal_period}")

    try:
        result = get_top_downward_revisions(
            estimate_type=est_type,
            fiscal_period=period,
            limit=limit,
        )
        return result.to_dict()

    except Exception as e:
        logger.error(f"Error getting top downward revisions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get top downward revisions")


@router.get("/accelerating")
def get_accelerating(
    direction: str = Query("up", description="Direction: up or down"),
    estimate_type: str = Query("eps", description="Estimate type"),
    fiscal_period: str = Query("FY", description="Fiscal period"),
    limit: int = Query(10, ge=1, le=100, description="Number of results"),
):
    """
    Get companies with accelerating revisions (#37).

    Finds companies where recent momentum exceeds longer-term momentum,
    indicating acceleration in revision activity.
    """
    if direction not in ["up", "down"]:
        raise HTTPException(status_code=400, detail="Direction must be 'up' or 'down'")

    # Parse estimate type
    try:
        est_type = EstimateType(estimate_type.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid estimate type: {estimate_type}")

    # Parse fiscal period
    try:
        period = PeriodType(fiscal_period.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid fiscal period: {fiscal_period}")

    try:
        result = get_accelerating_revisions(
            direction=direction,
            estimate_type=est_type,
            fiscal_period=period,
            limit=limit,
        )
        return result.to_dict()

    except Exception as e:
        logger.error(f"Error getting accelerating revisions: {e}")
        raise HTTPException(status_code=500, detail="Failed to get accelerating revisions")


@router.get("/alerts")
def get_alerts(
    tickers: Optional[List[str]] = Query(None, description="Tickers to check (default: all)"),
    estimate_type: str = Query("eps", description="Estimate type"),
    fiscal_period: str = Query("FY", description="Fiscal period"),
    momentum_threshold: float = Query(5.0, ge=1.0, le=20.0, description="Momentum spike threshold %"),
):
    """
    Get revision alerts for significant changes (#37).

    Detects:
    - Momentum spikes (sudden large revision changes)
    - Trend reversals (direction changes)
    - High dispersion (analyst disagreement)
    """
    # Parse estimate type
    try:
        est_type = EstimateType(estimate_type.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid estimate type: {estimate_type}")

    # Parse fiscal period
    try:
        period = PeriodType(fiscal_period.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid fiscal period: {fiscal_period}")

    try:
        alerts = get_revision_alerts(
            tickers=[t.upper() for t in tickers] if tickers else None,
            estimate_type=est_type,
            fiscal_period=period,
            momentum_spike_threshold=momentum_threshold,
        )

        return {
            "alert_count": len(alerts),
            "alerts": [a.to_dict() for a in alerts],
        }

    except Exception as e:
        logger.error(f"Error getting revision alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get revision alerts")


@router.get("/summary")
def get_summary(
    tickers: Optional[List[str]] = Query(None, description="Tickers to summarize (default: all)"),
    estimate_type: str = Query("eps", description="Estimate type"),
    fiscal_period: str = Query("FY", description="Fiscal period"),
):
    """
    Get revision summary statistics (#37).

    Returns aggregate metrics for the screened universe including
    direction breakdown and momentum statistics.
    """
    # Parse estimate type
    try:
        est_type = EstimateType(estimate_type.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid estimate type: {estimate_type}")

    # Parse fiscal period
    try:
        period = PeriodType(fiscal_period.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid fiscal period: {fiscal_period}")

    try:
        summary = get_revision_summary(
            tickers=[t.upper() for t in tickers] if tickers else None,
            estimate_type=est_type,
            fiscal_period=period,
        )
        return summary

    except Exception as e:
        logger.error(f"Error getting revision summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get revision summary")
