"""
Industry Trends Service
────────────────────────────────────────────────────────────────────────────
Analyzes industry direction and customer taste trends:
  - Industry trajectory (growing, mature, declining)
  - Technology adoption curves
  - Consumer preference shifts
  - Regulatory direction
  - ESG and sustainability trends

Uses SEC filings and news data - no external APIs required.
"""

import re
import logging
from typing import Dict, Any, List, Optional
from collections import Counter, defaultdict
from datetime import datetime

logger = logging.getLogger(__name__)

# Industry lifecycle indicators
LIFECYCLE_INDICATORS = {
    "growth_phase": {
        "signals": [
            "rapid growth", "emerging market", "market expansion", "new entrants",
            "innovation", "disruption", "first mover", "market creation",
            "greenfield", "untapped market", "early adoption", "growth rate",
            "expanding market", "market penetration",
        ],
        "weight": 1,
    },
    "mature_phase": {
        "signals": [
            "mature market", "established market", "market saturation",
            "consolidation", "market share", "competitive landscape",
            "price competition", "commoditization", "stable growth",
            "incremental improvement", "market leader", "dominant position",
        ],
        "weight": 0,
    },
    "decline_phase": {
        "signals": [
            "declining market", "market contraction", "legacy", "obsolete",
            "replacement technology", "phase out", "end of life",
            "declining demand", "structural decline", "sunset",
        ],
        "weight": -1,
    },
}

# Technology adoption trends
TECH_TRENDS = {
    "ai_adoption": {
        "keywords": ["artificial intelligence", "machine learning", "ai",
                     "generative ai", "large language model", "deep learning",
                     "neural network", "automation", "cognitive"],
        "direction": "accelerating",
    },
    "cloud_migration": {
        "keywords": ["cloud computing", "cloud migration", "saas", "paas",
                     "iaas", "multi-cloud", "hybrid cloud", "cloud-native"],
        "direction": "accelerating",
    },
    "digital_transformation": {
        "keywords": ["digital transformation", "digitization", "digital-first",
                     "online", "e-commerce", "digital channels"],
        "direction": "accelerating",
    },
    "sustainability": {
        "keywords": ["sustainability", "esg", "carbon neutral", "net zero",
                     "renewable", "clean energy", "green", "environmental"],
        "direction": "accelerating",
    },
    "remote_work": {
        "keywords": ["remote work", "hybrid work", "work from home", "distributed",
                     "flexible work", "virtual collaboration"],
        "direction": "normalizing",
    },
    "automation": {
        "keywords": ["automation", "robotics", "rpa", "autonomous",
                     "self-driving", "intelligent automation"],
        "direction": "accelerating",
    },
}

# Consumer preference trends
CONSUMER_TRENDS = {
    "personalization": {
        "keywords": ["personalization", "personalized", "customization",
                     "tailored", "individualized", "recommendation"],
        "direction": "increasing",
    },
    "subscription_economy": {
        "keywords": ["subscription", "recurring revenue", "membership",
                     "as a service", "saas", "monthly", "annual plan"],
        "direction": "growing",
    },
    "experience_over_ownership": {
        "keywords": ["experience", "sharing economy", "access", "rental",
                     "on-demand", "platform"],
        "direction": "growing",
    },
    "health_wellness": {
        "keywords": ["health", "wellness", "fitness", "mental health",
                     "well-being", "self-care", "healthy lifestyle"],
        "direction": "growing",
    },
    "sustainability_conscious": {
        "keywords": ["sustainable", "eco-friendly", "organic", "ethical",
                     "responsible", "conscious consumer", "green"],
        "direction": "growing",
    },
    "convenience": {
        "keywords": ["convenience", "same-day", "instant", "on-demand",
                     "seamless", "frictionless", "one-click"],
        "direction": "increasing",
    },
}

# Regulatory trend indicators
REGULATORY_TRENDS = {
    "data_privacy": {
        "keywords": ["data privacy", "gdpr", "ccpa", "privacy regulation",
                     "data protection", "consent", "personal data"],
        "direction": "tightening",
    },
    "antitrust": {
        "keywords": ["antitrust", "competition", "monopoly", "market concentration",
                     "merger review", "competitive harm"],
        "direction": "increasing scrutiny",
    },
    "ai_regulation": {
        "keywords": ["ai regulation", "algorithmic", "explainability",
                     "ai governance", "responsible ai", "ai ethics"],
        "direction": "emerging",
    },
    "esg_disclosure": {
        "keywords": ["esg disclosure", "climate disclosure", "sustainability report",
                     "carbon reporting", "stakeholder capitalism"],
        "direction": "increasing",
    },
    "cybersecurity": {
        "keywords": ["cybersecurity regulation", "data breach", "security requirements",
                     "incident reporting", "critical infrastructure"],
        "direction": "tightening",
    },
}


def _count_trend_signals(text: str, keywords: List[str]) -> int:
    """Count occurrences of trend signals in text."""
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw.lower() in text_lower)


def analyze_industry_lifecycle(
    filing_text: str,
    industry: str = "",
) -> Dict[str, Any]:
    """
    Determine where the industry sits in its lifecycle.

    Returns:
        Lifecycle analysis with:
        - phase: growth/mature/decline
        - confidence: How confident the assessment is
        - signals: Key indicators found
    """
    result = {
        "phase": "mature",
        "confidence": 50,
        "signals": [],
        "growth_indicators": 0,
        "maturity_indicators": 0,
        "decline_indicators": 0,
    }

    if not filing_text:
        return result

    text = " ".join(filing_text.split())

    # Count signals for each phase
    phase_scores = {}
    for phase, config in LIFECYCLE_INDICATORS.items():
        count = _count_trend_signals(text, config["signals"])
        phase_scores[phase] = count * (1 + config["weight"])

        if phase == "growth_phase":
            result["growth_indicators"] = count
        elif phase == "mature_phase":
            result["maturity_indicators"] = count
        elif phase == "decline_phase":
            result["decline_indicators"] = count

        # Collect found signals
        for signal in config["signals"]:
            if signal.lower() in text.lower():
                result["signals"].append({
                    "signal": signal,
                    "phase": phase.replace("_phase", ""),
                })

    # Determine dominant phase
    if phase_scores:
        dominant = max(phase_scores.items(), key=lambda x: x[1])
        result["phase"] = dominant[0].replace("_phase", "")

        # Calculate confidence
        total = sum(phase_scores.values())
        if total > 0:
            result["confidence"] = min(95, int(dominant[1] / total * 100))

    return result


def analyze_technology_trends(
    filing_text: str,
    news_articles: List[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Analyze technology adoption trends.

    Returns:
        Technology trend analysis with adoption levels for each trend.
    """
    result = {
        "trends": {},
        "dominant_trends": [],
        "emerging_trends": [],
        "technology_score": 50,
    }

    if not filing_text:
        return result

    text = " ".join(filing_text.split())

    # Add news text if available
    if news_articles:
        news_text = " ".join(
            f"{a.get('title', '')} {a.get('summary', '')}"
            for a in news_articles[:50]
        )
        text += " " + news_text

    # Analyze each tech trend
    trend_scores = {}
    for trend_name, config in TECH_TRENDS.items():
        count = _count_trend_signals(text, config["keywords"])
        if count > 0:
            adoption_level = "high" if count >= 10 else "medium" if count >= 3 else "low"
            trend_scores[trend_name] = {
                "mentions": count,
                "adoption_level": adoption_level,
                "direction": config["direction"],
            }

    result["trends"] = trend_scores

    # Identify dominant trends (high adoption)
    result["dominant_trends"] = [
        name for name, info in trend_scores.items()
        if info["adoption_level"] == "high"
    ]

    # Identify emerging trends (low but present)
    result["emerging_trends"] = [
        name for name, info in trend_scores.items()
        if info["adoption_level"] == "low"
    ]

    # Calculate technology score
    total_mentions = sum(t["mentions"] for t in trend_scores.values())
    result["technology_score"] = min(100, 30 + total_mentions * 2)

    return result


def analyze_consumer_trends(
    filing_text: str,
    business_model: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Analyze consumer preference trends.

    Returns:
        Consumer trend analysis with relevance to business.
    """
    result = {
        "trends": {},
        "alignment_score": 50,
        "key_trends": [],
        "trend_risks": [],
    }

    if not filing_text:
        return result

    text = " ".join(filing_text.split())

    # Analyze each consumer trend
    trend_scores = {}
    for trend_name, config in CONSUMER_TRENDS.items():
        count = _count_trend_signals(text, config["keywords"])
        if count > 0:
            relevance = "high" if count >= 5 else "medium" if count >= 2 else "low"
            trend_scores[trend_name] = {
                "mentions": count,
                "relevance": relevance,
                "direction": config["direction"],
            }

    result["trends"] = trend_scores

    # Key trends (high relevance)
    result["key_trends"] = [
        {
            "trend": name.replace("_", " ").title(),
            "direction": info["direction"],
            "relevance": info["relevance"],
        }
        for name, info in trend_scores.items()
        if info["relevance"] in ("high", "medium")
    ]

    # Calculate alignment score
    if trend_scores:
        avg_mentions = sum(t["mentions"] for t in trend_scores.values()) / len(trend_scores)
        result["alignment_score"] = min(100, int(40 + avg_mentions * 10))

    return result


def analyze_regulatory_trends(
    filing_text: str,
    industry: str = "",
) -> Dict[str, Any]:
    """
    Analyze regulatory direction and compliance requirements.

    Returns:
        Regulatory trend analysis with impact assessment.
    """
    result = {
        "trends": {},
        "regulatory_burden": "moderate",
        "key_regulations": [],
        "emerging_requirements": [],
    }

    if not filing_text:
        return result

    text = " ".join(filing_text.split())

    # Analyze each regulatory trend
    trend_scores = {}
    for trend_name, config in REGULATORY_TRENDS.items():
        count = _count_trend_signals(text, config["keywords"])
        if count > 0:
            impact = "high" if count >= 5 else "medium" if count >= 2 else "low"
            trend_scores[trend_name] = {
                "mentions": count,
                "impact": impact,
                "direction": config["direction"],
            }

    result["trends"] = trend_scores

    # Key regulations (high impact)
    result["key_regulations"] = [
        {
            "area": name.replace("_", " ").title(),
            "direction": info["direction"],
            "impact": info["impact"],
        }
        for name, info in trend_scores.items()
        if info["impact"] == "high"
    ]

    # Emerging requirements
    result["emerging_requirements"] = [
        {
            "area": name.replace("_", " ").title(),
            "direction": info["direction"],
        }
        for name, info in trend_scores.items()
        if info["direction"] in ("emerging", "tightening") and info["impact"] != "high"
    ]

    # Calculate regulatory burden
    high_impact_count = sum(1 for t in trend_scores.values() if t["impact"] == "high")
    if high_impact_count >= 3:
        result["regulatory_burden"] = "heavy"
    elif high_impact_count == 0:
        result["regulatory_burden"] = "light"

    return result


def get_industry_trends(
    filing_text: str = "",
    news_articles: List[Dict[str, Any]] = None,
    industry: str = "",
    business_model: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Comprehensive industry trends analysis.

    Returns:
        Complete industry trends analysis.
    """
    return {
        "industry_lifecycle": analyze_industry_lifecycle(filing_text, industry),
        "technology_trends": analyze_technology_trends(filing_text, news_articles),
        "consumer_trends": analyze_consumer_trends(filing_text, business_model),
        "regulatory_trends": analyze_regulatory_trends(filing_text, industry),
        "industry": industry,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }


def render_industry_trends_markdown(data: Dict[str, Any]) -> List[str]:
    """Render industry trends section as markdown."""
    lines = ["## Industry Direction & Trends", ""]

    # Industry lifecycle
    lifecycle = data.get("industry_lifecycle", {})
    if lifecycle.get("phase"):
        lines.append("### Industry Lifecycle")
        lines.append("")
        phase = lifecycle.get("phase", "mature").title()
        confidence = lifecycle.get("confidence", 0)
        lines.append(f"**Current Phase:** {phase} (confidence: {confidence}%)")
        lines.append("")

        lines.append("| Phase Indicator | Count |")
        lines.append("|-----------------|-------|")
        lines.append(f"| Growth signals | {lifecycle.get('growth_indicators', 0)} |")
        lines.append(f"| Maturity signals | {lifecycle.get('maturity_indicators', 0)} |")
        lines.append(f"| Decline signals | {lifecycle.get('decline_indicators', 0)} |")
        lines.append("")

        signals = lifecycle.get("signals", [])[:5]
        if signals:
            lines.append("**Key Signals Detected:**")
            for signal in signals:
                lines.append(f"- {signal['signal']} ({signal['phase']})")
            lines.append("")

    # Technology trends
    tech = data.get("technology_trends", {})
    if tech.get("trends"):
        lines.append("### Technology Adoption Trends")
        lines.append("")
        lines.append(f"**Technology Adoption Score:** {tech.get('technology_score', 0)}/100")
        lines.append("")

        if tech.get("dominant_trends"):
            lines.append("**Dominant Trends:** " +
                         ", ".join(t.replace("_", " ").title() for t in tech["dominant_trends"]))
            lines.append("")

        lines.append("| Trend | Adoption | Direction |")
        lines.append("|-------|----------|-----------|")
        for trend, info in list(tech.get("trends", {}).items())[:8]:
            lines.append(f"| {trend.replace('_', ' ').title()} | {info['adoption_level'].title()} | {info['direction'].title()} |")
        lines.append("")

    # Consumer trends
    consumer = data.get("consumer_trends", {})
    if consumer.get("key_trends"):
        lines.append("### Consumer Preference Trends")
        lines.append("")
        lines.append(f"**Trend Alignment Score:** {consumer.get('alignment_score', 0)}/100")
        lines.append("")

        lines.append("| Trend | Direction | Relevance |")
        lines.append("|-------|-----------|-----------|")
        for trend in consumer.get("key_trends", [])[:6]:
            lines.append(f"| {trend['trend']} | {trend['direction'].title()} | {trend['relevance'].title()} |")
        lines.append("")

    # Regulatory trends
    regulatory = data.get("regulatory_trends", {})
    if regulatory.get("key_regulations") or regulatory.get("trends"):
        lines.append("### Regulatory Direction")
        lines.append("")
        lines.append(f"**Regulatory Burden:** {regulatory.get('regulatory_burden', 'moderate').title()}")
        lines.append("")

        key_regs = regulatory.get("key_regulations", [])
        if key_regs:
            lines.append("**Key Regulatory Areas:**")
            for reg in key_regs:
                lines.append(f"- **{reg['area']}** — {reg['direction'].title()} ({reg['impact']} impact)")
            lines.append("")

        emerging = regulatory.get("emerging_requirements", [])
        if emerging:
            lines.append("**Emerging Requirements:**")
            for req in emerging[:5]:
                lines.append(f"- {req['area']} ({req['direction']})")
            lines.append("")

    lines.append("*Trend analysis based on SEC filings and market data.*")
    lines.append("")

    return lines
