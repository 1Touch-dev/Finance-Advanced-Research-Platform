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
    # F-04: per-item investment threshold alert settings
    investment_threshold = Column(Float, nullable=True)
    notify_email = Column(String, nullable=True)
    notify_phone = Column(String, nullable=True)
    alert_on_buy = Column(Boolean, default=True, nullable=False, server_default='1')
    alert_on_sell = Column(Boolean, default=False, nullable=False, server_default='0')


class InvestmentAlertSeen(Base):
    """Deduplication log — prevents re-alerting the same investment to the same user."""
    __tablename__ = 'investment_alert_seen'
    id = Column(Integer, primary_key=True)
    watchlist_item_id = Column(Integer, ForeignKey('watchlist_items.id'), nullable=False)
    investor_name = Column(String, nullable=False)
    ticker = Column(String, nullable=False)
    txn_type = Column(String, nullable=False)
    value_usd = Column(Float, nullable=True)
    trade_date = Column(String, nullable=False)
    alerted_at = Column(DateTime(timezone=True), server_default=func.now())

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


# ── Shared Watchlists & Dashboards (#46) ─────────────────────────────────────

class WatchlistShare(Base):
    """Tracks watchlist sharing between users."""
    __tablename__ = 'watchlist_shares'
    id = Column(Integer, primary_key=True)
    watchlist_id = Column(Integer, ForeignKey('watchlists.id'), nullable=False)
    shared_by = Column(String, nullable=False)  # user email/id who shared
    shared_with = Column(String, nullable=False)  # user email/id shared to
    permission = Column(String, default='view')  # view|edit
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Dashboard(Base):
    """User dashboard configuration with widgets."""
    __tablename__ = 'dashboards'
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    name = Column(String, nullable=False, default='My Dashboard')
    is_default = Column(Boolean, default=False)
    layout = Column(JSON, nullable=True)  # Grid layout configuration
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DashboardWidget(Base):
    """Individual widget on a dashboard."""
    __tablename__ = 'dashboard_widgets'
    id = Column(Integer, primary_key=True)
    dashboard_id = Column(Integer, ForeignKey('dashboards.id'), nullable=False)
    widget_type = Column(String, nullable=False)  # watchlist|portfolio|chart|news|calendar
    title = Column(String, nullable=True)
    config = Column(JSON, nullable=True)  # Widget-specific configuration
    position_x = Column(Integer, default=0)
    position_y = Column(Integer, default=0)
    width = Column(Integer, default=1)
    height = Column(Integer, default=1)


# ── Comments & Annotations (#47) ─────────────────────────────────────────────


class EntityComment(Base):
    """User comment on an entity (stock, filing, report, etc.)."""
    __tablename__ = 'entity_comments'
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    user_name = Column(String, nullable=True)  # Display name
    # Target entity
    entity_type = Column(String, nullable=False)  # stock|filing|report|watchlist|portfolio
    entity_id = Column(String, nullable=False)  # ticker or ID
    # Comment content
    content = Column(Text, nullable=False)
    # Threading
    parent_id = Column(Integer, ForeignKey('entity_comments.id'), nullable=True)  # For replies
    # Visibility
    visibility = Column(String, default='private')  # private|team|public
    # Metadata
    is_edited = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class CommentReaction(Base):
    """Reaction/like on a comment."""
    __tablename__ = 'comment_reactions'
    id = Column(Integer, primary_key=True)
    comment_id = Column(Integer, ForeignKey('entity_comments.id'), nullable=False)
    user_id = Column(String, nullable=False)
    reaction_type = Column(String, nullable=False)  # like|insightful|disagree|question
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Annotation(Base):
    """Text annotation/highlight in a document."""
    __tablename__ = 'annotations'
    id = Column(Integer, primary_key=True)
    user_id = Column(String, nullable=False)
    # Target document
    document_type = Column(String, nullable=False)  # filing|report|transcript|news
    document_id = Column(String, nullable=False)
    # Position in document
    start_offset = Column(Integer, nullable=False)
    end_offset = Column(Integer, nullable=False)
    selected_text = Column(Text, nullable=True)  # The highlighted text
    # Annotation content
    note = Column(Text, nullable=True)  # User's note
    color = Column(String, default='yellow')  # yellow|green|blue|red|purple
    # Tags for organization
    tags = Column(JSON, nullable=True)  # ["risk", "key-metric", etc.]
    # Visibility
    visibility = Column(String, default='private')  # private|team|public
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
