"""
Portable Corpora Export API
Band A Priority #13: Export, API, and MCP access to user data
"""
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.auth.security import get_current_user
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.session import get_db
import uuid
import json
import csv
import io

router = APIRouter(prefix="/export", tags=["export"])


# ─── Models ─────────────────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    data_types: List[str]  # watchlists, alerts, reports, entities, tracking
    format: str  # json, csv, parquet
    include_metadata: bool = True
    date_range: Optional[dict] = None  # {"start": "2026-01-01", "end": "2026-08-01"}


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


# ─── In-Memory Storage ──────────────────────────────────────────────────────

_export_jobs: Dict[str, dict] = {}

# Mock user data for export
_user_data = {
    "watchlists": [
        {"id": "wl-1", "name": "Tech Giants", "symbols": ["AAPL", "GOOGL", "MSFT", "AMZN"], "created_at": "2026-01-15"},
        {"id": "wl-2", "name": "Value Picks", "symbols": ["BRK.B", "JPM", "JNJ"], "created_at": "2026-03-20"},
    ],
    "alerts": [
        {"id": "alert-1", "type": "price", "symbol": "AAPL", "condition": "above", "value": 200, "active": True},
        {"id": "alert-2", "type": "filing", "entity": "Tesla Inc", "filing_type": "10-K", "active": True},
    ],
    "reports": [
        {"id": "rpt-1", "entity": "Apple Inc", "type": "intelligence", "created_at": "2026-07-01"},
        {"id": "rpt-2", "entity": "Microsoft", "type": "valuation", "created_at": "2026-07-15"},
    ],
    "entities": [
        {"id": "ent-1", "name": "Apple Inc", "type": "company", "ticker": "AAPL", "tracked_since": "2026-01-01"},
        {"id": "ent-2", "name": "Elon Musk", "type": "person", "role": "CEO", "tracked_since": "2026-02-15"},
    ],
    "tracking": [
        {"id": "trk-1", "entity_id": "ent-1", "event_type": "sec_filing", "last_checked": "2026-08-05"},
        {"id": "trk-2", "entity_id": "ent-2", "event_type": "insider_trade", "last_checked": "2026-08-05"},
    ],
}


# ─── Helper Functions ───────────────────────────────────────────────────────

def _to_csv(data: List[dict]) -> str:
    """Convert list of dicts to CSV string."""
    if not data:
        return ""

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()


def _generate_export(data_types: List[str], format: str, include_metadata: bool) -> tuple:
    """Generate export content and return (content, content_type, filename)."""
    export_data = {}

    for dtype in data_types:
        if dtype in _user_data:
            export_data[dtype] = _user_data[dtype]

    if include_metadata:
        export_data["_metadata"] = {
            "exported_at": datetime.utcnow().isoformat(),
            "data_types": data_types,
            "record_counts": {k: len(v) for k, v in export_data.items() if k != "_metadata"},
            "format": format,
            "platform": "Enterprise Intelligence",
            "version": "1.0",
        }

    if format == "json":
        content = json.dumps(export_data, indent=2)
        return content, "application/json", "export.json"

    elif format == "csv":
        # For CSV, we create a ZIP-like structure or concatenate with headers
        # For simplicity, we'll just export the first data type as CSV
        if data_types:
            first_type = data_types[0]
            if first_type in export_data:
                content = _to_csv(export_data[first_type])
                return content, "text/csv", f"{first_type}.csv"
        return "", "text/csv", "empty.csv"

    else:
        raise HTTPException(400, f"Unsupported format: {format}")


# ─── Routes ─────────────────────────────────────────────────────────────────

@router.get("/available-data")
def list_available_data():
    """List data types available for export."""
    return {
        "data_types": [
            {
                "id": "watchlists",
                "name": "Watchlists",
                "description": "Your saved watchlists and their symbols",
                "record_count": len(_user_data.get("watchlists", [])),
            },
            {
                "id": "alerts",
                "name": "Alerts",
                "description": "Your configured price and event alerts",
                "record_count": len(_user_data.get("alerts", [])),
            },
            {
                "id": "reports",
                "name": "Saved Reports",
                "description": "Intelligence reports you've generated",
                "record_count": len(_user_data.get("reports", [])),
            },
            {
                "id": "entities",
                "name": "Tracked Entities",
                "description": "Companies, people, and organizations you track",
                "record_count": len(_user_data.get("entities", [])),
            },
            {
                "id": "tracking",
                "name": "Tracking Configuration",
                "description": "Your entity tracking settings",
                "record_count": len(_user_data.get("tracking", [])),
            },
        ],
        "formats": ["json", "csv"],
    }


@router.post("/request")
def request_export(request: ExportRequest, current_user: dict = Depends(get_current_user)):
    """Request a data export."""
    job_id = f"export-{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow()

    # Validate data types
    valid_types = ["watchlists", "alerts", "reports", "entities", "tracking"]
    invalid = [t for t in request.data_types if t not in valid_types]
    if invalid:
        raise HTTPException(400, f"Invalid data types: {invalid}")

    # Create job
    job = {
        "job_id": job_id,
        "user_id": "demo",
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

    # For demo, process immediately
    try:
        content, content_type, filename = _generate_export(
            request.data_types,
            request.format,
            request.include_metadata,
        )

        job["status"] = "completed"
        job["completed_at"] = datetime.utcnow().isoformat()
        job["download_url"] = f"/export/download/{job_id}"
        job["file_size_bytes"] = len(content.encode())
        job["expires_at"] = (now + __import__("datetime").timedelta(days=7)).isoformat()
        job["_content"] = content
        job["_content_type"] = content_type
        job["_filename"] = filename

    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)

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
    """List recent export jobs."""
    jobs = list(_export_jobs.values())
    jobs.sort(key=lambda x: x["created_at"], reverse=True)

    return {
        "jobs": [
            ExportJob(
                job_id=j["job_id"],
                status=j["status"],
                data_types=j["data_types"],
                format=j["format"],
                created_at=j["created_at"],
                completed_at=j.get("completed_at"),
                download_url=j.get("download_url"),
                file_size_bytes=j.get("file_size_bytes"),
                expires_at=j.get("expires_at"),
            )
            for j in jobs[:limit]
        ]
    }


@router.get("/jobs/{job_id}")
def get_export_job(job_id: str):
    """Get export job status."""
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
    """Download completed export."""
    job = _export_jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Export job not found")

    if job["status"] != "completed":
        raise HTTPException(400, f"Export not ready (status: {job['status']})")

    # Check expiration
    if job.get("expires_at"):
        if datetime.fromisoformat(job["expires_at"]) < datetime.utcnow():
            raise HTTPException(410, "Export has expired")

    content = job.get("_content", "")
    content_type = job.get("_content_type", "application/octet-stream")
    filename = job.get("_filename", "export.dat")

    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.delete("/jobs/{job_id}")
def delete_export_job(job_id: str, current_user: dict = Depends(get_current_user)):
    """Delete an export job and its data."""
    if job_id not in _export_jobs:
        raise HTTPException(404, "Export job not found")

    del _export_jobs[job_id]
    return {"deleted": True}


# ─── MCP-Compatible Endpoints ───────────────────────────────────────────────

@router.get("/mcp/schema")
def get_mcp_schema():
    """Get MCP-compatible schema for data access."""
    return {
        "name": "enterprise-intelligence",
        "version": "1.0.0",
        "description": "Access to your Enterprise Intelligence data",
        "resources": [
            {
                "name": "watchlists",
                "uri": "/export/mcp/watchlists",
                "description": "Your saved watchlists",
            },
            {
                "name": "alerts",
                "uri": "/export/mcp/alerts",
                "description": "Your configured alerts",
            },
            {
                "name": "entities",
                "uri": "/export/mcp/entities",
                "description": "Your tracked entities",
            },
        ],
    }


@router.get("/mcp/{resource_type}")
def get_mcp_resource(resource_type: str):
    """Get resource data in MCP-compatible format."""
    if resource_type not in _user_data:
        raise HTTPException(404, f"Resource not found: {resource_type}")

    return {
        "resource": resource_type,
        "data": _user_data[resource_type],
        "meta": {
            "count": len(_user_data[resource_type]),
            "retrieved_at": datetime.utcnow().isoformat(),
        },
    }
