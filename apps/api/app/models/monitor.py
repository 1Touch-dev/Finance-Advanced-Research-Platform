from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, ForeignKey, Text, Float
from sqlalchemy.sql import func
from .base import Base

class Watchlist(Base):
    __tablename__ = 'watchlists'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    meta = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class WatchlistItem(Base):
    __tablename__ = 'watchlist_items'
    id = Column(Integer, primary_key=True)
    watchlist_id = Column(Integer, ForeignKey('watchlists.id'), nullable=False)
    entity_id = Column(Integer, nullable=True)
    ticker = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

class Portfolio(Base):
    __tablename__ = 'portfolios'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    base_ccy = Column(String, nullable=True, default='USD')
    thesis = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Position(Base):
    __tablename__ = 'positions'
    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), nullable=False)
    entity_id = Column(Integer, nullable=True)
    ticker = Column(String, nullable=True)
    qty = Column(Float, nullable=False)
    cost_basis = Column(Float, nullable=False)
    notes = Column(Text, nullable=True)

class AlertRule(Base):
    __tablename__ = 'alert_rules'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    kind = Column(String, nullable=False)  # filing|lobbying|contract|lawsuit|sanction|earnings|price_move|volume_spike
    params = Column(JSON, nullable=True)
    watchlist_id = Column(Integer, ForeignKey('watchlists.id'), nullable=True)
    portfolio_id = Column(Integer, ForeignKey('portfolios.id'), nullable=True)
    enabled = Column(Boolean, default=True)

class AlertEvent(Base):
    __tablename__ = 'alert_events'
    id = Column(Integer, primary_key=True)
    rule_id = Column(Integer, ForeignKey('alert_rules.id'), nullable=False)
    entity_id = Column(Integer, nullable=True)
    ticker = Column(String, nullable=True)
    kind = Column(String, nullable=False)
    payload = Column(JSON, nullable=True)
    delivered = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class DeliveryChannel(Base):
    __tablename__ = 'delivery_channels'
    id = Column(Integer, primary_key=True)
    rule_id = Column(Integer, ForeignKey('alert_rules.id'), nullable=False)
    kind = Column(String, nullable=False)  # inapp|email|slack|teams|webhook
    target = Column(String, nullable=True)  # address/webhook URL
    meta = Column(JSON, nullable=True)
