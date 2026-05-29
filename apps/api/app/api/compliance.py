from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import update
from typing import Optional
from app.db.session import get_db
from app.models.base import Base
from app.models.compliance import Policy, ExportApproval

router = APIRouter(prefix="/compliance")

@router.post('/bootstrap')
def bootstrap(db: Session = Depends(get_db)):
    Base.metadata.create_all(bind=db.get_bind())
    return {"ok": True}

@router.post('/policies')
def create_policy(name: str, rules: Optional[dict] = None, db: Session = Depends(get_db)):
    p = Policy(name=name, rules=rules or {})
    db.add(p); db.commit(); db.refresh(p)
    return {"id": p.id}

@router.post('/export/request')
def request_export(report_id: int, requested_by: Optional[str] = None, db: Session = Depends(get_db)):
    e = ExportApproval(report_id=report_id, requested_by=requested_by)
    db.add(e); db.commit(); db.refresh(e)
    return {"id": e.id, "status": e.status}

@router.post('/export/{eid}/approve')
def approve_export(eid: int, approve: bool = True, notes: Optional[str] = None, db: Session = Depends(get_db)):
    status = 'approved' if approve else 'rejected'
    db.execute(update(ExportApproval).where(ExportApproval.id==eid).values(status=status, notes=notes))
    db.commit(); return {"status": status}
