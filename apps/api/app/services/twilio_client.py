import os
import requests
from typing import Dict, Any

class TwilioClient:
    def __init__(self, sid: str | None = None, token: str | None = None, phone_number: str | None = None):
        self.sid = sid or os.getenv("TWILIO_ACCOUNT_SID")
        self.token = token or os.getenv("TWILIO_AUTH_TOKEN")
        self.phone_number = phone_number or os.getenv("TWILIO_PHONE_NUMBER")

    def is_configured(self) -> bool:
        return bool(self.sid and self.token and self.phone_number)

    def send_sms(self, to: str, body: str) -> Dict[str, Any]:
        """Dispatch instant SMS via Twilio API."""
        if not self.is_configured():
            return {"error": "Twilio parameters not configured."}

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.sid}/Messages.json"
        
        payload = {
            "From": self.phone_number,
            "To": to,
            "Body": body
        }

        try:
            resp = requests.post(url, data=payload, auth=(self.sid, self.token), timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": f"Failed to send Twilio SMS: {str(e)}"}

twilio_client = TwilioClient()
