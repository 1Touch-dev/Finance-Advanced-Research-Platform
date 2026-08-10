"""
Portable Corpora Export API.

Exports are generated from persisted application records only. If a resource
has no backing table or rows, the API reports an empty dataset instead of
fabricating demo content.
"""
from datetime import datetime, timedelta
import csv
import io
import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.base import Base
from app.models.entities import Entity
from app.models.monitor import AlertEvent, AlertRule, Watchlist, WatchlistItem
from app.models.reports import Report

router = APIRouter(prefix="/export", tags=["export"])


class ExportRequest(BaseModel):
    data_types: List[str]
    format: str
    include_metadata: bool = True
    date_range: Optional[dict] = None


class ExportJob(BaseModel):
    job_id: str
    status: str
    data_types: List[str]
    format: str
    created_at: str
    completed_at: Optional[str]
    download_url: Optional[str]
    file_size_bytes: Optional[int]
    expires_at: Optional[str]


_export_jobs: Dict[str, dict] = {}

_DATA_TYPE_META = {
    "watchlists": {
        "name": "Watchlists",
        "description": "Saved watchlists and their symbols",
    },
    "alerts": {
        "name": "Alerts",
        "description": "Configured alert rules and generated alert events",
    },
    "reports": {
        "name": "Saved Reports",
        "description": "Persisted intelligence reports",
    },
    "entities": {
        "name": "Tracked Entities",
        "description": "Persisted entity registry records",
    },
    "tracking": {
        "name": "Tracking Configuration",
        "description": "No dedicated tracking export table is currently wired",
    },
}


def _serialize_dt(value: Any) -> Any:
    return value.isoformat() if hasattr(value, "isoformat") else value


def _watchlists(db: Session) -> list[dict]:
    items_by_watchlist: dict[int, list[dict]] = {}
    for item in db.query(WatchlistItem).all():
        items_by_watchlist.setdefault(item.watchlist_id, []).append({
            "id": item.id,
            "entity_id": item.entity_id,
            "ticker": item.ticker,
            "notes": item.notes,
        })

    return [
        {
            "id": row.id,
            "name": row.name,
            "meta": row.meta,
            "created_at": _serialize_dt(row.created_at),
            "items": items_by_watchlist.get(row.id, []),
        }
        for row in db.query(Watchlist).order_by(Watchlist.id.asc()).all()
    ]


def _alerts(db: Session) -> list[dict]:
    rules = [
        {
            "id": row.id,
            "type": "rule",
            "name": row.name,
            "kind": row.kind,
            "params": row.params,
            "watchlist_id": row.watchlist_id,
            "portfolio_id": row.portfolio_id,
            "enabled": row.enabled,
        }
        for row in db.query(AlertRule).order_by(AlertRule.id.asc()).all()
    ]
    events = [
        {
            "id": row.id,
            "type": "event",
            "rule_id": row.rule_id,
            "entity_id": row.entity_id,
            "ticker": row.ticker,
            "kind": row.kind,
            "payload": row.payload,
            "delivered": row.delivered,
            "created_at": _serialize_dt(row.created_at),
        }
        for row in db.query(AlertEvent).order_by(AlertEvent.id.asc()).all()
    ]
    return [*rules, *events]


def _reports(db: Session) -> list[dict]:
    return [
        {
            "id": row.id,
            "title": row.title,
            "kind": row.kind,
            "status": row.status,
            "meta": row.meta,
            "created_at": _serialize_dt(row.created_at),
            "updated_at": _serialize_dt(row.updated_at),
        }
        for row in db.query(Report).order_by(Report.id.asc()).all()
    ]


def _entities(db: Session) -> list[dict]:
    return [
        {
            "id": row.id,
            "kind": row.kind,
            "name": row.name,
            "canonical": row.canonical,
            "meta": row.meta,
            "created_at": _serialize_dt(row.created_at),
            "updated_at": _serialize_dt(row.updated_at),
        }
        for row in db.query(Entity).order_by(Entity.id.asc()).all()
    ]


def _collect_data(db: Session, data_types: List[str]) -> dict:
    collectors = {
        "watchlists": _watchlists,
        "alerts": _alerts,
        "reports": _reports,
        "entities": _entities,
        "tracking": lambda session: [],
    }
    return {dtype: collectors[dtype](db) for dtype in data_types}


def _to_csv(data: List[dict]) -> str:
    if not data:
        return ""

    fieldnames = sorted({key for row in data for key in row.keys()})
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()


def _generate_export(db: Session, data_types: List[str], format: str, include_metadata: bool) -> tuple[str, str, str]:
    export_data = _collect_data(db, data_types)

    if include_metadata:
        export_data["_metadata"] = {
            "exported_at": datetime.utcnow().isoformat(),
            "data_types": data_types,
            "record_counts": {key: len(value) for key, value in export_data.items() if key != "_metadata"},
            "format": format,
            "platform": "Enterprise Intelligence",
            "version": "1.0",
            "note": "Only persisted records are exported; unavailable resources are empty.",
        }

    if format == "json":
        return json.dumps(export_data, indent=2, default=str), "application/json", "export.json"

    if format == "csv":
        first_type = data_types[0] if data_types else ""
        return _to_csv(export_data.get(first_type, [])), "text/csv", f"{first_type or 'empty'}.csv"

    raise HTTPException(400, f"Unsupported format: {format}")


def _record_count(db: Session, dtype: str) -> int:
    return len(_collect_data(db, [dtype]).get(dtype, []))


@router.get("/available-data")
def list_available_data(db: Session = Depends(get_db)):
    Base.metadata.create_all(bind=db.get_bind())
    return {
        "data_types": [
            {
                "id": dtype,
                "name": meta["name"],
                "description": meta["description"],
                "record_count": _record_count(db, dtype),
                "source": "database" if dtype != "tracking" else "unavailable",
            }
            for dtype, meta in _DATA_TYPE_META.items()
        ],
        "formats": ["json", "csv"],
    }


@router.post("/request")
def request_export(request: ExportRequest, db: Session = Depends(get_db)):
    Base.metadata.create_all(bind=db.get_bind())
    job_id = f"export-{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow()

    invalid = [item for item in request.data_types if item not in _DATA_TYPE_META]
    if invalid:
        raise HTTPException(400, f"Invalid data types: {invalid}")

    job = {
        "job_id": job_id,
        "data_types": request.data_types,
        "format": request.format,
        "include_metadata": request.include_metadata,
        "date_range": request.date_range,
        "status": "processing",
        "created_at": now.isoformat(),
        "completed_at": None,
        "download_url": None,
        "file_size_bytes": None,
        "expires_at": None,
    }

    try:
        content, content_type, filename = _generate_export(
            db,
            request.data_types,
            request.format,
            request.include_metadata,
        )
        job["status"] = "completed"
        job["completed_at"] = datetime.utcnow().isoformat()
        job["download_url"] = f"/export/download/{job_id}"
        job["file_size_bytes"] = len(content.encode())
        job["expires_at"] = (now + timedelta(days=7)).isoformat()
        job["_content"] = content
        job["_content_type"] = content_type
        job["_filename"] = filename
    except Exception as exc:
        job["status"] = "failed"
        job["error"] = str(exc)

    _export_jobs[job_id] = job

    return ExportJob(
        job_id=job_id,
        status=job["status"],
        data_types=job["data_types"],
        format=job["format"],
        created_at=job["created_at"],
        completed_at=job.get("completed_at"),
        download_url=job.get("download_url"),
        file_size_bytes=job.get("file_size_bytes"),
        expires_at=job.get("expires_at"),
    )


@router.get("/jobs")
def list_export_jobs(limit: int = 20):
    jobs = sorted(_export_jobs.values(), key=lambda item: item["created_at"], reverse=True)
    return {
        "jobs": [
            ExportJob(
                job_id=item["job_id"],
                status=item["status"],
                data_types=item["data_types"],
                format=item["format"],
                created_at=item["created_at"],
                completed_at=item.get("completed_at"),
                download_url=item.get("download_url"),
                file_size_bytes=item.get("file_size_bytes"),
                expires_at=item.get("expires_at"),
            )
            for item in jobs[:limit]
        ]
    }


@router.get("/jobs/{job_id}")
def get_export_job(job_id: str):
    job = _export_jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Export job not found")

    return ExportJob(
        job_id=job["job_id"],
        status=job["status"],
        data_types=job["data_types"],
        format=job["format"],
        created_at=job["created_at"],
        completed_at=job.get("completed_at"),
        download_url=job.get("download_url"),
        file_size_bytes=job.get("file_size_bytes"),
        expires_at=job.get("expires_at"),
    )


@router.get("/download/{job_id}")
def download_export(job_id: str):
    job = _export_jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Export job not found")

    if job["status"] != "completed":
        raise HTTPException(400, f"Export not ready (status: {job['status']})")

    if job.get("expires_at") and datetime.fromisoformat(job["expires_at"]) < datetime.utcnow():
        raise HTTPException(410, "Export has expired")

    return Response(
        content=job.get("_content", ""),
        media_type=job.get("_content_type", "application/octet-stream"),
        headers={"Content-Disposition": f'attachment; filename="{job.get("_filename", "export.dat")}"'},
    )


@router.delete("/jobs/{job_id}")
def delete_export_job(job_id: str):
    if job_id not in _export_jobs:
        raise HTTPException(404, "Export job not found")
    del _export_jobs[job_id]
    return {"deleted": True}


@router.get("/mcp/schema")
def get_mcp_schema():
    return {
        "name": "enterprise-intelligence",
        "version": "1.0.0",
        "description": "Access to persisted Enterprise Intelligence data",
        "resources": [
            {
                "name": dtype,
                "uri": f"/export/mcp/{dtype}",
                "description": meta["description"],
            }
            for dtype, meta in _DATA_TYPE_META.items()
        ],
    }


@router.get("/mcp/{resource_type}")
def get_mcp_resource(resource_type: str, db: Session = Depends(get_db)):
    Base.metadata.create_all(bind=db.get_bind())
    if resource_type not in _DATA_TYPE_META:
        raise HTTPException(404, f"Resource not found: {resource_type}")

    data = _collect_data(db, [resource_type])[resource_type]
    return {
        "resource": resource_type,
        "data": data,
        "meta": {
            "count": len(data),
            "source": "database" if resource_type != "tracking" else "unavailable",
            "retrieved_at": datetime.utcnow().isoformat(),
        },
    }
