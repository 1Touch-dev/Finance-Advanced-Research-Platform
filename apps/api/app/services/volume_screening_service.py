"""
Unusual Volume Screening Service (Band B #28)
Uses yfinance for volume data and spike detection.
"""
import time
import logging
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from enum import Enum
from dataclasses import dataclass, field

import yfinance as yf

log = logging.getLogger(__name__)

_cache: Dict[str, Any] = {}
_CACHE_TTL = 1800

DEFAULT_WATCHLIST = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD",
    "JPM", "BAC", "GS", "NFLX", "CRM", "COIN", "SHOP", "SQ",
    "DIS", "NKE", "BA", "UBER", "ABNB", "PLTR", "SOFI", "RIVN",
    "SPY", "QQQ", "IWM",
]

SECTOR_MAP = {
    "Technology": ["AAPL", "MSFT", "GOOGL", "NVDA", "META", "AMD", "CRM"],
    "Consumer": ["AMZN", "TSLA", "NFLX", "DIS", "NKE", "SHOP", "UBER", "ABNB"],
    "Finance": ["JPM", "BAC", "GS", "COIN", "SQ", "SOFI"],
    "Industrial": ["BA"],
    "Other": ["PLTR", "RIVN"],
}


class VolumeSignal(str, Enum):
    EXTREME_SPIKE = "extreme_spike"
    HIGH_VOLUME = "high_volume"
    ABOVE_AVERAGE = "above_average"
    NORMAL = "normal"
    BELOW_AVERAGE = "below_average"
    VERY_LOW = "very_low"


class PriceVolumePattern(str, Enum):
    BREAKOUT = "breakout"
    BREAKDOWN = "breakdown"
    ACCUMULATION = "accumulation"
    DISTRIBUTION = "distribution"
    CLIMAX = "climax"
    NORMAL = "normal"


def _get_cached(key: str):
    if key in _cache:
        entry = _cache[key]
        if time.time() - entry["ts"] < _CACHE_TTL:
            return entry["data"]
    return None


def _set_cache(key: str, data):
    _cache[key] = {"data": data, "ts": time.time()}


def _classify_volume(ratio: float) -> VolumeSignal:
    if ratio >= 3.0:
        return VolumeSignal.EXTREME_SPIKE
    elif ratio >= 2.0:
        return VolumeSignal.HIGH_VOLUME
    elif ratio >= 1.3:
        return VolumeSignal.ABOVE_AVERAGE
    elif ratio >= 0.7:
        return VolumeSignal.NORMAL
    elif ratio >= 0.4:
        return VolumeSignal.BELOW_AVERAGE
    else:
        return VolumeSignal.VERY_LOW


@dataclass
class VolumeBar:
    ticker: str
    date: str
    volume: int
    avg_volume_20d: int
    ratio: float
    signal: VolumeSignal
    price: float = 0.0
    price_change_pct: float = 0.0


@dataclass
class VolumeAlert:
    ticker: str
    company_name: str
    date: str
    volume: int
    avg_volume_20d: int
    ratio: float
    signal: VolumeSignal
    price: float
    price_change_pct: float
    sector: str = ""


@dataclass
class VolumeScreen:
    timestamp: str
    threshold: float
    alerts: List[VolumeAlert] = field(default_factory=list)
    total_screened: int = 0
    total_flagged: int = 0


@dataclass
class VolumeProfile:
    ticker: str
    company_name: str
    avg_volume_20d: int
    avg_volume_50d: int
    latest_volume: int
    latest_ratio: float
    latest_signal: VolumeSignal
    spikes_30d: int
    volume_trend: str
    price: float = 0.0
    sector: str = ""


@dataclass
class SectorVolumeFlow:
    sector: str
    tickers: List[str]
    total_volume: int
    avg_ratio: float
    direction: str
    top_mover: str = ""
    top_mover_ratio: float = 0.0


def _fetch_volume_data(tickers: List[str], period: str = "1mo") -> Dict[str, Any]:
    """Fetch volume + price data for multiple tickers."""
    cache_key = f"voldata_{'_'.join(sorted(tickers[:5]))}_{period}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        data = yf.download(tickers, period=period, progress=False)
        if data.empty:
            return {}
        result = {"data": data, "tickers": tickers}
        _set_cache(cache_key, result)
        return result
    except Exception as e:
        log.warning("Volume data fetch failed: %s", e)
        return {}


def get_volume_bar(ticker: str, bar_date=None) -> VolumeBar:
    """Get latest volume bar for a ticker."""
    try:
        data = yf.download(ticker, period="1mo", progress=False)
        if data.empty:
            return VolumeBar(ticker=ticker.upper(), date=str(date.today()), volume=0, avg_volume_20d=0, ratio=0, signal=VolumeSignal.NORMAL)

        volumes = data["Volume"].dropna().values.flatten()
        closes = data["Close"].dropna().values.flatten()
        dates = [str(d.date()) for d in data.index]

        if len(volumes) < 2:
            return VolumeBar(ticker=ticker.upper(), date=str(date.today()), volume=0, avg_volume_20d=0, ratio=0, signal=VolumeSignal.NORMAL)

        latest_vol = int(volumes[-1])
        avg_20d = int(np.mean(volumes[-20:])) if len(volumes) >= 20 else int(np.mean(volumes))
        ratio = round(latest_vol / avg_20d, 2) if avg_20d > 0 else 0

        price = float(closes[-1]) if len(closes) > 0 else 0
        price_change = ((closes[-1] / closes[-2]) - 1) * 100 if len(closes) >= 2 else 0

        return VolumeBar(
            ticker=ticker.upper(),
            date=dates[-1] if dates else str(date.today()),
            volume=latest_vol,
            avg_volume_20d=avg_20d,
            ratio=ratio,
            signal=_classify_volume(ratio),
            price=round(price, 2),
            price_change_pct=round(float(price_change), 2),
        )
    except Exception as e:
        log.warning("Volume bar failed for %s: %s", ticker, e)
        return VolumeBar(ticker=ticker.upper(), date=str(date.today()), volume=0, avg_volume_20d=0, ratio=0, signal=VolumeSignal.NORMAL)


def get_volume_history(ticker: str, days: int = 30) -> List[VolumeBar]:
    """Get historical volume data for a ticker."""
    try:
        period = "1mo" if days <= 30 else "3mo"
        data = yf.download(ticker, period=period, progress=False)
        if data.empty:
            return []

        volumes = data["Volume"].dropna().values.flatten()
        closes = data["Close"].dropna().values.flatten()
        dates = [str(d.date()) for d in data.index]

        bars = []
        for i in range(min(days, len(volumes))):
            idx = len(volumes) - 1 - i
            if idx < 0:
                break

            avg_start = max(0, idx - 20)
            avg_20d = int(np.mean(volumes[avg_start:idx])) if idx > 0 else int(volumes[idx])
            vol = int(volumes[idx])
            ratio = round(vol / avg_20d, 2) if avg_20d > 0 else 0

            price_chg = 0
            if idx > 0 and closes[idx - 1] > 0:
                price_chg = ((closes[idx] / closes[idx - 1]) - 1) * 100

            bars.append(VolumeBar(
                ticker=ticker.upper(),
                date=dates[idx],
                volume=vol,
                avg_volume_20d=avg_20d,
                ratio=ratio,
                signal=_classify_volume(ratio),
                price=round(float(closes[idx]), 2),
                price_change_pct=round(float(price_chg), 2),
            ))

        bars.reverse()
        return bars
    except Exception as e:
        log.warning("Volume history failed for %s: %s", ticker, e)
        return []


def screen_unusual_volume(min_ratio: float = 2.0, tickers: Optional[List[str]] = None, sector: Optional[str] = None) -> VolumeScreen:
    """Screen for unusual volume across watchlist."""
    cache_key = f"vol_screen_{min_ratio}_{sector}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    ticker_list = tickers or DEFAULT_WATCHLIST
    if sector and sector in SECTOR_MAP:
        ticker_list = SECTOR_MAP[sector]

    try:
        data = yf.download(ticker_list, period="1mo", progress=False)
        if data.empty:
            return VolumeScreen(timestamp=str(datetime.now()), threshold=min_ratio)
    except Exception:
        return VolumeScreen(timestamp=str(datetime.now()), threshold=min_ratio)

    alerts = []
    for ticker in ticker_list:
        try:
            if len(ticker_list) > 1:
                vol_series = data["Volume"][ticker].dropna().values if ticker in data["Volume"].columns else np.array([])
                close_series = data["Close"][ticker].dropna().values if ticker in data["Close"].columns else np.array([])
            else:
                vol_series = data["Volume"].dropna().values.flatten()
                close_series = data["Close"].dropna().values.flatten()

            if len(vol_series) < 5:
                continue

            latest_vol = int(vol_series[-1])
            avg_20d = int(np.mean(vol_series[-20:])) if len(vol_series) >= 20 else int(np.mean(vol_series))
            ratio = latest_vol / avg_20d if avg_20d > 0 else 0

            if ratio < min_ratio:
                continue

            price = float(close_series[-1]) if len(close_series) > 0 else 0
            price_chg = ((close_series[-1] / close_series[-2]) - 1) * 100 if len(close_series) >= 2 else 0

            # Find sector
            t_sector = ""
            for s, s_tickers in SECTOR_MAP.items():
                if ticker in s_tickers:
                    t_sector = s
                    break

            alerts.append(VolumeAlert(
                ticker=ticker.upper(),
                company_name=ticker.upper(),
                date=str(date.today()),
                volume=latest_vol,
                avg_volume_20d=avg_20d,
                ratio=round(ratio, 2),
                signal=_classify_volume(ratio),
                price=round(price, 2),
                price_change_pct=round(float(price_chg), 2),
                sector=t_sector,
            ))
        except Exception:
            continue

    alerts.sort(key=lambda x: x.ratio, reverse=True)

    result = VolumeScreen(
        timestamp=str(datetime.now()),
        threshold=min_ratio,
        alerts=alerts,
        total_screened=len(ticker_list),
        total_flagged=len(alerts),
    )
    _set_cache(cache_key, result)
    return result


def get_ticker_volume_profile(ticker: str) -> VolumeProfile:
    """Get comprehensive volume profile for a ticker."""
    cache_key = f"vol_profile_{ticker}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        data = yf.download(ticker, period="3mo", progress=False)
        if data.empty:
            raise ValueError(f"No data for {ticker}")

        volumes = data["Volume"].dropna().values.flatten()
        closes = data["Close"].dropna().values.flatten()

        if len(volumes) < 5:
            raise ValueError(f"Insufficient data for {ticker}")

        latest_vol = int(volumes[-1])
        avg_20d = int(np.mean(volumes[-20:])) if len(volumes) >= 20 else int(np.mean(volumes))
        avg_50d = int(np.mean(volumes[-50:])) if len(volumes) >= 50 else int(np.mean(volumes))
        ratio = latest_vol / avg_20d if avg_20d > 0 else 0

        # Count spikes in last 30 days
        spikes = 0
        for v in volumes[-30:]:
            if v > avg_20d * 2:
                spikes += 1

        # Volume trend
        if len(volumes) >= 20:
            recent_avg = np.mean(volumes[-10:])
            older_avg = np.mean(volumes[-20:-10])
            if recent_avg > older_avg * 1.2:
                trend = "increasing"
            elif recent_avg < older_avg * 0.8:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"

        price = float(closes[-1]) if len(closes) > 0 else 0

        # Get company name and sector
        t_sector = ""
        for s, s_tickers in SECTOR_MAP.items():
            if ticker.upper() in s_tickers:
                t_sector = s
                break

        result = VolumeProfile(
            ticker=ticker.upper(),
            company_name=ticker.upper(),
            avg_volume_20d=avg_20d,
            avg_volume_50d=avg_50d,
            latest_volume=latest_vol,
            latest_ratio=round(ratio, 2),
            latest_signal=_classify_volume(ratio),
            spikes_30d=spikes,
            volume_trend=trend,
            price=round(price, 2),
            sector=t_sector,
        )
        _set_cache(cache_key, result)
        return result
    except ValueError:
        raise
    except Exception as e:
        log.warning("Volume profile failed for %s: %s", ticker, e)
        raise ValueError(f"Failed to get profile for {ticker}")


def get_sector_volume_flow(sector: str) -> SectorVolumeFlow:
    """Get sector-level volume flow analysis."""
    if sector not in SECTOR_MAP:
        raise ValueError(f"Unknown sector: {sector}. Available: {list(SECTOR_MAP.keys())}")

    cache_key = f"sector_flow_{sector}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    tickers = SECTOR_MAP[sector]
    try:
        data = yf.download(tickers, period="5d", progress=False)
        if data.empty:
            return SectorVolumeFlow(sector=sector, tickers=tickers, total_volume=0, avg_ratio=0, direction="neutral")

        total_vol = 0
        ratios = []
        top_mover = ""
        top_ratio = 0.0

        for ticker in tickers:
            try:
                if len(tickers) > 1:
                    vol_series = data["Volume"][ticker].dropna().values if ticker in data["Volume"].columns else np.array([])
                else:
                    vol_series = data["Volume"].dropna().values.flatten()

                if len(vol_series) < 2:
                    continue

                latest = int(vol_series[-1])
                avg = int(np.mean(vol_series[:-1])) if len(vol_series) > 1 else latest
                ratio = latest / avg if avg > 0 else 1.0

                total_vol += latest
                ratios.append(ratio)

                if ratio > top_ratio:
                    top_ratio = ratio
                    top_mover = ticker
            except Exception:
                continue

        avg_ratio = round(float(np.mean(ratios)), 2) if ratios else 1.0
        if avg_ratio > 1.3:
            direction = "inflow"
        elif avg_ratio < 0.7:
            direction = "outflow"
        else:
            direction = "neutral"

        result = SectorVolumeFlow(
            sector=sector,
            tickers=tickers,
            total_volume=total_vol,
            avg_ratio=avg_ratio,
            direction=direction,
            top_mover=top_mover,
            top_mover_ratio=round(top_ratio, 2),
        )
        _set_cache(cache_key, result)
        return result
    except Exception as e:
        log.warning("Sector flow failed for %s: %s", sector, e)
        return SectorVolumeFlow(sector=sector, tickers=tickers, total_volume=0, avg_ratio=0, direction="neutral")


# ── Serializers ───────────────────────────────────────────────────────────────

def volume_bar_to_dict(bar) -> dict:
    if isinstance(bar, dict):
        return bar
    return {
        "ticker": bar.ticker,
        "date": bar.date,
        "volume": bar.volume,
        "avg_volume_20d": bar.avg_volume_20d,
        "ratio": bar.ratio,
        "signal": bar.signal.value if hasattr(bar.signal, "value") else bar.signal,
        "price": bar.price,
        "price_change_pct": bar.price_change_pct,
    }


def alert_to_dict(alert) -> dict:
    if isinstance(alert, dict):
        return alert
    return {
        "ticker": alert.ticker,
        "company_name": alert.company_name,
        "date": alert.date,
        "volume": alert.volume,
        "avg_volume_20d": alert.avg_volume_20d,
        "ratio": alert.ratio,
        "signal": alert.signal.value if hasattr(alert.signal, "value") else alert.signal,
        "price": alert.price,
        "price_change_pct": alert.price_change_pct,
        "sector": alert.sector,
    }


def screen_to_dict(screen) -> dict:
    if isinstance(screen, dict):
        return screen
    return {
        "timestamp": screen.timestamp,
        "threshold": screen.threshold,
        "total_screened": screen.total_screened,
        "total_flagged": screen.total_flagged,
        "alerts": [alert_to_dict(a) for a in screen.alerts],
    }


def profile_to_dict(profile) -> dict:
    if isinstance(profile, dict):
        return profile
    return {
        "ticker": profile.ticker,
        "company_name": profile.company_name,
        "avg_volume_20d": profile.avg_volume_20d,
        "avg_volume_50d": profile.avg_volume_50d,
        "latest_volume": profile.latest_volume,
        "latest_ratio": profile.latest_ratio,
        "latest_signal": profile.latest_signal.value if hasattr(profile.latest_signal, "value") else profile.latest_signal,
        "spikes_30d": profile.spikes_30d,
        "volume_trend": profile.volume_trend,
        "price": profile.price,
        "sector": profile.sector,
    }


def sector_flow_to_dict(flow) -> dict:
    if isinstance(flow, dict):
        return flow
    return {
        "sector": flow.sector,
        "tickers": flow.tickers,
        "total_volume": flow.total_volume,
        "avg_ratio": flow.avg_ratio,
        "direction": flow.direction,
        "top_mover": flow.top_mover,
        "top_mover_ratio": flow.top_mover_ratio,
    }
