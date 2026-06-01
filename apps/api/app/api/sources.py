from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import update, text
from datetime import datetime, timezone
from app.db.session import get_db
from app.models.sources import Source, SourceCredential, SourceContract, SourceRun, SourceRecordMeta
from app.models.base import Base

router = APIRouter(prefix="/sources")

@router.post('/bootstrap')
def bootstrap(db: Session = Depends(get_db)):
    Base.metadata.create_all(bind=db.get_bind())
    return {"ok": True}

@router.post('/')
def create_source(name: str, kind: str, workspace_id: int | None = None, db: Session = Depends(get_db)):
    src = Source(name=name, kind=kind, workspace_id=workspace_id)
    db.add(src); db.commit(); db.refresh(src)
    return {"id": src.id, "name": src.name, "kind": src.kind}

@router.post('/{source_id}/credentials')
def upsert_credentials(source_id: int, kind: str, secret: dict, db: Session = Depends(get_db)):
    cred = SourceCredential(source_id=source_id, kind=kind, secret=secret)
    db.add(cred); db.commit(); db.refresh(cred)
    return {"id": cred.id}

@router.post('/{source_id}/contracts')
def add_contract(source_id: int, version: str, spec: str, db: Session = Depends(get_db)):
    c = SourceContract(source_id=source_id, version=version, spec=spec)
    db.add(c); db.commit(); db.refresh(c)
    return {"id": c.id}

@router.post('/{source_id}/runs')
def trigger_run(source_id: int, checkpoint: dict | None = None, db: Session = Depends(get_db)):
    run = SourceRun(source_id=source_id, status='pending', checkpoint=checkpoint)
    db.add(run); db.commit(); db.refresh(run)
    return {"run_id": run.id, "status": run.status}

@router.post('/runs/{run_id}/status')
def update_run_status(run_id: int, status: str, metrics: dict | None = None, error: str | None = None, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    values = {"status": status, "metrics": metrics}
    if status in ("success","error"):
        values["finished_at"] = now
        if error:
            values["error"] = error
    db.execute(update(SourceRun).where(SourceRun.id==run_id).values(**values))
    db.commit()
    return {"ok": True}

@router.get('/{source_id}/health')
def source_health(source_id: int, db: Session = Depends(get_db)):
    row = db.execute(
        text("select status, started_at, finished_at from source_runs where source_id=:sid order by id desc limit 1"),
        {"sid": source_id}
    ).fetchone()
    if not row:
        return {"status": "unknown"}
    return {"status": row[0], "started_at": str(row[1]), "finished_at": str(row[2])}

@router.get('/health')
def registry_health(db: Session = Depends(get_db)):
    total = db.execute(text("select count(*) from sources")).scalar() or 0
    runs = db.execute(text("select count(*) from source_runs")).scalar() or 0
    errors = db.execute(text("select count(*) from source_runs where status='error'")).scalar() or 0
    return {"sources": total, "runs": runs, "errors": errors}
