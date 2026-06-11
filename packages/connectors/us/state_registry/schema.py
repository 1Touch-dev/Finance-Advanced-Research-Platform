"""Unified normalized schema for U.S. state company registry entities."""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

STATUS_VOCAB = {
    "active", "inactive", "dissolved", "cancelled", "withdrawn",
    "suspended", "revoked", "merged", "converted", "unknown",
}

ENTITY_TYPE_VOCAB = {
    "corporation", "llc", "lp", "llp", "lllp", "pc", "pllc",
    "nonprofit", "cooperative", "trust", "association", "sole_proprietorship",
    "general_partnership", "other", "unknown",
}


def _normalize_status(raw: Optional[str]) -> str:
    if not raw:
        return "unknown"
    r = raw.lower().strip()
    # Check inactive BEFORE active to avoid false match
    if any(w in r for w in ("inactiv",)):
        return "inactive"
    if any(w in r for w in ("active", "good standing", "current", "live")):
        return "active"
    if any(w in r for w in ("dissolv", "terminated", "struck off")):
        return "dissolved"
    if any(w in r for w in ("cancel", "void")):
        return "cancelled"
    if any(w in r for w in ("withdrawn", "withdraw")):
        return "withdrawn"
    if any(w in r for w in ("suspend", "delinquent")):
        return "suspended"
    if any(w in r for w in ("revok",)):
        return "revoked"
    return "unknown"


def _normalize_entity_type(raw: Optional[str]) -> str:
    if not raw:
        return "unknown"
    r = raw.lower().replace("-", "").replace(" ", "").strip()
    if "llc" in r or "limitedliability" in r:
        return "llc"
    if "nonprofit" in r or "notforprofit" in r:
        return "nonprofit"
    if "corp" in r or "inc" in r:
        return "corporation"
    if "llp" in r or "limitedliabilitypartnership" in r:
        return "llp"
    if "lp" in r or "limitedpartnership" in r:
        return "lp"
    if "pllc" in r:
        return "pllc"
    if "pc" in r or "professionalcorp" in r:
        return "pc"
    if "coop" in r:
        return "cooperative"
    if "trust" in r:
        return "trust"
    if "assoc" in r:
        return "association"
    if "sole" in r or "proprietor" in r:
        return "sole_proprietorship"
    if "partnership" in r:
        return "general_partnership"
    return "other"


@dataclass
class StateEntity:
    jurisdiction_code: str
    entity_id: str
    legal_name: str
    entity_type: Optional[str] = None
    status: str = "unknown"
    formation_date: Optional[str] = None
    registered_agent_name: Optional[str] = None
    registered_agent_address: Optional[Dict[str, Any]] = None
    principal_address: Optional[Dict[str, Any]] = None
    mailing_address: Optional[Dict[str, Any]] = None
    officers: List[Dict[str, Any]] = field(default_factory=list)
    source_tier: str = "unknown"
    source_url: str = ""
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    raw_document_id: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d.pop("extra", None)
        return d


def normalize(
    jurisdiction_code: str,
    entity_id: str,
    legal_name: str,
    raw_status: Optional[str] = None,
    raw_entity_type: Optional[str] = None,
    formation_date: Optional[str] = None,
    registered_agent_name: Optional[str] = None,
    registered_agent_address: Optional[Dict] = None,
    principal_address: Optional[Dict] = None,
    mailing_address: Optional[Dict] = None,
    officers: Optional[List] = None,
    source_tier: str = "unknown",
    source_url: str = "",
    extra: Optional[Dict] = None,
) -> Dict[str, Any]:
    entity = StateEntity(
        jurisdiction_code=jurisdiction_code,
        entity_id=str(entity_id),
        legal_name=str(legal_name).strip(),
        entity_type=_normalize_entity_type(raw_entity_type),
        status=_normalize_status(raw_status),
        formation_date=formation_date,
        registered_agent_name=registered_agent_name,
        registered_agent_address=registered_agent_address,
        principal_address=principal_address,
        mailing_address=mailing_address,
        officers=officers or [],
        source_tier=source_tier,
        source_url=source_url,
        extra=extra or {},
    )
    return entity.to_dict()
