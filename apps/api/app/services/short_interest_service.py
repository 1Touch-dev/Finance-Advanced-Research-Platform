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


# ── Service Functions ─────────────────────────────────────────────────────────


def get_short_interest(ticker: str) -> Optional[ShortInterestData]:
    """Get current short interest for a ticker from FINRA/yfinance."""
    try:
        real_data = finra_get_short_interest(ticker)
        if not real_data:
            return None
        return _connector_dict_to_data(real_data)
    except Exception as e:
        log.warning("FINRA data fetch failed for %s: %s", ticker, e)
        return None


def get_short_interest_history(
    ticker: str,
    periods: int = 12,
) -> List[Dict[str, Any]]:
    """Get historical short interest data from FINRA."""
    try:
        history = finra_get_history(ticker, periods=periods)
        if not history:
            return []

        results = []
        for record in history:
            results.append({
                "settlement_date": record.get("settlement_date", ""),
                "short_interest": record.get("short_interest", 0),
                "short_percent_float": record.get("short_percent_float", 0),
                "days_to_cover": record.get("days_to_cover", 0),
            })
        return results
    except Exception as e:
        log.warning("FINRA history fetch failed for %s: %s", ticker, e)
        return []


def get_most_shorted(
    min_short_percent: float = 10.0,
    limit: int = 20,
) -> List[ShortInterestData]:
    """Get most heavily shorted stocks from FINRA."""
    try:
        real_data = finra_get_most_shorted(min_short_interest=1_000_000, limit=limit * 3)
        if not real_data:
            return []

        results = []
        for item in real_data:
            si_pct = item.get("short_percent_float", 0) or 0
            if si_pct == 0:
                si = item.get("short_interest", 0)
                vol = item.get("avg_daily_volume", 1)
                si_pct = (si / (vol * 20)) * 100 if vol > 0 else 0
            if si_pct >= min_short_percent:
                results.append(_connector_dict_to_data(item))

        results.sort(key=lambda x: x.short_percent_float, reverse=True)
        return results[:limit]
    except Exception as e:
        log.warning("FINRA most shorted fetch failed: %s", e)
        return []


def get_short_squeeze_candidates(
    min_squeeze_score: float = 50.0,
    limit: int = 20,
) -> List[ShortSqueezeIndicator]:
    """Get potential short squeeze candidates based on FINRA data.

    Squeeze score is computed from short % of float and days to cover.
    Borrow rate, momentum, and volume_vs_avg are not available from FINRA;
    they are set to 0 to indicate no data.
    """
    try:
        real_data = finra_get_most_shorted(min_short_interest=1_000_000, limit=100)
        if not real_data:
            return []

        candidates = []
        for item in real_data:
            si_pct = item.get("short_percent_float", 0) or 0
            dtc = item.get("days_to_cover", 0) or 0

            score = 0.0
            score += min(si_pct * 2, 40)
            score += min(dtc * 5, 30)

            if score >= min_squeeze_score:
                risk_level = "low" if score < 60 else ("medium" if score < 75 else "high")
                candidates.append(ShortSqueezeIndicator(
                    ticker=item.get("ticker", ""),
                    squeeze_score=round(score, 1),
                    short_percent_float=round(si_pct, 2),
                    days_to_cover=round(dtc, 1),
                    borrow_rate=0.0,
                    price_momentum_5d=0.0,
                    volume_vs_avg=0.0,
                    risk_level=risk_level,
                ))

        candidates.sort(key=lambda x: x.squeeze_score, reverse=True)
        return candidates[:limit]
    except Exception as e:
        log.warning("FINRA squeeze candidates fetch failed: %s", e)
        return []


def get_short_changes(
    min_change_percent: float = 10.0,
    direction: str = "both",  # "up", "down", or "both"
    limit: int = 20,
) -> List[ShortInterestData]:
    """Get stocks with significant short interest changes from FINRA."""
    try:
        real_changes = finra_get_changes(min_change_percent=min_change_percent, limit=limit * 3)
        if not real_changes:
            return []

        results = []
        for item in real_changes:
            change_pct = item.get("change_percent", 0)
            if direction == "up" and change_pct < 0:
                continue
            if direction == "down" and change_pct > 0:
                continue
            results.append(_connector_dict_to_data(item))

        results.sort(key=lambda x: abs(x.short_change_percent), reverse=True)
        return results[:limit]
    except Exception as e:
        log.warning("FINRA short changes fetch failed: %s", e)
        return []


def get_sector_short_summary() -> List[Dict[str, Any]]:
    """Get short interest summary by sector.

    Fetches real data for representative tickers in each sector.
    """
    sectors = {
        "Technology": ["AAPL", "MSFT", "NVDA", "PLTR"],
        "Consumer Discretionary": ["TSLA", "GME", "AMC"],
        "Financials": ["HOOD", "SOFI"],
        "Automotive": ["RIVN", "LCID"],
        "Communications": ["BB", "NOK"],
    }

    summary = []
    for sector, tickers in sectors.items():
        sector_data: List[ShortInterestData] = []
        for t in tickers:
            try:
                data = finra_get_short_interest(t)
                if data:
                    sector_data.append(_connector_dict_to_data(data))
            except Exception:
                continue

        if not sector_data:
            continue

        avg_short_pct = sum(d.short_percent_float for d in sector_data) / len(sector_data)
        avg_dtc = sum(d.days_to_cover for d in sector_data) / len(sector_data)

        summary.append({
            "sector": sector,
            "stock_count": len(sector_data),
            "avg_short_percent_float": round(avg_short_pct, 2),
            "avg_days_to_cover": round(avg_dtc, 1),
            "most_shorted": max(sector_data, key=lambda x: x.short_percent_float).ticker,
        })

    summary.sort(key=lambda x: x["avg_short_percent_float"], reverse=True)
    return summary


def get_short_stats() -> Dict[str, Any]:
    """Get overall short interest statistics from real data."""
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
            }

        all_data = [_connector_dict_to_data(item) for item in all_data_raw]

        return {
            "total_tracked": len(all_data),
            "highly_shorted_count": len([d for d in all_data if d.short_percent_float >= 20]),
            "avg_short_percent": round(sum(d.short_percent_float for d in all_data) / len(all_data), 2),
            "avg_days_to_cover": round(sum(d.days_to_cover for d in all_data) / len(all_data), 1),
            "net_short_change": round(sum(d.short_change_percent for d in all_data) / len(all_data), 2),
            "most_shorted": max(all_data, key=lambda x: x.short_percent_float).ticker,
            "biggest_increase": max(all_data, key=lambda x: x.short_change_percent).ticker,
            "biggest_decrease": min(all_data, key=lambda x: x.short_change_percent).ticker,
            "last_updated": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        log.warning("FINRA short stats fetch failed: %s", e)
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
        }
