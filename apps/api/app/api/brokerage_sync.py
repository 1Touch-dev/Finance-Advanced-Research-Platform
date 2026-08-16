"""
Brokerage Sync API (#43)
Plaid/OAuth integration with brokers
"""
from fastapi import APIRouter, Query, HTTPException, Body
from typing import Optional, Dict, Any

from app.services.brokerage_sync_service import (
    get_supported_brokers,
    initiate_link,
    complete_link,
    get_linked_accounts,
    sync_account,
    get_account_positions,
    get_account_transactions,
    unlink_account,
    get_sync_status,
)

router = APIRouter(prefix="/brokerage", tags=["Brokerage Sync"])


@router.get("/brokers")
async def list_brokers():
    """Get list of supported brokers."""
    return get_supported_brokers()


@router.post("/link/initiate")
async def start_link(
    user_id: str = Query(..., description="User ID"),
    broker_id: str = Query(..., description="Broker ID")
):
    """Initiate broker linking process."""
    return initiate_link(user_id, broker_id)


@router.post("/link/complete")
async def finish_link(
    user_id: str = Query(..., description="User ID"),
    link_token: str = Query(..., description="Link token from initiate"),
    access_token: str = Query(..., description="Access token from OAuth")
):
    """Complete broker linking after OAuth."""
    return complete_link(user_id, link_token, access_token)


@router.get("/accounts")
async def list_accounts(
    user_id: str = Query(..., description="User ID")
):
    """Get all linked brokerage accounts."""
    return get_linked_accounts(user_id)


@router.post("/accounts/{account_id}/sync")
async def trigger_sync(
    account_id: str,
    user_id: str = Query(..., description="User ID")
):
    """Sync account data from broker."""
    return sync_account(user_id, account_id)


@router.get("/accounts/{account_id}/positions")
async def get_positions(
    account_id: str,
    user_id: str = Query(..., description="User ID")
):
    """Get positions from linked account."""
    return get_account_positions(user_id, account_id)


@router.get("/accounts/{account_id}/transactions")
async def get_transactions(
    account_id: str,
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(50, description="Max transactions to return")
):
    """Get recent transactions from linked account."""
    return get_account_transactions(user_id, account_id, limit)


@router.delete("/accounts/{account_id}")
async def remove_account(
    account_id: str,
    user_id: str = Query(..., description="User ID")
):
    """Unlink a brokerage account."""
    return unlink_account(user_id, account_id)


@router.get("/sync-status")
async def check_sync_status(
    user_id: str = Query(..., description="User ID")
):
    """Get sync status for all accounts."""
    return get_sync_status(user_id)
