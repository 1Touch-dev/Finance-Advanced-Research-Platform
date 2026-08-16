"""
Tax Lot Optimization Service (Band C #45)
FIFO/LIFO/specific lot selection for tax optimization
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum


class TaxMethod(str, Enum):
    FIFO = "fifo"
    LIFO = "lifo"
    HIFO = "hifo"  # Highest In First Out (minimize gains)
    LOFO = "lofo"  # Lowest In First Out (maximize gains for losses)
    SPECIFIC = "specific"


@dataclass
class TaxLot:
    """A tax lot for a position"""
    lot_id: str
    ticker: str
    shares: float
    cost_per_share: float
    purchase_date: str
    current_price: float

    @property
    def cost_basis(self) -> float:
        return self.shares * self.cost_per_share

    @property
    def market_value(self) -> float:
        return self.shares * self.current_price

    @property
    def gain_loss(self) -> float:
        return self.market_value - self.cost_basis

    @property
    def gain_loss_percent(self) -> float:
        if self.cost_basis == 0:
            return 0
        return (self.gain_loss / self.cost_basis) * 100

    @property
    def holding_days(self) -> int:
        purchase = datetime.strptime(self.purchase_date, "%Y-%m-%d")
        return (datetime.now() - purchase).days

    @property
    def is_long_term(self) -> bool:
        return self.holding_days > 365

    @property
    def days_until_long_term(self) -> int:
        return max(0, 365 - self.holding_days)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lot_id": self.lot_id,
            "ticker": self.ticker,
            "shares": self.shares,
            "cost_per_share": self.cost_per_share,
            "cost_basis": round(self.cost_basis, 2),
            "current_price": self.current_price,
            "market_value": round(self.market_value, 2),
            "gain_loss": round(self.gain_loss, 2),
            "gain_loss_percent": round(self.gain_loss_percent, 2),
            "purchase_date": self.purchase_date,
            "holding_days": self.holding_days,
            "is_long_term": self.is_long_term,
            "days_until_long_term": self.days_until_long_term,
        }


# Mock tax lots
MOCK_TAX_LOTS: Dict[str, List[TaxLot]] = {
    "demo_user": [
        # AAPL lots
        TaxLot("TL001", "AAPL", 100, 145.50, "2023-01-15", 178.50),
        TaxLot("TL002", "AAPL", 50, 168.20, "2023-08-10", 178.50),
        TaxLot("TL003", "AAPL", 25, 185.00, "2024-02-20", 178.50),
        # NVDA lots
        TaxLot("TL004", "NVDA", 200, 45.30, "2022-06-01", 125.80),
        TaxLot("TL005", "NVDA", 100, 85.50, "2023-05-15", 125.80),
        TaxLot("TL006", "NVDA", 50, 115.00, "2024-01-20", 125.80),
        # TSLA lots with losses
        TaxLot("TL007", "TSLA", 80, 195.00, "2023-09-01", 245.30),
        TaxLot("TL008", "TSLA", 40, 285.00, "2024-03-15", 245.30),  # Loss
        # GOOGL
        TaxLot("TL009", "GOOGL", 60, 125.00, "2023-07-20", 175.30),
        TaxLot("TL010", "GOOGL", 30, 165.00, "2024-04-10", 175.30),
    ],
}


def get_tax_lots(user_id: str, ticker: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get all tax lots for a user"""
    lots = MOCK_TAX_LOTS.get(user_id, [])
    if ticker:
        lots = [l for l in lots if l.ticker == ticker.upper()]
    return [l.to_dict() for l in lots]


def get_lot_by_id(user_id: str, lot_id: str) -> Optional[Dict[str, Any]]:
    """Get specific tax lot"""
    lots = MOCK_TAX_LOTS.get(user_id, [])
    for lot in lots:
        if lot.lot_id == lot_id:
            return lot.to_dict()
    return None


def optimize_sale(
    user_id: str,
    ticker: str,
    shares_to_sell: float,
    goal: str = "minimize_tax",  # minimize_tax, maximize_loss, long_term_only
) -> Dict[str, Any]:
    """Find optimal lots to sell based on tax goal"""
    lots = MOCK_TAX_LOTS.get(user_id, [])
    ticker_lots = [l for l in lots if l.ticker == ticker.upper()]

    if not ticker_lots:
        return {"error": f"No lots found for {ticker}"}

    total_shares = sum(l.shares for l in ticker_lots)
    if shares_to_sell > total_shares:
        return {"error": f"Not enough shares. Have {total_shares}, need {shares_to_sell}"}

    # Sort lots based on goal
    if goal == "minimize_tax":
        # Sell highest cost basis first (minimize gains/maximize losses)
        sorted_lots = sorted(ticker_lots, key=lambda l: l.cost_per_share, reverse=True)
    elif goal == "maximize_loss":
        # Sell lots with losses first
        sorted_lots = sorted(ticker_lots, key=lambda l: l.gain_loss)
    elif goal == "long_term_only":
        # Only sell long-term lots
        sorted_lots = sorted(
            [l for l in ticker_lots if l.is_long_term],
            key=lambda l: l.cost_per_share,
            reverse=True
        )
    else:
        sorted_lots = ticker_lots

    # Select lots
    remaining = shares_to_sell
    selected_lots = []
    total_cost_basis = 0
    total_proceeds = 0
    long_term_gain = 0
    short_term_gain = 0

    for lot in sorted_lots:
        if remaining <= 0:
            break

        shares_from_lot = min(lot.shares, remaining)
        cost = shares_from_lot * lot.cost_per_share
        proceeds = shares_from_lot * lot.current_price
        gain = proceeds - cost

        selected_lots.append({
            **lot.to_dict(),
            "shares_to_sell": shares_from_lot,
            "cost_for_sale": round(cost, 2),
            "proceeds": round(proceeds, 2),
            "realized_gain": round(gain, 2),
        })

        total_cost_basis += cost
        total_proceeds += proceeds

        if lot.is_long_term:
            long_term_gain += gain
        else:
            short_term_gain += gain

        remaining -= shares_from_lot

    total_gain = total_proceeds - total_cost_basis

    # Estimate tax impact (simplified)
    long_term_tax_rate = 0.15
    short_term_tax_rate = 0.35  # Ordinary income

    estimated_tax = (
        max(0, long_term_gain) * long_term_tax_rate +
        max(0, short_term_gain) * short_term_tax_rate
    )

    return {
        "ticker": ticker.upper(),
        "shares_to_sell": shares_to_sell,
        "optimization_goal": goal,
        "selected_lots": selected_lots,
        "summary": {
            "total_proceeds": round(total_proceeds, 2),
            "total_cost_basis": round(total_cost_basis, 2),
            "total_realized_gain": round(total_gain, 2),
            "long_term_gain": round(long_term_gain, 2),
            "short_term_gain": round(short_term_gain, 2),
            "estimated_tax": round(estimated_tax, 2),
            "after_tax_proceeds": round(total_proceeds - estimated_tax, 2),
        },
    }


def compare_methods(user_id: str, ticker: str, shares_to_sell: float) -> Dict[str, Any]:
    """Compare different tax lot selection methods"""
    methods = [
        ("fifo", "FIFO (First In, First Out)"),
        ("lifo", "LIFO (Last In, First Out)"),
        ("hifo", "HIFO (Highest In, First Out)"),
        ("minimize_tax", "Tax Optimized"),
    ]

    comparisons = []
    for method_key, method_name in methods:
        if method_key in ["fifo", "lifo"]:
            result = _calculate_by_method(user_id, ticker, shares_to_sell, method_key)
        else:
            result = optimize_sale(user_id, ticker, shares_to_sell, method_key)

        if "error" not in result:
            comparisons.append({
                "method": method_key,
                "method_name": method_name,
                "total_gain": result["summary"]["total_realized_gain"],
                "long_term_gain": result["summary"]["long_term_gain"],
                "short_term_gain": result["summary"]["short_term_gain"],
                "estimated_tax": result["summary"]["estimated_tax"],
                "after_tax_proceeds": result["summary"]["after_tax_proceeds"],
            })

    # Find best option
    if comparisons:
        best = min(comparisons, key=lambda x: x["estimated_tax"])
        for c in comparisons:
            c["is_optimal"] = c["method"] == best["method"]
            c["tax_savings_vs_fifo"] = round(
                comparisons[0]["estimated_tax"] - c["estimated_tax"], 2
            )

    return {
        "ticker": ticker.upper(),
        "shares_to_sell": shares_to_sell,
        "comparisons": comparisons,
        "recommendation": best["method"] if comparisons else None,
    }


def _calculate_by_method(
    user_id: str,
    ticker: str,
    shares_to_sell: float,
    method: str,
) -> Dict[str, Any]:
    """Calculate sale using standard methods"""
    lots = MOCK_TAX_LOTS.get(user_id, [])
    ticker_lots = [l for l in lots if l.ticker == ticker.upper()]

    if method == "fifo":
        sorted_lots = sorted(ticker_lots, key=lambda l: l.purchase_date)
    elif method == "lifo":
        sorted_lots = sorted(ticker_lots, key=lambda l: l.purchase_date, reverse=True)
    elif method == "hifo":
        sorted_lots = sorted(ticker_lots, key=lambda l: l.cost_per_share, reverse=True)
    else:
        sorted_lots = ticker_lots

    remaining = shares_to_sell
    selected_lots = []
    total_cost_basis = 0
    total_proceeds = 0
    long_term_gain = 0
    short_term_gain = 0

    for lot in sorted_lots:
        if remaining <= 0:
            break

        shares_from_lot = min(lot.shares, remaining)
        cost = shares_from_lot * lot.cost_per_share
        proceeds = shares_from_lot * lot.current_price
        gain = proceeds - cost

        selected_lots.append({
            **lot.to_dict(),
            "shares_to_sell": shares_from_lot,
        })

        total_cost_basis += cost
        total_proceeds += proceeds

        if lot.is_long_term:
            long_term_gain += gain
        else:
            short_term_gain += gain

        remaining -= shares_from_lot

    total_gain = total_proceeds - total_cost_basis

    long_term_tax_rate = 0.15
    short_term_tax_rate = 0.35
    estimated_tax = (
        max(0, long_term_gain) * long_term_tax_rate +
        max(0, short_term_gain) * short_term_tax_rate
    )

    return {
        "ticker": ticker.upper(),
        "method": method,
        "selected_lots": selected_lots,
        "summary": {
            "total_proceeds": round(total_proceeds, 2),
            "total_cost_basis": round(total_cost_basis, 2),
            "total_realized_gain": round(total_gain, 2),
            "long_term_gain": round(long_term_gain, 2),
            "short_term_gain": round(short_term_gain, 2),
            "estimated_tax": round(estimated_tax, 2),
            "after_tax_proceeds": round(total_proceeds - estimated_tax, 2),
        },
    }


def get_tax_loss_harvesting_opportunities(user_id: str, min_loss: float = 500) -> List[Dict[str, Any]]:
    """Find opportunities for tax loss harvesting"""
    lots = MOCK_TAX_LOTS.get(user_id, [])

    opportunities = []
    for lot in lots:
        if lot.gain_loss < -min_loss:
            opportunities.append({
                **lot.to_dict(),
                "potential_tax_savings": round(abs(lot.gain_loss) * 0.35, 2),  # Short-term rate
                "wash_sale_end_date": (
                    datetime.strptime(lot.purchase_date, "%Y-%m-%d") + timedelta(days=30)
                ).strftime("%Y-%m-%d"),
            })

    opportunities.sort(key=lambda x: x["gain_loss"])
    return opportunities


def get_approaching_long_term(user_id: str, days_threshold: int = 30) -> List[Dict[str, Any]]:
    """Find lots approaching long-term holding status"""
    lots = MOCK_TAX_LOTS.get(user_id, [])

    approaching = []
    for lot in lots:
        if not lot.is_long_term and lot.days_until_long_term <= days_threshold:
            approaching.append({
                **lot.to_dict(),
                "tax_savings_if_wait": round(
                    lot.gain_loss * (0.35 - 0.15), 2  # Difference between short/long term rates
                ) if lot.gain_loss > 0 else 0,
            })

    approaching.sort(key=lambda x: x["days_until_long_term"])
    return approaching
