import os
import hmac
import hashlib
import requests
from typing import Dict, Any

class StripeClient:
    def __init__(self, secret_key: str | None = None, webhook_secret: str | None = None):
        self.secret_key = secret_key or os.getenv("STRIPE_SECRET_KEY")
        self.webhook_secret = webhook_secret or os.getenv("STRIPE_WEBHOOK_SECRET")
        self.base_url = "https://api.stripe.com/v1"

    def is_configured(self) -> bool:
        return bool(self.secret_key)

    def create_checkout_session(self, price_id: str, success_url: str, cancel_url: str) -> Dict[str, Any]:
        """Create a Stripe Checkout Session using HTTP API."""
        if not self.is_configured():
            return {"error": "Stripe secret key not configured."}

        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        payload = {
            "payment_method_types[]": "card",
            "line_items[0][price]": price_id,
            "line_items[0][quantity]": "1",
            "mode": "subscription",
            "success_url": success_url,
            "cancel_url": cancel_url
        }

        try:
            resp = requests.post(f"{self.base_url}/checkout/sessions", data=payload, headers=headers, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": f"Failed to create Stripe session: {str(e)}"}

    def verify_webhook(self, payload: bytes, sig_header: str) -> bool:
        """Verify the signature of incoming Stripe webhooks using native HMAC-SHA256."""
        if not self.webhook_secret or not sig_header:
            return False
        try:
            # sig_header is like 't=1492774577,v1=5257a869e4ece...'
            parts = {}
            for item in sig_header.split(','):
                k, v = item.split('=', 1)
                parts[k.strip()] = v.strip()

            timestamp = parts.get('t')
            v1 = parts.get('v1')
            if not timestamp or not v1:
                return False

            # Payload to sign: timestamp + "." + request_body
            signed_payload = f"{timestamp}.".encode('utf-8') + payload
            computed = hmac.new(
                self.webhook_secret.encode('utf-8'),
                signed_payload,
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(computed, v1)
        except Exception:
            return False

stripe_client = StripeClient()
