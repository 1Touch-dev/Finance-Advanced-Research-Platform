"""Registry API key and usage models."""
import hashlib
import secrets
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text, JSON
from sqlalchemy.sql import func

from .base import Base


class RegistryApiKey(Base):
    __tablename__ = "registry_api_keys"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    key_hash = Column(String, nullable=False, unique=True)
    key_prefix = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    rate_limit_per_min = Column(Integer, default=100)
    notes = Column(Text, nullable=True)

    @staticmethod
    def generate() -> tuple:
        """Returns (raw_key, key_hash, key_prefix)."""
        raw = "rak_" + secrets.token_urlsafe(32)
        h = hashlib.sha256(raw.encode()).hexdigest()
        return raw, h, raw[:12]

    @staticmethod
    def hash_key(raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()


class RegistryApiUsage(Base):
    __tablename__ = "registry_api_usage"

    id = Column(Integer, primary_key=True)
    key_hash = Column(String, nullable=False)
    endpoint = Column(String, nullable=False)
    query_params = Column(JSON, nullable=True)
    response_count = Column(Integer, default=0)
    ip_address = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
