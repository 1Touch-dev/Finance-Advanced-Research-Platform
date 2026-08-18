"""
F-08 RSS Phase 2 — Event Intelligence storage.

One row per clustered "event" (a story covered by one or more RSS articles),
enriched with confirmed facts, unconfirmed claims, cross-source conflicts, and
per-article perspective labels. See docs/features/F08_RSS_PHASE2_EVENT_INTELLIGENCE.md.

Deliberately modeled with the SQLAlchemy ORM (Base.metadata.create_all), unlike
the raw-SQL Postgres-only rss_articles/rss_sources tables in rss_worker.py —
this makes the table portable across the SQLite (local dev) and Postgres
(staging/prod) backends this codebase runs on, with zero dialect branching.
"""
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text
from sqlalchemy.sql import func
from .base import Base


class RssEvent(Base):
    __tablename__ = "rss_events"

    id = Column(Integer, primary_key=True)
    topic_entity = Column(String, nullable=True, index=True)
    headline = Column(Text, nullable=False)
    article_ids = Column(JSON, nullable=True)      # [int, ...] — rss_articles.id values
    sources = Column(JSON, nullable=True)          # [{"source_name","title","url","published_at"}]
    source_count = Column(Integer, default=1, nullable=False)

    confirmed_facts = Column(JSON, nullable=True)      # [{"fact": "...", "sources": ["Reuters", ...]}]
    unconfirmed_claims = Column(JSON, nullable=True)   # [{"claim": "...", "source": "..."}]
    conflicts = Column(JSON, nullable=True)            # [{"claim_a","claim_b","source_a","source_b","note"}]
    perspectives = Column(JSON, nullable=True)         # [{"source","framing","lean","notes"}]
    market_impact = Column(Text, nullable=True)
    key_quotes = Column(JSON, nullable=True)           # [{"quote","attributed_to","source"}]

    enrichment_status = Column(String, default="pending", nullable=False)  # pending|enriched|failed|skipped_single_source
    enrichment_error = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
