"""
Global Equity Coverage API (#34)
International markets (EU, Asia, etc.)
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List

from app.services.global_equity_service import (
    get_supported_markets,
    get_market_status,
    search_global_stocks,
    get_global_quote,
    convert_currency,
    get_adr_mappings,
    get_global_indices,
)

router = APIRouter(prefix="/global", tags=["Global Equity"])


@router.get("/markets")
async def list_markets():
    """Get list of supported global markets."""
    return get_supported_markets()


@router.get("/markets/status")
async def market_status():
    """Get real-time status for all global markets."""
    return get_market_status()


@router.get("/search")
async def search_stocks(
    query: str = Query(..., description="Search query"),
    markets: Optional[str] = Query(None, description="Comma-separated market codes to filter")
):
    """Search for stocks across global markets."""
    market_list = markets.split(",") if markets else None
    return search_global_stocks(query, market_list)


@router.get("/quote/{ticker}")
async def get_quote(ticker: str):
    """Get quote for an international stock."""
    return get_global_quote(ticker)


@router.get("/convert")
async def currency_convert(
    amount: float = Query(..., description="Amount to convert"),
    from_currency: str = Query(..., description="Source currency code"),
    to_currency: str = Query(..., description="Target currency code")
):
    """Convert between currencies."""
    return convert_currency(amount, from_currency, to_currency)


@router.get("/adr/{ticker}")
async def get_adr(ticker: str):
    """Get ADR/GDR mappings for international stocks."""
    return get_adr_mappings(ticker)


@router.get("/indices")
async def list_indices():
    """Get major global indices."""
    return get_global_indices()
