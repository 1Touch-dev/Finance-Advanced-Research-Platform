"""
Portfolio Service (Band C #32)
--------------------------------------------------------------------------------
Provides comprehensive portfolio tracking with:
- Holdings with market values
- P&L calculations (unrealized, realized)
- Performance metrics (daily, total return)
- Sector/industry breakdown
- Risk metrics integration

All data is sourced from yfinance (real market data).
When data is unavailable, returns no_data responses per S0-C Mock Ban.
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any, Union
from enum import Enum
import logging
import math

import yfinance as yf

from app.core.no_data import no_data_response, NoDataReason, is_no_data_response

logger = logging.getLogger(__name__)

# Cache TTL constants
PRICE_CACHE_TTL = 300  # 5 minutes for prices
SECTOR_CACHE_TTL = 3600  # 1 hour for sector/company info
BETA_CACHE_TTL = 3600  # 1 hour for beta values


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
    current_price: Optional[float]  # None if market data unavailable
    market_value: Optional[float]  # None if price unavailable
    unrealized_pnl: Optional[float]
    unrealized_pnl_pct: Optional[float]
    weight: Optional[float]  # Portfolio weight
    sector: Optional[str] = None
    industry: Optional[str] = None
    asset_class: str = "equity"
    company_name: Optional[str] = None
    day_change: Optional[float] = None
    day_change_pct: Optional[float] = None
    data_available: bool = True
    data_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "ticker": self.ticker,
            "quantity": self.quantity,
            "cost_basis": round(self.cost_basis, 2),
            "sector": self.sector,
            "industry": self.industry,
            "asset_class": self.asset_class,
            "company_name": self.company_name,
            "data_available": self.data_available,
        }

        if self.data_available and self.current_price is not None:
            result.update({
                "current_price": round(self.current_price, 2),
                "market_value": round(self.market_value, 2) if self.market_value else None,
                "unrealized_pnl": round(self.unrealized_pnl, 2) if self.unrealized_pnl is not None else None,
                "unrealized_pnl_pct": round(self.unrealized_pnl_pct, 2) if self.unrealized_pnl_pct is not None else None,
                "weight": round(self.weight * 100, 2) if self.weight else None,
                "day_change": round(self.day_change, 2) if self.day_change is not None else None,
                "day_change_pct": round(self.day_change_pct, 2) if self.day_change_pct is not None else None,
            })
        else:
            result["data_error"] = self.data_error or "Market data unavailable"

        return result


@dataclass
class SectorAllocation:
    """Sector weight in portfolio."""
    sector: str
    weight: Optional[float]
    market_value: Optional[float]
    holdings_count: int
    day_change: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sector": self.sector,
            "weight": round(self.weight * 100, 2) if self.weight else None,
            "market_value": round(self.market_value, 2) if self.market_value else None,
            "holdings_count": self.holdings_count,
            "day_change": round(self.day_change, 2) if self.day_change is not None else None,
        }


@dataclass
class PerformanceMetrics:
    """Portfolio performance metrics."""
    total_market_value: Optional[float]
    total_cost_basis: float
    total_unrealized_pnl: Optional[float]
    total_unrealized_pnl_pct: Optional[float]
    day_change: Optional[float]
    day_change_pct: Optional[float]
    holdings_count: int
    positive_positions: Optional[int]
    negative_positions: Optional[int]
    largest_position_weight: Optional[float]
    top_gainer: Optional[str] = None
    top_gainer_pct: Optional[float] = None
    top_loser: Optional[str] = None
    top_loser_pct: Optional[float] = None
    data_available: bool = True
    partial_data: bool = False  # True if some holdings missing prices

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "holdings_count": self.holdings_count,
            "total_cost_basis": round(self.total_cost_basis, 2),
            "data_available": self.data_available,
            "partial_data": self.partial_data,
        }

        if self.data_available and self.total_market_value is not None:
            result.update({
                "total_market_value": round(self.total_market_value, 2),
                "total_unrealized_pnl": round(self.total_unrealized_pnl, 2) if self.total_unrealized_pnl is not None else None,
                "total_unrealized_pnl_pct": round(self.total_unrealized_pnl_pct, 2) if self.total_unrealized_pnl_pct is not None else None,
                "day_change": round(self.day_change, 2) if self.day_change is not None else None,
                "day_change_pct": round(self.day_change_pct, 2) if self.day_change_pct is not None else None,
                "positive_positions": self.positive_positions,
                "negative_positions": self.negative_positions,
                "largest_position_weight": round(self.largest_position_weight * 100, 2) if self.largest_position_weight else None,
                "top_gainer": self.top_gainer,
                "top_gainer_pct": round(self.top_gainer_pct, 2) if self.top_gainer_pct is not None else None,
                "top_loser": self.top_loser,
                "top_loser_pct": round(self.top_loser_pct, 2) if self.top_loser_pct is not None else None,
            })

        return result


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


# ─────────────────────────────────────────────────────────────────────────────
# Caches with TTL
# ─────────────────────────────────────────────────────────────────────────────

_SECTOR_CACHE: Dict[str, tuple] = {}  # ticker -> (sector, industry, timestamp)
_COMPANY_CACHE: Dict[str, tuple] = {}  # ticker -> (name, timestamp)
_BETA_CACHE: Dict[str, tuple] = {}  # ticker -> (beta, timestamp)


def _is_cache_valid(cache_entry: Optional[tuple], ttl: int) -> bool:
    """Check if a cache entry is still valid."""
    if cache_entry is None:
        return False
    timestamp = cache_entry[-1]
    return (datetime.now().timestamp() - timestamp) < ttl


def _get_ticker_info(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Fetch ticker info from yfinance with error handling.
    Returns None if data unavailable (no fake data).
    """
    try:
        info = yf.Ticker(ticker).info
        if info and len(info) > 1:  # yfinance returns {} or minimal dict on failure
            return info
        logger.warning(f"No info available for {ticker}")
        return None
    except Exception as e:
        logger.warning(f"Failed to fetch info for {ticker}: {e}")
        return None


def _get_sector_industry(ticker: str) -> tuple:
    """
    Get sector and industry from yfinance with caching.
    Returns (sector, industry) or (None, None) if unavailable.
    """
    now = datetime.now().timestamp()

    # Check cache with TTL
    if ticker in _SECTOR_CACHE:
        cached = _SECTOR_CACHE[ticker]
        if _is_cache_valid(cached, SECTOR_CACHE_TTL):
            return (cached[0], cached[1])

    # Fetch from yfinance
    info = _get_ticker_info(ticker)
    if info is None:
        return (None, None)

    sector = info.get("sector")
    industry = info.get("industry")

    if sector:
        _SECTOR_CACHE[ticker] = (sector, industry or "Other", now)
        return (sector, industry or "Other")

    # ETF detection
    quote_type = info.get("quoteType", "")
    if quote_type == "ETF":
        category = info.get("category", "Index")
        _SECTOR_CACHE[ticker] = ("ETF", category, now)
        return ("ETF", category)

    # Crypto detection
    if quote_type == "CRYPTOCURRENCY":
        _SECTOR_CACHE[ticker] = ("Crypto", "Cryptocurrency", now)
        return ("Crypto", "Cryptocurrency")

    # Unknown - return None, not fake data
    return (None, None)


def _get_company_name(ticker: str) -> Optional[str]:
    """
    Get company name from yfinance with caching.
    Returns None if unavailable (no fake data).
    """
    now = datetime.now().timestamp()

    # Check cache with TTL
    if ticker in _COMPANY_CACHE:
        cached = _COMPANY_CACHE[ticker]
        if _is_cache_valid(cached, SECTOR_CACHE_TTL):
            return cached[0]

    # Fetch from yfinance
    info = _get_ticker_info(ticker)
    if info is None:
        return None

    name = info.get("longName") or info.get("shortName")
    if name:
        _COMPANY_CACHE[ticker] = (name, now)
        return name

    return None


def _get_real_beta(ticker: str) -> Optional[float]:
    """
    Get beta from yfinance info.
    Returns None if unavailable (no default/fake values).
    """
    now = datetime.now().timestamp()

    # Check cache with TTL
    if ticker in _BETA_CACHE:
        cached = _BETA_CACHE[ticker]
        if _is_cache_valid(cached, BETA_CACHE_TTL):
            return cached[0]

    try:
        info = yf.Ticker(ticker).info
        beta = info.get("beta")
        if beta is not None:
            _BETA_CACHE[ticker] = (float(beta), now)
            return float(beta)
    except Exception as exc:
        logger.debug("beta fetch failed for %s: %s", ticker, exc)

    return None


class PortfolioService:
    """Service for portfolio tracking and analytics using real market data."""

    def __init__(self):
        self._price_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_time: Optional[datetime] = None

    def _is_cache_valid(self) -> bool:
        """Check if price cache is still within TTL."""
        if not self._cache_time or not self._price_cache:
            return False
        return (datetime.now() - self._cache_time).total_seconds() < PRICE_CACHE_TTL

    def _get_market_data(self, tickers: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get current market data for tickers using yfinance with caching.
        Returns only tickers with real data - no fake/simulated prices.
        """
        if not tickers:
            return {}

        # Check cache validity
        if self._is_cache_valid():
            missing = [t for t in tickers if t not in self._price_cache]
            if not missing:
                return {t: self._price_cache[t] for t in tickers if t in self._price_cache}
        else:
            missing = tickers
            self._price_cache = {}  # Clear stale cache

        if not missing:
            return {t: self._price_cache[t] for t in tickers if t in self._price_cache}

        try:
            # Download price data from yfinance
            data = yf.download(
                missing,
                period="2d",
                progress=False,
                group_by="ticker" if len(missing) > 1 else "column",
                threads=True,
                timeout=15,
            )

            if data.empty:
                logger.warning(f"yfinance returned empty data for tickers: {missing}")
                return {t: self._price_cache[t] for t in tickers if t in self._price_cache}

            for ticker in missing:
                try:
                    if len(missing) == 1:
                        ticker_data = data
                    else:
                        if ticker not in data.columns.get_level_values(0):
                            logger.warning(f"No data returned for ticker: {ticker}")
                            continue
                        ticker_data = data[ticker]

                    closes = ticker_data["Close"].dropna()
                    if len(closes) < 1:
                        logger.warning(f"No close prices for {ticker}")
                        continue

                    current_price = float(closes.iloc[-1])
                    prev_close = float(closes.iloc[-2]) if len(closes) >= 2 else None

                    day_change = None
                    day_change_pct = None
                    if prev_close is not None and prev_close > 0:
                        day_change = current_price - prev_close
                        day_change_pct = (day_change / prev_close * 100)

                    self._price_cache[ticker] = {
                        "price": current_price,
                        "prev_close": prev_close,
                        "day_change": day_change,
                        "day_change_pct": day_change_pct,
                    }
                except Exception as e:
                    logger.warning(f"Failed to parse market data for {ticker}: {e}")
                    continue

            self._cache_time = datetime.now()

        except Exception as e:
            logger.error(f"yfinance download failed: {e}")

        return {t: self._price_cache[t] for t in tickers if t in self._price_cache}

    def _get_sector_info(self, ticker: str) -> tuple:
        """Get sector and industry for a ticker."""
        return _get_sector_industry(ticker)

    def calculate_holdings(
        self,
        positions: List[Dict[str, Any]],
    ) -> List[Holding]:
        """
        Calculate holdings with market values and P&L.
        Only uses real market data - holdings without price data are marked accordingly.
        """
        if not positions:
            return []

        # Get unique tickers
        tickers = list(set(p["ticker"] for p in positions if p.get("ticker")))
        market_data = self._get_market_data(tickers)

        holdings_raw = []
        for pos in positions:
            ticker = pos.get("ticker", "UNKNOWN")
            qty = pos.get("qty", 0)
            cost_basis = pos.get("cost_basis", 0)

            # Get real market data - do NOT fall back to cost_basis
            data = market_data.get(ticker)
            sector, industry = self._get_sector_info(ticker)
            company_name = _get_company_name(ticker)

            if data is None:
                # No market data available - mark as unavailable
                holdings_raw.append({
                    "ticker": ticker,
                    "quantity": qty,
                    "cost_basis": cost_basis,
                    "current_price": None,
                    "market_value": None,
                    "unrealized_pnl": None,
                    "unrealized_pnl_pct": None,
                    "sector": sector,
                    "industry": industry,
                    "company_name": company_name,
                    "day_change": None,
                    "day_change_pct": None,
                    "data_available": False,
                    "data_error": "Market data unavailable from yfinance",
                })
            else:
                current_price = data["price"]
                market_value = qty * current_price
                cost_total = qty * cost_basis
                unrealized_pnl = market_value - cost_total
                unrealized_pnl_pct = (unrealized_pnl / cost_total * 100) if cost_total else 0

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
                    "company_name": company_name,
                    "day_change": data.get("day_change"),
                    "day_change_pct": data.get("day_change_pct"),
                    "data_available": True,
                    "data_error": None,
                })

        # Calculate weights based only on holdings with real data
        holdings_with_value = [h for h in holdings_raw if h["market_value"] is not None]
        total_value = sum(h["market_value"] for h in holdings_with_value)

        holdings = []
        for h in holdings_raw:
            weight = None
            if h["market_value"] is not None and total_value > 0:
                weight = h["market_value"] / total_value

            # Calculate day change in dollar terms for holding
            day_change_dollars = None
            if h.get("day_change") is not None:
                day_change_dollars = h["day_change"] * h["quantity"]

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
                company_name=h["company_name"],
                day_change=day_change_dollars,
                day_change_pct=h["day_change_pct"],
                data_available=h["data_available"],
                data_error=h["data_error"],
            ))

        # Sort by market value descending (holdings without value at end)
        holdings.sort(key=lambda x: (x.market_value is not None, x.market_value or 0), reverse=True)
        return holdings

    def calculate_sector_allocation(
        self,
        holdings: List[Holding],
    ) -> List[SectorAllocation]:
        """Calculate sector allocation from holdings with real data only."""
        sector_data: Dict[str, Dict[str, Any]] = {}

        for h in holdings:
            if not h.data_available or h.market_value is None:
                continue  # Skip holdings without real price data

            sector = h.sector or "Unknown"
            if sector not in sector_data:
                sector_data[sector] = {
                    "market_value": 0,
                    "day_change": 0,
                    "holdings_count": 0,
                }
            sector_data[sector]["market_value"] += h.market_value
            if h.day_change is not None:
                sector_data[sector]["day_change"] += h.day_change
            sector_data[sector]["holdings_count"] += 1

        total_value = sum(s["market_value"] for s in sector_data.values())

        allocations = []
        for sector, data in sector_data.items():
            weight = data["market_value"] / total_value if total_value > 0 else None
            allocations.append(SectorAllocation(
                sector=sector,
                weight=weight,
                market_value=data["market_value"],
                holdings_count=data["holdings_count"],
                day_change=data["day_change"] if data["day_change"] != 0 else None,
            ))

        allocations.sort(key=lambda x: (x.weight is not None, x.weight or 0), reverse=True)
        return allocations

    def calculate_performance(
        self,
        holdings: List[Holding],
    ) -> PerformanceMetrics:
        """Calculate portfolio performance metrics using only real data."""
        if not holdings:
            return PerformanceMetrics(
                total_market_value=None,
                total_cost_basis=0,
                total_unrealized_pnl=None,
                total_unrealized_pnl_pct=None,
                day_change=None,
                day_change_pct=None,
                holdings_count=0,
                positive_positions=None,
                negative_positions=None,
                largest_position_weight=None,
                data_available=False,
            )

        # Separate holdings with and without real data
        holdings_with_data = [h for h in holdings if h.data_available and h.market_value is not None]
        holdings_without_data = [h for h in holdings if not h.data_available or h.market_value is None]

        total_cost_basis = sum(h.quantity * h.cost_basis for h in holdings)

        if not holdings_with_data:
            # No real market data available
            return PerformanceMetrics(
                total_market_value=None,
                total_cost_basis=total_cost_basis,
                total_unrealized_pnl=None,
                total_unrealized_pnl_pct=None,
                day_change=None,
                day_change_pct=None,
                holdings_count=len(holdings),
                positive_positions=None,
                negative_positions=None,
                largest_position_weight=None,
                data_available=False,
            )

        total_market_value = sum(h.market_value for h in holdings_with_data)
        total_cost_with_data = sum(h.quantity * h.cost_basis for h in holdings_with_data)
        total_unrealized_pnl = total_market_value - total_cost_with_data
        total_unrealized_pnl_pct = (total_unrealized_pnl / total_cost_with_data * 100) if total_cost_with_data else None

        # Day change calculation
        day_changes = [h.day_change for h in holdings_with_data if h.day_change is not None]
        day_change = sum(day_changes) if day_changes else None
        day_change_pct = None
        if day_change is not None and total_market_value > 0:
            prev_value = total_market_value - day_change
            if prev_value > 0:
                day_change_pct = (day_change / prev_value * 100)

        positive_positions = sum(1 for h in holdings_with_data if h.unrealized_pnl is not None and h.unrealized_pnl >= 0)
        negative_positions = sum(1 for h in holdings_with_data if h.unrealized_pnl is not None and h.unrealized_pnl < 0)
        largest_position_weight = max((h.weight for h in holdings_with_data if h.weight is not None), default=None)

        # Find top gainer and loser
        sorted_by_pnl_pct = sorted(
            [h for h in holdings_with_data if h.unrealized_pnl_pct is not None],
            key=lambda x: x.unrealized_pnl_pct,
            reverse=True
        )
        top_gainer = sorted_by_pnl_pct[0].ticker if sorted_by_pnl_pct else None
        top_gainer_pct = sorted_by_pnl_pct[0].unrealized_pnl_pct if sorted_by_pnl_pct else None
        top_loser = sorted_by_pnl_pct[-1].ticker if sorted_by_pnl_pct else None
        top_loser_pct = sorted_by_pnl_pct[-1].unrealized_pnl_pct if sorted_by_pnl_pct else None

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
            data_available=True,
            partial_data=len(holdings_without_data) > 0,
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


# ── Risk Metrics (#45) ─────────────────────────────────────────────────────────

@dataclass
class RiskMetrics:
    """Portfolio risk metrics computed from real market data."""
    portfolio_id: int
    as_of_date: str
    data_available: bool = True
    data_error: Optional[str] = None

    # Value at Risk (VaR) - computed from real returns
    var_95_daily: Optional[float] = None
    var_99_daily: Optional[float] = None
    var_95_monthly: Optional[float] = None
    var_99_monthly: Optional[float] = None
    var_method: str = "parametric"

    # Beta (from real yfinance data)
    portfolio_beta: Optional[float] = None
    weighted_avg_beta: Optional[float] = None

    # Volatility metrics (from real historical returns)
    portfolio_volatility: Optional[float] = None
    downside_deviation: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None

    # Drawdown metrics (from real price history)
    max_drawdown: Optional[float] = None
    current_drawdown: Optional[float] = None
    avg_drawdown: Optional[float] = None
    drawdown_duration_days: Optional[int] = None

    # Concentration metrics (calculated, not fetched)
    top_5_concentration: Optional[float] = None
    herfindahl_index: Optional[float] = None
    sector_concentration: Optional[float] = None

    # Correlation (from real returns)
    avg_pairwise_correlation: Optional[float] = None
    diversification_ratio: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "portfolio_id": self.portfolio_id,
            "as_of_date": self.as_of_date,
            "data_available": self.data_available,
        }

        if not self.data_available:
            result["data_error"] = self.data_error
            return result

        result.update({
            "value_at_risk": {
                "var_95_daily": round(self.var_95_daily, 2) if self.var_95_daily is not None else None,
                "var_99_daily": round(self.var_99_daily, 2) if self.var_99_daily is not None else None,
                "var_95_monthly": round(self.var_95_monthly, 2) if self.var_95_monthly is not None else None,
                "var_99_monthly": round(self.var_99_monthly, 2) if self.var_99_monthly is not None else None,
                "method": self.var_method,
            },
            "beta": {
                "portfolio_beta": round(self.portfolio_beta, 3) if self.portfolio_beta is not None else None,
                "weighted_avg_beta": round(self.weighted_avg_beta, 3) if self.weighted_avg_beta is not None else None,
            },
            "volatility": {
                "annualized": round(self.portfolio_volatility * 100, 2) if self.portfolio_volatility is not None else None,
                "downside_deviation": round(self.downside_deviation * 100, 2) if self.downside_deviation is not None else None,
                "sharpe_ratio": round(self.sharpe_ratio, 3) if self.sharpe_ratio is not None else None,
                "sortino_ratio": round(self.sortino_ratio, 3) if self.sortino_ratio is not None else None,
            },
            "drawdown": {
                "max_drawdown_pct": round(self.max_drawdown * 100, 2) if self.max_drawdown is not None else None,
                "current_drawdown_pct": round(self.current_drawdown * 100, 2) if self.current_drawdown is not None else None,
                "avg_drawdown_pct": round(self.avg_drawdown * 100, 2) if self.avg_drawdown is not None else None,
                "duration_days": self.drawdown_duration_days,
            },
            "concentration": {
                "top_5_pct": round(self.top_5_concentration * 100, 2) if self.top_5_concentration is not None else None,
                "herfindahl_index": round(self.herfindahl_index, 4) if self.herfindahl_index is not None else None,
                "largest_sector_pct": round(self.sector_concentration * 100, 2) if self.sector_concentration is not None else None,
            },
            "diversification": {
                "avg_correlation": round(self.avg_pairwise_correlation, 3) if self.avg_pairwise_correlation is not None else None,
                "diversification_ratio": round(self.diversification_ratio, 3) if self.diversification_ratio is not None else None,
            },
        })
        return result


def calculate_risk_metrics(
    portfolio_id: int,
    holdings: List[Holding],
    total_value: float,
) -> Union[RiskMetrics, Dict[str, Any]]:
    """
    Calculate comprehensive risk metrics for a portfolio using REAL market data.

    All metrics are derived from actual yfinance historical data.
    If data is unavailable, returns no_data response - never fake/simulated values.
    """
    import numpy as np
    import pandas as pd

    today = datetime.now().strftime("%Y-%m-%d")

    # Filter to holdings with real data
    valid_holdings = [h for h in holdings if h.data_available and h.weight is not None]

    if not valid_holdings or total_value == 0:
        return RiskMetrics(
            portfolio_id=portfolio_id,
            as_of_date=today,
            data_available=False,
            data_error="No valid holdings with market data",
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Calculate weighted average beta from REAL yfinance data
    # ─────────────────────────────────────────────────────────────────────────
    betas = []
    weights_for_beta = []
    for h in valid_holdings:
        beta = _get_real_beta(h.ticker)
        if beta is not None:
            betas.append(beta)
            weights_for_beta.append(h.weight)

    weighted_beta = None
    if betas and weights_for_beta:
        total_weight = sum(weights_for_beta)
        if total_weight > 0:
            weighted_beta = sum(b * w for b, w in zip(betas, weights_for_beta)) / total_weight

    # ─────────────────────────────────────────────────────────────────────────
    # Compute portfolio volatility from REAL historical returns
    # ─────────────────────────────────────────────────────────────────────────
    portfolio_volatility = None
    downside_dev = None
    sharpe_ratio = None
    sortino_ratio = None
    max_dd = None
    current_dd = None
    avg_dd = None
    drawdown_duration = None
    avg_correlation = None

    try:
        # Limit to top 20 holdings for performance
        tickers_to_fetch = [h.ticker for h in valid_holdings[:20]]
        tickers_str = " ".join(tickers_to_fetch)

        hist = yf.download(
            tickers_str,
            period="1y",
            interval="1d",
            progress=False,
            timeout=20,
            threads=True
        )

        if hist.empty:
            logger.warning("yfinance returned empty historical data for risk metrics")
        else:
            # Extract close prices
            if "Adj Close" in hist.columns or ("Adj Close" in [c[0] for c in hist.columns] if isinstance(hist.columns, pd.MultiIndex) else False):
                prices = hist.get("Adj Close", hist.get("Close"))
            else:
                prices = hist.get("Close")

            if prices is not None:
                if isinstance(prices, pd.Series):
                    prices = prices.to_frame(name=tickers_to_fetch[0])

                returns = prices.pct_change().dropna()

                if len(returns) > 20:
                    # Build weights array matching available tickers
                    available_tickers = list(returns.columns)
                    weights_array = []
                    for ticker in available_tickers:
                        matching = [h for h in valid_holdings if h.ticker == ticker]
                        if matching:
                            weights_array.append(matching[0].weight)
                        else:
                            weights_array.append(0)

                    weights_array = np.array(weights_array)
                    if weights_array.sum() > 0:
                        weights_array = weights_array / weights_array.sum()

                    # Portfolio returns
                    port_returns = (returns * weights_array).sum(axis=1)

                    # Annualized volatility
                    portfolio_volatility = float(port_returns.std() * math.sqrt(252))

                    # Mean return (annualized)
                    mean_return = float(port_returns.mean() * 252)

                    # Downside deviation
                    downside_returns = port_returns[port_returns < 0]
                    if len(downside_returns) > 0:
                        downside_dev = float(downside_returns.std() * math.sqrt(252))

                    # Drawdown calculations
                    cumulative = (1 + port_returns).cumprod()
                    running_max = cumulative.cummax()
                    drawdowns = (cumulative - running_max) / running_max
                    max_dd = float(drawdowns.min())
                    current_dd = float(drawdowns.iloc[-1]) if len(drawdowns) > 0 else None
                    avg_dd = float(drawdowns[drawdowns < 0].mean()) if len(drawdowns[drawdowns < 0]) > 0 else None

                    # Drawdown duration - days since last peak
                    if current_dd is not None and current_dd < 0:
                        peak_idx = cumulative.idxmax()
                        drawdown_duration = (returns.index[-1] - peak_idx).days

                    # Risk-adjusted returns (using 5% risk-free rate)
                    risk_free_rate = 0.05
                    if portfolio_volatility is not None and portfolio_volatility > 0:
                        sharpe_ratio = (mean_return - risk_free_rate) / portfolio_volatility

                    if downside_dev is not None and downside_dev > 0:
                        sortino_ratio = (mean_return - risk_free_rate) / downside_dev

                    # Average pairwise correlation
                    if len(available_tickers) > 1:
                        corr_matrix = returns.corr()
                        # Get upper triangle (excluding diagonal)
                        upper_tri = np.triu(corr_matrix.values, k=1)
                        mask = upper_tri != 0
                        if mask.sum() > 0:
                            avg_correlation = float(upper_tri[mask].mean())

    except Exception as exc:
        logger.warning(f"Risk metrics calculation failed: {exc}")
        # Return partial metrics - don't generate fake data

    # ─────────────────────────────────────────────────────────────────────────
    # Calculate VaR from REAL volatility (if available)
    # ─────────────────────────────────────────────────────────────────────────
    var_95_daily = None
    var_99_daily = None
    var_95_monthly = None
    var_99_monthly = None

    if portfolio_volatility is not None:
        z_95 = 1.645
        z_99 = 2.326
        daily_vol = portfolio_volatility / math.sqrt(252)

        var_95_daily = total_value * z_95 * daily_vol
        var_99_daily = total_value * z_99 * daily_vol
        var_95_monthly = total_value * z_95 * portfolio_volatility * math.sqrt(21/252)
        var_99_monthly = total_value * z_99 * portfolio_volatility * math.sqrt(21/252)

    # ─────────────────────────────────────────────────────────────────────────
    # Concentration metrics (calculated from holding weights - no external data)
    # ─────────────────────────────────────────────────────────────────────────
    sorted_holdings = sorted(valid_holdings, key=lambda x: x.weight or 0, reverse=True)
    top_5_weight = sum(h.weight for h in sorted_holdings[:5] if h.weight is not None)
    hhi = sum((h.weight or 0) ** 2 for h in valid_holdings)  # Herfindahl index

    # Sector concentration
    sector_weights: Dict[str, float] = {}
    for h in valid_holdings:
        sector = h.sector or "Unknown"
        sector_weights[sector] = sector_weights.get(sector, 0) + (h.weight or 0)
    max_sector_weight = max(sector_weights.values()) if sector_weights else None

    # Diversification ratio
    n = len(valid_holdings)
    diversification_ratio = 1 / math.sqrt(n) if n > 0 else None

    return RiskMetrics(
        portfolio_id=portfolio_id,
        as_of_date=today,
        data_available=True,
        var_95_daily=var_95_daily,
        var_99_daily=var_99_daily,
        var_95_monthly=var_95_monthly,
        var_99_monthly=var_99_monthly,
        var_method="parametric",
        portfolio_beta=weighted_beta,
        weighted_avg_beta=weighted_beta,
        portfolio_volatility=portfolio_volatility,
        downside_deviation=downside_dev,
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        max_drawdown=max_dd,
        current_drawdown=current_dd,
        avg_drawdown=avg_dd,
        drawdown_duration_days=drawdown_duration,
        top_5_concentration=top_5_weight if top_5_weight > 0 else None,
        herfindahl_index=hhi if hhi > 0 else None,
        sector_concentration=max_sector_weight,
        avg_pairwise_correlation=avg_correlation,
        diversification_ratio=diversification_ratio,
    )


# ── Position-level P&L (#41) ──────────────────────────────────────────────────

@dataclass
class PositionPnL:
    """Detailed P&L metrics for a single position using real market data."""
    position_id: int
    ticker: str
    company_name: Optional[str]
    sector: Optional[str]
    data_available: bool = True
    data_error: Optional[str] = None

    # Current position
    quantity: float = 0
    cost_basis: float = 0
    current_price: Optional[float] = None
    market_value: Optional[float] = None

    # Unrealized P&L
    unrealized_pnl: Optional[float] = None
    unrealized_pnl_pct: Optional[float] = None

    # Period returns (from real historical data)
    day_pnl: Optional[float] = None
    day_pnl_pct: Optional[float] = None
    week_pnl: Optional[float] = None
    week_pnl_pct: Optional[float] = None
    month_pnl: Optional[float] = None
    month_pnl_pct: Optional[float] = None
    ytd_pnl: Optional[float] = None
    ytd_pnl_pct: Optional[float] = None

    # Cost tracking
    total_cost: float = 0
    avg_cost_per_share: float = 0

    # Realized P&L (from closed positions)
    realized_pnl: float = 0
    total_pnl: Optional[float] = None

    # Timestamps
    first_purchase_date: Optional[str] = None
    last_activity_date: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "position_id": self.position_id,
            "ticker": self.ticker,
            "company_name": self.company_name,
            "sector": self.sector,
            "data_available": self.data_available,
        }

        if not self.data_available:
            result["data_error"] = self.data_error
            result["position"] = {
                "quantity": self.quantity,
                "cost_basis": round(self.cost_basis, 2),
            }
            return result

        result.update({
            "position": {
                "quantity": self.quantity,
                "cost_basis": round(self.cost_basis, 2),
                "current_price": round(self.current_price, 2) if self.current_price else None,
                "market_value": round(self.market_value, 2) if self.market_value else None,
            },
            "pnl": {
                "unrealized": round(self.unrealized_pnl, 2) if self.unrealized_pnl is not None else None,
                "unrealized_pct": round(self.unrealized_pnl_pct, 2) if self.unrealized_pnl_pct is not None else None,
                "realized": round(self.realized_pnl, 2),
                "total": round(self.total_pnl, 2) if self.total_pnl is not None else None,
            },
            "period_returns": {
                "day": {"pnl": round(self.day_pnl, 2) if self.day_pnl is not None else None,
                        "pct": round(self.day_pnl_pct, 2) if self.day_pnl_pct is not None else None},
                "week": {"pnl": round(self.week_pnl, 2) if self.week_pnl is not None else None,
                         "pct": round(self.week_pnl_pct, 2) if self.week_pnl_pct is not None else None},
                "month": {"pnl": round(self.month_pnl, 2) if self.month_pnl is not None else None,
                          "pct": round(self.month_pnl_pct, 2) if self.month_pnl_pct is not None else None},
                "ytd": {"pnl": round(self.ytd_pnl, 2) if self.ytd_pnl is not None else None,
                        "pct": round(self.ytd_pnl_pct, 2) if self.ytd_pnl_pct is not None else None},
            },
            "cost_tracking": {
                "total_cost": round(self.total_cost, 2),
                "avg_cost_per_share": round(self.avg_cost_per_share, 2),
            },
            "dates": {
                "first_purchase": self.first_purchase_date,
                "last_activity": self.last_activity_date,
            },
        })
        return result


@dataclass
class PortfolioPnLSummary:
    """Summary of P&L for all positions in a portfolio."""
    portfolio_id: int
    portfolio_name: str
    as_of_date: str
    data_available: bool = True
    partial_data: bool = False

    # Totals
    total_market_value: Optional[float] = None
    total_cost_basis: float = 0
    total_unrealized_pnl: Optional[float] = None
    total_realized_pnl: float = 0
    total_pnl: Optional[float] = None

    # Period totals (from real data)
    day_pnl: Optional[float] = None
    week_pnl: Optional[float] = None
    month_pnl: Optional[float] = None
    ytd_pnl: Optional[float] = None

    # Position details
    positions: List[PositionPnL] = field(default_factory=list)

    # Statistics
    winners_count: Optional[int] = None
    losers_count: Optional[int] = None
    best_performer: Optional[str] = None
    best_performer_pct: Optional[float] = None
    worst_performer: Optional[str] = None
    worst_performer_pct: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "portfolio_id": self.portfolio_id,
            "portfolio_name": self.portfolio_name,
            "as_of_date": self.as_of_date,
            "data_available": self.data_available,
            "partial_data": self.partial_data,
        }

        if not self.data_available:
            result["positions"] = [p.to_dict() for p in self.positions]
            return result

        result.update({
            "summary": {
                "total_market_value": round(self.total_market_value, 2) if self.total_market_value else None,
                "total_cost_basis": round(self.total_cost_basis, 2),
                "total_unrealized_pnl": round(self.total_unrealized_pnl, 2) if self.total_unrealized_pnl is not None else None,
                "total_realized_pnl": round(self.total_realized_pnl, 2),
                "total_pnl": round(self.total_pnl, 2) if self.total_pnl is not None else None,
            },
            "period_totals": {
                "day": round(self.day_pnl, 2) if self.day_pnl is not None else None,
                "week": round(self.week_pnl, 2) if self.week_pnl is not None else None,
                "month": round(self.month_pnl, 2) if self.month_pnl is not None else None,
                "ytd": round(self.ytd_pnl, 2) if self.ytd_pnl is not None else None,
            },
            "statistics": {
                "winners": self.winners_count,
                "losers": self.losers_count,
                "best_performer": self.best_performer,
                "best_performer_pct": round(self.best_performer_pct, 2) if self.best_performer_pct is not None else None,
                "worst_performer": self.worst_performer,
                "worst_performer_pct": round(self.worst_performer_pct, 2) if self.worst_performer_pct is not None else None,
            },
            "positions": [p.to_dict() for p in self.positions],
        })
        return result


def _get_price_history(ticker: str) -> Optional[Dict[str, float]]:
    """
    Get historical prices from yfinance for period P&L calculations.
    Returns dict with price_1d_ago, price_5d_ago, price_21d_ago, price_ytd_start.
    Returns None if data unavailable.
    """
    try:
        hist = yf.Ticker(ticker).history(period="1y")
        if hist.empty or len(hist) < 2:
            return None

        current = float(hist['Close'].iloc[-1])

        result = {
            "current": current,
            "price_1d_ago": float(hist['Close'].iloc[-2]) if len(hist) >= 2 else None,
            "price_5d_ago": float(hist['Close'].iloc[-5]) if len(hist) >= 5 else None,
            "price_21d_ago": float(hist['Close'].iloc[-21]) if len(hist) >= 21 else None,
        }

        # YTD start price
        current_year = datetime.now().year
        ytd_start = f"{current_year}-01-01"
        ytd_hist = hist[hist.index >= ytd_start]
        if not ytd_hist.empty:
            result["price_ytd_start"] = float(ytd_hist['Close'].iloc[0])
        else:
            result["price_ytd_start"] = None

        return result

    except Exception as exc:
        logger.debug("Price history fetch failed for %s: %s", ticker, exc)
        return None


def calculate_position_pnl(
    position_id: int,
    ticker: str,
    quantity: float,
    cost_basis: float,
    notes: Optional[str] = None,
) -> PositionPnL:
    """
    Calculate detailed P&L for a single position using REAL market data only.
    Returns no_data-style response when data is unavailable.
    """
    service = get_portfolio_service()

    # Get current market data
    market_data = service._get_market_data([ticker])
    data = market_data.get(ticker)

    # Get sector info and company name
    sector, industry = service._get_sector_info(ticker)
    company_name = _get_company_name(ticker)

    total_cost = quantity * cost_basis

    if data is None:
        # No market data available - return with data_available=False
        return PositionPnL(
            position_id=position_id,
            ticker=ticker,
            company_name=company_name,
            sector=sector,
            data_available=False,
            data_error="Market data unavailable from yfinance",
            quantity=quantity,
            cost_basis=cost_basis,
            total_cost=total_cost,
            avg_cost_per_share=cost_basis,
            last_activity_date=datetime.now().strftime("%Y-%m-%d"),
        )

    current_price = data["price"]
    market_value = quantity * current_price
    unrealized_pnl = market_value - total_cost
    unrealized_pnl_pct = (unrealized_pnl / total_cost * 100) if total_cost else None

    # Get historical prices for period P&L
    price_history = _get_price_history(ticker)

    day_pnl = None
    day_pnl_pct = None
    week_pnl = None
    week_pnl_pct = None
    month_pnl = None
    month_pnl_pct = None
    ytd_pnl = None
    ytd_pnl_pct = None

    if price_history:
        # Day P&L
        if price_history.get("price_1d_ago"):
            prev_day_price = price_history["price_1d_ago"]
            day_pnl = quantity * (current_price - prev_day_price)
            day_pnl_pct = ((current_price - prev_day_price) / prev_day_price * 100) if prev_day_price else None

        # Week P&L
        if price_history.get("price_5d_ago"):
            prev_week_price = price_history["price_5d_ago"]
            week_pnl = quantity * (current_price - prev_week_price)
            week_pnl_pct = ((current_price - prev_week_price) / prev_week_price * 100) if prev_week_price else None

        # Month P&L
        if price_history.get("price_21d_ago"):
            prev_month_price = price_history["price_21d_ago"]
            month_pnl = quantity * (current_price - prev_month_price)
            month_pnl_pct = ((current_price - prev_month_price) / prev_month_price * 100) if prev_month_price else None

        # YTD P&L
        if price_history.get("price_ytd_start"):
            ytd_start_price = price_history["price_ytd_start"]
            ytd_pnl = quantity * (current_price - ytd_start_price)
            ytd_pnl_pct = ((current_price - ytd_start_price) / ytd_start_price * 100) if ytd_start_price else None

    return PositionPnL(
        position_id=position_id,
        ticker=ticker,
        company_name=company_name,
        sector=sector,
        data_available=True,
        quantity=quantity,
        cost_basis=cost_basis,
        current_price=current_price,
        market_value=market_value,
        unrealized_pnl=unrealized_pnl,
        unrealized_pnl_pct=unrealized_pnl_pct,
        day_pnl=day_pnl,
        day_pnl_pct=day_pnl_pct,
        week_pnl=week_pnl,
        week_pnl_pct=week_pnl_pct,
        month_pnl=month_pnl,
        month_pnl_pct=month_pnl_pct,
        ytd_pnl=ytd_pnl,
        ytd_pnl_pct=ytd_pnl_pct,
        total_cost=total_cost,
        avg_cost_per_share=cost_basis,
        realized_pnl=0,  # Would track from closed trades
        total_pnl=unrealized_pnl,  # unrealized + realized
        first_purchase_date=None,  # Would come from transaction history
        last_activity_date=datetime.now().strftime("%Y-%m-%d"),
    )


def calculate_portfolio_pnl_summary(
    portfolio_id: int,
    portfolio_name: str,
    positions: List[Dict[str, Any]],
) -> PortfolioPnLSummary:
    """
    Calculate P&L summary for all positions in a portfolio.
    Uses only real market data from yfinance.
    """
    today = datetime.now().strftime("%Y-%m-%d")

    if not positions:
        return PortfolioPnLSummary(
            portfolio_id=portfolio_id,
            portfolio_name=portfolio_name,
            as_of_date=today,
            data_available=True,
            positions=[],
        )

    # Calculate P&L for each position
    position_pnls = []
    for pos in positions:
        pnl = calculate_position_pnl(
            position_id=pos.get("id", 0),
            ticker=pos.get("ticker", "UNKNOWN"),
            quantity=pos.get("qty", 0),
            cost_basis=pos.get("cost_basis", 0),
            notes=pos.get("notes"),
        )
        position_pnls.append(pnl)

    # Separate positions with and without data
    positions_with_data = [p for p in position_pnls if p.data_available]
    positions_without_data = [p for p in position_pnls if not p.data_available]

    total_cost_basis = sum(p.total_cost for p in position_pnls)

    if not positions_with_data:
        return PortfolioPnLSummary(
            portfolio_id=portfolio_id,
            portfolio_name=portfolio_name,
            as_of_date=today,
            data_available=False,
            total_cost_basis=total_cost_basis,
            positions=position_pnls,
        )

    # Calculate totals from positions with real data
    total_market_value = sum(p.market_value for p in positions_with_data if p.market_value is not None)
    total_unrealized_pnl = sum(p.unrealized_pnl for p in positions_with_data if p.unrealized_pnl is not None)
    total_realized_pnl = sum(p.realized_pnl for p in positions_with_data)

    # Period P&L totals
    day_pnls = [p.day_pnl for p in positions_with_data if p.day_pnl is not None]
    week_pnls = [p.week_pnl for p in positions_with_data if p.week_pnl is not None]
    month_pnls = [p.month_pnl for p in positions_with_data if p.month_pnl is not None]
    ytd_pnls = [p.ytd_pnl for p in positions_with_data if p.ytd_pnl is not None]

    day_pnl = sum(day_pnls) if day_pnls else None
    week_pnl = sum(week_pnls) if week_pnls else None
    month_pnl = sum(month_pnls) if month_pnls else None
    ytd_pnl = sum(ytd_pnls) if ytd_pnls else None

    # Statistics
    winners = [p for p in positions_with_data if p.unrealized_pnl is not None and p.unrealized_pnl >= 0]
    losers = [p for p in positions_with_data if p.unrealized_pnl is not None and p.unrealized_pnl < 0]

    sorted_by_pct = sorted(
        [p for p in positions_with_data if p.unrealized_pnl_pct is not None],
        key=lambda x: x.unrealized_pnl_pct,
        reverse=True
    )
    best = sorted_by_pct[0] if sorted_by_pct else None
    worst = sorted_by_pct[-1] if sorted_by_pct else None

    return PortfolioPnLSummary(
        portfolio_id=portfolio_id,
        portfolio_name=portfolio_name,
        as_of_date=today,
        data_available=True,
        partial_data=len(positions_without_data) > 0,
        total_market_value=total_market_value,
        total_cost_basis=total_cost_basis,
        total_unrealized_pnl=total_unrealized_pnl,
        total_realized_pnl=total_realized_pnl,
        total_pnl=total_unrealized_pnl + total_realized_pnl if total_unrealized_pnl is not None else None,
        day_pnl=day_pnl,
        week_pnl=week_pnl,
        month_pnl=month_pnl,
        ytd_pnl=ytd_pnl,
        positions=position_pnls,
        winners_count=len(winners),
        losers_count=len(losers),
        best_performer=best.ticker if best else None,
        best_performer_pct=best.unrealized_pnl_pct if best else None,
        worst_performer=worst.ticker if worst else None,
        worst_performer_pct=worst.unrealized_pnl_pct if worst else None,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Singleton instance
# ─────────────────────────────────────────────────────────────────────────────

_service: Optional[PortfolioService] = None


def get_portfolio_service() -> PortfolioService:
    """Get or create portfolio service singleton."""
    global _service
    if _service is None:
        _service = PortfolioService()
    return _service
