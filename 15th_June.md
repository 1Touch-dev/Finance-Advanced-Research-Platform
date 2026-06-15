# 15th June 2026 — BizFile Live on Ubuntu 26.04, Full CA Waterfall Verified

**Purpose:** Daily handoff for James — end-to-end verification of all tiers except official CA SOS API (tier 1 pending). BizFile scrape confirmed working on current server.

**Prior docs:** `12th_June.md` (Cobalt + CA SOS application) · `PHASE2_COMPLETION_REPORT.md`

**Staging:** Web `http://184.72.123.188:3003` · API `:3001` · Admin `:3002`  
**Branch:** `feature/us-50-state-registry-api` · **PR #2**

---

## 1) Executive summary

| Area | Status (15 Jun, verified) |
|------|---------------------------|
| **Tier 1 — Official CA SOS API** | ⏳ **Pending** — `CA_SOS_API_KEY` empty; subscriptions submitted at calicodev.sos.ca.gov |
| **Tier 2 — BizFile scrape (free, official)** | ✅ **Working** — Playwright live scrape on this server; **150 CA entities** fetched (3 seed queries) |
| **Tier 3 — Cobalt Intelligence** | ⚠️ **Integrated, rate-limited** — API returns **429 Usage cap exceeded** (trial credits exhausted); code intact |
| **Tier 4 — Sample records** | ✅ **Working** — 4 embedded CA samples for tests/offline |
| **Staging registry** | ✅ **202 records**, 51 jurisdictions, API healthy |
| **Bulk states (NY, CO, FL, OR)** | ✅ Working — 50 records each on live fetch |
| **API states (WA, TX)** | ✅ Working — returns data via API + fallback |
| **BEA connector** | ✅ Working |
| **Tests** | ✅ **44/44 passed** (fast suite); **46/46** with orchestrator (full suite ~93s) |

---

## 2) CA data waterfall — verified 15 Jun

```
Priority (fetch_records in ca.py):

  1. Official CA SOS CBC API     ⏳  PENDING  — no subscription key yet
  2. BizFile Online scrape       ✅  WORKING  — Playwright headless on Ubuntu 26.04
  3. Cobalt Intelligence API     ⚠️  429 cap  — trial exhausted; DB has cached data
  4. Embedded sample records     ✅  WORKING  — tests / offline
```

### Live verification results (15 Jun)

| Check | Result |
|-------|--------|
| BizFile Playwright (`Apple`, 5 rows) | ✅ 5 records — e.g. `! ! ! APPLE IPAD & ANDROID TABLET TUTORING ! ! !` |
| BizFile full waterfall (no tier 1/3) | ✅ **150 records** across queries Apple, Google, Services |
| Cobalt live fetch | ❌ HTTP 429 — `"Usage cap exceeded"` |
| CA connector samples (test env) | ✅ 4 records |
| Staging `/registry/search?q=apple&state=us_ca` | ✅ 52+ matches from DB |

### Playwright fix on Ubuntu 26.04 (no new server needed)

BizFile was blocked earlier because Playwright did not recognise Ubuntu 26.04. Fixed with:

```bash
pip install playwright
PLAYWRIGHT_HOST_PLATFORM_OVERRIDE=ubuntu24.04-x64 playwright install chromium
playwright install-deps chromium
# or: ./scripts/setup-playwright.sh
```

Code auto-sets platform override via `ensure_playwright_platform()` in `us/_common/http_helpers.py`.

**Note:** Raw HTTP to BizFile API still returns 403 (Imperva WAF). Playwright browser path is required and is now operational.

---

## 3) Other connectors — verified 15 Jun

| Connector | Tier | Live fetch | Notes |
|-----------|------|------------|-------|
| `us_ny` bulk | A | ✅ 50 records | data.ny.gov |
| `us_co` bulk | A | ✅ 50 records | data.colorado.gov |
| `us_wa` API | B | ✅ 3 records | API 404 on some queries; fallback works |
| `us_tx` API | B | ✅ 3 records | API parse errors on some queries; fallback works |
| `us_ca` | B | ✅ 150 via BizFile | Tier 1 pending; tier 3 rate-limited |
| Scrape-tier (44 states) | D | ⚠️ Per-state | Playwright framework in place; generic SOS scrape varies; samples in test env |
| BEA | — | ✅ Live | `BEA_API_USER_ID` active |
| 17 federal connectors | — | ✅ | Regression tests pass |

### Staging API

```bash
curl http://127.0.0.1:3001/health
# → {"status":"ok"}

curl http://127.0.0.1:3001/registry/health
# → 51 jurisdictions, 202 records, tier_distribution: bulk=4, api=3, scrape=44

curl "http://127.0.0.1:3001/registry/search?q=apple&state=us_ca&limit=3"
# → live search over seeded DB records
```

---

## 4) Done today (15 Jun)

1. **BizFile Playwright scraper** — implemented in `ca.py` with DOM parsers, date normaliser, 4-tier waterfall
2. **Playwright on Ubuntu 26.04** — platform override + system deps; verified live on current server
3. **`scripts/setup-playwright.sh`** — one-time setup script for BizFile / scrape connectors
4. **`ensure_playwright_platform()`** — shared helper in `http_helpers.py`; used by `ca.py` and `scrape_generic.py`
5. **6 new BizFile unit tests** — parsers + graceful failure; all pass
6. **Full verification** — tier 2 confirmed independent of tier 1 and tier 3

---

## 5) Pending / blocked

| Item | Owner / action |
|------|----------------|
| **CA SOS API key (tier 1)** | Wait for CA SOS to approve `finance-platform-prod` subscription → paste Primary key into `CA_SOS_API_KEY` → `pm2 restart finance-api --update-env` |
| **Cobalt trial cap (tier 3)** | Trial exhausted (429). Options: upgrade plan with James, or rely on BizFile (tier 2) for CA + bulk/API states for others |
| **Re-seed CA from BizFile** | Optional — run `scripts/seed-state-registry.sh` for `us_ca` to replace Cobalt-sourced DB rows with official BizFile data |
| **OIDC / Google Workspace SSO** | Waiting on James for `OIDC_CLIENT_ID` / `OIDC_CLIENT_SECRET` |
| **E2E live re-run** | After tier 1 key active |

---

## 6) Keys status

| Key | Status | Notes |
|-----|--------|-------|
| `CA_SOS_API_KEY` | ⏳ Pending | calicodev.sos.ca.gov — subscriptions **Submitted** |
| `COBALT_API_KEY` | ⚠️ Set, capped | HTTP 429 — usage cap exceeded |
| `BEA_API_USER_ID` | ✅ Set | Live |
| 17 federal gov keys | ✅ Set | All working |
| `OIDC_CLIENT_ID/SECRET` | Empty | Optional |

---

## 7) Data strategy (aligned with James)

```
Free first, Cobalt last:

1. Tier A/B bulk/API     → NY, CO, FL, OR, WA, TX (+ CA official API when approved)
2. Tier 2 BizFile scrape → CA free official path — NOW LIVE on staging server
3. Tier D scrape         → 44 states (Playwright framework; per-state SOS varies)
4. Cobalt per-use        → Integrated but trial capped; not needed for CA while BizFile works
```

**CA is covered without tier 1 or tier 3** as long as Playwright deps remain installed.

---

## 8) Files changed (15 Jun)

| File | Change |
|------|--------|
| `packages/connectors/us/state_registry/api/ca.py` | BizFile scraper, 4-tier waterfall, Playwright error hints |
| `packages/connectors/us/_common/http_helpers.py` | `ensure_playwright_platform()` for Ubuntu 26.04 |
| `packages/connectors/us/state_registry/states/scrape_generic.py` | Use platform override before Playwright |
| `scripts/setup-playwright.sh` | One-time Playwright + Chromium setup |
| `tests/connectors/test_state_registry.py` | 6 BizFile parser tests |
| `15th_June.md` | This handoff |

---

## 9) Quick commands

```bash
# Verify BizFile tier 2 only (no CA key, no Cobalt)
cd /home/ubuntu/Finance-Advanced-Research-Platform
source venv/bin/activate
ENV=production COBALT_API_KEY= CA_SOS_API_KEY= \
  python3 -c "import sys; sys.path.insert(0,'packages/connectors'); \
  from us.state_registry.api.ca import _bizfile_fetch; \
  print(len(list(_bizfile_fetch(['Apple'], 10))))"
# → 10

# Run tests
pytest tests/connectors/test_state_registry.py -q

# Seed CA from BizFile (when ready)
# scripts/seed-state-registry.sh us_ca
```

---

*End of 15 June handoff*
