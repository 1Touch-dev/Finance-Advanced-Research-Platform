# Live E2E System Test — Full Agent Prompt

**Copy everything below the line into a new Cursor Agent chat. Do not summarize or shorten it.**

---

## YOUR MISSION

You are an autonomous QA + full-stack engineer agent. Perform a **live end-to-end test** of the Enterprise Intelligence & Investment Research Platform on staging using **Cursor Browser MCP** (`cursor-ide-browser`), fix any issues you find, retest, update documentation, and **commit + push** to GitHub.

Produce an **authentic, evidence-based report** — not marketing copy. Distinguish **FULLY working** vs **PARTIALLY working** vs **BROKEN** for every surface.

**Do not claim done until:**
1. Every test case in § TEST MATRIX has a pass/fail/partial result with evidence (screenshot or API response)
2. All fixable bugs are fixed and retested
3. `pytest tests/ -q` passes
4. Docs updated with **today's date** and real numbers from staging
5. Changes committed and pushed

---

## REPOSITORY CONTEXT

| Item | Value |
|------|-------|
| Workspace | `/home/ubuntu/Finance-Advanced-Research-Platform` |
| Current branch | `feature/us-50-state-registry-api` |
| Remote | `https://github.com/1Touch-dev/Finance-Advanced-Research-Platform.git` |
| Open PR | https://github.com/1Touch-dev/Finance-Advanced-Research-Platform/pull/2 |
| Staging | Web `http://184.72.123.188:3003` · API `http://184.72.123.188:3001` · Admin `http://184.72.123.188:3002` |
| PM2 | `finance-api`, `finance-web`, `finance-admin` |
| Credentials | `.env` (gitignored) — load locally; **never commit secrets** |

### Known baseline (verify fresh — do not trust blindly)

| Area | Expected today |
|------|----------------|
| Federal gov connectors | 17/17 last run success |
| BEA connector | Live — ~429 records, `BEA_API_USER_ID` activated |
| Registry jurisdictions | 51/51 registered, ~110 records |
| Live state data (real) | ~7 states: NY, CO, FL, OR (bulk), WA, TX (api), CA partial |
| Scrape-tier states | 44 + DC — **sample data only** until `COBALT_API_KEY` |
| Missing keys (James) | `COBALT_API_KEY`, `CA_SOS_API_KEY` |
| Tests | 72 pytest passing |
| Uncommitted work | `economics.js`, BEA connector fixes, `/sources/records` API, `seed-all-connectors.sh` includes `bea` |

---

## BROWSER MCP WORKFLOW (MANDATORY)

Use `cursor-ide-browser` for all UI tests:

1. `browser_navigate` to target URL
2. `browser_snapshot` — read page structure before interacting
3. `browser_lock` before multi-step interactions; `browser_unlock` when done
4. `browser_click`, `browser_type`, `browser_fill` for forms
5. `browser_take_screenshot` for evidence on pass/fail
6. Use `browser_cdp` only if dedicated tools fail

**Order:** navigate → lock → interact → snapshot/screenshot → unlock

Also verify APIs via `curl` or Shell alongside browser tests.

---

## TEST MATRIX

For each row: **Status** = `FULL` | `PARTIAL` | `FAIL` | `SKIP`  
Record: URL tested, what you did, what you saw, screenshot filename if any.

### A. Infrastructure & ops

| ID | Test | How | FULL means |
|----|------|-----|------------|
| A1 | API health | `GET /health` | 200 `{"status":"ok"}` |
| A2 | PM2 processes | `pm2 list` | api, web, admin all `online` |
| A3 | Source health | `GET /sources/health` | 17 gov + bea success; state sources have records |
| A4 | Registry health | `GET /registry/health` | 51 jurisdictions, tier counts |
| A5 | Pytest suite | `pytest tests/ -q` | All pass |
| A6 | Admin dashboard | Browser `:3002` | Loads, shows source counts |

### B. Web UI — navigation & shell

| ID | Page | URL | FULL means | Known partial |
|----|------|-----|------------|---------------|
| B1 | Home | `/` | Cards load, nav works | May not link Registry/Economics |
| B2 | Layout nav | All nav links | Home, Search, Graph, Merge, Registry, Economics, Stock, Skills, Alerts | — |
| B3 | Footer API URL | Any page | Shows correct `:3001` | — |

### C. Web UI — feature pages (browser + API)

| ID | Page | URL | Test steps | FULL means | Known partial |
|----|------|-----|------------|------------|---------------|
| C1 | **Registry** | `/registry` | Load health panel; search `corp`; filter NY | Results return, jurisdictions=51 | 44 states = sample data |
| C2 | **Economics** | `/economics` | Check tier=live, record count, table rows | BEA live data displays | — |
| C3 | **Search** | `/search` | Query `apple`, `microsoft` | Returns entities | Only 5 demo entities |
| C4 | **Graph** | `/graph` | Entity ID `1`, Expand, export PNG | Interactive graph renders | Demo relationships only |
| C5 | **Stock** | `/stock` | Ticker `AAPL`, Analyze | JSON with DCF, technicals, gov context | Quote price may be static mock |
| C6 | **Skills** | `/skills` | Check Anthropic status; run `dcf` skill | Claude responds (not simulated) | — |
| C7 | **Alerts** | `/alerts` | Load events; Run Scan + Deliver | Events list, scan returns 200 | — |
| C8 | **Entity profile** | `/entities/1` | Profile, relationships, evidence, timeline | All sections load JSON | Demo data only |
| C9 | **Portfolio** | `/portfolio/1` | Exposure breakdown visible | AAPL + MSFT weights shown | Demo portfolio |
| C10 | **Merge** | `/entities/merge` | Page loads, candidates API | No crash; empty list OK | 0 candidates expected |
| C11 | **Review** | `/review/1` | Report loads, try export Markdown | Demo report + export works | 1 demo report only |

### D. API endpoints (curl — verify web backends)

| ID | Endpoint | FULL means |
|----|----------|------------|
| D1 | `GET /search/?q=apple` | entities returned |
| D2 | `GET /graph/export?entity_id=1&depth=2` | nodes + edges |
| D3 | `GET /finance/analyze_stock?ticker=AAPL` | quote, technicals, live_sources |
| D4 | `GET /skills/status` | anthropic.configured=true |
| D5 | `POST /skills/run?name=dcf&version=v1` | structured response |
| D6 | `GET /monitor/events?limit=10` | array (may be empty) |
| D7 | `POST /monitor/scan` | 200 |
| D8 | `GET /registry/search?q=services&limit=5` | results with jurisdiction |
| D9 | `GET /registry/jurisdictions` | count=51 |
| D10 | `GET /sources/records?kind=bea&limit=5` | total≥400, source_tier=live |
| D11 | `GET /reports/1` | demo report JSON |
| D12 | `GET /monitor/portfolios/1/exposure` | breakdown with tickers |
| D13 | `GET /entities/merge/candidates` | 200 (array) |
| D14 | `POST /demo/seed` | re-seeds demo entities |

### E. Connectors & data integrity

| ID | Test | FULL means |
|----|------|------------|
| E1 | Re-run BEA connector | Live rows ingested, not samples |
| E2 | `bash scripts/seed-all-connectors.sh` | 17 gov + bea complete without fatal errors |
| E3 | `bash scripts/seed-state-registry.sh` | 51 jurisdictions get records |
| E4 | DB counts | `source_record_meta` ≥800, `raw_documents` ≥700 |
| E5 | Evidence pipeline | Connector run creates evidence_refs |

### F. Known limitations (mark PARTIAL — do not fail)

| Item | Why partial |
|------|-------------|
| 44 scrape-tier states | No `COBALT_API_KEY` — sample data only |
| California live | No `CA_SOS_API_KEY` |
| OIDC Google SSO | `OIDC_CLIENT_ID` empty |
| OpenSearch | Stub only |
| Entity search depth | Only 5 demo entities |
| Stock quotes | StaticProvider mock prices |

---

## FIX WORKFLOW

When you find a bug:

1. **Reproduce** — browser screenshot + curl output
2. **Fix minimally** — match existing code style; no over-engineering
3. **Retest** — same test case must pass
4. **Run pytest** — `pytest tests/ -q`
5. **Restart if needed** — `pm2 restart finance-api finance-web finance-admin`
6. **Re-seed if connector-related**

### Common fixes to check

- CORS / wrong API URL in web (`apps/web/lib/api.js`, `apps/web/.env`)
- Missing route in Layout nav for new pages
- BEA `Year=LAST5` fails on NIPA — must use explicit years `2020,2021,2022,2023,2024`
- Regional table should be `SAINC1` + `GeoFips=STATE`, not `CAINC1`
- State sources showing `pending` — re-run seed script
- Alerts first-load race — retry logic in `alerts.js`
- Uncommitted `economics.js` not deployed — restart `finance-web`

---

## DOCUMENTATION UPDATES (MANDATORY)

Update these files with **today's date** and **verified staging numbers**:

| File | What to update |
|------|----------------|
| `README.md` | Current status table, web routes (add `/economics`, `/registry`), test count, BEA live |
| `11th_June.md` | Phase 2 completion status, honest data gaps |
| `PHASE2_COMPLETION_REPORT.md` | E2E results, BEA live, economics page |
| `JAMES_REQUIREMENTS_VERIFICATION_REPORT.md` | J8 BEA now live; refresh record counts |
| `PHASE1_E2E_VERIFICATION_REPORT.md` | Or create **`E2E_LIVE_VERIFICATION_REPORT.md`** (new) — main deliverable |

### New report: `E2E_LIVE_VERIFICATION_REPORT.md`

Structure:

```markdown
# E2E Live Verification Report
**Date:** YYYY-MM-DD
**Branch:** feature/us-50-state-registry-api
**Staging:** 184.72.123.188

## Executive summary
- Overall readiness: X%
- FULL / PARTIAL / FAIL counts from test matrix

## Test matrix results
(table: ID, area, status, evidence)

## Issues found & fixed
(before/after for each fix)

## Data snapshot
(registry health, BEA count, source_record_meta, etc.)

## Honest gaps (need James)
- COBALT_API_KEY, CA_SOS_API_KEY

## Screenshots
(list paths or descriptions)

## Sign-off
Ready for James demo: YES/NO with caveats
```

---

## GIT WORKFLOW (MANDATORY)

```bash
cd /home/ubuntu/Finance-Advanced-Research-Platform
git status
git diff

# Stage only relevant files — never .env
git add <files>
git commit -m "$(cat <<'EOF'
Fix E2E issues found in live staging test; update docs and BEA integration.

EOF
)"
git push origin feature/us-50-state-registry-api
```

**Rules:**
- Never commit `.env`, tokens, or secrets
- Never force-push
- If pre-commit hook fails, fix and create NEW commit (no amend unless hook auto-modified)
- Update existing PR #2 or note in report if PR needs refresh

---

## ACCEPTANCE CRITERIA

| # | Criterion | Evidence |
|---|-----------|----------|
| 1 | All §A infrastructure tests pass | curl + pm2 output |
| 2 | All §C web pages load without JS errors | browser snapshots |
| 3 | §C FULL pages work as specified | screenshots |
| 4 | §D API smoke tests pass | curl JSON |
| 5 | BEA shows `source_tier: live` on `/economics` | screenshot |
| 6 | Registry search returns results | screenshot |
| 7 | `pytest tests/ -q` all pass | terminal output |
| 8 | `E2E_LIVE_VERIFICATION_REPORT.md` created | file exists |
| 9 | README + completion docs updated | git diff |
| 10 | Fixes committed and pushed | `git log -1` + push success |

---

## QUICK REFERENCE — Staging URLs

| Surface | URL |
|---------|-----|
| Web home | http://184.72.123.188:3003/ |
| Registry | http://184.72.123.188:3003/registry |
| Economics | http://184.72.123.188:3003/economics |
| Search | http://184.72.123.188:3003/search |
| Graph | http://184.72.123.188:3003/graph |
| Stock | http://184.72.123.188:3003/stock |
| Skills | http://184.72.123.188:3003/skills |
| Alerts | http://184.72.123.188:3003/alerts |
| Entity | http://184.72.123.188:3003/entities/1 |
| Portfolio | http://184.72.123.188:3003/portfolio/1 |
| Review | http://184.72.123.188:3003/review/1 |
| Merge | http://184.72.123.188:3003/entities/merge |
| Admin | http://184.72.123.188:3002/ |
| API docs | http://184.72.123.188:3001/docs |
| Registry health | http://184.72.123.188:3001/registry/health |
| Source health | http://184.72.123.188:3001/sources/health |

---

## EXECUTION ORDER

1. Read this file + skim `README.md`, `11th_June.md`
2. Run §A infrastructure checks
3. Run §D API curl smoke tests
4. Browser test §B + §C in order
5. Run §E connector/data checks
6. Compile failures → fix → retest
7. Run full pytest
8. Write `E2E_LIVE_VERIFICATION_REPORT.md`
9. Update docs listed above
10. Commit, push, report PR URL

**Start now. Work autonomously. Be honest in the report about partial vs full.**
