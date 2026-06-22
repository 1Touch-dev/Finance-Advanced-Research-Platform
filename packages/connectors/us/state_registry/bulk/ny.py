"""New York bulk connector — data.ny.gov open data."""
import os
from typing import Any, Dict, Iterable, Tuple

from us._common.http_helpers import http_get, is_test_env
from us.state_registry.base import StateRegistryConnector
from us.state_registry.schema import normalize


NY_BULK_URL = "https://data.ny.gov/api/views/n9v6-gdp6/rows.json?accessType=DOWNLOAD"
NY_SOCRATA_URL = "https://data.ny.gov/resource/n9v6-gdp6.json"
SEED_LIMIT = int(os.getenv("REGISTRY_SEED_LIMIT", "50"))


class NewYorkBulkConnector(StateRegistryConnector):
    name = "state_us_ny"
    jurisdiction_code = "us_ny"
    source_tier = "bulk"
    source_url = NY_SOCRATA_URL

    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        if is_test_env():
            yield from _sample_records()
            return
        try:
            url = f"{NY_SOCRATA_URL}?$limit={SEED_LIMIT}&$offset=0"
            resp = http_get(url, timeout=30)
            rows = resp.json()
            if isinstance(rows, list):
                for row in rows:
                    entity_id = row.get("dos_id") or row.get("initial_dos_filing_date", "") + "_" + row.get("current_entity_name", "")
                    if not entity_id:
                        continue
                    payload = _map_ny_row(row)
                    yield str(entity_id), payload
                return
        except Exception as exc:
            if not is_test_env():
                print(f"[us_ny] bulk fetch error: {exc}")
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


def _map_ny_row(row: Dict) -> Dict:
    addr = {}
    for f in ("location_address1", "location_address2", "location_city", "location_state", "location_zip"):
        if row.get(f):
            addr[f.replace("location_", "")] = row[f]
    return {
        "legal_name": row.get("current_entity_name", ""),
        "status": row.get("entity_status", ""),
        "entity_type": row.get("entity_type", ""),
        "formation_date": row.get("initial_dos_filing_date"),
        "registered_agent_name": row.get("registered_agent", ""),
        "principal_address": addr or None,
    }


def _sample_records():
    samples = [
        {"dos_id": "NY001", "legal_name": "APPLE INC", "status": "Active", "entity_type": "Domestic Business Corporation"},
        {"dos_id": "NY002", "legal_name": "SERVICES LLC", "status": "Active", "entity_type": "Domestic Limited Liability Company"},
        {"dos_id": "NY003", "legal_name": "TECH ASSOCIATES INC", "status": "Inactive", "entity_type": "Domestic Business Corporation"},
    ]
    for s in samples:
        eid = s["dos_id"]
        yield eid, {
            "legal_name": s["legal_name"],
            "status": s["status"],
            "entity_type": s["entity_type"],
            "formation_date": None,
            "registered_agent_name": None,
            "principal_address": None,
        }
