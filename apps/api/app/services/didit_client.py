import os
import requests
from typing import Dict, Any

class DiditClient:
    def __init__(self, client_id: str | None = None, api_key: str | None = None, org_id: str | None = None):
        self.client_id = client_id or os.getenv("DIDIT_CLIENT_ID")
        self.api_key = api_key or os.getenv("DIDIT_API_KEY")
        self.org_id = org_id or os.getenv("DIDIT_ORG_ID")
        self.management_url = os.getenv("DIDIT_MANAGEMENT_BASE_URL", "https://apx.didit.me")
        self.verification_url = os.getenv("DIDIT_VERIFICATION_BASE_URL", "https://verification.didit.me")

    def is_configured(self) -> bool:
        return bool(self.client_id and self.api_key and self.org_id)

    def create_verification_session(self, redirect_url: str) -> Dict[str, Any]:
        """Initialize a KYC verification flow using Didit API."""
        if not self.is_configured():
            return {"error": "Didit credentials not configured."}

        url = f"{self.management_url}/v1/session/decision"
        
        headers = {
            "Authorization": f"Basic {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "client_id": self.client_id,
            "org_id": self.org_id,
            "redirect_url": redirect_url,
            "flow_type": "kyc_biometrics"
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": f"Failed to create Didit session: {str(e)}"}

didit_client = DiditClient()
