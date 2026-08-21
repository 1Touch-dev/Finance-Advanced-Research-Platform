import sys
sys.path.insert(0, ".")
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)

from sqlalchemy import text
from app.db.session import SessionLocal
from app.models.monitor import WatchlistItem

PHONE = "+917477028192"
EMAIL = "akash.kr.issu@gmail.com"

db = SessionLocal()

# Fix F-04 notify phones to verified Twilio number
updated = 0
for item in db.query(WatchlistItem).filter(WatchlistItem.ticker.isnot(None)).all():
    if item.investment_threshold is not None:
        item.notify_phone = PHONE
        item.notify_email = EMAIL
        updated += 1
db.commit()
print(f"Updated {updated} watchlist item(s) notify_phone -> {PHONE}")

# Clear dedup so real alerts fire again
db.execute(text("DELETE FROM alert_events WHERE kind IN ('insider_trade', 'investment_alert')"))
db.execute(text("DELETE FROM investment_alert_seen"))
db.commit()
print("Cleared F-03/F-04 dedup records")
db.close()
