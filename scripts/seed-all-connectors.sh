#!/usr/bin/env bash
# Seed all 17 U.S. connectors on staging API with persistence.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_URL="${API_URL:-http://127.0.0.1:3001}"
CONNECTORS_DIR="$ROOT/packages/connectors"

CONNECTORS=(
  sec_edgar fec congress_gov sam_gov courtlistener usaspending ofac gleif
  lda_gov fara govinfo federal_register regulations_gov ecfr reginfo_oira irs_990 opencorporates
)

echo "==> Bootstrapping API modules"
for ep in bootstrap sources/bootstrap evidence/bootstrap entities/bootstrap reports/bootstrap monitor/bootstrap skills/bootstrap; do
  curl -sf -X POST "$API_URL/$ep" >/dev/null || true
done

echo "==> Running connectors against $API_URL"
cd "$CONNECTORS_DIR"
source "$ROOT/venv/bin/activate"
export API_URL
export PYTHONPATH="$CONNECTORS_DIR:${PYTHONPATH:-}"

for kind in "${CONNECTORS[@]}"; do
  echo "--- $kind"
  src_resp=$(curl -sf -X POST "$API_URL/sources/?name=$kind&kind=$kind" || echo '{}')
  src_id=$(echo "$src_resp" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null || echo "")
  if [ -z "$src_id" ]; then
    src_id=$(curl -sf "$API_URL/sources/health" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for s in d.get('per_source',[]):
    if s.get('kind')==sys.argv[1] or s.get('name')==sys.argv[1]:
        print(s['id']); break
" "$kind" 2>/dev/null || echo "1")
  fi
  run_resp=$(curl -sf -X POST "$API_URL/sources/${src_id}/runs")
  run_id=$(echo "$run_resp" | python3 -c "import sys,json; print(json.load(sys.stdin).get('run_id',''))")
  python -m runner.cli --connector "$kind" --source-id "$src_id" --run-id "$run_id" || {
    echo "WARN: $kind failed"
    curl -sf -X POST "$API_URL/sources/runs/${run_id}/status" \
      -H 'Content-Type: application/json' \
      -d '{"status":"error","error":"seed script failure"}' || true
  }
done

echo "==> Summary"
curl -sf "$API_URL/sources/health" | python3 -m json.tool
