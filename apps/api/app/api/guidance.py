"""
Guidance vs Actual Tracking API Routes (Band B #22)
────────────────────────────────────────────────────────────────────────────
Provides endpoints for:
  - Current guidance lookup
  - Guidance vs actual comparison
  - Management credibility scoring
  - Guidance revision history
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from app.services.guidance_service import (
    # Enums
    GuidanceMetric,
    # Functions
    get_current_guidance,
    get_guidance_vs_actual,
    get_guidance_history,
    get_guidance_revisions,
    calculate_management_credibility,
    get_full_guidance_track,
    # Serializers
    guidance_record_to_dict,
    vs_actual_to_dict,
    revision_to_dict,
    credibility_to_dict,
    guidance_track_to_dict,
)

router = APIRouter(prefix="/guidance")


@router.get("/current")
def get_current_guidance_api(
    ticker: str = Query(..., description="Stock ticker symbol"),
    metric: str = Query("eps", description="Metric type (eps, revenue, gross_margin)"),
):
    """
    Get current fiscal year guidance for a company.

    Returns the latest guidance range/point estimate.
    """
    try:
        metric_enum = GuidanceMetric(metric.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid metric: {metric}")

    try:
        records = get_current_guidance(ticker, metric_enum)
        return {
            "ticker": ticker.upper(),
            "metric": metric,
            "guidance": [guidance_record_to_dict(r) for r in records],
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching guidance: {str(e)}")


@router.get("/vs-actual")
def get_guidance_comparison(
    ticker: str = Query(..., description="Stock ticker symbol"),
    fiscal_year: int = Query(..., description="Fiscal year"),
    fiscal_period: str = Query("FY", description="Fiscal period (Q1-Q4, FY)"),
    metric: str = Query("eps", description="Metric type"),
):
    """
    Compare guidance vs actual results for a specific period.

    Returns outcome (beat/met/missed) and variance.
    """
    try:
        metric_enum = GuidanceMetric(metric.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid metric: {metric}")

    try:
        result = get_guidance_vs_actual(ticker, fiscal_year, fiscal_period, metric_enum)
        return vs_actual_to_dict(result)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparing guidance: {str(e)}")


@router.get("/history")
def get_guidance_track_record(
    ticker: str = Query(..., description="Stock ticker symbol"),
    metric: str = Query("eps", description="Metric type"),
    quarters: int = Query(12, description="Number of quarters"),
):
    """
    Get historical guidance vs actual record.

    Shows track record of guidance accuracy.
    """
    try:
        metric_enum = GuidanceMetric(metric.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid metric: {metric}")

    try:
        history = get_guidance_history(ticker, metric_enum, quarters)

        # Calculate summary stats
        beats = sum(1 for h in history if h.outcome.value in ["beat", "significantly_beat"])
        meets = sum(1 for h in history if h.outcome.value == "met")
        misses = sum(1 for h in history if h.outcome.value in ["missed", "significantly_missed"])
        total = len(history)

        return {
            "ticker": ticker.upper(),
            "metric": metric,
            "summary": {
                "total_periods": total,
                "beats": beats,
                "meets": meets,
                "misses": misses,
                "beat_rate": round(beats / total * 100, 1) if total > 0 else 0,
                "meet_or_beat_rate": round((beats + meets) / total * 100, 1) if total > 0 else 0,
            },
            "history": [vs_actual_to_dict(h) for h in history],
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")


@router.get("/revisions")
def get_revision_history(
    ticker: str = Query(..., description="Stock ticker symbol"),
    fiscal_year: Optional[int] = Query(None, description="Fiscal year"),
):
    """
    Get guidance revision history.

    Shows how guidance has been adjusted throughout the year.
    """
    try:
        revisions = get_guidance_revisions(ticker, fiscal_year)

        # Calculate summary
        raises = sum(1 for r in revisions if r.direction.value == "raised")
        lowers = sum(1 for r in revisions if r.direction.value == "lowered")

        return {
            "ticker": ticker.upper(),
            "fiscal_year": fiscal_year,
            "summary": {
                "total_revisions": len(revisions),
                "raises": raises,
                "lowers": lowers,
                "net_direction": "bullish" if raises > lowers else "bearish" if lowers > raises else "neutral",
            },
            "revisions": [revision_to_dict(r) for r in revisions],
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching revisions: {str(e)}")


@router.get("/credibility")
def get_management_credibility_api(
    ticker: str = Query(..., description="Stock ticker symbol"),
):
    """
    Get management credibility score.

    Evaluates guidance accuracy, revision patterns, consistency.
    """
    try:
        credibility = calculate_management_credibility(ticker)
        return credibility_to_dict(credibility)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating credibility: {str(e)}")


@router.get("/full/{ticker}")
def get_full_guidance_dashboard(ticker: str):
    """
    Get complete guidance dashboard for a ticker.

    Combines current guidance, history, revisions, and credibility.
    """
    try:
        track = get_full_guidance_track(ticker)
        return guidance_track_to_dict(track)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error building dashboard: {str(e)}")


@router.get("/compare")
def compare_credibility(
    tickers: str = Query(..., description="Comma-separated tickers"),
):
    """
    Compare management credibility across multiple companies.
    """
    ticker_list = [t.strip().upper() for t in tickers.split(",")]

    results = []
    for ticker in ticker_list:
        try:
            cred = calculate_management_credibility(ticker)
            results.append({
                "ticker": ticker,
                "company_name": cred.company_name,
                "credibility_score": cred.credibility_score,
                "tier": cred.credibility_tier.value,
                "beat_rate": cred.beat_rate,
                "meet_or_beat_rate": cred.meet_or_beat_rate,
                "revision_tendency": cred.revision_tendency,
            })
        except Exception:
            results.append({
                "ticker": ticker,
                "error": "Failed to calculate credibility",
            })

    # Sort by credibility score
    results.sort(key=lambda x: x.get("credibility_score", 0), reverse=True)

    return {
        "comparison": results,
        "leader": results[0]["ticker"] if results and "credibility_score" in results[0] else None,
    }


@router.get("/leaderboard")
def get_credibility_leaderboard():
    """
    Get management credibility leaderboard.

    Shows ranked list of companies by guidance credibility.
    """
    from app.services.guidance_service import COMPANY_GUIDANCE_DATA

    results = []
    for ticker in COMPANY_GUIDANCE_DATA.keys():
        try:
            cred = calculate_management_credibility(ticker)
            results.append({
                "rank": 0,  # Will be set after sorting
                "ticker": ticker,
                "company_name": cred.company_name,
                "credibility_score": cred.credibility_score,
                "tier": cred.credibility_tier.value,
                "beat_rate": cred.beat_rate,
                "green_flags": len(cred.green_flags),
                "red_flags": len(cred.red_flags),
            })
        except Exception:
            continue

    # Sort and assign ranks
    results.sort(key=lambda x: x["credibility_score"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1

    return {
        "leaderboard": results,
        "total_companies": len(results),
    }
