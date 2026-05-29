from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, UniqueConstraint, Boolean
from sqlalchemy.sql import func
from .base import Base

class Entity(Base):
    __tablename__ = 'entities'
    id = Column(Integer, primary_key=True)
    kind = Column(String, nullable=False)  # person|org|fund|agency|bill|docket|award|pac|nonprofit|case
    name = Column(String, nullable=False, index=True)
    canonical = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    meta = Column(JSON, nullable=True)

class EntityAlias(Base):
    __tablename__ = 'entity_aliases'
    id = Column(Integer, primary_key=True)
    entity_id = Column(Integer, ForeignKey('entities.id'), nullable=False)
    alias = Column(String, nullable=False, index=True)
    __table_args__ = (UniqueConstraint('entity_id','alias', name='uq_entity_alias'),)

class EntityIdentifier(Base):
    __tablename__ = 'entity_identifiers'
    id = Column(Integer, primary_key=True)
    entity_id = Column(Integer, ForeignKey('entities.id'), nullable=False)
    scheme = Column(String, nullable=False)  # CIK|LEI|EIN|UEI|CAGE|FEC|LDA|FARA|COURT|RIN|AWARD|DOCKET
    value = Column(String, nullable=False)
    __table_args__ = (UniqueConstraint('scheme','value', name='uq_scheme_value'),)

class Relationship(Base):
    __tablename__ = 'relationships'
    id = Column(Integer, primary_key=True)
    src_entity_id = Column(Integer, ForeignKey('entities.id'), nullable=False)
    dst_entity_id = Column(Integer, ForeignKey('entities.id'), nullable=False)
    kind = Column(String, nullable=False)  # owns|controls|affiliated|files|sponsors|awarded_to|donates|represented_by|...
    meta = Column(JSON, nullable=True)

class RelationshipEvidence(Base):
    __tablename__ = 'relationship_evidence'
    id = Column(Integer, primary_key=True)
    relationship_id = Column(Integer, ForeignKey('relationships.id'), nullable=False)
    evidence_ref_id = Column(Integer, nullable=True)  # FK to evidence_refs (not strict to avoid circular imports)
    meta = Column(JSON, nullable=True)  # page ranges, excerpts, etc.

class MergeCandidate(Base):
    __tablename__ = 'merge_candidates'
    id = Column(Integer, primary_key=True)
    a_entity_id = Column(Integer, ForeignKey('entities.id'), nullable=False)
    b_entity_id = Column(Integer, ForeignKey('entities.id'), nullable=False)
    score = Column(Integer, nullable=False)
    reason = Column(String, nullable=True)
    status = Column(String, nullable=False, default='pending')  # pending|approved|rejected|merged
    __table_args__ = (UniqueConstraint('a_entity_id','b_entity_id', name='uq_merge_pair'),)

class MergeAction(Base):
    __tablename__ = 'merge_actions'
    id = Column(Integer, primary_key=True)
    primary_id = Column(Integer, ForeignKey('entities.id'), nullable=False)
    secondary_id = Column(Integer, ForeignKey('entities.id'), nullable=False)
    action = Column(String, nullable=False)  # merge|unmerge
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    meta = Column(JSON, nullable=True)

class ResolutionQueue(Base):
    __tablename__ = 'resolution_queue'
    id = Column(Integer, primary_key=True)
    entity_id = Column(Integer, ForeignKey('entities.id'), nullable=False)
    reason = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
