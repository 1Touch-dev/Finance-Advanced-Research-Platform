from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, ForeignKey, Text
from sqlalchemy.sql import func
from .base import Base

class Report(Base):
    __tablename__ = 'reports'
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    kind = Column(String, nullable=False)  # stock_analysis|investor_memo|initiating_coverage|company_intel|related_party|gov_exposure|lobbying_influence|procurement_risk|portfolio_risk
    status = Column(String, nullable=False, default='draft')  # draft|in_review|approved|published
    meta = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ReportSection(Base):
    __tablename__ = 'report_sections'
    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey('reports.id'), nullable=False)
    name = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    order = Column(Integer, nullable=False, default=0)

class EvidenceBundle(Base):
    __tablename__ = 'evidence_bundles'
    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey('reports.id'), nullable=False)
    name = Column(String, nullable=False)
    items = Column(JSON, nullable=True)  # list of evidence_ref ids
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Claim(Base):
    __tablename__ = 'claims'
    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey('reports.id'), nullable=False)
    text = Column(Text, nullable=False)
    status = Column(String, nullable=False, default='pending')  # pending|verified|contradicted|needs_review
    contradiction_note = Column(Text, nullable=True)

class ClaimEvidence(Base):
    __tablename__ = 'claim_evidence'
    id = Column(Integer, primary_key=True)
    claim_id = Column(Integer, ForeignKey('claims.id'), nullable=False)
    evidence_ref_id = Column(Integer, nullable=False)
    weight = Column(Integer, nullable=True)
