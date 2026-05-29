from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, ForeignKey, Text
from sqlalchemy.sql import func
from .base import Base

class Comment(Base):
    __tablename__ = 'comments'
    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey('reports.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('report_sections.id'), nullable=True)
    text = Column(Text, nullable=False)
    author = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Suggestion(Base):
    __tablename__ = 'suggestions'
    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey('reports.id'), nullable=False)
    section_id = Column(Integer, ForeignKey('report_sections.id'), nullable=False)
    proposed = Column(Text, nullable=False)
    state = Column(String, nullable=False, default='open')  # open|accepted|rejected
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SectionVersion(Base):
    __tablename__ = 'section_versions'
    id = Column(Integer, primary_key=True)
    section_id = Column(Integer, ForeignKey('report_sections.id'), nullable=False)
    content = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ReviewerAssignment(Base):
    __tablename__ = 'review_assignments'
    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey('reports.id'), nullable=False)
    reviewer = Column(String, nullable=False)
    role = Column(String, nullable=True)  # reviewer|approver
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ReviewTask(Base):
    __tablename__ = 'review_tasks'
    id = Column(Integer, primary_key=True)
    report_id = Column(Integer, ForeignKey('reports.id'), nullable=False)
    kind = Column(String, nullable=False)  # verify_claims|enhance_section|export|redline
    payload = Column(JSON, nullable=True)
    status = Column(String, nullable=False, default='open')  # open|done
    created_at = Column(DateTime(timezone=True), server_default=func.now())
