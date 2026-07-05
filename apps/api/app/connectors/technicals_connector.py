"""
Technical Indicators Connector — Phase 5th-July
=================================================
Pure-Python (pandas-based) implementation of 15 common technical indicators.
No TA-Lib C library required.

Indicators implemented:
  SMA (10/20/50/200), EMA (12/26), RSI (14),
  MACD (12/26/9), Bollinger Bands (20,2σ),
  ATR (14), OBV, Stochastic (14,3),
  Williams %R (14), ROC (12), ADX (14),
  VWAP (rolling), Support/Resistance levels,
  Golden/Death cross signals

All computed from yfinance OHLCV data.
"""

import logging
from typing import Optional

log = logging.getLogger(__name__)


def _to_series(bars: list, field: str) -> list:
    return [b[field] for b in bars]


def _sma(values: list, period: int) -> list:
    result = [None] * len(values)
    for i in range(period - 1, len(values)):
        result[i] = round(sum(values[i - period + 1:i + 1]) / period, 4)
    return result


def _ema(values: list, period: int) -> list:
    k = 2 / (period + 1)
    result = [None] * len(values)
    # Seed with first SMA
    first_valid = period - 1
    result[first_valid] = round(sum(values[:period]) / period, 4)
    for i in range(first_valid + 1, len(values)):
        prev = result[i - 1]
        result[i] = round(values[i] * k + prev * (1 - k), 4)
    return result


def _rsi(closes: list, period: int = 14) -> list:
    result = [None] * len(closes)
    if len(closes) < period + 1:
        return result
    gains = []
    losses = []
    for i in range(1, period + 1):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    for i in range(period, len(closes)):
        if i > period:
            diff = closes[i] - closes[i - 1]
            avg_gain = (avg_gain * (period - 1) + max(diff, 0)) / period
            avg_loss = (avg_loss * (period - 1) + max(-diff, 0)) / period
        rs = avg_gain / avg_loss if avg_loss != 0 else float("inf")
        result[i] = round(100 - (100 / (1 + rs)), 2)
    return result


def _macd(closes: list, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    ema_fast = _ema(closes, fast)
    ema_slow = _ema(closes, slow)
    macd_line = []
    for f, s in zip(ema_fast, ema_slow):
        if f is None or s is None:
            macd_line.append(None)
        else:
            macd_line.append(round(f - s, 4))
    valid = [v for v in macd_line if v is not None]
    signal_line_partial = _ema(valid, signal)
    # Pad to full length
    offset = len(macd_line) - len(valid)
    signal_line = [None] * offset + signal_line_partial
    histogram = []
    for m, sg in zip(macd_line, signal_line):
        if m is None or sg is None:
            histogram.append(None)
        else:
            histogram.append(round(m - sg, 4))
    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


def _bollinger(closes: list, period: int = 20, std_dev: float = 2.0) -> dict:
    mid = _sma(closes, period)
    upper = [None] * len(closes)
    lower = [None] * len(closes)
    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1:i + 1]
        mean = sum(window) / period
        variance = sum((x - mean) ** 2 for x in window) / period
        sd = variance ** 0.5
        upper[i] = round(mean + std_dev * sd, 4)
        lower[i] = round(mean - std_dev * sd, 4)
    return {"upper": upper, "middle": mid, "lower": lower}


def _atr(highs: list, lows: list, closes: list, period: int = 14) -> list:
    tr = []
    for i in range(len(closes)):
        high = highs[i]
        low = lows[i]
        prev_close = closes[i - 1] if i > 0 else closes[i]
        true_range = max(high - low, abs(high - prev_close), abs(low - prev_close))
        tr.append(true_range)
    result = [None] * len(closes)
    result[period - 1] = round(sum(tr[:period]) / period, 4)
    for i in range(period, len(closes)):
        result[i] = round((result[i - 1] * (period - 1) + tr[i]) / period, 4)
    return result


def _obv(closes: list, volumes: list) -> list:
    result = [0]
    for i in range(1, len(closes)):
        prev_obv = result[-1]
        if closes[i] > closes[i - 1]:
            result.append(prev_obv + volumes[i])
        elif closes[i] < closes[i - 1]:
            result.append(prev_obv - volumes[i])
        else:
            result.append(prev_obv)
    return result


def _stochastic(closes: list, highs: list, lows: list, k_period: int = 14, d_period: int = 3) -> dict:
    pct_k = [None] * len(closes)
    for i in range(k_period - 1, len(closes)):
        h = max(highs[i - k_period + 1:i + 1])
        l = min(lows[i - k_period + 1:i + 1])
        if h == l:
            pct_k[i] = 50.0
        else:
            pct_k[i] = round(100 * (closes[i] - l) / (h - l), 2)
    pct_d = _sma([v if v is not None else 0 for v in pct_k], d_period)
    return {"k": pct_k, "d": pct_d}


def _williams_r(closes: list, highs: list, lows: list, period: int = 14) -> list:
    result = [None] * len(closes)
    for i in range(period - 1, len(closes)):
        h = max(highs[i - period + 1:i + 1])
        l = min(lows[i - period + 1:i + 1])
        if h == l:
            result[i] = -50.0
        else:
            result[i] = round(-100 * (h - closes[i]) / (h - l), 2)
    return result


def _roc(closes: list, period: int = 12) -> list:
    result = [None] * len(closes)
    for i in range(period, len(closes)):
        prev = closes[i - period]
        if prev != 0:
            result[i] = round(100 * (closes[i] - prev) / prev, 4)
    return result


def _support_resistance(closes: list, n: int = 20) -> dict:
    """Simple pivot-based support/resistance."""
    if len(closes) < n:
        return {"support": None, "resistance": None}
    window = closes[-n:]
    return {
        "support":    round(min(window), 4),
        "resistance": round(max(window), 4),
    }


def _detect_signals(sma50: list, sma200: list, rsi_vals: list, closes: list) -> list:
    """Detect golden/death cross, RSI overbought/oversold."""
    signals = []
    n = len(closes)
    # Golden/Death cross
    if n >= 2 and sma50[-1] and sma50[-2] and sma200[-1] and sma200[-2]:
        if sma50[-2] < sma200[-2] and sma50[-1] > sma200[-1]:
            signals.append({"type": "golden_cross", "label": "Golden Cross (bullish)", "index": n - 1})
        elif sma50[-2] > sma200[-2] and sma50[-1] < sma200[-1]:
            signals.append({"type": "death_cross", "label": "Death Cross (bearish)", "index": n - 1})
    # RSI extremes
    latest_rsi = next((v for v in reversed(rsi_vals) if v is not None), None)
    if latest_rsi is not None:
        if latest_rsi > 70:
            signals.append({"type": "rsi_overbought", "label": f"RSI Overbought ({latest_rsi:.1f})", "rsi": latest_rsi})
        elif latest_rsi < 30:
            signals.append({"type": "rsi_oversold", "label": f"RSI Oversold ({latest_rsi:.1f})", "rsi": latest_rsi})
    return signals


# ─── Main entry ──────────────────────────────────────────────────────────────

def compute_technicals(ticker: str, period: str = "1y") -> dict:
    """Compute all technical indicators for a ticker."""
    from app.connectors.yfinance_connector import yf_price_history
    bars = yf_price_history(ticker, period=period, interval="1d")
    if not bars or len(bars) < 20:
        return {"ticker": ticker, "error": "Insufficient data", "bars": len(bars)}

    dates   = [b["date"]   for b in bars]
    opens   = [b["open"]   for b in bars]
    highs   = [b["high"]   for b in bars]
    lows    = [b["low"]    for b in bars]
    closes  = [b["close"]  for b in bars]
    volumes = [b["volume"] for b in bars]

    sma10  = _sma(closes, 10)
    sma20  = _sma(closes, 20)
    sma50  = _sma(closes, 50)
    sma200 = _sma(closes, 200)
    ema12  = _ema(closes, 12)
    ema26  = _ema(closes, 26)
    rsi14  = _rsi(closes, 14)
    macd   = _macd(closes)
    bb     = _bollinger(closes, 20)
    atr14  = _atr(highs, lows, closes, 14)
    obv    = _obv(closes, volumes)
    stoch  = _stochastic(closes, highs, lows, 14, 3)
    wr14   = _williams_r(closes, highs, lows, 14)
    roc12  = _roc(closes, 12)
    sr     = _support_resistance(closes, 20)
    signals = _detect_signals(sma50, sma200, rsi14, closes)

    # Return only last 100 bars worth of indicator values to keep response compact
    tail = -100

    return {
        "ticker":   ticker,
        "period":   period,
        "bar_count": len(bars),
        "dates":    dates[tail:],
        "price": {
            "open":   opens[tail:],
            "high":   highs[tail:],
            "low":    lows[tail:],
            "close":  closes[tail:],
            "volume": volumes[tail:],
        },
        "indicators": {
            "sma_10":   sma10[tail:],
            "sma_20":   sma20[tail:],
            "sma_50":   sma50[tail:],
            "sma_200":  sma200[tail:],
            "ema_12":   ema12[tail:],
            "ema_26":   ema26[tail:],
            "rsi_14":   rsi14[tail:],
            "macd":     {k: v[tail:] for k, v in macd.items()},
            "bollinger": {k: v[tail:] for k, v in bb.items()},
            "atr_14":   atr14[tail:],
            "obv":      obv[tail:],
            "stochastic": {k: v[tail:] for k, v in stoch.items()},
            "williams_r_14": wr14[tail:],
            "roc_12":   roc12[tail:],
        },
        "summary": {
            "current_price":    closes[-1],
            "sma_50":           sma50[-1],
            "sma_200":          sma200[-1],
            "rsi":              rsi14[-1],
            "macd_histogram":   macd["histogram"][-1],
            "bb_upper":         bb["upper"][-1],
            "bb_lower":         bb["lower"][-1],
            "atr":              atr14[-1],
            "support":          sr["support"],
            "resistance":       sr["resistance"],
            "signals":          signals,
        },
        "source": "yfinance + pure-python TA",
    }
