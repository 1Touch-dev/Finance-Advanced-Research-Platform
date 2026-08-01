"""
Contract Probability Analysis Service
────────────────────────────────────────────────────────────────────────────
Analyzes federal contract data to compute:
  - Contract award probability based on historical win rates
  - Upcoming contract opportunities and recompete timelines
  - Competitive landscape analysis
  - Revenue concentration risk from government contracts

Uses FPDS data, SAM.gov opportunities, and historical patterns.
"""

import os
import logging
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import math

logger = logging.getLogger(__name__)

# SAM.gov API (free, requires API key)
SAM_API_KEY = os.getenv("SAM_API_KEY", "")
SAM_OPPORTUNITIES_URL = "https://api.sam.gov/opportunities/v2/search"

# USASpending.gov API (free, no key required)
USA_SPENDING_BASE = "https://api.usaspending.gov/api/v2"

# Import entity naming for better name matching
try:
    from app.connectors.entity_naming import entity_search_term, matches_entity
    NAMING_AVAILABLE = True
except ImportError:
    NAMING_AVAILABLE = False
    def entity_search_term(name): return name
    def matches_entity(candidate, name, aliases=None): return True

# Import FPDS connector if available for better contract data
try:
    from app.connectors.fpds_connector import fetch_usaspending_full
    FPDS_AVAILABLE = True
except ImportError:
    FPDS_AVAILABLE = False
    def fetch_usaspending_full(*args, **kwargs): return {}


def _fetch_usaspending_awards(
    recipient_name: str,
    fiscal_year: int = None,
    limit: int = 100,
    subsidiaries: List[str] = None,
) -> List[Dict[str, Any]]:
    """Fetch contract awards from USASpending.gov with proper name matching."""
    if fiscal_year is None:
        fiscal_year = datetime.now().year

    subsidiaries = subsidiaries or []

    # Use FPDS connector if available (has better name matching)
    if FPDS_AVAILABLE:
        try:
            start_date = f"{fiscal_year - 5}-10-01"
            fpds_data = fetch_usaspending_full(
                recipient_name,
                max_results=limit,
                start_date=start_date,
                subsidiaries=subsidiaries
            )
            # Convert to our expected format
            awards = []
            for contract in fpds_data.get("contracts", []):
                awards.append({
                    "award_id": contract.get("award_id"),
                    "recipient": contract.get("recipient"),
                    "amount": contract.get("amount"),
                    "start_date": contract.get("start_date"),
                    "end_date": contract.get("end_date"),
                    "agency": contract.get("agency"),
                    "type": contract.get("award_type"),
                    "description": contract.get("description"),
                    "naics_code": contract.get("naics_code"),
                    "psc_code": contract.get("psc_code"),
                })
            return awards
        except Exception as e:
            logger.warning("FPDS connector fetch failed, falling back: %s", e)

    # Fallback to direct API call with name matching
    awards = []

    # Build search terms using entity naming
    search_terms = [recipient_name]
    if NAMING_AVAILABLE:
        short_term = entity_search_term(recipient_name)
        if short_term and short_term != recipient_name:
            search_terms.append(short_term)
    search_terms.extend(subsidiaries)
    search_terms = list(set(search_terms))

    try:
        # Search for recipient
        resp = requests.post(
            f"{USA_SPENDING_BASE}/search/spending_by_award/",
            json={
                "filters": {
                    "recipient_search_text": search_terms,
                    "time_period": [
                        {
                            "start_date": f"{fiscal_year - 5}-10-01",
                            "end_date": f"{fiscal_year}-09-30"
                        }
                    ],
                    "award_type_codes": ["A", "B", "C", "D"]  # Contracts only
                },
                "fields": [
                    "Award ID", "Recipient Name", "Award Amount",
                    "Start Date", "End Date", "Awarding Agency",
                    "Award Type", "Description", "Period of Performance Current End Date"
                ],
                "limit": limit * 2,  # Fetch more to filter
                "page": 1,
                "sort": "Award Amount",
                "order": "desc"
            },
            timeout=30
        )

        if resp.ok:
            data = resp.json()
            for result in data.get("results", []):
                # Verify name match to avoid false positives
                recipient = result.get("Recipient Name", "")
                if NAMING_AVAILABLE:
                    if not matches_entity(recipient, recipient_name, subsidiaries):
                        continue

                awards.append({
                    "award_id": result.get("Award ID"),
                    "recipient": recipient,
                    "amount": result.get("Award Amount"),
                    "start_date": result.get("Start Date"),
                    "end_date": result.get("End Date") or result.get("Period of Performance Current End Date"),
                    "agency": result.get("Awarding Agency"),
                    "type": result.get("Award Type"),
                    "description": result.get("Description"),
                })

                if len(awards) >= limit:
                    break

    except Exception as e:
        logger.warning("USASpending fetch failed: %s", e)

    return awards


def _fetch_sam_opportunities(
    keywords: List[str],
    naics_codes: List[str] = None,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """Fetch open contract opportunities from SAM.gov."""
    if not SAM_API_KEY:
        logger.info("SAM_API_KEY not set — skipping opportunity search")
        return []

    opportunities = []

    try:
        params = {
            "api_key": SAM_API_KEY,
            "postedFrom": (datetime.now() - timedelta(days=90)).strftime("%m/%d/%Y"),
            "postedTo": datetime.now().strftime("%m/%d/%Y"),
            "limit": limit,
            "offset": 0,
        }

        if keywords:
            params["keyword"] = " OR ".join(keywords)

        if naics_codes:
            params["ncode"] = ",".join(naics_codes)

        resp = requests.get(SAM_OPPORTUNITIES_URL, params=params, timeout=30)

        if resp.ok:
            data = resp.json()
            for opp in data.get("opportunitiesData", []):
                opportunities.append({
                    "notice_id": opp.get("noticeId"),
                    "title": opp.get("title"),
                    "type": opp.get("type"),
                    "posted_date": opp.get("postedDate"),
                    "response_deadline": opp.get("responseDeadLine"),
                    "agency": opp.get("department"),
                    "office": opp.get("office"),
                    "set_aside": opp.get("typeOfSetAside"),
                    "naics": opp.get("naicsCode"),
                    "description": (opp.get("description") or "")[:500],
                    "url": f"https://sam.gov/opp/{opp.get('noticeId')}/view",
                })
    except Exception as e:
        logger.warning("SAM.gov opportunity fetch failed: %s", e)

    return opportunities


def _calculate_win_rate(
    awards: List[Dict[str, Any]],
    company_name: str
) -> Dict[str, Any]:
    """Calculate historical win rate metrics."""
    if not awards:
        return {
            "total_awards": 0,
            "total_value": 0,
            "avg_award_size": 0,
            "agencies_served": [],
            "win_rate_estimate": None
        }

    company_lower = company_name.lower()
    company_awards = [
        a for a in awards
        if company_lower in (a.get("recipient") or "").lower()
    ]

    total_value = sum(a.get("amount") or 0 for a in company_awards)
    agencies = list(set(a.get("agency") for a in company_awards if a.get("agency")))

    return {
        "total_awards": len(company_awards),
        "total_value": total_value,
        "avg_award_size": total_value / len(company_awards) if company_awards else 0,
        "agencies_served": agencies[:10],
        "win_rate_estimate": None  # Would need bid data to calculate true win rate
    }


def _identify_recompetes(
    awards: List[Dict[str, Any]],
    months_ahead: int = 18
) -> List[Dict[str, Any]]:
    """Identify contracts coming up for recompete."""
    recompetes = []
    cutoff = datetime.now() + timedelta(days=months_ahead * 30)

    for award in awards:
        end_date_str = award.get("end_date")
        if not end_date_str:
            continue

        try:
            # Parse various date formats
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%Y-%m-%dT%H:%M:%S"]:
                try:
                    end_date = datetime.strptime(end_date_str[:10], fmt[:len(end_date_str[:10])])
                    break
                except ValueError:
                    continue
            else:
                continue

            if datetime.now() < end_date <= cutoff:
                months_until = (end_date - datetime.now()).days / 30
                recompetes.append({
                    **award,
                    "months_until_recompete": round(months_until, 1),
                    "recompete_risk": "High" if months_until < 6 else "Medium" if months_until < 12 else "Low"
                })
        except Exception:
            continue

    return sorted(recompetes, key=lambda x: x.get("months_until_recompete", 999))


def _analyze_concentration_risk(
    awards: List[Dict[str, Any]],
    total_revenue: float = None
) -> Dict[str, Any]:
    """Analyze revenue concentration risk from government contracts."""
    if not awards:
        return {
            "total_contract_value": 0,
            "top_agency_concentration": 0,
            "top_contract_concentration": 0,
            "concentration_risk": "Unknown",
            "government_revenue_pct": None
        }

    total_contract_value = sum(a.get("amount") or 0 for a in awards)

    # Agency concentration
    agency_totals = defaultdict(float)
    for award in awards:
        agency = award.get("agency") or "Unknown"
        agency_totals[agency] += award.get("amount") or 0

    top_agency_value = max(agency_totals.values()) if agency_totals else 0
    top_agency_concentration = (top_agency_value / total_contract_value * 100) if total_contract_value else 0

    # Single contract concentration
    largest_contract = max((a.get("amount") or 0) for a in awards) if awards else 0
    top_contract_concentration = (largest_contract / total_contract_value * 100) if total_contract_value else 0

    # Risk assessment
    if top_agency_concentration > 50 or top_contract_concentration > 30:
        risk = "High"
    elif top_agency_concentration > 30 or top_contract_concentration > 20:
        risk = "Medium"
    else:
        risk = "Low"

    return {
        "total_contract_value": total_contract_value,
        "top_agency_concentration": round(top_agency_concentration, 1),
        "top_contract_concentration": round(top_contract_concentration, 1),
        "concentration_risk": risk,
        "government_revenue_pct": round(total_contract_value / total_revenue * 100, 1) if total_revenue else None
    }


def _calculate_award_probability(
    company_metrics: Dict[str, Any],
    opportunity: Dict[str, Any],
    industry_context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Estimate probability of winning a specific contract opportunity.

    Uses factors like:
    - Historical presence in the agency
    - Award size relative to typical wins
    - NAICS code match
    - Set-aside status
    """
    base_probability = 0.15  # Base win rate for competitive contracts

    adjustments = []

    # Agency familiarity bonus
    agency = opportunity.get("agency", "")
    if agency in company_metrics.get("agencies_served", []):
        base_probability += 0.10
        adjustments.append(("Incumbent agency relationship", "+10%"))

    # Contract size alignment
    avg_award = company_metrics.get("avg_award_size", 0)
    if avg_award > 0:
        # Estimate opportunity value (if not provided, assume medium)
        estimated_value = 10_000_000  # Default assumption
        size_ratio = estimated_value / avg_award if avg_award else 1

        if 0.5 <= size_ratio <= 2:
            base_probability += 0.05
            adjustments.append(("Contract size in sweet spot", "+5%"))
        elif size_ratio > 5:
            base_probability -= 0.05
            adjustments.append(("Contract larger than typical", "-5%"))

    # Historical success rate (if available)
    total_awards = company_metrics.get("total_awards", 0)
    if total_awards > 20:
        base_probability += 0.05
        adjustments.append(("Strong federal contract history", "+5%"))
    elif total_awards > 10:
        base_probability += 0.02
        adjustments.append(("Moderate federal contract history", "+2%"))

    # Set-aside considerations
    set_aside = opportunity.get("set_aside", "")
    if set_aside and "small business" in set_aside.lower():
        base_probability -= 0.10
        adjustments.append(("Small business set-aside (assuming large company)", "-10%"))

    # Clamp probability
    final_probability = max(0.01, min(0.90, base_probability))

    confidence = "Low"
    if company_metrics.get("total_awards", 0) > 10:
        confidence = "Medium"
    if company_metrics.get("total_awards", 0) > 30:
        confidence = "High"

    return {
        "probability": round(final_probability, 2),
        "probability_pct": f"{final_probability * 100:.0f}%",
        "confidence": confidence,
        "adjustments": adjustments,
        "methodology": "Historical win pattern analysis with agency/size adjustments"
    }


def analyze_contract_probability(
    company_name: str,
    ticker: str = "",
    naics_codes: List[str] = None,
    keywords: List[str] = None,
    total_revenue: float = None,
) -> Dict[str, Any]:
    """
    Comprehensive contract probability analysis.

    Args:
        company_name: Company name for contract lookup
        ticker: Stock ticker (for additional context)
        naics_codes: NAICS codes relevant to the company
        keywords: Keywords for opportunity search
        total_revenue: Total annual revenue for concentration calculations

    Returns:
        Complete contract probability analysis
    """
    logger.info("Starting contract probability analysis for %s", company_name)

    # Fetch historical awards
    current_fy = datetime.now().year if datetime.now().month >= 10 else datetime.now().year - 1
    awards = _fetch_usaspending_awards(company_name, fiscal_year=current_fy, limit=200)

    # Calculate win rate metrics
    win_metrics = _calculate_win_rate(awards, company_name)

    # Identify recompetes
    recompetes = _identify_recompetes(awards, months_ahead=18)

    # Concentration risk
    concentration = _analyze_concentration_risk(awards, total_revenue)

    # Fetch upcoming opportunities
    search_keywords = keywords or [company_name.split()[0]]  # Use first word of company name
    opportunities = _fetch_sam_opportunities(search_keywords, naics_codes, limit=30)

    # Score opportunities
    scored_opportunities = []
    for opp in opportunities[:10]:  # Top 10 opportunities
        prob = _calculate_award_probability(win_metrics, opp)
        scored_opportunities.append({
            **opp,
            "win_probability": prob
        })

    # Sort by probability
    scored_opportunities.sort(
        key=lambda x: x.get("win_probability", {}).get("probability", 0),
        reverse=True
    )

    # Calculate aggregate metrics
    total_opportunity_value = sum(
        10_000_000  # Estimate per opportunity
        for _ in scored_opportunities
    )

    weighted_probability = sum(
        opp.get("win_probability", {}).get("probability", 0)
        for opp in scored_opportunities
    ) / len(scored_opportunities) if scored_opportunities else 0

    # Recompete risk summary
    high_risk_recompetes = [r for r in recompetes if r.get("recompete_risk") == "High"]
    recompete_value_at_risk = sum(r.get("amount") or 0 for r in high_risk_recompetes)

    return {
        "company": company_name,
        "ticker": ticker,
        "analysis_date": datetime.utcnow().isoformat() + "Z",

        "historical_performance": {
            "total_awards_5yr": win_metrics["total_awards"],
            "total_value_5yr": win_metrics["total_value"],
            "avg_award_size": win_metrics["avg_award_size"],
            "agencies_served": win_metrics["agencies_served"],
        },

        "concentration_risk": concentration,

        "recompete_pipeline": {
            "total_recompetes_18mo": len(recompetes),
            "high_risk_count": len(high_risk_recompetes),
            "value_at_risk": recompete_value_at_risk,
            "upcoming_recompetes": recompetes[:10],
        },

        "opportunity_pipeline": {
            "opportunities_identified": len(scored_opportunities),
            "total_estimated_value": total_opportunity_value,
            "weighted_avg_win_probability": round(weighted_probability, 2),
            "top_opportunities": scored_opportunities[:5],
        },

        "key_insights": _generate_contract_insights(
            win_metrics, concentration, recompetes, scored_opportunities
        ),
    }


def _generate_contract_insights(
    win_metrics: Dict[str, Any],
    concentration: Dict[str, Any],
    recompetes: List[Dict[str, Any]],
    opportunities: List[Dict[str, Any]]
) -> List[str]:
    """Generate human-readable insights from contract analysis."""
    insights = []

    # Historical performance
    total_awards = win_metrics.get("total_awards", 0)
    total_value = win_metrics.get("total_value", 0)

    if total_awards > 0:
        insights.append(
            f"Company has won {total_awards} federal contracts worth "
            f"${total_value/1e9:.1f}B over the past 5 years."
        )
    else:
        insights.append("Limited federal contracting history identified.")

    # Concentration risk
    risk = concentration.get("concentration_risk", "Unknown")
    if risk == "High":
        insights.append(
            f"HIGH concentration risk: {concentration.get('top_agency_concentration', 0):.0f}% "
            f"of contract revenue from single agency."
        )
    elif risk == "Medium":
        insights.append("Moderate concentration risk across government agencies.")
    else:
        insights.append("Diversified government customer base reduces concentration risk.")

    # Recompete pipeline
    high_risk = [r for r in recompetes if r.get("recompete_risk") == "High"]
    if high_risk:
        total_risk_value = sum(r.get("amount") or 0 for r in high_risk)
        insights.append(
            f"{len(high_risk)} contracts worth ${total_risk_value/1e6:.0f}M "
            f"coming up for recompete within 6 months."
        )

    # Opportunities
    if opportunities:
        avg_prob = sum(
            o.get("win_probability", {}).get("probability", 0)
            for o in opportunities
        ) / len(opportunities)
        insights.append(
            f"{len(opportunities)} relevant contract opportunities identified "
            f"with average {avg_prob*100:.0f}% estimated win probability."
        )

    return insights


def render_contract_probability_markdown(analysis: Dict[str, Any]) -> List[str]:
    """Render contract probability analysis as markdown."""
    lines = ["## Government Contract Analysis", ""]

    hist = analysis.get("historical_performance", {})
    conc = analysis.get("concentration_risk", {})
    recomp = analysis.get("recompete_pipeline", {})
    opps = analysis.get("opportunity_pipeline", {})

    # Overview
    lines.append("### Federal Contracting Overview")
    lines.append("")

    total_awards = hist.get("total_awards_5yr", 0)
    total_value = hist.get("total_value_5yr", 0)

    if total_awards > 0:
        lines.append(
            f"Over the past 5 fiscal years, the company has been awarded "
            f"**{total_awards} federal contracts** totaling **${total_value/1e9:.2f}B**."
        )
        lines.append(
            f"Average contract size: ${hist.get('avg_award_size', 0)/1e6:.1f}M"
        )
        lines.append("")

        agencies = hist.get("agencies_served", [])
        if agencies:
            lines.append("**Key Federal Customers:**")
            for agency in agencies[:5]:
                lines.append(f"- {agency}")
            lines.append("")
    else:
        lines.append("No significant federal contracting activity identified in USASpending.gov data.")
        lines.append("")

    # Concentration Risk
    lines.append("### Concentration Risk Assessment")
    lines.append("")

    risk_level = conc.get("concentration_risk", "Unknown")
    risk_emoji = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(risk_level, "⚪")

    lines.append(f"**Overall Risk Level:** {risk_emoji} {risk_level}")
    lines.append("")
    lines.append(f"- Top agency concentration: {conc.get('top_agency_concentration', 0):.1f}%")
    lines.append(f"- Largest single contract: {conc.get('top_contract_concentration', 0):.1f}% of portfolio")

    if conc.get("government_revenue_pct"):
        lines.append(f"- Government revenue as % of total: {conc.get('government_revenue_pct'):.1f}%")
    lines.append("")

    # Recompete Pipeline
    lines.append("### Contract Recompete Pipeline (18 months)")
    lines.append("")

    upcoming = recomp.get("upcoming_recompetes", [])
    if upcoming:
        lines.append(
            f"**{recomp.get('total_recompetes_18mo', 0)} contracts** coming up for recompete, "
            f"with **{recomp.get('high_risk_count', 0)} high-risk** (within 6 months)."
        )
        lines.append("")

        lines.append("| Contract | Agency | Amount | Recompete Timeline | Risk |")
        lines.append("|----------|--------|--------|-------------------|------|")

        for contract in upcoming[:7]:
            award_id = (contract.get("award_id") or "N/A")[:20]
            agency = (contract.get("agency") or "Unknown")[:25]
            amount = contract.get("amount") or 0
            months = contract.get("months_until_recompete", "?")
            risk = contract.get("recompete_risk", "Unknown")
            risk_icon = {"High": "🔴", "Medium": "🟡", "Low": "🟢"}.get(risk, "")

            lines.append(
                f"| {award_id} | {agency} | ${amount/1e6:.1f}M | {months} months | {risk_icon} {risk} |"
            )
        lines.append("")
    else:
        lines.append("No imminent recompete deadlines identified.")
        lines.append("")

    # Opportunity Pipeline
    lines.append("### Contract Opportunity Pipeline")
    lines.append("")

    top_opps = opps.get("top_opportunities", [])
    if top_opps:
        lines.append(
            f"**{opps.get('opportunities_identified', 0)} relevant opportunities** identified "
            f"with weighted average win probability of **{opps.get('weighted_avg_win_probability', 0)*100:.0f}%**."
        )
        lines.append("")

        for opp in top_opps[:5]:
            prob = opp.get("win_probability", {})
            lines.append(f"**{opp.get('title', 'Opportunity')[:60]}**")
            lines.append(f"- Agency: {opp.get('agency', 'Unknown')}")
            lines.append(f"- Type: {opp.get('type', 'Unknown')}")
            lines.append(f"- Win Probability: {prob.get('probability_pct', 'N/A')} ({prob.get('confidence', 'Low')} confidence)")
            lines.append(f"- Response Deadline: {opp.get('response_deadline', 'TBD')}")
            if opp.get("url"):
                lines.append(f"- [View on SAM.gov]({opp.get('url')})")
            lines.append("")
    else:
        lines.append("No open contract opportunities matching company profile currently identified.")
        lines.append("")

    # Key Insights
    insights = analysis.get("key_insights", [])
    if insights:
        lines.append("### Key Contract Insights")
        lines.append("")
        for insight in insights:
            lines.append(f"- {insight}")
        lines.append("")

    lines.append("*Data sources: USASpending.gov, SAM.gov*")
    lines.append("")

    return lines
