"""Cobalt Intelligence fallback connector — used only when COBALT_API_KEY is set."""
import os
from typing import Any, Dict, Iterable, Optional, Tuple

from us._common.http_helpers import http_get, is_test_env
from us.state_registry.base import StateRegistryConnector
from us.state_registry.schema import normalize

COBALT_BASE = "https://apigateway.cobaltintelligence.com/v1/search/"


def cobalt_search(state: str, query: str) -> list:
    """Call Cobalt SOS API and return list of raw result dicts."""
    api_key = os.getenv("COBALT_API_KEY", "")
    if not api_key:
        return []
    try:
        url = f"{COBALT_BASE}?state={state}&searchQuery={query}"
        headers = {"x-api-key": api_key, "Accept": "application/json"}
        resp = http_get(url, headers=headers, timeout=30)
        data = resp.json()
        return data if isinstance(data, list) else data.get("results", [])
    except Exception as exc:
        print(f"[cobalt] fetch error state={state} q={query}: {exc}")
        return []


class CobaltFallbackConnector(StateRegistryConnector):
    """Generic Cobalt fallback connector for a specific jurisdiction."""
    source_tier = "cobalt"

    def __init__(self, jurisdiction_code: str, state_abbrev: str, query: str = "Services", **kwargs):
        super().__init__(**kwargs)
        self.jurisdiction_code = jurisdiction_code
        self.state_abbrev = state_abbrev
        self._query = query
        self.name = f"state_{jurisdiction_code}_cobalt"
        self.source_url = COBALT_BASE

    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        if is_test_env():
            return
        if not os.getenv("COBALT_API_KEY"):
            return
        results = cobalt_search(self.state_abbrev, self._query)
        for item in results:
            eid = str(item.get("entityNumber") or item.get("id") or item.get("registrationNumber", ""))
            if not eid:
                continue
            yield eid, {
                "legal_name": item.get("entityName") or item.get("name", ""),
                "status": item.get("status", ""),
                "entity_type": item.get("entityType", ""),
                "formation_date": item.get("formationDate"),
                "registered_agent_name": item.get("registeredAgent"),
                "source_tier": "cobalt",
            }
