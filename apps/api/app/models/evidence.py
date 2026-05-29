from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, JSON
from sqlalchemy.sql import func
from .base import Base

class RawDocument(Base):
    __tablename__ = 'raw_documents'
    id = Column(Integer, primary_key=True)
    sha256 = Column(String, nullable=False, index=True)
    content_type = Column(String, nullable=True)
    size_bytes = Column(Integer, nullable=True)
    storage_path = Column(String, nullable=False)  # immutable path
    source_url = Column(String, nullable=True)
    source_native_id = Column(String, nullable=True)
    source_id = Column(Integer, nullable=True)
    source_run_id = Column(Integer, nullable=True)
    uploader_user_id = Column(Integer, nullable=True)
    meta = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class EvidenceRef(Base):
    __tablename__ = 'evidence_refs'
    id = Column(Integer, primary_key=True)
    raw_document_id = Column(Integer, ForeignKey('raw_documents.id'), nullable=False)
    workspace_id = Column(Integer, nullable=True)
    project_id = Column(Integer, nullable=True)
    case_id = Column(Integer, nullable=True)
    field_path = Column(String, nullable=True)
    page_start = Column(Integer, nullable=True)
    page_end = Column(Integer, nullable=True)
    char_start = Column(Integer, nullable=True)
    char_end = Column(Integer, nullable=True)
    excerpt = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
