"""California SOS connector — CBC APIs Prod v1 (calico.sos.ca.gov)."""
import os
from typing import Any, Dict, Iterable, List, Optional, Tuple

from us._common.http_helpers import http_get, is_test_env
from us.state_registry.base import StateRegistryConnector
from us.state_registry.cobalt_fallback import cobalt_search
from us.state_registry.schema import normalize

CA_API_BASE = "https://calico.sos.ca.gov/cbc/v1/api"
SEED_QUERIES = ["Apple", "Google", "Services", "Technologies", "Inc"]


class CaliforniaSOSConnector(StateRegistryConnector):
    name = "state_us_ca"
    jurisdiction_code = "us_ca"
    source_tier = "api"
    source_url = "https://bizfileonline.sos.ca.gov/search/business"

    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        if is_test_env():
            yield from _sample_records()
            return
        api_key = os.getenv("CA_SOS_API_KEY", "").strip()
        if api_key:
            records = list(_api_fetch(api_key))
            if records:
                yield from records
                return
        cobalt_records = list(_cobalt_fetch())
        if cobalt_records:
            yield from cobalt_records
            return
        yield from _sample_records()

    def normalize(self, external_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return normalize(
            jurisdiction_code=self.jurisdiction_code,
            entity_id=external_id,
            legal_name=payload.get("legal_name", ""),
            raw_status=payload.get("status"),
            raw_entity_type=payload.get("entity_type"),
            formation_date=payload.get("formation_date"),
            source_tier=self.source_tier,
            source_url=self.source_url,
        )


def _api_headers(api_key: str) -> Dict[str, str]:
    return {
        "Ocp-Apim-Subscription-Key": api_key,
        "Accept": "application/json",
    }


def _map_entity(item: Dict[str, Any]) -> Optional[Tuple[str, Dict[str, Any]]]:
    eid = str(item.get("EntityID") or item.get("entityID") or "")
    name = item.get("EntityName") or item.get("entityName") or ""
    if not eid and not name:
        return None
    return eid or name, {
        "legal_name": name,
        "status": item.get("StatusDescription") or item.get("statusDescription") or "",
        "entity_type": item.get("EntityType") or item.get("entityType") or "",
        "formation_date": item.get("FilingDate") or item.get("filingDate"),
        "registered_agent_name": item.get("AgentName") or item.get("agentName"),
        "jurisdiction": item.get("Jurisdiction") or item.get("jurisdiction"),
    }


def _parse_keyword_response(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("EntityData") or data.get("entityData") or []
    return []


def _api_fetch(api_key: str) -> Iterable[Tuple[str, Dict[str, Any]]]:
    seen: set = set()
    for query in SEED_QUERIES[:3]:
        try:
            url = f"{CA_API_BASE}/BusinessEntityKeywordSearch"
            resp = http_get(
                url,
                params={"search-term": query},
                headers=_api_headers(api_key),
                timeout=30,
            )
            for item in _parse_keyword_response(resp.json()):
                mapped = _map_entity(item)
                if not mapped:
                    continue
                eid, payload = mapped
                if eid in seen:
                    continue
                seen.add(eid)
                yield eid, payload
        except Exception as exc:
            print(f"[us_ca] keyword search error ({query!r}): {exc}")

    if seen:
        return

    # Fallback: known public entity number (Apple Inc in CA)
    try:
        url = f"{CA_API_BASE}/BusinessEntityDetails"
        resp = http_get(
            url,
            params={"entity-number": "0806597"},
            headers=_api_headers(api_key),
            timeout=30,
        )
        data = resp.json()
        if isinstance(data, dict) and data.get("EntityID"):
            mapped = _map_entity(data)
            if mapped:
                eid, payload = mapped
                seen.add(eid)
                yield eid, payload
    except Exception as exc:
        print(f"[us_ca] entity details error: {exc}")

    if not seen:
        return


def _cobalt_fetch() -> Iterable[Tuple[str, Dict[str, Any]]]:
    """Interim live CA data while CA SOS subscription is pending approval."""
    seen: set = set()
    for query in SEED_QUERIES[:2]:
        for row in cobalt_search("ca", query):
            eid = str(row.get("sos_id") or row.get("legal_name") or "")
            if not eid or eid in seen:
                continue
            seen.add(eid)
            yield eid, {
                "legal_name": row.get("legal_name", ""),
                "status": row.get("status", ""),
                "entity_type": row.get("entity_type", ""),
                "formation_date": row.get("formation_date"),
                "registered_agent_name": row.get("registered_agent_name"),
            }


def _sample_records() -> Iterable[Tuple[str, Dict[str, Any]]]:
    samples = [
        {"id": "CA001", "legal_name": "APPLE INC", "status": "Active", "entity_type": "Domestic Stock Corporation"},
        {"id": "CA002", "legal_name": "GOOGLE LLC", "status": "Active", "entity_type": "Foreign Limited Liability Company"},
        {"id": "CA003", "legal_name": "NETFLIX INC", "status": "Active", "entity_type": "Domestic Stock Corporation"},
        {"id": "CA004", "legal_name": "SILICON VALLEY SERVICES LLC", "status": "Active", "entity_type": "Domestic Limited Liability Company"},
    ]
    for s in samples:
        eid = s["id"]
        yield eid, {
            "legal_name": s["legal_name"],
            "status": s["status"],
            "entity_type": s["entity_type"],
            "formation_date": None,
        }
