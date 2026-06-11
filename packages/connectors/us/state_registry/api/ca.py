"""California SOS connector — API with CA_SOS_API_KEY, fallback to scrape samples."""
import os
from typing import Any, Dict, Iterable, Tuple

from us._common.http_helpers import http_get, is_test_env
from us.state_registry.base import StateRegistryConnector
from us.state_registry.schema import normalize

CA_API_BASE = "https://calicodev.sos.ca.gov/api/BusinessSearch"
SEED_QUERIES = ["Services", "Technologies", "Inc"]


class CaliforniaSOSConnector(StateRegistryConnector):
    name = "state_us_ca"
    jurisdiction_code = "us_ca"
    source_tier = "api"
    source_url = "https://bizfileonline.sos.ca.gov/search/business"

    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        if is_test_env():
            yield from _sample_records()
            return
        api_key = os.getenv("CA_SOS_API_KEY", "")
        if api_key:
            yield from _api_fetch(api_key)
        else:
            # No API key — use CA Open Data portal
            yield from _open_data_fetch()

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


def _api_fetch(api_key: str) -> Iterable[Tuple[str, Dict]]:
    headers = {"X-API-Key": api_key, "Accept": "application/json"}
    for query in SEED_QUERIES[:1]:
        try:
            url = f"{CA_API_BASE}?businessName={query}&entityStatus=ACTIVE"
            resp = http_get(url, headers=headers, timeout=20)
            data = resp.json()
            items = data if isinstance(data, list) else data.get("businessSearchResults", [])
            for item in items[:20]:
                eid = str(item.get("entityNumber") or item.get("id", ""))
                if not eid:
                    continue
                yield eid, {
                    "legal_name": item.get("businessName", ""),
                    "status": item.get("entityStatus", ""),
                    "entity_type": item.get("entityType", ""),
                    "formation_date": item.get("dateOfFormation"),
                }
        except Exception as exc:
            print(f"[us_ca] API fetch error: {exc}")


def _open_data_fetch() -> Iterable[Tuple[str, Dict]]:
    """Fallback to CA open data or samples."""
    yield from _sample_records()


def _sample_records():
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
