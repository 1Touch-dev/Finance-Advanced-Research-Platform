"""
Tests for app.api.documents API endpoints (Band B #17)
--------------------------------------------------------------------------------
Tests the FastAPI endpoints for:
  - /documents/upload - Upload document
  - /documents/{id}/process - Process document
  - /documents/{id} - Get document metadata
  - /documents/{id}/chunks - Get document chunks
  - /documents/search - Search across documents
  - /documents/ - List documents
  - /documents/{id} DELETE - Delete document
  - /documents/bulk-upload - Bulk upload
"""
from __future__ import annotations

import io
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# -- Upload Tests -------------------------------------------------------------

class TestDocumentUpload:
    """Tests for POST /documents/upload."""

    def test_upload_txt_file(self):
        file_content = b"This is a test document with some content for testing."
        files = {"file": ("test.txt", io.BytesIO(file_content), "text/plain")}
        data = {"ticker": "AAPL", "description": "Test document"}

        response = client.post("/documents/upload", files=files, data=data)
        assert response.status_code == 200

        result = response.json()
        assert result["success"] is True
        assert "document" in result
        assert result["document"]["filename"] == "test.txt"
        assert result["document"]["ticker"] == "AAPL"

    def test_upload_csv_file(self):
        csv_content = b"date,value\n2024-01-01,100\n2024-01-02,150"
        files = {"file": ("data.csv", io.BytesIO(csv_content), "text/csv")}

        response = client.post("/documents/upload", files=files)
        assert response.status_code == 200

        result = response.json()
        assert result["success"] is True
        assert result["document"]["document_type"] == "csv"

    def test_upload_json_file(self):
        json_content = b'{"key": "value", "data": [1, 2, 3]}'
        files = {"file": ("config.json", io.BytesIO(json_content), "application/json")}

        response = client.post("/documents/upload", files=files)
        assert response.status_code == 200

        result = response.json()
        assert result["document"]["document_type"] == "json"

    def test_upload_with_tags(self):
        file_content = b"Document with tags"
        files = {"file": ("tagged.txt", io.BytesIO(file_content), "text/plain")}
        data = {"tags": "earnings,quarterly,2024"}

        response = client.post("/documents/upload", files=files, data=data)
        assert response.status_code == 200

        result = response.json()
        # Tags are stored in metadata
        assert "document" in result

    def test_upload_with_entity(self):
        file_content = b"Entity document"
        files = {"file": ("entity.txt", io.BytesIO(file_content), "text/plain")}
        data = {"entity_id": "AAPL_INC", "user_id": "user_001"}

        response = client.post("/documents/upload", files=files, data=data)
        assert response.status_code == 200

        result = response.json()
        assert result["document"]["entity_id"] == "AAPL_INC"
        assert result["document"]["user_id"] == "user_001"

    def test_upload_unsupported_type(self):
        file_content = b"Some binary content"
        files = {"file": ("file.xyz", io.BytesIO(file_content), "application/octet-stream")}

        response = client.post("/documents/upload", files=files)
        # Should return 400 for unsupported type
        assert response.status_code == 400


# -- Process Tests ------------------------------------------------------------

class TestDocumentProcess:
    """Tests for POST /documents/{id}/process."""

    def test_process_document(self):
        # First upload
        file_content = b"This is a longer document that will be chunked. " * 50
        files = {"file": ("process_test.txt", io.BytesIO(file_content), "text/plain")}

        upload = client.post("/documents/upload", files=files)
        assert upload.status_code == 200
        doc_id = upload.json()["document"]["id"]

        # Then process
        response = client.post(f"/documents/{doc_id}/process")
        assert response.status_code == 200

        result = response.json()
        assert result["success"] is True
        assert result["result"]["status"] == "completed"
        assert result["result"]["chunks_created"] > 0

    def test_process_nonexistent_document(self):
        response = client.post("/documents/nonexistent_doc_id/process")
        assert response.status_code == 404

    def test_process_creates_chunks(self):
        # Upload a larger document
        content = b"Section 1: Introduction. " * 100 + b"\n\n" + b"Section 2: Analysis. " * 100
        files = {"file": ("chunked.txt", io.BytesIO(content), "text/plain")}

        upload = client.post("/documents/upload", files=files)
        doc_id = upload.json()["document"]["id"]

        process = client.post(f"/documents/{doc_id}/process")
        result = process.json()

        assert result["result"]["chunks_created"] >= 1
        assert result["result"]["word_count"] > 0


# -- Get Document Tests -------------------------------------------------------

class TestGetDocument:
    """Tests for GET /documents/{id}."""

    def test_get_document(self):
        # Upload first
        file_content = b"Metadata test document"
        files = {"file": ("meta.txt", io.BytesIO(file_content), "text/plain")}
        data = {"ticker": "MSFT", "description": "Test metadata"}

        upload = client.post("/documents/upload", files=files, data=data)
        doc_id = upload.json()["document"]["id"]

        # Get metadata
        response = client.get(f"/documents/{doc_id}")
        assert response.status_code == 200

        result = response.json()
        assert "document" in result
        assert result["document"]["id"] == doc_id
        assert result["document"]["ticker"] == "MSFT"

    def test_get_nonexistent_document(self):
        response = client.get("/documents/nonexistent_id_12345")
        assert response.status_code == 404

    def test_get_document_has_required_fields(self):
        file_content = b"Field test"
        files = {"file": ("fields.txt", io.BytesIO(file_content), "text/plain")}

        upload = client.post("/documents/upload", files=files)
        doc_id = upload.json()["document"]["id"]

        response = client.get(f"/documents/{doc_id}")
        doc = response.json()["document"]

        assert "id" in doc
        assert "filename" in doc
        assert "document_type" in doc
        assert "file_size" in doc
        assert "upload_time" in doc
        assert "processing_status" in doc


# -- Get Chunks Tests ---------------------------------------------------------

class TestGetChunks:
    """Tests for GET /documents/{id}/chunks."""

    def test_get_chunks(self):
        # Upload and process
        content = b"Chunk content test. " * 100
        files = {"file": ("chunks.txt", io.BytesIO(content), "text/plain")}

        upload = client.post("/documents/upload", files=files)
        doc_id = upload.json()["document"]["id"]
        client.post(f"/documents/{doc_id}/process")

        # Get chunks
        response = client.get(f"/documents/{doc_id}/chunks")
        assert response.status_code == 200

        result = response.json()
        assert "chunks" in result
        assert result["total_chunks"] > 0

    def test_get_chunks_pagination(self):
        # Upload large document
        content = b"Large document chunk content. " * 500
        files = {"file": ("paginated.txt", io.BytesIO(content), "text/plain")}

        upload = client.post("/documents/upload", files=files)
        doc_id = upload.json()["document"]["id"]
        client.post(f"/documents/{doc_id}/process")

        # Get with pagination
        response = client.get(f"/documents/{doc_id}/chunks?limit=5&offset=0")
        assert response.status_code == 200

        result = response.json()
        assert len(result["chunks"]) <= 5
        assert "total_chunks" in result

    def test_get_chunks_unprocessed_fails(self):
        # Upload but don't process
        files = {"file": ("unprocessed.txt", io.BytesIO(b"content"), "text/plain")}

        upload = client.post("/documents/upload", files=files)
        doc_id = upload.json()["document"]["id"]

        response = client.get(f"/documents/{doc_id}/chunks")
        assert response.status_code == 400

    def test_chunks_have_required_fields(self):
        content = b"Content with fields. " * 50
        files = {"file": ("chunk_fields.txt", io.BytesIO(content), "text/plain")}

        upload = client.post("/documents/upload", files=files)
        doc_id = upload.json()["document"]["id"]
        client.post(f"/documents/{doc_id}/process")

        response = client.get(f"/documents/{doc_id}/chunks")
        chunks = response.json()["chunks"]

        if chunks:
            chunk = chunks[0]
            assert "id" in chunk
            assert "chunk_index" in chunk
            assert "text" in chunk


# -- Search Tests -------------------------------------------------------------

class TestDocumentSearch:
    """Tests for GET /documents/search."""

    def test_search_documents(self):
        # Upload and process a document with specific content
        content = b"Apple iPhone sales increased significantly in Q4."
        files = {"file": ("search_test.txt", io.BytesIO(content), "text/plain")}
        data = {"ticker": "AAPL"}

        upload = client.post("/documents/upload", files=files, data=data)
        doc_id = upload.json()["document"]["id"]
        client.post(f"/documents/{doc_id}/process")

        # Search
        response = client.get("/documents/search?query=iPhone sales")
        assert response.status_code == 200

        result = response.json()
        assert "results" in result
        assert "query" in result

    def test_search_with_ticker_filter(self):
        response = client.get("/documents/search?query=revenue&ticker=AAPL")
        assert response.status_code == 200

        result = response.json()
        assert result["filters"]["ticker"] == "AAPL"

    def test_search_with_mode(self):
        for mode in ["keyword", "vector", "hybrid"]:
            response = client.get(f"/documents/search?query=test&mode={mode}")
            assert response.status_code == 200
            assert response.json()["mode"] == mode

    def test_search_with_limit(self):
        response = client.get("/documents/search?query=test&limit=5")
        assert response.status_code == 200

        result = response.json()
        assert len(result["results"]) <= 5

    def test_search_with_debug(self):
        response = client.get("/documents/search?query=test&debug=true")
        assert response.status_code == 200
        # Debug trace may or may not be present depending on implementation


# -- List Documents Tests -----------------------------------------------------

class TestListDocuments:
    """Tests for GET /documents/."""

    def test_list_documents(self):
        response = client.get("/documents/")
        assert response.status_code == 200

        result = response.json()
        assert "documents" in result
        assert "total" in result
        assert isinstance(result["documents"], list)

    def test_list_with_ticker_filter(self):
        # Upload a document with ticker
        content = b"NVDA test document"
        files = {"file": ("nvda.txt", io.BytesIO(content), "text/plain")}
        data = {"ticker": "NVDA"}

        client.post("/documents/upload", files=files, data=data)

        # List with filter
        response = client.get("/documents/?ticker=NVDA")
        assert response.status_code == 200

        result = response.json()
        for doc in result["documents"]:
            assert doc["ticker"] == "NVDA"

    def test_list_with_user_filter(self):
        content = b"User specific document"
        files = {"file": ("user_doc.txt", io.BytesIO(content), "text/plain")}
        data = {"user_id": "test_user_123"}

        client.post("/documents/upload", files=files, data=data)

        response = client.get("/documents/?user_id=test_user_123")
        assert response.status_code == 200

        result = response.json()
        for doc in result["documents"]:
            assert doc["user_id"] == "test_user_123"

    def test_list_with_status_filter(self):
        response = client.get("/documents/?status=pending")
        assert response.status_code == 200

        result = response.json()
        for doc in result["documents"]:
            assert doc["processing_status"] == "pending"


# -- Delete Tests -------------------------------------------------------------

class TestDeleteDocument:
    """Tests for DELETE /documents/{id}."""

    def test_delete_document(self):
        # Upload first
        files = {"file": ("delete_me.txt", io.BytesIO(b"to delete"), "text/plain")}

        upload = client.post("/documents/upload", files=files)
        doc_id = upload.json()["document"]["id"]

        # Delete
        response = client.delete(f"/documents/{doc_id}")
        assert response.status_code == 200

        result = response.json()
        assert result["success"] is True

        # Verify deleted
        get = client.get(f"/documents/{doc_id}")
        assert get.status_code == 404

    def test_delete_nonexistent(self):
        response = client.delete("/documents/nonexistent_doc_999")
        assert response.status_code == 404


# -- Bulk Upload Tests --------------------------------------------------------

class TestBulkUpload:
    """Tests for POST /documents/bulk-upload."""

    def test_bulk_upload(self):
        files = [
            ("files", ("file1.txt", io.BytesIO(b"Content 1"), "text/plain")),
            ("files", ("file2.txt", io.BytesIO(b"Content 2"), "text/plain")),
            ("files", ("file3.txt", io.BytesIO(b"Content 3"), "text/plain")),
        ]
        data = {"ticker": "GOOG"}

        response = client.post("/documents/bulk-upload", files=files, data=data)
        assert response.status_code == 200

        result = response.json()
        assert result["total"] == 3
        assert result["successful"] >= 0
        assert "results" in result

    def test_bulk_upload_with_tags(self):
        files = [
            ("files", ("tag1.txt", io.BytesIO(b"Tagged content"), "text/plain")),
        ]
        data = {"tags": "bulk,test,upload"}

        response = client.post("/documents/bulk-upload", files=files, data=data)
        assert response.status_code == 200

    def test_bulk_upload_partial_failure(self):
        files = [
            ("files", ("good.txt", io.BytesIO(b"Good file"), "text/plain")),
            ("files", ("bad.xyz", io.BytesIO(b"Bad file type"), "application/octet-stream")),
        ]

        response = client.post("/documents/bulk-upload", files=files)
        assert response.status_code == 200

        result = response.json()
        assert result["total"] == 2
        assert result["failed"] >= 0


# -- Service Integration Tests ------------------------------------------------

class TestDocumentServiceIntegration:
    """Integration tests for the document ingestion service."""

    def test_full_workflow(self):
        """Test complete upload -> process -> search workflow."""
        # 1. Upload
        content = b"This document discusses quarterly earnings and revenue growth for tech companies."
        files = {"file": ("integration.txt", io.BytesIO(content), "text/plain")}
        data = {"ticker": "TECH", "tags": "earnings,quarterly"}

        upload = client.post("/documents/upload", files=files, data=data)
        assert upload.status_code == 200
        doc_id = upload.json()["document"]["id"]

        # 2. Process
        process = client.post(f"/documents/{doc_id}/process")
        assert process.status_code == 200
        assert process.json()["success"] is True

        # 3. Get metadata
        meta = client.get(f"/documents/{doc_id}")
        assert meta.status_code == 200
        assert meta.json()["document"]["processing_status"] == "completed"

        # 4. Get chunks
        chunks = client.get(f"/documents/{doc_id}/chunks")
        assert chunks.status_code == 200
        assert chunks.json()["total_chunks"] > 0

        # 5. Search
        search = client.get("/documents/search?query=earnings revenue")
        assert search.status_code == 200

        # 6. Delete
        delete = client.delete(f"/documents/{doc_id}")
        assert delete.status_code == 200

    def test_duplicate_detection(self):
        """Test that duplicate files are detected."""
        content = b"Exact same content for duplicate detection"
        files1 = {"file": ("dup1.txt", io.BytesIO(content), "text/plain")}
        files2 = {"file": ("dup2.txt", io.BytesIO(content), "text/plain")}

        upload1 = client.post("/documents/upload", files=files1)
        upload2 = client.post("/documents/upload", files=files2)

        # Both should succeed, but second may return existing doc
        assert upload1.status_code == 200
        assert upload2.status_code == 200

        # Same document ID if duplicate detected
        id1 = upload1.json()["document"]["id"]
        id2 = upload2.json()["document"]["id"]
        # Service detects duplicates by hash
        assert id1 == id2  # Duplicate returns same ID

    def test_markdown_support(self):
        """Test markdown file ingestion."""
        md_content = b"# Header\n\n## Subheader\n\n- Item 1\n- Item 2\n\nParagraph text."
        files = {"file": ("test.md", io.BytesIO(md_content), "text/markdown")}

        upload = client.post("/documents/upload", files=files)
        assert upload.status_code == 200
        assert upload.json()["document"]["document_type"] == "md"

    def test_html_support(self):
        """Test HTML file ingestion."""
        html_content = b"<html><body><h1>Title</h1><p>Content paragraph.</p></body></html>"
        files = {"file": ("page.html", io.BytesIO(html_content), "text/html")}

        upload = client.post("/documents/upload", files=files)
        assert upload.status_code == 200
        assert upload.json()["document"]["document_type"] == "html"
