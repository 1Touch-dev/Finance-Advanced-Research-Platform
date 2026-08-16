"""
Portfolio Service (Band C #32)
--------------------------------------------------------------------------------
Provides comprehensive portfolio tracking with:
- Holdings with market values
- P&L calculations (unrealized, realized)
- Performance metrics (daily, total return)
- Sector/industry breakdown
- Risk metrics integration
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AssetClass(Enum):
    EQUITY = "equity"
    ETF = "etf"
    FIXED_INCOME = "fixed_income"
    CRYPTO = "crypto"
    CASH = "cash"
    OTHER = "other"


@dataclass
class Holding:
    """Individual position in a portfolio."""
    ticker: str
    quantity: float
    cost_basis: float  # Per share
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    weight: float  # Portfolio weight
    sector: Optional[str] = None
    industry: Optional[str] = None
    asset_class: str = "equity"
    company_name: Optional[str] = None
    day_change: float = 0.0
    day_change_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "quantity": self.quantity,
            "cost_basis": round(self.cost_basis, 2),
            "current_price": round(self.current_price, 2),
            "market_value": round(self.market_value, 2),
            "unrealized_pnl": round(self.unrealized_pnl, 2),
            "unrealized_pnl_pct": round(self.unrealized_pnl_pct, 2),
            "weight": round(self.weight * 100, 2),
            "sector": self.sector,
            "industry": self.industry,
            "asset_class": self.asset_class,
            "company_name": self.company_name,
            "day_change": round(self.day_change, 2),
            "day_change_pct": round(self.day_change_pct, 2),
        }


@dataclass
class SectorAllocation:
    """Sector weight in portfolio."""
    sector: str
    weight: float
    market_value: float
    holdings_count: int
    day_change: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sector": self.sector,
            "weight": round(self.weight * 100, 2),
            "market_value": round(self.market_value, 2),
            "holdings_count": self.holdings_count,
            "day_change": round(self.day_change, 2),
        }


@dataclass
class PerformanceMetrics:
    """Portfolio performance metrics."""
    total_market_value: float
    total_cost_basis: float
    total_unrealized_pnl: float
    total_unrealized_pnl_pct: float
    day_change: float
    day_change_pct: float
    holdings_count: int
    positive_positions: int
    negative_positions: int
    largest_position_weight: float
    top_gainer: Optional[str] = None
    top_gainer_pct: float = 0.0
    top_loser: Optional[str] = None
    top_loser_pct: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_market_value": round(self.total_market_value, 2),
            "total_cost_basis": round(self.total_cost_basis, 2),
            "total_unrealized_pnl": round(self.total_unrealized_pnl, 2),
            "total_unrealized_pnl_pct": round(self.total_unrealized_pnl_pct, 2),
            "day_change": round(self.day_change, 2),
            "day_change_pct": round(self.day_change_pct, 2),
            "holdings_count": self.holdings_count,
            "positive_positions": self.positive_positions,
            "negative_positions": self.negative_positions,
            "largest_position_weight": round(self.largest_position_weight * 100, 2),
            "top_gainer": self.top_gainer,
            "top_gainer_pct": round(self.top_gainer_pct, 2),
            "top_loser": self.top_loser,
            "top_loser_pct": round(self.top_loser_pct, 2),
        }


@dataclass
class PortfolioSummary:
    """Full portfolio summary."""
    portfolio_id: int
    name: str
    base_currency: str
    thesis: Optional[str]
    holdings: List[Holding]
    sector_allocation: List[SectorAllocation]
    performance: PerformanceMetrics
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio_id": self.portfolio_id,
            "name": self.name,
            "base_currency": self.base_currency,
            "thesis": self.thesis,
            "holdings": [h.to_dict() for h in self.holdings],
            "sector_allocation": [s.to_dict() for s in self.sector_allocation],
            "performance": self.performance.to_dict(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# Sector mapping for common tickers (simulated - in production would use API)
_SECTOR_MAP = {
    "AAPL": ("Technology", "Consumer Electronics"),
    "MSFT": ("Technology", "Software"),
    "GOOGL": ("Technology", "Internet Services"),
    "AMZN": ("Consumer Discretionary", "E-Commerce"),
    "META": ("Technology", "Social Media"),
    "NVDA": ("Technology", "Semiconductors"),
    "TSLA": ("Consumer Discretionary", "Electric Vehicles"),
    "AMD": ("Technology", "Semiconductors"),
    "JPM": ("Financials", "Banks"),
    "BAC": ("Financials", "Banks"),
    "WFC": ("Financials", "Banks"),
    "GS": ("Financials", "Investment Banking"),
    "MS": ("Financials", "Investment Banking"),
    "JNJ": ("Healthcare", "Pharmaceuticals"),
    "PFE": ("Healthcare", "Pharmaceuticals"),
    "UNH": ("Healthcare", "Insurance"),
    "XOM": ("Energy", "Oil & Gas"),
    "CVX": ("Energy", "Oil & Gas"),
    "PG": ("Consumer Staples", "Household Products"),
    "KO": ("Consumer Staples", "Beverages"),
    "PEP": ("Consumer Staples", "Beverages"),
    "WMT": ("Consumer Staples", "Retail"),
    "HD": ("Consumer Discretionary", "Home Improvement"),
    "DIS": ("Communication Services", "Entertainment"),
    "NFLX": ("Communication Services", "Streaming"),
    "V": ("Financials", "Payment Processing"),
    "MA": ("Financials", "Payment Processing"),
    "INTC": ("Technology", "Semiconductors"),
    "CRM": ("Technology", "Software"),
    "ORCL": ("Technology", "Software"),
    "IBM": ("Technology", "IT Services"),
    "SPY": ("ETF", "S&P 500 Index"),
    "QQQ": ("ETF", "Nasdaq 100 Index"),
    "IWM": ("ETF", "Russell 2000 Index"),
    "VTI": ("ETF", "Total Stock Market"),
    "BTC": ("Crypto", "Cryptocurrency"),
    "ETH": ("Crypto", "Cryptocurrency"),
}


class PortfolioService:
    """Service for portfolio tracking and analytics."""

    def __init__(self):
        self._price_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_time: Optional[datetime] = None

    def _get_market_data(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get current market data for tickers (simulated for demo)."""
        # In production, would call yfinance or market data API
        # For now, simulate with deterministic prices based on ticker
        import hashlib

        result = {}
        for ticker in tickers:
            # Generate deterministic but realistic prices
            seed = int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)
            base_price = 50 + (seed % 500)
            day_change_pct = ((seed % 100) - 50) / 100  # -0.5% to +0.5%

            result[ticker] = {
                "price": base_price,
                "prev_close": base_price / (1 + day_change_pct),
                "day_change": base_price * day_change_pct,
                "day_change_pct": day_change_pct * 100,
            }

        return result

    def _get_sector_info(self, ticker: str) -> tuple:
        """Get sector and industry for a ticker."""
        if ticker in _SECTOR_MAP:
            return _SECTOR_MAP[ticker]
        return ("Other", "Other")

    def calculate_holdings(
        self,
        positions: List[Dict[str, Any]],
    ) -> List[Holding]:
        """Calculate holdings with market values and P&L."""
        if not positions:
            return []

        # Get unique tickers
        tickers = list(set(p["ticker"] for p in positions if p.get("ticker")))
        market_data = self._get_market_data(tickers)

        # Calculate total market value for weights
        holdings_raw = []
        for pos in positions:
            ticker = pos.get("ticker", "UNKNOWN")
            qty = pos.get("qty", 0)
            cost_basis = pos.get("cost_basis", 0)

            data = market_data.get(ticker, {"price": cost_basis, "day_change": 0, "day_change_pct": 0})
            current_price = data["price"]
            market_value = qty * current_price
            cost_total = qty * cost_basis
            unrealized_pnl = market_value - cost_total
            unrealized_pnl_pct = (unrealized_pnl / cost_total * 100) if cost_total else 0

            sector, industry = self._get_sector_info(ticker)

            holdings_raw.append({
                "ticker": ticker,
                "quantity": qty,
                "cost_basis": cost_basis,
                "current_price": current_price,
                "market_value": market_value,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_pct": unrealized_pnl_pct,
                "sector": sector,
                "industry": industry,
                "day_change": data.get("day_change", 0) * qty,
                "day_change_pct": data.get("day_change_pct", 0),
            })

        # Calculate weights
        total_value = sum(h["market_value"] for h in holdings_raw)

        holdings = []
        for h in holdings_raw:
            weight = h["market_value"] / total_value if total_value else 0
            holdings.append(Holding(
                ticker=h["ticker"],
                quantity=h["quantity"],
                cost_basis=h["cost_basis"],
                current_price=h["current_price"],
                market_value=h["market_value"],
                unrealized_pnl=h["unrealized_pnl"],
                unrealized_pnl_pct=h["unrealized_pnl_pct"],
                weight=weight,
                sector=h["sector"],
                industry=h["industry"],
                day_change=h["day_change"],
                day_change_pct=h["day_change_pct"],
            ))

        # Sort by market value descending
        holdings.sort(key=lambda x: x.market_value, reverse=True)
        return holdings

    def calculate_sector_allocation(
        self,
        holdings: List[Holding],
    ) -> List[SectorAllocation]:
        """Calculate sector allocation from holdings."""
        sector_data: Dict[str, Dict[str, Any]] = {}

        for h in holdings:
            sector = h.sector or "Other"
            if sector not in sector_data:
                sector_data[sector] = {
                    "market_value": 0,
                    "day_change": 0,
                    "holdings_count": 0,
                }
            sector_data[sector]["market_value"] += h.market_value
            sector_data[sector]["day_change"] += h.day_change
            sector_data[sector]["holdings_count"] += 1

        total_value = sum(s["market_value"] for s in sector_data.values())

        allocations = []
        for sector, data in sector_data.items():
            weight = data["market_value"] / total_value if total_value else 0
            allocations.append(SectorAllocation(
                sector=sector,
                weight=weight,
                market_value=data["market_value"],
                holdings_count=data["holdings_count"],
                day_change=data["day_change"],
            ))

        allocations.sort(key=lambda x: x.weight, reverse=True)
        return allocations

    def calculate_performance(
        self,
        holdings: List[Holding],
    ) -> PerformanceMetrics:
        """Calculate portfolio performance metrics."""
        if not holdings:
            return PerformanceMetrics(
                total_market_value=0,
                total_cost_basis=0,
                total_unrealized_pnl=0,
                total_unrealized_pnl_pct=0,
                day_change=0,
                day_change_pct=0,
                holdings_count=0,
                positive_positions=0,
                negative_positions=0,
                largest_position_weight=0,
            )

        total_market_value = sum(h.market_value for h in holdings)
        total_cost_basis = sum(h.quantity * h.cost_basis for h in holdings)
        total_unrealized_pnl = total_market_value - total_cost_basis
        total_unrealized_pnl_pct = (total_unrealized_pnl / total_cost_basis * 100) if total_cost_basis else 0

        day_change = sum(h.day_change for h in holdings)
        prev_value = total_market_value - day_change
        day_change_pct = (day_change / prev_value * 100) if prev_value else 0

        positive_positions = sum(1 for h in holdings if h.unrealized_pnl >= 0)
        negative_positions = sum(1 for h in holdings if h.unrealized_pnl < 0)
        largest_position_weight = max(h.weight for h in holdings) if holdings else 0

        # Find top gainer and loser
        sorted_by_pnl_pct = sorted(holdings, key=lambda x: x.unrealized_pnl_pct, reverse=True)
        top_gainer = sorted_by_pnl_pct[0].ticker if sorted_by_pnl_pct else None
        top_gainer_pct = sorted_by_pnl_pct[0].unrealized_pnl_pct if sorted_by_pnl_pct else 0
        top_loser = sorted_by_pnl_pct[-1].ticker if sorted_by_pnl_pct else None
        top_loser_pct = sorted_by_pnl_pct[-1].unrealized_pnl_pct if sorted_by_pnl_pct else 0

        return PerformanceMetrics(
            total_market_value=total_market_value,
            total_cost_basis=total_cost_basis,
            total_unrealized_pnl=total_unrealized_pnl,
            total_unrealized_pnl_pct=total_unrealized_pnl_pct,
            day_change=day_change,
            day_change_pct=day_change_pct,
            holdings_count=len(holdings),
            positive_positions=positive_positions,
            negative_positions=negative_positions,
            largest_position_weight=largest_position_weight,
            top_gainer=top_gainer,
            top_gainer_pct=top_gainer_pct,
            top_loser=top_loser,
            top_loser_pct=top_loser_pct,
        )

    def get_portfolio_summary(
        self,
        portfolio_id: int,
        name: str,
        base_currency: str,
        thesis: Optional[str],
        positions: List[Dict[str, Any]],
        created_at: str,
    ) -> PortfolioSummary:
        """Get full portfolio summary with holdings and metrics."""
        holdings = self.calculate_holdings(positions)
        sector_allocation = self.calculate_sector_allocation(holdings)
        performance = self.calculate_performance(holdings)

        return PortfolioSummary(
            portfolio_id=portfolio_id,
            name=name,
            base_currency=base_currency,
            thesis=thesis,
            holdings=holdings,
            sector_allocation=sector_allocation,
            performance=performance,
            created_at=created_at,
            updated_at=datetime.now().isoformat(),
        )


# Singleton instance
_service: Optional[PortfolioService] = None


def get_portfolio_service() -> PortfolioService:
    """Get or create portfolio service singleton."""
    global _service
    if _service is None:
        _service = PortfolioService()
    return _service
