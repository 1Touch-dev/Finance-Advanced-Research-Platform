# Phase 2 — U.S. 50-State Registry + BEA + Licensable API — Full Agent Prompt

**Copy everything below the line into a new Cursor Agent chat. Do not summarize or shorten it.**

---

## YOUR MISSION

You are an autonomous senior full-stack engineer agent working in **partnership** with a parent agent who will verify your work afterward.

**Build James Thunder Marketing’s full U.S. state company registry program end-to-end:**

1. **All 50 U.S. states + DC** — same normalized schema, free sources first, scrape where needed, Cobalt per-use fallback only
2. **Licensable registry API** — `GET /registry/search`, `GET /registry/entity/{jurisdiction}/{entity_id}`, API key auth, rate limits
3. **BEA economic data connector** (#18) — Bureau of Economic Analysis API
4. Keep **existing 17 gov connectors + Phase 1 MVP** working (do not regress)
5. **Live E2E test** everything on staging using **Cursor Browser MCP** (`cursor-ide-browser`)
6. **Update all docs** (README, `11th_June.md`, completion reports)
7. **Commit, push, open PR** on GitHub
8. Produce **`JAMES_REQUIREMENTS_VERIFICATION_REPORT.md`** — structured report for parent agent sign-off

**Do not claim done until every item in § ACCEPTANCE CRITERIA is ✅ with evidence.**

---

## JAMES REQUIREMENTS (NON-NEGOTIABLE)

Source: WhatsApp 9–11 June 2026, documented in `11th_June.md`.

| # | Requirement | Implementation |
|---|-------------|----------------|
| J1 | **All 50 states + DC** | 51 jurisdiction connectors/adapters registered and ingest ≥1 record each on staging |
| J2 | **Same normalized schema** | `state_entity` model in `packages/connectors/us/state_registry/schema.py` |
| J3 | **Free first** | Tier A bulk + Tier B API before scrape; document tier per state |
| J4 | **Scrape where no API** | Playwright framework in `packages/scrapers/` with per-state configs |
| J5 | **No paid OpenCorporates** | Deprecate or keep SEC fallback only; do not require `OPENCORPORATES_API_KEY` |
| J6 | **Cobalt 3rd fallback** | Optional `COBALT_API_KEY` — only when free path fails; config-gated |
| J7 | **Licensable API product** | External `/registry/*` routes with API keys + usage logging |
| J8 | **BEA economic data** | New connector + env `BEA_API_USER_ID` (free signup) |
| J9 | **Evidence/provenance** | Every record → raw in vault → EvidenceRef (existing pipeline) |
| J10 | **Keep James updated** | Final report includes state-by-state status table |

**Google OIDC (SSO):** Nice-to-have only — do not block on `OIDC_CLIENT_ID` if unset.

---

## REPOSITORY CONTEXT

| Item | Value |
|------|-------|
| Workspace | `/home/ubuntu/Finance-Advanced-Research-Platform` |
| **Base branch (branch FROM this)** | `feature/phase1-us-mvp-100pct` |
| **New branch (CREATE this)** | `feature/us-50-state-registry-api` |
| Parent PR (Phase 1) | https://github.com/1Touch-dev/Finance-Advanced-Research-Platform/pull/1 |
| Remote | `https://github.com/1Touch-dev/Finance-Advanced-Research-Platform.git` |
| Staging EC2 | `184.72.123.188` — Web `:3003`, API `:3001`, Admin `:3002` |
| PM2 apps | `finance-api`, `finance-web`, `finance-admin` |
| Infra | Postgres `:5433`, MinIO `:9000`, OpenSearch `:9200` |
| Credentials | `.env` (gitignored) — read locally; never commit secrets |
| Planning docs | `5th_june.md`, `10th_June.md`, `11th_June.md` |

### Uncommitted work on base branch (INCLUDE in your branch)

Before creating the new branch, **commit or carry forward** these local changes on `feature/phase1-us-mvp-100pct`:

- Connector fixes (USAspending, SAM, FARA, CourtListener, OpenCorporates SEC fallback)
- Anthropic live integration (`claude-sonnet-4-6`), skills status, finance `ai_narrative`
- Admin source health dedupe, alerts retry
- `scripts/seed-all-connectors.sh` env loading fix
- `10th_June.md`, `11th_June.md` (new)
- `.env.example` updates

**One logical commit** for Phase 1 fixes if not already pushed, then branch.

### Git workflow (MANDATORY)

```bash
cd /home/ubuntu/Finance-Advanced-Research-Platform
git fetch origin
git checkout feature/phase1-us-mvp-100pct
git pull origin feature/phase1-us-mvp-100pct
# commit any pending Phase 1 fixes if needed (never commit .env)
git checkout -b feature/us-50-state-registry-api
# ... implement ...
git push -u origin feature/us-50-state-registry-api
gh pr create --base integration/phase1-mvp-base --title "..." --body "..."
```

**Never commit:** `.env`, PDFs, API keys, credentials.  
**Never force-push** `main` or `integration/phase1-mvp-base`.

---

## ARCHITECTURE TO BUILD

### Layer 1 — Unified schema

Create `packages/connectors/us/state_registry/`:

```
state_registry/
  __init__.py
  schema.py              # StateEntity dataclass + normalize() + status vocabulary
  base.py                # StateRegistryConnector(USBaseConnector)
  registry.py            # JURISDICTIONS dict: 51 entries with tier, search_url, adapter
  bulk/                  # NY, CO, FL, OR parsers
  api/                   # WA, TX, CA adapters
  scrape/                # Playwright per-state (or configs YAML)
  cobalt_fallback.py     # thin wrapper
  states/
    us_ny.py
    us_co.py
    ... (51 files or grouped by tier)
```

**Normalized `state_entity` fields (minimum):**

```python
jurisdiction_code: str      # e.g. "us_ny"
entity_id: str              # SOS file/registration number
legal_name: str
entity_type: str | None
status: str                 # normalized: active|inactive|dissolved|unknown
formation_date: str | None
registered_agent_name: str | None
principal_address: dict | None
mailing_address: dict | None
officers: list[dict]        # optional
source_tier: str            # bulk|api|scrape|cobalt
source_url: str
retrieved_at: str           # ISO8601
```

### Layer 2 — Ingestion tiers (implement ALL 51)

**Tier A — Bulk (implement fully, seed real data):**

| Code | State | Source |
|------|-------|--------|
| us_ny | New York | https://data.ny.gov/api/views/n9v6-gdp6/rows.json?accessType=DOWNLOAD (paginate/limit for seed) |
| us_co | Colorado | https://data.colorado.gov/resource/4ykn-tg5h.json |
| us_fl | Florida | SFTP `sftp.floridados.gov` public creds on https://dos.fl.gov/sunbiz/other-services/data-downloads/ |
| us_or | Oregon | https://data.oregon.gov/resource/tckn-sxa6.json |

**Tier B — API (implement):**

| Code | State | Source |
|------|-------|--------|
| us_wa | Washington | https://finditconsumer.wa.gov/corps/searchapi.aspx |
| us_tx | Texas | https://api-doc.comptroller.texas.gov/ (franchise tax; document limitation) |
| us_ca | California | CA SOS BE Public Search API if `CA_SOS_API_KEY` set; else scrape bizfile |

**Tier D — Scrape (Playwright) for remaining ~40 states:**

Use James’s SOS URLs from `11th_June.md` §8 / NASS: https://www.nass.org/business-services/corporate-registration

**Minimum viable scrape per state:** search for a known entity name (e.g. "Department", "Services", "Inc") → parse top 5 results → yield records.

**Tier E — Cobalt fallback (`COBALT_API_KEY` optional):**

- `GET https://apigateway.cobaltintelligence.com/v1/search/?state={st}&searchQuery={q}`
- Use only when bulk/api/scrape returns 0 and key is set
- Docs: https://cobaltintelligence.stoplight.io/docs/cobalt-intelligence/0f51bcacc3743-secretary-of-state-api

### Layer 3 — Orchestrator

- `packages/connectors/us/state_registry/orchestrator.py` — runs all 51 jurisdictions
- Register in `packages/connectors/runner/cli.py` as `state_registry_us` OR 51 separate connector kinds `state_us_ny`, etc. (prefer **single orchestrator** + per-state sub-metrics)
- `scripts/seed-state-registry.sh` — bootstrap sources, run all 51, print summary
- Update `scripts/seed-all-connectors.sh` to include registry seed (optional flag)

### Layer 4 — Licensable Registry API

Create `apps/api/app/api/registry.py`:

```
GET  /registry/health              # jurisdictions live count
GET  /registry/jurisdictions       # list 51 with tier + last_run status
GET  /registry/search?q=&state=    # search normalized records (Postgres + OpenSearch)
GET  /registry/entity/{jurisdiction}/{entity_id}
POST /registry/keys                # admin: create API key (simple hashed key in DB)
```

- API key via header `X-Registry-Api-Key` or query `api_key`
- Rate limit: e.g. 100 req/min per key (in-memory or Redis if available)
- Log usage to `registry_api_usage` table

Wire router in `apps/api/app/main.py`.

### Layer 5 — BEA connector (#18)

- `packages/connectors/us/bea/bea.py` — fetch Regional GDP or NIPA sample
- Signup: https://apps.bea.gov/API/signup/ → `BEA_API_USER_ID` in `.env.example`
- Endpoint: `https://apps.bea.gov/api/data?UserID=...&method=GetData&datasetname=Regional&...`
- Register in CLI + seed script
- Optional: expose `/finance/macro` or enrich `analyze_stock` with BEA regional snippet

### Layer 6 — Web UI (minimal)

- `apps/web/pages/registry.js` — search box, state filter, results table
- Link from nav in `apps/web/src/components/Layout.js`
- Admin: registry health on dashboard or link to `/registry/health`

### Layer 7 — Deprecate OpenCorporates as primary

- Keep `opencorporates` connector with SEC fallback OR redirect to `state_registry` search
- Update README: registry is now **in-house 50-state**

---

## EXISTING PATTERNS (FOLLOW — DO NOT REINVENT)

- **Connector base:** `packages/connectors/us/_common/base_us.py` — `fetch_records()`, `normalize()`, `run()`
- **HTTP helpers:** `packages/connectors/us/_common/http_helpers.py` — `env_or_creds`, `http_get`, `yield_samples` (test only)
- **Runner:** `packages/connectors/runner/run_connector.py` — `persist_raw_and_evidence()`
- **CLI env:** `runner/cli.py` `_load_env()` loads root `.env`
- **Sources API:** `apps/api/app/api/sources.py` — health, runs, bootstrap
- **Tests:** `tests/connectors/` — add `test_state_registry.py`, contract tests per tier

**Playwright:** add to `requirements.txt` or `packages/scrapers/requirements.txt`; headless in CI, respect rate limits on staging.

---

## STEP-BY-STEP EXECUTION PLAN

### Step 0 — Setup (30 min)
- [ ] Read `11th_June.md`, `5th_june.md` §4 (connectors module)
- [ ] Commit pending Phase 1 local changes on base branch
- [ ] Create branch `feature/us-50-state-registry-api`
- [ ] `source venv/bin/activate` — ensure deps install

### Step 1 — Framework (Day 1)
- [ ] `schema.py`, `base.py`, `registry.py` with all 51 jurisdictions metadata
- [ ] DB migration if needed for `registry_api_keys`, `registry_api_usage` (or SQLAlchemy models)
- [ ] `/registry/health` stub returning 0/51

### Step 2 — Tier A bulk (Day 1–2)
- [ ] NY, CO, FL, OR connectors with real fetch (limit 10–50 records per state for seed)
- [ ] Seed script + verify `/sources/health` shows records

### Step 3 — Tier B API (Day 2)
- [ ] WA, TX, CA adapters
- [ ] Register BEA connector; signup key if not in `.env`

### Step 4 — Scrape framework + all remaining states (Day 2–4)
- [ ] `packages/scrapers/playwright_runner.py` + YAML configs per state
- [ ] Implement scrape adapter for **every remaining state** (at minimum: search → 3–5 records)
- [ ] States without successful scrape: document blocker; use Cobalt if key present OR sample in `ENV=test` only with clear `source_tier: scrape_pending`

**James requires all 51 jurisdictions to show as "connected" in `/registry/jurisdictions`** — even if tier is scrape with limited fields.

### Step 5 — Registry API + keys (Day 4)
- [ ] Full search + entity endpoints
- [ ] API key creation + rate limit
- [ ] OpenSearch index `registry-entities` for full-text name search

### Step 6 — Integration (Day 4–5)
- [ ] Entity resolution: link `state_entity` ↔ SEC CIK where possible (name match)
- [ ] Web registry page
- [ ] Update admin health

### Step 7 — Tests (mandatory)
```bash
cd /home/ubuntu/Finance-Advanced-Research-Platform
source venv/bin/activate
ENV=test pytest tests/ -q                    # all must pass
ENV=test pytest tests/connectors/ -q           # include new registry tests
```
- [ ] At least 1 test per tier (bulk, api, scrape mock, registry API)
- [ ] Contract test: 51 jurisdictions in registry metadata

### Step 8 — Staging deploy + seed
```bash
pm2 restart finance-api finance-web finance-admin
bash scripts/seed-all-connectors.sh
bash scripts/seed-state-registry.sh          # new
curl http://127.0.0.1:3001/registry/health
curl http://127.0.0.1:3001/registry/jurisdictions
```

### Step 9 — Browser E2E (MANDATORY — Cursor Browser MCP)

Use `cursor-ide-browser` MCP tools. Test on **staging public URLs**:

| # | URL / action | Pass criteria |
|---|--------------|---------------|
| 1 | `http://184.72.123.188:3003` | Home loads |
| 2 | `/registry` | Search "Apple" or "Services" returns results |
| 3 | `/skills` | Shows Anthropic live if key set |
| 4 | `/stock?ticker=AAPL` or stock page | analyze works |
| 5 | `http://184.72.123.188:3001/registry/jurisdictions` | Shows **51** jurisdictions |
| 6 | `http://184.72.123.188:3001/registry/search?q=inc&state=us_ny` | JSON results |
| 7 | `http://184.72.123.188:3001/sources/health` | 17 gov connectors still success |
| 8 | `http://184.72.123.188:3002` | Admin loads, registry count visible |
| 9 | API docs `/docs` | `/registry` routes listed |

Document screenshots/snapshots in `JAMES_REQUIREMENTS_VERIFICATION_REPORT.md`.

### Step 10 — Documentation updates (MANDATORY)

Update these files:

| File | Updates |
|------|---------|
| `README.md` | Phase 2 status, 50-state registry, BEA, `/registry` API, new env vars |
| `11th_June.md` | Mark completed items, actual timeline, state coverage table |
| `10th_June.md` | Cross-reference Phase 2 branch |
| `.env.example` | `BEA_API_USER_ID`, `COBALT_API_KEY`, `CA_SOS_API_KEY`, `REGISTRY_API_*` |
| `docs/DEPLOYMENT.md` | seed-state-registry.sh, Playwright deps |
| `PHASE2_COMPLETION_REPORT.md` | **NEW** — executive summary |
| `JAMES_REQUIREMENTS_VERIFICATION_REPORT.md` | **NEW** — parent verification checklist (§ below) |

### Step 11 — Commit, push, PR

```bash
git add -A  # exclude .env
git status  # verify no secrets
git commit -m "$(cat <<'EOF'
Add U.S. 50-state registry framework, BEA connector, and licensable registry API.

Implements James-approved state-by-state company data ingestion (bulk, API, scrape, Cobalt fallback) with unified schema and external /registry search API.
EOF
)"
git push -u origin feature/us-50-state-registry-api
gh pr create --base integration/phase1-mvp-base --title "Phase 2: U.S. 50-state registry + licensable API + BEA" --body "$(cat <<'EOF'
## Summary
- 51-jurisdiction U.S. state company registry (bulk/API/scrape/Cobalt fallback)
- Licensable `/registry/search` API with API keys
- BEA economic data connector (#18)
- Phase 1 connectors preserved

## Test plan
- [ ] pytest green
- [ ] seed-state-registry.sh all 51 jurisdictions
- [ ] Browser E2E on staging (see JAMES_REQUIREMENTS_VERIFICATION_REPORT.md)

EOF
)"
```

Return **PR URL** in final message.

---

## ACCEPTANCE CRITERIA (ALL MUST PASS)

### James requirements
- [ ] **J1** 51/51 jurisdictions in `/registry/jurisdictions` with `last_status: success` or `partial` with ≥1 record
- [ ] **J2** All records use same `state_entity` schema in `normalized` JSON
- [ ] **J3** Tier A/B used where documented in `11th_June.md` before scrape
- [ ] **J4** Playwright scraper framework exists + configs for scrape-tier states
- [ ] **J5** No OpenCorporates API key required
- [ ] **J6** Cobalt adapter exists, disabled without `COBALT_API_KEY`
- [ ] **J7** `/registry/search` works with API key; usage logged
- [ ] **J8** BEA connector ingests ≥1 regional/industry record
- [ ] **J9** Evidence refs exist for registry seed runs
- [ ] **J10** Final report has 51-row state table

### Technical
- [ ] `pytest tests/ -q` — 0 failures (≥ prior 33 tests)
- [ ] 17 original gov connectors still success on `/sources/health`
- [ ] Anthropic skills still work if key in `.env`
- [ ] No secrets in git
- [ ] PM2 services online after deploy

### Deliverables
- [ ] Branch `feature/us-50-state-registry-api` pushed
- [ ] GitHub PR created
- [ ] `JAMES_REQUIREMENTS_VERIFICATION_REPORT.md` committed
- [ ] `PHASE2_COMPLETION_REPORT.md` committed

---

## JAMES_REQUIREMENTS_VERIFICATION_REPORT.md — TEMPLATE

Create this file for the **parent agent** to verify. Fill every row with real staging evidence.

```markdown
# James Requirements Verification Report
Date: YYYY-MM-DD
Branch: feature/us-50-state-registry-api
PR: <url>
Agent: Phase 2 implementation agent

## Executive summary
(2-3 sentences: met / partial / blocked)

## J1 — 51 jurisdictions
| jurisdiction | tier | adapter | records_seeded | last_status | evidence |
|--------------|------|---------|----------------|-------------|----------|
| us_al | scrape | ... | N | success | run_id |
| ... (51 rows) | | | | | |

## J2–J10 checklist
| ID | Requirement | Status | Evidence |
|----|-------------|--------|----------|
| J1 | 51 states + DC | ✅/❌ | |
...

## API smoke tests
| Endpoint | Status | Sample |
|----------|--------|--------|
| GET /registry/jurisdictions | 200 | count=51 |
| GET /registry/search?q=... | 200 | |
...

## Browser E2E (staging 184.72.123.188)
| Step | Pass | Notes |
|------|------|-------|
| Registry web search | ✅/❌ | |

## Regression
| Check | Pass |
|-------|------|
| 17 gov connectors | |
| pytest | |
| Anthropic skills | |

## Blockers / honest gaps
(list anything not fully met)

## Sign-off recommendation
COMPLETE / INCOMPLETE — reason
```

---

## ENV VARS TO ADD (.env.example only)

```bash
# BEA — free signup https://apps.bea.gov/API/signup/
BEA_API_USER_ID=

# California SOS BE API (optional) — https://calicodev.sos.ca.gov/
CA_SOS_API_KEY=

# Cobalt SOS fallback (optional, per-use)
COBALT_API_KEY=

# Registry API (generated keys stored in DB; optional bootstrap admin key)
REGISTRY_API_ADMIN_TOKEN=
```

---

## CONSTRAINTS & PRINCIPLES

1. **Minimize scope creep** — no Phase 2 global (UK, OpenSanctions) in this PR
2. **Match existing code style** — read surrounding files before writing
3. **Official APIs first**, scrape second, Cobalt third
4. **Never fabricate success** — if a state portal blocks bots, document it and use Cobalt or mark `partial`
5. **Real environment** — run commands on EC2 staging, not hypothetical
6. **Use Browser MCP** for E2E — do not skip
7. **Parent agent will verify** — the verification report must be honest

---

## REFERENCE LINKS

- Planning: `11th_June.md`, `10th_June.md`, `5th_june.md`
- NASS state directory: https://www.nass.org/business-services/corporate-registration
- BEA developers: https://www.bea.gov/resources/for-developers
- BEA API signup: https://apps.bea.gov/API/signup/
- Florida SFTP: https://dos.fl.gov/sunbiz/other-services/data-downloads/
- Cobalt API: https://cobaltintelligence.stoplight.io/docs/cobalt-intelligence/0f51bcacc3743-secretary-of-state-api
- OpenCorporates DIY analysis: https://blog.opencorporates.com/2025/09/15/sourcing-data-directly-from-us-state-registries/

---

## FINAL MESSAGE TO USER (when done)

Post this exact structure:

1. **PR URL**
2. **Summary** — what was built (3-5 bullets)
3. **51/51 jurisdiction status** — count with records
4. **Test results** — pytest count, browser E2E pass/fail
5. **Path to verification report** — `JAMES_REQUIREMENTS_VERIFICATION_REPORT.md`
6. **Honest gaps** — anything James wanted but isn't 100%
7. **Ask parent agent** to review verification report against James requirements

---

**END OF PROMPT — execute fully without asking for permission unless blocked on credentials only James can provide (e.g. Cobalt key). Proceed with free sources and scrapes regardless.**
