"""
Whisper Estimates + Buy/Sell-Side Split API (Band B #25)
--------------------------------------------------------------------------------
Endpoints:
- GET /whisper/compare - Compare whispers across tickers
- GET /whisper/screen - Screen by whisper characteristics
- GET /whisper/types/analyst - List analyst types
- GET /whisper/types/metrics - List estimate metrics
- GET /whisper/{ticker} - Get whisper estimate
- GET /whisper/{ticker}/snapshot - Quick whisper snapshot
- GET /whisper/{ticker}/side-split - Buy-side vs sell-side analysis
- GET /whisper/{ticker}/history - Whisper accuracy history
- GET /whisper/{ticker}/dispersion - Dispersion by analyst type
- GET /whisper/{ticker}/estimates - Estimates by analyst type
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from app.services.whisper_estimates_service import (
    get_whisper_service,
    AnalystType,
    EstimateMetric,
)

router = APIRouter(prefix="/whisper", tags=["whisper"])


# ── Static Routes (MUST come before parameterized routes) ────────────────────

@router.get("/compare")
async def compare_whispers(
    tickers: str = Query(..., description="Comma-separated tickers"),
    metric: str = Query("eps", description="Metric to compare"),
):
    """
    Compare whisper estimates across multiple tickers.

    Returns:
        Comparison of whisper vs consensus for each ticker
    """
    try:
        metric_enum = EstimateMetric(metric.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid metric: {metric}")

    ticker_list = [t.strip().upper() for t in tickers.split(",")]

    if len(ticker_list) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 tickers to compare")

    service = get_whisper_service()
    results = []

    for ticker in ticker_list:
        whisper = service.get_whisper_estimate(ticker, "next_quarter", metric_enum)
        results.append({
            "ticker": ticker,
            "whisper": whisper.whisper_value,
            "consensus": whisper.consensus_value,
            "whisper_vs_consensus": whisper.whisper_vs_consensus,
            "direction": whisper.whisper_direction,
            "confidence": whisper.confidence_score,
        })

    # Sort by whisper vs consensus spread
    results.sort(key=lambda x: x["whisper_vs_consensus"], reverse=True)

    return {
        "metric": metric,
        "comparisons": results,
        "most_bullish_whisper": results[0]["ticker"] if results else None,
        "most_bearish_whisper": results[-1]["ticker"] if results else None,
    }


@router.get("/screen")
async def screen_by_whisper(
    min_whisper_vs_consensus: float = Query(None, description="Minimum whisper vs consensus %"),
    max_whisper_vs_consensus: float = Query(None, description="Maximum whisper vs consensus %"),
    direction: Optional[str] = Query(None, description="Filter by direction (above, below, inline)"),
    tickers: Optional[str] = Query(None, description="Comma-separated tickers to screen"),
):
    """
    Screen stocks by whisper characteristics.

    Filter by whisper vs consensus spread, direction, etc.

    Returns:
        Filtered list of whisper estimates
    """
    # Default tickers if not provided
    default_tickers = ["NVDA", "AAPL", "MSFT", "GOOGL", "META", "AMZN", "TSLA", "AMD"]
    ticker_list = [t.strip().upper() for t in tickers.split(",")] if tickers else default_tickers

    service = get_whisper_service()
    results = []

    for ticker in ticker_list:
        whisper = service.get_whisper_estimate(ticker, "next_quarter", EstimateMetric.EPS)

        # Apply filters
        if min_whisper_vs_consensus is not None and whisper.whisper_vs_consensus < min_whisper_vs_consensus:
            continue
        if max_whisper_vs_consensus is not None and whisper.whisper_vs_consensus > max_whisper_vs_consensus:
            continue
        if direction and whisper.whisper_direction != direction.lower():
            continue

        results.append({
            "ticker": ticker,
            "whisper": whisper.whisper_value,
            "consensus": whisper.consensus_value,
            "whisper_vs_consensus": whisper.whisper_vs_consensus,
            "direction": whisper.whisper_direction,
            "confidence": whisper.confidence_score,
        })

    return {
        "results": results,
        "count": len(results),
        "filters": {
            "min_whisper_vs_consensus": min_whisper_vs_consensus,
            "max_whisper_vs_consensus": max_whisper_vs_consensus,
            "direction": direction,
        },
    }


@router.get("/types/analyst")
async def list_analyst_types():
    """
    List available analyst types.
    """
    service = get_whisper_service()
    return {"analyst_types": service.list_analyst_types()}


@router.get("/types/metrics")
async def list_estimate_metrics():
    """
    List available estimate metrics.
    """
    service = get_whisper_service()
    return {"metrics": service.list_estimate_metrics()}


# ── Parameterized Routes (after static routes) ───────────────────────────────

@router.get("/{ticker}")
async def get_whisper_estimate(
    ticker: str,
    period: str = Query("next_quarter", description="Period (e.g., next_quarter, Q1_2025)"),
    metric: str = Query("eps", description="Metric (eps, revenue, ebitda, fcf)"),
):
    """
    Get whisper estimate for a ticker.

    Whisper estimates are unofficial "street expectations" that often differ
    from published analyst consensus. They incorporate buy-side sentiment
    and non-public sources.

    Returns:
        Whisper estimate with consensus comparison
    """
    try:
        metric_enum = EstimateMetric(metric.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid metric: {metric}")

    service = get_whisper_service()
    whisper = service.get_whisper_estimate(ticker.upper(), period, metric_enum)

    return whisper.to_dict()


@router.get("/{ticker}/snapshot")
async def get_whisper_snapshot(ticker: str):
    """
    Get quick whisper snapshot for a ticker.

    Returns EPS and revenue whisper estimates with beat probability.
    """
    service = get_whisper_service()
    snapshot = service.get_whisper_snapshot(ticker.upper())

    return snapshot.to_dict()


@router.get("/{ticker}/side-split")
async def get_side_split_analysis(
    ticker: str,
    period: str = Query("next_quarter", description="Period"),
    metric: str = Query("eps", description="Metric"),
):
    """
    Get buy-side vs sell-side estimate analysis.

    Compares estimates from buy-side firms (investment managers) against
    sell-side firms (brokerages). Buy-side estimates are often more accurate
    but less available.

    Returns:
        Analysis with count, mean, spread, and interpretation
    """
    try:
        metric_enum = EstimateMetric(metric.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid metric: {metric}")

    service = get_whisper_service()
    analysis = service.get_side_split_analysis(ticker.upper(), period, metric_enum)

    return analysis.to_dict()


@router.get("/{ticker}/history")
async def get_whisper_history(
    ticker: str,
    metric: str = Query("eps", description="Metric"),
    periods: int = Query(8, ge=4, le=20, description="Number of periods"),
):
    """
    Get historical whisper accuracy.

    Shows how whisper estimates compared to actual results vs consensus.

    Returns:
        Historical comparison with accuracy rates
    """
    try:
        metric_enum = EstimateMetric(metric.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid metric: {metric}")

    service = get_whisper_service()
    history = service.get_whisper_history(ticker.upper(), metric_enum, periods)

    return history.to_dict()


@router.get("/{ticker}/dispersion")
async def get_dispersion_by_side(
    ticker: str,
    period: str = Query("next_quarter", description="Period"),
    metric: str = Query("eps", description="Metric"),
):
    """
    Get estimate dispersion by analyst type.

    Shows how much disagreement exists within buy-side vs sell-side analysts.

    Returns:
        Dispersion metrics by analyst type
    """
    try:
        metric_enum = EstimateMetric(metric.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid metric: {metric}")

    service = get_whisper_service()
    dispersion = service.get_dispersion_by_side(ticker.upper(), period, metric_enum)

    return dispersion.to_dict()


@router.get("/{ticker}/estimates")
async def get_estimates_by_type(
    ticker: str,
    analyst_type: str = Query(..., description="Analyst type (buy_side, sell_side, independent)"),
    period: str = Query("next_quarter", description="Period"),
    metric: str = Query("eps", description="Metric"),
):
    """
    Get individual estimates filtered by analyst type.

    Returns:
        List of analyst estimates
    """
    try:
        type_enum = AnalystType(analyst_type.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid analyst type: {analyst_type}")

    try:
        metric_enum = EstimateMetric(metric.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid metric: {metric}")

    service = get_whisper_service()
    estimates = service.get_estimates_by_type(ticker.upper(), type_enum, period, metric_enum)

    return {
        "ticker": ticker.upper(),
        "analyst_type": analyst_type,
        "period": period,
        "metric": metric,
        "estimates": [e.to_dict() for e in estimates],
        "count": len(estimates),
        "mean": round(sum(e.estimate for e in estimates) / len(estimates), 2) if estimates else None,
    }
