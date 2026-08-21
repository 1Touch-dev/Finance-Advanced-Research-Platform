import sys
sys.path.insert(0, ".")
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)

from app.db.session import SessionLocal
from app.services import investment_alert_service
import json

db = SessionLocal()
try:
    print("Running F-04 LIVE scan (dry_run=False)...")
    result = investment_alert_service.run_scan(db, dry_run=False)
    print(f"\nSummary:")
    print(f"  Scanned items:     {result['scanned_items']}")
    print(f"  New alerts:        {result['new_alerts_created']}")
    print(f"  Emails sent:       {result['notifications_sent']['email']}")
    print(f"  SMS sent:          {result['notifications_sent']['sms']}")
    for r in result["results"]:
        if "error" in r:
            print(f"\n  [{r.get('ticker','?')}] ERROR: {r['error']}")
        else:
            print(f"\n  [{r['ticker']}] found={r['investments_found']} "
                  f"new={r['new_alerts_created']} "
                  f"email={r['notifications_sent']['email']} sms={r['notifications_sent']['sms']}")
finally:
    db.close()
