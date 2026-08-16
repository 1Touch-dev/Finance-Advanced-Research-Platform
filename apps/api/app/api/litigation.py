"""
Litigation Intelligence API (Band C #52-56)
────────────────────────────────────────────────────────────────────────────────
Endpoints:
- GET /litigation/{ticker}/enforcement - Enforcement events (#52)
- GET /litigation/{ticker}/event-study - Event study analysis (#52)
- GET /litigation/{ticker}/velocity - Docket velocity indicator (#53)
- GET /litigation/{ticker}/exposure - Normalized exposure (#54)
- GET /litigation/{ticker}/snapshot - Point-in-time snapshot (#55)
- GET /litigation/{ticker}/history - Historical time series (#55)
- GET /litigation/{ticker}/screener-fields - Screener fields (#56)
- POST /litigation/screen - Screen companies (#56)
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
import logging

from app.services.litigation_service import (
    get_enforcement_events,
    run_enforcement_event_study,
    calculate_docket_velocity,
    calculate_normalized_exposure,
    get_litigation_snapshot,
    get_litigation_time_series,
    get_screener_fields,
    screen_companies,
    EnforcementType,
    RiskLevel,
)

router = APIRouter(prefix="/litigation", tags=["litigation"])
logger = logging.getLogger(__name__)


# ── Reference Endpoints (MUST come before parameterized routes) ───────────────


@router.get("/types/enforcement")
async def list_enforcement_types():
    """List available enforcement event types."""
    return {
        "enforcement_types": [
            {"value": t.value, "name": t.name}
            for t in EnforcementType
        ],
    }


@router.get("/types/risk-levels")
async def list_risk_levels():
    """List available risk levels."""
    return {
        "risk_levels": [
            {"value": r.value, "name": r.name}
            for r in RiskLevel
        ],
    }


# ── #52: Enforcement Events ───────────────────────────────────────────────────


@router.get("/{ticker}/enforcement")
async def get_ticker_enforcement_events(
    ticker: str,
    years: int = Query(5, ge=1, le=10, description="Years to search back"),
    event_type: Optional[str] = Query(None, description="Filter by event type (sec, doj, ftc, ofac)"),
):
    """
    Get enforcement action events for a company (#52).

    Returns SEC, DOJ, FTC, and other regulatory enforcement actions.
    """
    ticker_upper = ticker.upper()

    # Parse event type filter
    event_types = None
    if event_type:
        try:
            event_types = [EnforcementType(event_type.lower())]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid event type: {event_type}")

    try:
        # Would normally resolve entity name from ticker
        entity_name = ticker_upper

        events = get_enforcement_events(
            ticker=ticker_upper,
            entity_name=entity_name,
            years=years,
            event_types=event_types,
        )

        return {
            "ticker": ticker_upper,
            "event_count": len(events),
            "events": [e.to_dict() for e in events],
        }
    except Exception as e:
        logger.error(f"Error getting enforcement events for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get enforcement events")


@router.get("/{ticker}/event-study")
async def run_ticker_event_study(
    ticker: str,
    event_window: int = Query(5, ge=1, le=20, description="Days before/after event"),
):
    """
    Run event study on enforcement actions (#52).

    Calculates abnormal returns around enforcement events using
    a simple market model approach.
    """
    ticker_upper = ticker.upper()

    try:
        entity_name = ticker_upper

        results = run_enforcement_event_study(
            ticker=ticker_upper,
            entity_name=entity_name,
            event_window=event_window,
        )

        # Calculate summary statistics
        negative_reactions = sum(1 for r in results if r.market_reaction and "negative" in r.market_reaction)
        positive_reactions = sum(1 for r in results if r.market_reaction and "positive" in r.market_reaction)

        return {
            "ticker": ticker_upper,
            "event_window": event_window,
            "event_count": len(results),
            "summary": {
                "negative_reactions": negative_reactions,
                "positive_reactions": positive_reactions,
                "neutral_reactions": len(results) - negative_reactions - positive_reactions,
            },
            "results": [r.to_dict() for r in results],
        }
    except Exception as e:
        logger.error(f"Error running event study for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Failed to run event study")


# ── #53: Docket Velocity ──────────────────────────────────────────────────────


@router.get("/{ticker}/velocity")
async def get_ticker_docket_velocity(
    ticker: str,
    period_days: int = Query(90, ge=30, le=365, description="Period to measure velocity"),
):
    """
    Get docket velocity indicator for a company (#53).

    Measures rate of new court filings to detect acceleration
    in litigation activity before it appears in disclosures.
    """
    ticker_upper = ticker.upper()

    try:
        entity_name = ticker_upper

        velocity = calculate_docket_velocity(
            ticker=ticker_upper,
            entity_name=entity_name,
            period_days=period_days,
        )

        return velocity.to_dict()
    except Exception as e:
        logger.error(f"Error getting docket velocity for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get docket velocity")


# ── #54: Normalized Exposure ──────────────────────────────────────────────────


@router.get("/{ticker}/exposure")
async def get_ticker_normalized_exposure(ticker: str):
    """
    Get litigation exposure normalized to financials (#54).

    Returns exposure as percentage of:
    - Annual revenue
    - Book equity
    - Cash position
    - Market cap
    - Total assets
    """
    ticker_upper = ticker.upper()

    try:
        entity_name = ticker_upper

        exposure = calculate_normalized_exposure(
            ticker=ticker_upper,
            entity_name=entity_name,
        )

        return exposure.to_dict()
    except Exception as e:
        logger.error(f"Error getting normalized exposure for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get normalized exposure")


# ── #55: Point-in-Time Litigation ─────────────────────────────────────────────


@router.get("/{ticker}/snapshot")
async def get_ticker_litigation_snapshot(
    ticker: str,
    as_of_date: Optional[str] = Query(None, description="Date for snapshot (YYYY-MM-DD)"),
):
    """
    Get point-in-time litigation snapshot (#55).

    Returns litigation state as of a specific date.
    """
    ticker_upper = ticker.upper()

    try:
        entity_name = ticker_upper

        snapshot = get_litigation_snapshot(
            ticker=ticker_upper,
            entity_name=entity_name,
            as_of_date=as_of_date,
        )

        return snapshot.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting litigation snapshot for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get litigation snapshot")


@router.get("/{ticker}/history")
async def get_ticker_litigation_history(
    ticker: str,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    frequency: str = Query("quarterly", description="Snapshot frequency (daily, weekly, monthly, quarterly)"),
):
    """
    Get historical litigation time series (#55).

    Returns a panel of point-in-time snapshots for trend analysis.
    """
    ticker_upper = ticker.upper()

    if frequency not in ["daily", "weekly", "monthly", "quarterly"]:
        raise HTTPException(status_code=400, detail="Invalid frequency. Use: daily, weekly, monthly, quarterly")

    try:
        entity_name = ticker_upper

        time_series = get_litigation_time_series(
            ticker=ticker_upper,
            entity_name=entity_name,
            start_date=start_date,
            end_date=end_date,
            frequency=frequency,
        )

        return time_series.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting litigation history for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get litigation history")


# ── #56: Screener Fields ──────────────────────────────────────────────────────


@router.get("/{ticker}/screener-fields")
async def get_ticker_screener_fields(ticker: str):
    """
    Get litigation screener fields for a company (#56).

    Returns all litigation metrics suitable for screening/filtering.
    """
    ticker_upper = ticker.upper()

    try:
        entity_name = ticker_upper

        fields = get_screener_fields(
            ticker=ticker_upper,
            entity_name=entity_name,
        )

        return fields.to_dict()
    except Exception as e:
        logger.error(f"Error getting screener fields for {ticker}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get screener fields")


@router.post("/screen")
async def screen_by_litigation(
    tickers: List[str] = Query(..., description="List of tickers to screen"),
    min_risk_score: Optional[float] = Query(None, ge=0, le=100),
    max_risk_score: Optional[float] = Query(None, ge=0, le=100),
    has_sec_enforcement: Optional[bool] = Query(None),
    has_class_action: Optional[bool] = Query(None),
    has_undisclosed: Optional[bool] = Query(None),
    min_exposure_pct: Optional[float] = Query(None, ge=0),
    max_exposure_pct: Optional[float] = Query(None, ge=0),
    risk_level: Optional[str] = Query(None, description="Filter by risk level (critical, high, medium, low, minimal)"),
):
    """
    Screen companies by litigation criteria (#56).

    Filters a list of companies based on litigation risk metrics.
    """
    # Parse risk level filter
    risk_levels = None
    if risk_level:
        try:
            risk_levels = [RiskLevel(risk_level.lower())]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid risk level: {risk_level}")

    try:
        results = screen_companies(
            tickers=[t.upper() for t in tickers],
            min_risk_score=min_risk_score,
            max_risk_score=max_risk_score,
            has_sec_enforcement=has_sec_enforcement,
            has_class_action=has_class_action,
            has_undisclosed=has_undisclosed,
            min_exposure_pct=min_exposure_pct,
            max_exposure_pct=max_exposure_pct,
            risk_levels=risk_levels,
        )

        return {
            "screened_count": len(results),
            "total_input": len(tickers),
            "results": [r.to_dict() for r in results],
        }
    except Exception as e:
        logger.error(f"Error screening companies: {e}")
        raise HTTPException(status_code=500, detail="Failed to screen companies")
