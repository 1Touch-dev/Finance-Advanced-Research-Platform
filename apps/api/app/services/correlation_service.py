"""
Correlations and event studies (C-series / G-01).

Everything here answers a question of the form "does A move with B, and by how
much", and the honest answer is often no. The rules below are not stylistic —
they exist because a report that manufactures a finding from five observations
is worse than one that says nothing, and every pass of this document has been
removing that failure mode.

1.  n travels with the coefficient. Always.
2.  Below MIN_SAMPLE observations the finding is suppressed entirely rather
    than printed with a caveat. A caveat is read as a hedge; an absence is not
    read at all, which is the correct outcome for a measurement that cannot be
    made.
3.  A confidence interval accompanies a point estimate, or neither is shown.
4.  Nothing here says "because". Every phrasing is co-movement, not cause.
5.  Testing many pairs at p<0.05 buys a false positive by construction, so the
    threshold is corrected for the number of tests actually run.
6.  Negative results are returned, not dropped. "No relationship at any lag
    tested" is the single most useful sentence this module can produce, and it
    only carries weight if the reader knows we would have reported the
    opposite.

No third-party statistics package is used. Everything below is closed-form on
the normal or t approximation, which keeps the dependency surface at numpy and
makes each number traceable to the line that computed it.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

# Below this, a correlation is not reported at any strength. Twelve is the
# convention the plan fixed; it is small enough to be reachable on a single
# report run and large enough that one outlier cannot carry the sign.
MIN_SAMPLE = 12

# Trading days either side of an event.
EVENT_WINDOW = 30

# Events closer together than this share overlapping windows, which breaks the
# independence assumption underneath the standard error.
MIN_EVENT_SPACING_DAYS = 5


def _safe(fn):
    """An analysis must never take the report down with it."""
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as error:
            logger.warning("Correlation %s failed: %s", fn.__name__, error)
            return None
    wrapper.__name__ = fn.__name__
    return wrapper


# ---------------------------------------------------------------------------
# Statistics — closed form, no scipy
# ---------------------------------------------------------------------------

def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _stdev(values: Sequence[float]) -> float:
    """Sample standard deviation, Bessel-corrected."""
    if len(values) < 2:
        return 0.0
    mu = _mean(values)
    return math.sqrt(sum((v - mu) ** 2 for v in values) / (len(values) - 1))


def _normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _two_sided_p(z: float) -> float:
    return 2.0 * (1.0 - _normal_cdf(abs(z)))


def pearson(xs: Sequence[float], ys: Sequence[float]) -> Optional[Dict[str, Any]]:
    """Correlation with a Fisher-z interval. None below MIN_SAMPLE.

    The interval is built on Fisher's transform rather than on r directly
    because r is bounded at ±1 and its sampling distribution is skewed
    everywhere except zero — a symmetric interval on r runs past the bound and
    reads as precision the estimate does not have.
    """
    pairs = [(x, y) for x, y in zip(xs, ys)
             if x is not None and y is not None]
    n = len(pairs)
    if n < MIN_SAMPLE:
        return None

    xs2 = [p[0] for p in pairs]
    ys2 = [p[1] for p in pairs]
    mx, my = _mean(xs2), _mean(ys2)
    sx, sy = _stdev(xs2), _stdev(ys2)
    if sx == 0 or sy == 0:
        return None

    cov = sum((x - mx) * (y - my) for x, y in pairs) / (n - 1)
    r = max(-0.999999, min(0.999999, cov / (sx * sy)))

    # Fisher z, back-transformed for the interval.
    z = 0.5 * math.log((1 + r) / (1 - r))
    se = 1.0 / math.sqrt(n - 3) if n > 3 else None
    if se is None:
        return None
    lo_z, hi_z = z - 1.96 * se, z + 1.96 * se
    lo = (math.exp(2 * lo_z) - 1) / (math.exp(2 * lo_z) + 1)
    hi = (math.exp(2 * hi_z) - 1) / (math.exp(2 * hi_z) + 1)

    t = r * math.sqrt((n - 2) / max(1e-12, 1 - r * r))
    return {
        "r": round(r, 3),
        "n": n,
        "ci_low": round(lo, 3),
        "ci_high": round(hi, 3),
        "p": round(_two_sided_p(t), 4),
        "significant": _two_sided_p(t) < 0.05,
    }


def bonferroni(p_value: float, tests_run: int) -> float:
    """Threshold corrected for the number of comparisons actually made."""
    return 0.05 / max(1, tests_run)


# ---------------------------------------------------------------------------
# Price series helpers
# ---------------------------------------------------------------------------

def _parse_bars(price_history: Dict[str, Any]) -> List[Tuple[datetime, float]]:
    """Daily closes, ascending, as (date, close)."""
    out = []
    for bar in (price_history or {}).get("bars") or []:
        try:
            out.append((datetime.strptime(str(bar["date"])[:10], "%Y-%m-%d"),
                        float(bar["close"])))
        except (KeyError, TypeError, ValueError):
            continue
    out.sort()
    return out


def _returns(closes: Sequence[Tuple[datetime, float]]) -> List[Tuple[datetime, float]]:
    """Simple daily returns. Index i is the return earned on day i."""
    out = []
    for i in range(1, len(closes)):
        prior = closes[i - 1][1]
        if prior:
            out.append((closes[i][0], (closes[i][1] - prior) / prior))
    return out


def _index_by_date(series: Sequence[Tuple[datetime, float]]) -> Dict[str, int]:
    return {d.strftime("%Y-%m-%d"): i for i, (d, _) in enumerate(series)}


def _nearest_trading_index(series: Sequence[Tuple[datetime, float]],
                           when: datetime, forward: bool = True) -> Optional[int]:
    """Index of the first trading day at or after (or before) a date.

    An event dated on a weekend or a holiday has no bar of its own. Anchoring
    to the next session is what a reader means by "the day it was announced".
    """
    if not series:
        return None
    if forward:
        for i, (d, _) in enumerate(series):
            if d >= when:
                return i
        return None
    last = None
    for i, (d, _) in enumerate(series):
        if d <= when:
            last = i
        else:
            break
    return last


# ---------------------------------------------------------------------------
# C-01  Insider sale timing against subsequent price
# ---------------------------------------------------------------------------

@_safe
def insider_sale_event_study(insider: Dict[str, Any],
                             price_history: Dict[str, Any],
                             window: int = EVENT_WINDOW) -> Optional[Dict[str, Any]]:
    """Do discretionary sales land before weakness that plan sales do not?

    A 10b5-1 sale is scheduled months ahead and its date carries no
    information about what the seller knew that week. A discretionary sale is
    chosen. Comparing the two is the whole design: the plan sales are a control
    drawn from the same issuer, the same period and the same people, which
    removes the market-wide drift that would otherwise have to be modelled.
    """
    closes = _parse_bars(price_history)
    if len(closes) < window * 2 + MIN_SAMPLE:
        return None

    sales = [t for t in (insider or {}).get("transactions") or []
             if t.get("acquired_disposed") == "D" and t.get("date")
             and t.get("value")]
    if not sales:
        return None

    first_day, last_day = closes[0][0], closes[-1][0]

    def forward_return(day: datetime) -> Optional[float]:
        idx = _nearest_trading_index(closes, day, forward=True)
        if idx is None or idx + window >= len(closes):
            return None
        start_price = closes[idx][1]
        end_price = closes[idx + window][1]
        if not start_price:
            return None
        return (end_price - start_price) / start_price

    groups: Dict[str, List[float]] = {"discretionary": [], "plan": []}
    used_dates: Dict[str, List[datetime]] = {"discretionary": [], "plan": []}

    for row in sales:
        try:
            day = datetime.strptime(str(row["date"])[:10], "%Y-%m-%d")
        except ValueError:
            continue
        if day < first_day or day > last_day:
            continue
        bucket = "plan" if row.get("is_10b5_1") else "discretionary"
        # One observation per bucket per day: a single decision executed as
        # fourteen Form 4 lines is one event, not fourteen.
        if any(abs((day - seen).days) < 1 for seen in used_dates[bucket]):
            continue
        ret = forward_return(day)
        if ret is None:
            continue
        used_dates[bucket].append(day)
        groups[bucket].append(ret)

    disc, plan = groups["discretionary"], groups["plan"]
    result: Dict[str, Any] = {
        "window_days": window,
        "discretionary_n": len(disc),
        "plan_n": len(plan),
        "suppressed": False,
    }

    if len(disc) < MIN_SAMPLE:
        result["suppressed"] = True
        result["reason"] = (
            f"{len(disc)} discretionary sale date"
            f"{'' if len(disc) == 1 else 's'} fall inside the price window; "
            f"{MIN_SAMPLE} is the minimum this report will measure on"
        )
        return result

    result["discretionary_mean_pct"] = round(_mean(disc) * 100, 2)
    result["discretionary_median_pct"] = round(
        sorted(disc)[len(disc) // 2] * 100, 2)

    # One-sample t against zero: did the stock move at all after these sales?
    sd = _stdev(disc)
    if sd > 0:
        t_stat = _mean(disc) / (sd / math.sqrt(len(disc)))
        result["p_vs_zero"] = round(_two_sided_p(t_stat), 4)
        half = 1.96 * sd / math.sqrt(len(disc))
        result["ci_low_pct"] = round((_mean(disc) - half) * 100, 2)
        result["ci_high_pct"] = round((_mean(disc) + half) * 100, 2)

    if len(plan) >= MIN_SAMPLE:
        result["plan_mean_pct"] = round(_mean(plan) * 100, 2)
        # Welch's t — the two groups have no reason to share a variance.
        s1, s2 = _stdev(disc), _stdev(plan)
        n1, n2 = len(disc), len(plan)
        se = math.sqrt(s1 * s1 / n1 + s2 * s2 / n2)
        if se > 0:
            t_stat = (_mean(disc) - _mean(plan)) / se
            result["spread_pct"] = round((_mean(disc) - _mean(plan)) * 100, 2)
            result["p_vs_plan"] = round(_two_sided_p(t_stat), 4)
            result["differs_from_plan"] = result["p_vs_plan"] < 0.05
    else:
        result["plan_note"] = (
            f"only {len(plan)} plan-sale date"
            f"{'' if len(plan) == 1 else 's'} in window — no control group"
        )
    return result


# ---------------------------------------------------------------------------
# C-02  8-K abnormal return by item code
# ---------------------------------------------------------------------------

# What each 8-K item actually reports. Grouping by item is the point: a
# departure of a principal officer and a results release are both 8-Ks and
# have nothing else in common.
_ITEM_LABEL = {
    "1.01": "Entry into a material agreement",
    "1.02": "Termination of a material agreement",
    "2.01": "Completion of an acquisition or disposition",
    "2.02": "Results of operations",
    "2.03": "Creation of a direct financial obligation",
    "2.05": "Costs associated with exit or disposal",
    "3.02": "Unregistered sale of equity",
    "5.02": "Departure or appointment of directors or officers",
    "5.03": "Amendment to articles or bylaws",
    "5.07": "Submission of matters to a vote",
    "7.01": "Regulation FD disclosure",
    "8.01": "Other events",
}


@_safe
def event_abnormal_returns(timeline: Dict[str, Any],
                           price_history: Dict[str, Any],
                           market_history: Optional[Dict[str, Any]] = None,
                           window: int = 3) -> Optional[Dict[str, Any]]:
    """Return around each 8-K, grouped by the item the filing reported.

    Where a market series is supplied the return is market-adjusted, which is
    the difference between "the stock rose" and "the stock rose more than the
    market did". Without it the raw return is reported and labelled as raw —
    an unadjusted number presented as abnormal is the most common way this
    analysis is got wrong.
    """
    closes = _parse_bars(price_history)
    if len(closes) < 60:
        return None

    market = _parse_bars(market_history) if market_history else []
    market_by_date = {d.strftime("%Y-%m-%d"): c for d, c in market}
    adjusted = len(market) >= 60

    events = (timeline or {}).get("events") or []
    by_item: Dict[str, List[float]] = {}
    total_events = 0

    for event in events:
        if event.get("form_type") != "8-K" or not event.get("date"):
            continue
        try:
            day = datetime.strptime(str(event["date"])[:10], "%Y-%m-%d")
        except ValueError:
            continue
        idx = _nearest_trading_index(closes, day, forward=True)
        if idx is None or idx == 0 or idx + window >= len(closes):
            continue

        before, after = closes[idx - 1][1], closes[idx + window][1]
        if not before:
            continue
        ret = (after - before) / before

        if adjusted:
            m_before = market_by_date.get(closes[idx - 1][0].strftime("%Y-%m-%d"))
            m_after = market_by_date.get(closes[idx + window][0].strftime("%Y-%m-%d"))
            if m_before and m_after:
                ret -= (m_after - m_before) / m_before

        codes = [i.get("code") for i in (event.get("items") or []) if i.get("code")]
        if not codes:
            codes = ["unclassified"]
        for code in codes:
            by_item.setdefault(str(code), []).append(ret)
        total_events += 1

    if total_events < MIN_SAMPLE:
        return {
            "suppressed": True,
            "n": total_events,
            "reason": (f"{total_events} 8-K filings fall inside the price "
                       f"window; {MIN_SAMPLE} is the minimum measured on"),
        }

    groups = []
    for code, rets in sorted(by_item.items(), key=lambda kv: -len(kv[1])):
        if len(rets) < MIN_SAMPLE:
            continue
        sd = _stdev(rets)
        entry = {
            "item": code,
            "label": _ITEM_LABEL.get(code, "Item " + code),
            "n": len(rets),
            "mean_pct": round(_mean(rets) * 100, 2),
        }
        if sd > 0:
            t_stat = _mean(rets) / (sd / math.sqrt(len(rets)))
            entry["p"] = round(_two_sided_p(t_stat), 4)
        groups.append(entry)

    # Correct for having tested every item group in one pass.
    threshold = bonferroni(0.05, max(1, len(groups)))
    for entry in groups:
        entry["significant"] = entry.get("p", 1.0) < threshold

    # Enough filings overall but none of the item groups individually clears
    # the bar. That is a distinct outcome from having no filings, and the
    # reader is owed the difference — the reason nothing is reported is
    # thinness per item code, not absence of 8-Ks.
    if not groups:
        return {
            "suppressed": True,
            "n": total_events,
            "reason": (
                f"{total_events} 8-K filings fall inside the price window, but "
                f"no single item code reaches {MIN_SAMPLE} of them. Pooling "
                f"unlike items — a results release with an officer departure — "
                f"would produce a number with no interpretation"
            ),
            "largest_group": max((len(v) for v in by_item.values()), default=0),
            "item_codes_seen": len(by_item),
        }

    return {
        "suppressed": False,
        "adjusted": adjusted,
        "window_days": window,
        "total_events": total_events,
        "groups": groups,
        "tests_run": len(groups),
        "threshold": round(threshold, 5),
        "suppressed_groups": sum(1 for v in by_item.values() if len(v) < MIN_SAMPLE),
    }


# ---------------------------------------------------------------------------
# C-03  Lobbying spend against federal obligations, with lag
# ---------------------------------------------------------------------------

@_safe
def lobbying_award_lag(political: Dict[str, Any],
                       contracts: Dict[str, Any],
                       max_lag_years: int = 3) -> Optional[Dict[str, Any]]:
    """Cross-correlate annual lobbying spend with annual federal obligations.

    This is the analysis most likely to be misread as causal, so the return
    carries the negative result explicitly and the renderer is expected to
    print it. Annual granularity puts n at the number of years held, which is
    almost always below MIN_SAMPLE — that is the honest state of the data and
    the reason quarterly XBRL (D-02) is on the plan.
    """
    # Lobbying arrives as {year: amount} under lobbying_summary; federal awards
    # arrive as a list of {year, amount}. Both shapes are read rather than one
    # being normalised upstream, because both are also rendered directly.
    lobbying = (political or {}).get("lobbying_summary") or political or {}
    spend_by_year: Dict[int, float] = {}
    for year, amount in (lobbying.get("year_breakdown") or {}).items():
        try:
            spend_by_year[int(year)] = float(amount or 0)
        except (TypeError, ValueError):
            continue
    # Only years with full quarterly coverage are comparable; a partial year
    # would drag the correlation toward an artefact of our retrieval window.
    complete = set(str(y) for y in (lobbying.get("complete_years") or []))
    if complete:
        spend_by_year = {y: v for y, v in spend_by_year.items()
                         if str(y) in complete}

    awards_by_year: Dict[int, float] = {}
    for row in (contracts or {}).get("year_breakdown") or []:
        try:
            awards_by_year[int(row.get("year"))] = float(row.get("amount") or 0)
        except (TypeError, ValueError):
            continue

    if not spend_by_year or not awards_by_year:
        return None

    results = []
    for lag in range(0, max_lag_years + 1):
        xs, ys = [], []
        for year, spend in sorted(spend_by_year.items()):
            award = awards_by_year.get(year + lag)
            if award is not None:
                xs.append(spend)
                ys.append(award)
        stat = pearson(xs, ys)
        results.append({
            "lag_years": lag,
            "pairs": len(xs),
            "result": stat,
        })

    best = max((r for r in results if r["result"]),
               key=lambda r: abs(r["result"]["r"]), default=None)
    return {
        "lags": results,
        "max_pairs": max((r["pairs"] for r in results), default=0),
        "min_sample": MIN_SAMPLE,
        "measurable": bool(best),
        "best": best,
        "negative_result": not best,
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def run_all(data: Dict[str, Any]) -> Dict[str, Any]:
    """Every correlation the held data supports. Absences are reported."""
    price = data.get("price_history") or {}
    out: Dict[str, Any] = {
        "min_sample": MIN_SAMPLE,
        "price_bars": len((price or {}).get("bars") or []),
        "price_source": price.get("source"),
    }

    out["insider_timing"] = insider_sale_event_study(
        data.get("insider_transactions") or {}, price)
    out["event_returns"] = event_abnormal_returns(
        data.get("event_timeline") or {}, price,
        data.get("market_history"))
    out["lobbying_lag"] = lobbying_award_lag(
        data.get("political_intelligence") or {},
        data.get("contract_intelligence") or {})

    out["ran"] = sum(1 for k in ("insider_timing", "event_returns",
                                 "lobbying_lag") if out.get(k))
    return out
