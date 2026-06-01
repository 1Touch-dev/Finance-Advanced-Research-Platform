import os
import requests
from typing import Dict, Any

class TwentyClient:
    def __init__(self, api_key_id: str | None = None, workspace_url: str | None = None):
        self.api_key_id = api_key_id or os.getenv("TWENTY_API_KEY_ID")
        self.workspace_url = workspace_url or os.getenv("TWENTY_WORKSPACE_URL", "https://fierce-lime-dragon.twenty.com")
        self.rest_url = os.getenv("TWENTY_API_REST", "https://api.twenty.com/rest")

    def is_configured(self) -> bool:
        return bool(self.api_key_id)

    def sync_company_entity(self, name: str, domain: str, meta: Dict[str, Any]) -> Dict[str, Any]:
        """Sync resolved corporate entities to Twenty CRM."""
        if not self.is_configured():
            return {"error": "Twenty CRM API key not configured."}

        url = f"{self.rest_url}/companies"
        
        headers = {
            "Authorization": f"Bearer {self.api_key_id}",
            "Content-Type": "application/json"
        }

        payload = {
            "name": name,
            "domainName": domain,
            "address": str(meta.get("address", "")),
            "x": str(meta.get("ticker", ""))
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": f"Failed to sync entity to Twenty CRM: {str(e)}"}

twenty_client = TwentyClient()
