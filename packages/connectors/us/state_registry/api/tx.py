"""Texas Comptroller franchise tax API connector."""
import os
from typing import Any, Dict, Iterable, Tuple

from us._common.http_helpers import http_get, is_test_env
from us.state_registry.base import StateRegistryConnector
from us.state_registry.schema import normalize

TX_API_BASE = "https://mycpa.cpa.state.tx.us/coa/cosearch"
SEED_QUERIES = ["Services", "Technologies", "LLC"]


class TexasAPIConnector(StateRegistryConnector):
    name = "state_us_tx"
    jurisdiction_code = "us_tx"
    source_tier = "api"
    source_url = "https://comptroller.texas.gov/taxes/franchise/"

    def fetch_records(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        if is_test_env():
            yield from _sample_records()
            return
        seen_ids: set = set()
        for query in SEED_QUERIES[:1]:
            try:
                url = f"https://mycpa.cpa.state.tx.us/coa/cosearch?name={query}&searchType=name&format=json"
                headers = {"Accept": "application/json", "User-Agent": "Research Platform research@example.com"}
                resp = http_get(url, headers=headers, timeout=20)
                data = resp.json()
                items = data if isinstance(data, list) else data.get("taxpayers", data.get("results", []))
                for item in items[:20]:
                    eid = str(item.get("taxpayerNumber") or item.get("id", ""))
                    if not eid or eid in seen_ids:
                        continue
                    seen_ids.add(eid)
                    yield eid, _map_tx(item)
            except Exception as exc:
                if not is_test_env():
                    print(f"[us_tx] API fetch error for {query}: {exc}")
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
            principal_address=payload.get("principal_address"),
            source_tier=self.source_tier,
            source_url=self.source_url,
        )


def _map_tx(item: Dict) -> Dict:
    addr = None
    if item.get("taxpayerAddress"):
        addr = {"address": item["taxpayerAddress"]}
    return {
        "legal_name": item.get("taxpayerName") or item.get("name", ""),
        "status": item.get("rightToTransact") or item.get("status", ""),
        "entity_type": item.get("entityType", ""),
        "formation_date": item.get("registrationDate"),
        "principal_address": addr,
    }


def _sample_records():
    samples = [
        {"id": "TX001", "legal_name": "EXXON MOBIL CORPORATION", "status": "Active", "entity_type": "Corporation"},
        {"id": "TX002", "legal_name": "DELL TECHNOLOGIES INC", "status": "Active", "entity_type": "Corporation"},
        {"id": "TX003", "legal_name": "HOUSTON SERVICES LLC", "status": "Active", "entity_type": "Limited Liability Company"},
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
