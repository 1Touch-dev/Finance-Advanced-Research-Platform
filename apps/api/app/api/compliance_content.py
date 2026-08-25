"""
Content Compliance Guardrails API
Band A Priority #9: Compliance guardrails on generated content
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime
from app.auth.security import get_current_user
import re

router = APIRouter(prefix="/compliance/content", tags=["compliance"])


# ─── Models ─────────────────────────────────────────────────────────────────

class ContentCheckRequest(BaseModel):
    content: str
    content_type: str  # intelligence_report, analysis, summary
    entity_id: Optional[str] = None


class ComplianceViolation(BaseModel):
    rule_id: str
    severity: str  # error, warning, info
    message: str
    span: Optional[tuple] = None  # (start, end) indices
    suggestion: Optional[str] = None


class ComplianceResult(BaseModel):
    passed: bool
    violations: List[ComplianceViolation]
    warnings: int
    errors: int
    disclaimer_required: bool
    suggested_disclaimer: Optional[str]


# ─── Compliance Rules ───────────────────────────────────────────────────────

# Patterns that indicate potential compliance issues
COMPLIANCE_RULES = [
    {
        "id": "no_projections",
        "name": "No Forward Projections",
        "severity": "error",
        "patterns": [
            r"\bwill\s+(rise|fall|increase|decrease|grow|decline)\b",
            r"\bexpect(s|ed)?\s+to\s+(rise|fall|increase|decrease)\b",
            r"\bprojected?\s+(to|growth|revenue|earnings)\b",
            r"\bforecast(s|ed)?\s+(to|growth|revenue|earnings)\b",
            r"\b(target\s+price|price\s+target)\s*[:\s]*\$?\d+\b",
        ],
        "message": "Content contains forward-looking projections which may constitute investment advice",
        "suggestion": "Reframe as historical data or remove speculative language",
    },
    {
        "id": "no_recommendations",
        "name": "No Buy/Sell Recommendations",
        "severity": "error",
        "patterns": [
            r"\b(should|recommend|advise)\s+(buy|sell|hold)\b",
            r"\b(buy|sell|hold)\s+recommend(ation|ed)?\b",
            r"\bstrong\s+(buy|sell)\b",
            r"\b(underweight|overweight|outperform|underperform)\b",
            r"\binvestors\s+should\b",
        ],
        "message": "Content contains investment recommendations",
        "suggestion": "Remove advisory language - present only factual data",
    },
    {
        "id": "no_guarantees",
        "name": "No Performance Guarantees",
        "severity": "error",
        "patterns": [
            r"\bguarantee[ds]?\b",
            r"\brisk-?\s*free\b",
            r"\bcertain\s+(to|gain|profit|return)\b",
            r"\bsafe\s+investment\b",
            r"\balways\s+(profitable|gains|returns)\b",
        ],
        "message": "Content contains performance guarantees",
        "suggestion": "Remove guarantee language - all investments carry risk",
    },
    {
        "id": "disclaimer_missing",
        "name": "Disclaimer Required",
        "severity": "warning",
        "check_type": "missing",
        "required_text": ["not financial advice", "not investment advice", "informational purposes only"],
        "message": "Content should include a disclaimer",
        "suggestion": "Add standard disclaimer about informational purposes",
    },
    {
        "id": "past_performance_warning",
        "name": "Past Performance Disclaimer",
        "severity": "warning",
        "patterns": [
            r"\breturned?\s+\d+%\b",
            r"\b(historical|past)\s+(returns?|performance|gains?)\b",
            r"\b(year|month|quarter)\s+over\s+(year|month|quarter)\b",
        ],
        "message": "Content discusses past performance without disclaimer",
        "suggestion": "Add: 'Past performance is not indicative of future results'",
    },
    {
        "id": "source_attribution",
        "name": "Source Attribution",
        "severity": "info",
        "check_type": "missing",
        "required_patterns": [r"\bsource[sd]?\s*:", r"\baccording\s+to\b", r"\bdata\s+from\b"],
        "message": "Consider adding source attribution for data points",
        "suggestion": "Cite data sources explicitly",
    },
    {
        "id": "as_of_date",
        "name": "Data Staleness Warning",
        "severity": "warning",
        "check_type": "missing",
        "required_patterns": [r"\bas\s+of\b", r"\bdata\s+(as\s+of|through|from)\b", r"\bupdated?\s+(on|through)\b"],
        "message": "Content should indicate data freshness",
        "suggestion": "Add 'as of [date]' to key data points",
    },
]


# Standard disclaimers
DISCLAIMERS = {
    "general": """
**Disclaimer:** This content is for informational purposes only and does not constitute financial, investment, legal, or tax advice. The information presented is based on publicly available data and may not be complete or accurate. Past performance is not indicative of future results. Always consult with qualified professionals before making investment decisions.
""".strip(),

    "ai_generated": """
**AI-Generated Content Notice:** This content was generated with AI assistance. While we strive for accuracy, AI-generated content may contain errors or omissions. This information should not be relied upon for investment decisions without independent verification.
""".strip(),

    "13f_data": """
**13F Data Disclaimer:** 13F filings are reported with a 45-day delay from quarter end. The holdings shown reflect positions as of the filing date and may not represent current holdings. Institutional investors may have materially changed their positions since the filing date.
""".strip(),

    "market_data": """
**Market Data Notice:** Market data may be delayed. Real-time quotes are not guaranteed. Price and volume data is provided for informational purposes only.
""".strip(),
}


# ─── Helper Functions ───────────────────────────────────────────────────────

def _check_patterns(content: str, patterns: List[str]) -> List[tuple]:
    """Check content against regex patterns, return matches with positions."""
    matches = []
    content_lower = content.lower()

    for pattern in patterns:
        for match in re.finditer(pattern, content_lower, re.IGNORECASE):
            matches.append((match.start(), match.end(), match.group()))

    return matches


def _check_required(content: str, required_patterns: List[str]) -> bool:
    """Check if content contains at least one of the required patterns."""
    content_lower = content.lower()

    for pattern in required_patterns:
        if re.search(pattern, content_lower, re.IGNORECASE):
            return True

    return False


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.post("/check", response_model=ComplianceResult)
def check_content_compliance(request: ContentCheckRequest, current_user: dict = Depends(get_current_user)):
    """Check content for compliance violations."""
    violations = []

    for rule in COMPLIANCE_RULES:
        if rule.get("check_type") == "missing":
            # Check for required content
            required = rule.get("required_text") or rule.get("required_patterns", [])
            if not _check_required(request.content, required):
                violations.append(ComplianceViolation(
                    rule_id=rule["id"],
                    severity=rule["severity"],
                    message=rule["message"],
                    suggestion=rule.get("suggestion"),
                ))
        elif "patterns" in rule:
            # Check for prohibited patterns
            matches = _check_patterns(request.content, rule["patterns"])
            for start, end, matched_text in matches:
                violations.append(ComplianceViolation(
                    rule_id=rule["id"],
                    severity=rule["severity"],
                    message=f"{rule['message']}: '{matched_text}'",
                    span=(start, end),
                    suggestion=rule.get("suggestion"),
                ))

    errors = sum(1 for v in violations if v.severity == "error")
    warnings = sum(1 for v in violations if v.severity == "warning")

    # Determine which disclaimer is needed
    disclaimer_required = errors > 0 or warnings > 0
    suggested_disclaimer = DISCLAIMERS["general"]

    if "13f" in request.content_type.lower() or "institutional" in request.content_type.lower():
        suggested_disclaimer = DISCLAIMERS["13f_data"] + "\n\n" + DISCLAIMERS["general"]
    elif request.content_type in ["intelligence_report", "analysis"]:
        suggested_disclaimer = DISCLAIMERS["ai_generated"] + "\n\n" + DISCLAIMERS["general"]

    return ComplianceResult(
        passed=errors == 0,
        violations=violations,
        errors=errors,
        warnings=warnings,
        disclaimer_required=disclaimer_required,
        suggested_disclaimer=suggested_disclaimer if disclaimer_required else None,
    )


@router.post("/sanitize")
def sanitize_content(request: ContentCheckRequest, current_user: dict = Depends(get_current_user)):
    """Attempt to automatically sanitize content for compliance."""
    content = request.content
    changes = []

    # Replace problematic patterns with compliant alternatives
    replacements = [
        (r"\bwill\s+(rise|fall|increase|decrease|grow|decline)\b", "may \\1", "no_projections"),
        (r"\bexpects?\s+to\s+", "may ", "no_projections"),
        (r"\b(should|recommend)\s+(buy|sell|hold)\b", "historically has shown", "no_recommendations"),
        (r"\bguarantee[ds]?\b", "potential", "no_guarantees"),
        (r"\brisk-?\s*free\b", "lower-risk", "no_guarantees"),
        (r"\bcertain\s+to\b", "potentially", "no_guarantees"),
    ]

    for pattern, replacement, rule_id in replacements:
        new_content, count = re.subn(pattern, replacement, content, flags=re.IGNORECASE)
        if count > 0:
            changes.append({
                "rule_id": rule_id,
                "replacements": count,
                "pattern": pattern,
            })
            content = new_content

    # Add disclaimer if not present
    has_disclaimer = any(phrase.lower() in content.lower() for phrase in ["not financial advice", "informational purposes"])

    if not has_disclaimer:
        content = content + "\n\n" + DISCLAIMERS["general"]
        changes.append({"rule_id": "disclaimer_missing", "action": "added_disclaimer"})

    # Re-check compliance
    result = check_content_compliance(ContentCheckRequest(
        content=content,
        content_type=request.content_type,
        entity_id=request.entity_id,
    ))

    return {
        "sanitized_content": content,
        "changes_made": changes,
        "compliance_result": result,
    }


@router.get("/rules")
def get_compliance_rules():
    """Get all compliance rules."""
    return {
        "rules": [
            {
                "id": r["id"],
                "name": r["name"],
                "severity": r["severity"],
                "message": r["message"],
                "suggestion": r.get("suggestion"),
            }
            for r in COMPLIANCE_RULES
        ]
    }


@router.get("/disclaimers")
def get_disclaimers():
    """Get available disclaimer templates."""
    return {"disclaimers": DISCLAIMERS}


@router.get("/disclaimers/{disclaimer_type}")
def get_disclaimer(disclaimer_type: str):
    """Get a specific disclaimer."""
    if disclaimer_type not in DISCLAIMERS:
        raise HTTPException(404, f"Disclaimer type not found: {disclaimer_type}")
    return {"type": disclaimer_type, "text": DISCLAIMERS[disclaimer_type]}
