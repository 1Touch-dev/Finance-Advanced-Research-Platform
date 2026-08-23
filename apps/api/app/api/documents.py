"""
Document Ingestion API Routes (Band B #17)
--------------------------------------------------------------------------------
Provides endpoints for:
  - File upload
  - Document processing
  - Chunk retrieval and search
  - Document management
"""

import os
from fastapi import APIRouter, Query, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import JSONResponse
from typing import Optional, List

from app.services.document_ingestion_service import (
    get_ingestion_service,
    metadata_to_dict,
    ingestion_result_to_dict,
    ProcessingStatus,
)
from app.core.rate_limit import rate_limiter

router = APIRouter(prefix="/documents")

_SEARCH_LIMIT = int(os.getenv("RAG_SEARCH_RATE_LIMIT", "30"))


# -- Static routes first (before parameterized routes) ------------------------

@router.post("/upload")
def upload_document(
    file: UploadFile = File(...),
    ticker: Optional[str] = Form(None),
    entity_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # Comma-separated
    description: Optional[str] = Form(None),
    source: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
):
    """
    Upload a document for processing.

    Supported formats: PDF, DOCX, XLSX, TXT, CSV, HTML, MD, JSON

    Returns:
        Document metadata and ID
    """
    service = get_ingestion_service()

    try:
        # Parse tags
        tag_list = [t.strip() for t in tags.split(",")] if tags else []

        # Upload file
        metadata = service.upload_document(
            file=file.file,
            filename=file.filename,
            user_id=user_id,
            entity_id=entity_id,
            ticker=ticker.upper() if ticker else None,
            tags=tag_list,
            description=description,
            source=source,
        )

        return {
            "success": True,
            "document": metadata_to_dict(metadata),
            "message": f"Document uploaded successfully. Use /documents/{metadata.id}/process to extract text.",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/bulk-upload")
def bulk_upload_documents(
    files: List[UploadFile] = File(...),
    ticker: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None),
):
    """
    Upload multiple documents at once.
    """
    service = get_ingestion_service()
    results = []

    tag_list = [t.strip() for t in tags.split(",")] if tags else []

    for file in files:
        try:
            metadata = service.upload_document(
                file=file.file,
                filename=file.filename,
                user_id=user_id,
                ticker=ticker.upper() if ticker else None,
                tags=tag_list,
            )
            results.append({
                "filename": file.filename,
                "success": True,
                "document_id": metadata.id,
            })
        except Exception as e:
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e),
            })

    return {
        "total": len(files),
        "successful": sum(1 for r in results if r["success"]),
        "failed": sum(1 for r in results if not r["success"]),
        "results": results,
    }


@router.get("/search", dependencies=[Depends(rate_limiter("docs_search", limit=_SEARCH_LIMIT, window=60))])
def search_documents(
    query: str = Query(..., description="Search query", max_length=2000),
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    document_ids: Optional[str] = Query(None, description="Comma-separated document IDs"),
    limit: int = Query(10, ge=1, le=100, description="Maximum results (1-100)"),
    mode: str = Query("hybrid", description="Retrieval mode: vector | keyword | hybrid"),
    debug: bool = Query(False, description="Attach per-stage RAG retrieval trace"),
    user_id: Optional[str] = Query(None, description="Tenant scope — only this user's docs"),
):
    """
    Search across document chunks (vector / keyword / hybrid + rerank).
    Falls back to keyword automatically when embeddings are unavailable.
    Rate-limited and tenant-scoped (user_id) to prevent abuse / cross-tenant leakage.
    """
    service = get_ingestion_service()

    doc_id_list = None
    if document_ids:
        doc_id_list = [d.strip() for d in document_ids.split(",")]

    results = service.search_chunks(
        query=query,
        document_ids=doc_id_list,
        ticker=ticker.upper() if ticker else None,
        limit=limit,
        mode=mode,
        debug=debug,
        user_id=user_id,
    )

    # Pull the trace off the last result (set by the service when debug=True).
    trace = None
    if debug and results and "_trace" in results[-1]:
        trace = results[-1].pop("_trace")

    return {
        "query": query,
        "mode": mode,
        "filters": {
            "ticker": ticker,
            "document_ids": doc_id_list,
            "user_id": user_id,
        },
        "results": results,
        "count": len(results),
        **({"trace": trace} if trace else {}),
    }


@router.get("/")
def list_documents(
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    entity_id: Optional[str] = Query(None, description="Filter by entity ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    status: Optional[str] = Query(None, description="Filter by processing status"),
):
    """
    List all uploaded documents with optional filters.
    """
    service = get_ingestion_service()

    # Parse status
    proc_status = None
    if status:
        try:
            proc_status = ProcessingStatus(status.lower())
        except ValueError:
            pass

    documents = service.list_documents(
        user_id=user_id,
        ticker=ticker.upper() if ticker else None,
        entity_id=entity_id,
        status=proc_status,
    )

    return {
        "documents": [metadata_to_dict(d) for d in documents],
        "total": len(documents),
    }


# -- Parameterized routes (after static routes) -------------------------------

@router.post("/{document_id}/process")
def process_document(document_id: str):
    """
    Process an uploaded document: extract text and create chunks.

    Returns:
        Processing result with chunk count
    """
    service = get_ingestion_service()

    try:
        result = service.process_document(document_id)
        return {
            "success": result.status == ProcessingStatus.COMPLETED,
            "result": ingestion_result_to_dict(result),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@router.get("/{document_id}")
def get_document(document_id: str):
    """
    Get document metadata by ID.
    """
    service = get_ingestion_service()

    metadata = service.get_document(document_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "document": metadata_to_dict(metadata),
    }


@router.get("/{document_id}/chunks")
def get_document_chunks(
    document_id: str,
    page: Optional[int] = Query(None, description="Filter by page number"),
    limit: int = Query(50, description="Maximum chunks to return"),
    offset: int = Query(0, description="Offset for pagination"),
):
    """
    Get chunks from a processed document.
    """
    service = get_ingestion_service()

    metadata = service.get_document(document_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Document not found")

    if metadata.processing_status != ProcessingStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"Document not processed. Status: {metadata.processing_status.value}"
        )

    chunks = service.get_chunks(document_id)

    # Filter by page
    if page is not None:
        chunks = [c for c in chunks if c.page_number == page]

    # Pagination
    total = len(chunks)
    chunks = chunks[offset:offset + limit]

    return {
        "document_id": document_id,
        "total_chunks": total,
        "offset": offset,
        "limit": limit,
        "chunks": [
            {
                "id": c.id,
                "chunk_index": c.chunk_index,
                "text": c.text,
                "page_number": c.page_number,
                "section": c.section,
            }
            for c in chunks
        ],
    }


@router.delete("/{document_id}")
def delete_document(document_id: str):
    """
    Delete a document and its chunks.
    """
    service = get_ingestion_service()

    success = service.delete_document(document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "success": True,
        "message": f"Document {document_id} deleted",
    }
