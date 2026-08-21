import sys
import json
sys.path.insert(0, ".")
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)

from app.db.session import SessionLocal
from app.services import big_trade_scanner, investment_alert_service

db = SessionLocal()
try:
    print("=" * 60)
    print("F-03 LIVE — real Form 4 data + SendGrid + Twilio")
    print("=" * 60)
    f03 = big_trade_scanner.run_scan_all_rules(db, dry_run=False)
    for r in f03.get("results", []):
        print(f"  Rule: {r.get('rule_name')}")
        print(f"  Tickers scanned: {r.get('scanned_tickers')}")
        print(f"  Trades found: {r.get('trades_found')}")
        print(f"  Above threshold: {r.get('above_threshold')}")
        print(f"  New alerts: {r.get('new_alerts_created')}")
        print(f"  Notifications: {r.get('notifications_sent')}")
        alerts = r.get("alerts") or []
        if alerts:
            top = alerts[0]
            print(f"  Top trade: {top.get('ticker')} | {top.get('insider')} | ${float(top.get('value_usd') or 0):,.0f}")

    print()
    print("=" * 60)
    print("F-04 LIVE — real 13F/insider data + SendGrid + Twilio")
    print("=" * 60)
    f04 = investment_alert_service.run_scan(db, dry_run=False)
    print(f"  Scanned items: {f04.get('scanned_items')}")
    print(f"  New alerts: {f04.get('new_alerts_created')}")
    print(f"  Notifications: {f04.get('notifications_sent')}")
    for r in f04.get("results", []):
        if "error" in r:
            print(f"  [{r.get('ticker','?')}] ERROR: {r['error']}")
        else:
            print(
                f"  [{r['ticker']}] found={r['investments_found']} "
                f"new={r['new_alerts_created']} "
                f"email={r['notifications_sent']['email']} "
                f"sms={r['notifications_sent']['sms']}"
            )
            alerts = r.get("alerts") or []
            if alerts:
                top = alerts[0]
                print(
                    f"    Top: {top.get('investor_name')} | "
                    f"{top.get('investor_type')} | "
                    f"${float(top.get('value_usd') or 0):,.0f}"
                )
finally:
    db.close()
