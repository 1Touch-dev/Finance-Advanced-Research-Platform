from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class Institutional13FPeriodCache(Base):
    __tablename__ = "institutional_13f_period_cache"

    id = Column(Integer, primary_key=True)
    institution_cik = Column(String, nullable=False, index=True)
    report_period = Column(Date, nullable=False, index=True)
    institution_name = Column(String, nullable=False)
    primary_accession_number = Column(String, nullable=False)
    primary_form = Column(String, nullable=False)
    primary_filing_date = Column(Date, nullable=False)
    primary_is_amendment = Column(Boolean, nullable=False, default=False)
    primary_is_confidential_omitted = Column(Boolean, nullable=False, default=False)
    primary_amendment_type = Column(String, nullable=True)
    primary_amendment_no = Column(Integer, nullable=True)
    warnings_json = Column(JSON, nullable=True)
    data_quality_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    supplemental_amendments = relationship(
        "Institutional13FSupplementalAmendmentCache",
        back_populates="period_cache",
        cascade="all, delete-orphan",
        order_by="Institutional13FSupplementalAmendmentCache.sort_order",
    )
    positions = relationship(
        "Institutional13FPositionCache",
        back_populates="period_cache",
        cascade="all, delete-orphan",
        order_by="Institutional13FPositionCache.sort_order",
    )

    __table_args__ = (
        UniqueConstraint(
            "institution_cik",
            "report_period",
            name="uq_institutional_13f_cache_period",
        ),
    )


class Institutional13FSupplementalAmendmentCache(Base):
    __tablename__ = "institutional_13f_supplemental_amendment_cache"

    id = Column(Integer, primary_key=True)
    period_cache_id = Column(
        Integer,
        ForeignKey("institutional_13f_period_cache.id"),
        nullable=False,
        index=True,
    )
    sort_order = Column(Integer, nullable=False)
    accession_number = Column(String, nullable=False)
    form = Column(String, nullable=False)
    filing_date = Column(Date, nullable=False)
    amendment_type = Column(String, nullable=True)
    amendment_no = Column(Integer, nullable=True)
    is_confidential_omitted = Column(Boolean, nullable=False, default=False)

    period_cache = relationship(
        "Institutional13FPeriodCache",
        back_populates="supplemental_amendments",
    )

    __table_args__ = (
        UniqueConstraint(
            "period_cache_id",
            "accession_number",
            name="uq_institutional_13f_cache_supplemental_accession",
        ),
    )


class Institutional13FPositionCache(Base):
    __tablename__ = "institutional_13f_position_cache"

    id = Column(Integer, primary_key=True)
    period_cache_id = Column(
        Integer,
        ForeignKey("institutional_13f_period_cache.id"),
        nullable=False,
        index=True,
    )
    sort_order = Column(Integer, nullable=False)
    accession_number = Column(String, nullable=True)
    filing_date = Column(Date, nullable=True)
    issuer_name = Column(String, nullable=False)
    ticker = Column(String, nullable=True)
    ticker_resolution_method = Column(String, nullable=True)
    cusip = Column(String, nullable=True)
    security_title = Column(String, nullable=True)
    put_call = Column(String, nullable=True)
    shares = Column(Float, nullable=False, default=0.0)
    reported_value_usd = Column(Float, nullable=False, default=0.0)
    raw_row_index = Column(Integer, nullable=True)

    period_cache = relationship(
        "Institutional13FPeriodCache",
        back_populates="positions",
    )

    __table_args__ = (
        UniqueConstraint(
            "period_cache_id",
            "sort_order",
            name="uq_institutional_13f_cache_position_order",
        ),
    )
