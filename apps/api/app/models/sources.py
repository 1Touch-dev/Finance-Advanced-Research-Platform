from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, JSON, UniqueConstraint
from sqlalchemy.sql import func
from .base import Base

class Source(Base):
    __tablename__ = 'sources'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    kind = Column(String, nullable=False)
    workspace_id = Column(Integer, nullable=True)
    config = Column(JSON, nullable=True)
    __table_args__ = (UniqueConstraint('name','workspace_id', name='uq_source_ws_name'),)

class SourceCredential(Base):
    __tablename__ = 'source_credentials'
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey('sources.id'), nullable=False)
    kind = Column(String, nullable=False)
    secret = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SourceContract(Base):
    __tablename__ = 'source_contracts'
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey('sources.id'), nullable=False)
    version = Column(String, nullable=False)
    spec = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SourceRun(Base):
    __tablename__ = 'source_runs'
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey('sources.id'), nullable=False)
    status = Column(String, nullable=False, default='pending')
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    error = Column(Text, nullable=True)
    metrics = Column(JSON, nullable=True)
    checkpoint = Column(JSON, nullable=True)

class SourceRecordMeta(Base):
    __tablename__ = 'source_record_meta'
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey('sources.id'), nullable=False)
    run_id = Column(Integer, ForeignKey('source_runs.id'), nullable=True)
    external_id = Column(String, nullable=False)
    hash = Column(String, nullable=True)
    normalized = Column(JSON, nullable=True)
    evidence_ref_id = Column(Integer, nullable=True)
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_ingested_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint('source_id','external_id', name='uq_src_external'),)

class SourceDeadLetter(Base):
    __tablename__ = 'source_dead_letters'
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey('source_runs.id'), nullable=False)
    external_id = Column(String, nullable=True)
    error = Column(Text, nullable=False)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SourceCheckpoint(Base):
    __tablename__ = 'source_checkpoints'
    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey('sources.id'), nullable=False)
    cursor_key = Column(String, nullable=False, default='default')
    state = Column(JSON, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (UniqueConstraint('source_id','cursor_key', name='uq_src_checkpoint'),)
