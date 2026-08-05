"""
13F Honesty Layer API
Band A Priority #14: Flag that 13F data is 45-day stale
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime, timedelta

router = APIRouter(prefix="/honesty", tags=["honesty"])


# ─── Models ─────────────────────────────────────────────────────────────────

class DataFreshnessInfo(BaseModel):
    data_type: str
    as_of_date: str
    filing_date: Optional[str]
    staleness_days: int
    staleness_level: str  # fresh, stale, very_stale
    warning_message: str
    detailed_explanation: str


class HonestyDisclosure(BaseModel):
    entity_id: str
    data_sources: List[dict]
    overall_staleness: str
    disclaimers: List[str]
    last_updated: str


# ─── Staleness Rules ────────────────────────────────────────────────────────

STALENESS_RULES = {
    "13f": {
        "name": "13F Holdings",
        "inherent_delay_days": 45,  # SEC requirement
        "fresh_threshold_days": 60,
        "stale_threshold_days": 90,
        "explanation": "13F filings are required within 45 days of quarter end. Holdings shown may have changed significantly since the filing date.",
    },
    "insider_trading": {
        "name": "Insider Trading (Form 4)",
        "inherent_delay_days": 2,
        "fresh_threshold_days": 7,
        "stale_threshold_days": 30,
        "explanation": "Form 4 filings are required within 2 business days of the transaction.",
    },
    "10k": {
        "name": "Annual Report (10-K)",
        "inherent_delay_days": 60,  # For large accelerated filers
        "fresh_threshold_days": 90,
        "stale_threshold_days": 365,
        "explanation": "10-K filings are required 60 days after fiscal year end for large accelerated filers.",
    },
    "10q": {
        "name": "Quarterly Report (10-Q)",
        "inherent_delay_days": 40,
        "fresh_threshold_days": 60,
        "stale_threshold_days": 120,
        "explanation": "10-Q filings are required 40 days after quarter end for large accelerated filers.",
    },
    "8k": {
        "name": "Current Report (8-K)",
        "inherent_delay_days": 4,
        "fresh_threshold_days": 7,
        "stale_threshold_days": 30,
        "explanation": "8-K filings are typically required within 4 business days of a material event.",
    },
    "market_data": {
        "name": "Market Data",
        "inherent_delay_days": 0,
        "fresh_threshold_days": 0,  # Real-time
        "stale_threshold_days": 1,
        "explanation": "Market data should be real-time or near real-time during market hours.",
    },
}


# ─── Helper Functions ───────────────────────────────────────────────────────

def _calculate_staleness(data_type: str, as_of_date: datetime, filing_date: Optional[datetime] = None) -> dict:
    """Calculate staleness information for a data type."""
    rule = STALENESS_RULES.get(data_type, STALENESS_RULES["market_data"])
    now = datetime.utcnow()

    # Calculate days since the data was current
    reference_date = filing_date or as_of_date
    days_old = (now - reference_date).days

    # For 13F, add inherent delay to the as_of_date for more accurate staleness
    if data_type == "13f" and not filing_date:
        # If we only have as_of_date (quarter end), add typical filing delay
        days_old += rule["inherent_delay_days"]

    # Determine staleness level
    if days_old <= rule["fresh_threshold_days"]:
        level = "fresh"
        warning = ""
    elif days_old <= rule["stale_threshold_days"]:
        level = "stale"
        warning = f"This {rule['name']} data is {days_old} days old."
    else:
        level = "very_stale"
        warning = f"WARNING: This {rule['name']} data is {days_old} days old and may be significantly outdated."

    return {
        "data_type": data_type,
        "data_type_name": rule["name"],
        "as_of_date": as_of_date.isoformat(),
        "filing_date": filing_date.isoformat() if filing_date else None,
        "staleness_days": days_old,
        "staleness_level": level,
        "inherent_delay_days": rule["inherent_delay_days"],
        "warning_message": warning,
        "detailed_explanation": rule["explanation"],
    }


def _generate_13f_disclaimer(as_of_date: datetime, filing_date: Optional[datetime] = None) -> str:
    """Generate specific 13F disclaimer."""
    now = datetime.utcnow()

    if filing_date:
        days_since_filing = (now - filing_date).days
        days_since_quarter = (now - as_of_date).days
    else:
        days_since_quarter = (now - as_of_date).days
        days_since_filing = days_since_quarter - 45  # Estimate

    return f"""
**13F Data Disclaimer**

The institutional holdings data shown is based on 13F filings with the SEC.

• **Quarter End Date:** {as_of_date.strftime('%B %d, %Y')}
• **Data Age:** {days_since_quarter} days since quarter end
• **SEC Filing Deadline:** 45 days after quarter end

**Important Limitations:**
1. Holdings reflect positions as of {as_of_date.strftime('%B %d, %Y')}, not current positions
2. Institutions may have bought, sold, or modified positions since then
3. 13F only requires disclosure of long equity positions over $100M
4. Short positions, derivatives, and some other holdings are not disclosed
5. Small positions may be aggregated or omitted

This data should not be used as the sole basis for investment decisions.
""".strip()


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.get("/check/{data_type}")
def check_data_freshness(
    data_type: str,
    as_of_date: str,
    filing_date: Optional[str] = None,
):
    """Check freshness of a specific data type."""
    if data_type not in STALENESS_RULES:
        raise HTTPException(400, f"Unknown data type: {data_type}. Valid types: {list(STALENESS_RULES.keys())}")

    try:
        as_of = datetime.fromisoformat(as_of_date)
        filing = datetime.fromisoformat(filing_date) if filing_date else None
    except ValueError as e:
        raise HTTPException(400, f"Invalid date format: {e}")

    result = _calculate_staleness(data_type, as_of, filing)

    return DataFreshnessInfo(**result)


@router.get("/13f/disclaimer")
def get_13f_disclaimer(
    quarter_end: str,
    filing_date: Optional[str] = None,
):
    """Get 13F-specific disclaimer text."""
    try:
        as_of = datetime.fromisoformat(quarter_end)
        filing = datetime.fromisoformat(filing_date) if filing_date else None
    except ValueError as e:
        raise HTTPException(400, f"Invalid date format: {e}")

    staleness = _calculate_staleness("13f", as_of, filing)
    disclaimer = _generate_13f_disclaimer(as_of, filing)

    return {
        "staleness": staleness,
        "disclaimer_text": disclaimer,
        "disclaimer_html": disclaimer.replace("\n", "<br>").replace("**", "<strong>").replace("</strong><br>", "</strong><br>"),
    }


@router.get("/entity/{entity_id}")
def get_entity_disclosure(entity_id: str):
    """Get honesty disclosure for all data about an entity."""
    # In production, this would fetch actual data timestamps from the database
    now = datetime.utcnow()

    # Mock data sources with varying freshness
    data_sources = [
        {
            "type": "13f",
            "source": "SEC EDGAR",
            "as_of_date": (now - timedelta(days=60)).isoformat(),
            "filing_date": (now - timedelta(days=20)).isoformat(),
        },
        {
            "type": "insider_trading",
            "source": "SEC EDGAR Form 4",
            "as_of_date": (now - timedelta(days=3)).isoformat(),
        },
        {
            "type": "10q",
            "source": "SEC EDGAR",
            "as_of_date": (now - timedelta(days=45)).isoformat(),
            "filing_date": (now - timedelta(days=35)).isoformat(),
        },
        {
            "type": "market_data",
            "source": "Market Feed",
            "as_of_date": now.isoformat(),
        },
    ]

    # Calculate staleness for each
    staleness_results = []
    disclaimers = []

    for ds in data_sources:
        as_of = datetime.fromisoformat(ds["as_of_date"])
        filing = datetime.fromisoformat(ds["filing_date"]) if ds.get("filing_date") else None

        result = _calculate_staleness(ds["type"], as_of, filing)
        result["source"] = ds["source"]
        staleness_results.append(result)

        if result["warning_message"]:
            disclaimers.append(result["warning_message"])

        # Add specific disclaimers for very stale data
        if result["staleness_level"] == "very_stale":
            disclaimers.append(f"⚠️ {result['data_type_name']} data is significantly outdated ({result['staleness_days']} days old)")

    # Determine overall staleness
    levels = [r["staleness_level"] for r in staleness_results]
    if "very_stale" in levels:
        overall = "very_stale"
    elif "stale" in levels:
        overall = "stale"
    else:
        overall = "fresh"

    return HonestyDisclosure(
        entity_id=entity_id,
        data_sources=staleness_results,
        overall_staleness=overall,
        disclaimers=disclaimers,
        last_updated=now.isoformat(),
    )


@router.get("/rules")
def get_staleness_rules():
    """Get all staleness rules."""
    return {"rules": STALENESS_RULES}


@router.get("/badge/{data_type}")
def get_freshness_badge(
    data_type: str,
    as_of_date: str,
):
    """Get a freshness badge (for UI display)."""
    if data_type not in STALENESS_RULES:
        raise HTTPException(400, f"Unknown data type: {data_type}")

    try:
        as_of = datetime.fromisoformat(as_of_date)
    except ValueError as e:
        raise HTTPException(400, f"Invalid date format: {e}")

    result = _calculate_staleness(data_type, as_of, None)

    # Generate badge info
    badges = {
        "fresh": {"color": "#10b981", "label": "Fresh", "icon": "✓"},
        "stale": {"color": "#f59e0b", "label": "Stale", "icon": "⚠"},
        "very_stale": {"color": "#dc2626", "label": "Outdated", "icon": "⚠"},
    }

    badge = badges[result["staleness_level"]]

    return {
        "level": result["staleness_level"],
        "color": badge["color"],
        "label": badge["label"],
        "icon": badge["icon"],
        "days_old": result["staleness_days"],
        "tooltip": result["warning_message"] or f"Data as of {as_of_date}",
    }
