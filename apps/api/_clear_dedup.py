import sys

sys.path.insert(0, ".")

from dotenv import find_dotenv, load_dotenv
from sqlalchemy import text

from app.db.session import SessionLocal

load_dotenv(find_dotenv(), override=True)

db = SessionLocal()
db.execute(text("DELETE FROM alert_events WHERE kind = 'insider_trade'"))
db.execute(text("DELETE FROM investment_alert_seen"))
db.commit()
print("Cleared F-03 alert_events and F-04 investment_alert_seen dedup rows")
db.close()
