"""
Analyst Accuracy Scoring API Routes (Band B #24)
────────────────────────────────────────────────────────────────────────────
Provides endpoints for:
  - Analyst search and profiles
  - Accuracy scoring and rankings
  - Sector/firm leaderboards
  - Historical estimate accuracy
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List

from app.services.analyst_scoring_service import (
    get_analyst_profile,
    search_analysts,
    calculate_analyst_accuracy,
    get_analyst_ranking,
    get_firm_ranking,
    get_sector_ranking,
    get_ticker_analysts,
    get_analyst_estimates_history,
    compare_analysts,
    profile_to_dict,
    accuracy_score_to_dict,
    estimate_record_to_dict,
    sector_ranking_to_dict,
)

router = APIRouter(prefix="/analysts")


@router.get("/search")
def search_analysts_api(
    firm: Optional[str] = Query(None, description="Filter by firm"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    ticker: Optional[str] = Query(None, description="Filter by ticker coverage"),
    name: Optional[str] = Query(None, description="Search by name"),
):
    """
    Search analysts by firm, sector, ticker, or name.

    Returns matching analyst profiles.
    """
    analysts = search_analysts(firm=firm, sector=sector, ticker=ticker, name=name)

    return {
        "filters": {
            "firm": firm,
            "sector": sector,
            "ticker": ticker,
            "name": name,
        },
        "analysts": [profile_to_dict(a) for a in analysts],
        "total": len(analysts),
    }


@router.get("/profile/{analyst_id}")
def get_analyst_profile_api(analyst_id: str):
    """
    Get detailed analyst profile.
    """
    profile = get_analyst_profile(analyst_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Analyst not found: {analyst_id}")

    return profile_to_dict(profile)


@router.get("/score/{analyst_id}")
def get_analyst_score(analyst_id: str):
    """
    Get comprehensive accuracy score for an analyst.

    Includes calibration metrics, sector expertise, and tier ranking.
    """
    try:
        score = calculate_analyst_accuracy(analyst_id)
        return accuracy_score_to_dict(score)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating score: {str(e)}")


@router.get("/history/{analyst_id}")
def get_analyst_history(
    analyst_id: str,
    limit: int = Query(20, description="Number of estimates to return"),
):
    """
    Get analyst's historical estimates with outcomes.

    Shows track record of accuracy.
    """
    try:
        records = get_analyst_estimates_history(analyst_id, limit=limit)
        return {
            "analyst_id": analyst_id,
            "estimates": [estimate_record_to_dict(r) for r in records],
            "total": len(records),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching history: {str(e)}")


@router.get("/ranking")
def get_analyst_leaderboard(
    sector: Optional[str] = Query(None, description="Filter by sector"),
    firm: Optional[str] = Query(None, description="Filter by firm"),
    limit: int = Query(20, description="Number of analysts"),
):
    """
    Get ranked list of analysts by accuracy.

    Can filter by sector or firm.
    """
    try:
        ranking = get_analyst_ranking(sector=sector, firm=firm, limit=limit)
        return {
            "filters": {
                "sector": sector,
                "firm": firm,
            },
            "ranking": [accuracy_score_to_dict(s) for s in ranking],
            "total": len(ranking),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching ranking: {str(e)}")


@router.get("/ranking/firms")
def get_firm_leaderboard():
    """
    Get ranking of firms by average analyst quality.

    Shows which firms have the most accurate research teams.
    """
    try:
        ranking = get_firm_ranking()
        return {
            "ranking": ranking,
            "total_firms": len(ranking),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching firm ranking: {str(e)}")


@router.get("/ranking/sector/{sector}")
def get_sector_leaderboard(sector: str):
    """
    Get ranking of analysts covering a specific sector.

    Shows who has the best track record in that sector.
    """
    try:
        ranking = get_sector_ranking(sector)
        return sector_ranking_to_dict(ranking)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching sector ranking: {str(e)}")


@router.get("/by-ticker/{ticker}")
def get_ticker_coverage(ticker: str):
    """
    Get all analysts covering a ticker with their accuracy scores.

    Helps identify which analyst estimates to weight more heavily.
    """
    try:
        analysts = get_ticker_analysts(ticker)
        return {
            "ticker": ticker.upper(),
            "analysts": [accuracy_score_to_dict(a) for a in analysts],
            "total": len(analysts),
            "best_analyst": analysts[0].analyst_name if analysts else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching coverage: {str(e)}")


@router.get("/compare")
def compare_analysts_api(
    analyst_ids: str = Query(..., description="Comma-separated analyst IDs"),
):
    """
    Compare multiple analysts side by side.
    """
    id_list = [a.strip() for a in analyst_ids.split(",")]

    if len(id_list) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 analysts to compare")

    try:
        scores = compare_analysts(id_list)
        return {
            "comparison": [accuracy_score_to_dict(s) for s in scores],
            "leader": scores[0].analyst_name if scores else None,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparing analysts: {str(e)}")


@router.get("/full/{analyst_id}")
def get_full_analyst_profile(analyst_id: str):
    """
    Get complete analyst profile with score and history.
    """
    profile = get_analyst_profile(analyst_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Analyst not found: {analyst_id}")

    try:
        score = calculate_analyst_accuracy(analyst_id)
        history = get_analyst_estimates_history(analyst_id, limit=10)

        return {
            "profile": profile_to_dict(profile),
            "score": accuracy_score_to_dict(score),
            "recent_estimates": [estimate_record_to_dict(r) for r in history],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error building profile: {str(e)}")
