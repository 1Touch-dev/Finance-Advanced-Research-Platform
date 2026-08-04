"""
Market Dynamics Service
────────────────────────────────────────────────────────────────────────────
Analyzes market dynamics and competitive factors affecting a company:
  - Demand factors and growth drivers
  - Infrastructure scaling indicators
  - Customer concentration and churn risk
  - Competitive landscape analysis
  - Industry direction and trends

Uses SEC filings (10-K, 10-Q) and existing news data - no external APIs required.
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict, Counter
from datetime import datetime

logger = logging.getLogger(__name__)

# Demand factor keywords by category
DEMAND_KEYWORDS = {
    "growth_drivers": {
        "ai_ml": ["artificial intelligence", "machine learning", "ai", "deep learning",
                  "neural network", "generative ai", "large language model", "llm"],
        "cloud": ["cloud computing", "cloud services", "saas", "infrastructure as a service",
                  "platform as a service", "cloud migration", "hybrid cloud"],
        "data_center": ["data center", "datacenter", "server", "hyperscale",
                        "colocation", "edge computing"],
        "ev_electrification": ["electric vehicle", "ev", "battery", "electrification",
                               "charging infrastructure", "renewable energy"],
        "5g_connectivity": ["5g", "wireless", "connectivity", "iot", "internet of things"],
        "digital_transformation": ["digital transformation", "digitization", "automation",
                                   "modernization", "digital-first"],
    },
    "demand_signals": {
        "increasing": ["growing demand", "strong demand", "robust demand", "increased demand",
                       "demand growth", "accelerating demand", "surging demand", "demand exceeds"],
        "stable": ["stable demand", "steady demand", "consistent demand", "healthy demand"],
        "decreasing": ["declining demand", "weak demand", "softening demand", "reduced demand",
                       "demand weakness", "demand headwinds"],
    },
    "supply_constraints": {
        "shortage": ["shortage", "supply constraint", "limited supply", "supply chain disruption",
                     "capacity constraint", "production bottleneck"],
        "lead_times": ["lead time", "backlog", "order backlog", "delivery delay",
                       "extended lead times"],
        "inventory": ["inventory build", "inventory levels", "channel inventory",
                      "excess inventory", "inventory correction"],
    },
}

# Infrastructure scaling indicators
INFRASTRUCTURE_KEYWORDS = {
    "capacity_expansion": ["capacity expansion", "expanding capacity", "new facility",
                           "new fab", "manufacturing expansion", "production capacity",
                           "capex increase", "capital investment"],
    "geographic_expansion": ["geographic expansion", "international expansion",
                             "entering new markets", "new regions", "global footprint"],
    "workforce": ["hiring", "headcount growth", "workforce expansion", "talent acquisition",
                  "employee growth", "layoffs", "workforce reduction", "restructuring"],
    "technology_investment": ["r&d investment", "research and development", "technology investment",
                              "innovation", "new product development"],
    "partnerships": ["strategic partnership", "joint venture", "collaboration",
                     "alliance", "licensing agreement"],
}

# Customer concentration patterns
CUSTOMER_PATTERNS = [
    re.compile(r"(?:one|two|three|four|five|1|2|3|4|5)\s+(?:customer|client)s?\s+(?:accounted|represented|comprised)\s+(?:for\s+)?(?:approximately\s+)?(\d+)[%\s]", re.I),
    re.compile(r"largest\s+customer\s+(?:accounted|represented)\s+(?:for\s+)?(?:approximately\s+)?(\d+)[%\s]", re.I),
    re.compile(r"top\s+(\d+)\s+customers?\s+(?:accounted|represented)\s+(?:for\s+)?(?:approximately\s+)?(\d+)[%\s]", re.I),
    re.compile(r"customer\s+concentration[:\s]+(\d+)[%\s]", re.I),
    re.compile(r"(\d+)[%\s]+of\s+(?:our\s+)?(?:total\s+)?(?:net\s+)?revenues?\s+(?:from|was attributed to)\s+(?:our\s+)?(?:largest|single)", re.I),
]

# Churn risk indicators
CHURN_INDICATORS = {
    "high_risk": [
        "customer attrition", "customer losses", "losing customers",
        "contract termination", "non-renewal", "customer defection",
        "competitive displacement", "switched to competitor",
    ],
    "retention_focus": [
        "customer retention", "renewal rate", "customer loyalty",
        "long-term contracts", "recurring revenue", "subscription",
        "annual recurring revenue", "arr growth",
    ],
    "switching_costs": [
        "switching costs", "lock-in", "ecosystem", "integration",
        "migration costs", "platform dependency", "proprietary",
    ],
}

# Competitive landscape keywords
COMPETITIVE_KEYWORDS = {
    "competitive_position": [
        "market leader", "market share", "competitive advantage",
        "differentiation", "market position", "industry leader",
        "first mover", "technology leadership",
    ],
    "competitive_threats": [
        "competitive pressure", "new entrants", "competition",
        "market share loss", "price competition", "commoditization",
        "disruptive technology", "alternative solutions",
    ],
    "barriers_to_entry": [
        "barriers to entry", "intellectual property", "patents",
        "regulatory requirements", "capital requirements",
        "economies of scale", "network effects",
    ],
}


def _count_keywords(text: str, keywords: List[str]) -> int:
    """Count occurrences of keywords in text."""
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw.lower() in text_lower)


def _extract_percentages(text: str, patterns: List[re.Pattern]) -> List[Dict[str, Any]]:
    """Extract percentage mentions matching patterns."""
    results = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            groups = match.groups()
            pct = None
            for g in groups:
                if g and g.isdigit():
                    pct = int(g)
                    break
            if pct:
                results.append({
                    "text": match.group(0),
                    "percentage": pct,
                })
    return results


def analyze_demand_factors(
    filing_text: str,
    news_articles: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Analyze demand factors from 10-K/10-Q filings and news.

    Returns:
        Demand analysis including:
        - growth_drivers: Identified demand drivers and their strength
        - demand_signals: Direction of demand (increasing/stable/decreasing)
        - supply_dynamics: Supply constraints and capacity
        - demand_score: Overall demand health score (0-100)
    """
    result = {
        "growth_drivers": {},
        "demand_signals": {"direction": "stable", "confidence": 0},
        "supply_dynamics": {},
        "key_mentions": [],
        "demand_score": 50,
        "analysis_summary": "",
    }

    if not filing_text:
        return result

    text = " ".join(filing_text.split())

    # Analyze growth drivers
    driver_scores = {}
    for category, keywords in DEMAND_KEYWORDS["growth_drivers"].items():
        count = _count_keywords(text, keywords)
        if count > 0:
            driver_scores[category] = {
                "mentions": count,
                "relevance": "high" if count >= 5 else "medium" if count >= 2 else "low",
            }

    result["growth_drivers"] = driver_scores

    # Analyze demand signals
    increasing = _count_keywords(text, DEMAND_KEYWORDS["demand_signals"]["increasing"])
    decreasing = _count_keywords(text, DEMAND_KEYWORDS["demand_signals"]["decreasing"])
    stable = _count_keywords(text, DEMAND_KEYWORDS["demand_signals"]["stable"])

    if increasing > decreasing + stable:
        result["demand_signals"] = {"direction": "increasing", "confidence": min(increasing * 10, 100)}
    elif decreasing > increasing + stable:
        result["demand_signals"] = {"direction": "decreasing", "confidence": min(decreasing * 10, 100)}
    else:
        result["demand_signals"] = {"direction": "stable", "confidence": min((stable + 1) * 10, 100)}

    # Analyze supply dynamics
    supply_analysis = {}
    for category, keywords in DEMAND_KEYWORDS["supply_constraints"].items():
        count = _count_keywords(text, keywords)
        if count > 0:
            supply_analysis[category] = count

    result["supply_dynamics"] = supply_analysis

    # Calculate demand score
    score = 50  # Baseline
    score += increasing * 3
    score -= decreasing * 5
    score += len(driver_scores) * 5
    score -= supply_analysis.get("shortage", 0) * 3

    result["demand_score"] = max(0, min(100, score))

    # Add news-based demand signals if available
    if news_articles:
        news_signals = {"positive": 0, "negative": 0}
        for article in news_articles:
            tone = article.get("tone", "neutral")
            themes = article.get("themes", [])
            if "operations" in themes or "results" in themes:
                if tone == "positive":
                    news_signals["positive"] += 1
                elif tone == "negative":
                    news_signals["negative"] += 1

        if news_signals["positive"] > news_signals["negative"]:
            result["demand_score"] = min(100, result["demand_score"] + 5)
        elif news_signals["negative"] > news_signals["positive"]:
            result["demand_score"] = max(0, result["demand_score"] - 5)

    # Generate summary
    direction = result["demand_signals"]["direction"]
    drivers = list(driver_scores.keys())[:3]
    driver_text = ", ".join(d.replace("_", " ") for d in drivers) if drivers else "general market factors"

    if direction == "increasing":
        result["analysis_summary"] = f"Demand appears to be strengthening, driven by {driver_text}."
    elif direction == "decreasing":
        result["analysis_summary"] = f"Demand shows signs of softening, with headwinds in {driver_text}."
    else:
        result["analysis_summary"] = f"Demand remains stable, supported by {driver_text}."

    return result


def analyze_infrastructure_scaling(
    filing_text: str,
    financial_data: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Analyze infrastructure scaling indicators.

    Returns:
        Infrastructure analysis including:
        - capacity_indicators: Signs of expansion or contraction
        - capex_trend: Capital expenditure direction
        - workforce_trend: Hiring/layoffs signals
        - scaling_score: Overall scaling momentum (0-100)
    """
    result = {
        "capacity_indicators": {},
        "capex_trend": "stable",
        "workforce_trend": "stable",
        "geographic_expansion": [],
        "technology_investments": [],
        "scaling_score": 50,
        "analysis_summary": "",
    }

    if not filing_text:
        return result

    text = " ".join(filing_text.split())

    # Analyze infrastructure categories
    for category, keywords in INFRASTRUCTURE_KEYWORDS.items():
        count = _count_keywords(text, keywords)
        if count > 0:
            result["capacity_indicators"][category] = {
                "mentions": count,
                "signal": "expansion" if category != "workforce" or "hiring" in text.lower() else "mixed",
            }

    # Determine workforce trend
    hiring_count = _count_keywords(text, ["hiring", "headcount growth", "workforce expansion"])
    layoff_count = _count_keywords(text, ["layoffs", "workforce reduction", "restructuring"])

    if hiring_count > layoff_count:
        result["workforce_trend"] = "expanding"
    elif layoff_count > hiring_count:
        result["workforce_trend"] = "contracting"

    # Analyze capex from financial data if available
    if financial_data:
        cf_data = financial_data.get("cash_flow", [])
        if len(cf_data) >= 2:
            current_capex = abs(cf_data[0].get("capex", 0) or 0)
            prior_capex = abs(cf_data[1].get("capex", 0) or 0)
            if prior_capex > 0:
                capex_change = (current_capex - prior_capex) / prior_capex
                if capex_change > 0.1:
                    result["capex_trend"] = "increasing"
                elif capex_change < -0.1:
                    result["capex_trend"] = "decreasing"

    # Calculate scaling score
    score = 50
    expansion_count = sum(1 for v in result["capacity_indicators"].values()
                          if v.get("signal") == "expansion")
    score += expansion_count * 10

    if result["workforce_trend"] == "expanding":
        score += 10
    elif result["workforce_trend"] == "contracting":
        score -= 15

    if result["capex_trend"] == "increasing":
        score += 10
    elif result["capex_trend"] == "decreasing":
        score -= 10

    result["scaling_score"] = max(0, min(100, score))

    # Generate summary
    if result["scaling_score"] >= 65:
        result["analysis_summary"] = "Company is actively scaling infrastructure with capacity expansion and investment."
    elif result["scaling_score"] <= 35:
        result["analysis_summary"] = "Infrastructure scaling shows contraction signals with reduced investment."
    else:
        result["analysis_summary"] = "Infrastructure scaling is stable with modest investment activity."

    return result


def analyze_customer_dynamics(
    filing_text: str,
    segment_data: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Analyze customer concentration and churn risk.

    Returns:
        Customer analysis including:
        - concentration_risk: Customer concentration level
        - top_customer_pct: Largest customer as % of revenue
        - churn_indicators: Signs of customer attrition
        - retention_signals: Customer retention strength
        - churn_risk_score: Overall churn risk (0-100, higher = more risk)
    """
    result = {
        "concentration_risk": "low",
        "top_customer_pct": None,
        "top_customers": [],
        "churn_indicators": [],
        "retention_signals": [],
        "switching_cost_level": "medium",
        "churn_risk_score": 30,
        "analysis_summary": "",
    }

    if not filing_text:
        return result

    text = " ".join(filing_text.split())

    # Extract customer concentration percentages
    concentrations = _extract_percentages(text, CUSTOMER_PATTERNS)
    if concentrations:
        max_pct = max(c["percentage"] for c in concentrations)
        result["top_customer_pct"] = max_pct
        result["top_customers"] = concentrations[:5]

        if max_pct >= 30:
            result["concentration_risk"] = "high"
        elif max_pct >= 15:
            result["concentration_risk"] = "medium"

    # Analyze churn indicators
    for indicator in CHURN_INDICATORS["high_risk"]:
        if indicator.lower() in text.lower():
            result["churn_indicators"].append(indicator)

    # Analyze retention signals
    for signal in CHURN_INDICATORS["retention_focus"]:
        if signal.lower() in text.lower():
            result["retention_signals"].append(signal)

    # Analyze switching costs
    switching_cost_count = _count_keywords(text, CHURN_INDICATORS["switching_costs"])
    if switching_cost_count >= 5:
        result["switching_cost_level"] = "high"
    elif switching_cost_count <= 1:
        result["switching_cost_level"] = "low"

    # Add segment data if available
    if segment_data:
        customer_concentration = segment_data.get("customer_concentration", [])
        for cc in customer_concentration[:3]:
            if cc.get("pct") and cc["pct"] > (result.get("top_customer_pct") or 0):
                result["top_customer_pct"] = cc["pct"]

    # Calculate churn risk score
    score = 30  # Baseline

    # Concentration risk
    if result["top_customer_pct"]:
        score += result["top_customer_pct"] // 2

    # Churn indicators increase risk
    score += len(result["churn_indicators"]) * 10

    # Retention signals decrease risk
    score -= len(result["retention_signals"]) * 5

    # Switching costs decrease risk
    if result["switching_cost_level"] == "high":
        score -= 15
    elif result["switching_cost_level"] == "low":
        score += 10

    result["churn_risk_score"] = max(0, min(100, score))

    # Generate summary
    conc = result["concentration_risk"]
    pct = result["top_customer_pct"]

    if result["churn_risk_score"] >= 60:
        summary = "High customer churn risk"
        if pct:
            summary += f" with {pct}% revenue concentration"
    elif result["churn_risk_score"] <= 30:
        summary = "Low churn risk with strong customer retention signals"
    else:
        summary = f"Moderate customer concentration ({conc} risk level)"

    result["analysis_summary"] = summary

    return result


def analyze_competitive_landscape(
    filing_text: str,
    peers: List[str] = None,
) -> Dict[str, Any]:
    """
    Analyze competitive landscape and positioning.

    Returns:
        Competitive analysis including:
        - market_position: Self-described market position
        - competitive_threats: Identified competitive pressures
        - barriers_to_entry: Moat indicators
        - competitor_mentions: Named competitors
        - competitive_intensity: Overall competitive pressure level
    """
    result = {
        "market_position": [],
        "competitive_threats": [],
        "barriers_to_entry": [],
        "competitor_mentions": [],
        "competitive_intensity": "moderate",
        "competitive_score": 50,
        "analysis_summary": "",
    }

    if not filing_text:
        return result

    text = " ".join(filing_text.split())

    # Analyze market position claims
    for kw in COMPETITIVE_KEYWORDS["competitive_position"]:
        if kw.lower() in text.lower():
            result["market_position"].append(kw)

    # Analyze competitive threats
    for kw in COMPETITIVE_KEYWORDS["competitive_threats"]:
        if kw.lower() in text.lower():
            result["competitive_threats"].append(kw)

    # Analyze barriers to entry
    for kw in COMPETITIVE_KEYWORDS["barriers_to_entry"]:
        if kw.lower() in text.lower():
            result["barriers_to_entry"].append(kw)

    # Find competitor mentions if peers provided
    if peers:
        for peer in peers:
            if peer.upper() in text.upper() or peer.lower() in text.lower():
                result["competitor_mentions"].append(peer)

    # Determine competitive intensity
    threat_count = len(result["competitive_threats"])
    position_count = len(result["market_position"])
    barrier_count = len(result["barriers_to_entry"])

    if threat_count > position_count + barrier_count:
        result["competitive_intensity"] = "high"
    elif position_count + barrier_count > threat_count * 2:
        result["competitive_intensity"] = "low"

    # Calculate competitive score (higher = stronger position)
    score = 50
    score += position_count * 5
    score += barrier_count * 8
    score -= threat_count * 5

    result["competitive_score"] = max(0, min(100, score))

    # Generate summary
    if result["competitive_score"] >= 65:
        result["analysis_summary"] = "Strong competitive position with significant barriers to entry."
    elif result["competitive_score"] <= 35:
        result["analysis_summary"] = "Facing significant competitive pressures with limited moat."
    else:
        result["analysis_summary"] = "Moderate competitive position in a contested market."

    return result


def get_market_dynamics(
    filing_text: str = "",
    news_articles: List[Dict[str, Any]] = None,
    financial_data: Dict[str, Any] = None,
    segment_data: Dict[str, Any] = None,
    peers: List[str] = None,
) -> Dict[str, Any]:
    """
    Comprehensive market dynamics analysis.

    Returns:
        Complete market dynamics including all sub-analyses.
    """
    return {
        "demand_factors": analyze_demand_factors(filing_text, news_articles),
        "infrastructure_scaling": analyze_infrastructure_scaling(filing_text, financial_data),
        "customer_dynamics": analyze_customer_dynamics(filing_text, segment_data),
        "competitive_landscape": analyze_competitive_landscape(filing_text, peers),
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


def render_market_dynamics_markdown(data: Dict[str, Any]) -> List[str]:
    """Render market dynamics section as markdown."""
    lines = ["## Market Dynamics Analysis", ""]

    # Demand factors
    demand = data.get("demand_factors", {})
    if demand.get("growth_drivers") or demand.get("demand_signals"):
        lines.append("### Demand Factors")
        lines.append("")

        if demand.get("analysis_summary"):
            lines.append(demand["analysis_summary"])
            lines.append("")

        lines.append(f"**Demand Direction:** {demand.get('demand_signals', {}).get('direction', 'N/A').title()}")
        lines.append(f"**Demand Score:** {demand.get('demand_score', 'N/A')}/100")
        lines.append("")

        drivers = demand.get("growth_drivers", {})
        if drivers:
            lines.append("**Key Growth Drivers:**")
            for driver, info in list(drivers.items())[:5]:
                relevance = info.get("relevance", "low")
                lines.append(f"- {driver.replace('_', ' ').title()} ({relevance} relevance)")
            lines.append("")

        supply = demand.get("supply_dynamics", {})
        if supply:
            lines.append("**Supply Dynamics:**")
            for factor, count in supply.items():
                lines.append(f"- {factor.replace('_', ' ').title()}: {count} mentions")
            lines.append("")

    # Infrastructure scaling
    infra = data.get("infrastructure_scaling", {})
    if infra.get("capacity_indicators") or infra.get("scaling_score"):
        lines.append("### Infrastructure Scaling")
        lines.append("")

        if infra.get("analysis_summary"):
            lines.append(infra["analysis_summary"])
            lines.append("")

        lines.append(f"**Scaling Score:** {infra.get('scaling_score', 'N/A')}/100")
        lines.append(f"**Capex Trend:** {infra.get('capex_trend', 'N/A').title()}")
        lines.append(f"**Workforce Trend:** {infra.get('workforce_trend', 'N/A').title()}")
        lines.append("")

        indicators = infra.get("capacity_indicators", {})
        if indicators:
            lines.append("**Scaling Indicators:**")
            for indicator, info in indicators.items():
                signal = info.get("signal", "mixed")
                lines.append(f"- {indicator.replace('_', ' ').title()}: {signal}")
            lines.append("")

    # Customer dynamics
    customer = data.get("customer_dynamics", {})
    if customer.get("concentration_risk") or customer.get("churn_risk_score"):
        lines.append("### Customer Dynamics")
        lines.append("")

        if customer.get("analysis_summary"):
            lines.append(customer["analysis_summary"])
            lines.append("")

        lines.append(f"**Concentration Risk:** {customer.get('concentration_risk', 'N/A').title()}")
        if customer.get("top_customer_pct"):
            lines.append(f"**Top Customer Revenue:** {customer['top_customer_pct']}%")
        lines.append(f"**Churn Risk Score:** {customer.get('churn_risk_score', 'N/A')}/100")
        lines.append(f"**Switching Costs:** {customer.get('switching_cost_level', 'N/A').title()}")
        lines.append("")

        if customer.get("retention_signals"):
            lines.append("**Retention Signals:** " + ", ".join(customer["retention_signals"][:5]))
            lines.append("")

    # Competitive landscape
    competitive = data.get("competitive_landscape", {})
    if competitive.get("market_position") or competitive.get("competitive_score"):
        lines.append("### Competitive Landscape")
        lines.append("")

        if competitive.get("analysis_summary"):
            lines.append(competitive["analysis_summary"])
            lines.append("")

        lines.append(f"**Competitive Intensity:** {competitive.get('competitive_intensity', 'N/A').title()}")
        lines.append(f"**Competitive Score:** {competitive.get('competitive_score', 'N/A')}/100")
        lines.append("")

        if competitive.get("market_position"):
            lines.append("**Market Position Claims:** " + ", ".join(competitive["market_position"][:5]))
            lines.append("")

        if competitive.get("barriers_to_entry"):
            lines.append("**Barriers to Entry:** " + ", ".join(competitive["barriers_to_entry"][:5]))
            lines.append("")

        if competitive.get("competitive_threats"):
            lines.append("**Competitive Threats:** " + ", ".join(competitive["competitive_threats"][:5]))
            lines.append("")

    lines.append("*Analysis based on SEC filings and market data.*")
    lines.append("")

    return lines
