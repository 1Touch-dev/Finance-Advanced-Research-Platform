"""
Database session management with connection pooling and health checks.

Pool settings (configurable via env):
  - DB_POOL_SIZE: Number of persistent connections (default: 5)
  - DB_MAX_OVERFLOW: Extra connections allowed under load (default: 10)
  - DB_POOL_TIMEOUT: Seconds to wait for a connection (default: 30)
  - DB_POOL_RECYCLE: Seconds before recycling a connection (default: 1800)
"""
from __future__ import annotations

import logging
import os
import time
from contextlib import contextmanager
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool

from app.core.settings import settings

logger = logging.getLogger(__name__)

# Pool configuration from environment
_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))  # 30 minutes

_is_sqlite = settings.database_url.startswith("sqlite")

if _is_sqlite:
    # SQLite: use StaticPool for single-connection mode
    _connect_args = {"check_same_thread": False}
    engine = create_engine(
        settings.database_url,
        connect_args=_connect_args,
        poolclass=StaticPool,
        pool_pre_ping=True,
        future=True,
    )
else:
    # PostgreSQL/MySQL: use QueuePool with proper sizing
    engine = create_engine(
        settings.database_url,
        poolclass=QueuePool,
        pool_size=_POOL_SIZE,
        max_overflow=_MAX_OVERFLOW,
        pool_timeout=_POOL_TIMEOUT,
        pool_recycle=_POOL_RECYCLE,
        pool_pre_ping=True,
        future=True,
    )

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Context manager for database sessions (for non-FastAPI use)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db_health() -> dict:
    """
    Check database connectivity and pool status.
    Returns a dict with status, latency, and pool info.
    """
    result = {
        "status": "unknown",
        "backend": "sqlite" if _is_sqlite else "postgresql",
        "latency_ms": None,
        "pool": None,
        "error": None,
    }

    try:
        t0 = time.perf_counter()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency = (time.perf_counter() - t0) * 1000
        result["status"] = "ok"
        result["latency_ms"] = round(latency, 2)

        # Pool stats (only for QueuePool)
        if not _is_sqlite and hasattr(engine.pool, "size"):
            result["pool"] = {
                "size": engine.pool.size(),
                "checkedin": engine.pool.checkedin(),
                "checkedout": engine.pool.checkedout(),
                "overflow": engine.pool.overflow(),
            }
    except Exception as exc:
        result["status"] = "error"
        result["error"] = str(exc)
        logger.warning("database health check failed: %s", exc)

    return result
