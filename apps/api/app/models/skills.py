from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, ForeignKey, Text
from sqlalchemy.sql import func
from .base import Base

class SkillRegistry(Base):
    __tablename__ = 'skill_registry'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)  # dcf|comps|earnings|one_pager|ic_memo|due_diligence|model_review|market_research
    version = Column(String, nullable=False, default='v1')
    provider = Column(String, nullable=False)  # anthropic|internal
    allowlisted = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SkillRun(Base):
    __tablename__ = 'skill_runs'
    id = Column(Integer, primary_key=True)
    skill_id = Column(Integer, ForeignKey('skill_registry.id'), nullable=False)
    input = Column(JSON, nullable=True)
    output = Column(JSON, nullable=True)
    adapter = Column(String, nullable=False)
    status = Column(String, nullable=False, default='queued')  # queued|running|succeeded|failed|requires_review
    review_required = Column(Boolean, default=False)
    audit_log = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)
    cost_usd = Column(Integer, default=0)
    token_count = Column(Integer, default=0)

class SkillArtifact(Base):
    __tablename__ = 'skill_artifacts'
    id = Column(Integer, primary_key=True)
    run_id = Column(Integer, ForeignKey('skill_runs.id'), nullable=False)
    kind = Column(String, nullable=False)  # csv|xlsx|pdf|json|txt
    path = Column(String, nullable=False)
    meta = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
