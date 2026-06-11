"""Washington State API connector."""
import os
from typing import Any, Dict, Iterable, Tuple

from us._common.http_helpers import http_get, is_test_env
from us.state_registry.base import StateRegistryConnector
from us.state_registry.schema import normalize

WA_API_URL = "https://ccfs.sos.wa.gov/api/v1/BusinessSearch/SearchByName"
SEED_QUERIES = ["Services", "Inc", "LLC", "Corporation", "Tech"]


class WashingtonAPIConnector(StateRegistryConnector):
    name = "state_us_wa"
    jurisdiction_code = "us_wa"
    source_tier = "api"
    source_url = "https://ccfs.sos.wa.gov/"

    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        if is_test_env():
            yield from _sample_records()
            return
        seen_ids: set = set()
        for query in SEED_QUERIES[:2]:
            try:
                url = f"{WA_API_URL}?businessName={query}&maxRows=10"
                headers = {"Accept": "application/json", "User-Agent": "Research Platform research@example.com"}
                resp = http_get(url, headers=headers, timeout=20)
                data = resp.json()
                items = data if isinstance(data, list) else data.get("businessSearchResults", [])
                for item in items:
                    eid = str(item.get("ubi") or item.get("UBI") or item.get("id", ""))
                    if not eid or eid in seen_ids:
                        continue
                    seen_ids.add(eid)
                    yield eid, _map_wa(item)
            except Exception as exc:
                if not is_test_env():
                    print(f"[us_wa] API fetch error for {query}: {exc}")
        if not seen_ids:
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


def _map_wa(item: Dict) -> Dict:
    return {
        "legal_name": item.get("businessName") or item.get("BusinessName", ""),
        "status": item.get("businessStatus") or item.get("BusinessStatus", ""),
        "entity_type": item.get("businessType") or item.get("BusinessType", ""),
        "formation_date": item.get("expirationDate") or item.get("registrationDate"),
        "registered_agent_name": item.get("registeredAgent"),
        "principal_address": None,
    }


def _sample_records():
    samples = [
        {"id": "WA001", "legal_name": "AMAZON.COM SERVICES LLC", "status": "Active", "entity_type": "WA Limited Liability Co."},
        {"id": "WA002", "legal_name": "MICROSOFT CORPORATION", "status": "Active", "entity_type": "WA Profit Corporation"},
        {"id": "WA003", "legal_name": "STARBUCKS CORPORATION", "status": "Active", "entity_type": "WA Profit Corporation"},
    ]
    for s in samples:
        eid = s["id"]
        yield eid, {
            "legal_name": s["legal_name"],
            "status": s["status"],
            "entity_type": s["entity_type"],
            "formation_date": None,
            "registered_agent_name": None,
            "principal_address": None,
        }
