#!/usr/bin/env bash
# Seed all 51 U.S. state registry jurisdictions.
# Usage: bash scripts/seed-state-registry.sh [jurisdiction_code...]
# Examples:
#   bash scripts/seed-state-registry.sh            # all 51
#   bash scripts/seed-state-registry.sh us_ny us_co # specific states
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_URL="${API_URL:-http://127.0.0.1:3001}"
CONNECTORS_DIR="$ROOT/packages/connectors"

source "$ROOT/venv/bin/activate"
export PYTHONPATH="$CONNECTORS_DIR:${PYTHONPATH:-}"

# Load .env if present
if [ -f "$ROOT/.env" ]; then
  set -o allexport
  source "$ROOT/.env"
  set +o allexport
fi

echo "==> Bootstrapping registry API tables"
curl -sf -X POST "$API_URL/sources/bootstrap" >/dev/null || true

echo "==> Running state registry seeder"
python3 - <<'PYEOF'
import os, sys, json, time, requests

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__ if "__file__" in dir() else ".")), ".."))
sys.path.insert(0, os.path.join(ROOT, "packages", "connectors"))

API_URL = os.getenv("API_URL", "http://127.0.0.1:3001")
TOKEN = os.getenv("API_TOKEN", "")
HEADERS = {"Authorization": f"Bearer {TOKEN}"} if TOKEN else {}

from connectors.us.state_registry.registry import JURISDICTIONS
from connectors.us.state_registry.orchestrator import _load_connector

def get_or_create_source(kind: str) -> int:
    r = requests.get(f"{API_URL}/sources/health", timeout=10)
    per = r.json().get("per_source", [])
    match = next((s for s in per if s.get("kind") == kind or s.get("name") == kind), None)
    if match:
        return match["id"]
    r2 = requests.post(f"{API_URL}/sources/?name={kind}&kind={kind}", headers=HEADERS, timeout=10)
    return r2.json()["id"]

def create_run(source_id: int) -> int:
    r = requests.post(f"{API_URL}/sources/{source_id}/runs", headers=HEADERS, timeout=10)
    return r.json()["run_id"]

def persist_record(source_id: int, run_id: int, external_id: str, normalized: dict):
    payload = {
        "source_id": source_id,
        "run_id": run_id,
        "external_id": external_id,
        "normalized": normalized,
    }
    requests.post(f"{API_URL}/sources/records/upsert", json=payload, headers=HEADERS, timeout=10)

import sys
target_jurisdictions = sys.argv[1:] if len(sys.argv) > 1 else list(JURISDICTIONS.keys())

total_seen = 0
success = 0
partial = 0
failed = 0

print(f"==> Seeding {len(target_jurisdictions)} jurisdictions...")

for jcode in target_jurisdictions:
    meta = JURISDICTIONS.get(jcode)
    if not meta:
        print(f"  [{jcode}] SKIP: not in registry")
        continue

    kind = f"state_{jcode}"
    try:
        source_id = get_or_create_source(kind)
        run_id = create_run(source_id)
    except Exception as e:
        print(f"  [{jcode}] ERROR creating source/run: {e}")
        failed += 1
        continue

    seen = 0
    errors = 0
    try:
        connector = _load_connector(meta)
        for ext_id, payload in connector.fetch_records():
            try:
                normalized = connector.normalize(ext_id, payload)
                persist_record(source_id, run_id, ext_id, normalized)
                seen += 1
            except Exception as pe:
                errors += 1

        if seen > 0:
            status = "success" if errors == 0 else "partial"
            if errors == 0:
                success += 1
            else:
                partial += 1
        else:
            status = "no_records"
            partial += 1

        total_seen += seen
        print(f"  [{jcode}] {status}: {seen} records, {errors} errors", flush=True)

        # Update run status
        try:
            requests.post(
                f"{API_URL}/sources/{source_id}/runs/{run_id}",
                json={"status": "success" if errors == 0 else "partial", "metrics": {"seen": seen, "errors": errors}},
                headers=HEADERS,
                timeout=10,
            )
        except Exception:
            pass

    except Exception as e:
        print(f"  [{jcode}] ERROR: {e}", flush=True)
        failed += 1

print(f"\n{'='*60}")
print(f"Registry Seed Summary:")
print(f"  Total jurisdictions: {len(target_jurisdictions)}")
print(f"  Success: {success}")
print(f"  Partial: {partial}")
print(f"  Failed:  {failed}")
print(f"  Records: {total_seen}")
print(f"{'='*60}")
PYEOF

echo ""
echo "==> Registry health check:"
curl -sf "$API_URL/registry/health" | python3 -m json.tool || echo "(health endpoint may need API restart)"

echo ""
echo "==> Done. View jurisdictions at: $API_URL/registry/jurisdictions"
