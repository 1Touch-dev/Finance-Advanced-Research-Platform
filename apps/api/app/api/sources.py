from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text, update
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.base import Base
from app.models.sources import (
    Source,
    SourceCheckpoint,
    SourceContract,
    SourceCredential,
    SourceDeadLetter,
    SourceRecordMeta,
    SourceRun,
)

router = APIRouter(prefix="/sources")


class RunStatusUpdate(BaseModel):
    status: str
    metrics: Optional[dict] = None
    error: Optional[str] = None


class SourceRecordUpsert(BaseModel):
    source_id: int
    external_id: str
    run_id: Optional[int] = None
    normalized: Optional[dict] = None
    evidence_ref_id: Optional[int] = None


class DlqBatch(BaseModel):
    run_id: int
    items: list


@router.post("/bootstrap")
def bootstrap(db: Session = Depends(get_db)):
    Base.metadata.create_all(bind=db.get_bind())
    return {"ok": True}


@router.post("/")
def create_source(name: str, kind: str, workspace_id: int | None = None, db: Session = Depends(get_db)):
    src = Source(name=name, kind=kind, workspace_id=workspace_id)
    db.add(src)
    db.commit()
    db.refresh(src)
    return {"id": src.id, "name": src.name, "kind": src.kind}


@router.post("/{source_id}/credentials")
def upsert_credentials(source_id: int, kind: str, secret: dict, db: Session = Depends(get_db)):
    cred = SourceCredential(source_id=source_id, kind=kind, secret=secret)
    db.add(cred)
    db.commit()
    db.refresh(cred)
    return {"id": cred.id}


@router.post("/{source_id}/contracts")
def add_contract(source_id: int, version: str, spec: str, db: Session = Depends(get_db)):
    c = SourceContract(source_id=source_id, version=version, spec=spec)
    db.add(c)
    db.commit()
    db.refresh(c)
    return {"id": c.id}


@router.post("/{source_id}/runs")
def trigger_run(source_id: int, checkpoint: dict | None = None, db: Session = Depends(get_db)):
    run = SourceRun(source_id=source_id, status="pending", checkpoint=checkpoint)
    db.add(run)
    db.commit()
    db.refresh(run)
    return {"run_id": run.id, "status": run.status}


@router.post("/runs/{run_id}/status")
def update_run_status(
    run_id: int,
    body: RunStatusUpdate,
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    values = {"status": body.status, "metrics": body.metrics}
    if body.status in ("success", "error", "partial"):
        values["finished_at"] = now
        if body.error:
            values["error"] = body.error
    db.execute(update(SourceRun).where(SourceRun.id == run_id).values(**values))
    db.commit()
    return {"ok": True}


@router.post("/records")
def upsert_record(
    body: SourceRecordUpsert,
    db: Session = Depends(get_db),
):
    row = db.query(SourceRecordMeta).filter_by(source_id=body.source_id, external_id=body.external_id).first()
    if row:
        row.run_id = body.run_id
        row.normalized = body.normalized
        row.evidence_ref_id = body.evidence_ref_id
        row.last_ingested_at = datetime.now(timezone.utc)
    else:
        row = SourceRecordMeta(
            source_id=body.source_id,
            run_id=body.run_id,
            external_id=body.external_id,
            normalized=body.normalized,
            evidence_ref_id=body.evidence_ref_id,
        )
        db.add(row)
    db.commit()
    return {"ok": True, "external_id": body.external_id}


@router.post("/dlq")
def add_dlq(body: DlqBatch, db: Session = Depends(get_db)):
    for item in body.items:
        db.add(
            SourceDeadLetter(
                run_id=body.run_id,
                external_id=item.get("external_id"),
                error=item.get("error", "unknown"),
                payload=item,
            )
        )
    db.commit()
    return {"count": len(body.items)}


@router.get("/checkpoints/{source_id}")
def get_checkpoint(source_id: int, cursor_key: str = "default", db: Session = Depends(get_db)):
    row = db.query(SourceCheckpoint).filter_by(source_id=source_id, cursor_key=cursor_key).first()
    return {"state": row.state if row else {}}


@router.post("/checkpoints/{source_id}")
def save_checkpoint(source_id: int, state: dict, cursor_key: str = "default", db: Session = Depends(get_db)):
    row = db.query(SourceCheckpoint).filter_by(source_id=source_id, cursor_key=cursor_key).first()
    if row:
        row.state = state
    else:
        row = SourceCheckpoint(source_id=source_id, cursor_key=cursor_key, state=state)
        db.add(row)
    db.commit()
    return {"ok": True}


@router.get("/runs")
def list_runs(limit: int = 50, db: Session = Depends(get_db)):
    rows = (
        db.query(SourceRun)
        .order_by(SourceRun.id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "source_id": r.source_id,
            "status": r.status,
            "metrics": r.metrics,
            "started_at": str(r.started_at),
            "finished_at": str(r.finished_at) if r.finished_at else None,
            "error": r.error,
        }
        for r in rows
    ]


@router.get("/{source_id}/health")
def source_health(source_id: int, db: Session = Depends(get_db)):
    row = db.execute(
        text("select status, started_at, finished_at, metrics, error from source_runs where source_id=:sid order by id desc limit 1"),
        {"sid": source_id},
    ).fetchone()
    records = db.execute(
        text("select count(*) from source_record_meta where source_id=:sid"),
        {"sid": source_id},
    ).scalar() or 0
    if not row:
        return {"status": "unknown", "records": records}
    return {
        "status": row[0],
        "started_at": str(row[1]),
        "finished_at": str(row[2]),
        "metrics": row[3],
        "error": row[4],
        "records": records,
    }


@router.get("/health")
def registry_health(db: Session = Depends(get_db)):
    total = db.execute(text("select count(*) from sources")).scalar() or 0
    runs = db.execute(text("select count(*) from source_runs")).scalar() or 0
    errors = db.execute(text("select count(*) from source_runs where status='error'")).scalar() or 0
    success = db.execute(text("select count(*) from source_runs where status='success'")).scalar() or 0
    dlq = db.execute(text("select count(*) from source_dead_letters")).scalar() or 0
    sources = db.execute(text("select id, name, kind from sources")).fetchall()
    per_source = []
    for s in sources:
        last = db.execute(
            text("select status, finished_at, metrics from source_runs where source_id=:sid order by id desc limit 1"),
            {"sid": s[0]},
        ).fetchone()
        per_source.append({
            "id": s[0],
            "name": s[1],
            "kind": s[2],
            "last_status": last[0] if last else "never_run",
            "last_finished": str(last[1]) if last and last[1] else None,
            "last_metrics": last[2] if last else None,
        })
    return {
        "sources": total,
        "runs": runs,
        "errors": errors,
        "success": success,
        "dlq": dlq,
        "success_rate": (success / runs) if runs else 0,
        "per_source": per_source,
    }
