import os
import requests
from typing import Dict, Any, List

class OpenAIClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = "https://api.openai.com/v1"

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def analyze_text(self, prompt: str, system_instruction: str = "You are an expert financial and intelligence research analyst.") -> str:
        """Call OpenAI completions to analyze a structured prompt."""
        if not self.is_configured():
            return "[OpenAI Client Error: OPENAI_API_KEY not configured. Simulated completion returned.]"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2
        }

        try:
            resp = requests.post(f"{self.base_url}/chat/completions", json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            return f"[Error calling OpenAI API: {str(e)}]"

openai_client = OpenAIClient()
