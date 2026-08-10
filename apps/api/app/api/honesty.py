"""
13F Honesty Layer API.

This module reports freshness based on caller-supplied dates or persisted
source metadata. It does not fabricate entity-level data when no metadata is
available.
"""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.sources import Source, SourceRecordMeta

router = APIRouter(prefix="/honesty", tags=["honesty"])


class DataFreshnessInfo(BaseModel):
    data_type: str
    as_of_date: str
    filing_date: Optional[str]
    staleness_days: int
    staleness_level: str
    warning_message: str
    detailed_explanation: str


class HonestyDisclosure(BaseModel):
    entity_id: str
    data_sources: List[dict]
    overall_staleness: str
    disclaimers: List[str]
    last_updated: str


STALENESS_RULES = {
    "13f": {
        "name": "13F Holdings",
        "inherent_delay_days": 45,
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
        "inherent_delay_days": 60,
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
        "fresh_threshold_days": 0,
        "stale_threshold_days": 1,
        "explanation": "Market data should be real-time or near real-time during market hours.",
    },
}


def _calculate_staleness(data_type: str, as_of_date: datetime, filing_date: Optional[datetime] = None) -> dict:
    rule = STALENESS_RULES.get(data_type, STALENESS_RULES["market_data"])
    reference_date = filing_date or as_of_date
    days_old = (datetime.utcnow() - reference_date).days

    if data_type == "13f" and not filing_date:
        days_old += rule["inherent_delay_days"]

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
    now = datetime.utcnow()
    days_since_quarter = (now - as_of_date).days

    return f"""
**13F Data Disclaimer**

The institutional holdings data shown is based on 13F filings with the SEC.

- **Quarter End Date:** {as_of_date.strftime('%B %d, %Y')}
- **Data Age:** {days_since_quarter} days since quarter end
- **SEC Filing Deadline:** 45 days after quarter end

**Important Limitations:**
1. Holdings reflect positions as of {as_of_date.strftime('%B %d, %Y')}, not current positions
2. Institutions may have bought, sold, or modified positions since then
3. 13F only requires disclosure of long equity positions over $100M
4. Short positions, derivatives, and some other holdings are not disclosed
5. Small positions may be aggregated or omitted

This data should not be used as the sole basis for investment decisions.
""".strip()


def _parse_optional_datetime(value: object) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return None


@router.get("/check/{data_type}")
def check_data_freshness(
    data_type: str,
    as_of_date: str,
    filing_date: Optional[str] = None,
):
    if data_type not in STALENESS_RULES:
        raise HTTPException(400, f"Unknown data type: {data_type}. Valid types: {list(STALENESS_RULES.keys())}")

    try:
        as_of = datetime.fromisoformat(as_of_date)
        filing = datetime.fromisoformat(filing_date) if filing_date else None
    except ValueError as exc:
        raise HTTPException(400, f"Invalid date format: {exc}")

    return DataFreshnessInfo(**_calculate_staleness(data_type, as_of, filing))


@router.get("/13f/disclaimer")
def get_13f_disclaimer(
    quarter_end: str,
    filing_date: Optional[str] = None,
):
    try:
        as_of = datetime.fromisoformat(quarter_end)
        filing = datetime.fromisoformat(filing_date) if filing_date else None
    except ValueError as exc:
        raise HTTPException(400, f"Invalid date format: {exc}")

    staleness = _calculate_staleness("13f", as_of, filing)
    disclaimer = _generate_13f_disclaimer(as_of, filing)

    return {
        "staleness": staleness,
        "disclaimer_text": disclaimer,
        "disclaimer_html": disclaimer.replace("\n", "<br>").replace("**", "<strong>").replace("</strong><br>", "</strong><br>"),
    }


@router.get("/entity/{entity_id}")
def get_entity_disclosure(entity_id: str, db: Session = Depends(get_db)):
    now = datetime.utcnow()
    rows = (
        db.query(SourceRecordMeta, Source)
        .join(Source, SourceRecordMeta.source_id == Source.id)
        .filter(SourceRecordMeta.external_id == entity_id)
        .limit(50)
        .all()
    )

    staleness_results = []
    disclaimers = []

    for record, source in rows:
        normalized = record.normalized or {}
        data_type = normalized.get("data_type") or source.kind or "market_data"
        if data_type not in STALENESS_RULES:
            data_type = "market_data"

        as_of = (
            _parse_optional_datetime(normalized.get("as_of_date"))
            or _parse_optional_datetime(normalized.get("report_period"))
            or record.last_ingested_at
        )
        filing = _parse_optional_datetime(normalized.get("filing_date"))

        result = _calculate_staleness(data_type, as_of, filing)
        result["source"] = source.name
        result["external_id"] = record.external_id
        staleness_results.append(result)

        if result["warning_message"]:
            disclaimers.append(result["warning_message"])
        if result["staleness_level"] == "very_stale":
            disclaimers.append(f"{result['data_type_name']} data is significantly outdated ({result['staleness_days']} days old)")

    levels = [item["staleness_level"] for item in staleness_results]
    if not levels:
        overall = "unknown"
        disclaimers.append("No verified source freshness metadata is available for this entity.")
    elif "very_stale" in levels:
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
    return {"rules": STALENESS_RULES}


@router.get("/badge/{data_type}")
def get_freshness_badge(
    data_type: str,
    as_of_date: str,
):
    if data_type not in STALENESS_RULES:
        raise HTTPException(400, f"Unknown data type: {data_type}")

    try:
        as_of = datetime.fromisoformat(as_of_date)
    except ValueError as exc:
        raise HTTPException(400, f"Invalid date format: {exc}")

    result = _calculate_staleness(data_type, as_of, None)
    badges = {
        "fresh": {"color": "#10b981", "label": "Fresh", "icon": "ok"},
        "stale": {"color": "#f59e0b", "label": "Stale", "icon": "warning"},
        "very_stale": {"color": "#dc2626", "label": "Outdated", "icon": "warning"},
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
