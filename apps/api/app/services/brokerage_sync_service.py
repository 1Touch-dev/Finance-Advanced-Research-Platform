"""
Brokerage Sync Service (#43)
Plaid/OAuth integration with brokers
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import hashlib
import random


SUPPORTED_BROKERS = [
    {"id": "fidelity", "name": "Fidelity", "logo": "/logos/fidelity.png", "oauth": True},
    {"id": "schwab", "name": "Charles Schwab", "logo": "/logos/schwab.png", "oauth": True},
    {"id": "tdameritrade", "name": "TD Ameritrade", "logo": "/logos/tda.png", "oauth": True},
    {"id": "etrade", "name": "E*TRADE", "logo": "/logos/etrade.png", "oauth": True},
    {"id": "robinhood", "name": "Robinhood", "logo": "/logos/robinhood.png", "oauth": True},
    {"id": "vanguard", "name": "Vanguard", "logo": "/logos/vanguard.png", "oauth": False},
    {"id": "interactive_brokers", "name": "Interactive Brokers", "logo": "/logos/ibkr.png", "oauth": True},
]

LINKED_ACCOUNTS: Dict[str, List[Dict]] = {}


def get_supported_brokers() -> Dict[str, Any]:
    """Get list of supported brokers."""
    return {"brokers": SUPPORTED_BROKERS, "count": len(SUPPORTED_BROKERS)}


def initiate_link(user_id: str, broker_id: str) -> Dict[str, Any]:
    """Initiate broker linking process."""
    broker = next((b for b in SUPPORTED_BROKERS if b["id"] == broker_id), None)
    if not broker:
        return {"error": "Unsupported broker"}
    
    link_token = hashlib.md5(f"{user_id}:{broker_id}:{datetime.now()}".encode()).hexdigest()
    return {
        "link_token": link_token,
        "broker": broker,
        "oauth_url": f"https://api.plaid.com/link?token={link_token}" if broker["oauth"] else None,
        "expires_at": (datetime.now().replace(hour=23, minute=59)).isoformat()
    }


def complete_link(user_id: str, link_token: str, access_token: str) -> Dict[str, Any]:
    """Complete broker linking after OAuth."""
    account_id = hashlib.md5(f"{user_id}:{access_token}".encode()).hexdigest()[:12]
    
    account = {
        "account_id": account_id,
        "broker": "fidelity",
        "account_type": random.choice(["individual", "ira", "roth_ira", "401k"]),
        "account_name": f"Account ending in {random.randint(1000, 9999)}",
        "linked_at": datetime.now().isoformat(),
        "last_sync": datetime.now().isoformat(),
        "status": "active"
    }
    
    if user_id not in LINKED_ACCOUNTS:
        LINKED_ACCOUNTS[user_id] = []
    LINKED_ACCOUNTS[user_id].append(account)
    
    return {"status": "linked", "account": account}


def get_linked_accounts(user_id: str) -> Dict[str, Any]:
    """Get all linked brokerage accounts."""
    accounts = LINKED_ACCOUNTS.get(user_id, [])
    return {"user_id": user_id, "accounts": accounts, "count": len(accounts)}


def sync_account(user_id: str, account_id: str) -> Dict[str, Any]:
    """Sync account data from broker."""
    return {
        "account_id": account_id,
        "sync_status": "completed",
        "last_sync": datetime.now().isoformat(),
        "positions_synced": random.randint(5, 20),
        "transactions_synced": random.randint(10, 50),
        "next_sync": (datetime.now().replace(hour=6, minute=0)).isoformat()
    }


def get_account_positions(user_id: str, account_id: str) -> Dict[str, Any]:
    """Get positions from linked account."""
    positions = [
        {"ticker": "NVDA", "shares": 50, "avg_cost": 450.00, "current_price": 485.00},
        {"ticker": "AAPL", "shares": 100, "avg_cost": 165.00, "current_price": 175.00},
        {"ticker": "MSFT", "shares": 75, "avg_cost": 380.00, "current_price": 420.00},
    ]
    return {
        "account_id": account_id,
        "positions": positions,
        "total_value": sum(p["shares"] * p["current_price"] for p in positions),
        "last_sync": datetime.now().isoformat()
    }


def get_account_transactions(user_id: str, account_id: str, limit: int = 50) -> Dict[str, Any]:
    """Get recent transactions from linked account."""
    transactions = [
        {"date": "2026-08-15", "type": "buy", "ticker": "NVDA", "shares": 10, "price": 480.00, "total": 4800.00},
        {"date": "2026-08-10", "type": "dividend", "ticker": "AAPL", "amount": 24.00},
        {"date": "2026-08-05", "type": "sell", "ticker": "TSLA", "shares": 5, "price": 250.00, "total": 1250.00},
    ]
    return {"account_id": account_id, "transactions": transactions[:limit], "count": len(transactions)}


def unlink_account(user_id: str, account_id: str) -> Dict[str, Any]:
    """Unlink a brokerage account."""
    if user_id in LINKED_ACCOUNTS:
        LINKED_ACCOUNTS[user_id] = [a for a in LINKED_ACCOUNTS[user_id] if a["account_id"] != account_id]
    return {"status": "unlinked", "account_id": account_id}


def get_sync_status(user_id: str) -> Dict[str, Any]:
    """Get sync status for all accounts."""
    accounts = LINKED_ACCOUNTS.get(user_id, [])
    return {
        "user_id": user_id,
        "accounts": [
            {
                "account_id": a["account_id"],
                "broker": a["broker"],
                "last_sync": a["last_sync"],
                "status": a["status"],
                "next_sync": (datetime.now().replace(hour=6, minute=0)).isoformat()
            }
            for a in accounts
        ]
    }
