"""
Risk Register Generator
────────────────────────────────────────────────────────────────────────────
Generate comprehensive risk registers for deep intelligence reports:
  - Strategic risks (market position, competition, technology shifts)
  - Operational risks (supply chain, key person, concentration)
  - Financial risks (leverage, liquidity, currency, valuation)
  - Legal/Compliance risks (litigation, regulatory, sanctions)
  - ESG risks (environmental, social, governance)

Risk registers are CRITICAL for:
  - Investment due diligence
  - Board risk oversight
  - Regulatory compliance
  - Insurance underwriting

Usage:
    from app.connectors.risk_register_connector import (
        generate_risk_register,
        assess_risk_profile,
    )
    risks = generate_risk_register("NVDA", all_intelligence_data)
"""
import os
import re
import time
import logging
import requests
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from collections import defaultdict
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class RiskItem:
    """Individual risk item in the register."""
    id: str
    category: str  # Strategic, Operational, Financial, Legal, ESG
    subcategory: str
    title: str
    description: str
    likelihood: str  # Low, Medium, High, Critical
    impact: str  # Low, Medium, High, Critical
    risk_score: int  # 1-25 (likelihood * impact)
    mitigants: List[str] = field(default_factory=list)
    indicators: List[str] = field(default_factory=list)  # Early warning signs
    data_source: str = ""
    last_updated: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Risk scoring matrix
LIKELIHOOD_SCORES = {"Low": 1, "Medium": 2, "High": 3, "Very High": 4, "Critical": 5}
IMPACT_SCORES = {"Low": 1, "Medium": 2, "High": 3, "Very High": 4, "Critical": 5}


def _calculate_risk_score(likelihood: str, impact: str) -> int:
    """Calculate risk score from likelihood and impact."""
    l_score = LIKELIHOOD_SCORES.get(likelihood, 2)
    i_score = IMPACT_SCORES.get(impact, 2)
    return l_score * i_score


def _risk_level_from_score(score: int) -> str:
    """Convert numeric score to risk level."""
    if score >= 20:
        return "Critical"
    elif score >= 12:
        return "High"
    elif score >= 6:
        return "Medium"
    else:
        return "Low"


def extract_strategic_risks(
    entity_name: str,
    financial_data: Dict[str, Any] = None,
    market_data: Dict[str, Any] = None,
    competitive_data: Dict[str, Any] = None,
) -> List[RiskItem]:
    """
    Extract strategic risks from available data.

    Strategic risks include:
    - Market position threats
    - Competitive pressure
    - Technology disruption
    - Customer concentration
    - Geographic concentration
    """
    risks = []
    financial_data = financial_data or {}
    market_data = market_data or {}
    competitive_data = competitive_data or {}

    # Customer concentration risk
    customer_concentration = financial_data.get("customer_concentration", {})
    top_customer_pct = customer_concentration.get("top_customer_pct", 0)
    if top_customer_pct > 30:
        likelihood = "High" if top_customer_pct > 50 else "Medium"
        risks.append(RiskItem(
            id="STR-001",
            category="Strategic",
            subcategory="Customer Concentration",
            title="High Customer Concentration",
            description=f"Top customer represents {top_customer_pct:.0f}% of revenue, creating dependency risk",
            likelihood=likelihood,
            impact="High",
            risk_score=_calculate_risk_score(likelihood, "High"),
            mitigants=["Diversify customer base", "Long-term contracts", "Strategic partnerships"],
            indicators=["Contract renewal discussions", "Customer financial health", "Order volume trends"],
            data_source="Financial Statements",
        ))

    # Geographic concentration risk
    geo_concentration = financial_data.get("geographic_concentration", {})
    top_region_pct = geo_concentration.get("top_region_pct", 0)
    if top_region_pct > 50:
        risks.append(RiskItem(
            id="STR-002",
            category="Strategic",
            subcategory="Geographic Concentration",
            title="Geographic Revenue Concentration",
            description=f"Geographic concentration of {top_region_pct:.0f}% in single region",
            likelihood="Medium",
            impact="Medium",
            risk_score=_calculate_risk_score("Medium", "Medium"),
            mitigants=["Market expansion initiatives", "Regional diversification"],
            indicators=["Regional economic indicators", "Local regulatory changes"],
            data_source="10-K Geographic Disclosure",
        ))

    # Technology disruption risk (standard for tech companies)
    risks.append(RiskItem(
        id="STR-003",
        category="Strategic",
        subcategory="Technology Disruption",
        title="Technology Obsolescence Risk",
        description="Rapid technology evolution could render current products less competitive",
        likelihood="Medium",
        impact="High",
        risk_score=_calculate_risk_score("Medium", "High"),
        mitigants=["R&D investment", "Strategic acquisitions", "Partnership ecosystem"],
        indicators=["Competitor product launches", "Patent filings", "Research publications"],
        data_source="Industry Analysis",
    ))

    # Market position risk
    market_share = market_data.get("market_share_pct", 0)
    if market_share > 0:
        if market_share > 60:
            # Dominant position - antitrust risk
            risks.append(RiskItem(
                id="STR-004",
                category="Strategic",
                subcategory="Market Position",
                title="Dominant Market Position - Antitrust Exposure",
                description=f"Market share of {market_share:.0f}% may attract regulatory scrutiny",
                likelihood="Medium",
                impact="High",
                risk_score=_calculate_risk_score("Medium", "High"),
                mitigants=["Compliance programs", "Fair dealing practices", "Legal monitoring"],
                indicators=["Regulatory inquiries", "Competitor complaints", "Political commentary"],
                data_source="Market Analysis",
            ))
        elif market_share < 20:
            # Smaller player - competitive pressure
            risks.append(RiskItem(
                id="STR-004",
                category="Strategic",
                subcategory="Competitive Position",
                title="Competitive Pressure from Market Leaders",
                description=f"Market share of {market_share:.0f}% creates vulnerability to larger competitors",
                likelihood="Medium",
                impact="Medium",
                risk_score=_calculate_risk_score("Medium", "Medium"),
                mitigants=["Niche focus", "Innovation leadership", "Cost efficiency"],
                indicators=["Price competition", "Customer churn", "Market share trends"],
                data_source="Market Analysis",
            ))

    return risks


def extract_operational_risks(
    entity_name: str,
    personnel_data: Dict[str, Any] = None,
    supply_chain_data: Dict[str, Any] = None,
    contract_data: Dict[str, Any] = None,
) -> List[RiskItem]:
    """
    Extract operational risks from available data.

    Operational risks include:
    - Key person dependency
    - Supply chain disruption
    - Cybersecurity
    - Business continuity
    """
    risks = []
    personnel_data = personnel_data or {}
    supply_chain_data = supply_chain_data or {}
    contract_data = contract_data or {}

    # Key person risk
    executives = personnel_data.get("executive_dossiers", [])
    ceo_tenure = 0
    founder_ceo = False

    for exec in executives:
        title = exec.get("title", "").lower()
        if "ceo" in title or "chief executive" in title:
            ceo_tenure = exec.get("tenure_years", 0)
            founder_ceo = "founder" in exec.get("background", "").lower()
            break

    if founder_ceo or ceo_tenure > 10:
        risks.append(RiskItem(
            id="OPS-001",
            category="Operational",
            subcategory="Key Person",
            title="Key Executive Dependency",
            description="Strong association with founder/long-tenured CEO creates succession risk",
            likelihood="Medium",
            impact="High",
            risk_score=_calculate_risk_score("Medium", "High"),
            mitigants=["Succession planning", "Management depth", "Knowledge transfer"],
            indicators=["Executive health", "Retirement announcements", "Leadership changes"],
            data_source="Personnel Analysis",
        ))

    # Supply chain concentration
    supplier_concentration = supply_chain_data.get("top_supplier_pct", 0)
    if supplier_concentration > 30:
        risks.append(RiskItem(
            id="OPS-002",
            category="Operational",
            subcategory="Supply Chain",
            title="Supply Chain Concentration Risk",
            description=f"Critical supplier represents {supplier_concentration:.0f}% of supply",
            likelihood="Medium",
            impact="High",
            risk_score=_calculate_risk_score("Medium", "High"),
            mitigants=["Supplier diversification", "Strategic inventory", "Alternative sourcing"],
            indicators=["Supplier financial health", "Geopolitical tensions", "Logistics disruptions"],
            data_source="10-K Risk Factors",
        ))

    # Standard cybersecurity risk
    risks.append(RiskItem(
        id="OPS-003",
        category="Operational",
        subcategory="Cybersecurity",
        title="Cybersecurity and Data Protection Risk",
        description="Potential for data breaches, ransomware, or system compromises",
        likelihood="Medium",
        impact="High",
        risk_score=_calculate_risk_score("Medium", "High"),
        mitigants=["Security infrastructure", "Employee training", "Incident response plans"],
        indicators=["Security audits", "Industry breach reports", "Attempted intrusions"],
        data_source="Standard Assessment",
    ))

    # Government contract dependency (if applicable)
    gov_contract_pct = contract_data.get("government_revenue_pct", 0)
    if gov_contract_pct > 10:
        likelihood = "High" if gov_contract_pct > 30 else "Medium"
        risks.append(RiskItem(
            id="OPS-004",
            category="Operational",
            subcategory="Government Dependency",
            title="Government Contract Dependency",
            description=f"Government contracts represent {gov_contract_pct:.0f}% of revenue",
            likelihood=likelihood,
            impact="Medium",
            risk_score=_calculate_risk_score(likelihood, "Medium"),
            mitigants=["Contract diversification", "Compliance programs", "Bipartisan relationships"],
            indicators=["Budget appropriations", "Contract renewals", "Policy changes"],
            data_source="Contract Analysis",
        ))

    return risks


def extract_financial_risks(
    entity_name: str,
    financial_data: Dict[str, Any] = None,
    valuation_data: Dict[str, Any] = None,
) -> List[RiskItem]:
    """
    Extract financial risks from available data.

    Financial risks include:
    - Leverage/debt
    - Liquidity
    - Currency exposure
    - Valuation
    - Interest rate sensitivity
    """
    risks = []
    financial_data = financial_data or {}
    valuation_data = valuation_data or {}

    # Leverage risk
    debt_to_equity = financial_data.get("debt_to_equity", 0)
    if debt_to_equity > 1.0:
        likelihood = "High" if debt_to_equity > 2.0 else "Medium"
        risks.append(RiskItem(
            id="FIN-001",
            category="Financial",
            subcategory="Leverage",
            title="Elevated Debt Levels",
            description=f"Debt-to-equity ratio of {debt_to_equity:.2f}x indicates leverage risk",
            likelihood=likelihood,
            impact="High",
            risk_score=_calculate_risk_score(likelihood, "High"),
            mitigants=["Debt reduction plan", "Cash flow management", "Refinancing strategy"],
            indicators=["Interest coverage", "Credit rating changes", "Covenant compliance"],
            data_source="Balance Sheet Analysis",
        ))

    # Liquidity risk
    current_ratio = financial_data.get("current_ratio", 0)
    if 0 < current_ratio < 1.5:
        risks.append(RiskItem(
            id="FIN-002",
            category="Financial",
            subcategory="Liquidity",
            title="Liquidity Constraints",
            description=f"Current ratio of {current_ratio:.2f}x below comfortable levels",
            likelihood="Medium",
            impact="Medium",
            risk_score=_calculate_risk_score("Medium", "Medium"),
            mitigants=["Credit facilities", "Working capital optimization", "Cash reserves"],
            indicators=["Days payable/receivable", "Inventory levels", "Credit line utilization"],
            data_source="Balance Sheet Analysis",
        ))

    # Valuation risk
    assessment = valuation_data.get("assessment", "")
    intrinsic = valuation_data.get("intrinsic_price_per_share", 0)
    current = valuation_data.get("current_market_price", 0)

    if "OVERVALUED" in assessment.upper():
        downside_pct = ((intrinsic - current) / current * 100) if current else 0
        risks.append(RiskItem(
            id="FIN-003",
            category="Financial",
            subcategory="Valuation",
            title="Valuation Risk - Trading Above Intrinsic Value",
            description=f"Stock trading {abs(downside_pct):.0f}% above estimated intrinsic value",
            likelihood="High",
            impact="Medium",
            risk_score=_calculate_risk_score("High", "Medium"),
            mitigants=["Fundamental improvement", "Earnings growth", "Multiple contraction awareness"],
            indicators=["Analyst revisions", "Peer multiples", "Growth deceleration"],
            data_source="DCF Valuation",
        ))

    # Currency risk (standard for multinationals)
    international_revenue_pct = financial_data.get("international_revenue_pct", 0)
    if international_revenue_pct > 30:
        risks.append(RiskItem(
            id="FIN-004",
            category="Financial",
            subcategory="Currency",
            title="Foreign Exchange Exposure",
            description=f"{international_revenue_pct:.0f}% international revenue creates FX exposure",
            likelihood="High",
            impact="Medium",
            risk_score=_calculate_risk_score("High", "Medium"),
            mitigants=["Hedging programs", "Natural hedges", "Currency diversification"],
            indicators=["USD strength", "Emerging market volatility", "Hedge effectiveness"],
            data_source="Geographic Disclosure",
        ))

    return risks


def extract_legal_risks(
    entity_name: str,
    litigation_data: Dict[str, Any] = None,
    regulatory_data: Dict[str, Any] = None,
    political_data: Dict[str, Any] = None,
) -> List[RiskItem]:
    """
    Extract legal and compliance risks from available data.

    Legal risks include:
    - Active litigation
    - Regulatory investigations
    - Sanctions exposure
    - IP disputes
    """
    risks = []
    litigation_data = litigation_data or {}
    regulatory_data = regulatory_data or {}
    political_data = political_data or {}

    # Active litigation risk
    total_matters = litigation_data.get("summary", {}).get("total_matters", 0)
    active_matters = litigation_data.get("summary", {}).get("active_matters", 0)

    if active_matters > 5:
        likelihood = "High" if active_matters > 15 else "Medium"
        risks.append(RiskItem(
            id="LEG-001",
            category="Legal",
            subcategory="Litigation",
            title="Material Litigation Exposure",
            description=f"{active_matters} active legal matters may result in adverse outcomes",
            likelihood=likelihood,
            impact="Medium",
            risk_score=_calculate_risk_score(likelihood, "Medium"),
            mitigants=["Legal reserves", "Insurance coverage", "Settlement strategy"],
            indicators=["Case rulings", "Settlement discussions", "New filings"],
            data_source="Litigation Analysis",
        ))

    # SEC enforcement risk
    sec_actions = litigation_data.get("sec_enforcement", {}).get("summary", {}).get("total_actions", 0)
    if sec_actions > 0:
        risks.append(RiskItem(
            id="LEG-002",
            category="Legal",
            subcategory="Regulatory",
            title="SEC Enforcement History",
            description=f"{sec_actions} SEC enforcement action(s) in company history",
            likelihood="Medium" if sec_actions == 1 else "High",
            impact="High",
            risk_score=_calculate_risk_score("Medium" if sec_actions == 1 else "High", "High"),
            mitigants=["Enhanced compliance", "Internal controls", "Board oversight"],
            indicators=["SEC inquiries", "Subpoenas", "Whistleblower activity"],
            data_source="SEC Enforcement Database",
        ))

    # Political/lobbying risk
    lobbying_spend = political_data.get("lobbying_summary", {}).get("total_spend", 0)
    if lobbying_spend > 10_000_000:  # >$10M lobbying
        risks.append(RiskItem(
            id="LEG-003",
            category="Legal",
            subcategory="Political",
            title="Political and Lobbying Exposure",
            description=f"Significant lobbying activity (${lobbying_spend / 1e6:.1f}M) creates political risk",
            likelihood="Medium",
            impact="Medium",
            risk_score=_calculate_risk_score("Medium", "Medium"),
            mitigants=["Bipartisan engagement", "Transparent disclosure", "Issue diversification"],
            indicators=["Political climate", "Policy changes", "Media scrutiny"],
            data_source="OpenSecrets",
        ))

    # Patent/IP risk
    patent_cases = len(litigation_data.get("federal_cases", {}).get("by_type", {}).get("patent", []))
    if patent_cases > 3:
        risks.append(RiskItem(
            id="LEG-004",
            category="Legal",
            subcategory="Intellectual Property",
            title="Patent Litigation Exposure",
            description=f"{patent_cases} patent-related cases create IP risk",
            likelihood="Medium",
            impact="High",
            risk_score=_calculate_risk_score("Medium", "High"),
            mitigants=["Patent portfolio", "Licensing agreements", "Design-around capability"],
            indicators=["New patent claims", "ITC actions", "PTAB proceedings"],
            data_source="Court Records",
        ))

    return risks


def extract_esg_risks(
    entity_name: str,
    governance_data: Dict[str, Any] = None,
    environmental_data: Dict[str, Any] = None,
) -> List[RiskItem]:
    """
    Extract ESG (Environmental, Social, Governance) risks.
    """
    risks = []
    governance_data = governance_data or {}

    # Board independence
    board = governance_data.get("board_composition", {})
    director_count = len(board.get("directors", []))

    if director_count > 0:
        # Standard governance risk assessment
        risks.append(RiskItem(
            id="ESG-001",
            category="ESG",
            subcategory="Governance",
            title="Board Governance Structure",
            description="Standard governance risk related to board composition and oversight",
            likelihood="Low",
            impact="Medium",
            risk_score=_calculate_risk_score("Low", "Medium"),
            mitigants=["Independent directors", "Committee structure", "Shareholder engagement"],
            indicators=["Proxy advisor ratings", "Shareholder votes", "Board refreshment"],
            data_source="Proxy Statement",
        ))

    # Environmental (standard for all companies)
    risks.append(RiskItem(
        id="ESG-002",
        category="ESG",
        subcategory="Environmental",
        title="Climate and Environmental Transition Risk",
        description="Exposure to climate regulation and environmental compliance requirements",
        likelihood="Medium",
        impact="Medium",
        risk_score=_calculate_risk_score("Medium", "Medium"),
        mitigants=["Sustainability initiatives", "Emissions reduction", "ESG reporting"],
        indicators=["Carbon pricing", "Regulatory changes", "Physical climate events"],
        data_source="Standard Assessment",
    ))

    # Executive compensation. The approval percentage is None when it could not
    # be read from the proxy or the Item 5.07 8-K, which is not the same as a
    # low vote: raising a governance risk on an unretrieved value would invent
    # a finding for every issuer whose proxy does not parse.
    say_on_pay = governance_data.get("say_on_pay", {})
    approval_pct = say_on_pay.get("approval_pct")
    if approval_pct is not None and approval_pct < 80:
        risks.append(RiskItem(
            id="ESG-003",
            category="ESG",
            subcategory="Governance",
            title="Executive Compensation Controversy",
            description=f"Say-on-pay approval of {approval_pct:.0f}% indicates shareholder concerns",
            likelihood="Medium",
            impact="Medium",
            risk_score=_calculate_risk_score("Medium", "Medium"),
            mitigants=["Compensation committee review", "Shareholder engagement", "Pay-for-performance alignment"],
            indicators=["Proxy advisor recommendations", "Shareholder proposals", "Media coverage"],
            data_source="Proxy Statement",
        ))

    return risks


def generate_risk_register(
    entity_name: str,
    ticker: str = "",
    all_data: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Generate comprehensive risk register from all available intelligence.

    Args:
        entity_name: Company name
        ticker: Stock ticker
        all_data: Dictionary containing all intelligence data

    Returns:
        Complete risk register with categorized risks.
    """
    all_data = all_data or {}

    result = {
        "entity_name": entity_name,
        "ticker": ticker,
        "risks": [],
        "by_category": defaultdict(list),
        "summary": {
            "total_risks": 0,
            "critical_risks": 0,
            "high_risks": 0,
            "medium_risks": 0,
            "low_risks": 0,
            "overall_risk_profile": "UNKNOWN",
        },
        "risk_matrix": [],
        "top_risks": [],
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    all_risks: List[RiskItem] = []

    # Extract risks from each domain
    strategic_risks = extract_strategic_risks(
        entity_name,
        financial_data=all_data.get("financial_data", {}),
        market_data=all_data.get("market_data", {}),
        competitive_data=all_data.get("competitive_data", {}),
    )
    all_risks.extend(strategic_risks)

    operational_risks = extract_operational_risks(
        entity_name,
        personnel_data=all_data.get("personnel_intelligence", {}),
        supply_chain_data=all_data.get("supply_chain_data", {}),
        contract_data=all_data.get("contract_intelligence", {}),
    )
    all_risks.extend(operational_risks)

    financial_risks = extract_financial_risks(
        entity_name,
        financial_data=all_data.get("financial_data", {}),
        valuation_data=all_data.get("valuation_data", {}),
    )
    all_risks.extend(financial_risks)

    legal_risks = extract_legal_risks(
        entity_name,
        litigation_data=all_data.get("litigation_intelligence", {}),
        regulatory_data=all_data.get("regulatory_data", {}),
        political_data=all_data.get("political_intelligence", {}),
    )
    all_risks.extend(legal_risks)

    esg_risks = extract_esg_risks(
        entity_name,
        governance_data=all_data.get("proxy_intelligence", {}),
        environmental_data=all_data.get("environmental_data", {}),
    )
    all_risks.extend(esg_risks)

    # Update timestamps
    now = datetime.utcnow().isoformat() + "Z"
    for risk in all_risks:
        risk.last_updated = now

    # Sort by risk score descending
    all_risks.sort(key=lambda r: r.risk_score, reverse=True)

    # Convert to dicts and organize
    result["risks"] = [r.to_dict() for r in all_risks]

    for risk in all_risks:
        result["by_category"][risk.category].append(risk.to_dict())

    # Calculate summary statistics
    result["summary"]["total_risks"] = len(all_risks)

    for risk in all_risks:
        level = _risk_level_from_score(risk.risk_score)
        if level == "Critical":
            result["summary"]["critical_risks"] += 1
        elif level == "High":
            result["summary"]["high_risks"] += 1
        elif level == "Medium":
            result["summary"]["medium_risks"] += 1
        else:
            result["summary"]["low_risks"] += 1

    # Determine overall risk profile
    critical = result["summary"]["critical_risks"]
    high = result["summary"]["high_risks"]

    if critical >= 2:
        result["summary"]["overall_risk_profile"] = "CRITICAL"
    elif critical >= 1 or high >= 4:
        result["summary"]["overall_risk_profile"] = "HIGH"
    elif high >= 2:
        result["summary"]["overall_risk_profile"] = "ELEVATED"
    else:
        result["summary"]["overall_risk_profile"] = "MODERATE"

    # Top 5 risks
    result["top_risks"] = [r.to_dict() for r in all_risks[:5]]

    # Risk matrix for visualization
    result["risk_matrix"] = {
        "categories": list(result["by_category"].keys()),
        "counts_by_category": {k: len(v) for k, v in result["by_category"].items()},
        "scores_by_category": {
            k: sum(r["risk_score"] for r in v) / len(v) if v else 0
            for k, v in result["by_category"].items()
        },
    }

    return result


def generate_risk_register_markdown(register: Dict[str, Any]) -> str:
    """
    Generate markdown-formatted risk register for reports.

    Args:
        register: Output from generate_risk_register

    Returns:
        Markdown string.
    """
    lines = []
    entity = register.get("entity_name", "")
    ticker = register.get("ticker", "")

    lines.append(f"## Risk Register: {entity}" + (f" ({ticker})" if ticker else ""))
    lines.append("")

    # Summary
    summary = register.get("summary", {})
    profile = summary.get("overall_risk_profile", "UNKNOWN")
    lines.append(f"**Overall Risk Profile:** {profile}")
    lines.append(f"**Total Risks Identified:** {summary.get('total_risks', 0)}")
    lines.append("")

    lines.append("| Level | Count |")
    lines.append("|-------|-------|")
    lines.append(f"| Critical | {summary.get('critical_risks', 0)} |")
    lines.append(f"| High | {summary.get('high_risks', 0)} |")
    lines.append(f"| Medium | {summary.get('medium_risks', 0)} |")
    lines.append(f"| Low | {summary.get('low_risks', 0)} |")
    lines.append("")

    # Top Risks
    top_risks = register.get("top_risks", [])
    if top_risks:
        lines.append("### Top Risks")
        lines.append("")

        for i, risk in enumerate(top_risks, 1):
            level = _risk_level_from_score(risk.get("risk_score", 0))
            lines.append(f"**{i}. {risk.get('title')}** [{level}]")
            lines.append(f"- Category: {risk.get('category')} / {risk.get('subcategory')}")
            lines.append(f"- {risk.get('description')}")
            lines.append(f"- Likelihood: {risk.get('likelihood')} | Impact: {risk.get('impact')}")
            if risk.get("mitigants"):
                lines.append(f"- Mitigants: {', '.join(risk.get('mitigants', []))}")
            lines.append("")

    # By Category
    lines.append("### Risks by Category")
    lines.append("")

    for category, risks in register.get("by_category", {}).items():
        lines.append(f"#### {category} ({len(risks)} risks)")
        lines.append("")

        for risk in risks:
            level = _risk_level_from_score(risk.get("risk_score", 0))
            lines.append(f"- **{risk.get('title')}** [{level}]: {risk.get('description')}")

        lines.append("")

    return "\n".join(lines)


# ── Convenience Exports ──────────────────────────────────────────────────────

def build_risk_register(entity: str, ticker: str = "", data: Dict = None) -> Dict[str, Any]:
    """Generate risk register."""
    return generate_risk_register(entity, ticker, data)


def risk_register_to_markdown(register: Dict[str, Any]) -> str:
    """Convert risk register to markdown."""
    return generate_risk_register_markdown(register)


def assess_profile(entity: str, ticker: str = "", data: Dict = None) -> Dict[str, Any]:
    """Assess risk profile and return summary."""
    register = generate_risk_register(entity, ticker, data)
    return {
        "entity": entity,
        "ticker": ticker,
        "profile": register.get("summary", {}).get("overall_risk_profile", "UNKNOWN"),
        "top_risks": register.get("top_risks", []),
        "summary": register.get("summary", {}),
    }
