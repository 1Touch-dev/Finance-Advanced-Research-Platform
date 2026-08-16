"""
Reddit & Whale Tracking API (James J4)
"""

from fastapi import APIRouter, Query
from typing import Optional

router = APIRouter(prefix="/social", tags=["Social & Whales"])

try:
    from ..services.reddit_whale_service import (
        get_reddit_sentiment,
        get_reddit_trending,
        get_subreddit_activity,
        get_sentiment_history,
        get_whale_transactions,
        get_whale_flow,
        get_top_whales,
        get_institutional_ownership,
        get_insider_sentiment,
        get_social_momentum,
    )
    SERVICE_AVAILABLE = True
except ImportError:
    SERVICE_AVAILABLE = False


@router.get("/reddit/sentiment")
def api_get_reddit_sentiment(
    ticker: Optional[str] = None,
    subreddit: Optional[str] = None,
    limit: int = Query(default=20),
):
    """Get Reddit sentiment"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_reddit_sentiment(ticker, subreddit, limit)


@router.get("/reddit/trending")
def api_get_trending(
    limit: int = Query(default=10),
):
    """Get trending tickers on Reddit"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_reddit_trending(limit)


@router.get("/reddit/subreddit/{subreddit}")
def api_get_subreddit(subreddit: str):
    """Get subreddit activity metrics"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_subreddit_activity(subreddit)


@router.get("/reddit/history/{ticker}")
def api_get_sentiment_history(
    ticker: str,
    days: int = Query(default=30),
):
    """Get sentiment history over time"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_sentiment_history(ticker, days)


@router.get("/whales/transactions")
def api_get_whale_transactions(
    ticker: Optional[str] = None,
    whale_type: Optional[str] = None,
    transaction_type: Optional[str] = None,
    min_value: float = Query(default=0),
    limit: int = Query(default=20),
):
    """Get whale transactions"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_whale_transactions(ticker, whale_type, transaction_type, min_value, limit)


@router.get("/whales/flow/{ticker}")
def api_get_whale_flow(
    ticker: str,
    days: int = Query(default=30),
):
    """Get whale money flow over time"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_whale_flow(ticker, days)


@router.get("/whales/top")
def api_get_top_whales(
    ticker: Optional[str] = None,
    whale_type: Optional[str] = None,
    limit: int = Query(default=10),
):
    """Get top whales by volume"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return {"whales": get_top_whales(ticker, whale_type, limit)}


@router.get("/institutional/{ticker}")
def api_get_institutional(ticker: str):
    """Get institutional ownership breakdown"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_institutional_ownership(ticker)


@router.get("/insider-sentiment/{ticker}")
def api_get_insider_sentiment(
    ticker: str,
    days: int = Query(default=90),
):
    """Get insider buying/selling sentiment"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_insider_sentiment(ticker, days)


@router.get("/momentum/{ticker}")
def api_get_momentum(ticker: str):
    """Get combined social momentum score"""
    if not SERVICE_AVAILABLE:
        return {"error": "Service not available"}
    return get_social_momentum(ticker)
