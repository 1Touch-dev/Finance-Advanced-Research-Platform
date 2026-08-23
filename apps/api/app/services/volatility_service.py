"""
Implied Volatility Surface Service (Band B #27)
Uses yfinance options chain for IV data + historical price data for HV.
"""
import time
import logging
import numpy as np
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from dataclasses import dataclass, field

import yfinance as yf

log = logging.getLogger(__name__)

_cache: Dict[str, Any] = {}
_CACHE_TTL = 1800

DEFAULT_SCREEN_TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD",
    "SPY", "QQQ", "IWM", "NFLX", "CRM", "COIN", "SHOP", "SQ",
]


def _get_cached(key: str):
    if key in _cache:
        entry = _cache[key]
        if time.time() - entry["ts"] < _CACHE_TTL:
            return entry["data"]
    return None


def _set_cache(key: str, data):
    _cache[key] = {"data": data, "ts": time.time()}


@dataclass
class TermStructurePoint:
    expiry: str
    days_to_expiry: int
    atm_iv: float
    num_strikes: int


@dataclass
class VolatilitySurface:
    ticker: str
    underlying_price: float
    as_of_date: str
    data_delay_minutes: int = 15
    as_of_time: str = ""
    term_structure: List[Dict] = field(default_factory=list)
    surface: List[Dict] = field(default_factory=list)
    strikes_by_expiry: Dict[str, List[Dict]] = field(default_factory=dict)
    skew: Dict[str, Any] = field(default_factory=dict)
    atm_iv_30d: float = 0.0
    atm_iv_60d: float = 0.0
    atm_iv_90d: float = 0.0
    put_call_skew_25d: float = 0.0
    iv_rank_52w: float = 0.0

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "underlying_price": self.underlying_price,
            "as_of_date": self.as_of_date,
            "data_delay_minutes": self.data_delay_minutes,
            "summary": {
                "atm_iv_30d": self.atm_iv_30d,
                "atm_iv_60d": self.atm_iv_60d,
                "atm_iv_90d": self.atm_iv_90d,
                "put_call_skew_25d": self.put_call_skew_25d,
                "iv_rank_52w": self.iv_rank_52w,
            },
            "term_structure": self.term_structure,
            "expirations_available": len(self.strikes_by_expiry),
            "source": "yfinance (delayed EOD)",
        }


@dataclass
class VolatilitySnapshot:
    ticker: str
    current_iv: float
    historical_vol_30d: float
    historical_vol_60d: float
    iv_rank: float
    iv_percentile: float
    iv_hv_spread: float
    put_call_skew: float
    term_structure_shape: str

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "current_iv": self.current_iv,
            "historical_volatility": {
                "hv_30d": self.historical_vol_30d,
                "hv_60d": self.historical_vol_60d,
            },
            "iv_rank": self.iv_rank,
            "iv_percentile": self.iv_percentile,
            "iv_hv_spread": self.iv_hv_spread,
            "put_call_skew": self.put_call_skew,
            "term_structure_shape": self.term_structure_shape,
            "source": "yfinance",
        }


@dataclass
class VolatilityHistory:
    ticker: str
    days: int
    iv_high_52w: float = 0.0
    iv_low_52w: float = 0.0
    iv_current: float = 0.0
    iv_rank: float = 0.0
    hv_series: List[Dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "period_days": self.days,
            "iv_52w_high": self.iv_high_52w,
            "iv_52w_low": self.iv_low_52w,
            "iv_current": self.iv_current,
            "iv_rank": self.iv_rank,
            "hv_data_points": len(self.hv_series),
            "hv_series": self.hv_series[-30:],  # Last 30 points
            "source": "yfinance",
        }


@dataclass
class SkewAnalysis:
    ticker: str
    expiry: str
    skew_25d: float = 0.0
    skew_10d: float = 0.0
    atm_iv: float = 0.0
    put_iv_25d: float = 0.0
    call_iv_25d: float = 0.0
    interpretation: str = ""

    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "expiry": self.expiry,
            "skew_25_delta": self.skew_25d,
            "skew_10_delta": self.skew_10d,
            "atm_iv": self.atm_iv,
            "put_iv_25d": self.put_iv_25d,
            "call_iv_25d": self.call_iv_25d,
            "interpretation": self.interpretation,
            "source": "yfinance",
        }


def _compute_hv(prices, window: int = 21) -> float:
    """Compute annualized historical volatility."""
    if prices is None or len(prices) < window + 1:
        return 0.0
    returns = np.diff(np.log(prices[-window - 1:]))
    return float(np.std(returns) * np.sqrt(252) * 100)


def _get_option_iv_data(ticker: str) -> Dict[str, Any]:
    """Fetch options chain and extract IV data."""
    cache_key = f"vol_opts_{ticker}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    try:
        t = yf.Ticker(ticker)
        info = t.info
        price = info.get("currentPrice") or info.get("regularMarketPrice") or 0

        expirations = t.options
        if not expirations:
            return {"price": price, "expirations": [], "chains": {}}

        chains = {}
        for exp in expirations[:6]:  # Limit to 6 nearest expiries
            try:
                chain = t.option_chain(exp)
                calls = chain.calls
                puts = chain.puts

                # Get ATM strikes (closest to current price)
                call_ivs = []
                put_ivs = []
                strike_data = []

                if not calls.empty and "impliedVolatility" in calls.columns:
                    for _, row in calls.iterrows():
                        iv = row.get("impliedVolatility", 0)
                        strike = row.get("strike", 0)
                        if iv and iv > 0 and strike > 0:
                            call_ivs.append({"strike": strike, "iv": iv, "volume": row.get("volume", 0) or 0})

                if not puts.empty and "impliedVolatility" in puts.columns:
                    for _, row in puts.iterrows():
                        iv = row.get("impliedVolatility", 0)
                        strike = row.get("strike", 0)
                        if iv and iv > 0 and strike > 0:
                            put_ivs.append({"strike": strike, "iv": iv, "volume": row.get("volume", 0) or 0})

                # Find ATM IV
                atm_call_iv = 0
                atm_put_iv = 0
                if call_ivs and price > 0:
                    closest_call = min(call_ivs, key=lambda x: abs(x["strike"] - price))
                    atm_call_iv = closest_call["iv"]
                if put_ivs and price > 0:
                    closest_put = min(put_ivs, key=lambda x: abs(x["strike"] - price))
                    atm_put_iv = closest_put["iv"]

                atm_iv = (atm_call_iv + atm_put_iv) / 2 if (atm_call_iv and atm_put_iv) else (atm_call_iv or atm_put_iv)

                chains[exp] = {
                    "atm_iv": round(atm_iv * 100, 2),
                    "call_ivs": call_ivs[:10],
                    "put_ivs": put_ivs[:10],
                    "num_calls": len(call_ivs),
                    "num_puts": len(put_ivs),
                }
            except Exception:
                continue

        result = {"price": price, "expirations": list(expirations[:6]), "chains": chains}
        _set_cache(cache_key, result)
        return result
    except Exception as e:
        log.warning("Options data fetch failed for %s: %s", ticker, e)
        return {"price": 0, "expirations": [], "chains": {}}


class VolatilityService:
    """Implied volatility surface and analysis service."""

    def get_volatility_surface(self, ticker: str) -> VolatilitySurface:
        opt_data = _get_option_iv_data(ticker)
        price = opt_data.get("price", 0)
        chains = opt_data.get("chains", {})

        term_structure = []
        today = date.today()
        iv_30d = iv_60d = iv_90d = 0.0

        for exp_str, chain_data in chains.items():
            try:
                exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
                dte = (exp_date - today).days
                atm_iv = chain_data.get("atm_iv", 0)

                term_structure.append({
                    "expiry": exp_str,
                    "days_to_expiry": dte,
                    "atm_iv": atm_iv,
                    "num_strikes": chain_data.get("num_calls", 0) + chain_data.get("num_puts", 0),
                })

                if 20 <= dte <= 40 and iv_30d == 0:
                    iv_30d = atm_iv
                elif 50 <= dte <= 70 and iv_60d == 0:
                    iv_60d = atm_iv
                elif 80 <= dte <= 100 and iv_90d == 0:
                    iv_90d = atm_iv
            except Exception as exc:
                log.debug("term structure parse failed for expiry %s: %s", exp_str, exc)
                continue

        if term_structure and iv_30d == 0:
            iv_30d = term_structure[0].get("atm_iv", 0)

        # Compute skew from first expiry
        skew_25d = 0.0
        if chains:
            first_chain = list(chains.values())[0]
            put_ivs = first_chain.get("put_ivs", [])
            call_ivs = first_chain.get("call_ivs", [])
            if put_ivs and call_ivs and price > 0:
                otm_puts = [p for p in put_ivs if p["strike"] < price * 0.95]
                otm_calls = [c for c in call_ivs if c["strike"] > price * 1.05]
                if otm_puts and otm_calls:
                    avg_put_iv = sum(p["iv"] for p in otm_puts[:3]) / len(otm_puts[:3])
                    avg_call_iv = sum(c["iv"] for c in otm_calls[:3]) / len(otm_calls[:3])
                    skew_25d = round((avg_put_iv - avg_call_iv) * 100, 2)

        return VolatilitySurface(
            ticker=ticker.upper(),
            underlying_price=round(price, 2),
            as_of_date=str(today),
            term_structure=term_structure,
            strikes_by_expiry={},
            atm_iv_30d=iv_30d,
            atm_iv_60d=iv_60d,
            atm_iv_90d=iv_90d,
            put_call_skew_25d=skew_25d,
        )

    def get_volatility_snapshot(self, ticker: str) -> VolatilitySnapshot:
        cache_key = f"vol_snap_{ticker}"
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached

        # Historical volatility from price data
        try:
            data = yf.download(ticker, period="3mo", progress=False)
            prices = data["Close"].dropna().values.flatten() if not data.empty else np.array([])
        except Exception as exc:
            log.debug("historical price download failed for %s: %s", ticker, exc)
            prices = np.array([])

        hv_30d = _compute_hv(prices, 21)
        hv_60d = _compute_hv(prices, 42)

        # IV from options
        opt_data = _get_option_iv_data(ticker)
        chains = opt_data.get("chains", {})
        current_iv = 0.0
        if chains:
            first = list(chains.values())[0]
            current_iv = first.get("atm_iv", 0)

        iv_hv_spread = round(current_iv - hv_30d, 2)

        # Approximate IV rank (simplified - would need 52w history)
        if current_iv > 0 and hv_30d > 0:
            iv_rank = min(100, max(0, round((current_iv / (hv_30d * 1.5)) * 50, 1)))
        else:
            iv_rank = 50.0
        iv_percentile = iv_rank  # simplified

        # Term structure shape
        term_ivs = [c.get("atm_iv", 0) for c in chains.values() if c.get("atm_iv", 0) > 0]
        if len(term_ivs) >= 2:
            if term_ivs[-1] > term_ivs[0]:
                shape = "contango"
            elif term_ivs[-1] < term_ivs[0]:
                shape = "backwardation"
            else:
                shape = "flat"
        else:
            shape = "insufficient_data"

        # Skew
        skew = 0.0
        if chains:
            first_chain = list(chains.values())[0]
            put_ivs = first_chain.get("put_ivs", [])
            call_ivs = first_chain.get("call_ivs", [])
            price = opt_data.get("price", 0)
            if put_ivs and call_ivs and price > 0:
                otm_puts = [p for p in put_ivs if p["strike"] < price * 0.95]
                otm_calls = [c for c in call_ivs if c["strike"] > price * 1.05]
                if otm_puts and otm_calls:
                    skew = round((sum(p["iv"] for p in otm_puts[:3]) / len(otm_puts[:3]) -
                                  sum(c["iv"] for c in otm_calls[:3]) / len(otm_calls[:3])) * 100, 2)

        result = VolatilitySnapshot(
            ticker=ticker.upper(),
            current_iv=current_iv,
            historical_vol_30d=round(hv_30d, 2),
            historical_vol_60d=round(hv_60d, 2),
            iv_rank=iv_rank,
            iv_percentile=iv_percentile,
            iv_hv_spread=iv_hv_spread,
            put_call_skew=skew,
            term_structure_shape=shape,
        )
        _set_cache(cache_key, result)
        return result

    def get_volatility_history(self, ticker: str, days: int = 252) -> VolatilityHistory:
        cache_key = f"vol_hist_{ticker}_{days}"
        cached = _get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            period = "1y" if days <= 252 else "2y"
            data = yf.download(ticker, period=period, progress=False)
            if data.empty:
                return VolatilityHistory(ticker=ticker.upper(), days=days)

            prices = data["Close"].dropna().values.flatten()
            dates = [str(d.date()) for d in data["Close"].dropna().index]
        except Exception as exc:
            log.debug("volatility history download failed for %s: %s", ticker, exc)
            return VolatilityHistory(ticker=ticker.upper(), days=days)

        # Rolling HV
        window = 21
        hv_series = []
        for i in range(window, len(prices)):
            hv = _compute_hv(prices[:i + 1], window)
            hv_series.append({"date": dates[i], "hv_21d": round(hv, 2)})

        hvs = [h["hv_21d"] for h in hv_series if h["hv_21d"] > 0]
        iv_high = max(hvs) if hvs else 0
        iv_low = min(hvs) if hvs else 0
        iv_current = hvs[-1] if hvs else 0
        iv_rank = round(((iv_current - iv_low) / (iv_high - iv_low)) * 100, 1) if (iv_high - iv_low) > 0 else 50

        result = VolatilityHistory(
            ticker=ticker.upper(),
            days=days,
            iv_high_52w=round(iv_high, 2),
            iv_low_52w=round(iv_low, 2),
            iv_current=round(iv_current, 2),
            iv_rank=iv_rank,
            hv_series=hv_series,
        )
        _set_cache(cache_key, result)
        return result

    def get_skew_analysis(self, ticker: str, expiry: Optional[str] = None) -> SkewAnalysis:
        opt_data = _get_option_iv_data(ticker)
        chains = opt_data.get("chains", {})
        price = opt_data.get("price", 0)

        if not chains:
            return SkewAnalysis(ticker=ticker.upper(), expiry="N/A", interpretation="No options data available")

        # Use specified or first expiry
        if expiry and expiry in chains:
            chain = chains[expiry]
            exp_str = expiry
        else:
            exp_str = list(chains.keys())[0]
            chain = chains[exp_str]

        atm_iv = chain.get("atm_iv", 0)
        put_ivs = chain.get("put_ivs", [])
        call_ivs = chain.get("call_ivs", [])

        put_iv_25d = 0.0
        call_iv_25d = 0.0
        put_iv_10d = 0.0

        if price > 0:
            # 25-delta approximation: ~5% OTM
            otm_puts_25 = [p for p in put_ivs if 0.93 * price <= p["strike"] <= 0.97 * price]
            otm_calls_25 = [c for c in call_ivs if 1.03 * price <= c["strike"] <= 1.07 * price]
            # 10-delta approximation: ~10% OTM
            otm_puts_10 = [p for p in put_ivs if 0.88 * price <= p["strike"] <= 0.92 * price]

            if otm_puts_25:
                put_iv_25d = sum(p["iv"] for p in otm_puts_25) / len(otm_puts_25) * 100
            if otm_calls_25:
                call_iv_25d = sum(c["iv"] for c in otm_calls_25) / len(otm_calls_25) * 100
            if otm_puts_10:
                put_iv_10d = sum(p["iv"] for p in otm_puts_10) / len(otm_puts_10) * 100

        skew_25d = round(put_iv_25d - call_iv_25d, 2) if (put_iv_25d and call_iv_25d) else 0
        skew_10d = round(put_iv_10d - atm_iv, 2) if (put_iv_10d and atm_iv) else 0

        if skew_25d > 10:
            interp = "Significant downside fear — puts much more expensive than calls"
        elif skew_25d > 5:
            interp = "Moderate negative skew — typical protective put demand"
        elif skew_25d < -2:
            interp = "Unusual positive skew — call demand exceeds put demand"
        else:
            interp = "Relatively flat skew — balanced market sentiment"

        return SkewAnalysis(
            ticker=ticker.upper(),
            expiry=exp_str,
            skew_25d=skew_25d,
            skew_10d=skew_10d,
            atm_iv=atm_iv,
            put_iv_25d=round(put_iv_25d, 2),
            call_iv_25d=round(call_iv_25d, 2),
            interpretation=interp,
        )

    def screen_volatility(self, min_iv_rank: float = 0, max_iv_rank: float = 100, min_iv_hv_spread: float = -1, tickers: Optional[List[str]] = None) -> List[Dict]:
        ticker_list = tickers or DEFAULT_SCREEN_TICKERS
        results = []

        for ticker in ticker_list:
            try:
                snap = self.get_volatility_snapshot(ticker)
                if snap.iv_rank < min_iv_rank or snap.iv_rank > max_iv_rank:
                    continue
                if snap.iv_hv_spread < min_iv_hv_spread:
                    continue

                results.append({
                    "ticker": snap.ticker,
                    "current_iv": snap.current_iv,
                    "hv_30d": snap.historical_vol_30d,
                    "iv_rank": snap.iv_rank,
                    "iv_hv_spread": snap.iv_hv_spread,
                    "skew": snap.put_call_skew,
                    "term_structure": snap.term_structure_shape,
                })
            except Exception:
                continue

        results.sort(key=lambda x: x.get("iv_rank", 0), reverse=True)
        return results


_service_instance = None


def get_volatility_service() -> VolatilityService:
    global _service_instance
    if _service_instance is None:
        _service_instance = VolatilityService()
    return _service_instance
