"""
Consensus & Earnings API Routes (Band B #19-#21, #23)
────────────────────────────────────────────────────────────────────────────
Provides endpoints for:
  - Point-in-time consensus snapshots
  - Consensus revision history and momentum
  - Estimate dispersion analysis
  - Earnings surprise history
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from datetime import date, datetime

from app.services.consensus_service import (
    # Enums
    EstimateType,
    PeriodType,
    # Functions
    get_consensus_snapshot,
    get_rolling_consensus,
    get_consensus_revisions,
    get_consensus_momentum,
    get_estimate_dispersion,
    get_earnings_surprise,
    get_surprise_history,
    # Serializers
    consensus_snapshot_to_dict,
    revision_to_dict,
    momentum_to_dict,
    dispersion_to_dict,
    surprise_to_dict,
    surprise_history_to_dict,
)

router = APIRouter(prefix="/consensus")


# ── Point-in-Time Consensus ────────────────────────────────────────────────────

@router.get("/snapshot")
def get_pit_consensus(
    ticker: str = Query(..., description="Stock ticker symbol"),
    estimate_type: str = Query("eps", description="Estimate type (eps, revenue, ebitda)"),
    fiscal_year: Optional[int] = Query(None, description="Fiscal year"),
    fiscal_period: str = Query("FY", description="Fiscal period (Q1, Q2, Q3, Q4, FY)"),
    as_of_date: Optional[str] = Query(None, description="Point-in-time date (YYYY-MM-DD)"),
):
    """
    Get consensus snapshot as of a specific date.

    THE KEY FEATURE: Returns consensus as-it-was, not revised.
    """
    try:
        est_type = EstimateType(estimate_type.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid estimate type: {estimate_type}")

    try:
        period = PeriodType(fiscal_period.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid fiscal period: {fiscal_period}")

    as_of = None
    if as_of_date:
        try:
            as_of = datetime.strptime(as_of_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    try:
        snapshot = get_consensus_snapshot(
            ticker=ticker,
            estimate_type=est_type,
            fiscal_year=fiscal_year,
            fiscal_period=period,
            as_of_date=as_of,
        )
        return consensus_snapshot_to_dict(snapshot)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching consensus: {str(e)}")


@router.get("/rolling")
def get_consensus_history(
    ticker: str = Query(..., description="Stock ticker symbol"),
    estimate_type: str = Query("eps", description="Estimate type"),
    fiscal_year: Optional[int] = Query(None, description="Fiscal year"),
    fiscal_period: str = Query("FY", description="Fiscal period"),
    lookback_days: int = Query(180, description="Days of history"),
):
    """
    Get rolling consensus history showing evolution over time.

    Returns weekly snapshots to show how consensus changed.
    """
    try:
        est_type = EstimateType(estimate_type.lower())
        period = PeriodType(fiscal_period.upper())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        snapshots = get_rolling_consensus(
            ticker=ticker,
            estimate_type=est_type,
            fiscal_year=fiscal_year,
            fiscal_period=period,
            lookback_days=lookback_days,
        )
        return {
            "ticker": ticker.upper(),
            "estimate_type": estimate_type,
            "fiscal_year": fiscal_year or date.today().year,
            "fiscal_period": fiscal_period,
            "snapshots": [consensus_snapshot_to_dict(s) for s in snapshots],
            "count": len(snapshots),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")


# ── Revisions & Momentum ───────────────────────────────────────────────────────

@router.get("/revisions")
def get_revisions(
    ticker: str = Query(..., description="Stock ticker symbol"),
    estimate_type: str = Query("eps", description="Estimate type"),
    fiscal_year: Optional[int] = Query(None, description="Fiscal year"),
    fiscal_period: str = Query("FY", description="Fiscal period"),
    days: int = Query(90, description="Days of revision history"),
):
    """
    Get consensus revision history.

    Shows how analyst estimates have changed over time.
    """
    try:
        est_type = EstimateType(estimate_type.lower())
        period = PeriodType(fiscal_period.upper())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        revisions = get_consensus_revisions(
            ticker=ticker,
            estimate_type=est_type,
            fiscal_year=fiscal_year,
            fiscal_period=period,
            days=days,
        )

        # Calculate summary
        ups = sum(1 for r in revisions if r.direction.value == "up")
        downs = sum(1 for r in revisions if r.direction.value == "down")

        return {
            "ticker": ticker.upper(),
            "estimate_type": estimate_type,
            "fiscal_year": fiscal_year or date.today().year,
            "fiscal_period": fiscal_period,
            "summary": {
                "total_revisions": len(revisions),
                "revisions_up": ups,
                "revisions_down": downs,
                "net_direction": "bullish" if ups > downs else "bearish" if downs > ups else "neutral",
            },
            "revisions": [revision_to_dict(r) for r in revisions],
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching revisions: {str(e)}")


@router.get("/momentum")
def get_momentum(
    ticker: str = Query(..., description="Stock ticker symbol"),
    estimate_type: str = Query("eps", description="Estimate type"),
    fiscal_year: Optional[int] = Query(None, description="Fiscal year"),
    fiscal_period: str = Query("FY", description="Fiscal period"),
):
    """
    Get consensus momentum analysis.

    Calculates 7d, 30d, 90d momentum and trend direction.
    """
    try:
        est_type = EstimateType(estimate_type.lower())
        period = PeriodType(fiscal_period.upper())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        momentum = get_consensus_momentum(
            ticker=ticker,
            estimate_type=est_type,
            fiscal_year=fiscal_year,
            fiscal_period=period,
        )
        return momentum_to_dict(momentum)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating momentum: {str(e)}")


# ── Estimate Dispersion ────────────────────────────────────────────────────────

@router.get("/dispersion")
def get_dispersion(
    ticker: str = Query(..., description="Stock ticker symbol"),
    estimate_type: str = Query("eps", description="Estimate type"),
    fiscal_year: Optional[int] = Query(None, description="Fiscal year"),
    fiscal_period: str = Query("FY", description="Fiscal period"),
):
    """
    Get estimate dispersion analysis.

    Measures how much analysts disagree on estimates.
    High dispersion = high uncertainty.
    """
    try:
        est_type = EstimateType(estimate_type.lower())
        period = PeriodType(fiscal_period.upper())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        dispersion = get_estimate_dispersion(
            ticker=ticker,
            estimate_type=est_type,
            fiscal_year=fiscal_year,
            fiscal_period=period,
        )
        return dispersion_to_dict(dispersion)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating dispersion: {str(e)}")


# ── Earnings Surprises ─────────────────────────────────────────────────────────

@router.get("/surprise")
def get_surprise(
    ticker: str = Query(..., description="Stock ticker symbol"),
    fiscal_year: int = Query(..., description="Fiscal year"),
    fiscal_period: str = Query(..., description="Fiscal period (Q1, Q2, Q3, Q4)"),
):
    """
    Get earnings surprise for a specific quarter.

    Returns actual vs consensus and market reaction.
    """
    try:
        period = PeriodType(fiscal_period.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid fiscal period: {fiscal_period}")

    try:
        surprise = get_earnings_surprise(
            ticker=ticker,
            fiscal_year=fiscal_year,
            fiscal_period=period,
        )
        return surprise_to_dict(surprise)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching surprise: {str(e)}")


@router.get("/surprise-history")
def get_historical_surprises(
    ticker: str = Query(..., description="Stock ticker symbol"),
    quarters: int = Query(12, description="Number of quarters"),
):
    """
    Get historical earnings surprise pattern.

    Shows beat/miss history and market reaction patterns.
    """
    try:
        history = get_surprise_history(
            ticker=ticker,
            quarters=quarters,
        )
        return surprise_history_to_dict(history)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")


# ── Combined Dashboard ─────────────────────────────────────────────────────────

@router.get("/dashboard/{ticker}")
def get_consensus_dashboard(
    ticker: str,
    fiscal_year: Optional[int] = Query(None, description="Fiscal year"),
):
    """
    Get full consensus dashboard for a ticker.

    Combines snapshot, momentum, dispersion, and recent surprises.
    """
    fy = fiscal_year or date.today().year

    try:
        # Get current consensus
        snapshot = get_consensus_snapshot(
            ticker=ticker,
            estimate_type=EstimateType.EPS,
            fiscal_year=fy,
            fiscal_period=PeriodType.FY,
        )

        # Get momentum
        momentum = get_consensus_momentum(
            ticker=ticker,
            estimate_type=EstimateType.EPS,
            fiscal_year=fy,
            fiscal_period=PeriodType.FY,
        )

        # Get dispersion
        dispersion = get_estimate_dispersion(
            ticker=ticker,
            estimate_type=EstimateType.EPS,
            fiscal_year=fy,
            fiscal_period=PeriodType.FY,
        )

        # Get recent surprises
        history = get_surprise_history(ticker=ticker, quarters=4)

        return {
            "ticker": ticker.upper(),
            "fiscal_year": fy,
            "current_consensus": consensus_snapshot_to_dict(snapshot),
            "momentum": momentum_to_dict(momentum),
            "dispersion": dispersion_to_dict(dispersion),
            "recent_surprises": {
                "beat_rate": history.beat_rate,
                "avg_surprise": history.avg_surprise_pct,
                "current_streak": history.beat_streak_current,
                "last_4_quarters": [surprise_to_dict(s) for s in history.surprises[:4]],
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error building dashboard: {str(e)}")


# ── Multi-Ticker Comparison ────────────────────────────────────────────────────

@router.get("/compare")
def compare_consensus(
    tickers: str = Query(..., description="Comma-separated tickers"),
    estimate_type: str = Query("eps", description="Estimate type"),
    fiscal_year: Optional[int] = Query(None, description="Fiscal year"),
):
    """
    Compare consensus metrics across multiple tickers.
    """
    ticker_list = [t.strip().upper() for t in tickers.split(",")]
    fy = fiscal_year or date.today().year

    try:
        est_type = EstimateType(estimate_type.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid estimate type: {estimate_type}")

    results = []
    for ticker in ticker_list:
        try:
            snapshot = get_consensus_snapshot(
                ticker=ticker,
                estimate_type=est_type,
                fiscal_year=fy,
            )
            momentum = get_consensus_momentum(
                ticker=ticker,
                estimate_type=est_type,
                fiscal_year=fy,
            )
            dispersion = get_estimate_dispersion(
                ticker=ticker,
                estimate_type=est_type,
                fiscal_year=fy,
            )

            results.append({
                "ticker": ticker,
                "consensus_mean": snapshot.mean,
                "num_analysts": snapshot.num_analysts,
                "momentum_30d": momentum.momentum_30d,
                "trend": momentum.trend,
                "dispersion_level": dispersion.dispersion_level,
                "uncertainty_score": dispersion.uncertainty_score,
            })
        except Exception:
            results.append({
                "ticker": ticker,
                "error": "Failed to fetch data",
            })

    return {
        "estimate_type": estimate_type,
        "fiscal_year": fy,
        "comparison": results,
    }
