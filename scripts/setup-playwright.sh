#!/usr/bin/env bash
# One-time Playwright setup for BizFile / scrape-tier connectors.
# Works on Ubuntu 26.04 via platform override (24.04 binaries are compatible).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -d venv ]]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

pip install -q playwright

export PLAYWRIGHT_HOST_PLATFORM_OVERRIDE="${PLAYWRIGHT_HOST_PLATFORM_OVERRIDE:-ubuntu24.04-x64}"
playwright install chromium
playwright install-deps chromium

echo "Playwright ready. Test CA BizFile scrape:"
echo "  python3 -c \"import sys; sys.path.insert(0,'packages/connectors'); from us.state_registry.api.ca import _bizfile_fetch; print(len(list(_bizfile_fetch(['Apple'], 5))))\""
