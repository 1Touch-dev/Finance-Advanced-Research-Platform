"""
Brokerage Sync API (#43)
Plaid/OAuth integration with brokers
"""
from fastapi import APIRouter, Query, HTTPException, Body, Depends
from typing import Optional, Dict, Any

from app.auth.security import get_current_user

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
def list_brokers():
    """Get list of supported brokers."""
    return get_supported_brokers()


@router.post("/link/initiate")
def start_link(
    user_id: Optional[str] = Query(None, description="User ID"),
    broker_id: str = Query(..., description="Broker ID"),
    current_user: dict = Depends(get_current_user),
):
    """Initiate broker linking process."""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    return initiate_link(user_id, broker_id)


@router.post("/link/complete")
def finish_link(
    user_id: Optional[str] = Query(None, description="User ID"),
    link_token: str = Query(..., description="Link token from initiate"),
    access_token: str = Query(..., description="Access token from OAuth"),
    current_user: dict = Depends(get_current_user),
):
    """Complete broker linking after OAuth."""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    return complete_link(user_id, link_token, access_token)


@router.get("/accounts")
def list_accounts(
    user_id: Optional[str] = Query(None, description="User ID")
):
    """Get all linked brokerage accounts."""
    return get_linked_accounts(user_id)


@router.post("/accounts/{account_id}/sync")
def trigger_sync(
    account_id: str,
    user_id: Optional[str] = Query(None, description="User ID"),
    current_user: dict = Depends(get_current_user),
):
    """Sync account data from broker."""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    return sync_account(user_id, account_id)


@router.get("/accounts/{account_id}/positions")
def get_positions(
    account_id: str,
    user_id: Optional[str] = Query(None, description="User ID")
):
    """Get positions from linked account."""
    return get_account_positions(user_id, account_id)


@router.get("/accounts/{account_id}/transactions")
def get_transactions(
    account_id: str,
    user_id: Optional[str] = Query(None, description="User ID"),
    limit: int = Query(50, description="Max transactions to return")
):
    """Get recent transactions from linked account."""
    return get_account_transactions(user_id, account_id, limit)


@router.delete("/accounts/{account_id}")
def remove_account(
    account_id: str,
    user_id: Optional[str] = Query(None, description="User ID"),
    current_user: dict = Depends(get_current_user),
):
    """Unlink a brokerage account."""
    user_id = str(current_user["user_id"])  # authz: token identity wins over any query param
    return unlink_account(user_id, account_id)


@router.get("/sync-status")
def check_sync_status(
    user_id: Optional[str] = Query(None, description="User ID")
):
    """Get sync status for all accounts."""
    return get_sync_status(user_id)
