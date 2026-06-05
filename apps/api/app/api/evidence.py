from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional
from app.db.session import get_db
from app.models.evidence import RawDocument, EvidenceRef
from app.models.base import Base
from app.storage.files import ensure_vault, compute_sha256, store_file

router = APIRouter(prefix="/evidence")

@router.post('/bootstrap')
def bootstrap(db: Session = Depends(get_db)):
    Base.metadata.create_all(bind=db.get_bind())
    ensure_vault()
    return {"ok": True}

@router.post('/raw')
async def upload_raw(
    file: UploadFile = File(...),
    workspace_id: Optional[int] = Form(None),
    source_url: Optional[str] = Form(None),
    source_native_id: Optional[str] = Form(None),
    source_id: Optional[int] = Form(None),
    source_run_id: Optional[int] = Form(None),
    uploader_user_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
):
    ensure_vault()
    contents = await file.read()
    from io import BytesIO
    bio = BytesIO(contents)
    sha, size = compute_sha256(bio)
    bio.seek(0)
    storage_path = store_file(bio, file.filename or sha, sha)

    doc = db.query(RawDocument).filter_by(sha256=sha).first()
    if not doc:
        doc = RawDocument(
            sha256=sha,
            content_type=file.content_type,
            size_bytes=size,
            storage_path=storage_path,
            source_url=source_url,
            source_native_id=source_native_id,
            source_id=source_id,
            source_run_id=source_run_id,
            uploader_user_id=uploader_user_id,
            meta={"filename": file.filename},
        )
        db.add(doc); db.commit(); db.refresh(doc)
    return {"id": doc.id, "sha256": doc.sha256, "size": doc.size_bytes, "path": storage_path}

@router.get('/raw/{doc_id}')
def get_raw(doc_id: int, download: bool = False, db: Session = Depends(get_db)):
    doc = db.query(RawDocument).filter_by(id=doc_id).first()
    if not doc:
        raise HTTPException(404, "not found")
    if download:
        return FileResponse(path=doc.storage_path, media_type=doc.content_type, filename=(doc.meta or {}).get("filename", str(doc_id)))
    return {
        "id": doc.id,
        "sha256": doc.sha256,
        "content_type": doc.content_type,
        "size": doc.size_bytes,
        "storage_path": doc.storage_path,
        "source_url": doc.source_url,
        "source_native_id": doc.source_native_id,
        "source_id": doc.source_id,
        "source_run_id": doc.source_run_id,
        "meta": doc.meta,
    }

@router.post('/refs')
def create_ref(
    raw_document_id: int = Form(...),
    workspace_id: Optional[int] = Form(None),
    project_id: Optional[int] = Form(None),
    case_id: Optional[int] = Form(None),
    field_path: Optional[str] = Form(None),
    page_start: Optional[int] = Form(None),
    page_end: Optional[int] = Form(None),
    char_start: Optional[int] = Form(None),
    char_end: Optional[int] = Form(None),
    excerpt: Optional[str] = Form(None),
    created_by_user_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
):
    ref = EvidenceRef(
        raw_document_id=raw_document_id,
        workspace_id=workspace_id,
        project_id=project_id,
        case_id=case_id,
        field_path=field_path,
        page_start=page_start,
        page_end=page_end,
        char_start=char_start,
        char_end=char_end,
        excerpt=excerpt,
        created_by_user_id=created_by_user_id,
    )
    db.add(ref); db.commit(); db.refresh(ref)
    return {"id": ref.id}

@router.post('/raw/{doc_id}/legal_hold')
def set_legal_hold(doc_id: int, hold: bool = True, db: Session = Depends(get_db)):
    doc = db.query(RawDocument).filter_by(id=doc_id).first()
    if not doc:
        raise HTTPException(404, "not found")
    doc.legal_hold = 1 if hold else 0
    db.commit()
    return {"id": doc.id, "legal_hold": bool(doc.legal_hold)}

@router.post('/raw/{doc_id}/retention')
def set_retention(doc_id: int, retention_until: str, db: Session = Depends(get_db)):
    from datetime import datetime
    doc = db.query(RawDocument).filter_by(id=doc_id).first()
    if not doc:
        raise HTTPException(404, "not found")
    doc.retention_until = datetime.fromisoformat(retention_until.replace("Z", "+00:00"))
    db.commit()
    return {"id": doc.id, "retention_until": str(doc.retention_until)}

@router.get('/refs/{ref_id}')
def get_ref(ref_id: int, db: Session = Depends(get_db)):
    ref = db.query(EvidenceRef).filter_by(id=ref_id).first()
    if not ref:
        raise HTTPException(404, "not found")
    return {
        "id": ref.id,
        "raw_document_id": ref.raw_document_id,
        "workspace_id": ref.workspace_id,
        "project_id": ref.project_id,
        "case_id": ref.case_id,
        "field_path": ref.field_path,
        "page_start": ref.page_start,
        "page_end": ref.page_end,
        "char_start": ref.char_start,
        "char_end": ref.char_end,
        "excerpt": ref.excerpt,
        "created_by_user_id": ref.created_by_user_id,
    }
