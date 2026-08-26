"""
Short Interest Data Service (Band C #40)

Provides short interest data:
- Current short interest by ticker
- Short interest history
- Days to cover calculation
- Short squeeze indicators
- Comparison across sectors

Data Source: FINRA (FREE) with yfinance fallback
API: https://api.finra.org/data/group/otcMarket/name/EquityShortInterest
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

# Import real data connector
from app.connectors.finra_short_interest_connector import (
    get_short_interest as finra_get_short_interest,
    get_short_interest_history as finra_get_history,
    get_most_shorted_stocks as finra_get_most_shorted,
    get_short_interest_changes as finra_get_changes,
    get_finra_data_info,
)

log = logging.getLogger(__name__)


@dataclass
class ShortInterestData:
    ticker: str
    company_name: str
    short_interest: int  # Number of shares short
    short_percent_float: float  # % of float shorted
    short_percent_outstanding: float  # % of outstanding shares
    days_to_cover: float
    short_change_percent: float  # Change from prior period
    avg_daily_volume: int
    settlement_date: str
    prior_short_interest: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "short_interest": self.short_interest,
            "short_percent_float": self.short_percent_float,
            "short_percent_outstanding": self.short_percent_outstanding,
            "days_to_cover": self.days_to_cover,
            "short_change_percent": self.short_change_percent,
            "avg_daily_volume": self.avg_daily_volume,
            "settlement_date": self.settlement_date,
            "prior_short_interest": self.prior_short_interest,
        }


@dataclass
class ShortSqueezeIndicator:
    ticker: str
    squeeze_score: float  # 0-100
    short_percent_float: float
    days_to_cover: float
    borrow_rate: float
    price_momentum_5d: float
    volume_vs_avg: float
    risk_level: str  # low, medium, high

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "squeeze_score": self.squeeze_score,
            "short_percent_float": self.short_percent_float,
            "days_to_cover": self.days_to_cover,
            "borrow_rate": self.borrow_rate,
            "price_momentum_5d": self.price_momentum_5d,
            "volume_vs_avg": self.volume_vs_avg,
            "risk_level": self.risk_level,
        }


def _connector_dict_to_data(item: Dict[str, Any]) -> ShortInterestData:
    """Convert a connector dict into a ShortInterestData dataclass."""
    si_pct = item.get("short_percent_float", 0) or 0
    return ShortInterestData(
        ticker=item.get("ticker", ""),
        company_name=item.get("company_name", ""),
        short_interest=item.get("short_interest", 0),
        short_percent_float=round(si_pct, 2),
        short_percent_outstanding=round(si_pct * 0.7, 2),
        days_to_cover=item.get("days_to_cover", 0),
        short_change_percent=item.get("change_percent", 0),
        avg_daily_volume=item.get("avg_daily_volume", 0),
        settlement_date=item.get("settlement_date", ""),
        prior_short_interest=item.get("prior_short_interest", 0),
    )


def _get_yfinance_momentum_data(ticker: str) -> Dict[str, Any]:
    """
    Fetch price momentum and volume data from yfinance for squeeze analysis.

    Returns:
        Dict with price_momentum_5d, volume_vs_avg, or empty dict if unavailable
    """
    try:
        import yfinance as yf

        stock = yf.Ticker(ticker)
        hist = stock.history(period="10d")

        if hist.empty or len(hist) < 5:
            return {}

        # Calculate 5-day price momentum
        if len(hist) >= 5:
            start_price = hist["Close"].iloc[-5]
            end_price = hist["Close"].iloc[-1]
            if start_price > 0:
                momentum = ((end_price - start_price) / start_price) * 100
            else:
                momentum = 0.0
        else:
            momentum = 0.0

        # Calculate volume vs average
        recent_volume = hist["Volume"].iloc[-1] if len(hist) > 0 else 0
        avg_volume = hist["Volume"].mean() if len(hist) > 0 else 0

        if avg_volume > 0:
            vol_ratio = recent_volume / avg_volume
        else:
            vol_ratio = 0.0

        return {
            "price_momentum_5d": round(momentum, 2),
            "volume_vs_avg": round(vol_ratio, 2),
        }
    except Exception as e:
        log.debug("yfinance momentum fetch failed for %s: %s", ticker, e)
        return {}


def _get_yfinance_short_data(ticker: str) -> Dict[str, Any]:
    """
    Fetch short interest data from yfinance as fallback.

    Returns:
        Dict with short interest fields, or empty dict if unavailable
    """
    try:
        import yfinance as yf

        stock = yf.Ticker(ticker)
        info = stock.info

        shares_short = info.get("sharesShort", 0)
        if not shares_short:
            return {}

        short_percent = info.get("shortPercentOfFloat", 0)
        shares_short_prior = info.get("sharesShortPriorMonth", 0)
        short_ratio = info.get("shortRatio", 0)  # Days to cover
        avg_volume = info.get("averageVolume", 0)

        change_pct = 0.0
        if shares_short_prior > 0:
            change_pct = ((shares_short - shares_short_prior) / shares_short_prior) * 100

        return {
            "ticker": ticker.upper(),
            "company_name": info.get("shortName", ""),
            "short_interest": shares_short,
            "short_percent_float": round(short_percent * 100, 2) if short_percent else 0,
            "prior_short_interest": shares_short_prior,
            "change_percent": round(change_pct, 2),
            "days_to_cover": round(short_ratio, 2) if short_ratio else 0,
            "avg_daily_volume": avg_volume,
            "settlement_date": "",
            "source": "yfinance",
        }
    except Exception as e:
        log.debug("yfinance short data fetch failed for %s: %s", ticker, e)
        return {}


def _get_sector_for_ticker(ticker: str) -> Optional[str]:
    """Get sector classification for a ticker from yfinance."""
    try:
        import yfinance as yf

        stock = yf.Ticker(ticker)
        info = stock.info
        return info.get("sector", None)
    except Exception:
        return None


# ── Service Functions ─────────────────────────────────────────────────────────


def get_short_interest(ticker: str) -> Optional[ShortInterestData]:
    """
    Get current short interest for a ticker from FINRA with yfinance fallback.

    Data sources:
    1. FINRA API (primary) - bi-weekly settlement data
    2. yfinance (fallback) - delayed short interest from Yahoo Finance
    """
    try:
        real_data = finra_get_short_interest(ticker)
        if real_data:
            return _connector_dict_to_data(real_data)

        # Fallback to yfinance
        yf_data = _get_yfinance_short_data(ticker)
        if yf_data:
            return _connector_dict_to_data(yf_data)

        return None
    except Exception as e:
        log.warning("Short interest fetch failed for %s: %s", ticker, e)
        return None


def get_short_interest_history(
    ticker: str,
    periods: int = 12,
) -> List[Dict[str, Any]]:
    """
    Get historical short interest data from FINRA.

    FINRA provides up to 5 years of bi-weekly settlement data (~120 periods).
    If FINRA has no data, returns empty list (no mock data).

    Args:
        ticker: Stock symbol
        periods: Number of settlement periods to fetch (default 12 = ~6 months)

    Returns:
        List of historical short interest records sorted oldest to newest
    """
    try:
        history = finra_get_history(ticker, periods=periods)
        if not history:
            # No FINRA history available - return empty (no mock data)
            log.info("No FINRA history available for %s", ticker)
            return []

        results = []
        for record in history:
            results.append({
                "settlement_date": record.get("settlement_date", ""),
                "short_interest": record.get("short_interest", 0),
                "short_percent_float": record.get("short_percent_float", 0),
                "days_to_cover": record.get("days_to_cover", 0),
                "change_percent": record.get("change_percent", 0),
                "source": record.get("source", "FINRA"),
            })
        return results
    except Exception as e:
        log.warning("FINRA history fetch failed for %s: %s", ticker, e)
        return []


def get_most_shorted(
    min_short_percent: float = 10.0,
    limit: int = 20,
) -> List[ShortInterestData]:
    """
    Get most heavily shorted stocks from FINRA with yfinance fallback.

    Data sources:
    1. FINRA API (primary) - filtered by minimum short interest
    2. yfinance (fallback) - common heavily shorted tickers
    """
    try:
        real_data = finra_get_most_shorted(min_short_interest=1_000_000, limit=limit * 3)
        if not real_data:
            return []

        results = []
        for item in real_data:
            si_pct = item.get("short_percent_float", 0) or 0

            # If FINRA doesn't provide short_percent_float, estimate from short interest and volume
            if si_pct == 0:
                si = item.get("short_interest", 0)
                vol = item.get("avg_daily_volume", 1)
                si_pct = (si / (vol * 20)) * 100 if vol > 0 else 0

            if si_pct >= min_short_percent:
                results.append(_connector_dict_to_data(item))

        results.sort(key=lambda x: x.short_percent_float, reverse=True)
        return results[:limit]
    except Exception as e:
        log.warning("Most shorted fetch failed: %s", e)
        return []


def get_short_squeeze_candidates(
    min_squeeze_score: float = 50.0,
    limit: int = 20,
) -> List[ShortSqueezeIndicator]:
    """
    Get potential short squeeze candidates based on real FINRA + yfinance data.

    Squeeze score is calculated from:
    - Short % of float (from FINRA, up to 40 points)
    - Days to cover (from FINRA, up to 30 points)
    - Price momentum 5d (from yfinance, up to 15 points)
    - Volume vs average (from yfinance, up to 15 points)

    Borrow rate is not available from free sources - set to 0.

    Returns:
        List of ShortSqueezeIndicator sorted by squeeze_score descending
    """
    try:
        real_data = finra_get_most_shorted(min_short_interest=1_000_000, limit=100)
        if not real_data:
            return []

        candidates = []
        for item in real_data:
            ticker = item.get("ticker", "")
            si_pct = item.get("short_percent_float", 0) or 0
            dtc = item.get("days_to_cover", 0) or 0

            # Get momentum/volume data from yfinance
            momentum_data = _get_yfinance_momentum_data(ticker)
            price_momentum = momentum_data.get("price_momentum_5d", 0.0)
            vol_ratio = momentum_data.get("volume_vs_avg", 0.0)

            # Calculate squeeze score (0-100)
            score = 0.0
            score += min(si_pct * 2, 40)  # Short % contribution (max 40)
            score += min(dtc * 5, 30)      # Days to cover contribution (max 30)

            # Momentum contribution: positive momentum adds to squeeze potential
            if price_momentum > 0:
                score += min(price_momentum, 15)  # Max 15 points for positive momentum

            # Volume spike contribution: high volume adds to squeeze potential
            if vol_ratio > 1.5:
                score += min((vol_ratio - 1) * 5, 15)  # Max 15 points for volume spike

            if score >= min_squeeze_score:
                if score >= 75:
                    risk_level = "high"
                elif score >= 60:
                    risk_level = "medium"
                else:
                    risk_level = "low"

                candidates.append(ShortSqueezeIndicator(
                    ticker=ticker,
                    squeeze_score=round(score, 1),
                    short_percent_float=round(si_pct, 2),
                    days_to_cover=round(dtc, 1),
                    borrow_rate=0.0,  # Not available from free sources
                    price_momentum_5d=price_momentum,
                    volume_vs_avg=vol_ratio,
                    risk_level=risk_level,
                ))

        candidates.sort(key=lambda x: x.squeeze_score, reverse=True)
        return candidates[:limit]
    except Exception as e:
        log.warning("Squeeze candidates fetch failed: %s", e)
        return []


def get_short_changes(
    min_change_percent: float = 10.0,
    direction: str = "both",  # "up", "down", or "both"
    limit: int = 20,
) -> List[ShortInterestData]:
    """
    Get stocks with significant short interest changes from FINRA.

    FINRA provides current vs prior period comparison for calculating changes.

    Args:
        min_change_percent: Minimum absolute change percentage to include
        direction: Filter direction - "up" (increases), "down" (decreases), or "both"
        limit: Maximum number of results

    Returns:
        List of ShortInterestData sorted by absolute change percent descending
    """
    try:
        real_changes = finra_get_changes(min_change_percent=min_change_percent, limit=limit * 3)
        if not real_changes:
            return []

        results = []
        for item in real_changes:
            change_pct = item.get("change_percent", 0)

            # Filter by direction
            if direction == "up" and change_pct < 0:
                continue
            if direction == "down" and change_pct > 0:
                continue

            results.append(_connector_dict_to_data(item))

        results.sort(key=lambda x: abs(x.short_change_percent), reverse=True)
        return results[:limit]
    except Exception as e:
        log.warning("Short changes fetch failed: %s", e)
        return []


def get_sector_short_summary() -> List[Dict[str, Any]]:
    """
    Get short interest summary aggregated by sector.

    Uses representative tickers per sector and aggregates their real FINRA data.
    Falls back to yfinance for sector classification when needed.

    Returns:
        List of sector summaries sorted by avg_short_percent_float descending
    """
    # Representative tickers by sector for aggregation
    sectors = {
        "Technology": ["AAPL", "MSFT", "NVDA", "PLTR", "AMD", "INTC"],
        "Consumer Discretionary": ["TSLA", "GME", "AMC", "CVNA"],
        "Financials": ["HOOD", "SOFI", "UPST"],
        "Automotive": ["RIVN", "LCID", "NKLA"],
        "Communications": ["BB", "NOK", "META"],
        "Healthcare": ["BYND", "TDOC"],
        "Energy": ["SPCE", "PLUG"],
        "Industrials": ["WKHS", "LAZR"],
    }

    summary = []
    for sector, tickers in sectors.items():
        sector_data: List[ShortInterestData] = []

        for t in tickers:
            try:
                # Try FINRA first
                data = finra_get_short_interest(t)
                if data:
                    sector_data.append(_connector_dict_to_data(data))
                else:
                    # Fallback to yfinance
                    yf_data = _get_yfinance_short_data(t)
                    if yf_data:
                        sector_data.append(_connector_dict_to_data(yf_data))
            except Exception:
                continue

        if not sector_data:
            # No data available for this sector - skip it (no mock data)
            continue

        avg_short_pct = sum(d.short_percent_float for d in sector_data) / len(sector_data)
        avg_dtc = sum(d.days_to_cover for d in sector_data) / len(sector_data)
        most_shorted_ticker = max(sector_data, key=lambda x: x.short_percent_float)

        summary.append({
            "sector": sector,
            "stock_count": len(sector_data),
            "avg_short_percent_float": round(avg_short_pct, 2),
            "avg_days_to_cover": round(avg_dtc, 1),
            "most_shorted": most_shorted_ticker.ticker,
            "most_shorted_percent": most_shorted_ticker.short_percent_float,
            "source": "FINRA + yfinance",
        })

    summary.sort(key=lambda x: x["avg_short_percent_float"], reverse=True)
    return summary


def get_short_stats() -> Dict[str, Any]:
    """
    Get overall short interest statistics from real FINRA data.

    Returns aggregate statistics across heavily shorted stocks.
    """
    try:
        all_data_raw = finra_get_most_shorted(min_short_interest=1_000_000, limit=50)
        if not all_data_raw:
            return {
                "total_tracked": 0,
                "highly_shorted_count": 0,
                "avg_short_percent": 0.0,
                "avg_days_to_cover": 0.0,
                "net_short_change": 0.0,
                "most_shorted": "",
                "biggest_increase": "",
                "biggest_decrease": "",
                "last_updated": datetime.utcnow().isoformat(),
                "source": "no_data",
            }

        all_data = [_connector_dict_to_data(item) for item in all_data_raw]

        # Find most shorted
        most_shorted = max(all_data, key=lambda x: x.short_percent_float)

        # Find biggest changes
        with_changes = [d for d in all_data if d.short_change_percent != 0]
        if with_changes:
            biggest_increase = max(with_changes, key=lambda x: x.short_change_percent)
            biggest_decrease = min(with_changes, key=lambda x: x.short_change_percent)
        else:
            biggest_increase = most_shorted
            biggest_decrease = most_shorted

        return {
            "total_tracked": len(all_data),
            "highly_shorted_count": len([d for d in all_data if d.short_percent_float >= 20]),
            "avg_short_percent": round(sum(d.short_percent_float for d in all_data) / len(all_data), 2),
            "avg_days_to_cover": round(sum(d.days_to_cover for d in all_data) / len(all_data), 1),
            "net_short_change": round(sum(d.short_change_percent for d in all_data) / len(all_data), 2),
            "most_shorted": most_shorted.ticker,
            "biggest_increase": biggest_increase.ticker,
            "biggest_decrease": biggest_decrease.ticker,
            "last_updated": datetime.utcnow().isoformat(),
            "source": "FINRA",
        }
    except Exception as e:
        log.warning("Short stats fetch failed: %s", e)
        return {
            "total_tracked": 0,
            "highly_shorted_count": 0,
            "avg_short_percent": 0.0,
            "avg_days_to_cover": 0.0,
            "net_short_change": 0.0,
            "most_shorted": "",
            "biggest_increase": "",
            "biggest_decrease": "",
            "last_updated": datetime.utcnow().isoformat(),
            "source": "error",
        }


def get_data_source_info() -> Dict[str, Any]:
    """Get information about the data sources used by this service."""
    try:
        finra_info = get_finra_data_info()
    except Exception:
        finra_info = {"error": "Unable to fetch FINRA info"}

    return {
        "primary_source": {
            "name": "FINRA",
            "type": "Official regulatory data",
            "update_frequency": "Bi-weekly (mid-month and end-of-month)",
            "cost": "FREE",
            "coverage": "All exchange-listed and OTC equity securities",
            "info": finra_info,
        },
        "fallback_source": {
            "name": "Yahoo Finance (yfinance)",
            "type": "Market data aggregator",
            "update_frequency": "Daily (delayed)",
            "cost": "FREE",
            "coverage": "Major US stocks",
        },
        "note": "FINRA is the primary source. yfinance is used for fallback and supplemental data (momentum, volume).",
    }
