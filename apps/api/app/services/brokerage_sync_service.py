"""
Brokerage Sync Service (#43)
Plaid/OAuth integration with brokers

BLOCKED: Plaid contract not signed.
All functions return no_data responses until Plaid integration is configured.
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from app.core.no_data import no_data_response, NoDataReason


def get_supported_brokers() -> Dict[str, Any]:
    """Get list of supported brokers.

    BLOCKED: Plaid contract not signed.
    Returns no_data response until Plaid integration is configured.
    """
    return no_data_response(
        entity="brokers",
        data_type="supported_brokers",
        reason=NoDataReason.INTEGRATION_NOT_CONFIGURED,
        source="Plaid",
        details="Plaid brokerage integration not configured",
    )


def initiate_link(user_id: str, broker_id: str) -> Dict[str, Any]:
    """Initiate broker linking process.

    BLOCKED: Plaid contract not signed.
    Returns no_data response until Plaid integration is configured.
    """
    return no_data_response(
        entity=broker_id,
        data_type="broker_link",
        reason=NoDataReason.INTEGRATION_NOT_CONFIGURED,
        source="Plaid",
        details="Plaid brokerage integration not configured",
    )


def complete_link(user_id: str, link_token: str, access_token: str) -> Dict[str, Any]:
    """Complete broker linking after OAuth.

    BLOCKED: Plaid contract not signed.
    Returns no_data response until Plaid integration is configured.
    """
    return no_data_response(
        entity=user_id,
        data_type="broker_link_completion",
        reason=NoDataReason.INTEGRATION_NOT_CONFIGURED,
        source="Plaid",
        details="Plaid brokerage integration not configured",
    )


def get_linked_accounts(user_id: str) -> Dict[str, Any]:
    """Get all linked brokerage accounts.

    BLOCKED: Plaid contract not signed.
    Returns no_data response until Plaid integration is configured.
    """
    return no_data_response(
        entity=user_id,
        data_type="linked_accounts",
        reason=NoDataReason.INTEGRATION_NOT_CONFIGURED,
        source="Plaid",
        details="Plaid brokerage integration not configured",
    )


def sync_account(user_id: str, account_id: str) -> Dict[str, Any]:
    """Sync account data from broker.

    BLOCKED: Plaid contract not signed.
    Returns no_data response until Plaid integration is configured.
    """
    return no_data_response(
        entity=account_id,
        data_type="account_sync",
        reason=NoDataReason.INTEGRATION_NOT_CONFIGURED,
        source="Plaid",
        details="Plaid brokerage integration not configured",
    )


def get_account_positions(user_id: str, account_id: str) -> Dict[str, Any]:
    """Get positions from linked account.

    BLOCKED: Plaid contract not signed.
    Returns no_data response until Plaid integration is configured.
    """
    return no_data_response(
        entity=account_id,
        data_type="account_positions",
        reason=NoDataReason.INTEGRATION_NOT_CONFIGURED,
        source="Plaid",
        details="Plaid brokerage integration not configured",
    )


def get_account_transactions(user_id: str, account_id: str, limit: int = 50) -> Dict[str, Any]:
    """Get recent transactions from linked account.

    BLOCKED: Plaid contract not signed.
    Returns no_data response until Plaid integration is configured.
    """
    return no_data_response(
        entity=account_id,
        data_type="account_transactions",
        reason=NoDataReason.INTEGRATION_NOT_CONFIGURED,
        source="Plaid",
        details="Plaid brokerage integration not configured",
    )


def unlink_account(user_id: str, account_id: str) -> Dict[str, Any]:
    """Unlink a brokerage account.

    BLOCKED: Plaid contract not signed.
    Returns no_data response until Plaid integration is configured.
    """
    return no_data_response(
        entity=account_id,
        data_type="unlink_account",
        reason=NoDataReason.INTEGRATION_NOT_CONFIGURED,
        source="Plaid",
        details="Plaid brokerage integration not configured",
    )


def get_sync_status(user_id: str) -> Dict[str, Any]:
    """Get sync status for all accounts.

    BLOCKED: Plaid contract not signed.
    Returns no_data response until Plaid integration is configured.
    """
    return no_data_response(
        entity=user_id,
        data_type="sync_status",
        reason=NoDataReason.INTEGRATION_NOT_CONFIGURED,
        source="Plaid",
        details="Plaid brokerage integration not configured",
    )
