import os
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import httpx


class OIDCProvider:
    """Google Workspace OIDC integration."""

    def __init__(self):
        self.client_id = os.getenv("OIDC_CLIENT_ID", "")
        self.client_secret = os.getenv("OIDC_CLIENT_SECRET", "")
        self.redirect_uri = os.getenv("OIDC_REDIRECT_URI", "http://localhost:3001/auth/oidc/callback")
        self.issuer = os.getenv("OIDC_ISSUER", "https://accounts.google.com")
        self.auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
        self.token_url = "https://oauth2.googleapis.com/token"
        self.userinfo_url = "https://openidconnect.googleapis.com/v1/userinfo"

    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def authorization_url(self, state: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
        }
        return f"{self.auth_url}?{urlencode(params)}"

    def exchange_code(self, code: str) -> Dict[str, Any]:
        with httpx.Client(timeout=30) as client:
            resp = client.post(
                self.token_url,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri,
                },
            )
            resp.raise_for_status()
            return resp.json()

    def get_userinfo(self, access_token: str) -> Dict[str, Any]:
        with httpx.Client(timeout=30) as client:
            resp = client.get(self.userinfo_url, headers={"Authorization": f"Bearer {access_token}"})
            resp.raise_for_status()
            return resp.json()


oidc_provider = OIDCProvider()
