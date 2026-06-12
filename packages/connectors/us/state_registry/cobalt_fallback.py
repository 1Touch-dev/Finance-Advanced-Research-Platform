"""Cobalt Intelligence fallback connector — used only when COBALT_API_KEY is set.

API docs: https://apigateway.cobaltintelligence.com/v1/search
Header: x-api-key
Params: searchQuery, state (full name e.g. Georgia), optional liveData=false for cache
"""
import os
from typing import Any, Dict, Iterable, List, Optional, Tuple

from us._common.http_helpers import http_get, is_test_env
from us.state_registry.base import StateRegistryConnector
from us.state_registry.registry import JURISDICTIONS
from us.state_registry.schema import normalize

COBALT_BASE = "https://apigateway.cobaltintelligence.com/v1/search"


def _api_key() -> str:
    return os.getenv("COBALT_API_KEY", "").strip().lstrip("@")


def _state_name(state_abbrev: str) -> str:
    """Map DE / us_de → Delaware for Cobalt API."""
    code = state_abbrev.lower().replace("us_", "")
    jcode = f"us_{code}"
    if jcode in JURISDICTIONS:
        return JURISDICTIONS[jcode]["name"]
    return state_abbrev


def _parse_cobalt_item(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    eid = str(item.get("sosId") or item.get("entityNumber") or item.get("id") or "")
    name = item.get("title") or item.get("entityName") or item.get("name") or ""
    if not eid and not name:
        return None
    formation = None
    for h in item.get("history") or []:
        if "formation" in (h.get("name") or "").lower():
            formation = h.get("date")
            break
    return {
        "legal_name": name,
        "status": item.get("normalizedStatus") or item.get("status", ""),
        "entity_type": item.get("entityType", ""),
        "formation_date": formation,
        "registered_agent_name": item.get("agentName"),
        "sos_id": eid,
        "state_of_formation": item.get("stateOfFormation"),
        "source_tier": "cobalt",
        "raw": item,
    }


def cobalt_search(state_abbrev: str, query: str, *, live: Optional[bool] = None) -> List[Dict[str, Any]]:
    """Call Cobalt SOS API and return parsed result dicts."""
    api_key = _api_key()
    if not api_key:
        return []

    if live is None:
        live = os.getenv("COBALT_LIVE_DATA", "false").lower() in ("1", "true", "yes")

    params: Dict[str, str] = {
        "searchQuery": query,
        "state": _state_name(state_abbrev),
        "liveData": "true" if live else "false",
    }

    try:
        resp = http_get(COBALT_BASE, params=params, headers={"x-api-key": api_key, "Accept": "application/json"}, timeout=45)
        data = resp.json()
        if isinstance(data, list):
            raw_items = data
        else:
            raw_items = data.get("results") or data.get("data") or []
        parsed = []
        for item in raw_items:
            row = _parse_cobalt_item(item)
            if row:
                parsed.append(row)
        return parsed
    except Exception as exc:
        print(f"[cobalt] fetch error state={state_abbrev} q={query}: {exc}")
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
        if not _api_key():
            return
        for item in cobalt_search(self.state_abbrev, self._query):
            eid = item.get("sos_id") or item.get("legal_name", "")[:32]
            if not eid:
                continue
            yield str(eid), item

    def normalize(self, external_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return normalize(
            jurisdiction_code=self.jurisdiction_code,
            entity_id=external_id,
            legal_name=payload.get("legal_name", ""),
            raw_status=payload.get("status"),
            raw_entity_type=payload.get("entity_type"),
            formation_date=payload.get("formation_date"),
            registered_agent_name=payload.get("registered_agent_name"),
            source_tier="cobalt",
            source_url=self.source_url,
        )

