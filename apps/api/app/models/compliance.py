from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, ForeignKey, Text
from sqlalchemy.sql import func
from .base import Base

class Policy(Base):
    __tablename__ = 'policies'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    rules = Column(JSON, nullable=True)  # field-level restrictions, restricted sources, export controls
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ExportApproval(Base):
    __tablename__ = 'export_approvals'
    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, nullable=True)
    requested_by = Column(String, nullable=True)
    status = Column(String, nullable=False, default='pending')  # pending|approved|rejected
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
