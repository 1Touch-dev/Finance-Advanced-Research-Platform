import sys
sys.path.insert(0, ".")
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)
import os
import requests

sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
from_phone = os.getenv("TWILIO_PHONE_NUMBER", "").strip()
to_phone = os.getenv("ALERT_RECIPIENT_PHONE", "").strip()

print("SID:", sid)
print("Token:", token[:8] + "..." if token else "(empty)")
print("From:", from_phone, "| To:", to_phone)

r = requests.post(
    f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
    auth=(sid, token),
    data={"From": from_phone, "To": to_phone,
          "Body": "Finance Platform: Big Trade Alert test - 73 insider trades found (Musk $7B TSLA + more)"},
)
print("Status:", r.status_code)
print("Response:", r.text[:300])
