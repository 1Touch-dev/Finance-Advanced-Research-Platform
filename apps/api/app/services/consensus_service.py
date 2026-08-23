"""
Point-in-Time Rolling Consensus Service (Band B #19-#21, #23)
Uses Finnhub for analyst recommendations and price targets.
"""
import os
import time
import logging
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from enum import Enum
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

FINNHUB_KEY = os.getenv("FINNHUB_API_KEY", "")
FINNHUB_BASE = "https://finnhub.io/api/v1"

_cache: Dict[str, Any] = {}
_CACHE_TTL = 1800


class EstimateType(str, Enum):
    EPS = "eps"
    REVENUE = "revenue"
    EBITDA = "ebitda"


class PeriodType(str, Enum):
    Q1 = "Q1"
    Q2 = "Q2"
    Q3 = "Q3"
    Q4 = "Q4"
    FY = "FY"


class RevisionDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    UNCHANGED = "unchanged"


class SurpriseType(str, Enum):
    BEAT = "beat"
    MISS = "miss"
    INLINE = "inline"


@dataclass
class ConsensusSnapshot:
    ticker: str
    estimate_type: str
    fiscal_year: int
    fiscal_period: str
    mean: float
    high: float
    low: float
    num_analysts: int
    buy: int = 0
    hold: int = 0
    sell: int = 0
    strong_buy: int = 0
    strong_sell: int = 0
    as_of_date: str = ""
    price_target_mean: float = 0.0
    price_target_high: float = 0.0
    price_target_low: float = 0.0
    source: str = "Finnhub"


@dataclass
class Revision:
    date: str
    direction: RevisionDirection
    old_value: float
    new_value: float
    change_pct: float
    analyst: str = ""


@dataclass
class Momentum:
    ticker: str
    estimate_type: str
    fiscal_year: int
    momentum_7d: float = 0.0
    momentum_30d: float = 0.0
    momentum_90d: float = 0.0
    trend: str = "neutral"
    num_revisions_30d: int = 0


# Backwards-compatible alias used by revision_screener_service
ConsensusMomentum = Momentum


@dataclass
class Dispersion:
    ticker: str
    estimate_type: str
    fiscal_year: int
    spread: float = 0.0
    std_dev: float = 0.0
    cv: float = 0.0
    dispersion_level: str = "low"
    uncertainty_score: float = 0.0


@dataclass
class Surprise:
    ticker: str
    fiscal_year: int
    fiscal_period: str
    estimate: float = 0.0
    actual: float = 0.0
    surprise_pct: float = 0.0
    direction: str = "inline"
    report_date: str = ""


@dataclass
class SurpriseHistory:
    ticker: str
    surprises: List[Surprise] = field(default_factory=list)
    beat_rate: float = 0.0
    avg_surprise_pct: float = 0.0
    beat_streak_current: int = 0


@dataclass
class ForwardMultiples:
    ticker: str
    fiscal_year: int
    forward_pe: float = 0.0
    forward_ps: float = 0.0
    forward_ev_ebitda: float = 0.0
    peg_ratio: float = 0.0
    eps_growth_rate: float = 0.0
    pe_premium_discount: float = 0.0
    current_price: float = 0.0


def _get_cached(key: str):
    if key in _cache:
        entry = _cache[key]
        if time.time() - entry["ts"] < _CACHE_TTL:
            return entry["data"]
    return None


def _set_cache(key: str, data):
    _cache[key] = {"data": data, "ts": time.time()}


def _finnhub_get(endpoint: str, params: dict = None) -> Optional[dict]:
    if not FINNHUB_KEY:
        return None
    params = params or {}
    params["token"] = FINNHUB_KEY
    try:
        r = requests.get(f"{FINNHUB_BASE}{endpoint}", params=params, timeout=12)
        if r.status_code == 200:
            return r.json()
        log.warning("Finnhub %s → %s", endpoint, r.status_code)
    except Exception as e:
        log.warning("Finnhub %s failed: %s", endpoint, e)
    return None


def _fetch_recommendations(ticker: str) -> list:
    """Fetch analyst recommendations from Finnhub."""
    cache_key = f"recs_{ticker}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    data = _finnhub_get("/stock/recommendation", {"symbol": ticker.upper()})
    result = data if isinstance(data, list) else []
    _set_cache(cache_key, result)
    return result


def _fetch_price_target(ticker: str) -> dict:
    """Fetch consensus price target from Finnhub."""
    cache_key = f"pt_{ticker}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    data = _finnhub_get("/stock/price-target", {"symbol": ticker.upper()})
    result = data if isinstance(data, dict) else {}
    _set_cache(cache_key, result)
    return result


def _fetch_eps_estimates(ticker: str) -> list:
    """Fetch EPS estimates from Finnhub."""
    cache_key = f"eps_est_{ticker}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    data = _finnhub_get("/stock/eps-estimate", {"symbol": ticker.upper()})
    result = data.get("data", []) if isinstance(data, dict) else []
    _set_cache(cache_key, result)
    return result


def _fetch_revenue_estimates(ticker: str) -> list:
    """Fetch revenue estimates from Finnhub."""
    cache_key = f"rev_est_{ticker}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    data = _finnhub_get("/stock/revenue-estimate", {"symbol": ticker.upper()})
    result = data.get("data", []) if isinstance(data, dict) else []
    _set_cache(cache_key, result)
    return result


def _fetch_earnings(ticker: str) -> list:
    """Fetch actual earnings from Finnhub."""
    cache_key = f"earnings_{ticker}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached
    data = _finnhub_get("/stock/earnings", {"symbol": ticker.upper()})
    result = data if isinstance(data, list) else []
    _set_cache(cache_key, result)
    return result


def get_consensus_snapshot(
    ticker: str,
    estimate_type: "EstimateType" = EstimateType.EPS,
    fiscal_year: Optional[int] = None,
    fiscal_period: "PeriodType" = PeriodType.FY,
    as_of_date=None,
) -> ConsensusSnapshot:
    fy = fiscal_year or date.today().year
    est_type = estimate_type if isinstance(estimate_type, str) else estimate_type.value
    period = fiscal_period if isinstance(fiscal_period, str) else fiscal_period.value

    recs = _fetch_recommendations(ticker)
    pt = _fetch_price_target(ticker)

    # Latest recommendation
    latest_rec = recs[0] if recs else {}
    buy_count = latest_rec.get("buy", 0)
    hold_count = latest_rec.get("hold", 0)
    sell_count = latest_rec.get("sell", 0)
    strong_buy = latest_rec.get("strongBuy", 0)
    strong_sell = latest_rec.get("strongSell", 0)
    total_analysts = buy_count + hold_count + sell_count + strong_buy + strong_sell

    # Price targets
    pt_mean = pt.get("targetMean", 0) or 0
    pt_high = pt.get("targetHigh", 0) or 0
    pt_low = pt.get("targetLow", 0) or 0

    # EPS / Revenue estimates
    if est_type == "eps":
        estimates = _fetch_eps_estimates(ticker)
    elif est_type == "revenue":
        estimates = _fetch_revenue_estimates(ticker)
    else:
        estimates = _fetch_eps_estimates(ticker)

    mean_est = 0.0
    high_est = 0.0
    low_est = 0.0
    if estimates:
        matched = [e for e in estimates if str(e.get("year", "")) == str(fy)]
        if matched:
            entry = matched[0]
            mean_est = entry.get("epsAvg", 0) or entry.get("revenueAvg", 0) or 0
            high_est = entry.get("epsHigh", 0) or entry.get("revenueHigh", 0) or 0
            low_est = entry.get("epsLow", 0) or entry.get("revenueLow", 0) or 0
            total_analysts = max(total_analysts, entry.get("numberAnalysts", 0))
        elif estimates:
            entry = estimates[0]
            mean_est = entry.get("epsAvg", 0) or entry.get("revenueAvg", 0) or 0
            high_est = entry.get("epsHigh", 0) or entry.get("revenueHigh", 0) or 0
            low_est = entry.get("epsLow", 0) or entry.get("revenueLow", 0) or 0

    return ConsensusSnapshot(
        ticker=ticker.upper(),
        estimate_type=est_type,
        fiscal_year=fy,
        fiscal_period=period,
        mean=mean_est,
        high=high_est,
        low=low_est,
        num_analysts=total_analysts,
        buy=buy_count,
        hold=hold_count,
        sell=sell_count,
        strong_buy=strong_buy,
        strong_sell=strong_sell,
        as_of_date=latest_rec.get("period", str(date.today())),
        price_target_mean=pt_mean,
        price_target_high=pt_high,
        price_target_low=pt_low,
    )


def get_rolling_consensus(
    ticker: str,
    estimate_type=EstimateType.EPS,
    fiscal_year: Optional[int] = None,
    fiscal_period=PeriodType.FY,
    lookback_days: int = 180,
) -> List[ConsensusSnapshot]:
    """Get rolling consensus history from recommendation timeline."""
    recs = _fetch_recommendations(ticker)
    if not recs:
        return []

    snapshots = []
    for rec in recs[:min(len(recs), lookback_days // 30)]:
        snap = ConsensusSnapshot(
            ticker=ticker.upper(),
            estimate_type=estimate_type.value if hasattr(estimate_type, "value") else estimate_type,
            fiscal_year=fiscal_year or date.today().year,
            fiscal_period=fiscal_period.value if hasattr(fiscal_period, "value") else fiscal_period,
            mean=0,
            high=0,
            low=0,
            num_analysts=rec.get("buy", 0) + rec.get("hold", 0) + rec.get("sell", 0) + rec.get("strongBuy", 0) + rec.get("strongSell", 0),
            buy=rec.get("buy", 0),
            hold=rec.get("hold", 0),
            sell=rec.get("sell", 0),
            strong_buy=rec.get("strongBuy", 0),
            strong_sell=rec.get("strongSell", 0),
            as_of_date=rec.get("period", ""),
        )
        snapshots.append(snap)
    return snapshots


def get_consensus_revisions(
    ticker: str,
    estimate_type=EstimateType.EPS,
    fiscal_year: Optional[int] = None,
    fiscal_period=PeriodType.FY,
    days: int = 90,
) -> List[Revision]:
    """Get consensus revision history derived from recommendation changes."""
    recs = _fetch_recommendations(ticker)
    if len(recs) < 2:
        return []

    revisions = []
    for i in range(len(recs) - 1):
        curr = recs[i]
        prev = recs[i + 1]
        curr_score = curr.get("buy", 0) * 2 + curr.get("strongBuy", 0) * 3 - curr.get("sell", 0) - curr.get("strongSell", 0) * 2
        prev_score = prev.get("buy", 0) * 2 + prev.get("strongBuy", 0) * 3 - prev.get("sell", 0) - prev.get("strongSell", 0) * 2

        if curr_score != prev_score:
            direction = RevisionDirection.UP if curr_score > prev_score else RevisionDirection.DOWN
            change_pct = ((curr_score - prev_score) / max(abs(prev_score), 1)) * 100
            revisions.append(Revision(
                date=curr.get("period", ""),
                direction=direction,
                old_value=float(prev_score),
                new_value=float(curr_score),
                change_pct=round(change_pct, 2),
            ))

    return revisions[:days // 30]


def get_consensus_momentum(
    ticker: str,
    estimate_type=EstimateType.EPS,
    fiscal_year: Optional[int] = None,
    fiscal_period=PeriodType.FY,
) -> Momentum:
    """Calculate consensus momentum from recommendation trends."""
    recs = _fetch_recommendations(ticker)
    fy = fiscal_year or date.today().year

    if len(recs) < 2:
        return Momentum(ticker=ticker.upper(), estimate_type=estimate_type.value if hasattr(estimate_type, "value") else estimate_type, fiscal_year=fy)

    def _score(rec):
        return rec.get("buy", 0) * 2 + rec.get("strongBuy", 0) * 3 - rec.get("sell", 0) - rec.get("strongSell", 0) * 2

    current_score = _score(recs[0])
    score_1m = _score(recs[1]) if len(recs) > 1 else current_score
    score_3m = _score(recs[3]) if len(recs) > 3 else score_1m

    m_7d = (current_score - score_1m) / max(abs(score_1m), 1) * 100
    m_30d = (current_score - score_1m) / max(abs(score_1m), 1) * 100
    m_90d = (current_score - score_3m) / max(abs(score_3m), 1) * 100

    if m_30d > 5:
        trend = "improving"
    elif m_30d < -5:
        trend = "deteriorating"
    else:
        trend = "stable"

    return Momentum(
        ticker=ticker.upper(),
        estimate_type=estimate_type.value if hasattr(estimate_type, "value") else estimate_type,
        fiscal_year=fy,
        momentum_7d=round(m_7d, 2),
        momentum_30d=round(m_30d, 2),
        momentum_90d=round(m_90d, 2),
        trend=trend,
        num_revisions_30d=min(len(recs), 4),
    )


def get_estimate_dispersion(
    ticker: str,
    estimate_type=EstimateType.EPS,
    fiscal_year: Optional[int] = None,
    fiscal_period=PeriodType.FY,
) -> Dispersion:
    """Calculate estimate dispersion from high/low spread."""
    fy = fiscal_year or date.today().year
    snapshot = get_consensus_snapshot(ticker, estimate_type, fy, fiscal_period)

    spread = snapshot.high - snapshot.low
    mean = snapshot.mean if snapshot.mean != 0 else 1
    cv = spread / abs(mean) if mean != 0 else 0
    std_dev = spread / 4  # approximate from range

    if cv > 0.3:
        level = "high"
    elif cv > 0.15:
        level = "moderate"
    else:
        level = "low"

    uncertainty = min(cv * 100, 100)

    return Dispersion(
        ticker=ticker.upper(),
        estimate_type=estimate_type.value if hasattr(estimate_type, "value") else estimate_type,
        fiscal_year=fy,
        spread=round(spread, 4),
        std_dev=round(std_dev, 4),
        cv=round(cv, 4),
        dispersion_level=level,
        uncertainty_score=round(uncertainty, 1),
    )


def get_earnings_surprise(ticker: str, fiscal_year: int, fiscal_period) -> Surprise:
    """Get earnings surprise for a specific quarter."""
    earnings = _fetch_earnings(ticker)
    period_val = fiscal_period.value if hasattr(fiscal_period, "value") else fiscal_period

    for e in earnings:
        q = e.get("quarter", 0)
        y = e.get("year", 0)
        if y == fiscal_year and f"Q{q}" == period_val:
            estimate = e.get("estimate", 0) or 0
            actual = e.get("actual", 0) or 0
            surprise_pct = e.get("surprisePercent", 0) or 0
            direction = "beat" if actual > estimate else "miss" if actual < estimate else "inline"
            return Surprise(
                ticker=ticker.upper(),
                fiscal_year=fiscal_year,
                fiscal_period=period_val,
                estimate=estimate,
                actual=actual,
                surprise_pct=surprise_pct,
                direction=direction,
                report_date=e.get("period", ""),
            )

    return Surprise(ticker=ticker.upper(), fiscal_year=fiscal_year, fiscal_period=period_val)


def get_surprise_history(ticker: str, quarters: int = 12) -> SurpriseHistory:
    """Get historical earnings surprise pattern."""
    earnings = _fetch_earnings(ticker)

    surprises = []
    beats = 0
    streak = 0
    total_surprise = 0.0

    for e in earnings[:quarters]:
        estimate = e.get("estimate", 0) or 0
        actual = e.get("actual", 0) or 0
        surprise_pct = e.get("surprisePercent", 0) or 0
        direction = "beat" if actual > estimate else "miss" if actual < estimate else "inline"

        if direction == "beat":
            beats += 1
            streak += 1
        else:
            streak = 0

        total_surprise += surprise_pct
        surprises.append(Surprise(
            ticker=ticker.upper(),
            fiscal_year=e.get("year", 0),
            fiscal_period=f"Q{e.get('quarter', 0)}",
            estimate=estimate,
            actual=actual,
            surprise_pct=surprise_pct,
            direction=direction,
            report_date=e.get("period", ""),
        ))

    total = len(surprises) or 1
    return SurpriseHistory(
        ticker=ticker.upper(),
        surprises=surprises,
        beat_rate=round(beats / total * 100, 1),
        avg_surprise_pct=round(total_surprise / total, 2),
        beat_streak_current=streak,
    )


def get_forward_multiples(ticker: str, fiscal_year: Optional[int] = None) -> ForwardMultiples:
    """Get forward valuation multiples based on consensus estimates."""
    fy = fiscal_year or date.today().year

    import yfinance as yf
    try:
        info = yf.Ticker(ticker).info
        price = info.get("currentPrice", 0) or info.get("regularMarketPrice", 0) or 0
        forward_pe = info.get("forwardPE", 0) or 0
        trailing_pe = info.get("trailingPE", 0) or 0
        forward_ps = info.get("priceToSalesTrailing12Months", 0) or 0
        ev_ebitda = info.get("enterpriseToEbitda", 0) or 0
        peg = info.get("pegRatio", 0) or 0
        eps_growth = info.get("earningsGrowth", 0) or 0
    except Exception:
        price = forward_pe = forward_ps = ev_ebitda = peg = eps_growth = trailing_pe = 0

    pe_premium = ((forward_pe / trailing_pe) - 1) * 100 if trailing_pe and forward_pe else 0

    return ForwardMultiples(
        ticker=ticker.upper(),
        fiscal_year=fy,
        forward_pe=round(forward_pe, 2),
        forward_ps=round(forward_ps, 2),
        forward_ev_ebitda=round(ev_ebitda, 2),
        peg_ratio=round(peg, 2),
        eps_growth_rate=round(eps_growth * 100, 2) if eps_growth else 0,
        pe_premium_discount=round(pe_premium, 2),
        current_price=round(price, 2),
    )


# ── Serializers ───────────────────────────────────────────────────────────────

def consensus_snapshot_to_dict(snap) -> dict:
    if isinstance(snap, dict):
        return snap
    return {
        "ticker": snap.ticker,
        "estimate_type": snap.estimate_type,
        "fiscal_year": snap.fiscal_year,
        "fiscal_period": snap.fiscal_period,
        "mean": snap.mean,
        "high": snap.high,
        "low": snap.low,
        "num_analysts": snap.num_analysts,
        "recommendations": {
            "strong_buy": snap.strong_buy,
            "buy": snap.buy,
            "hold": snap.hold,
            "sell": snap.sell,
            "strong_sell": snap.strong_sell,
        },
        "price_target": {
            "mean": snap.price_target_mean,
            "high": snap.price_target_high,
            "low": snap.price_target_low,
        },
        "as_of_date": snap.as_of_date,
        "source": snap.source,
    }


def revision_to_dict(rev) -> dict:
    if isinstance(rev, dict):
        return rev
    return {
        "date": rev.date,
        "direction": rev.direction.value if hasattr(rev.direction, "value") else rev.direction,
        "old_value": rev.old_value,
        "new_value": rev.new_value,
        "change_pct": rev.change_pct,
        "analyst": rev.analyst,
    }


def momentum_to_dict(m) -> dict:
    if isinstance(m, dict):
        return m
    return {
        "ticker": m.ticker,
        "estimate_type": m.estimate_type,
        "fiscal_year": m.fiscal_year,
        "momentum_7d": m.momentum_7d,
        "momentum_30d": m.momentum_30d,
        "momentum_90d": m.momentum_90d,
        "trend": m.trend,
        "num_revisions_30d": m.num_revisions_30d,
    }


def dispersion_to_dict(d) -> dict:
    if isinstance(d, dict):
        return d
    return {
        "ticker": d.ticker,
        "estimate_type": d.estimate_type,
        "fiscal_year": d.fiscal_year,
        "spread": d.spread,
        "std_dev": d.std_dev,
        "cv": d.cv,
        "dispersion_level": d.dispersion_level,
        "uncertainty_score": d.uncertainty_score,
    }


def surprise_to_dict(s) -> dict:
    if isinstance(s, dict):
        return s
    return {
        "ticker": s.ticker,
        "fiscal_year": s.fiscal_year,
        "fiscal_period": s.fiscal_period,
        "estimate": s.estimate,
        "actual": s.actual,
        "surprise_pct": s.surprise_pct,
        "direction": s.direction,
        "report_date": s.report_date,
    }


def surprise_history_to_dict(h) -> dict:
    if isinstance(h, dict):
        return h
    return {
        "ticker": h.ticker,
        "beat_rate": h.beat_rate,
        "avg_surprise_pct": h.avg_surprise_pct,
        "beat_streak_current": h.beat_streak_current,
        "surprises": [surprise_to_dict(s) for s in h.surprises],
        "total_quarters": len(h.surprises),
    }


def forward_multiples_to_dict(fm) -> dict:
    if isinstance(fm, dict):
        return fm
    return {
        "ticker": fm.ticker,
        "fiscal_year": fm.fiscal_year,
        "forward_pe": fm.forward_pe,
        "forward_ps": fm.forward_ps,
        "forward_ev_ebitda": fm.forward_ev_ebitda,
        "peg_ratio": fm.peg_ratio,
        "eps_growth_rate": fm.eps_growth_rate,
        "pe_premium_discount": fm.pe_premium_discount,
        "current_price": fm.current_price,
    }
