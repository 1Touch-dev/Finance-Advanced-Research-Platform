from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text, update
from typing import Optional
from difflib import unified_diff
from app.db.session import get_db
from app.models.base import Base
from app.models.reports import ReportSection, Claim
from app.models.review import Comment, Suggestion, SectionVersion, ReviewerAssignment, ReviewTask

router = APIRouter(prefix="/review")

@router.post('/bootstrap')
def bootstrap(db: Session = Depends(get_db)):
    Base.metadata.create_all(bind=db.get_bind())
    return {"ok": True}

@router.post('/comments')
def add_comment(report_id: int, section_id: Optional[int] = None, text: str = '', author: Optional[str] = None, db: Session = Depends(get_db)):
    c = Comment(report_id=report_id, section_id=section_id, text=text, author=author)
    db.add(c); db.commit(); db.refresh(c)
    return {"id": c.id}

@router.post('/suggest')
def suggest(report_id: int, section_id: int, proposed: str, db: Session = Depends(get_db)):
    s = Suggestion(report_id=report_id, section_id=section_id, proposed=proposed)
    db.add(s); db.commit(); db.refresh(s)
    return {"id": s.id}

@router.post('/suggestions/{sid}/accept')
def accept_suggestion(sid: int, db: Session = Depends(get_db)):
    s = db.query(Suggestion).filter_by(id=sid).first()
    if not s: raise HTTPException(404, 'not found')
    sec = db.query(ReportSection).filter_by(id=s.section_id).first()
    # version old
    db.add(SectionVersion(section_id=sec.id, content=sec.content))
    # apply
    sec.content = s.proposed
    db.execute(update(Suggestion).where(Suggestion.id==sid).values(state='accepted'))
    db.commit(); return {"ok": True}

@router.post('/suggestions/{sid}/reject')
def reject_suggestion(sid: int, db: Session = Depends(get_db)):
    db.execute(update(Suggestion).where(Suggestion.id==sid).values(state='rejected'))
    db.commit(); return {"ok": True}

@router.get('/sections/{section_id}/versions')
def section_versions(section_id: int, db: Session = Depends(get_db)):
    rows = db.query(SectionVersion).filter_by(section_id=section_id).order_by(SectionVersion.created_at.desc()).all()
    return [{"id": r.id, "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]

@router.get('/sections/{section_id}/diff')
def section_diff(section_id: int, v1: int, v2: int, db: Session = Depends(get_db)):
    a = db.query(SectionVersion).filter_by(id=v1, section_id=section_id).first()
    b = db.query(SectionVersion).filter_by(id=v2, section_id=section_id).first()
    if not a or not b: raise HTTPException(404, 'version not found')
    diff = unified_diff((a.content or '').splitlines(), (b.content or '').splitlines(), lineterm='')
    return {"diff": list(diff)}

@router.post('/assign')
def assign_reviewer(report_id: int, reviewer: str, role: str = 'reviewer', db: Session = Depends(get_db)):
    db.add(ReviewerAssignment(report_id=report_id, reviewer=reviewer, role=role)); db.commit(); return {"ok": True}

@router.post('/tasks')
def create_task(report_id: int, kind: str, payload: Optional[dict] = None, db: Session = Depends(get_db)):
    db.add(ReviewTask(report_id=report_id, kind=kind, payload=payload or {})); db.commit(); return {"ok": True}

@router.post('/reverify')
def reverify(report_id: int, db: Session = Depends(get_db)):
    # iterate claims and call verify
    claims = db.execute(text("select id from claims where report_id=:id"), {"id": report_id}).fetchall()
    results = []
    for c in claims:
        cid = c[0]
        # reuse reports API function via SQL directly
        rows = db.execute(text("select evidence_ref_id from claim_evidence where claim_id=:cid"), {"cid": cid}).fetchall()
        status = 'verified' if rows else 'needs_review'
        db.execute(update(Claim).where(Claim.id==cid).values(status=status))
        results.append({"claim_id": cid, "status": status})
    db.commit(); return {"results": results}

@router.post('/enhance/section')
def enhance_section(section_id: int, skill: str = 'one_pager', db: Session = Depends(get_db)):
    # placeholder: record a task; external worker/skills gateway will process
    sec = db.query(ReportSection).filter_by(id=section_id).first()
    db.add(ReviewTask(report_id=sec.report_id, kind='enhance_section', payload={"section_id": section_id, "skill": skill}))
    db.commit(); return {"queued": True}

# --- Exports (stubs for Phase 1) ---
import os, json, csv
EXPORT_DIR = os.getenv('EXPORT_DIR', 'exports')
os.makedirs(EXPORT_DIR, exist_ok=True)

@router.get('/export/{report_id}/markdown')
def export_markdown(report_id: int, db: Session = Depends(get_db)):
    rep = db.execute(text("select title,kind,status from reports where id=:id"), {"id": report_id}).fetchone()
    secs = db.execute(text("select name,content,\"order\" from report_sections where report_id=:id order by \"order\""), {"id": report_id}).fetchall()
    lines = [f"# {rep[0]} ({rep[1]})", f"Status: {rep[2]}", ""]
    for s in secs:
        lines.append(f"## {s[0]}")
        lines.append(s[1] or '')
        lines.append('')
    path = os.path.join(EXPORT_DIR, f'report-{report_id}.md')
    with open(path,'w') as f: f.write("\n".join(lines))
    return {"path": path}

@router.get('/export/{report_id}/html')
def export_html(report_id: int, db: Session = Depends(get_db)):
    md = export_markdown(report_id, db)
    with open(md['path'],'r') as f: body = f.read()
    html = f"<html><body><pre>{body}</pre></body></html>"
    path = md['path'].replace('.md','.html')
    with open(path,'w') as f: f.write(html)
    return {"path": path}

@router.get('/export/{report_id}/json')
def export_json(report_id: int, db: Session = Depends(get_db)):
    data = db.execute(text("select id,title,kind,status from reports where id=:id"), {"id": report_id}).fetchone()
    secs = db.execute(text("select name,content,\"order\" from report_sections where report_id=:id order by \"order\""), {"id": report_id}).fetchall()
    out = {"id": data[0], "title": data[1], "kind": data[2], "status": data[3],
           "sections": [{"name": s[0], "content": s[1], "order": s[2]} for s in secs]}
    path = os.path.join(EXPORT_DIR, f'report-{report_id}.json')
    with open(path,'w') as f: json.dump(out,f,indent=2)
    return {"path": path}

@router.get('/export/{report_id}/evidence_csv')
def export_evidence_csv(report_id: int, db: Session = Depends(get_db)):
    rows = db.execute(text("""
      select c.id as claim_id, ce.evidence_ref_id from claims c
      join claim_evidence ce on ce.claim_id=c.id
      where c.report_id=:id
    """), {"id": report_id}).fetchall()
    path = os.path.join(EXPORT_DIR, f'report-{report_id}-evidence.csv')
    with open(path,'w',newline='') as f:
        w=csv.writer(f); w.writerow(['claim_id','evidence_ref_id'])
        for r in rows: w.writerow([r[0], r[1]])
    return {"path": path}
