"""
Private Document Ingestion Service (Band B #17)
────────────────────────────────────────────────────────────────────────────
Provides document ingestion capabilities:
  - File upload and storage
  - Text extraction from PDF, DOCX, XLSX, TXT
  - Chunking and embedding generation
  - Vector storage for RAG queries
  - Document metadata management

Enables users to upload private documents for analysis.
"""

import os
import re
import json
import logging
import hashlib
import tempfile
from typing import Dict, Any, List, Optional, BinaryIO, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import uuid

logger = logging.getLogger(__name__)

# Configuration
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/document_uploads")
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_MB", "50")) * 1024 * 1024  # 50MB default
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))  # Characters per chunk
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))  # Overlap between chunks


class DocumentType(Enum):
    """Supported document types."""
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    TXT = "txt"
    CSV = "csv"
    HTML = "html"
    MD = "md"
    JSON = "json"


class ProcessingStatus(Enum):
    """Document processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class DocumentMetadata:
    """Metadata for an uploaded document."""
    id: str
    filename: str
    document_type: DocumentType
    file_size: int
    upload_time: str
    user_id: Optional[str] = None
    entity_id: Optional[str] = None  # Associated entity (company, person)
    ticker: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    description: Optional[str] = None
    source: Optional[str] = None  # e.g., "internal", "analyst_report", "contract"
    date_range: Optional[Dict[str, str]] = None  # For time-sensitive documents
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    chunk_count: int = 0
    page_count: int = 0
    word_count: int = 0
    hash: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class DocumentChunk:
    """A chunk of text from a document for embedding."""
    id: str
    document_id: str
    chunk_index: int
    text: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class IngestionResult:
    """Result of document ingestion."""
    document_id: str
    status: ProcessingStatus
    chunks_created: int
    pages_processed: int
    word_count: int
    processing_time_ms: int
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None


class DocumentIngestionService:
    """Service for ingesting and processing private documents."""

    def __init__(self, upload_dir: str = UPLOAD_DIR):
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.documents: Dict[str, DocumentMetadata] = {}
        self.chunks: Dict[str, List[DocumentChunk]] = {}

    def upload_document(
        self,
        file: BinaryIO,
        filename: str,
        user_id: Optional[str] = None,
        entity_id: Optional[str] = None,
        ticker: Optional[str] = None,
        tags: Optional[List[str]] = None,
        description: Optional[str] = None,
        source: Optional[str] = None,
    ) -> DocumentMetadata:
        """
        Upload and register a document.

        Args:
            file: File-like object
            filename: Original filename
            user_id: Uploading user
            entity_id: Associated entity
            ticker: Associated stock ticker
            tags: Document tags
            description: Document description
            source: Document source type

        Returns:
            DocumentMetadata for the uploaded file
        """
        # Validate file type
        doc_type = self._get_document_type(filename)
        if not doc_type:
            raise ValueError(f"Unsupported file type: {filename}")

        # Read file content
        content = file.read()

        # Check file size
        if len(content) > MAX_FILE_SIZE:
            raise ValueError(f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB")

        # Generate document ID and hash
        doc_id = str(uuid.uuid4())
        file_hash = hashlib.sha256(content).hexdigest()

        # Check for duplicates
        for existing in self.documents.values():
            if existing.hash == file_hash:
                logger.warning(f"Duplicate document detected: {existing.id}")
                return existing

        # Save file
        safe_filename = self._sanitize_filename(filename)
        file_path = self.upload_dir / doc_id / safe_filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)

        # Create metadata
        metadata = DocumentMetadata(
            id=doc_id,
            filename=safe_filename,
            document_type=doc_type,
            file_size=len(content),
            upload_time=datetime.utcnow().isoformat(),
            user_id=user_id,
            entity_id=entity_id,
            ticker=ticker,
            tags=tags or [],
            description=description,
            source=source,
            hash=file_hash,
        )

        self.documents[doc_id] = metadata
        return metadata

    def process_document(self, document_id: str) -> IngestionResult:
        """
        Process an uploaded document: extract text, chunk, and prepare for embedding.

        Args:
            document_id: ID of the document to process

        Returns:
            IngestionResult with processing details
        """
        import time
        start_time = time.time()

        if document_id not in self.documents:
            raise ValueError(f"Document not found: {document_id}")

        metadata = self.documents[document_id]
        metadata.processing_status = ProcessingStatus.PROCESSING

        try:
            # Get file path
            file_path = self.upload_dir / document_id / metadata.filename

            # Extract text based on document type
            text, pages = self._extract_text(file_path, metadata.document_type)

            # Count words
            word_count = len(text.split())

            # Create chunks
            chunks = self._create_chunks(document_id, text, pages)

            # Store chunks
            self.chunks[document_id] = chunks

            # Update metadata
            metadata.processing_status = ProcessingStatus.COMPLETED
            metadata.chunk_count = len(chunks)
            metadata.page_count = len(pages) if pages else 1
            metadata.word_count = word_count

            processing_time = int((time.time() - start_time) * 1000)

            return IngestionResult(
                document_id=document_id,
                status=ProcessingStatus.COMPLETED,
                chunks_created=len(chunks),
                pages_processed=metadata.page_count,
                word_count=word_count,
                processing_time_ms=processing_time,
            )

        except Exception as e:
            logger.error(f"Error processing document {document_id}: {e}")
            metadata.processing_status = ProcessingStatus.FAILED
            metadata.error_message = str(e)

            return IngestionResult(
                document_id=document_id,
                status=ProcessingStatus.FAILED,
                chunks_created=0,
                pages_processed=0,
                word_count=0,
                processing_time_ms=int((time.time() - start_time) * 1000),
                error=str(e),
            )

    def _extract_text(
        self,
        file_path: Path,
        doc_type: DocumentType,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """Extract text from a document."""
        pages = []

        if doc_type == DocumentType.PDF:
            text, pages = self._extract_pdf(file_path)
        elif doc_type == DocumentType.DOCX:
            text = self._extract_docx(file_path)
        elif doc_type == DocumentType.XLSX:
            text = self._extract_xlsx(file_path)
        elif doc_type == DocumentType.TXT:
            text = file_path.read_text(encoding='utf-8', errors='ignore')
        elif doc_type == DocumentType.MD:
            text = file_path.read_text(encoding='utf-8', errors='ignore')
        elif doc_type == DocumentType.CSV:
            text = self._extract_csv(file_path)
        elif doc_type == DocumentType.HTML:
            text = self._extract_html(file_path)
        elif doc_type == DocumentType.JSON:
            text = self._extract_json(file_path)
        else:
            raise ValueError(f"Unsupported document type: {doc_type}")

        return text, pages

    def _extract_pdf(self, file_path: Path) -> Tuple[str, List[Dict[str, Any]]]:
        """Extract text from PDF."""
        try:
            import pypdf
            reader = pypdf.PdfReader(str(file_path))
            pages = []
            all_text = []

            for i, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                all_text.append(page_text)
                pages.append({
                    "page_number": i + 1,
                    "text": page_text,
                    "char_count": len(page_text),
                })

            return "\n\n".join(all_text), pages
        except ImportError:
            logger.warning("pypdf not installed, attempting fallback")
            # Fallback: just read as binary and return placeholder
            return "[PDF content - pypdf not installed]", []

    def _extract_docx(self, file_path: Path) -> str:
        """Extract text from DOCX."""
        try:
            from docx import Document
            doc = Document(str(file_path))
            paragraphs = [p.text for p in doc.paragraphs]
            return "\n\n".join(paragraphs)
        except ImportError:
            logger.warning("python-docx not installed")
            return "[DOCX content - python-docx not installed]"

    def _extract_xlsx(self, file_path: Path) -> str:
        """Extract text from XLSX."""
        try:
            import openpyxl
            wb = openpyxl.load_workbook(str(file_path), data_only=True)
            all_text = []

            for sheet_name in wb.sheetnames:
                sheet = wb[sheet_name]
                all_text.append(f"## Sheet: {sheet_name}\n")

                for row in sheet.iter_rows(values_only=True):
                    row_text = " | ".join(str(cell) if cell is not None else "" for cell in row)
                    if row_text.strip(" |"):
                        all_text.append(row_text)

            return "\n".join(all_text)
        except ImportError:
            logger.warning("openpyxl not installed")
            return "[XLSX content - openpyxl not installed]"

    def _extract_csv(self, file_path: Path) -> str:
        """Extract text from CSV."""
        import csv
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        reader = csv.reader(content.splitlines())
        rows = [" | ".join(row) for row in reader]
        return "\n".join(rows)

    def _extract_html(self, file_path: Path) -> str:
        """Extract text from HTML."""
        try:
            from bs4 import BeautifulSoup
            html_content = file_path.read_text(encoding='utf-8', errors='ignore')
            soup = BeautifulSoup(html_content, 'html.parser')
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            return soup.get_text(separator="\n", strip=True)
        except ImportError:
            # Fallback: basic regex stripping
            html_content = file_path.read_text(encoding='utf-8', errors='ignore')
            text = re.sub(r'<[^>]+>', '', html_content)
            return text

    def _extract_json(self, file_path: Path) -> str:
        """Extract text from JSON."""
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        data = json.loads(content)
        return json.dumps(data, indent=2)

    def _create_chunks(
        self,
        document_id: str,
        text: str,
        pages: List[Dict[str, Any]],
    ) -> List[DocumentChunk]:
        """Create overlapping chunks from text."""
        chunks = []

        # If we have page data, chunk by page
        if pages:
            for page_info in pages:
                page_text = page_info.get("text", "")
                page_num = page_info.get("page_number", 1)

                page_chunks = self._chunk_text(page_text)
                for i, chunk_text in enumerate(page_chunks):
                    chunks.append(DocumentChunk(
                        id=f"{document_id}_p{page_num}_c{i}",
                        document_id=document_id,
                        chunk_index=len(chunks),
                        text=chunk_text,
                        page_number=page_num,
                    ))
        else:
            # No page data, chunk the whole text
            text_chunks = self._chunk_text(text)
            for i, chunk_text in enumerate(text_chunks):
                chunks.append(DocumentChunk(
                    id=f"{document_id}_c{i}",
                    document_id=document_id,
                    chunk_index=i,
                    text=chunk_text,
                ))

        return chunks

    def _chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        chunks = []

        # Clean text
        text = text.strip()
        if not text:
            return chunks

        # Split by paragraphs first, then by size
        paragraphs = re.split(r'\n\s*\n', text)

        current_chunk = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) + 2 <= CHUNK_SIZE:
                current_chunk += ("\n\n" if current_chunk else "") + para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                    # Start new chunk with overlap
                    if len(current_chunk) > CHUNK_OVERLAP:
                        overlap_start = current_chunk[-CHUNK_OVERLAP:]
                        current_chunk = overlap_start + "\n\n" + para
                    else:
                        current_chunk = para
                else:
                    # Single paragraph too long, split by sentences
                    if len(para) > CHUNK_SIZE:
                        sentences = re.split(r'(?<=[.!?])\s+', para)
                        for sent in sentences:
                            if len(current_chunk) + len(sent) + 1 <= CHUNK_SIZE:
                                current_chunk += (" " if current_chunk else "") + sent
                            else:
                                if current_chunk:
                                    chunks.append(current_chunk)
                                current_chunk = sent
                    else:
                        current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _get_document_type(self, filename: str) -> Optional[DocumentType]:
        """Determine document type from filename."""
        ext = filename.lower().split('.')[-1]
        type_map = {
            'pdf': DocumentType.PDF,
            'docx': DocumentType.DOCX,
            'doc': DocumentType.DOCX,
            'xlsx': DocumentType.XLSX,
            'xls': DocumentType.XLSX,
            'txt': DocumentType.TXT,
            'csv': DocumentType.CSV,
            'html': DocumentType.HTML,
            'htm': DocumentType.HTML,
            'md': DocumentType.MD,
            'markdown': DocumentType.MD,
            'json': DocumentType.JSON,
        }
        return type_map.get(ext)

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename for safe storage."""
        # Remove path components
        filename = os.path.basename(filename)
        # Replace unsafe characters
        filename = re.sub(r'[^\w\s\-\.]', '_', filename)
        # Limit length
        if len(filename) > 200:
            name, ext = os.path.splitext(filename)
            filename = name[:195] + ext
        return filename

    def get_document(self, document_id: str) -> Optional[DocumentMetadata]:
        """Get document metadata by ID."""
        return self.documents.get(document_id)

    def get_chunks(self, document_id: str) -> List[DocumentChunk]:
        """Get all chunks for a document."""
        return self.chunks.get(document_id, [])

    def search_chunks(
        self,
        query: str,
        document_ids: Optional[List[str]] = None,
        ticker: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant chunks (basic keyword search).
        For production, this should use vector similarity search.
        """
        results = []
        query_lower = query.lower()
        query_terms = query_lower.split()

        # Filter documents
        search_docs = []
        for doc_id, metadata in self.documents.items():
            if document_ids and doc_id not in document_ids:
                continue
            if ticker and metadata.ticker != ticker.upper():
                continue
            search_docs.append(doc_id)

        # Search chunks
        for doc_id in search_docs:
            chunks = self.chunks.get(doc_id, [])
            for chunk in chunks:
                chunk_lower = chunk.text.lower()
                # Simple scoring: count term matches
                score = sum(1 for term in query_terms if term in chunk_lower)
                if score > 0:
                    results.append({
                        "document_id": doc_id,
                        "chunk_id": chunk.id,
                        "text": chunk.text[:500],
                        "page_number": chunk.page_number,
                        "score": score,
                        "document_filename": self.documents[doc_id].filename,
                    })

        # Sort by score and limit
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def delete_document(self, document_id: str) -> bool:
        """Delete a document and its chunks."""
        if document_id not in self.documents:
            return False

        # Remove file
        metadata = self.documents[document_id]
        file_path = self.upload_dir / document_id / metadata.filename
        if file_path.exists():
            file_path.unlink()
        doc_dir = self.upload_dir / document_id
        if doc_dir.exists():
            doc_dir.rmdir()

        # Remove from memory
        del self.documents[document_id]
        if document_id in self.chunks:
            del self.chunks[document_id]

        return True

    def list_documents(
        self,
        user_id: Optional[str] = None,
        ticker: Optional[str] = None,
        entity_id: Optional[str] = None,
        status: Optional[ProcessingStatus] = None,
    ) -> List[DocumentMetadata]:
        """List documents with optional filters."""
        results = []
        for doc in self.documents.values():
            if user_id and doc.user_id != user_id:
                continue
            if ticker and doc.ticker != ticker.upper():
                continue
            if entity_id and doc.entity_id != entity_id:
                continue
            if status and doc.processing_status != status:
                continue
            results.append(doc)
        return results


# Global service instance
_ingestion_service: Optional[DocumentIngestionService] = None


def get_ingestion_service() -> DocumentIngestionService:
    """Get or create the global ingestion service instance."""
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = DocumentIngestionService()
    return _ingestion_service


# ── Serialization helpers ────────────────────────────────────────────────────

def metadata_to_dict(metadata: DocumentMetadata) -> Dict[str, Any]:
    """Convert DocumentMetadata to JSON-serializable dict."""
    return {
        "id": metadata.id,
        "filename": metadata.filename,
        "document_type": metadata.document_type.value,
        "file_size": metadata.file_size,
        "upload_time": metadata.upload_time,
        "user_id": metadata.user_id,
        "entity_id": metadata.entity_id,
        "ticker": metadata.ticker,
        "tags": metadata.tags,
        "description": metadata.description,
        "source": metadata.source,
        "date_range": metadata.date_range,
        "processing_status": metadata.processing_status.value,
        "chunk_count": metadata.chunk_count,
        "page_count": metadata.page_count,
        "word_count": metadata.word_count,
        "error_message": metadata.error_message,
    }


def ingestion_result_to_dict(result: IngestionResult) -> Dict[str, Any]:
    """Convert IngestionResult to JSON-serializable dict."""
    return {
        "document_id": result.document_id,
        "status": result.status.value,
        "chunks_created": result.chunks_created,
        "pages_processed": result.pages_processed,
        "word_count": result.word_count,
        "processing_time_ms": result.processing_time_ms,
        "warnings": result.warnings,
        "error": result.error,
    }
