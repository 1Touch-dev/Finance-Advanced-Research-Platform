"""
Enhanced Narrative Service - Deep AI Analysis for Intelligence Reports.

This service generates advanced analytical sections for intelligence reports:
- Executive Summary (1-page brief)
- Investment Thesis (Buy/Hold/Sell with bull/bear cases)
- SWOT Analysis (with evidence citations)
- Risk Matrix (severity/likelihood ratings)
- Financial Health Summary (key metrics)
- Competitive Analysis (market position, moats)
"""

import os
import json
import logging
import requests
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from app.templates.report_prompts import (
    get_executive_summary_prompt,
    get_investment_thesis_prompt,
    get_swot_analysis_prompt,
    get_risk_matrix_prompt,
    get_financial_health_prompt,
    get_competitive_analysis_prompt,
)

logger = logging.getLogger(__name__)

# OpenAI configuration
_OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
_OPENAI_BASE = "https://api.openai.com/v1/chat/completions"
_MODEL = "gpt-4o-mini"
_TIMEOUT = 60  # Extended timeout for complex analysis


class RecommendationType(str, Enum):
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    NOT_RATED = "NOT_RATED"


class ConvictionLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class InvestmentThesis:
    """Structured investment thesis data."""
    recommendation: RecommendationType
    conviction: ConvictionLevel
    summary: str
    bull_case: List[Dict[str, Any]]
    bear_case: List[Dict[str, Any]]
    fair_value: Optional[float]
    current_price: Optional[float]
    upside_pct: Optional[float]
    key_milestones: List[str]
    raw_narrative: str


@dataclass
class SWOTAnalysis:
    """Structured SWOT analysis data."""
    strengths: List[Dict[str, Any]]
    weaknesses: List[Dict[str, Any]]
    opportunities: List[Dict[str, Any]]
    threats: List[Dict[str, Any]]
    synthesis: str
    raw_narrative: str


@dataclass
class RiskMatrix:
    """Structured risk matrix data."""
    risks: List[Dict[str, Any]]
    critical_risks: List[str]
    high_risks: List[str]
    medium_risks: List[str]
    low_risks: List[str]
    overall_score: float
    top_priority_risks: List[Dict[str, Any]]
    raw_narrative: str


@dataclass
class FinancialHealth:
    """Structured financial health data."""
    metrics: Dict[str, Any]
    profitability_assessment: str
    liquidity_assessment: str
    growth_assessment: str
    technical_position: Optional[str]
    grade: str
    grade_rationale: str
    raw_narrative: str


# ============================================================================
# CORE AI CALL FUNCTION
# ============================================================================

def _call_openai(
    prompt: str,
    system_instruction: str = "You are a senior intelligence analyst.",
    temperature: float = 0.3,
    max_tokens: int = 4000,
) -> str:
    """
    Call OpenAI API with the given prompt.

    Args:
        prompt: User prompt to send
        system_instruction: System instruction for the model
        temperature: Sampling temperature (lower = more deterministic)
        max_tokens: Maximum tokens in response

    Returns:
        Model response text
    """
    if not _OPENAI_KEY:
        logger.warning("OPENAI_API_KEY not configured")
        return "[Enhanced narrative unavailable — OPENAI_API_KEY not configured]"

    try:
        resp = requests.post(
            _OPENAI_BASE,
            headers={
                "Authorization": f"Bearer {_OPENAI_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": _MODEL,
                "messages": [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt},
                ],
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.Timeout:
        logger.error("OpenAI API timeout")
        return "[Analysis timeout — please try again]"
    except requests.exceptions.RequestException as e:
        logger.error(f"OpenAI API error: {e}")
        return f"[Analysis error: {str(e)}]"
    except Exception as e:
        logger.error(f"Unexpected error calling OpenAI: {e}")
        return f"[Unexpected error: {str(e)}]"


# ============================================================================
# EXECUTIVE SUMMARY GENERATION
# ============================================================================

def generate_executive_summary(
    entity_name: str,
    entity_type: str,
    report_data: Dict[str, Any],
    financial_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate a 1-page executive summary with key metrics, risks, and opportunities.

    Args:
        entity_name: Name of the entity
        entity_type: Type of entity (org, person)
        report_data: Existing report sections and claims
        financial_data: Optional financial metrics from yfinance

    Returns:
        Dict with narrative text and structured data
    """
    prompt = get_executive_summary_prompt(
        entity_name=entity_name,
        entity_type=entity_type,
        report_data=report_data,
        financial_data=financial_data,
    )

    system_instruction = """You are a senior intelligence analyst at a top-tier research firm.
You write concise, actionable executive summaries suitable for C-suite executives.
Always cite sources and tag claims with [DOCUMENTED], [REPORTED], or [ANALYTICAL]."""

    narrative = _call_openai(prompt, system_instruction)

    return {
        "section_name": "Executive Summary",
        "narrative": narrative,
        "metadata": {
            "entity_name": entity_name,
            "entity_type": entity_type,
            "model": _MODEL,
            "analysis_type": "executive_summary",
        },
    }


# ============================================================================
# INVESTMENT THESIS GENERATION
# ============================================================================

def generate_investment_thesis(
    entity_name: str,
    ticker: Optional[str],
    report_data: Dict[str, Any],
    financial_data: Optional[Dict[str, Any]] = None,
    valuation_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate investment thesis with Buy/Hold/Sell recommendation.

    Args:
        entity_name: Name of the entity
        ticker: Stock ticker symbol
        report_data: Existing report sections and claims
        financial_data: Optional financial metrics from yfinance
        valuation_data: Optional DCF valuation data

    Returns:
        Dict with narrative text and structured investment thesis
    """
    prompt = get_investment_thesis_prompt(
        entity_name=entity_name,
        ticker=ticker,
        report_data=report_data,
        financial_data=financial_data,
        valuation_data=valuation_data,
    )

    system_instruction = """You are a senior equity research analyst at Goldman Sachs.
You write rigorous, data-driven investment recommendations.
Always provide specific price targets and quantified bull/bear cases.
Tag all claims with [DOCUMENTED], [REPORTED], or [ANALYTICAL]."""

    narrative = _call_openai(prompt, system_instruction, temperature=0.2)

    # Parse recommendation from narrative
    recommendation = _extract_recommendation(narrative)

    return {
        "section_name": "Investment Thesis",
        "narrative": narrative,
        "recommendation": recommendation.get("recommendation", "NOT_RATED"),
        "conviction": recommendation.get("conviction", "MEDIUM"),
        "bull_case": recommendation.get("bull_case", []),
        "bear_case": recommendation.get("bear_case", []),
        "fair_value": recommendation.get("fair_value"),
        "upside_pct": recommendation.get("upside_pct"),
        "metadata": {
            "ticker": ticker,
            "model": _MODEL,
            "analysis_type": "investment_thesis",
            "has_valuation_data": valuation_data is not None,
        },
    }


def _extract_recommendation(narrative: str) -> Dict[str, Any]:
    """Extract structured recommendation data from narrative text."""
    result = {
        "recommendation": "NOT_RATED",
        "conviction": "MEDIUM",
        "bull_case": [],
        "bear_case": [],
        "fair_value": None,
        "upside_pct": None,
    }

    text_upper = narrative.upper()

    # Extract recommendation
    if "BUY" in text_upper and "RECOMMENDATION" in text_upper:
        result["recommendation"] = "BUY"
    elif "SELL" in text_upper and "RECOMMENDATION" in text_upper:
        result["recommendation"] = "SELL"
    elif "HOLD" in text_upper and "RECOMMENDATION" in text_upper:
        result["recommendation"] = "HOLD"

    # Extract conviction
    if "HIGH" in text_upper and "CONVICTION" in text_upper:
        result["conviction"] = "HIGH"
    elif "LOW" in text_upper and "CONVICTION" in text_upper:
        result["conviction"] = "LOW"

    return result


# ============================================================================
# SWOT ANALYSIS GENERATION
# ============================================================================

def generate_swot_analysis(
    entity_name: str,
    entity_type: str,
    report_data: Dict[str, Any],
    financial_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate SWOT analysis with evidence citations.

    Args:
        entity_name: Name of the entity
        entity_type: Type of entity
        report_data: Existing report sections
        financial_data: Optional financial data

    Returns:
        Dict with SWOT narrative and structured quadrant data
    """
    prompt = get_swot_analysis_prompt(
        entity_name=entity_name,
        entity_type=entity_type,
        report_data=report_data,
        financial_data=financial_data,
    )

    system_instruction = """You are a strategic consultant at McKinsey & Company.
You provide rigorous, evidence-based SWOT analyses.
Each item must have a clear evidence citation and impact rating.
Tag all claims with [DOCUMENTED], [REPORTED], or [ANALYTICAL]."""

    narrative = _call_openai(prompt, system_instruction)

    # Parse SWOT quadrants from narrative
    swot_data = _parse_swot(narrative)

    return {
        "section_name": "SWOT Analysis",
        "narrative": narrative,
        "strengths": swot_data.get("strengths", []),
        "weaknesses": swot_data.get("weaknesses", []),
        "opportunities": swot_data.get("opportunities", []),
        "threats": swot_data.get("threats", []),
        "synthesis": swot_data.get("synthesis", ""),
        "metadata": {
            "entity_name": entity_name,
            "model": _MODEL,
            "analysis_type": "swot",
        },
    }


def _parse_swot(narrative: str) -> Dict[str, Any]:
    """Parse SWOT quadrants from narrative text.

    Robust to the different shapes the model actually emits: markdown tables,
    bullet lists, numbered lists, and bold/plain headers (``**Strengths**``,
    ``Strengths:``, ``1. Strengths``). Falls back to per-line extraction so the
    grids never render blank when the model wrote prose instead of a table.
    """
    import re as _re
    result = {
        "strengths": [],
        "weaknesses": [],
        "opportunities": [],
        "threats": [],
        "synthesis": "",
    }

    # keyword prefix -> quadrant key
    section_keys = [
        ("strategic synthesis", "synthesis"),
        ("synthesis", "synthesis"),
        ("strength", "strengths"),
        ("weakness", "weaknesses"),
        ("opportunit", "opportunities"),
        ("threat", "threats"),
    ]

    def _detect_section(text_line: str):
        # normalise markdown/formatting chrome around a potential header
        low = text_line.lower().strip().strip("#*_-:•. ").strip()
        for key, val in section_keys:
            if low == key or low.startswith(key):
                # Only treat as a header if it's a short header-ish line, not a
                # full sentence that merely contains the word.
                if len(text_line.strip()) <= 45 or text_line.strip().startswith(("#", "*", "-", "|")):
                    return val
        return None

    def _clean(text: str) -> str:
        text = _re.sub(r'^\[(?:HIGH|MEDIUM|LOW|DOCUMENTED|REPORTED|ANALYTICAL|VERIFIED)\]\s*', '', text)
        return text.strip(" *_")

    current = None
    for raw in narrative.split("\n"):
        line = raw.rstrip()
        if not line.strip():
            continue

        sect = _detect_section(line)
        if sect:
            current = sect
            continue
        if not current:
            continue

        if current == "synthesis":
            result["synthesis"] += line.strip() + " "
            continue

        if len(result[current]) >= 12:
            continue

        # markdown table row
        if line.strip().startswith("|"):
            parts = [p.strip() for p in line.split("|") if p.strip()]
            if not parts:
                continue
            # skip header/separator rows
            joined = "".join(parts)
            if set(joined) <= set("-: "):
                continue
            first_low = parts[0].lower()
            if first_low in ("factor", "description", "item", "#", current[:-1], current):
                continue
            desc = parts[1] if len(parts) > 1 else parts[0]
            evidence = parts[2] if len(parts) > 2 else ""
            impact = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 3
            if _clean(desc):
                result[current].append({"description": _clean(desc), "evidence": evidence, "impact": impact})
            continue

        # bullet / numbered / plain line
        m = _re.match(r'^\s*(?:[-*•]|\d+[.)])\s+(.*)$', line)
        item_text = _clean(m.group(1) if m else line.strip())
        if item_text and not item_text.startswith(("#", "|")):
            result[current].append({"description": item_text, "evidence": "", "impact": 3})

    result["synthesis"] = result["synthesis"].strip()
    return result


# ============================================================================
# RISK MATRIX GENERATION
# ============================================================================

def generate_risk_matrix(
    entity_name: str,
    entity_type: str,
    report_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate risk matrix with severity/likelihood ratings.

    Args:
        entity_name: Name of the entity
        entity_type: Type of entity
        report_data: Existing report sections

    Returns:
        Dict with risk matrix narrative and structured risk data
    """
    prompt = get_risk_matrix_prompt(
        entity_name=entity_name,
        entity_type=entity_type,
        report_data=report_data,
    )

    system_instruction = """You are a Chief Risk Officer conducting enterprise risk assessment.
You identify and categorize all material risks with specific severity and likelihood ratings.
Provide actionable mitigation recommendations for top risks.
Tag all claims with [DOCUMENTED], [REPORTED], or [ANALYTICAL]."""

    narrative = _call_openai(prompt, system_instruction)

    # Parse risk data from narrative
    risk_data = _parse_risk_matrix(narrative)

    return {
        "section_name": "Risk Matrix",
        "narrative": narrative,
        "risks": risk_data.get("risks", []),
        "critical_risks": risk_data.get("critical_risks", []),
        "high_risks": risk_data.get("high_risks", []),
        "medium_risks": risk_data.get("medium_risks", []),
        "low_risks": risk_data.get("low_risks", []),
        "overall_score": risk_data.get("overall_score", 50),
        "top_priority_risks": risk_data.get("top_priority_risks", []),
        "metadata": {
            "entity_name": entity_name,
            "model": _MODEL,
            "analysis_type": "risk_matrix",
        },
    }


def _parse_risk_matrix(narrative: str) -> Dict[str, Any]:
    """Parse risk matrix data from narrative text."""
    result = {
        "risks": [],
        "critical_risks": [],
        "high_risks": [],
        "medium_risks": [],
        "low_risks": [],
        "overall_score": 50,
        "top_priority_risks": [],
    }

    import re as _re

    def _word_score(text: str):
        t = text.lower()
        if "critical" in t or "severe" in t:
            return 5
        if "high" in t:
            return 4
        if "medium" in t or "moderate" in t:
            return 3
        if "low" in t or "minor" in t:
            return 2
        return None

    n = 0
    for line in narrative.split("\n"):
        s = line.strip()
        if not s.startswith("|"):
            continue
        parts = [p.strip() for p in s.split("|") if p.strip()]
        if len(parts) < 3:
            continue
        # skip header / separator rows
        joined = "".join(parts)
        if set(joined) <= set("-: "):
            continue
        if parts[0].lower() in ("risk", "id", "risk id", "#", "category"):
            continue

        n += 1
        canonical_id = bool(_re.match(r'^R\d+$', parts[0], _re.IGNORECASE))

        # Canonical prompt schema: | R# | Description | Category | Severity | Likelihood | Score | Mitigation |
        if canonical_id and len(parts) >= 5 and parts[3].isdigit() and parts[4].isdigit():
            risk_id     = parts[0].upper()
            description = parts[1]
            category    = parts[2]
            severity    = int(parts[3])
            likelihood  = int(parts[4])
            mitigation  = parts[6] if len(parts) > 6 else parts[-1]
        else:
            # Heuristic fallback for off-schema rows (missing cols, word ratings)
            int_cells = [int(p) for p in parts if p.isdigit() and 1 <= int(p) <= 5]
            if len(int_cells) >= 2:
                severity, likelihood = int_cells[0], int_cells[1]
            else:
                sev_w = next((_word_score(p) for p in parts if _word_score(p) is not None), None)
                if sev_w is None:
                    n -= 1
                    continue  # not a real risk row
                severity, likelihood = sev_w, 3
            risk_id = parts[0].upper() if canonical_id else f"R{n}"
            description = ""
            for i, p in enumerate(parts):
                if i == 0 or p.isdigit() or _word_score(p) is not None:
                    continue
                description = p
                break
            description = description or (parts[1] if len(parts) > 1 else parts[0])
            category = next((p for p in parts[1:] if not p.isdigit()
                             and _word_score(p) is None and p != description), "Other")
            mitigation = parts[-1] if len(parts) > 3 else "Unknown"

        severity = max(1, min(5, severity))
        likelihood = max(1, min(5, likelihood))
        score = severity * likelihood

        risk = {
            "id": risk_id,
            "description": description,
            "category": category,
            "severity": severity,
            "likelihood": likelihood,
            "score": score,
            "mitigation": mitigation,
        }
        result["risks"].append(risk)

        if score >= 20:
            result["critical_risks"].append(risk_id)
        elif score >= 15:
            result["high_risks"].append(risk_id)
        elif score >= 8:
            result["medium_risks"].append(risk_id)
        else:
            result["low_risks"].append(risk_id)

    # Calculate overall score
    if result["risks"]:
        total_score = sum(r["score"] for r in result["risks"])
        max_possible = len(result["risks"]) * 25
        result["overall_score"] = round((total_score / max_possible) * 100, 1)

    # Top 3 priority risks
    sorted_risks = sorted(result["risks"], key=lambda x: x["score"], reverse=True)
    result["top_priority_risks"] = sorted_risks[:3]

    return result


# ============================================================================
# FINANCIAL HEALTH GENERATION
# ============================================================================

def generate_financial_health(
    entity_name: str,
    ticker: Optional[str],
    financial_data: Dict[str, Any],
    technicals_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate financial health summary with key metrics.

    Args:
        entity_name: Name of the entity
        ticker: Stock ticker
        financial_data: Financial metrics from yfinance
        technicals_data: Optional technical indicators

    Returns:
        Dict with financial health narrative and structured metrics
    """
    prompt = get_financial_health_prompt(
        entity_name=entity_name,
        ticker=ticker,
        financial_data=financial_data,
        technicals_data=technicals_data,
    )

    system_instruction = """You are a senior financial analyst at Moody's Analytics.
You provide rigorous financial health assessments with specific metrics and grades.
Compare metrics to industry averages where possible.
Tag all data with [DOCUMENTED], [REPORTED], or [ANALYTICAL]."""

    narrative = _call_openai(prompt, system_instruction)

    # Extract grade from narrative
    grade_data = _extract_financial_grade(narrative)

    return {
        "section_name": "Financial Health Summary",
        "narrative": narrative,
        "grade": grade_data.get("grade", "C"),
        "grade_rationale": grade_data.get("rationale", ""),
        "metrics": financial_data.get("fundamentals", {}),
        "metadata": {
            "ticker": ticker,
            "model": _MODEL,
            "analysis_type": "financial_health",
            "has_technicals": technicals_data is not None,
        },
    }


def _extract_financial_grade(narrative: str) -> Dict[str, str]:
    """Extract financial health grade from narrative."""
    result = {"grade": "C", "rationale": ""}

    # Look for grade patterns (order matters - check +/- variants first)
    grade_patterns = ["A+", "A-", "B+", "B-", "C+", "C-", "D+", "D-", "A", "B", "C", "D", "F"]

    narrative_upper = narrative.upper()

    for grade in grade_patterns:
        # Check various patterns: "Grade: A+", "grade: B-", "**A+**", ": A+"
        patterns_to_check = [
            f"GRADE: {grade}",
            f"GRADE:{grade}",
            f": {grade}",
            f"**{grade}**",
            f"'{grade}'",
            f"\"{grade}\"",
        ]
        for pattern in patterns_to_check:
            if pattern in narrative_upper:
                result["grade"] = grade
                return result

    return result


# ============================================================================
# COMPETITIVE ANALYSIS GENERATION
# ============================================================================

def generate_competitive_analysis(
    entity_name: str,
    sector: Optional[str],
    report_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Generate competitive analysis with market position and moats.

    Args:
        entity_name: Name of the entity
        sector: Industry sector
        report_data: Existing report data

    Returns:
        Dict with competitive analysis narrative
    """
    prompt = get_competitive_analysis_prompt(
        entity_name=entity_name,
        sector=sector,
        report_data=report_data,
    )

    system_instruction = """You are a competitive intelligence analyst at Bain & Company.
You provide rigorous competitive assessments with specific market share data.
Evaluate competitive moats using Warren Buffett's framework.
Tag all claims with [DOCUMENTED], [REPORTED], or [ANALYTICAL]."""

    narrative = _call_openai(prompt, system_instruction)

    return {
        "section_name": "Competitive Analysis",
        "narrative": narrative,
        "metadata": {
            "entity_name": entity_name,
            "sector": sector,
            "model": _MODEL,
            "analysis_type": "competitive_analysis",
        },
    }


# ============================================================================
# FULL ENHANCED REPORT GENERATION
# ============================================================================

def generate_enhanced_sections(
    entity_name: str,
    entity_type: str,
    ticker: Optional[str],
    report_data: Dict[str, Any],
    financial_data: Optional[Dict[str, Any]] = None,
    valuation_data: Optional[Dict[str, Any]] = None,
    technicals_data: Optional[Dict[str, Any]] = None,
    include_investment_thesis: bool = True,
    include_swot: bool = True,
    include_risk_matrix: bool = True,
    include_financial_health: bool = True,
    include_competitive: bool = True,
) -> List[Dict[str, Any]]:
    """
    Generate all enhanced report sections.

    Args:
        entity_name: Name of the entity
        entity_type: Type of entity (org, person)
        ticker: Optional stock ticker
        report_data: Existing report data with sections/claims
        financial_data: Optional yfinance data
        valuation_data: Optional DCF valuation data
        technicals_data: Optional technical indicators
        include_*: Flags to include/exclude specific sections

    Returns:
        List of enhanced section dicts
    """
    enhanced_sections = []

    # Always generate executive summary
    logger.info(f"Generating executive summary for {entity_name}")
    exec_summary = generate_executive_summary(
        entity_name=entity_name,
        entity_type=entity_type,
        report_data=report_data,
        financial_data=financial_data,
    )
    enhanced_sections.append(exec_summary)

    # Investment Thesis (for companies with tickers)
    if include_investment_thesis and (ticker or entity_type == "org"):
        logger.info(f"Generating investment thesis for {entity_name}")
        investment_thesis = generate_investment_thesis(
            entity_name=entity_name,
            ticker=ticker,
            report_data=report_data,
            financial_data=financial_data,
            valuation_data=valuation_data,
        )
        enhanced_sections.append(investment_thesis)

    # SWOT Analysis
    if include_swot:
        logger.info(f"Generating SWOT analysis for {entity_name}")
        swot = generate_swot_analysis(
            entity_name=entity_name,
            entity_type=entity_type,
            report_data=report_data,
            financial_data=financial_data,
        )
        enhanced_sections.append(swot)

    # Risk Matrix
    if include_risk_matrix:
        logger.info(f"Generating risk matrix for {entity_name}")
        risk_matrix = generate_risk_matrix(
            entity_name=entity_name,
            entity_type=entity_type,
            report_data=report_data,
        )
        enhanced_sections.append(risk_matrix)

    # Financial Health (requires financial data)
    if include_financial_health and financial_data:
        logger.info(f"Generating financial health summary for {entity_name}")
        financial_health = generate_financial_health(
            entity_name=entity_name,
            ticker=ticker,
            financial_data=financial_data,
            technicals_data=technicals_data,
        )
        enhanced_sections.append(financial_health)

    # Competitive Analysis
    if include_competitive and entity_type == "org":
        sector = None
        if financial_data:
            sector = financial_data.get("company_info", {}).get("sector")

        logger.info(f"Generating competitive analysis for {entity_name}")
        competitive = generate_competitive_analysis(
            entity_name=entity_name,
            sector=sector,
            report_data=report_data,
        )
        enhanced_sections.append(competitive)

    logger.info(f"Generated {len(enhanced_sections)} enhanced sections for {entity_name}")
    return enhanced_sections


def convert_enhanced_to_report_sections(
    enhanced_sections: List[Dict[str, Any]],
    starting_order: int = 100,
) -> List[Dict[str, Any]]:
    """
    Convert enhanced section dicts to standard report section format.

    Args:
        enhanced_sections: List of enhanced section dicts
        starting_order: Starting order number for sections

    Returns:
        List of report sections in standard format
    """
    report_sections = []

    for i, section in enumerate(enhanced_sections):
        section_name = section.get("section_name", f"Enhanced Section {i+1}")
        narrative = section.get("narrative", "")

        claims = [
            {
                "text": narrative,
                "confidence": "ANALYTICAL",
                "source": f"{_MODEL} (Enhanced Analysis)",
            }
        ]

        # Build data dict with all non-narrative fields
        data = {}
        for key, value in section.items():
            if key not in ("section_name", "narrative", "claims"):
                data[key] = value

        report_sections.append({
            "name": section_name,
            "order": starting_order + i,
            "claims": claims,
            "data": data,
        })

    return report_sections
