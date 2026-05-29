from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.services.opensearch_client import OpenSearchClient
from sqlalchemy import text

router = APIRouter(prefix="/searchos")

@router.get('/')
def fulltext(q: str, size: int = 20, db: Session = Depends(get_db)):
    # hybrid-ready: fetch snippets from DB as fallback, OS client stub for structure
    osclient = OpenSearchClient()
    os_hits = osclient.search(q, size=size)
    # DB fallback: search URLs in raw_documents
    rows = db.execute(text("select id, source_url from raw_documents where source_url ilike :q limit :lim"), {"q": f"%{q}%", "lim": size}).fetchall()
    return {"opensearch": os_hits, "db_snippets": [{"id": r[0], "url": r[1]} for r in rows]}

@router.post('/index/doc')
def index_doc(doc_id: int, db: Session = Depends(get_db)):
    row = db.execute(text("select id, source_url, meta from raw_documents where id=:id"), {"id": doc_id}).fetchone()
    if not row:
        return {"ok": False, "reason": "not found"}
    body = {"url": row[1], "meta": row[2]}
    return OpenSearchClient().index_document(str(row[0]), body)
