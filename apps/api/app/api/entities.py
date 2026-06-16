from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from difflib import SequenceMatcher
from typing import Optional, List
from app.db.session import get_db
from app.models.base import Base
from app.models.entities import (
    Entity, EntityAlias, EntityIdentifier, Relationship, RelationshipEvidence,
    MergeCandidate, MergeAction, ResolutionQueue
)

router = APIRouter(prefix="/entities")

@router.post('/bootstrap')
def bootstrap(db: Session = Depends(get_db)):
    Base.metadata.create_all(bind=db.get_bind())
    return {"ok": True}

@router.post('/')
def create_entity(name: str, kind: str, db: Session = Depends(get_db)):
    e = Entity(name=name, kind=kind)
    db.add(e); db.commit(); db.refresh(e)
    return {"id": e.id, "name": e.name, "kind": e.kind}

@router.post('/{entity_id}/aliases')
def add_alias(entity_id: int, alias: str, db: Session = Depends(get_db)):
    a = EntityAlias(entity_id=entity_id, alias=alias)
    db.add(a); db.commit(); db.refresh(a)
    return {"id": a.id}

@router.post('/{entity_id}/identifiers')
def add_identifier(entity_id: int, scheme: str, value: str, db: Session = Depends(get_db)):
    # deterministic linking: if scheme+value exists for another entity, propose merge
    existing = db.query(EntityIdentifier).filter_by(scheme=scheme, value=value).first()
    if existing and existing.entity_id != entity_id:
        # create merge candidate with high score
        pair = sorted([existing.entity_id, entity_id])
        if not db.query(MergeCandidate).filter_by(a_entity_id=pair[0], b_entity_id=pair[1]).first():
            db.add(MergeCandidate(a_entity_id=pair[0], b_entity_id=pair[1], score=100, reason=f"deterministic match: {scheme}"))
        db.commit()
    i = EntityIdentifier(entity_id=entity_id, scheme=scheme.upper(), value=value)
    db.add(i); db.commit(); db.refresh(i)
    return {"id": i.id}

@router.get('/resolve')
def resolve(name: Optional[str] = None, scheme: Optional[str] = None, value: Optional[str] = None, threshold: int = 85, db: Session = Depends(get_db)):
    # Deterministic by identifier
    if scheme and value:
        ii = db.query(EntityIdentifier).filter_by(scheme=scheme.upper(), value=value).first()
        if ii:
            return {"match": {"entity_id": ii.entity_id, "confidence": 100, "method": "deterministic"}}
    # Probabilistic by name/aliases
    if name:
        cands = db.query(Entity).filter(or_(Entity.name.ilike(f"%{name}%"))).limit(50).all()
        best = None; best_score = 0
        for e in cands:
            for nm in [e.name] + [a.alias for a in db.query(EntityAlias).filter_by(entity_id=e.id).all()]:
                s = int(SequenceMatcher(None, name.lower(), nm.lower()).ratio() * 100)
                if s > best_score:
                    best, best_score = e, s
        if best and best_score >= threshold:
            # enqueue for review if not perfect
            if best_score < 100:
                db.add(ResolutionQueue(entity_id=best.id, reason=f"fuzzy {best_score}% for '{name}'"))
                db.commit()
            return {"match": {"entity_id": best.id, "confidence": best_score, "method": "fuzzy"}}
    return {"match": None}

@router.post('/relationships')
def create_relationship(src_entity_id: int, dst_entity_id: int, kind: str, db: Session = Depends(get_db)):
    r = Relationship(src_entity_id=src_entity_id, dst_entity_id=dst_entity_id, kind=kind)
    db.add(r); db.commit(); db.refresh(r)
    return {"id": r.id}

@router.post('/relationships/{rel_id}/evidence')
def add_relationship_evidence(rel_id: int, evidence_ref_id: Optional[int] = None, db: Session = Depends(get_db)):
    ev = RelationshipEvidence(relationship_id=rel_id, evidence_ref_id=evidence_ref_id)
    db.add(ev); db.commit(); db.refresh(ev)
    return {"id": ev.id}

@router.post('/merge/propose')
def propose_merge(a_entity_id: int, b_entity_id: int, score: int = 70, reason: Optional[str] = None, db: Session = Depends(get_db)):
    pair = sorted([a_entity_id, b_entity_id])
    if db.query(MergeCandidate).filter_by(a_entity_id=pair[0], b_entity_id=pair[1]).first():
        return {"ok": True}
    db.add(MergeCandidate(a_entity_id=pair[0], b_entity_id=pair[1], score=score, reason=reason or "manual"))
    db.commit()
    return {"ok": True}

@router.post('/merge/approve')
def approve_merge(primary_id: int, secondary_id: int, db: Session = Depends(get_db)):
    # Move aliases/identifiers/relationships from secondary to primary; record action for unmerge
    for a in db.query(EntityAlias).filter_by(entity_id=secondary_id).all():
        a.entity_id = primary_id
    for i in db.query(EntityIdentifier).filter_by(entity_id=secondary_id).all():
        # maintain unique constraint by reassigning; if conflict, skip
        exists = db.query(EntityIdentifier).filter_by(scheme=i.scheme, value=i.value).first()
        if exists and exists.entity_id == primary_id:
            pass
        else:
            i.entity_id = primary_id
    for r in db.query(Relationship).filter_by(src_entity_id=secondary_id).all():
        r.src_entity_id = primary_id
    for r in db.query(Relationship).filter_by(dst_entity_id=secondary_id).all():
        r.dst_entity_id = primary_id
    db.add(MergeAction(primary_id=primary_id, secondary_id=secondary_id, action='merge'))
    pair = sorted([primary_id, secondary_id])
    cand = db.query(MergeCandidate).filter_by(a_entity_id=pair[0], b_entity_id=pair[1]).first()
    if cand:
        cand.status = 'merged'
    sec = db.query(Entity).filter_by(id=secondary_id).first()
    if sec:
        sec.canonical = False
    db.commit()
    return {"ok": True}

@router.post('/merge/unmerge')
def unmerge(primary_id: int, secondary_id: int, db: Session = Depends(get_db)):
    # Naive: just toggle canonical and queue for review; detailed reversal would track per-record moves
    sec = db.query(Entity).filter_by(id=secondary_id).first()
    if sec:
        sec.canonical = True
    db.add(ResolutionQueue(entity_id=secondary_id, reason=f"unmerge from {primary_id}"))
    db.add(MergeAction(primary_id=primary_id, secondary_id=secondary_id, action='unmerge'))
    db.commit()
    return {"ok": True}

@router.get('/queue')
def review_queue(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.query(ResolutionQueue).order_by(ResolutionQueue.created_at.desc()).limit(limit).all()
    return [{"id": r.id, "entity_id": r.entity_id, "reason": r.reason, "created_at": r.created_at.isoformat() if r.created_at else None} for r in rows]

@router.get('/merge/candidates')
def merge_candidates(status: str = 'pending', limit: int = 50, db: Session = Depends(get_db)):
    rows = db.query(MergeCandidate).filter_by(status=status).order_by(MergeCandidate.score.desc()).limit(limit).all()
    out = []
    for r in rows:
        a = db.query(Entity).filter_by(id=r.a_entity_id).first()
        b = db.query(Entity).filter_by(id=r.b_entity_id).first()
        out.append({
            "id": r.id, "score": r.score, "reason": r.reason, "status": r.status,
            "a": {"id": r.a_entity_id, "name": a.name if a else None, "kind": a.kind if a else None},
            "b": {"id": r.b_entity_id, "name": b.name if b else None, "kind": b.kind if b else None},
        })
    return out

@router.post('/merge/reject')
def reject_merge(candidate_id: int, db: Session = Depends(get_db)):
    c = db.query(MergeCandidate).filter_by(id=candidate_id).first()
    if not c:
        raise HTTPException(404, 'not found')
    c.status = 'rejected'
    db.commit()
    return {"ok": True}
