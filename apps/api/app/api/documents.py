"""
Document Ingestion API Routes (Band B #17)
────────────────────────────────────────────────────────────────────────────
Provides endpoints for:
  - File upload
  - Document processing
  - Chunk retrieval and search
  - Document management
"""

import os
from fastapi import APIRouter, Query, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import Optional, List

from app.services.document_ingestion_service import (
    get_ingestion_service,
    metadata_to_dict,
    ingestion_result_to_dict,
    ProcessingStatus,
)

router = APIRouter(prefix="/documents")


@router.post("/upload")
async def upload_document(
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


@router.post("/{document_id}/process")
async def process_document(document_id: str):
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
async def get_document(document_id: str):
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
async def get_document_chunks(
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


@router.get("/search")
async def search_documents(
    query: str = Query(..., description="Search query"),
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    document_ids: Optional[str] = Query(None, description="Comma-separated document IDs"),
    limit: int = Query(10, description="Maximum results"),
):
    """
    Search across document chunks.
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
    )

    return {
        "query": query,
        "filters": {
            "ticker": ticker,
            "document_ids": doc_id_list,
        },
        "results": results,
        "count": len(results),
    }


@router.get("/")
async def list_documents(
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


@router.delete("/{document_id}")
async def delete_document(document_id: str):
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


@router.post("/bulk-upload")
async def bulk_upload_documents(
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
