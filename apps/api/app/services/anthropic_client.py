import json
import os
from typing import Any, Dict, Optional

import httpx


class AnthropicClient:
    def __init__(self):
        self.base_url = "https://api.anthropic.com/v1/messages"

    @property
    def api_key(self) -> str:
        return os.getenv("ANTHROPIC_API_KEY", "").strip()

    @property
    def model(self) -> str:
        return os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def analyze_text(self, prompt: str, system: str = "", max_tokens: int = 4096) -> Dict[str, Any]:
        if not self.is_configured():
            return {"text": f"Simulated Claude response (ANTHROPIC_API_KEY not set): {prompt[:200]}", "tokens": 0}
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        body = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system or "You are an expert financial analyst.",
            "messages": [{"role": "user", "content": prompt}],
        }
        with httpx.Client(timeout=120) as client:
            resp = client.post(self.base_url, headers=headers, json=body)
        if resp.status_code >= 400:
            detail = resp.text[:500]
            try:
                detail = resp.json().get("error", {}).get("message", detail)
            except Exception:
                pass
            raise RuntimeError(f"Anthropic API error ({resp.status_code}): {detail}")
        data = resp.json()
        text = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")
        usage = data.get("usage", {})
        return {
            "text": text,
            "tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "model": self.model,
        }


anthropic_client = AnthropicClient()
