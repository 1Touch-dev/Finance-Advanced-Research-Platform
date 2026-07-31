"""
Charts for the intelligence report.

Every figure here is drawn from data the report already states in a table. A
chart that shows something the numbers do not is a second source of truth, and
this document has spent nine passes removing those. The rule is one direction
only: a table may exist without a chart, a chart may not exist without a table.

Two constraints govern the implementation.

WeasyPrint renders a PNG embedded as a `data:` URI and renders
`data:image/svg+xml;utf8,` as well, but silently produces a blank page for
base64-encoded SVG — no error, no image. PNG is therefore the only path used
here.

The palette and typeface are taken from `markdown_pdf_service.REPORT_CSS`. A
chart set in matplotlib's defaults reads as clip art pasted into a typeset
document, which undoes the styling work rather than adding to it.

Each builder returns a markdown image line or an empty list. A caller passes
whatever it holds and gets nothing back when the data will not support a
figure — no placeholder, no empty axes.
"""

import base64
import io
import logging
import math
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    from matplotlib.ticker import FuncFormatter
    CHARTS_AVAILABLE = True
except Exception:  # pragma: no cover - matplotlib is a hard dependency in prod
    CHARTS_AVAILABLE = False

# Lifted from REPORT_CSS. Keep in step with it.
NAVY = "#12283F"
NAVY_DEEP = "#0B1A2B"
INK = "#14202E"
BODY = "#253546"
MUTED = "#64748B"
ACCENT = "#B45309"
RULE = "#D7DEE6"
RULE_LIGHT = "#EBEFF4"
TINT = "#F6F8FA"
NEG = "#A32020"

# A sequence for categorical fills: navy through to a light slate, with the
# amber accent reserved for the series a reader should look at first.
SERIES = ["#12283F", "#2C4257", "#4A6274", "#6D8296", "#9AA7B4", "#C3CEDA"]

FONT = ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"]

# The text column is 210mm less 18mm margins each side. Figures are drawn at
# that width so they align with the tables above and below them.
COLUMN_INCHES = (210 - 36) / 25.4
DPI = 200


def _style() -> None:
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": FONT,
        "font.size": 7.5,
        "text.color": BODY,
        "axes.edgecolor": RULE,
        "axes.labelcolor": MUTED,
        "axes.labelsize": 7,
        "axes.titlesize": 8.5,
        "axes.titleweight": "bold",
        "axes.titlecolor": INK,
        "axes.linewidth": 0.6,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": RULE_LIGHT,
        "grid.linewidth": 0.5,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "xtick.major.width": 0.5,
        "ytick.major.width": 0.5,
        "legend.frameon": False,
        "legend.fontsize": 7,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    })


def _emit(fig, alt: str, caption: str) -> List[str]:
    """A figure as a markdown image line plus its caption."""
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=DPI, bbox_inches="tight",
                facecolor="white", pad_inches=0.04)
    plt.close(fig)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return [f"![{alt}](data:image/png;base64,{encoded})", "",
            f"*{caption}*", ""]


def _axes(height: float = 2.3):
    _style()
    fig, ax = plt.subplots(figsize=(COLUMN_INCHES, height))
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color(RULE)
    ax.spines["bottom"].set_color(RULE)
    return fig, ax


def _money_axis(ax, values: Sequence[float]) -> str:
    """Scale a money axis to one unit and label it once, not per tick."""
    peak = max((abs(v) for v in values if v is not None), default=0)
    if peak >= 1e12:
        divisor, unit = 1e12, "$tn"
    elif peak >= 1e9:
        divisor, unit = 1e9, "$bn"
    elif peak >= 1e6:
        divisor, unit = 1e6, "$m"
    elif peak >= 1e3:
        divisor, unit = 1e3, "$k"
    else:
        divisor, unit = 1.0, "$"
    ax.yaxis.set_major_formatter(
        FuncFormatter(lambda v, _: f"{v / divisor:,.0f}"))
    return unit


def _safe(builder):
    """A chart must never take the report down with it."""
    def wrapper(*args, **kwargs):
        if not CHARTS_AVAILABLE:
            return []
        try:
            return builder(*args, **kwargs) or []
        except Exception as error:
            logger.warning("Chart %s failed: %s", builder.__name__, error)
            plt.close("all")
            return []
    wrapper.__name__ = builder.__name__
    return wrapper


# ---------------------------------------------------------------------------
# V-01  Revenue and margin trend
# ---------------------------------------------------------------------------

@_safe
def revenue_and_margin(income_statement: List[Dict[str, Any]]) -> List[str]:
    rows = [r for r in (income_statement or []) if r.get("Revenues")]
    rows = sorted(rows, key=lambda r: r.get("fiscal_year") or 0)[-6:]
    if len(rows) < 3:
        return []

    labels = [str(r.get("fiscal_year") or "") for r in rows]
    revenue = [float(r["Revenues"]) for r in rows]

    def margin(row, field):
        value = row.get(field)
        return (float(value) / float(row["Revenues"]) * 100
                if value is not None else None)

    fig, ax = _axes(2.5)
    unit = _money_axis(ax, revenue)
    ax.bar(labels, revenue, color=SERIES[0], width=0.58, label=f"Revenue ({unit})")
    ax.set_ylabel(f"Revenue ({unit})")
    ax.grid(axis="x", visible=False)

    margins = {
        "Gross": [margin(r, "GrossProfit") for r in rows],
        "Operating": [margin(r, "OperatingIncome") for r in rows],
        "Net": [margin(r, "NetIncome") for r in rows],
    }
    drawn = {k: v for k, v in margins.items() if any(x is not None for x in v)}
    if drawn:
        right = ax.twinx()
        right.grid(False)
        for side in ("top", "left"):
            right.spines[side].set_visible(False)
        right.spines["right"].set_color(RULE)
        for index, (name, series) in enumerate(drawn.items()):
            colour = ACCENT if name == "Gross" else SERIES[index + 2]
            right.plot(labels, series, color=colour, linewidth=1.3,
                       marker="o", markersize=2.6, label=f"{name} margin")
        right.set_ylabel("Margin (%)")
        right.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}%"))
        right.set_ylim(0, max(x for s in drawn.values()
                              for x in s if x is not None) * 1.35)
        handles = [Patch(facecolor=SERIES[0], label="Revenue")]
        lines, labels_ = right.get_legend_handles_labels()
        right.legend(handles + lines, ["Revenue"] + labels_,
                     loc="upper left", ncol=4, bbox_to_anchor=(0, 1.14))

    ax.set_title("Revenue and margin trend", loc="left", pad=16)
    return _emit(fig, "Revenue and margin by fiscal year",
                 "Revenue on the left axis, margins on the right. Both are "
                 "tabulated above; the figure adds the shape, not new data.")


# ---------------------------------------------------------------------------
# V-02  Capital allocation waterfall
# ---------------------------------------------------------------------------

@_safe
def capital_allocation(cash_flow: List[Dict[str, Any]]) -> List[str]:
    rows = sorted([r for r in (cash_flow or []) if r.get("OperatingCashFlow")],
                  key=lambda r: r.get("fiscal_year") or 0)
    if not rows:
        return []
    latest = rows[-1]

    steps = [("Operating\ncash flow", float(latest["OperatingCashFlow"]), "start")]
    for key, label in (("CapEx", "Capital\nexpenditure"),
                       ("StockRepurchases", "Buybacks"),
                       ("Dividends", "Dividends"),
                       ("DebtRepaid", "Debt repaid")):
        value = latest.get(key)
        if value:
            steps.append((label, -abs(float(value)), "out"))
    if len(steps) < 3:
        return []

    fig, ax = _axes(2.4)
    running = 0.0
    positions, heights, bottoms, colours = [], [], [], []
    for index, (label, value, kind) in enumerate(steps):
        positions.append(index)
        if kind == "start":
            bottoms.append(0.0)
            heights.append(value)
            colours.append(SERIES[0])
            running = value
        else:
            bottoms.append(running + value)
            heights.append(-value)
            colours.append(ACCENT)
            running += value

    positions.append(len(steps))
    bottoms.append(0.0)
    heights.append(running)
    colours.append(SERIES[2] if running >= 0 else NEG)
    labels = [s[0] for s in steps] + ["Retained"]

    unit = _money_axis(ax, [abs(h) + abs(b) for h, b in zip(heights, bottoms)])
    ax.bar(positions, heights, bottom=bottoms, color=colours, width=0.6)
    ax.set_xticks(positions)
    ax.set_xticklabels(labels)
    ax.set_ylabel(f"Cash ({unit})")
    ax.grid(axis="x", visible=False)
    ax.axhline(0, color=RULE, linewidth=0.6)
    year = latest.get("fiscal_year")
    ax.set_title(f"Where operating cash went{f', FY{year}' if year else ''}",
                 loc="left", pad=8)
    return _emit(fig, "Capital allocation waterfall",
                 "Operating cash flow less each claim on it. The final bar is "
                 "what remained after the uses shown, before working capital "
                 "and investment flows.")


# ---------------------------------------------------------------------------
# V-03  Segment and geographic composition
# ---------------------------------------------------------------------------

@_safe
def composition(segments: Dict[str, Any]) -> List[str]:
    panels = []
    for key, title in (("segments", "By reportable segment"),
                       ("geographic", "By region"),
                       ("markets", "By market")):
        entries = (segments or {}).get(key) or []

        # A member listed under another member's `parent_of` is a component of
        # it. Charting both makes the total read as double what was reported.
        children = {name for entry in entries
                    for name in (entry.get("parent_of") or [])}
        rows = [(entry.get("name"), float(entry.get("current") or 0))
                for entry in entries
                if (entry.get("current") or 0) > 0
                and entry.get("name") not in children]
        if len(rows) >= 2:
            panels.append((title, sorted(rows, key=lambda r: -r[1])[:8]))
    if not panels:
        return []

    _style()
    fig, axes = plt.subplots(
        len(panels), 1, figsize=(COLUMN_INCHES, 1.1 + 0.34 * sum(
            len(rows) for _, rows in panels)))
    if len(panels) == 1:
        axes = [axes]

    for ax, (title, rows) in zip(axes, panels):
        names = [r[0] for r in rows][::-1]
        values = [r[1] for r in rows][::-1]
        total = sum(values) or 1
        ax.barh(names, values, color=SERIES[0], height=0.6)
        for index, value in enumerate(values):
            ax.text(value, index, f"  {value / total * 100:.1f}%",
                    va="center", fontsize=6.8, color=MUTED)
        ax.set_title(title, loc="left", pad=6)
        ax.grid(axis="y", visible=False)
        ax.set_xlim(0, max(values) * 1.22)
        ax.set_xticks([])
        for side in ("top", "right", "bottom"):
            ax.spines[side].set_visible(False)
        ax.spines["left"].set_color(RULE)

    fig.tight_layout(h_pad=1.4)
    return _emit(fig, "Revenue composition",
                 "Share of the disclosed total in each breakdown. Percentages "
                 "are of what the issuer reports, which is not always the "
                 "consolidated figure.")


# ---------------------------------------------------------------------------
# V-04  DCF sensitivity
# ---------------------------------------------------------------------------

@_safe
def dcf_sensitivity(waccs: Sequence[float], growths: Sequence[float],
                    matrix: Sequence[Sequence[Optional[float]]],
                    base_wacc: Optional[float] = None,
                    base_growth: Optional[float] = None,
                    current: Optional[float] = None) -> List[str]:
    """The grid the valuation section has already tabulated, as a heat map.

    The caller passes the values it printed rather than recomputing them, so
    the chart cannot drift from the table beside it.
    """
    if not matrix or not waccs or not growths:
        return []
    if any(any(v is None for v in row) for row in matrix):
        return []
    data = [[float(v) for v in row] for row in matrix]
    if any(len(row) != len(growths) for row in data):
        return []

    flat = [v for row in data for v in row]
    low, high = min(flat), max(flat)

    fig, ax = _axes(0.9 + 0.26 * len(waccs))
    ax.grid(False)
    image = ax.imshow(data, cmap="BuPu", aspect="auto")

    ax.set_xticks(range(len(growths)))
    ax.set_xticklabels([f"{float(g) * 100:.2f}%" for g in growths])
    ax.set_yticks(range(len(waccs)))
    ax.set_yticklabels([f"{float(w) * 100:.2f}%" for w in waccs])
    ax.set_xlabel("Terminal growth")
    ax.set_ylabel("WACC")
    for side in ("top", "right"):
        ax.spines[side].set_visible(True)
        ax.spines[side].set_color(RULE)

    span = (high - low) or 1
    above = 0
    for i, row in enumerate(data):
        for j, value in enumerate(row):
            light = (value - low) / span > 0.55
            is_base = (base_wacc is not None
                       and abs(float(waccs[i]) - base_wacc) < 1e-9
                       and abs(float(growths[j]) - (base_growth or 0)) < 1e-9)
            ax.text(j, i, f"{value:,.0f}", ha="center", va="center",
                    fontsize=6.6, color="white" if light else INK,
                    fontweight="bold" if is_base else "normal")
            if is_base:
                ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1,
                                           fill=False, edgecolor=ACCENT,
                                           linewidth=1.4))
            if current and value > float(current):
                above += 1

    caption = ("Implied value per share across the discount rate and terminal "
               "growth assumptions; the outlined cell is the base case.")
    if current:
        caption += (f" At the ${float(current):,.2f} market price, "
                    f"{above} of {len(flat)} cells imply upside.")
    ax.set_title("Valuation sensitivity", loc="left", pad=8)
    bar = fig.colorbar(image, ax=ax, fraction=0.025, pad=0.02)
    bar.outline.set_visible(False)
    bar.ax.tick_params(labelsize=6, color=RULE)
    if current:
        bar.ax.axhline(float(current), color=ACCENT, linewidth=1.1)
    return _emit(fig, "DCF sensitivity to WACC and terminal growth", caption)


# ---------------------------------------------------------------------------
# V-05  Commitment maturity ladder
# ---------------------------------------------------------------------------

@_safe
def commitments(notes: Dict[str, Any], operating_cash_flow: Optional[float] = None
                ) -> List[str]:
    merged: Dict[str, float] = {}
    for entry in (notes or {}).get("commitments") or []:
        kind = entry.get("kind")
        amount = entry.get("amount")
        if kind and amount:
            merged[kind] = merged.get(kind, 0.0) + float(amount)
    if len(merged) < 2:
        return []
    rows = sorted(merged.items(), key=lambda kv: kv[1])

    fig, ax = _axes(0.9 + 0.3 * len(rows))
    names = [r[0] for r in rows]
    values = [r[1] for r in rows]
    ax.barh(names, values, color=SERIES[1], height=0.58)

    peak = max(values)
    divisor, unit = ((1e9, "bn") if peak >= 1e9 else (1e6, "m"))
    for index, value in enumerate(values):
        text = f"  ${value / divisor:,.1f}{unit}"
        if operating_cash_flow:
            text += f"  ({value / float(operating_cash_flow):.2f}x OCF)"
        ax.text(value, index, text, va="center", fontsize=6.8, color=MUTED)
    ax.set_xticks([])
    ax.set_xlim(0, peak * 1.42)
    ax.grid(visible=False)
    for side in ("top", "right", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_title("Contractual commitments by type", loc="left", pad=8)
    caption = ("Amounts the issuer has contracted to pay but has not yet "
               "recognised.")
    if operating_cash_flow:
        caption += (" The multiple is against one year of operating cash flow, "
                    "which is the scale that makes an obligation legible.")
    return _emit(fig, "Contractual commitments", caption)


# ---------------------------------------------------------------------------
# V-06  Insider disposals by month
# ---------------------------------------------------------------------------

@_safe
def insider_disposals(insider: Dict[str, Any]) -> List[str]:
    buckets: Dict[str, Dict[str, float]] = {}
    for row in (insider or {}).get("transactions") or []:
        if row.get("acquired_disposed") != "D" or not row.get("value"):
            continue
        date = str(row.get("date") or "")[:7]
        if len(date) != 7:
            continue
        slot = buckets.setdefault(date, {"plan": 0.0, "discretionary": 0.0})
        key = "plan" if row.get("is_10b5_1") else "discretionary"
        slot[key] += float(row["value"])
    if len(buckets) < 4:
        return []

    months = sorted(buckets)[-30:]
    plan = [buckets[m]["plan"] for m in months]
    discretionary = [buckets[m]["discretionary"] for m in months]

    fig, ax = _axes(2.3)
    unit = _money_axis(ax, [p + d for p, d in zip(plan, discretionary)])
    ax.bar(months, plan, color=SERIES[2], width=0.7, label="10b5-1 plan")
    ax.bar(months, discretionary, bottom=plan, color=ACCENT, width=0.7,
           label="Discretionary")
    ax.set_ylabel(f"Disposed ({unit})")
    ax.grid(axis="x", visible=False)
    step = max(1, len(months) // 12)
    ax.set_xticks(range(0, len(months), step))
    ax.set_xticklabels([months[i] for i in range(0, len(months), step)],
                       rotation=45, ha="right")
    ax.legend(loc="upper left", ncol=2, bbox_to_anchor=(0, 1.16))
    ax.set_title("Insider disposals by month", loc="left", pad=16)
    return _emit(fig, "Insider disposals split by trading plan",
                 "Sales under a 10b5-1 plan are scheduled in advance; "
                 "discretionary sales are not, which is why the split matters "
                 "more than the total.")


# ---------------------------------------------------------------------------
# V-07  Filing cadence
# ---------------------------------------------------------------------------

@_safe
def filing_cadence(timeline: Dict[str, Any]) -> List[str]:
    events = (timeline or {}).get("events") or []
    grid: Dict[str, Dict[str, int]] = {}
    for event in events:
        period = str(event.get("date") or "")[:7]
        form = (event.get("form_type") or "").upper()[:10]
        if len(period) != 7 or not form:
            continue
        grid.setdefault(period, {})
        grid[period][form] = grid[period].get(form, 0) + 1
    if len(grid) < 4:
        return []

    periods = sorted(grid)[-30:]
    totals: Dict[str, int] = {}
    for period in periods:
        for form, count in grid[period].items():
            totals[form] = totals.get(form, 0) + count
    forms = [f for f, _ in sorted(totals.items(), key=lambda kv: -kv[1])[:5]]

    fig, ax = _axes(2.2)
    bottom = [0] * len(periods)
    for index, form in enumerate(forms):
        values = [grid[p].get(form, 0) for p in periods]
        ax.bar(periods, values, bottom=bottom, width=0.7,
               color=SERIES[index % len(SERIES)], label=form)
        bottom = [b + v for b, v in zip(bottom, values)]

    ax.set_ylabel("Filings")
    ax.grid(axis="x", visible=False)
    step = max(1, len(periods) // 12)
    ax.set_xticks(range(0, len(periods), step))
    ax.set_xticklabels([periods[i] for i in range(0, len(periods), step)],
                       rotation=45, ha="right")
    ax.legend(loc="upper left", ncol=len(forms), bbox_to_anchor=(0, 1.18))
    ax.set_title("Filing cadence by form type", loc="left", pad=18)
    return _emit(fig, "Filings per month by form type",
                 "A change in filing rhythm is often the first visible sign of "
                 "a change in circumstances.")


# ---------------------------------------------------------------------------
# V-08  Institutional concentration
# ---------------------------------------------------------------------------

@_safe
def institutional_concentration(holdings: Dict[str, Any]) -> List[str]:
    holders = [(h.get("institution"), float(h.get("value") or 0))
               for h in (holdings or {}).get("holders") or []
               if (h.get("value") or 0) > 0]
    if len(holders) < 3:
        return []
    holders = sorted(holders, key=lambda h: -h[1])[:12][::-1]

    fig, ax = _axes(0.9 + 0.24 * len(holders))
    names = [h[0] for h in holders]
    values = [h[1] for h in holders]
    bars = ax.barh(names, values, color=SERIES[0], height=0.62)
    if holders:
        bars[-1].set_color(ACCENT)

    peak = max(values)
    unit = "bn" if peak >= 1e9 else "m"
    divisor = 1e9 if peak >= 1e9 else 1e6
    for index, value in enumerate(values):
        ax.text(value, index, f"  ${value / divisor:,.1f}{unit}",
                va="center", fontsize=6.8, color=MUTED)
    ax.set_xticks([])
    ax.set_xlim(0, peak * 1.22)
    ax.grid(visible=False)
    for side in ("top", "right", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_title("Reported institutional positions", loc="left", pad=8)
    return _emit(fig, "Institutional positions by reported value",
                 "Positions from the largest 13F filers polled. This is a "
                 "floor on institutional ownership, not a census.")


# ---------------------------------------------------------------------------
# V-10  Board interlock network
# ---------------------------------------------------------------------------

@_safe
def interlock_network(interlocks: Dict[str, Any], entity_name: str,
                      name_formatter=None) -> List[str]:
    people = [p for p in (interlocks or {}).get("people") or []
              if p.get("current_seat_count")]
    if len(people) < 2:
        return []

    format_name = name_formatter or (lambda n: n)
    edges = []
    for person in people[:10]:
        for seat in person["other_seats"]:
            if seat.get("current"):
                edges.append((format_name(person["name"]),
                              seat.get("ticker") or seat["issuer"]))
    if len(edges) < 2:
        return []

    persons = sorted({e[0] for e in edges})
    issuers = sorted({e[1] for e in edges})

    _style()
    height = 0.9 + 0.30 * max(len(persons), len(issuers))
    fig, ax = plt.subplots(figsize=(COLUMN_INCHES, height))
    ax.axis("off")

    def positions(items, x):
        if len(items) == 1:
            return {items[0]: (x, 0.5)}
        return {item: (x, 1 - index / (len(items) - 1))
                for index, item in enumerate(items)}

    left = positions(persons, 0.06)
    right = positions(issuers, 0.94)

    for person, issuer in edges:
        x1, y1 = left[person]
        x2, y2 = right[issuer]
        ax.annotate("", xy=(x2 - 0.015, y2), xytext=(x1 + 0.015, y1),
                    arrowprops=dict(arrowstyle="-", color=RULE,
                                    linewidth=0.7, connectionstyle="arc3,rad=0.08"))

    for person, (x, y) in left.items():
        ax.plot(x, y, "o", markersize=4, color=NAVY)
        ax.text(x - 0.02, y, person, ha="right", va="center", fontsize=7,
                color=INK)
    for issuer, (x, y) in right.items():
        ax.plot(x, y, "s", markersize=4, color=ACCENT)
        ax.text(x + 0.02, y, issuer, ha="left", va="center", fontsize=7,
                color=BODY)

    ax.set_xlim(-0.42, 1.42)
    ax.set_ylim(-0.12, 1.12)
    ax.set_title(f"Where {entity_name}'s insiders also serve", loc="left",
                 pad=6, fontsize=8.5, color=INK, fontweight="bold")
    return _emit(fig, "Board interlock network",
                 "Current outside seats only. A seat counts as current where "
                 "the person has filed at that issuer within two years.")


# ---------------------------------------------------------------------------
# V-12  Subsidiaries by jurisdiction
# ---------------------------------------------------------------------------

@_safe
def subsidiary_jurisdictions(subsidiaries: Dict[str, Any]) -> List[str]:
    counts = (subsidiaries or {}).get("by_jurisdiction") or {}
    rows = sorted(((k, v) for k, v in counts.items() if v),
                  key=lambda kv: -kv[1])[:14]
    # Three jurisdictions holding one entity each is a list, not a
    # distribution. Charting it implies a structure the exhibit does not show.
    if len(rows) < 3 or sum(v for _, v in rows) < 8:
        return []

    holding = {"cayman islands", "bermuda", "luxembourg", "ireland",
               "netherlands", "british virgin islands", "jersey", "guernsey",
               "mauritius", "curacao", "barbados", "panama"}
    rows = rows[::-1]

    fig, ax = _axes(0.9 + 0.24 * len(rows))
    names = [r[0] for r in rows]
    values = [r[1] for r in rows]
    colours = [ACCENT if n.lower() in holding else SERIES[0] for n in names]
    ax.barh(names, values, color=colours, height=0.62)
    for index, value in enumerate(values):
        ax.text(value, index, f"  {value}", va="center", fontsize=6.8,
                color=MUTED)
    ax.set_xticks([])
    ax.set_xlim(0, max(values) * 1.18)
    ax.grid(visible=False)
    for side in ("top", "right", "bottom"):
        ax.spines[side].set_visible(False)
    ax.set_title("Subsidiaries by jurisdiction of organisation", loc="left",
                 pad=8)
    if any(n.lower() in holding for n in names):
        ax.legend(handles=[Patch(facecolor=ACCENT,
                                 label="Holding and financing jurisdictions")],
                  loc="lower right", fontsize=6.6)
    return _emit(fig, "Subsidiary count by jurisdiction",
                 "Where each entity is organised, per Exhibit 21. It states "
                 "nothing about where the entity operates.")


# ---------------------------------------------------------------------------
# V-13  Private portfolio rollforward
# ---------------------------------------------------------------------------

@_safe
def portfolio_rollforward(investments: List[Dict[str, Any]]) -> List[str]:
    rollforward = next((i for i in (investments or [])
                        if i.get("kind") == "portfolio_rollforward"), None)
    if not rollforward:
        return []
    opening = rollforward.get("opening_balance")
    closing = rollforward.get("closing_balance")
    if opening is None or closing is None:
        return []

    movements = [("Opening", float(opening), "start")]
    for field, label in (("net_additions", "Net additions"),
                         ("unrealized_gains", "Unrealised gains"),
                         ("impairments", "Impairments"),
                         ("sales", "Sales and\nreclassifications")):
        value = rollforward.get(field)
        if value:
            movements.append((label, float(value), "step"))
    movements.append(("Closing", float(closing), "end"))
    if len(movements) < 3:
        return []

    fig, ax = _axes(2.4)
    running, positions, heights, bottoms, colours = 0.0, [], [], [], []
    for index, (label, value, kind) in enumerate(movements):
        positions.append(index)
        if kind == "start":
            bottoms.append(0.0)
            heights.append(value)
            colours.append(SERIES[2])
            running = value
        elif kind == "end":
            bottoms.append(0.0)
            heights.append(value)
            colours.append(SERIES[0])
        else:
            bottoms.append(running if value >= 0 else running + value)
            heights.append(abs(value))
            colours.append(ACCENT if value >= 0 else NEG)
            running += value

    unit = _money_axis(ax, [abs(h) + abs(b) for h, b in zip(heights, bottoms)])
    ax.bar(positions, heights, bottom=bottoms, color=colours, width=0.6)
    ax.set_xticks(positions)
    ax.set_xticklabels([m[0] for m in movements])
    ax.set_ylabel(f"Carrying value ({unit})")
    ax.grid(axis="x", visible=False)
    ax.set_title("Private company holdings, movement in the year", loc="left",
                 pad=8)
    return _emit(fig, "Non-marketable equity rollforward",
                 "Amber is capital deployed and value added; the closing bar "
                 "is the carrying value the note reports.")


# ---------------------------------------------------------------------------
# V-11  Insider disposals overlaid on price history
# ---------------------------------------------------------------------------

@_safe
def insider_on_price(insider: Dict[str, Any], price_history: Dict[str, Any]
                     ) -> List[str]:
    """Discretionary and plan sales against the daily close — needs D-01 bars."""
    bars = (price_history or {}).get("bars") or []
    if len(bars) < 40:
        return []

    sales = [t for t in (insider or {}).get("transactions") or []
             if t.get("acquired_disposed") == "D" and t.get("value")
             and t.get("date")]
    if len(sales) < 3:
        return []

    from datetime import datetime as _dt
    closes = []
    for bar in bars:
        try:
            closes.append((_dt.strptime(bar["date"][:10], "%Y-%m-%d"),
                           float(bar["close"])))
        except (ValueError, TypeError, KeyError):
            continue
    if len(closes) < 40:
        return []
    closes.sort()
    start = closes[0][0]

    plan_pts, disc_pts = [], []
    for row in sales:
        try:
            day = _dt.strptime(str(row["date"])[:10], "%Y-%m-%d")
        except ValueError:
            continue
        if day < start:
            continue
        point = (day, float(row["value"]))
        (plan_pts if row.get("is_10b5_1") else disc_pts).append(point)

    fig, ax = _axes(2.6)
    ax.plot([d for d, _ in closes], [c for _, c in closes],
            color=SERIES[0], linewidth=1.1, label="Close")
    ax.set_ylabel("Price")
    ax.grid(axis="x", visible=False)

    right = ax.twinx()
    right.grid(False)
    for side in ("top", "left"):
        right.spines[side].set_visible(False)
    if plan_pts:
        right.scatter([d for d, _ in plan_pts], [v for _, v in plan_pts],
                      s=14, color=SERIES[2], alpha=0.85, label="10b5-1",
                      zorder=3)
    if disc_pts:
        right.scatter([d for d, _ in disc_pts], [v for _, v in disc_pts],
                      s=18, color=ACCENT, alpha=0.9, label="Discretionary",
                      zorder=4)
    unit = _money_axis(right, [v for _, v in plan_pts + disc_pts] or [1])
    right.set_ylabel(f"Disposal ({unit})")

    handles, labels_ = ax.get_legend_handles_labels()
    h2, l2 = right.get_legend_handles_labels()
    ax.legend(handles + h2, labels_ + l2, loc="upper left", ncol=3,
              bbox_to_anchor=(0, 1.14))
    ax.set_title("Insider disposals against the share price", loc="left", pad=16)
    import matplotlib.dates as mdates
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=max(1, len(closes) // 200)))
    fig.autofmt_xdate(rotation=45, ha="right")
    return _emit(fig, "Insider disposals overlaid on price",
                 "Markers are individual Form 4 disposals sized by value. "
                 "Discretionary sales are amber; 10b5-1 plan sales are slate. "
                 f"Price from {(price_history or {}).get('source') or 'market data'}.")


# ---------------------------------------------------------------------------
# V-09  Federal obligations by agency
# ---------------------------------------------------------------------------

@_safe
def federal_obligations(contracts: Dict[str, Any]) -> List[str]:
    agencies = [(a.get("agency") or "Not stated", float(a.get("amount") or 0))
                for a in (contracts or {}).get("agency_breakdown") or []]
    agencies = [a for a in agencies if a[1] > 0]
    years = [(str(y.get("year")), float(y.get("amount") or 0))
             for y in (contracts or {}).get("year_breakdown") or []]
    years = sorted([y for y in years if y[1] > 0])
    if len(agencies) < 2 and len(years) < 3:
        return []

    _style()
    panels = int(len(agencies) >= 2) + int(len(years) >= 3)
    height = 1.1 + (0.26 * min(len(agencies), 10) if agencies else 0) + \
        (1.5 if len(years) >= 3 else 0)
    fig, axes = plt.subplots(panels, 1, figsize=(COLUMN_INCHES, height))
    axes = [axes] if panels == 1 else list(axes)
    total = sum(a[1] for a in agencies) or 1

    if len(agencies) >= 2:
        ax = axes.pop(0)
        rows = sorted(agencies, key=lambda kv: kv[1])[-10:]
        names = [r[0][:46] for r in rows]
        values = [r[1] for r in rows]
        ax.barh(names, values, color=SERIES[1], height=0.58)
        for index, value in enumerate(values):
            ax.text(value, index, f"  {value / total * 100:.1f}%", va="center",
                    fontsize=6.8, color=MUTED)
        ax.set_xticks([])
        ax.set_xlim(0, max(values) * 1.2)
        ax.grid(visible=False)
        for side in ("top", "right", "bottom"):
            ax.spines[side].set_visible(False)
        ax.set_title("Obligations by awarding agency", loc="left", pad=6)

    if len(years) >= 3:
        ax = axes.pop(0)
        ax.bar([y[0] for y in years], [y[1] for y in years], color=SERIES[0],
               width=0.6)
        unit = _money_axis(ax, [y[1] for y in years])
        ax.set_ylabel(f"Obligated ({unit})")
        ax.grid(axis="x", visible=False)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.set_title("Obligations by year awarded", loc="left", pad=6)

    fig.tight_layout(h_pad=1.6)
    return _emit(fig, "Federal obligations by agency and year",
                 "Awards where the issuer or a named subsidiary is the prime "
                 "recipient. Gaps between years are years with no award, not "
                 "missing data.")
