"""
No Data Contract — S0-C Mock Ban
================================
Standard responses when data is unavailable.
NEVER return synthetic/mock data. Return these instead.

Usage:
    from app.core.no_data import no_data_response, NoDataReason

    if not real_data_available:
        return no_data_response(
            entity="AAPL",
            data_type="short_interest",
            reason=NoDataReason.API_UNAVAILABLE
        )
"""

from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime


class NoDataReason(str, Enum):
    """Standard reasons for missing data."""
    API_UNAVAILABLE = "api_unavailable"
    API_ERROR = "api_error"
    API_RATE_LIMITED = "api_rate_limited"
    API_KEY_MISSING = "api_key_missing"
    API_KEY_INVALID = "api_key_invalid"
    ENTITY_NOT_FOUND = "entity_not_found"
    NO_FILINGS = "no_filings"
    NO_TRADES = "no_trades"
    DATA_NOT_PUBLIC = "data_not_public"
    UNSUPPORTED_TICKER = "unsupported_ticker"
    DEPENDENCY_MISSING = "dependency_missing"
    INTEGRATION_NOT_CONFIGURED = "integration_not_configured"
    SERVICE_UNAVAILABLE = "service_unavailable"


# Human-readable messages for each reason
REASON_MESSAGES = {
    NoDataReason.API_UNAVAILABLE: "Data source is temporarily unavailable",
    NoDataReason.API_ERROR: "Error fetching data from source",
    NoDataReason.API_RATE_LIMITED: "Rate limit exceeded, please try again later",
    NoDataReason.API_KEY_MISSING: "API key not configured",
    NoDataReason.API_KEY_INVALID: "API key is invalid or expired",
    NoDataReason.ENTITY_NOT_FOUND: "Entity not found in data source",
    NoDataReason.NO_FILINGS: "No filings available for this entity",
    NoDataReason.NO_TRADES: "No trades found for this period",
    NoDataReason.DATA_NOT_PUBLIC: "Data is not publicly available",
    NoDataReason.UNSUPPORTED_TICKER: "Ticker not supported by data source",
    NoDataReason.DEPENDENCY_MISSING: "Required package not installed",
    NoDataReason.INTEGRATION_NOT_CONFIGURED: "Integration not configured",
    NoDataReason.SERVICE_UNAVAILABLE: "Service not available",
}


def no_data_response(
    entity: str,
    data_type: str,
    reason: NoDataReason,
    source: Optional[str] = None,
    details: Optional[str] = None
) -> Dict[str, Any]:
    """
    Return a standardized no-data response.

    Args:
        entity: The entity being queried (e.g., "AAPL", "Nancy Pelosi")
        data_type: Type of data requested (e.g., "short_interest", "insider_trades")
        reason: Why data is unavailable
        source: Data source that was queried (e.g., "FINRA", "SEC EDGAR")
        details: Additional context

    Returns:
        Standardized response dict with no_data flag
    """
    return {
        "no_data": True,
        "entity": entity,
        "data_type": data_type,
        "reason": reason.value,
        "message": REASON_MESSAGES.get(reason, "Data unavailable"),
        "source": source,
        "details": details,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


def is_no_data_response(response: Any) -> bool:
    """Check if a response is a no-data response."""
    if isinstance(response, dict):
        return response.get("no_data", False) is True
    return False


# Convenience functions for common cases
def api_unavailable(entity: str, data_type: str, source: str) -> Dict[str, Any]:
    """Quick helper for API unavailable."""
    return no_data_response(entity, data_type, NoDataReason.API_UNAVAILABLE, source=source)


def entity_not_found(entity: str, data_type: str, source: str) -> Dict[str, Any]:
    """Quick helper for entity not found."""
    return no_data_response(entity, data_type, NoDataReason.ENTITY_NOT_FOUND, source=source)


def api_key_missing(entity: str, data_type: str, source: str) -> Dict[str, Any]:
    """Quick helper for missing API key."""
    return no_data_response(entity, data_type, NoDataReason.API_KEY_MISSING, source=source)


# BANNED: These imports should NEVER be used
# import random  # BANNED - no synthetic data
# import faker   # BANNED - no fake data
# def _generate_mock_*  # BANNED - no mock generators
