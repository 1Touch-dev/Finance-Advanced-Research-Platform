"""
Price Alerts Service (Band C #35)

Provides price alert functionality:
- Create/update/delete price alerts
- Multiple alert types (above/below, percent change, volume spike)
- Alert triggering and notification
- Alert history

Persistence: SQLite via SQLAlchemy (survives restarts).
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
import logging
import uuid

import yfinance as yf

logger = logging.getLogger(__name__)

from app.db.session import get_db_context
from app.models.monitor import PriceAlertModel, AlertNotificationModel


class AlertType(str, Enum):
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    PERCENT_CHANGE = "percent_change"
    VOLUME_SPIKE = "volume_spike"
    NEW_HIGH = "new_high"
    NEW_LOW = "new_low"


class AlertStatus(str, Enum):
    ACTIVE = "active"
    TRIGGERED = "triggered"
    EXPIRED = "expired"
    DISABLED = "disabled"


class NotificationChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


@dataclass
class PriceAlert:
    alert_id: str
    user_id: str
    ticker: str
    alert_type: str
    target_value: float
    current_value: Optional[float]
    status: str
    created_at: str
    triggered_at: Optional[str]
    expires_at: Optional[str]
    notification_channels: List[str]
    note: Optional[str]
    recurring: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "user_id": self.user_id,
            "ticker": self.ticker,
            "alert_type": self.alert_type,
            "target_value": self.target_value,
            "current_value": self.current_value,
            "status": self.status,
            "created_at": self.created_at,
            "triggered_at": self.triggered_at,
            "expires_at": self.expires_at,
            "notification_channels": self.notification_channels,
            "note": self.note,
            "recurring": self.recurring,
        }


@dataclass
class AlertNotification:
    notification_id: str
    alert_id: str
    user_id: str
    ticker: str
    message: str
    sent_at: str
    channel: str
    read: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "notification_id": self.notification_id,
            "alert_id": self.alert_id,
            "user_id": self.user_id,
            "ticker": self.ticker,
            "message": self.message,
            "sent_at": self.sent_at,
            "channel": self.channel,
            "read": self.read,
        }


# ── Helpers ───────────────────────────────────────────────────────────────────

_price_cache: Dict[str, Tuple[float, datetime]] = {}  # ticker -> (price, timestamp)
CACHE_TTL = 300  # 5 minutes


def _get_real_price(ticker: str) -> float:
    """Get real current price from yfinance with 5-min cache."""
    now = datetime.utcnow()
    if ticker in _price_cache:
        price, cached_at = _price_cache[ticker]
        if (now - cached_at).total_seconds() < CACHE_TTL:
            return price
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1d")
        if not hist.empty:
            price = float(hist['Close'].iloc[-1])
            _price_cache[ticker] = (price, now)
            return price
    except Exception as exc:
        logger.debug("price fetch failed for %s: %s", ticker, exc)
    if ticker in _price_cache:
        return _price_cache[ticker][0]
    return 0.0


def _row_to_alert(row: PriceAlertModel) -> PriceAlert:
    """Convert a DB row to the PriceAlert dataclass."""
    return PriceAlert(
        alert_id=row.alert_id,
        user_id=row.user_id,
        ticker=row.ticker,
        alert_type=row.alert_type,
        target_value=row.target_value,
        current_value=row.current_value,
        status=row.status,
        created_at=row.created_at,
        triggered_at=row.triggered_at,
        expires_at=row.expires_at,
        notification_channels=row.notification_channels or [],
        note=row.note,
        recurring=row.recurring or False,
    )


def _row_to_notification(row: AlertNotificationModel) -> AlertNotification:
    """Convert a DB row to the AlertNotification dataclass."""
    return AlertNotification(
        notification_id=row.notification_id,
        alert_id=row.alert_id,
        user_id=row.user_id,
        ticker=row.ticker,
        message=row.message,
        sent_at=row.sent_at,
        channel=row.channel,
        read=row.read or False,
    )


# ── Service Functions ─────────────────────────────────────────────────────────


def create_alert(
    user_id: str,
    ticker: str,
    alert_type: str,
    target_value: float,
    notification_channels: Optional[List[str]] = None,
    note: Optional[str] = None,
    expires_in_days: Optional[int] = None,
    recurring: bool = False,
) -> PriceAlert:
    """Create a new price alert."""
    alert_id = f"alert_{uuid.uuid4().hex[:8]}"
    now = datetime.utcnow()

    expires_at = None
    if expires_in_days:
        expires_at = (now + timedelta(days=expires_in_days)).isoformat()

    current_price = _get_real_price(ticker.upper())
    channels = notification_channels or [NotificationChannel.IN_APP.value]

    with get_db_context() as db:
        row = PriceAlertModel(
            alert_id=alert_id,
            user_id=user_id,
            ticker=ticker.upper(),
            alert_type=alert_type,
            target_value=target_value,
            current_value=current_price,
            status=AlertStatus.ACTIVE.value,
            created_at=now.isoformat(),
            triggered_at=None,
            expires_at=expires_at,
            notification_channels=channels,
            note=note,
            recurring=recurring,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return _row_to_alert(row)


def get_user_alerts(
    user_id: str,
    status: Optional[str] = None,
    ticker: Optional[str] = None,
) -> List[PriceAlert]:
    """Get all alerts for a user."""
    with get_db_context() as db:
        q = db.query(PriceAlertModel).filter(PriceAlertModel.user_id == user_id)

        if status:
            q = q.filter(PriceAlertModel.status == status)
        if ticker:
            q = q.filter(PriceAlertModel.ticker == ticker.upper())

        rows = q.order_by(PriceAlertModel.created_at.desc()).all()

        alerts = []
        for row in rows:
            row.current_value = _get_real_price(row.ticker)
            alert = _row_to_alert(row)
            alerts.append(alert)

        db.commit()
        return alerts


def get_alert(alert_id: str, user_id: str) -> Optional[PriceAlert]:
    """Get a specific alert."""
    with get_db_context() as db:
        row = (
            db.query(PriceAlertModel)
            .filter(PriceAlertModel.alert_id == alert_id, PriceAlertModel.user_id == user_id)
            .first()
        )
        if not row:
            return None
        row.current_value = _get_real_price(row.ticker)
        db.commit()
        return _row_to_alert(row)


def update_alert(
    alert_id: str,
    user_id: str,
    target_value: Optional[float] = None,
    notification_channels: Optional[List[str]] = None,
    note: Optional[str] = None,
    status: Optional[str] = None,
) -> Optional[PriceAlert]:
    """Update an existing alert."""
    with get_db_context() as db:
        row = (
            db.query(PriceAlertModel)
            .filter(PriceAlertModel.alert_id == alert_id, PriceAlertModel.user_id == user_id)
            .first()
        )
        if not row:
            return None

        if target_value is not None:
            row.target_value = target_value
        if notification_channels is not None:
            row.notification_channels = notification_channels
        if note is not None:
            row.note = note
        if status is not None:
            row.status = status

        db.commit()
        db.refresh(row)
        return _row_to_alert(row)


def delete_alert(alert_id: str, user_id: str) -> bool:
    """Delete an alert."""
    with get_db_context() as db:
        row = (
            db.query(PriceAlertModel)
            .filter(PriceAlertModel.alert_id == alert_id, PriceAlertModel.user_id == user_id)
            .first()
        )
        if not row:
            return False
        db.delete(row)
        db.commit()
        return True


def check_alerts(ticker: str, current_price: float) -> List[PriceAlert]:
    """Check if any alerts should be triggered for a ticker."""
    triggered = []

    with get_db_context() as db:
        rows = (
            db.query(PriceAlertModel)
            .filter(
                PriceAlertModel.ticker == ticker.upper(),
                PriceAlertModel.status == AlertStatus.ACTIVE.value,
            )
            .all()
        )

        for row in rows:
            should_trigger = False

            if row.alert_type == AlertType.PRICE_ABOVE.value:
                should_trigger = current_price >= row.target_value
            elif row.alert_type == AlertType.PRICE_BELOW.value:
                should_trigger = current_price <= row.target_value
            elif row.alert_type == AlertType.PERCENT_CHANGE.value:
                if row.current_value:
                    pct_change = abs((current_price - row.current_value) / row.current_value * 100)
                    should_trigger = pct_change >= row.target_value

            if should_trigger:
                row.triggered_at = datetime.utcnow().isoformat()
                if not row.recurring:
                    row.status = AlertStatus.TRIGGERED.value
                triggered.append(_row_to_alert(row))
                _create_notification_in_db(db, row, current_price)

        db.commit()

    return triggered


def _create_notification_in_db(db, alert_row: PriceAlertModel, current_price: float) -> None:
    """Create a notification row for a triggered alert (within an existing session)."""
    notif_id = f"notif_{uuid.uuid4().hex[:8]}"

    messages = {
        AlertType.PRICE_ABOVE.value: f"{alert_row.ticker} is now above ${alert_row.target_value:.2f} (current: ${current_price:.2f})",
        AlertType.PRICE_BELOW.value: f"{alert_row.ticker} is now below ${alert_row.target_value:.2f} (current: ${current_price:.2f})",
        AlertType.PERCENT_CHANGE.value: f"{alert_row.ticker} moved {alert_row.target_value}% (current: ${current_price:.2f})",
    }

    channels = alert_row.notification_channels or []
    channel = channels[0] if channels else "in_app"

    notif = AlertNotificationModel(
        notification_id=notif_id,
        alert_id=alert_row.alert_id,
        user_id=alert_row.user_id,
        ticker=alert_row.ticker,
        message=messages.get(alert_row.alert_type, f"Alert triggered for {alert_row.ticker}"),
        sent_at=datetime.utcnow().isoformat(),
        channel=channel,
        read=False,
    )
    db.add(notif)


def get_user_notifications(
    user_id: str,
    unread_only: bool = False,
    limit: int = 50,
) -> List[AlertNotification]:
    """Get notifications for a user."""
    with get_db_context() as db:
        q = db.query(AlertNotificationModel).filter(AlertNotificationModel.user_id == user_id)

        if unread_only:
            q = q.filter(AlertNotificationModel.read == False)  # noqa: E712

        rows = q.order_by(AlertNotificationModel.sent_at.desc()).limit(limit).all()
        return [_row_to_notification(r) for r in rows]


def mark_notification_read(notification_id: str, user_id: str) -> bool:
    """Mark a notification as read."""
    with get_db_context() as db:
        row = (
            db.query(AlertNotificationModel)
            .filter(
                AlertNotificationModel.notification_id == notification_id,
                AlertNotificationModel.user_id == user_id,
            )
            .first()
        )
        if not row:
            return False
        row.read = True
        db.commit()
        return True


def get_alert_types() -> List[Dict[str, Any]]:
    """Get available alert types."""
    return [
        {
            "type": AlertType.PRICE_ABOVE.value,
            "name": "Price Above",
            "description": "Trigger when price goes above target",
            "value_label": "Target Price",
        },
        {
            "type": AlertType.PRICE_BELOW.value,
            "name": "Price Below",
            "description": "Trigger when price drops below target",
            "value_label": "Target Price",
        },
        {
            "type": AlertType.PERCENT_CHANGE.value,
            "name": "Percent Change",
            "description": "Trigger on percentage move",
            "value_label": "Percent (%)",
        },
        {
            "type": AlertType.VOLUME_SPIKE.value,
            "name": "Volume Spike",
            "description": "Trigger on unusual volume",
            "value_label": "Volume Multiplier",
        },
        {
            "type": AlertType.NEW_HIGH.value,
            "name": "New High",
            "description": "Trigger on new 52-week high",
            "value_label": "N/A",
        },
        {
            "type": AlertType.NEW_LOW.value,
            "name": "New Low",
            "description": "Trigger on new 52-week low",
            "value_label": "N/A",
        },
    ]


def get_alert_stats(user_id: str) -> Dict[str, Any]:
    """Get alert statistics for a user."""
    with get_db_context() as db:
        total = db.query(PriceAlertModel).filter(PriceAlertModel.user_id == user_id).count()
        active = (
            db.query(PriceAlertModel)
            .filter(PriceAlertModel.user_id == user_id, PriceAlertModel.status == AlertStatus.ACTIVE.value)
            .count()
        )
        today_prefix = datetime.utcnow().strftime("%Y-%m-%d")
        triggered_today = (
            db.query(PriceAlertModel)
            .filter(
                PriceAlertModel.user_id == user_id,
                PriceAlertModel.triggered_at.isnot(None),
                PriceAlertModel.triggered_at.like(f"{today_prefix}%"),
            )
            .count()
        )
        triggered_total = (
            db.query(PriceAlertModel)
            .filter(PriceAlertModel.user_id == user_id, PriceAlertModel.status == AlertStatus.TRIGGERED.value)
            .count()
        )
        unread = (
            db.query(AlertNotificationModel)
            .filter(AlertNotificationModel.user_id == user_id, AlertNotificationModel.read == False)  # noqa: E712
            .count()
        )

    return {
        "total_alerts": total,
        "active": active,
        "triggered_today": triggered_today,
        "triggered_total": triggered_total,
        "unread_notifications": unread,
    }
