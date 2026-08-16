"""
Cost Basis Tracking Service (Band C #42)
Track purchase prices, calculate gains/losses
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum
import random


class CostBasisMethod(str, Enum):
    FIFO = "fifo"
    LIFO = "lifo"
    AVERAGE = "average"
    SPECIFIC = "specific"


@dataclass
class Position:
    """A position/lot in a portfolio"""
    lot_id: str
    ticker: str
    shares: float
    purchase_price: float
    purchase_date: str
    current_price: float = 0.0

    @property
    def cost_basis(self) -> float:
        return self.shares * self.purchase_price

    @property
    def market_value(self) -> float:
        return self.shares * self.current_price

    @property
    def unrealized_gain(self) -> float:
        return self.market_value - self.cost_basis

    @property
    def unrealized_gain_percent(self) -> float:
        if self.cost_basis == 0:
            return 0
        return (self.unrealized_gain / self.cost_basis) * 100

    @property
    def holding_days(self) -> int:
        purchase = datetime.strptime(self.purchase_date, "%Y-%m-%d")
        return (datetime.now() - purchase).days

    @property
    def is_long_term(self) -> bool:
        return self.holding_days > 365

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lot_id": self.lot_id,
            "ticker": self.ticker,
            "shares": self.shares,
            "purchase_price": self.purchase_price,
            "purchase_date": self.purchase_date,
            "current_price": self.current_price,
            "cost_basis": round(self.cost_basis, 2),
            "market_value": round(self.market_value, 2),
            "unrealized_gain": round(self.unrealized_gain, 2),
            "unrealized_gain_percent": round(self.unrealized_gain_percent, 2),
            "holding_days": self.holding_days,
            "is_long_term": self.is_long_term,
        }


# Mock portfolio data
MOCK_POSITIONS: Dict[str, List[Position]] = {
    "demo_user": [
        Position("LOT001", "AAPL", 100, 145.50, "2023-01-15", 178.50),
        Position("LOT002", "AAPL", 50, 168.20, "2023-08-10", 178.50),
        Position("LOT003", "AAPL", 25, 185.00, "2024-02-20", 178.50),
        Position("LOT004", "NVDA", 200, 45.30, "2022-06-01", 125.80),
        Position("LOT005", "NVDA", 100, 85.50, "2023-05-15", 125.80),
        Position("LOT006", "MSFT", 75, 285.00, "2023-03-01", 420.50),
        Position("LOT007", "MSFT", 50, 350.00, "2024-01-10", 420.50),
        Position("LOT008", "GOOGL", 60, 125.00, "2023-07-20", 175.30),
        Position("LOT009", "TSLA", 80, 195.00, "2023-09-01", 245.30),
        Position("LOT010", "TSLA", 40, 265.00, "2024-03-15", 245.30),
        Position("LOT011", "AMD", 150, 95.00, "2023-04-10", 158.40),
        Position("LOT012", "META", 45, 285.00, "2023-06-01", 505.20),
    ],
}


def get_user_positions(user_id: str, ticker: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all positions for a user"""
    positions = MOCK_POSITIONS.get(user_id, [])
    if ticker:
        positions = [p for p in positions if p.ticker == ticker.upper()]
    return [p.to_dict() for p in positions]


def get_position_by_lot(user_id: str, lot_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific lot"""
    positions = MOCK_POSITIONS.get(user_id, [])
    for p in positions:
        if p.lot_id == lot_id:
            return p.to_dict()
    return None


def get_portfolio_summary(user_id: str) -> Dict[str, Any]:
    """Get portfolio cost basis summary"""
    positions = MOCK_POSITIONS.get(user_id, [])

    total_cost_basis = sum(p.cost_basis for p in positions)
    total_market_value = sum(p.market_value for p in positions)
    total_unrealized_gain = total_market_value - total_cost_basis

    # Group by ticker
    by_ticker = {}
    for p in positions:
        if p.ticker not in by_ticker:
            by_ticker[p.ticker] = {
                "ticker": p.ticker,
                "total_shares": 0,
                "total_cost_basis": 0,
                "total_market_value": 0,
                "avg_cost_per_share": 0,
                "current_price": p.current_price,
                "lots": 0,
            }
        by_ticker[p.ticker]["total_shares"] += p.shares
        by_ticker[p.ticker]["total_cost_basis"] += p.cost_basis
        by_ticker[p.ticker]["total_market_value"] += p.market_value
        by_ticker[p.ticker]["lots"] += 1

    # Calculate averages
    for ticker, data in by_ticker.items():
        data["avg_cost_per_share"] = round(data["total_cost_basis"] / data["total_shares"], 2)
        data["unrealized_gain"] = round(data["total_market_value"] - data["total_cost_basis"], 2)
        data["unrealized_gain_percent"] = round(
            (data["unrealized_gain"] / data["total_cost_basis"]) * 100, 2
        ) if data["total_cost_basis"] > 0 else 0

    # Long term vs short term
    long_term_gain = sum(p.unrealized_gain for p in positions if p.is_long_term)
    short_term_gain = sum(p.unrealized_gain for p in positions if not p.is_long_term)

    return {
        "total_cost_basis": round(total_cost_basis, 2),
        "total_market_value": round(total_market_value, 2),
        "total_unrealized_gain": round(total_unrealized_gain, 2),
        "total_unrealized_gain_percent": round(
            (total_unrealized_gain / total_cost_basis) * 100, 2
        ) if total_cost_basis > 0 else 0,
        "long_term_gain": round(long_term_gain, 2),
        "short_term_gain": round(short_term_gain, 2),
        "positions_count": len(positions),
        "tickers_count": len(by_ticker),
        "by_ticker": list(by_ticker.values()),
    }


def get_ticker_cost_basis(user_id: str, ticker: str) -> Dict[str, Any]:
    """Get cost basis details for a specific ticker"""
    positions = MOCK_POSITIONS.get(user_id, [])
    ticker_positions = [p for p in positions if p.ticker == ticker.upper()]

    if not ticker_positions:
        return {"ticker": ticker.upper(), "positions": [], "summary": None}

    total_shares = sum(p.shares for p in ticker_positions)
    total_cost = sum(p.cost_basis for p in ticker_positions)
    total_value = sum(p.market_value for p in ticker_positions)

    return {
        "ticker": ticker.upper(),
        "positions": [p.to_dict() for p in ticker_positions],
        "summary": {
            "total_shares": total_shares,
            "total_cost_basis": round(total_cost, 2),
            "total_market_value": round(total_value, 2),
            "avg_cost_per_share": round(total_cost / total_shares, 2),
            "current_price": ticker_positions[0].current_price,
            "unrealized_gain": round(total_value - total_cost, 2),
            "unrealized_gain_percent": round(
                ((total_value - total_cost) / total_cost) * 100, 2
            ) if total_cost > 0 else 0,
        },
    }


def calculate_realized_gain(
    user_id: str,
    ticker: str,
    shares_to_sell: float,
    method: CostBasisMethod = CostBasisMethod.FIFO,
    specific_lots: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Calculate realized gain for a potential sale"""
    positions = MOCK_POSITIONS.get(user_id, [])
    ticker_positions = [p for p in positions if p.ticker == ticker.upper()]

    if not ticker_positions:
        return {"error": f"No positions found for {ticker}"}

    total_shares = sum(p.shares for p in ticker_positions)
    if shares_to_sell > total_shares:
        return {"error": f"Not enough shares. Have {total_shares}, trying to sell {shares_to_sell}"}

    current_price = ticker_positions[0].current_price

    # Sort positions based on method
    if method == CostBasisMethod.FIFO:
        sorted_positions = sorted(ticker_positions, key=lambda p: p.purchase_date)
    elif method == CostBasisMethod.LIFO:
        sorted_positions = sorted(ticker_positions, key=lambda p: p.purchase_date, reverse=True)
    elif method == CostBasisMethod.SPECIFIC and specific_lots:
        sorted_positions = [p for p in ticker_positions if p.lot_id in specific_lots]
    else:
        sorted_positions = ticker_positions

    # Calculate gain
    remaining_to_sell = shares_to_sell
    lots_used = []
    total_cost_basis = 0
    long_term_gain = 0
    short_term_gain = 0

    for position in sorted_positions:
        if remaining_to_sell <= 0:
            break

        shares_from_lot = min(position.shares, remaining_to_sell)
        cost_from_lot = shares_from_lot * position.purchase_price
        proceeds = shares_from_lot * current_price
        gain = proceeds - cost_from_lot

        lots_used.append({
            "lot_id": position.lot_id,
            "shares_sold": shares_from_lot,
            "cost_basis": round(cost_from_lot, 2),
            "proceeds": round(proceeds, 2),
            "gain": round(gain, 2),
            "is_long_term": position.is_long_term,
            "holding_days": position.holding_days,
        })

        total_cost_basis += cost_from_lot
        if position.is_long_term:
            long_term_gain += gain
        else:
            short_term_gain += gain

        remaining_to_sell -= shares_from_lot

    total_proceeds = shares_to_sell * current_price
    total_gain = total_proceeds - total_cost_basis

    return {
        "ticker": ticker.upper(),
        "shares_sold": shares_to_sell,
        "method": method.value,
        "current_price": current_price,
        "total_proceeds": round(total_proceeds, 2),
        "total_cost_basis": round(total_cost_basis, 2),
        "total_realized_gain": round(total_gain, 2),
        "long_term_gain": round(long_term_gain, 2),
        "short_term_gain": round(short_term_gain, 2),
        "lots_used": lots_used,
    }


def get_tax_lot_comparison(user_id: str, ticker: str, shares_to_sell: float) -> Dict[str, Any]:
    """Compare different cost basis methods for tax planning"""
    methods = [CostBasisMethod.FIFO, CostBasisMethod.LIFO, CostBasisMethod.AVERAGE]
    comparisons = []

    for method in methods:
        result = calculate_realized_gain(user_id, ticker, shares_to_sell, method)
        if "error" not in result:
            comparisons.append({
                "method": method.value,
                "total_gain": result["total_realized_gain"],
                "long_term_gain": result["long_term_gain"],
                "short_term_gain": result["short_term_gain"],
                "lots_used": len(result["lots_used"]),
            })

    # Find optimal for tax (minimize short-term gains)
    if comparisons:
        optimal = min(comparisons, key=lambda x: x["short_term_gain"])
        for c in comparisons:
            c["is_optimal"] = c["method"] == optimal["method"]

    return {
        "ticker": ticker.upper(),
        "shares_to_sell": shares_to_sell,
        "comparisons": comparisons,
    }


def get_gains_by_holding_period(user_id: str) -> Dict[str, Any]:
    """Get unrealized gains grouped by holding period"""
    positions = MOCK_POSITIONS.get(user_id, [])

    long_term = [p for p in positions if p.is_long_term]
    short_term = [p for p in positions if not p.is_long_term]

    return {
        "long_term": {
            "positions": len(long_term),
            "total_cost_basis": round(sum(p.cost_basis for p in long_term), 2),
            "total_market_value": round(sum(p.market_value for p in long_term), 2),
            "unrealized_gain": round(sum(p.unrealized_gain for p in long_term), 2),
        },
        "short_term": {
            "positions": len(short_term),
            "total_cost_basis": round(sum(p.cost_basis for p in short_term), 2),
            "total_market_value": round(sum(p.market_value for p in short_term), 2),
            "unrealized_gain": round(sum(p.unrealized_gain for p in short_term), 2),
        },
        "approaching_long_term": [
            {
                **p.to_dict(),
                "days_until_long_term": 365 - p.holding_days,
            }
            for p in short_term if 300 <= p.holding_days < 365
        ],
    }


def add_position(
    user_id: str,
    ticker: str,
    shares: float,
    purchase_price: float,
    purchase_date: str,
) -> Dict[str, Any]:
    """Add a new position/lot"""
    if user_id not in MOCK_POSITIONS:
        MOCK_POSITIONS[user_id] = []

    lot_id = f"LOT{len(MOCK_POSITIONS[user_id]) + 1:03d}"
    position = Position(
        lot_id=lot_id,
        ticker=ticker.upper(),
        shares=shares,
        purchase_price=purchase_price,
        purchase_date=purchase_date,
        current_price=purchase_price,  # Would be fetched from market data
    )
    MOCK_POSITIONS[user_id].append(position)

    return position.to_dict()
