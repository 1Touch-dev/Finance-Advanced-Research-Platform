"""
Multi-Perspective Investment Analysis Service
────────────────────────────────────────────────────────────────────────────
Generates investment views from multiple analyst perspectives:
  - Value Investor (Buffett/Graham style)
  - Growth Investor (momentum, TAM expansion)
  - Income/Dividend Investor
  - Risk/Contrarian Analyst
  - Macro/Geopolitical Lens

Uses only data already collected in the pipeline — no external API calls.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def generate_multi_perspective_analysis(
    entity_name: str,
    ticker: str,
    financial_data: Dict[str, Any] = None,
    valuation: Dict[str, Any] = None,
    insider_data: Dict[str, Any] = None,
    peer_comparison: Dict[str, Any] = None,
    risk_register: Dict[str, Any] = None,
    news_data: Dict[str, Any] = None,
    lobbying_data: Dict[str, Any] = None,
    contracts_data: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Generate investment views from multiple analyst perspectives.
    All analysis is derived from already-collected data.
    """
    result = {
        "perspectives": [],
        "consensus_view": "",
        "key_debates": [],
        "generated_at": datetime.utcnow().isoformat(),
    }

    financial = financial_data or {}
    annual = financial.get("financial_statements", {}).get("annual", [])
    latest = annual[0] if annual else {}

    # Extract key metrics
    revenue = latest.get("revenue", 0)
    revenue_growth = latest.get("revenue_growth_pct")
    net_margin = latest.get("net_margin_pct")
    gross_margin = latest.get("gross_margin_pct")

    val_data = valuation or {}
    dcf_price = val_data.get("dcf_result", {}).get("price_per_share")
    market_price = val_data.get("market_data", {}).get("price")

    insider = insider_data or {}
    total_sold = insider.get("total_disposed_value", 0)
    total_bought = insider.get("total_acquired_value", 0)

    peers = peer_comparison or {}
    risk = risk_register or {}

    # ── VALUE INVESTOR PERSPECTIVE ────────────────────────────────────────
    value_view = _value_investor_view(
        entity_name, revenue, revenue_growth, net_margin, gross_margin,
        dcf_price, market_price, total_sold, total_bought, annual
    )
    result["perspectives"].append(value_view)

    # ── GROWTH INVESTOR PERSPECTIVE ───────────────────────────────────────
    growth_view = _growth_investor_view(
        entity_name, revenue, revenue_growth, gross_margin,
        market_price, dcf_price, annual, peers
    )
    result["perspectives"].append(growth_view)

    # ── RISK / CONTRARIAN PERSPECTIVE ─────────────────────────────────────
    risk_view = _risk_contrarian_view(
        entity_name, total_sold, total_bought, revenue_growth,
        market_price, dcf_price, risk, insider, lobbying_data, news_data
    )
    result["perspectives"].append(risk_view)

    # ── MACRO / GEOPOLITICAL PERSPECTIVE ──────────────────────────────────
    macro_view = _macro_geopolitical_view(
        entity_name, contracts_data, lobbying_data, news_data,
        revenue, annual
    )
    result["perspectives"].append(macro_view)

    # ── INCOME INVESTOR PERSPECTIVE ───────────────────────────────────────
    income_view = _income_investor_view(entity_name, annual, market_price)
    result["perspectives"].append(income_view)

    # Generate consensus and key debates
    result["consensus_view"] = _derive_consensus(result["perspectives"])
    result["key_debates"] = _identify_key_debates(result["perspectives"])

    return result


def _value_investor_view(name, revenue, rev_growth, net_margin, gross_margin,
                         dcf_price, market_price, sold, bought, annual) -> Dict:
    """Benjamin Graham / Warren Buffett perspective."""
    signals = []
    stance = "NEUTRAL"

    if dcf_price and market_price:
        premium = ((market_price - dcf_price) / dcf_price) * 100
        if premium > 50:
            signals.append(f"Trading {premium:.0f}% above intrinsic value — extreme premium")
            stance = "AVOID"
        elif premium > 20:
            signals.append(f"Trading {premium:.0f}% above intrinsic value — no margin of safety")
            stance = "CAUTIOUS"
        elif premium < -20:
            signals.append(f"Trading {abs(premium):.0f}% below intrinsic value — potential opportunity")
            stance = "INTERESTED"
        else:
            signals.append("Trading near fair value")

    if net_margin and net_margin > 25:
        signals.append(f"Exceptional net margin ({net_margin:.1f}%) suggests durable competitive advantage")
    elif net_margin and net_margin > 15:
        signals.append(f"Healthy margins ({net_margin:.1f}%) but not a wide moat signal alone")

    if sold > 0 and bought == 0:
        signals.append(f"Insiders are pure sellers (${sold/1e9:.1f}B disposed) — not a confidence signal")

    # Check consistency of margins
    if len(annual) >= 3:
        margins = [y.get("net_margin_pct", 0) for y in annual[:3] if y.get("net_margin_pct")]
        if margins and min(margins) > 0.8 * max(margins):
            signals.append("Margins stable across multiple years — moat durability signal")

    return {
        "name": "Value Investor",
        "style": "Graham / Buffett",
        "stance": stance,
        "signals": signals,
        "thesis": _build_value_thesis(name, stance, signals),
    }


def _growth_investor_view(name, revenue, rev_growth, gross_margin,
                          market_price, dcf_price, annual, peers) -> Dict:
    """Growth / momentum investor perspective."""
    signals = []
    stance = "NEUTRAL"

    if rev_growth and rev_growth > 40:
        signals.append(f"Revenue growing {rev_growth:.0f}% — hypergrowth territory")
        stance = "BULLISH"
    elif rev_growth and rev_growth > 20:
        signals.append(f"Revenue growing {rev_growth:.0f}% — strong growth")
        stance = "CONSTRUCTIVE"
    elif rev_growth and rev_growth > 0:
        signals.append(f"Revenue growing {rev_growth:.0f}% — decelerating")
        stance = "CAUTIOUS"

    # Check growth deceleration
    if len(annual) >= 2:
        prev_growth = annual[1].get("revenue_growth_pct")
        if prev_growth and rev_growth and prev_growth > rev_growth:
            decel = prev_growth - rev_growth
            signals.append(f"Growth decelerating {decel:.0f}pp vs prior year — key risk for multiple")

    if gross_margin and gross_margin > 70:
        signals.append(f"Gross margin {gross_margin:.1f}% — platform economics / network effects")
    elif gross_margin and gross_margin > 50:
        signals.append(f"Gross margin {gross_margin:.1f}% — good but not best-in-class")

    # TAM expansion signal from revenue scale
    if revenue and revenue > 50000:
        signals.append("Revenue >$50B — TAM expansion becomes the investment question, not product-market fit")

    return {
        "name": "Growth Investor",
        "style": "ARK / Baillie Gifford",
        "stance": stance,
        "signals": signals,
        "thesis": _build_growth_thesis(name, stance, signals, rev_growth),
    }


def _risk_contrarian_view(name, sold, bought, rev_growth, market_price,
                          dcf_price, risk, insider, lobbying, news) -> Dict:
    """Risk analyst / short-seller perspective."""
    signals = []
    stance = "NEUTRAL"
    red_flags = 0

    if sold > 1e9 and bought == 0:
        signals.append(f"${sold/1e9:.1f}B of insider selling with zero purchases — classic divergence")
        red_flags += 1

    if dcf_price and market_price and market_price > 2 * dcf_price:
        signals.append("Trading >2x DCF value — sentiment-driven, vulnerable to narrative shift")
        red_flags += 1

    risk_data = risk.get("risks", []) if isinstance(risk, dict) else []
    high_risks = [r for r in risk_data if r.get("severity") in ("HIGH", "CRITICAL")]
    if high_risks:
        signals.append(f"{len(high_risks)} high/critical risks identified in the register")
        red_flags += 1

    if rev_growth and rev_growth > 50:
        signals.append("Hypergrowth creates expectation risk — any miss triggers severe repricing")

    lobbying_total = 0
    if isinstance(lobbying, dict):
        lobbying_total = lobbying.get("total_disclosed_spend", 0)
        if lobbying_total > 5e6:
            signals.append(f"${lobbying_total/1e6:.0f}M in lobbying — regulatory battle or defensive moat maintenance")

    if red_flags >= 2:
        stance = "BEARISH"
    elif red_flags >= 1:
        stance = "CAUTIOUS"

    return {
        "name": "Risk / Contrarian Analyst",
        "style": "Short-seller research",
        "stance": stance,
        "signals": signals,
        "thesis": _build_risk_thesis(name, stance, signals, red_flags),
    }


def _macro_geopolitical_view(name, contracts, lobbying, news, revenue, annual) -> Dict:
    """Macro / geopolitical lens."""
    signals = []
    stance = "NEUTRAL"

    # Government exposure
    contract_value = 0
    if isinstance(contracts, dict):
        contract_value = contracts.get("total_obligations", 0)
        if contract_value > 1e8:
            signals.append(f"${contract_value/1e6:.0f}M in federal contracts — significant government exposure")
        agency_count = len(contracts.get("by_agency", []))
        if agency_count >= 3:
            signals.append(f"Spread across {agency_count} agencies — diversified government revenue")

    lobbying_total = 0
    if isinstance(lobbying, dict):
        lobbying_total = lobbying.get("total_disclosed_spend", 0)
        if lobbying_total > 0:
            signals.append(f"${lobbying_total/1e6:.1f}M lobbying spend — active regulatory participant")

    # International exposure from revenue data
    if len(annual) > 0:
        # Check if company has high international revenue
        pass  # This would come from segment data

    # Trade war / export control signals from news
    if isinstance(news, dict):
        articles = news.get("articles", [])
        policy_articles = [a for a in articles if "policy" in (a.get("themes") or "")]
        if policy_articles:
            signals.append(f"{len(policy_articles)} policy-related news articles — regulatory sensitivity")

    if contract_value > 1e8 or lobbying_total > 5e6:
        stance = "GOVERNMENT-LINKED"
    elif any("export" in s.lower() or "trade" in s.lower() for s in signals):
        stance = "GEOPOLITICALLY EXPOSED"

    return {
        "name": "Macro / Geopolitical Analyst",
        "style": "Geopolitical risk",
        "stance": stance,
        "signals": signals,
        "thesis": _build_macro_thesis(name, stance, signals),
    }


def _income_investor_view(name, annual, market_price) -> Dict:
    """Income / dividend investor perspective."""
    signals = []
    stance = "NOT APPLICABLE"

    if annual:
        latest = annual[0]
        # Check for dividends
        div_per_share = latest.get("dividends_per_share", 0)
        if div_per_share and market_price:
            div_yield = (div_per_share / market_price) * 100
            signals.append(f"Dividend yield: {div_yield:.2f}%")
            if div_yield > 3:
                stance = "ATTRACTIVE"
            elif div_yield > 1.5:
                stance = "ADEQUATE"
            else:
                stance = "INSUFFICIENT YIELD"
        else:
            signals.append("No dividend paid — not a yield vehicle")
            stance = "NOT A YIELD PLAY"

        # Check buyback activity
        # This would come from cash flow data
        net_income = latest.get("net_income", 0)
        if net_income > 50000:
            signals.append("Substantial earnings capacity — could support large buyback programs")

    return {
        "name": "Income / Dividend Investor",
        "style": "Yield-focused",
        "stance": stance,
        "signals": signals,
        "thesis": f"{name} is evaluated as a yield vehicle. " + (" ".join(signals) if signals else "Insufficient data."),
    }


def _build_value_thesis(name, stance, signals) -> str:
    if stance == "AVOID":
        return (f"{name} commands a significant premium to intrinsic value. "
                "A value discipline requires either a lower entry point or evidence "
                "that the moat is wider than current modelling assumes.")
    elif stance == "INTERESTED":
        return (f"{name} trades below estimated fair value, warranting deeper research. "
                "The margin of safety exists on paper; the question is whether "
                "the business quality justifies holding through a potential drawdown.")
    return (f"{name} trades near estimated fair value. "
            "Neither a bargain nor overpriced by classical value metrics.")


def _build_growth_thesis(name, stance, signals, rev_growth) -> str:
    if stance == "BULLISH":
        return (f"{name} is in hypergrowth ({rev_growth:.0f}% revenue growth). "
                "The growth investor's question is not price but durability: "
                "can this rate sustain for 3-5 more years, and what is the TAM ceiling?")
    elif stance == "CAUTIOUS":
        return (f"{name}'s growth is decelerating. Growth investors must decide "
                "whether deceleration is structural (TAM saturation) or cyclical "
                "(digestion before the next leg). Multiple compression is the risk.")
    return f"{name} shows moderate growth. Position sizing matters more than conviction here."


def _build_risk_thesis(name, stance, signals, red_flags) -> str:
    if stance == "BEARISH":
        return (f"{name} presents {red_flags} red flags that short-seller research "
                "would investigate further. The combination of insider selling, "
                "valuation extremes, and identified risks suggests the stock is "
                "priced for perfection with imperfect conditions.")
    return (f"{name} does not present an obvious short thesis, but the risk "
            "register warrants monitoring.")


def _build_macro_thesis(name, stance, signals) -> str:
    if "GOVERNMENT" in stance:
        return (f"{name} has significant government linkage through contracts and lobbying. "
                "Policy changes, budget cycles, and administration shifts create "
                "non-market risk that financial models do not capture. The position "
                "is partly a bet on political stability.")
    return (f"{name}'s macro exposure is manageable. Standard geopolitical monitoring applies.")


def _derive_consensus(perspectives: List[Dict]) -> str:
    stances = [p["stance"] for p in perspectives]
    bullish = sum(1 for s in stances if s in ("BULLISH", "INTERESTED", "ATTRACTIVE"))
    bearish = sum(1 for s in stances if s in ("BEARISH", "AVOID", "CAUTIOUS"))

    if bullish > bearish + 1:
        return "CONSENSUS POSITIVE — majority of analytical frameworks support the position"
    elif bearish > bullish + 1:
        return "CONSENSUS NEGATIVE — risk outweighs opportunity across most frameworks"
    return "NO CONSENSUS — different analytical lenses reach different conclusions, which is itself informative"


def _identify_key_debates(perspectives: List[Dict]) -> List[str]:
    debates = []
    stances = {p["name"]: p["stance"] for p in perspectives}

    if stances.get("Value Investor") in ("AVOID",) and stances.get("Growth Investor") in ("BULLISH",):
        debates.append("Value vs Growth: Is the premium justified by the growth runway, or is it speculation?")
    if stances.get("Risk / Contrarian Analyst") in ("BEARISH",) and stances.get("Growth Investor") in ("BULLISH",):
        debates.append("Growth vs Risk: Insider selling during hypergrowth — do insiders know the ceiling?")
    if "GOVERNMENT" in (stances.get("Macro / Geopolitical Analyst") or ""):
        debates.append("Political exposure: Government revenue is stable until it isn't — election/budget cycle risk")

    if not debates:
        debates.append("No major analytical disagreements — unusual and may indicate consensus complacency")

    return debates


def render_multi_perspective_markdown(data: Dict[str, Any]) -> List[str]:
    """Render multi-perspective analysis as markdown for the report."""
    if not data or not data.get("perspectives"):
        return []

    lines = []
    lines.append("## Multi-Perspective Investment Analysis")
    lines.append("")
    lines.append("Five analytical frameworks applied to the same data reach different conclusions. "
                 "The disagreements are more informative than the agreements.")
    lines.append("")

    # Summary table
    lines.append("| Perspective | Style | Stance |")
    lines.append("|------------|-------|--------|")
    for p in data["perspectives"]:
        lines.append(f"| {p['name']} | {p['style']} | **{p['stance']}** |")
    lines.append("")

    # Consensus
    lines.append(f"**Consensus:** {data.get('consensus_view', 'N/A')}")
    lines.append("")

    # Key debates
    if data.get("key_debates"):
        lines.append("### Key Analytical Debates")
        lines.append("")
        for debate in data["key_debates"]:
            lines.append(f"- {debate}")
        lines.append("")

    # Each perspective in detail
    for p in data["perspectives"]:
        lines.append(f"### {p['name']} ({p['style']})")
        lines.append("")
        lines.append(f"**Stance: {p['stance']}**")
        lines.append("")
        if p.get("thesis"):
            lines.append(f"> {p['thesis']}")
            lines.append("")
        if p.get("signals"):
            lines.append("Evidence:")
            for signal in p["signals"]:
                lines.append(f"- {signal}")
            lines.append("")

    return lines
