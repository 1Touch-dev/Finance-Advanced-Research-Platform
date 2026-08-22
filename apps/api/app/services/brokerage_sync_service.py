"""
Brokerage Sync Service (#43)
Plaid/OAuth integration with brokers
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from app.core.no_data import no_data_response, NoDataReason


def get_supported_brokers() -> Dict[str, Any]:
    """Get list of supported brokers."""
    return {"status": "not_available", "reason": "Plaid integration not yet configured", **no_data_response("brokers", "supported_brokers", NoDataReason.DEPENDENCY_MISSING, details="Plaid integration not yet configured")}


def initiate_link(user_id: str, broker_id: str) -> Dict[str, Any]:
    """Initiate broker linking process."""
    return {"status": "not_available", "reason": "Plaid integration not yet configured", **no_data_response(broker_id, "broker_link", NoDataReason.DEPENDENCY_MISSING, details="Plaid integration not yet configured")}


def complete_link(user_id: str, link_token: str, access_token: str) -> Dict[str, Any]:
    """Complete broker linking after OAuth."""
    return {"status": "not_available", "reason": "Plaid integration not yet configured", **no_data_response(user_id, "broker_link_completion", NoDataReason.DEPENDENCY_MISSING, details="Plaid integration not yet configured")}


def get_linked_accounts(user_id: str) -> Dict[str, Any]:
    """Get all linked brokerage accounts."""
    return {"status": "not_available", "reason": "Plaid integration not yet configured", **no_data_response(user_id, "linked_accounts", NoDataReason.DEPENDENCY_MISSING, details="Plaid integration not yet configured")}


def sync_account(user_id: str, account_id: str) -> Dict[str, Any]:
    """Sync account data from broker."""
    return {"status": "not_available", "reason": "Plaid integration not yet configured", **no_data_response(account_id, "account_sync", NoDataReason.DEPENDENCY_MISSING, details="Plaid integration not yet configured")}


def get_account_positions(user_id: str, account_id: str) -> Dict[str, Any]:
    """Get positions from linked account."""
    return {"status": "not_available", "reason": "Plaid integration not yet configured", **no_data_response(account_id, "account_positions", NoDataReason.DEPENDENCY_MISSING, details="Plaid integration not yet configured")}


def get_account_transactions(user_id: str, account_id: str, limit: int = 50) -> Dict[str, Any]:
    """Get recent transactions from linked account."""
    return {"status": "not_available", "reason": "Plaid integration not yet configured", **no_data_response(account_id, "account_transactions", NoDataReason.DEPENDENCY_MISSING, details="Plaid integration not yet configured")}


def unlink_account(user_id: str, account_id: str) -> Dict[str, Any]:
    """Unlink a brokerage account."""
    return {"status": "not_available", "reason": "Plaid integration not yet configured", **no_data_response(account_id, "unlink_account", NoDataReason.DEPENDENCY_MISSING, details="Plaid integration not yet configured")}


def get_sync_status(user_id: str) -> Dict[str, Any]:
    """Get sync status for all accounts."""
    return {"status": "not_available", "reason": "Plaid integration not yet configured", **no_data_response(user_id, "sync_status", NoDataReason.DEPENDENCY_MISSING, details="Plaid integration not yet configured")}
