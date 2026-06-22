"""
Licensable U.S. State Registry API.

Endpoints:
  GET  /registry/health               — live jurisdiction count
  GET  /registry/jurisdictions        — list all 51 with tier + status
  GET  /registry/search               — search normalized records
  GET  /registry/entity/{jur}/{eid}   — single entity detail
  POST /registry/keys                 — admin: create API key
  GET  /registry/keys                 — admin: list keys

Auth: X-Registry-Api-Key header or ?api_key= query param
Rate limit: 100 req/min per key (in-memory)
"""
import hashlib
import os
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.registry import RegistryApiKey, RegistryApiUsage

# ---------------------------------------------------------------------------
# Rate limiter (in-memory, per key hash, per minute)
# ---------------------------------------------------------------------------
_rate_buckets: Dict[str, List[float]] = defaultdict(list)
_RATE_LIMIT = int(os.getenv("REGISTRY_RATE_LIMIT_PER_MIN", "100"))


def _check_rate_limit(key_hash: str) -> bool:
    now = time.time()
    window_start = now - 60
    bucket = _rate_buckets[key_hash]
    _rate_buckets[key_hash] = [t for t in bucket if t > window_start]
    if len(_rate_buckets[key_hash]) >= _RATE_LIMIT:
        return False
    _rate_buckets[key_hash].append(now)
    return True


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------
ADMIN_TOKEN = os.getenv("REGISTRY_API_ADMIN_TOKEN", "")


def _resolve_key(
    request: Request,
    x_registry_api_key: Optional[str] = Header(None, alias="X-Registry-Api-Key"),
    api_key: Optional[str] = Query(None),
    db: Session = Depends(get_db),
) -> Optional[str]:
    """
    Return key_hash if key is valid, or None if auth is not required.
    Raise 401/429 on invalid key or rate limit exceeded.
    """
    raw = x_registry_api_key or api_key
    if not raw:
        # Allow unauthenticated in dev; require in prod if env says so
        if os.getenv("REGISTRY_REQUIRE_AUTH", "").lower() == "true":
            raise HTTPException(status_code=401, detail="API key required. Set X-Registry-Api-Key header.")
        return None

    key_hash = RegistryApiKey.hash_key(raw)

    # Check admin bootstrap token
    if ADMIN_TOKEN and raw == ADMIN_TOKEN:
        if not _check_rate_limit("admin_token"):
            raise HTTPException(status_code=429, detail="Rate limit exceeded.")
        return "admin_token"

    # Check DB
    try:
        row = db.query(RegistryApiKey).filter(
            RegistryApiKey.key_hash == key_hash,
            RegistryApiKey.revoked_at.is_(None),
        ).first()
    except Exception:
        row = None

    if not row:
        raise HTTPException(status_code=401, detail="Invalid or revoked API key.")

    if not _check_rate_limit(key_hash):
        raise HTTPException(status_code=429, detail="Rate limit exceeded (100 req/min).")

    return key_hash


def _log_usage(
    db: Session,
    key_hash: Optional[str],
    endpoint: str,
    query_params: Optional[dict],
    response_count: int,
    ip_address: Optional[str] = None,
) -> None:
    if not key_hash:
        return
    try:
        usage = RegistryApiUsage(
            key_hash=key_hash,
            endpoint=endpoint,
            query_params=query_params,
            response_count=response_count,
            ip_address=ip_address,
        )
        db.add(usage)
        db.commit()
    except Exception:
        db.rollback()


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/registry", tags=["registry"])


# ---------------------------------------------------------------------------
# /registry/health
# ---------------------------------------------------------------------------
@router.get("/health")
def registry_health(db: Session = Depends(get_db)):
    """Returns jurisdiction count and live record count."""
    from us.state_registry.registry import JURISDICTIONS, TIER_COUNTS

    try:
        result = db.execute(text(
            "SELECT COUNT(DISTINCT sm.normalized->>'jurisdiction_code') "
            "FROM source_record_meta sm "
            "WHERE sm.normalized->>'jurisdiction_code' IS NOT NULL "
            "AND sm.normalized->>'jurisdiction_code' LIKE 'us_%'"
        )).scalar()
        live_jur_count = int(result or 0)
    except Exception:
        live_jur_count = 0

    try:
        rec_count = db.execute(text(
            "SELECT COUNT(*) FROM source_record_meta sm "
            "WHERE sm.normalized->>'jurisdiction_code' LIKE 'us_%'"
        )).scalar()
        total_records = int(rec_count or 0)
    except Exception:
        total_records = 0

    return {
        "status": "ok",
        "total_jurisdictions_registered": len(JURISDICTIONS),
        "live_jurisdictions_with_data": live_jur_count,
        "total_registry_records": total_records,
        "tier_distribution": TIER_COUNTS,
    }


# ---------------------------------------------------------------------------
# /registry/jurisdictions
# ---------------------------------------------------------------------------
@router.get("/jurisdictions")
def list_jurisdictions(db: Session = Depends(get_db)):
    """List all 51 jurisdictions with tier, SOS URL, and last run status."""
    from us.state_registry.registry import JURISDICTIONS

    rows = {}
    try:
        result = db.execute(text("""
            SELECT
                sm.normalized->>'jurisdiction_code' AS jcode,
                COUNT(*) AS record_count,
                MAX(sm.last_ingested_at) AS last_run
            FROM source_record_meta sm
            WHERE sm.normalized->>'jurisdiction_code' LIKE 'us_%'
            GROUP BY jcode
        """)).fetchall()
        for row in result:
            rows[row.jcode] = {
                "record_count": row.record_count,
                "last_run": str(row.last_run) if row.last_run else None,
            }
    except Exception:
        pass

    jurisdictions = []
    for jcode, meta in JURISDICTIONS.items():
        db_info = rows.get(jcode, {})
        rc = db_info.get("record_count", 0)
        last_status = "success" if rc > 0 else "pending"
        jurisdictions.append({
            "jurisdiction_code": jcode,
            "name": meta["name"],
            "tier": meta["tier"],
            "sos_url": meta.get("sos_url", ""),
            "record_count": rc,
            "last_run": db_info.get("last_run"),
            "last_status": last_status,
            "notes": meta.get("notes", ""),
        })

    return {
        "count": len(jurisdictions),
        "jurisdictions": sorted(jurisdictions, key=lambda x: x["jurisdiction_code"]),
    }


# ---------------------------------------------------------------------------
# /registry/search
# ---------------------------------------------------------------------------
@router.get("/search")
def search_registry(
    q: Optional[str] = Query(None, description="Search query (entity name)"),
    state: Optional[str] = Query(None, description="Jurisdiction code e.g. us_ny"),
    entity_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    key_hash: Optional[str] = Depends(_resolve_key),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Search normalized state registry records."""
    conditions = ["sm.normalized->>'jurisdiction_code' LIKE 'us_%'"]
    params: Dict[str, Any] = {"limit": limit, "offset": offset}

    if q:
        conditions.append("LOWER(sm.normalized->>'legal_name') LIKE LOWER(:q_like)")
        params["q_like"] = f"%{q}%"

    if state:
        conditions.append("sm.normalized->>'jurisdiction_code' = :state")
        params["state"] = state

    if entity_type:
        conditions.append("sm.normalized->>'entity_type' = :entity_type")
        params["entity_type"] = entity_type

    if status:
        conditions.append("sm.normalized->>'status' = :status")
        params["status"] = status

    where_clause = " AND ".join(conditions)

    try:
        count_result = db.execute(text(
            f"SELECT COUNT(*) FROM source_record_meta sm WHERE {where_clause}"
        ), params).scalar()
        total = int(count_result or 0)

        result = db.execute(text(
            f"SELECT sm.external_id, sm.normalized, sm.last_ingested_at "
            f"FROM source_record_meta sm "
            f"WHERE {where_clause} "
            f"ORDER BY sm.last_ingested_at DESC "
            f"LIMIT :limit OFFSET :offset"
        ), params).fetchall()

        records = []
        for row in result:
            rec = row.normalized or {}
            rec["_db_id"] = row.external_id
            rec["_ingested_at"] = str(row.last_ingested_at) if row.last_ingested_at else None
            records.append(rec)

    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Search error: {exc}")

    _log_usage(db, key_hash, "/registry/search", {"q": q, "state": state}, len(records),
               getattr(request, "client", {}).host if request else None)

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": records,
    }


# ---------------------------------------------------------------------------
# /registry/entity/{jurisdiction}/{entity_id}
# ---------------------------------------------------------------------------
@router.get("/entity/{jurisdiction}/{entity_id}")
def get_entity(
    jurisdiction: str,
    entity_id: str,
    key_hash: Optional[str] = Depends(_resolve_key),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Fetch a single normalized entity by jurisdiction + entity_id."""
    try:
        row = db.execute(text("""
            SELECT sm.external_id, sm.normalized, sm.last_ingested_at
            FROM source_record_meta sm
            WHERE sm.normalized->>'jurisdiction_code' = :jur
            AND (sm.external_id = :eid OR sm.normalized->>'entity_id' = :eid)
            LIMIT 1
        """), {"jur": jurisdiction, "eid": entity_id}).fetchone()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DB error: {exc}")

    if not row:
        raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found in {jurisdiction}")

    rec = row.normalized or {}
    rec["_db_id"] = row.external_id
    rec["_ingested_at"] = str(row.last_ingested_at) if row.last_ingested_at else None

    _log_usage(db, key_hash, f"/registry/entity/{jurisdiction}/{entity_id}", None, 1,
               getattr(request, "client", {}).host if request else None)

    return rec


# ---------------------------------------------------------------------------
# /registry/keys — admin only
# ---------------------------------------------------------------------------
class CreateKeyRequest(BaseModel):
    name: str
    rate_limit_per_min: int = 100
    notes: Optional[str] = None


@router.post("/keys")
def create_api_key(
    body: CreateKeyRequest,
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
    db: Session = Depends(get_db),
):
    """Create a new registry API key. Requires X-Admin-Token."""
    if ADMIN_TOKEN and x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Admin token required.")

    raw, key_hash, prefix = RegistryApiKey.generate()
    key = RegistryApiKey(
        name=body.name,
        key_hash=key_hash,
        key_prefix=prefix,
        rate_limit_per_min=body.rate_limit_per_min,
        notes=body.notes,
    )
    try:
        db.add(key)
        db.commit()
        db.refresh(key)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create key: {exc}")

    return {
        "id": key.id,
        "name": key.name,
        "api_key": raw,
        "key_prefix": prefix,
        "rate_limit_per_min": key.rate_limit_per_min,
        "message": "Store this key securely — it will not be shown again.",
    }


@router.get("/keys")
def list_api_keys(
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
    db: Session = Depends(get_db),
):
    """List all API keys (without raw key). Requires X-Admin-Token."""
    if ADMIN_TOKEN and x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Admin token required.")

    try:
        keys = db.query(RegistryApiKey).order_by(RegistryApiKey.created_at.desc()).all()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"DB error: {exc}")

    return {
        "keys": [
            {
                "id": k.id,
                "name": k.name,
                "key_prefix": k.key_prefix,
                "created_at": str(k.created_at),
                "revoked_at": str(k.revoked_at) if k.revoked_at else None,
                "rate_limit_per_min": k.rate_limit_per_min,
                "notes": k.notes,
            }
            for k in keys
        ]
    }
