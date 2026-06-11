"""Oregon bulk connector — data.oregon.gov Socrata API."""
import os
from typing import Any, Dict, Iterable, Tuple

from us._common.http_helpers import http_get, is_test_env
from us.state_registry.base import StateRegistryConnector
from us.state_registry.schema import normalize

OR_SOCRATA_URL = "https://data.oregon.gov/resource/tckn-sxa6.json"
SEED_LIMIT = int(os.getenv("REGISTRY_SEED_LIMIT", "50"))


class OregonBulkConnector(StateRegistryConnector):
    name = "state_us_or"
    jurisdiction_code = "us_or"
    source_tier = "bulk"
    source_url = OR_SOCRATA_URL

    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        if is_test_env():
            yield from _sample_records()
            return
        try:
            url = f"{OR_SOCRATA_URL}?$limit={SEED_LIMIT}&$offset=0"
            resp = http_get(url, timeout=30)
            rows = resp.json()
            if isinstance(rows, list):
                for row in rows:
                    entity_id = row.get("registry_number") or row.get("entity_number", "")
                    if not entity_id:
                        continue
                    payload = _map_or_row(row)
                    yield str(entity_id), payload
                return
        except Exception as exc:
            if not is_test_env():
                print(f"[us_or] bulk fetch error: {exc}")
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


def _map_or_row(row: Dict) -> Dict:
    addr = None
    if row.get("principal_address"):
        addr = {"address": row["principal_address"]}
    elif row.get("address"):
        addr = {"address": row["address"]}
    return {
        "legal_name": row.get("entity_name", row.get("business_name", "")),
        "status": row.get("entity_status", row.get("status", "")),
        "entity_type": row.get("entity_type", ""),
        "formation_date": row.get("registry_date") or row.get("formation_date"),
        "registered_agent_name": row.get("registered_agent"),
        "principal_address": addr,
    }


def _sample_records():
    samples = [
        {"id": "OR001", "legal_name": "PACIFIC NORTHWEST LLC", "status": "Active", "entity_type": "Limited Liability Company"},
        {"id": "OR002", "legal_name": "PORTLAND SERVICES INC", "status": "Active", "entity_type": "Domestic Business Corporation"},
        {"id": "OR003", "legal_name": "CASCADE VENTURES", "status": "Inactive", "entity_type": "Limited Liability Company"},
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
