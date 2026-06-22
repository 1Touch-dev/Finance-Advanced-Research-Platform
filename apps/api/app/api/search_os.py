from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.opensearch_client import OpenSearchClient

router = APIRouter(prefix="/searchos")


def _index_body(row) -> dict:
    meta = row[3] or {}
    excerpt = row[4] or ""
    return {
        "title": meta.get("filename") or row[2] or "",
        "content": str(meta),
        "excerpt": excerpt[:500] if excerpt else str(meta)[:500],
        "source_url": row[2],
        "source_native_id": row[5],
        "source_id": row[6],
    }


@router.get("/")
def fulltext(q: str, size: int = 20, db: Session = Depends(get_db)):
    osclient = OpenSearchClient()
    os_hits = osclient.search(q, size=size)
    if not os_hits.get("hits"):
        rows = db.execute(
            text("""
                select rd.id, rd.sha256, rd.source_url, rd.meta, er.excerpt, rd.source_native_id, rd.source_id
                from raw_documents rd
                left join evidence_refs er on er.raw_document_id = rd.id
                where rd.source_url ilike :q or rd.source_native_id ilike :q
                   or cast(rd.meta as text) ilike :q or er.excerpt ilike :q
                limit :lim
            """),
            {"q": f"%{q}%", "lim": size},
        ).fetchall()
        for row in rows:
            osclient.index_document(str(row[0]), _index_body(row))
        os_hits = osclient.search(q, size=size)
    rows = db.execute(
        text("select id, source_url from raw_documents where source_url ilike :q limit :lim"),
        {"q": f"%{q}%", "lim": size},
    ).fetchall()
    return {"opensearch": os_hits, "db_snippets": [{"id": r[0], "url": r[1]} for r in rows]}


@router.post("/index/doc")
def index_doc(doc_id: int, db: Session = Depends(get_db)):
    row = db.execute(
        text("""
            select rd.id, rd.sha256, rd.source_url, rd.meta, er.excerpt, rd.source_native_id, rd.source_id
            from raw_documents rd
            left join evidence_refs er on er.raw_document_id = rd.id
            where rd.id = :id
            limit 1
        """),
        {"id": doc_id},
    ).fetchone()
    if not row:
        return {"ok": False, "reason": "not found"}
    return OpenSearchClient().index_document(str(row[0]), _index_body(row))


@router.post("/index/rebuild")
def rebuild_index(db: Session = Depends(get_db)):
    osclient = OpenSearchClient()
    rows = db.execute(
        text("""
            select rd.id, rd.sha256, rd.source_url, rd.meta, er.excerpt, rd.source_native_id, rd.source_id
            from raw_documents rd
            left join evidence_refs er on er.raw_document_id = rd.id
        """)
    ).fetchall()
    count = 0
    for row in rows:
        osclient.index_document(str(row[0]), _index_body(row))
        count += 1
    return {"ok": True, "indexed": count}
