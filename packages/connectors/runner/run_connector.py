import os
import json
import requests
from typing import Dict, Any
from connectors.sdk import BaseConnector

API_URL = os.getenv("API_URL", "http://localhost:3001")

def persist_raw_and_evidence(token: str, source_id: int, run_id: int, item: Dict[str, Any]):
    # Persist raw document as JSON bytes
    data = json.dumps(item).encode("utf-8")
    files = {"file": (item.get("external_id","item.json"), data, "application/json")}
    resp = requests.post(f"{API_URL}/evidence/raw", files=files, data={
        "source_id": str(source_id),
        "source_run_id": str(run_id),
    }, headers={"Authorization": f"Bearer {token}"} if token else None)
    resp.raise_for_status()
    doc = resp.json()
    # Create simple EvidenceRef
    ref = requests.post(f"{API_URL}/evidence/refs", data={
        "raw_document_id": str(doc["id"]),
        "excerpt": str(item)[:280]
    }, headers={"Authorization": f"Bearer {token}"} if token else None)
    ref.raise_for_status()
    return {"doc": doc, "ref": ref.json()}


def run(connector: BaseConnector, token: str | None, source_id: int, run_id: int) -> Dict[str, Any]:
    metrics = connector.run()
    # For a real run, you would pass each fetched record through persist_raw_and_evidence
    requests.post(f"{API_URL}/sources/runs/{run_id}/status", json={
        "status": "success",
        "metrics": metrics
    }, headers={"Authorization": f"Bearer {token}"} if token else None).raise_for_status()
    return metrics
