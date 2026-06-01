from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, update
from typing import List, Dict, Any, Optional
from app.db.session import get_db
from app.models.base import Base
from app.models.reports import Report, ReportSection, EvidenceBundle, Claim, ClaimEvidence

router = APIRouter(prefix="/reports")

@router.post('/bootstrap')
def bootstrap(db: Session = Depends(get_db)):
    Base.metadata.create_all(bind=db.get_bind())
    return {"ok": True}

@router.post('/')
def create_report(title: str, kind: str, db: Session = Depends(get_db)):
    r = Report(title=title, kind=kind)
    db.add(r); db.commit(); db.refresh(r)
    return {"id": r.id, "title": r.title, "kind": r.kind}

@router.post('/{report_id}/sections')
def add_section(report_id: int, name: str, content: Optional[str] = None, order: int = 0, db: Session = Depends(get_db)):
    s = ReportSection(report_id=report_id, name=name, content=content, order=order)
    db.add(s); db.commit(); db.refresh(s)
    return {"id": s.id}

@router.post('/{report_id}/bundles')
def add_bundle(report_id: int, name: str, items: Optional[List[int]] = None, db: Session = Depends(get_db)):
    b = EvidenceBundle(report_id=report_id, name=name, items=items or [])
    db.add(b); db.commit(); db.refresh(b)
    return {"id": b.id}

@router.post('/{report_id}/claims')
def add_claim(report_id: int, text: str, db: Session = Depends(get_db)):
    c = Claim(report_id=report_id, text=text)
    db.add(c); db.commit(); db.refresh(c)
    return {"id": c.id}

@router.post('/claims/{claim_id}/evidence')
def attach_claim_evidence(claim_id: int, evidence_ref_id: int, weight: int = 1, db: Session = Depends(get_db)):
    ce = ClaimEvidence(claim_id=claim_id, evidence_ref_id=evidence_ref_id, weight=weight)
    db.add(ce); db.commit(); db.refresh(ce)
    return {"id": ce.id}

@router.post('/claims/{claim_id}/verify')
def verify_claim(claim_id: int, db: Session = Depends(get_db)):
    # simple verifier: ensure attached evidence refs exist and are not contradictory by timestamp overlap (placeholder)
    rows = db.execute(text("select evidence_ref_id from claim_evidence where claim_id=:cid"), {"cid": claim_id}).fetchall()
    if not rows:
        db.execute(update(Claim).where(Claim.id==claim_id).values(status='needs_review'))
        db.commit(); return {"status": "needs_review", "reason": "no evidence"}
    # check that refs exist in evidence_refs
    missing = []
    for r in rows:
        er = db.execute(text("select id from evidence_refs where id=:id"), {"id": r[0]}).fetchone()
        if not er:
            missing.append(r[0])
    if missing:
        db.execute(update(Claim).where(Claim.id==claim_id).values(status='needs_review'))
        db.commit(); return {"status": "needs_review", "reason": f"missing refs {missing}"}
    # mark verified
    db.execute(update(Claim).where(Claim.id==claim_id).values(status='verified'))
    db.commit(); return {"status": "verified"}

@router.post('/claims/{claim_id}/contradict')
def contradict_claim(claim_id: int, note: Optional[str] = None, db: Session = Depends(get_db)):
    db.execute(update(Claim).where(Claim.id==claim_id).values(status='contradicted', contradiction_note=note))
    db.commit(); return {"status": "contradicted"}

@router.get('/{report_id}')
def get_report(report_id: int, db: Session = Depends(get_db)):
    r = db.query(Report).filter_by(id=report_id).first()
    if not r: raise HTTPException(404, 'not found')
    secs = db.execute(text('select id,name,content,"order" from report_sections where report_id=:id order by "order"'), {"id": report_id}).fetchall()
    clms = db.execute(text("select id,text,status,contradiction_note from claims where report_id=:id"), {"id": report_id}).fetchall()
    buns = db.execute(text("select id,name,items from evidence_bundles where report_id=:id"), {"id": report_id}).fetchall()
    return {
        "id": r.id, "title": r.title, "kind": r.kind, "status": r.status,
        "sections": [{"id": s[0], "name": s[1], "content": s[2], "order": s[3]} for s in secs],
        "claims": [{"id": c[0], "text": c[1], "status": c[2], "note": c[3]} for c in clms],
        "bundles": [{"id": b[0], "name": b[1], "items": b[2]} for b in buns]
    }

@router.post('/{report_id}/status')
def set_status(report_id: int, status: str, db: Session = Depends(get_db)):
    db.execute(update(Report).where(Report.id==report_id).values(status=status))
    db.commit(); return {"ok": True}
