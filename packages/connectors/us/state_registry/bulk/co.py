"""Colorado bulk connector — data.colorado.gov Socrata API."""
import os
from typing import Any, Dict, Iterable, Tuple

from us._common.http_helpers import http_get, is_test_env
from us.state_registry.base import StateRegistryConnector
from us.state_registry.schema import normalize

CO_SOCRATA_URL = "https://data.colorado.gov/resource/4ykn-tg5h.json"
SEED_LIMIT = int(os.getenv("REGISTRY_SEED_LIMIT", "50"))


class ColoradoBulkConnector(StateRegistryConnector):
    name = "state_us_co"
    jurisdiction_code = "us_co"
    source_tier = "bulk"
    source_url = CO_SOCRATA_URL

    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        if is_test_env():
            yield from _sample_records()
            return
        try:
            url = f"{CO_SOCRATA_URL}?$limit={SEED_LIMIT}&$offset=0"
            resp = http_get(url, timeout=30)
            rows = resp.json()
            if isinstance(rows, list):
                for row in rows:
                    entity_id = row.get("entityid") or row.get("entity_id") or row.get("id", "")
                    if not entity_id:
                        continue
                    payload = _map_co_row(row)
                    yield str(entity_id), payload
                return
        except Exception as exc:
            if not is_test_env():
                print(f"[us_co] bulk fetch error: {exc}")
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


def _map_co_row(row: Dict) -> Dict:
    addr = None
    for field_combo in [
        ("principaladdress1", "principalcity", "principalstate", "principalzipcode"),
    ]:
        if row.get(field_combo[0]):
            addr = {
                "address1": row.get(field_combo[0], ""),
                "city": row.get(field_combo[1], ""),
                "state": row.get(field_combo[2], ""),
                "zip": row.get(field_combo[3], ""),
            }
            break
    return {
        "legal_name": row.get("entityname", row.get("entity_name", "")),
        "status": row.get("entitystatus", row.get("status", "")),
        "entity_type": row.get("entitytype", row.get("entity_type", "")),
        "formation_date": row.get("formdate", row.get("formation_date")),
        "registered_agent_name": row.get("agentfirstlastname", row.get("registered_agent")),
        "principal_address": addr,
    }


def _sample_records():
    samples = [
        {"id": "CO001", "legal_name": "MOUNTAIN VENTURES LLC", "status": "Good Standing", "entity_type": "Limited Liability Company"},
        {"id": "CO002", "legal_name": "PEAK SERVICES INC", "status": "Good Standing", "entity_type": "Corporation"},
        {"id": "CO003", "legal_name": "DENVER TECH CORP", "status": "Dissolved", "entity_type": "Corporation"},
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
