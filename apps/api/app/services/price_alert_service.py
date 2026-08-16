"""
Price Alerts Service (Band C #35)

Provides price alert functionality:
- Create/update/delete price alerts
- Multiple alert types (above/below, percent change, volume spike)
- Alert triggering and notification
- Alert history
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid


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


# ── In-Memory Storage ─────────────────────────────────────────────────────────

_alerts: Dict[str, PriceAlert] = {}
_notifications: Dict[str, AlertNotification] = {}

# Mock current prices
_mock_prices: Dict[str, float] = {
    "AAPL": 185.50,
    "MSFT": 378.25,
    "GOOGL": 142.80,
    "AMZN": 178.90,
    "NVDA": 875.40,
    "META": 495.20,
    "TSLA": 245.60,
    "JPM": 195.30,
}


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
    
    current_price = _mock_prices.get(ticker.upper(), 100.0)
    
    alert = PriceAlert(
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
        notification_channels=notification_channels or [NotificationChannel.IN_APP.value],
        note=note,
        recurring=recurring,
    )
    
    _alerts[alert_id] = alert
    return alert


def get_user_alerts(
    user_id: str,
    status: Optional[str] = None,
    ticker: Optional[str] = None,
) -> List[PriceAlert]:
    """Get all alerts for a user."""
    alerts = [a for a in _alerts.values() if a.user_id == user_id]
    
    if status:
        alerts = [a for a in alerts if a.status == status]
    if ticker:
        alerts = [a for a in alerts if a.ticker == ticker.upper()]
    
    # Update current values
    for alert in alerts:
        alert.current_value = _mock_prices.get(alert.ticker, 100.0)
    
    return sorted(alerts, key=lambda a: a.created_at, reverse=True)


def get_alert(alert_id: str, user_id: str) -> Optional[PriceAlert]:
    """Get a specific alert."""
    alert = _alerts.get(alert_id)
    if alert and alert.user_id == user_id:
        alert.current_value = _mock_prices.get(alert.ticker, 100.0)
        return alert
    return None


def update_alert(
    alert_id: str,
    user_id: str,
    target_value: Optional[float] = None,
    notification_channels: Optional[List[str]] = None,
    note: Optional[str] = None,
    status: Optional[str] = None,
) -> Optional[PriceAlert]:
    """Update an existing alert."""
    alert = _alerts.get(alert_id)
    if not alert or alert.user_id != user_id:
        return None
    
    if target_value is not None:
        alert.target_value = target_value
    if notification_channels is not None:
        alert.notification_channels = notification_channels
    if note is not None:
        alert.note = note
    if status is not None:
        alert.status = status
    
    return alert


def delete_alert(alert_id: str, user_id: str) -> bool:
    """Delete an alert."""
    alert = _alerts.get(alert_id)
    if alert and alert.user_id == user_id:
        del _alerts[alert_id]
        return True
    return False


def check_alerts(ticker: str, current_price: float) -> List[PriceAlert]:
    """Check if any alerts should be triggered for a ticker."""
    triggered = []
    
    for alert in _alerts.values():
        if alert.ticker != ticker.upper() or alert.status != AlertStatus.ACTIVE.value:
            continue
        
        should_trigger = False
        
        if alert.alert_type == AlertType.PRICE_ABOVE.value:
            should_trigger = current_price >= alert.target_value
        elif alert.alert_type == AlertType.PRICE_BELOW.value:
            should_trigger = current_price <= alert.target_value
        elif alert.alert_type == AlertType.PERCENT_CHANGE.value:
            if alert.current_value:
                pct_change = abs((current_price - alert.current_value) / alert.current_value * 100)
                should_trigger = pct_change >= alert.target_value
        
        if should_trigger:
            alert.triggered_at = datetime.utcnow().isoformat()
            if not alert.recurring:
                alert.status = AlertStatus.TRIGGERED.value
            triggered.append(alert)
            
            # Create notification
            _create_notification(alert, current_price)
    
    return triggered


def _create_notification(alert: PriceAlert, current_price: float) -> AlertNotification:
    """Create a notification for a triggered alert."""
    notif_id = f"notif_{uuid.uuid4().hex[:8]}"
    
    messages = {
        AlertType.PRICE_ABOVE.value: f"{alert.ticker} is now above ${alert.target_value:.2f} (current: ${current_price:.2f})",
        AlertType.PRICE_BELOW.value: f"{alert.ticker} is now below ${alert.target_value:.2f} (current: ${current_price:.2f})",
        AlertType.PERCENT_CHANGE.value: f"{alert.ticker} moved {alert.target_value}% (current: ${current_price:.2f})",
    }
    
    notification = AlertNotification(
        notification_id=notif_id,
        alert_id=alert.alert_id,
        user_id=alert.user_id,
        ticker=alert.ticker,
        message=messages.get(alert.alert_type, f"Alert triggered for {alert.ticker}"),
        sent_at=datetime.utcnow().isoformat(),
        channel=alert.notification_channels[0] if alert.notification_channels else "in_app",
        read=False,
    )
    
    _notifications[notif_id] = notification
    return notification


def get_user_notifications(
    user_id: str,
    unread_only: bool = False,
    limit: int = 50,
) -> List[AlertNotification]:
    """Get notifications for a user."""
    notifs = [n for n in _notifications.values() if n.user_id == user_id]
    
    if unread_only:
        notifs = [n for n in notifs if not n.read]
    
    return sorted(notifs, key=lambda n: n.sent_at, reverse=True)[:limit]


def mark_notification_read(notification_id: str, user_id: str) -> bool:
    """Mark a notification as read."""
    notif = _notifications.get(notification_id)
    if notif and notif.user_id == user_id:
        notif.read = True
        return True
    return False


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
    user_alerts = [a for a in _alerts.values() if a.user_id == user_id]
    
    return {
        "total_alerts": len(user_alerts),
        "active": len([a for a in user_alerts if a.status == AlertStatus.ACTIVE.value]),
        "triggered_today": len([a for a in user_alerts 
                                if a.triggered_at and a.triggered_at.startswith(datetime.utcnow().strftime("%Y-%m-%d"))]),
        "triggered_total": len([a for a in user_alerts if a.status == AlertStatus.TRIGGERED.value]),
        "unread_notifications": len([n for n in _notifications.values() 
                                     if n.user_id == user_id and not n.read]),
    }
