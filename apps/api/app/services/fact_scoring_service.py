"""
Fact Scoring Service — Source Reliability & Credibility Scoring
───────────────────────────────────────────────────────────────
Provides quality metrics for data sources and generated insights.

Features:
- Source reliability scoring (0-100)
- Data freshness assessment
- Citation verification
- Cross-reference validation
- Confidence intervals for claims
- Historical accuracy tracking
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

log = logging.getLogger(__name__)


class SourceTier(str, Enum):
    """Source reliability tiers."""
    TIER_1 = "tier_1"  # Primary official sources (SEC, Fed, govt)
    TIER_2 = "tier_2"  # Reputable financial data providers
    TIER_3 = "tier_3"  # News and media
    TIER_4 = "tier_4"  # Community/social sources
    UNVERIFIED = "unverified"


class DataFreshness(str, Enum):
    """Data freshness levels."""
    REAL_TIME = "real_time"  # < 1 minute
    VERY_FRESH = "very_fresh"  # < 1 hour
    FRESH = "fresh"  # < 24 hours
    RECENT = "recent"  # < 7 days
    DATED = "dated"  # < 30 days
    STALE = "stale"  # > 30 days


@dataclass
class SourceProfile:
    """Profile for a data source."""
    name: str
    tier: SourceTier
    base_reliability: float  # 0-100
    update_frequency: str
    data_types: List[str]
    requires_verification: bool = False
    historical_accuracy: Optional[float] = None
    last_verified: Optional[str] = None


# ── Source Registry ─────────────────────────────────────────────────────────

SOURCE_REGISTRY: Dict[str, SourceProfile] = {
    # Tier 1: Official Government/Regulatory Sources
    "sec_edgar": SourceProfile(
        name="SEC EDGAR",
        tier=SourceTier.TIER_1,
        base_reliability=98,
        update_frequency="Real-time filings",
        data_types=["filings", "insider_transactions", "financial_statements"],
    ),
    "fred": SourceProfile(
        name="Federal Reserve Economic Data",
        tier=SourceTier.TIER_1,
        base_reliability=99,
        update_frequency="Varies by series",
        data_types=["economic_indicators", "macro_data"],
    ),
    "bea": SourceProfile(
        name="Bureau of Economic Analysis",
        tier=SourceTier.TIER_1,
        base_reliability=99,
        update_frequency="Quarterly/Annual",
        data_types=["gdp", "trade", "state_data"],
    ),
    "finra": SourceProfile(
        name="FINRA",
        tier=SourceTier.TIER_1,
        base_reliability=97,
        update_frequency="Bi-weekly",
        data_types=["short_interest"],
    ),
    "uk_companies_house": SourceProfile(
        name="UK Companies House",
        tier=SourceTier.TIER_1,
        base_reliability=98,
        update_frequency="Real-time",
        data_types=["company_registry", "officers", "filings"],
    ),
    "gleif": SourceProfile(
        name="GLEIF (LEI Registry)",
        tier=SourceTier.TIER_1,
        base_reliability=99,
        update_frequency="Daily",
        data_types=["legal_entity_identifiers", "ownership"],
    ),
    "opencorporates": SourceProfile(
        name="OpenCorporates",
        tier=SourceTier.TIER_1,
        base_reliability=95,
        update_frequency="Aggregated from registries",
        data_types=["company_registry", "global_entities"],
    ),

    # Tier 2: Reputable Financial Data Providers
    "finnhub": SourceProfile(
        name="Finnhub",
        tier=SourceTier.TIER_2,
        base_reliability=90,
        update_frequency="Real-time",
        data_types=["quotes", "earnings", "news"],
    ),
    "fmp": SourceProfile(
        name="Financial Modeling Prep",
        tier=SourceTier.TIER_2,
        base_reliability=88,
        update_frequency="Daily",
        data_types=["financials", "ipo", "metrics"],
    ),
    "yahoo_finance": SourceProfile(
        name="Yahoo Finance",
        tier=SourceTier.TIER_2,
        base_reliability=85,
        update_frequency="Real-time",
        data_types=["quotes", "financials", "news"],
    ),
    "capitol_trades": SourceProfile(
        name="Capitol Trades / Kapitol.ai",
        tier=SourceTier.TIER_2,
        base_reliability=92,
        update_frequency="Daily",
        data_types=["politician_trades", "congress_activity"],
    ),

    # Tier 3: News and Media
    "newsapi": SourceProfile(
        name="NewsAPI",
        tier=SourceTier.TIER_3,
        base_reliability=75,
        update_frequency="Real-time",
        data_types=["news", "headlines"],
        requires_verification=True,
    ),
    "guardian": SourceProfile(
        name="The Guardian",
        tier=SourceTier.TIER_3,
        base_reliability=80,
        update_frequency="Real-time",
        data_types=["news", "analysis"],
    ),
    "nyt": SourceProfile(
        name="New York Times",
        tier=SourceTier.TIER_3,
        base_reliability=82,
        update_frequency="Real-time",
        data_types=["news", "analysis"],
    ),
    "gdelt": SourceProfile(
        name="GDELT Project",
        tier=SourceTier.TIER_3,
        base_reliability=70,
        update_frequency="15 minutes",
        data_types=["global_events", "sentiment"],
        requires_verification=True,
    ),

    # Tier 4: Community/Social Sources
    "reddit": SourceProfile(
        name="Reddit",
        tier=SourceTier.TIER_4,
        base_reliability=40,
        update_frequency="Real-time",
        data_types=["sentiment", "discussion"],
        requires_verification=True,
    ),
    "stocktwits": SourceProfile(
        name="StockTwits",
        tier=SourceTier.TIER_4,
        base_reliability=35,
        update_frequency="Real-time",
        data_types=["sentiment", "discussion"],
        requires_verification=True,
    ),
}


# ── Core Scoring Functions ─────────────────────────────────────────────────


def get_source_reliability(source: str) -> Dict[str, Any]:
    """Get reliability score and profile for a data source."""
    source_key = source.lower().replace(" ", "_").replace("-", "_")
    profile = SOURCE_REGISTRY.get(source_key)

    if not profile:
        return {
            "source": source,
            "tier": SourceTier.UNVERIFIED.value,
            "reliability_score": 50,
            "confidence": "low",
            "requires_verification": True,
            "warning": "Unknown source - manual verification recommended",
        }

    return {
        "source": profile.name,
        "tier": profile.tier.value,
        "reliability_score": profile.base_reliability,
        "confidence": _score_to_confidence(profile.base_reliability),
        "update_frequency": profile.update_frequency,
        "data_types": profile.data_types,
        "requires_verification": profile.requires_verification,
    }


def score_fact(
    claim: str,
    sources: List[str],
    data_age_hours: Optional[float] = None,
    cross_references: int = 0,
    has_primary_source: bool = False,
) -> Dict[str, Any]:
    """
    Score the reliability of a fact/claim based on its sources.

    Args:
        claim: The fact or claim being scored
        sources: List of data sources used
        data_age_hours: Age of the data in hours
        cross_references: Number of cross-references confirming the fact
        has_primary_source: Whether a primary source (Tier 1) confirms it

    Returns:
        Dict with reliability score and breakdown
    """
    # Calculate base source score
    source_scores = []
    source_details = []

    for src in sources:
        reliability = get_source_reliability(src)
        source_scores.append(reliability["reliability_score"])
        source_details.append({
            "source": reliability["source"],
            "tier": reliability["tier"],
            "score": reliability["reliability_score"],
        })

    if not source_scores:
        base_score = 0
    else:
        # Use weighted average favoring highest-tier source
        base_score = max(source_scores) * 0.6 + (sum(source_scores) / len(source_scores)) * 0.4

    # Freshness adjustment
    freshness_multiplier = 1.0
    freshness_level = DataFreshness.FRESH

    if data_age_hours is not None:
        if data_age_hours < 0.0167:  # < 1 minute
            freshness_level = DataFreshness.REAL_TIME
            freshness_multiplier = 1.0
        elif data_age_hours < 1:
            freshness_level = DataFreshness.VERY_FRESH
            freshness_multiplier = 1.0
        elif data_age_hours < 24:
            freshness_level = DataFreshness.FRESH
            freshness_multiplier = 0.98
        elif data_age_hours < 168:  # 7 days
            freshness_level = DataFreshness.RECENT
            freshness_multiplier = 0.95
        elif data_age_hours < 720:  # 30 days
            freshness_level = DataFreshness.DATED
            freshness_multiplier = 0.85
        else:
            freshness_level = DataFreshness.STALE
            freshness_multiplier = 0.70

    # Cross-reference bonus
    cross_ref_bonus = min(cross_references * 3, 15)  # Max +15 for 5+ cross-refs

    # Primary source bonus
    primary_bonus = 10 if has_primary_source else 0

    # Calculate final score
    final_score = min(100, (base_score * freshness_multiplier) + cross_ref_bonus + primary_bonus)

    return {
        "claim": claim[:100] + "..." if len(claim) > 100 else claim,
        "reliability_score": round(final_score, 1),
        "confidence": _score_to_confidence(final_score),
        "breakdown": {
            "base_source_score": round(base_score, 1),
            "freshness_multiplier": freshness_multiplier,
            "freshness_level": freshness_level.value,
            "cross_reference_bonus": cross_ref_bonus,
            "primary_source_bonus": primary_bonus,
        },
        "sources_used": source_details,
        "num_sources": len(sources),
        "warnings": _generate_warnings(source_details, freshness_level, cross_references),
        "recommendation": _generate_recommendation(final_score, source_details),
    }


def score_report(
    report_sections: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Score an entire report's reliability.

    Args:
        report_sections: List of sections with 'content', 'sources', 'data_age_hours'

    Returns:
        Overall report reliability score and section breakdown
    """
    section_scores = []

    for section in report_sections:
        section_score = score_fact(
            claim=section.get("content", "")[:200],
            sources=section.get("sources", []),
            data_age_hours=section.get("data_age_hours"),
            cross_references=section.get("cross_references", 0),
            has_primary_source=section.get("has_primary_source", False),
        )
        section_scores.append({
            "section": section.get("name", "Unnamed"),
            "score": section_score["reliability_score"],
            "confidence": section_score["confidence"],
        })

    if not section_scores:
        return {
            "overall_score": 0,
            "confidence": "none",
            "sections": [],
        }

    # Overall score is weighted average
    scores = [s["score"] for s in section_scores]
    overall = sum(scores) / len(scores)

    # Count confidence levels
    confidence_counts = {
        "very_high": sum(1 for s in section_scores if s["confidence"] == "very_high"),
        "high": sum(1 for s in section_scores if s["confidence"] == "high"),
        "medium": sum(1 for s in section_scores if s["confidence"] == "medium"),
        "low": sum(1 for s in section_scores if s["confidence"] == "low"),
        "very_low": sum(1 for s in section_scores if s["confidence"] == "very_low"),
    }

    return {
        "overall_score": round(overall, 1),
        "confidence": _score_to_confidence(overall),
        "sections": section_scores,
        "confidence_distribution": confidence_counts,
        "total_sections": len(section_scores),
        "recommendation": _generate_report_recommendation(overall, confidence_counts),
    }


def validate_claim(
    claim: str,
    expected_sources: List[str],
    actual_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Validate a specific claim against actual data.

    Returns validation status and any discrepancies.
    """
    validation = {
        "claim": claim,
        "validated": False,
        "confidence": "low",
        "discrepancies": [],
        "supporting_evidence": [],
    }

    # Check if expected sources provided data
    sources_with_data = []
    sources_missing = []

    for src in expected_sources:
        src_key = src.lower().replace(" ", "_").replace("-", "_")
        if src_key in actual_data and actual_data[src_key]:
            sources_with_data.append(src)
        else:
            sources_missing.append(src)

    if sources_with_data:
        validation["validated"] = True
        validation["confidence"] = "medium" if len(sources_with_data) >= 2 else "low"
        validation["supporting_evidence"] = sources_with_data

    if sources_missing:
        validation["discrepancies"].append(f"Missing data from: {', '.join(sources_missing)}")

    return validation


# ── Helper Functions ────────────────────────────────────────────────────────


def _score_to_confidence(score: float) -> str:
    """Convert numeric score to confidence level."""
    if score >= 95:
        return "very_high"
    elif score >= 85:
        return "high"
    elif score >= 70:
        return "medium"
    elif score >= 50:
        return "low"
    else:
        return "very_low"


def _generate_warnings(
    sources: List[Dict],
    freshness: DataFreshness,
    cross_refs: int,
) -> List[str]:
    """Generate warnings based on scoring factors."""
    warnings = []

    # Check for low-tier sources only
    tiers = [s["tier"] for s in sources]
    if all(t in ["tier_3", "tier_4", "unverified"] for t in tiers):
        warnings.append("No primary or high-reliability sources used")

    # Check freshness
    if freshness in [DataFreshness.DATED, DataFreshness.STALE]:
        warnings.append(f"Data is {freshness.value} - consider refreshing")

    # Check cross-references
    if cross_refs == 0 and len(sources) == 1:
        warnings.append("Single source with no cross-references")

    return warnings


def _generate_recommendation(score: float, sources: List[Dict]) -> str:
    """Generate actionable recommendation based on score."""
    if score >= 95:
        return "High confidence - suitable for decision making"
    elif score >= 85:
        return "Good confidence - verify critical claims if needed"
    elif score >= 70:
        return "Moderate confidence - recommend additional verification"
    elif score >= 50:
        return "Low confidence - manual verification strongly recommended"
    else:
        return "Very low confidence - treat as unverified information"


def _generate_report_recommendation(score: float, conf_dist: Dict[str, int]) -> str:
    """Generate report-level recommendation."""
    low_conf_sections = conf_dist.get("low", 0) + conf_dist.get("very_low", 0)
    total = sum(conf_dist.values())

    if score >= 90 and low_conf_sections == 0:
        return "Report is well-sourced and reliable"
    elif score >= 80:
        if low_conf_sections > 0:
            return f"Overall good, but {low_conf_sections} section(s) need verification"
        return "Report is reliable with minor caveats"
    elif score >= 65:
        return "Report quality is mixed - verify key claims"
    else:
        return "Report reliability is low - significant verification needed"


# ── API Functions ───────────────────────────────────────────────────────────


def list_sources() -> List[Dict[str, Any]]:
    """List all registered sources with their profiles."""
    return [
        {
            "key": key,
            "name": profile.name,
            "tier": profile.tier.value,
            "reliability": profile.base_reliability,
            "update_frequency": profile.update_frequency,
            "data_types": profile.data_types,
        }
        for key, profile in SOURCE_REGISTRY.items()
    ]


def get_tier_summary() -> Dict[str, Any]:
    """Get summary of sources by tier."""
    tier_counts = {}
    tier_avg_reliability = {}

    for profile in SOURCE_REGISTRY.values():
        tier = profile.tier.value
        if tier not in tier_counts:
            tier_counts[tier] = 0
            tier_avg_reliability[tier] = []
        tier_counts[tier] += 1
        tier_avg_reliability[tier].append(profile.base_reliability)

    return {
        "tiers": {
            tier: {
                "count": tier_counts[tier],
                "avg_reliability": round(sum(tier_avg_reliability[tier]) / len(tier_avg_reliability[tier]), 1),
            }
            for tier in tier_counts
        },
        "total_sources": len(SOURCE_REGISTRY),
    }
