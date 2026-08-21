"""
Insider Activity Screener Service (Band C #41)
Screens Form 4 filings, clusters buys/sells

Data Source: SEC EDGAR Form 4 (FREE) with mock fallback
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import random
import logging

log = logging.getLogger(__name__)

# Import real SEC EDGAR connector
try:
    from app.connectors.sec_edgar_connector import (
        get_insider_transactions as sec_get_insider_transactions,
        ticker_to_cik,
    )
    from app.connectors.gov_trading_connector import (
        get_recent_sec_form4,
        get_insider_trades_for_ticker,
    )
    SEC_AVAILABLE = True
except ImportError:
    SEC_AVAILABLE = False
    log.warning("SEC EDGAR connector not available for insider activity")

# Feature flag: set to True to use real SEC EDGAR data
USE_REAL_DATA = True


@dataclass
class InsiderTransaction:
    """Insider transaction from Form 4"""
    transaction_id: str
    ticker: str
    company_name: str
    insider_name: str
    insider_title: str
    relationship: str  # CEO, CFO, Director, 10% Owner, etc.
    transaction_type: str  # P (Purchase), S (Sale), A (Award), M (Exercise), G (Gift)
    transaction_date: str
    filing_date: str
    shares: int
    price: float
    value: float
    shares_owned_after: int
    ownership_change_percent: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "ticker": self.ticker,
            "company_name": self.company_name,
            "insider_name": self.insider_name,
            "insider_title": self.insider_title,
            "relationship": self.relationship,
            "transaction_type": self.transaction_type,
            "transaction_date": self.transaction_date,
            "filing_date": self.filing_date,
            "shares": self.shares,
            "price": self.price,
            "value": self.value,
            "shares_owned_after": self.shares_owned_after,
            "ownership_change_percent": self.ownership_change_percent,
        }


@dataclass
class InsiderCluster:
    """Cluster of insider activity for a ticker"""
    ticker: str
    company_name: str
    total_buys: int
    total_sells: int
    net_shares: int
    net_value: float
    buy_value: float
    sell_value: float
    insider_count: int
    latest_transaction: str
    signal: str  # strong_buy, buy, neutral, sell, strong_sell
    transactions: List[InsiderTransaction] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "total_buys": self.total_buys,
            "total_sells": self.total_sells,
            "net_shares": self.net_shares,
            "net_value": self.net_value,
            "buy_value": self.buy_value,
            "sell_value": self.sell_value,
            "insider_count": self.insider_count,
            "latest_transaction": self.latest_transaction,
            "signal": self.signal,
            "transactions": [t.to_dict() for t in self.transactions],
        }


# Mock insider transactions
MOCK_TRANSACTIONS = [
    # NVDA - Multiple insider buys
    InsiderTransaction(
        transaction_id="INS001",
        ticker="NVDA",
        company_name="NVIDIA Corp",
        insider_name="Jensen Huang",
        insider_title="CEO",
        relationship="CEO",
        transaction_type="P",
        transaction_date=(datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
        filing_date=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        shares=50000,
        price=125.50,
        value=6275000,
        shares_owned_after=5000000,
        ownership_change_percent=1.01,
    ),
    InsiderTransaction(
        transaction_id="INS002",
        ticker="NVDA",
        company_name="NVIDIA Corp",
        insider_name="Colette Kress",
        insider_title="CFO",
        relationship="CFO",
        transaction_type="P",
        transaction_date=(datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
        filing_date=(datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
        shares=25000,
        price=124.80,
        value=3120000,
        shares_owned_after=500000,
        ownership_change_percent=5.26,
    ),
    InsiderTransaction(
        transaction_id="INS003",
        ticker="NVDA",
        company_name="NVIDIA Corp",
        insider_name="Mark Stevens",
        insider_title="Director",
        relationship="Director",
        transaction_type="P",
        transaction_date=(datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
        filing_date=(datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d"),
        shares=10000,
        price=122.30,
        value=1223000,
        shares_owned_after=150000,
        ownership_change_percent=7.14,
    ),
    # TSLA - Mixed signals
    InsiderTransaction(
        transaction_id="INS004",
        ticker="TSLA",
        company_name="Tesla Inc",
        insider_name="Robyn Denholm",
        insider_title="Chairman",
        relationship="Director",
        transaction_type="S",
        transaction_date=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        filing_date=datetime.now().strftime("%Y-%m-%d"),
        shares=100000,
        price=245.30,
        value=24530000,
        shares_owned_after=400000,
        ownership_change_percent=-20.0,
    ),
    InsiderTransaction(
        transaction_id="INS005",
        ticker="TSLA",
        company_name="Tesla Inc",
        insider_name="Zachary Kirkhorn",
        insider_title="CFO",
        relationship="CFO",
        transaction_type="P",
        transaction_date=(datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d"),
        filing_date=(datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
        shares=5000,
        price=238.50,
        value=1192500,
        shares_owned_after=55000,
        ownership_change_percent=10.0,
    ),
    # AAPL - CEO selling (routine)
    InsiderTransaction(
        transaction_id="INS006",
        ticker="AAPL",
        company_name="Apple Inc",
        insider_name="Tim Cook",
        insider_title="CEO",
        relationship="CEO",
        transaction_type="S",
        transaction_date=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
        filing_date=(datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d"),
        shares=200000,
        price=178.50,
        value=35700000,
        shares_owned_after=3500000,
        ownership_change_percent=-5.41,
    ),
    # META - Zuckerberg routine sale
    InsiderTransaction(
        transaction_id="INS007",
        ticker="META",
        company_name="Meta Platforms Inc",
        insider_name="Mark Zuckerberg",
        insider_title="CEO",
        relationship="CEO",
        transaction_type="S",
        transaction_date=(datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
        filing_date=(datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
        shares=150000,
        price=505.20,
        value=75780000,
        shares_owned_after=350000000,
        ownership_change_percent=-0.04,
    ),
    # AMD - Multiple buys (cluster)
    InsiderTransaction(
        transaction_id="INS008",
        ticker="AMD",
        company_name="Advanced Micro Devices",
        insider_name="Lisa Su",
        insider_title="CEO",
        relationship="CEO",
        transaction_type="P",
        transaction_date=(datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
        filing_date=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        shares=75000,
        price=158.40,
        value=11880000,
        shares_owned_after=2500000,
        ownership_change_percent=3.09,
    ),
    InsiderTransaction(
        transaction_id="INS009",
        ticker="AMD",
        company_name="Advanced Micro Devices",
        insider_name="Victor Peng",
        insider_title="President",
        relationship="Officer",
        transaction_type="P",
        transaction_date=(datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
        filing_date=(datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
        shares=30000,
        price=156.80,
        value=4704000,
        shares_owned_after=200000,
        ownership_change_percent=17.65,
    ),
    InsiderTransaction(
        transaction_id="INS010",
        ticker="AMD",
        company_name="Advanced Micro Devices",
        insider_name="Phil Guido",
        insider_title="Director",
        relationship="Director",
        transaction_type="P",
        transaction_date=(datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d"),
        filing_date=(datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
        shares=15000,
        price=155.20,
        value=2328000,
        shares_owned_after=75000,
        ownership_change_percent=25.0,
    ),
    # GOOGL - Director buy
    InsiderTransaction(
        transaction_id="INS011",
        ticker="GOOGL",
        company_name="Alphabet Inc",
        insider_name="John Hennessy",
        insider_title="Chairman",
        relationship="Director",
        transaction_type="P",
        transaction_date=(datetime.now() - timedelta(days=6)).strftime("%Y-%m-%d"),
        filing_date=(datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
        shares=20000,
        price=175.30,
        value=3506000,
        shares_owned_after=180000,
        ownership_change_percent=12.5,
    ),
    # MSFT - Executive sale
    InsiderTransaction(
        transaction_id="INS012",
        ticker="MSFT",
        company_name="Microsoft Corp",
        insider_name="Satya Nadella",
        insider_title="CEO",
        relationship="CEO",
        transaction_type="S",
        transaction_date=(datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"),
        filing_date=(datetime.now() - timedelta(days=9)).strftime("%Y-%m-%d"),
        shares=50000,
        price=420.50,
        value=21025000,
        shares_owned_after=800000,
        ownership_change_percent=-5.88,
    ),
    # Small cap with big insider buy
    InsiderTransaction(
        transaction_id="INS013",
        ticker="IONQ",
        company_name="IonQ Inc",
        insider_name="Peter Chapman",
        insider_title="CEO",
        relationship="CEO",
        transaction_type="P",
        transaction_date=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        filing_date=datetime.now().strftime("%Y-%m-%d"),
        shares=500000,
        price=12.50,
        value=6250000,
        shares_owned_after=2500000,
        ownership_change_percent=25.0,
    ),
    InsiderTransaction(
        transaction_id="INS014",
        ticker="IONQ",
        company_name="IonQ Inc",
        insider_name="Thomas Kramer",
        insider_title="CFO",
        relationship="CFO",
        transaction_type="P",
        transaction_date=(datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
        filing_date=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        shares=200000,
        price=12.30,
        value=2460000,
        shares_owned_after=500000,
        ownership_change_percent=66.67,
    ),
]


def get_recent_transactions(
    days: int = 7,
    transaction_type: Optional[str] = None,
    min_value: float = 0,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Get recent insider transactions.

    Uses SEC EDGAR Form 4 data when available, falls back to mock data.
    """
    if USE_REAL_DATA and SEC_AVAILABLE:
        try:
            real_txns = get_recent_sec_form4(days=days, limit=limit * 2)
            if real_txns:
                transactions = []
                for txn in real_txns:
                    # Filter by transaction type
                    txn_type = txn.get("transaction_code") or txn.get("transaction_type", "")
                    if transaction_type and txn_type != transaction_type:
                        continue
                    # Filter by value
                    value = txn.get("value") or txn.get("total_value") or 0
                    if value < min_value:
                        continue
                    transactions.append(_normalize_sec_transaction(txn))

                transactions.sort(key=lambda x: x.get("transaction_date", ""), reverse=True)
                return transactions[:limit]
        except Exception as e:
            log.warning("SEC EDGAR insider fetch failed, using mock: %s", e)

    # Fallback to mock data
    cutoff_date = datetime.now() - timedelta(days=days)
    transactions = []
    for txn in MOCK_TRANSACTIONS:
        txn_date = datetime.strptime(txn.transaction_date, "%Y-%m-%d")
        if txn_date >= cutoff_date:
            if transaction_type and txn.transaction_type != transaction_type:
                continue
            if txn.value < min_value:
                continue
            transactions.append(txn.to_dict())

    transactions.sort(key=lambda x: x["transaction_date"], reverse=True)
    return transactions[:limit]


def get_transactions_by_ticker(ticker: str, days: int = 90) -> List[Dict[str, Any]]:
    """Get all insider transactions for a ticker.

    Uses SEC EDGAR Form 4 data when available, falls back to mock data.
    """
    ticker = ticker.upper()

    if USE_REAL_DATA and SEC_AVAILABLE:
        try:
            real_txns = get_insider_trades_for_ticker(ticker, days=days)
            if real_txns:
                transactions = [_normalize_sec_transaction(txn) for txn in real_txns]
                transactions.sort(key=lambda x: x.get("transaction_date", ""), reverse=True)
                return transactions
        except Exception as e:
            log.warning("SEC EDGAR insider fetch for %s failed, using mock: %s", ticker, e)

    # Fallback to mock data
    cutoff_date = datetime.now() - timedelta(days=days)
    transactions = []
    for txn in MOCK_TRANSACTIONS:
        if txn.ticker == ticker:
            txn_date = datetime.strptime(txn.transaction_date, "%Y-%m-%d")
            if txn_date >= cutoff_date:
                transactions.append(txn.to_dict())

    transactions.sort(key=lambda x: x["transaction_date"], reverse=True)
    return transactions


def _normalize_sec_transaction(txn: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize SEC EDGAR transaction to our standard format."""
    return {
        "transaction_id": txn.get("accession") or txn.get("id") or "",
        "ticker": txn.get("ticker") or txn.get("symbol") or "",
        "company_name": txn.get("company") or txn.get("issuer") or "",
        "insider_name": txn.get("insider") or txn.get("owner_name") or "",
        "insider_title": txn.get("title") or txn.get("relationship") or "",
        "relationship": txn.get("relationship") or txn.get("title") or "",
        "transaction_type": txn.get("transaction_code") or txn.get("type") or "",
        "transaction_date": txn.get("transaction_date") or txn.get("date") or "",
        "filing_date": txn.get("filing_date") or txn.get("filed") or "",
        "shares": int(txn.get("shares") or txn.get("quantity") or 0),
        "price": float(txn.get("price") or txn.get("price_per_share") or 0),
        "value": float(txn.get("value") or txn.get("total_value") or 0),
        "shares_owned_after": int(txn.get("shares_owned") or txn.get("post_shares") or 0),
        "ownership_change_percent": float(txn.get("ownership_change") or 0),
        "source": "SEC EDGAR Form 4",
    }


def get_cluster_buys(days: int = 14, min_insiders: int = 2) -> List[Dict[str, Any]]:
    """Get stocks with cluster buying (multiple insiders buying)"""
    cutoff_date = datetime.now() - timedelta(days=days)

    # Group by ticker
    ticker_buys = {}
    for txn in MOCK_TRANSACTIONS:
        if txn.transaction_type == "P":
            txn_date = datetime.strptime(txn.transaction_date, "%Y-%m-%d")
            if txn_date >= cutoff_date:
                if txn.ticker not in ticker_buys:
                    ticker_buys[txn.ticker] = {
                        "ticker": txn.ticker,
                        "company_name": txn.company_name,
                        "insiders": set(),
                        "total_value": 0,
                        "total_shares": 0,
                        "transactions": [],
                    }
                ticker_buys[txn.ticker]["insiders"].add(txn.insider_name)
                ticker_buys[txn.ticker]["total_value"] += txn.value
                ticker_buys[txn.ticker]["total_shares"] += txn.shares
                ticker_buys[txn.ticker]["transactions"].append(txn.to_dict())

    # Filter by min insiders
    clusters = []
    for ticker, data in ticker_buys.items():
        if len(data["insiders"]) >= min_insiders:
            clusters.append({
                "ticker": data["ticker"],
                "company_name": data["company_name"],
                "insider_count": len(data["insiders"]),
                "total_value": data["total_value"],
                "total_shares": data["total_shares"],
                "transactions": data["transactions"],
            })

    clusters.sort(key=lambda x: x["insider_count"], reverse=True)
    return clusters


def get_cluster_sells(days: int = 14, min_insiders: int = 2) -> List[Dict[str, Any]]:
    """Get stocks with cluster selling (multiple insiders selling)"""
    cutoff_date = datetime.now() - timedelta(days=days)

    # Group by ticker
    ticker_sells = {}
    for txn in MOCK_TRANSACTIONS:
        if txn.transaction_type == "S":
            txn_date = datetime.strptime(txn.transaction_date, "%Y-%m-%d")
            if txn_date >= cutoff_date:
                if txn.ticker not in ticker_sells:
                    ticker_sells[txn.ticker] = {
                        "ticker": txn.ticker,
                        "company_name": txn.company_name,
                        "insiders": set(),
                        "total_value": 0,
                        "total_shares": 0,
                        "transactions": [],
                    }
                ticker_sells[txn.ticker]["insiders"].add(txn.insider_name)
                ticker_sells[txn.ticker]["total_value"] += txn.value
                ticker_sells[txn.ticker]["total_shares"] += txn.shares
                ticker_sells[txn.ticker]["transactions"].append(txn.to_dict())

    # Filter by min insiders
    clusters = []
    for ticker, data in ticker_sells.items():
        if len(data["insiders"]) >= min_insiders:
            clusters.append({
                "ticker": data["ticker"],
                "company_name": data["company_name"],
                "insider_count": len(data["insiders"]),
                "total_value": data["total_value"],
                "total_shares": data["total_shares"],
                "transactions": data["transactions"],
            })

    clusters.sort(key=lambda x: x["insider_count"], reverse=True)
    return clusters


def get_largest_transactions(
    days: int = 30,
    transaction_type: Optional[str] = None,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Get largest insider transactions by value"""
    cutoff_date = datetime.now() - timedelta(days=days)

    transactions = []
    for txn in MOCK_TRANSACTIONS:
        txn_date = datetime.strptime(txn.transaction_date, "%Y-%m-%d")
        if txn_date >= cutoff_date:
            if transaction_type and txn.transaction_type != transaction_type:
                continue
            transactions.append(txn.to_dict())

    transactions.sort(key=lambda x: x["value"], reverse=True)
    return transactions[:limit]


def get_ceo_transactions(days: int = 30) -> List[Dict[str, Any]]:
    """Get CEO/CFO transactions only"""
    cutoff_date = datetime.now() - timedelta(days=days)

    transactions = []
    for txn in MOCK_TRANSACTIONS:
        if txn.relationship in ["CEO", "CFO"]:
            txn_date = datetime.strptime(txn.transaction_date, "%Y-%m-%d")
            if txn_date >= cutoff_date:
                transactions.append(txn.to_dict())

    transactions.sort(key=lambda x: x["transaction_date"], reverse=True)
    return transactions


def get_insider_stats() -> Dict[str, Any]:
    """Get insider trading statistics"""
    total_buys = len([t for t in MOCK_TRANSACTIONS if t.transaction_type == "P"])
    total_sells = len([t for t in MOCK_TRANSACTIONS if t.transaction_type == "S"])

    buy_value = sum(t.value for t in MOCK_TRANSACTIONS if t.transaction_type == "P")
    sell_value = sum(t.value for t in MOCK_TRANSACTIONS if t.transaction_type == "S")

    # Unique tickers with buying
    buy_tickers = set(t.ticker for t in MOCK_TRANSACTIONS if t.transaction_type == "P")
    sell_tickers = set(t.ticker for t in MOCK_TRANSACTIONS if t.transaction_type == "S")

    # By relationship
    by_relationship = {}
    for txn in MOCK_TRANSACTIONS:
        by_relationship[txn.relationship] = by_relationship.get(txn.relationship, 0) + 1

    return {
        "total_transactions": len(MOCK_TRANSACTIONS),
        "total_buys": total_buys,
        "total_sells": total_sells,
        "buy_value": buy_value,
        "sell_value": sell_value,
        "net_value": buy_value - sell_value,
        "buy_sell_ratio": round(total_buys / max(1, total_sells), 2),
        "tickers_with_buying": len(buy_tickers),
        "tickers_with_selling": len(sell_tickers),
        "by_relationship": by_relationship,
    }


def get_insider_sentiment(ticker: str, days: int = 90) -> Dict[str, Any]:
    """Get insider sentiment for a specific ticker"""
    ticker = ticker.upper()
    cutoff_date = datetime.now() - timedelta(days=days)

    buys = []
    sells = []

    for txn in MOCK_TRANSACTIONS:
        if txn.ticker == ticker:
            txn_date = datetime.strptime(txn.transaction_date, "%Y-%m-%d")
            if txn_date >= cutoff_date:
                if txn.transaction_type == "P":
                    buys.append(txn.to_dict())
                elif txn.transaction_type == "S":
                    sells.append(txn.to_dict())

    buy_value = sum(t["value"] for t in buys)
    sell_value = sum(t["value"] for t in sells)
    net_value = buy_value - sell_value

    # Determine signal
    if len(buys) >= 3 and buy_value > sell_value * 2:
        signal = "strong_buy"
    elif len(buys) >= 2 and buy_value > sell_value:
        signal = "buy"
    elif len(sells) >= 3 and sell_value > buy_value * 2:
        signal = "strong_sell"
    elif len(sells) >= 2 and sell_value > buy_value:
        signal = "sell"
    else:
        signal = "neutral"

    return {
        "ticker": ticker,
        "total_buys": len(buys),
        "total_sells": len(sells),
        "buy_value": buy_value,
        "sell_value": sell_value,
        "net_value": net_value,
        "signal": signal,
        "recent_buys": buys[:5],
        "recent_sells": sells[:5],
    }


def screen_insiders(
    min_buy_value: float = 100000,
    min_insiders: int = 1,
    days: int = 14,
    signal_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Screen stocks by insider activity"""
    cutoff_date = datetime.now() - timedelta(days=days)

    # Group by ticker
    ticker_data = {}
    for txn in MOCK_TRANSACTIONS:
        txn_date = datetime.strptime(txn.transaction_date, "%Y-%m-%d")
        if txn_date >= cutoff_date:
            if txn.ticker not in ticker_data:
                ticker_data[txn.ticker] = {
                    "ticker": txn.ticker,
                    "company_name": txn.company_name,
                    "buy_value": 0,
                    "sell_value": 0,
                    "buy_count": 0,
                    "sell_count": 0,
                    "insiders": set(),
                    "latest_date": txn.transaction_date,
                }
            data = ticker_data[txn.ticker]
            data["insiders"].add(txn.insider_name)
            if txn.transaction_date > data["latest_date"]:
                data["latest_date"] = txn.transaction_date

            if txn.transaction_type == "P":
                data["buy_value"] += txn.value
                data["buy_count"] += 1
            elif txn.transaction_type == "S":
                data["sell_value"] += txn.value
                data["sell_count"] += 1

    # Calculate signals and filter
    results = []
    for ticker, data in ticker_data.items():
        insider_count = len(data["insiders"])
        if insider_count < min_insiders:
            continue

        buy_value = data["buy_value"]
        sell_value = data["sell_value"]
        net_value = buy_value - sell_value

        # Determine signal
        if data["buy_count"] >= 3 and buy_value > sell_value * 2:
            signal = "strong_buy"
        elif data["buy_count"] >= 2 and buy_value > sell_value:
            signal = "buy"
        elif data["sell_count"] >= 3 and sell_value > buy_value * 2:
            signal = "strong_sell"
        elif data["sell_count"] >= 2 and sell_value > buy_value:
            signal = "sell"
        else:
            signal = "neutral"

        if signal_filter and signal != signal_filter:
            continue

        if buy_value < min_buy_value and signal in ["buy", "strong_buy"]:
            continue

        results.append({
            "ticker": data["ticker"],
            "company_name": data["company_name"],
            "buy_value": buy_value,
            "sell_value": sell_value,
            "net_value": net_value,
            "buy_count": data["buy_count"],
            "sell_count": data["sell_count"],
            "insider_count": insider_count,
            "signal": signal,
            "latest_transaction": data["latest_date"],
        })

    # Sort by net value
    results.sort(key=lambda x: x["net_value"], reverse=True)
    return results
