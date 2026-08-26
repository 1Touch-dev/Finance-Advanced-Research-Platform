import json
import logging
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

try:
    from app.core.tracing import trace_op
except ImportError:
    from contextlib import contextmanager

    @contextmanager
    def trace_op(op, description=None, data=None):
        yield None


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

    def analyze_text(self, prompt: str, system: str = "", max_tokens: int = 4096) -> Optional[Dict[str, Any]]:
        if not self.is_configured():
            return None
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
        with trace_op("llm.anthropic", description=f"Claude {self.model}",
                      data={"model": self.model, "max_tokens": max_tokens}):
            with httpx.Client(timeout=120) as client:
                resp = client.post(self.base_url, headers=headers, json=body)
        if resp.status_code >= 400:
            detail = resp.text[:500]
            try:
                detail = resp.json().get("error", {}).get("message", detail)
            except Exception as e:
                logger.debug("Failed to parse Anthropic API error response: %s", e)
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
