"""
Insider Activity Screener API (Band C #41)
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional

from app.services import insider_activity_service

router = APIRouter(prefix="/insider", tags=["Insider Activity"])


@router.get("/transactions")
def get_recent_transactions(
    days: int = Query(7, ge=1, le=90, description="Days to look back"),
    ticker: Optional[str] = Query(None, description="Filter by ticker symbol"),
    transaction_type: Optional[str] = Query(None, description="P=Purchase, S=Sale"),
    min_value: float = Query(0, ge=0, description="Minimum transaction value"),
    limit: int = Query(50, ge=1, le=200),
):
    """Get recent insider transactions"""
    if transaction_type and transaction_type not in ["P", "S", "A", "M", "G"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid transaction_type. Must be P, S, A, M, or G",
        )

    transactions = insider_activity_service.get_recent_transactions(
        days=days,
        transaction_type=transaction_type,
        min_value=min_value,
        limit=limit,
    )
    if ticker:
        ticker_upper = ticker.upper()
        transactions = [t for t in transactions if t.get("ticker", "").upper() == ticker_upper]
    return {
        "transactions": transactions,
        "count": len(transactions),
        "filters": {
            "days": days,
            "ticker": ticker,
            "transaction_type": transaction_type,
            "min_value": min_value,
        },
    }


@router.get("/ticker/{ticker}")
def get_transactions_by_ticker(
    ticker: str,
    days: int = Query(90, ge=1, le=365, description="Days to look back"),
):
    """Get all insider transactions for a ticker"""
    transactions = insider_activity_service.get_transactions_by_ticker(ticker, days=days)
    return {
        "ticker": ticker.upper(),
        "transactions": transactions,
        "count": len(transactions),
        "days_back": days,
    }


@router.get("/cluster-buys")
def get_cluster_buys(
    days: int = Query(14, ge=1, le=60, description="Days to look back"),
    min_insiders: int = Query(2, ge=2, le=10, description="Minimum number of insiders"),
):
    """Get stocks with cluster buying (multiple insiders buying)"""
    clusters = insider_activity_service.get_cluster_buys(days=days, min_insiders=min_insiders)
    return {
        "clusters": clusters,
        "count": len(clusters),
        "min_insiders": min_insiders,
        "days_back": days,
    }


@router.get("/cluster-sells")
def get_cluster_sells(
    days: int = Query(14, ge=1, le=60, description="Days to look back"),
    min_insiders: int = Query(2, ge=2, le=10, description="Minimum number of insiders"),
):
    """Get stocks with cluster selling (multiple insiders selling)"""
    clusters = insider_activity_service.get_cluster_sells(days=days, min_insiders=min_insiders)
    return {
        "clusters": clusters,
        "count": len(clusters),
        "min_insiders": min_insiders,
        "days_back": days,
    }


@router.get("/largest")
def get_largest_transactions(
    days: int = Query(30, ge=1, le=180, description="Days to look back"),
    transaction_type: Optional[str] = Query(None, description="P=Purchase, S=Sale"),
    limit: int = Query(10, ge=1, le=50),
):
    """Get largest insider transactions by value"""
    if transaction_type and transaction_type not in ["P", "S"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid transaction_type. Must be P or S",
        )

    transactions = insider_activity_service.get_largest_transactions(
        days=days,
        transaction_type=transaction_type,
        limit=limit,
    )
    return {
        "transactions": transactions,
        "count": len(transactions),
        "type_filter": transaction_type,
    }


@router.get("/ceo-cfo")
def get_ceo_transactions(
    days: int = Query(30, ge=1, le=180, description="Days to look back"),
):
    """Get CEO/CFO transactions only"""
    transactions = insider_activity_service.get_ceo_transactions(days=days)
    return {
        "transactions": transactions,
        "count": len(transactions),
        "days_back": days,
    }


@router.get("/stats")
def get_insider_stats():
    """Get insider trading statistics"""
    stats = insider_activity_service.get_insider_stats()
    return stats


@router.get("/sentiment/{ticker}")
def get_insider_sentiment(
    ticker: str,
    days: int = Query(90, ge=1, le=365, description="Days to analyze"),
):
    """Get insider sentiment for a specific ticker"""
    sentiment = insider_activity_service.get_insider_sentiment(ticker, days=days)
    return sentiment


@router.get("/screen")
def screen_insiders(
    min_buy_value: float = Query(100000, ge=0, description="Minimum buy value"),
    min_insiders: int = Query(1, ge=1, le=10, description="Minimum number of insiders"),
    days: int = Query(14, ge=1, le=60, description="Days to look back"),
    signal: Optional[str] = Query(None, description="Filter by signal: strong_buy, buy, neutral, sell, strong_sell"),
):
    """Screen stocks by insider activity"""
    valid_signals = ["strong_buy", "buy", "neutral", "sell", "strong_sell"]
    if signal and signal not in valid_signals:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid signal. Must be one of: {', '.join(valid_signals)}",
        )

    results = insider_activity_service.screen_insiders(
        min_buy_value=min_buy_value,
        min_insiders=min_insiders,
        days=days,
        signal_filter=signal,
    )
    return {
        "results": results,
        "count": len(results),
        "filters": {
            "min_buy_value": min_buy_value,
            "min_insiders": min_insiders,
            "days": days,
            "signal": signal,
        },
    }
