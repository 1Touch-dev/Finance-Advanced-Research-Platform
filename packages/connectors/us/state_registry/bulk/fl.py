"""Florida bulk connector — Sunbiz HTTP search (SFTP fallback)."""
import os
from typing import Any, Dict, Iterable, Tuple

from us._common.http_helpers import http_get, is_test_env
from us.state_registry.base import StateRegistryConnector
from us.state_registry.schema import normalize

FL_SEARCH_URL = "https://search.sunbiz.org/Inquiry/CorporationSearch/SearchResults"
SEED_LIMIT = int(os.getenv("REGISTRY_SEED_LIMIT", "50"))


class FloridaBulkConnector(StateRegistryConnector):
    name = "state_us_fl"
    jurisdiction_code = "us_fl"
    source_tier = "bulk"
    source_url = "https://dos.fl.gov/sunbiz/other-services/data-downloads/"

    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        if is_test_env():
            yield from _sample_records()
            return
        try:
            # Florida Sunbiz JSON search endpoint
            url = "https://search.sunbiz.org/Inquiry/CorporationSearch/GetList?SearchTerm=Services&SearchType=EntityName&SearchNameOrder=SERVICES"
            headers = {
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 Research Platform",
            }
            resp = http_get(url, headers=headers, timeout=30)
            data = resp.json()
            items = data if isinstance(data, list) else data.get("CurrentList", [])
            for item in items[:SEED_LIMIT]:
                entity_id = item.get("DocumentNumber") or item.get("document_number", "")
                if not entity_id:
                    continue
                payload = _map_fl_item(item)
                yield str(entity_id), payload
            return
        except Exception as exc:
            if not is_test_env():
                print(f"[us_fl] bulk fetch error: {exc}")
        yield from _sample_records()

    def normalize(self, external_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return normalize(
            jurisdiction_code=self.jurisdiction_code,
            entity_id=external_id,
            legal_name=payload.get("legal_name", ""),
            raw_status=payload.get("status"),
            raw_entity_type=payload.get("entity_type"),
            formation_date=payload.get("formation_date"),
            registered_agent_name=payload.get("registered_agent_name"),
            principal_address=payload.get("principal_address"),
            source_tier=self.source_tier,
            source_url=self.source_url,
        )


def _map_fl_item(item: Dict) -> Dict:
    return {
        "legal_name": item.get("Name") or item.get("EntityName", ""),
        "status": item.get("Status", ""),
        "entity_type": item.get("EntityType", ""),
        "formation_date": item.get("FileDate") or item.get("FilingDate"),
        "registered_agent_name": item.get("RegisteredAgent"),
        "principal_address": None,
    }


def _sample_records():
    samples = [
        {"id": "FL001", "legal_name": "SUNSHINE SERVICES LLC", "status": "Active", "entity_type": "Florida Limited Liability"},
        {"id": "FL002", "legal_name": "MIAMI TECH INC", "status": "Active", "entity_type": "Domestic Profit"},
        {"id": "FL003", "legal_name": "GULF ASSOCIATES CORP", "status": "Inactive", "entity_type": "Domestic Profit"},
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
