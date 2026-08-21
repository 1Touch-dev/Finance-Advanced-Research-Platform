import requests

r = requests.post("http://localhost:3001/tracking/scan/insider-trades?dry_run=false", timeout=120)
print("Status:", r.status_code)
data = r.json()
for res in data.get("results", []):
    print("Rule:", res.get("rule_name"))
    print("  scanned_tickers:", res.get("scanned_tickers"))
    print("  above_threshold:", res.get("above_threshold"))
    print("  new_alerts_created:", res.get("new_alerts_created"))
    print("  notifications_sent:", res.get("notifications_sent"))
