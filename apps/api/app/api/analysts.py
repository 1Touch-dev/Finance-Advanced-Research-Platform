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
    get_rating_changes,
    get_price_target_history,
    get_rating_distribution,
    get_analyst_rating_history,
    profile_to_dict,
    accuracy_score_to_dict,
    estimate_record_to_dict,
    sector_ranking_to_dict,
    rating_change_to_dict,
    price_target_history_to_dict,
    rating_distribution_to_dict,
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


# ── Rating Changes & Price Target History (#36) ───────────────────────────────

@router.get("/ratings/{ticker}")
def get_ticker_rating_changes(
    ticker: str,
    days: int = Query(90, description="Days of history"),
):
    """
    Get recent analyst rating changes for a ticker.

    Shows upgrades, downgrades, initiations, and reiterations.
    """
    try:
        changes = get_rating_changes(ticker, days=days)

        # Calculate summary
        upgrades = sum(1 for c in changes if c.action.value == "upgrade")
        downgrades = sum(1 for c in changes if c.action.value == "downgrade")
        initiations = sum(1 for c in changes if c.action.value == "initiate")

        return {
            "ticker": ticker.upper(),
            "days": days,
            "summary": {
                "total_changes": len(changes),
                "upgrades": upgrades,
                "downgrades": downgrades,
                "initiations": initiations,
                "net_sentiment": "bullish" if upgrades > downgrades else "bearish" if downgrades > upgrades else "neutral",
            },
            "changes": [rating_change_to_dict(c) for c in changes],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching rating changes: {str(e)}")


@router.get("/price-targets/{ticker}")
def get_ticker_price_targets(ticker: str):
    """
    Get price target history and consensus for a ticker.

    Includes current consensus, target evolution, and recent analyst changes.
    """
    try:
        history = get_price_target_history(ticker)
        return price_target_history_to_dict(history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching price target history: {str(e)}")


@router.get("/distribution/{ticker}")
def get_ticker_rating_distribution(ticker: str):
    """
    Get current rating distribution for a ticker.

    Shows breakdown of buy/hold/sell ratings and consensus.
    """
    try:
        distribution = get_rating_distribution(ticker)
        return rating_distribution_to_dict(distribution)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching rating distribution: {str(e)}")


@router.get("/rating-history/{analyst_id}")
def get_analyst_ratings(
    analyst_id: str,
    limit: int = Query(20, description="Number of ratings to return"),
):
    """
    Get an analyst's rating history across all covered tickers.

    Shows all their rating calls with targets and outcomes.
    """
    try:
        ratings = get_analyst_rating_history(analyst_id, limit=limit)
        return {
            "analyst_id": analyst_id,
            "ratings": [rating_change_to_dict(r) for r in ratings],
            "total": len(ratings),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching rating history: {str(e)}")


@router.get("/summary/{ticker}")
def get_ticker_analyst_summary(ticker: str):
    """
    Get complete analyst summary for a ticker.

    Combines coverage, ratings, price targets, and recent changes.
    """
    try:
        coverage = get_ticker_analysts(ticker)
        distribution = get_rating_distribution(ticker)
        pt_history = get_price_target_history(ticker)
        rating_changes = get_rating_changes(ticker, days=30)

        return {
            "ticker": ticker.upper(),
            "coverage": {
                "total_analysts": len(coverage),
                "top_rated_analyst": coverage[0].analyst_name if coverage else None,
                "top_analyst_score": coverage[0].overall_score if coverage else None,
            },
            "ratings": rating_distribution_to_dict(distribution),
            "price_targets": {
                "consensus": pt_history.consensus_target,
                "upside_pct": pt_history.consensus_upside,
                "high": pt_history.high_target,
                "low": pt_history.low_target,
                "change_30d_pct": pt_history.target_change_30d_pct,
            },
            "recent_activity": {
                "changes_30d": len(rating_changes),
                "latest_change": rating_change_to_dict(rating_changes[0]) if rating_changes else None,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error building summary: {str(e)}")
