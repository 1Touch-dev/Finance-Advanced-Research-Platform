import os
import requests
from typing import Dict, Any

class SendGridClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("SENDGRID_API_KEY")
        self.sender_email = "alerts@democapital.test"

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def send_email(self, to_email: str, subject: str, body_html: str) -> Dict[str, Any]:
        """Deliver consolidated email alerts via SendGrid Web API."""
        if not self.is_configured():
            return {"error": "SendGrid API key not configured."}

        url = "https://api.sendgrid.com/v3/mail/send"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "personalizations": [
                {
                    "to": [{"email": to_email}]
                }
            ],
            "from": {
                "email": self.sender_email,
                "name": "Enterprise Intelligence Platform"
            },
            "subject": subject,
            "content": [
                {
                    "type": "text/html",
                    "value": body_html
                }
            ]
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=15)
            # SendGrid returns 202 Accepted on success
            if resp.status_code in (200, 201, 202):
                return {"success": True}
            return {"error": f"SendGrid returned status code: {resp.status_code}", "body": resp.text}
        except Exception as e:
            return {"error": f"Failed to send SendGrid email: {str(e)}"}

sendgrid_client = SendGridClient()
