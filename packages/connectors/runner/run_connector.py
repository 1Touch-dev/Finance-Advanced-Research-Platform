import json
import os
from typing import Any, Dict

import requests
from connectors.sdk import BaseConnector

API_URL = os.getenv("API_URL", os.getenv("NEXT_PUBLIC_API_URL", "http://localhost:3001"))


def _headers(token: str | None) -> dict:
    return {"Authorization": f"Bearer {token}"} if token else {}


def persist_raw_and_evidence(
    token: str | None,
    source_id: int,
    run_id: int,
    *,
    external_id: str,
    raw: Dict[str, Any],
    excerpt: str = "",
    normalized: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    data = json.dumps(raw, default=str).encode("utf-8")
    files = {"file": (f"{external_id}.json", data, "application/json")}
    resp = requests.post(
        f"{API_URL}/evidence/raw",
        files=files,
        data={
            "source_id": str(source_id),
            "source_run_id": str(run_id),
            "source_native_id": external_id,
        },
        headers=_headers(token),
        timeout=60,
    )
    resp.raise_for_status()
    doc = resp.json()
    ref = requests.post(
        f"{API_URL}/evidence/refs",
        data={
            "raw_document_id": str(doc["id"]),
            "excerpt": excerpt or str(raw)[:500],
        },
        headers=_headers(token),
        timeout=30,
    )
    ref.raise_for_status()
    if normalized:
        requests.post(
            f"{API_URL}/sources/records",
            json={
                "source_id": source_id,
                "run_id": run_id,
                "external_id": external_id,
                "normalized": normalized,
                "evidence_ref_id": ref.json().get("id"),
            },
            headers=_headers(token),
            timeout=30,
        )
    return {"doc": doc, "ref": ref.json()}


def run(connector: BaseConnector, token: str | None, source_id: int, run_id: int) -> Dict[str, Any]:
    dlq = []

    def persist_fn(**kwargs):
        try:
            persist_raw_and_evidence(token, source_id, run_id, **kwargs)
        except Exception as e:
            dlq.append({"external_id": kwargs.get("external_id"), "error": str(e)})
            raise

    try:
        metrics = connector.run(persist_fn=persist_fn)
        status = "success" if metrics.get("errors", 0) == 0 else "partial"
    except Exception as e:
        metrics = {"errors": 1, "error": str(e)}
        status = "error"

    if dlq:
        requests.post(
            f"{API_URL}/sources/dlq",
            json={"run_id": run_id, "items": dlq},
            headers=_headers(token),
            timeout=30,
        )

    requests.post(
        f"{API_URL}/sources/runs/{run_id}/status",
        json={"status": status, "metrics": metrics},
        headers=_headers(token),
        timeout=30,
    ).raise_for_status()
    return metrics
