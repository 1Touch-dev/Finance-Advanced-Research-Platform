from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, text
from typing import Optional, List
from datetime import datetime
from app.db.session import get_db
from app.models.entities import Entity, Relationship
from app.models.evidence import RawDocument, EvidenceRef
from app.models.sources import Source, SourceRun

router = APIRouter(prefix="/search")

def _safe_isoformat(val):
    if not val:
        return None
    if isinstance(val, str):
        return val.replace(" ", "T")
    try:
        return val.isoformat()
    except AttributeError:
        return str(val)

@router.get('/')
def global_search(q: Optional[str] = None, type: Optional[str] = None, source: Optional[str] = None,
                  date_from: Optional[str] = None, date_to: Optional[str] = None,
                  confidence: Optional[int] = None, limit: int = 20, db: Session = Depends(get_db)):
    results = {"entities": [], "documents": [], "relationships": []}
    # Entities by name alias match
    if q:
        ents = db.query(Entity).filter(Entity.name.ilike(f"%{q}%"))
        if type:
            ents = ents.filter(Entity.kind == type)
        ents = ents.limit(limit).all()
        results["entities"] = [{"id": e.id, "name": e.name, "kind": e.kind} for e in ents]
    # Documents by meta/URL
    docs = db.query(RawDocument)
    if q:
        docs = docs.filter(or_(RawDocument.source_url.ilike(f"%{q}%")))
    if date_from:
        try:
            df = datetime.fromisoformat(date_from)
            docs = docs.filter(RawDocument.created_at >= df)
        except Exception:
            pass
    if date_to:
        try:
            dt = datetime.fromisoformat(date_to)
            docs = docs.filter(RawDocument.created_at <= dt)
        except Exception:
            pass
    docs = docs.limit(limit).all()
    results["documents"] = [{"id": d.id, "url": d.source_url, "sha256": d.sha256, "created_at": d.created_at.isoformat() if d.created_at else None} for d in docs]
    # Relationships by src/dst names
    if q:
        rels = db.query(Relationship).limit(limit).all()
        out = []
        for r in rels:
            out.append({"id": r.id, "kind": r.kind, "src": r.src_entity_id, "dst": r.dst_entity_id})
        results["relationships"] = out
    return results

@router.get('/entities/{entity_id}')
def entity_profile(entity_id: int, db: Session = Depends(get_db)):
    e = db.query(Entity).filter_by(id=entity_id).first()
    if not e:
        return {"error": "not found"}
    aliases = [a.alias for a in db.execute(text("select alias from entity_aliases where entity_id=:id"), {"id": entity_id}).fetchall()]
    ids = db.execute(text("select scheme,value from entity_identifiers where entity_id=:id"), {"id": entity_id}).fetchall()
    return {
        "id": e.id,
        "name": e.name,
        "kind": e.kind,
        "aliases": aliases,
        "identifiers": [{"scheme": r[0], "value": r[1]} for r in ids],
    }

@router.get('/entities/{entity_id}/timeline')
def entity_timeline(entity_id: int, limit: int = 100, db: Session = Depends(get_db)):
    # Timeline from evidence refs and relationships
    refs = db.execute(
        text("""
        select er.id, rd.created_at, 'evidence' as kind
        from evidence_refs er
        join raw_documents rd on rd.id = er.raw_document_id
        where er.workspace_id is null or er.workspace_id is not null and er.raw_document_id = rd.id
        order by rd.created_at desc
        limit :lim
        """), {"lim": limit}
    ).fetchall()
    rels = db.execute(
        text("select id, null as created_at, 'relationship' as kind from relationships where src_entity_id=:id or dst_entity_id=:id limit :lim"),
        {"id": entity_id, "lim": limit}
    ).fetchall()
    items = []
    for r in refs:
        items.append({"id": r[0], "ts": _safe_isoformat(r[1]), "type": r[2]})
    for r in rels:
        items.append({"id": r[0], "ts": None, "type": r[2]})
    items.sort(key=lambda x: (x["ts"] or ''), reverse=True)
    return {"items": items[:limit]}

@router.get('/entities/{entity_id}/relationships')
def entity_relationships(entity_id: int, db: Session = Depends(get_db)):
    rows = db.execute(
        text("select id, src_entity_id, dst_entity_id, kind from relationships where src_entity_id=:id or dst_entity_id=:id"),
        {"id": entity_id}
    ).fetchall()
    return [{"id": r[0], "src": r[1], "dst": r[2], "kind": r[3]} for r in rows]

@router.get('/entities/{entity_id}/evidence')
def entity_evidence(entity_id: int, limit: int = 50, db: Session = Depends(get_db)):
    rows = db.execute(
        text("""
        select er.id, er.excerpt, rd.id as doc_id, rd.source_url, rd.created_at
        from evidence_refs er
        join raw_documents rd on rd.id = er.raw_document_id
        where er.project_id=:id or er.case_id=:id or er.workspace_id is not null
        order by rd.created_at desc limit :lim
        """), {"id": entity_id, "lim": limit}
    ).fetchall()
    return [
        {"ref_id": r[0], "excerpt": r[1], "doc_id": r[2], "source_url": r[3], "ts": _safe_isoformat(r[4])}
        for r in rows
    ]

# Saved/recent searches (Phase 1 basics)
@router.post('/saved')
def save_search(query: str, db: Session = Depends(get_db)):
    db.execute(text("create table if not exists saved_searches (id serial primary key, query text, created_at timestamp with time zone default now())"))
    db.execute(text("insert into saved_searches (query) values (:q)"), {"q": query}); db.commit()
    return {"ok": True}

@router.get('/saved')
def list_saved(db: Session = Depends(get_db)):
    rows = db.execute(text("select id, query, created_at from saved_searches order by id desc limit 50")).fetchall()
    return [{"id": r[0], "query": r[1], "created_at": _safe_isoformat(r[2])} for r in rows]

@router.post('/recent')
def add_recent(query: str, db: Session = Depends(get_db)):
    db.execute(text("create table if not exists recent_searches (id serial primary key, query text, created_at timestamp with time zone default now())"))
    db.execute(text("insert into recent_searches (query) values (:q)"), {"q": query}); db.commit()
    return {"ok": True}

@router.get('/recent')
def list_recent(db: Session = Depends(get_db)):
    rows = db.execute(text("select id, query, created_at from recent_searches order by id desc limit 50")).fetchall()
    return [{"id": r[0], "query": r[1], "created_at": _safe_isoformat(r[2])} for r in rows]
