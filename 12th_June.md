# 12th June 2026 — Cobalt Live Integration, California SOS API Application & CA Data Seeded

**Purpose:** Daily handoff for James — Cobalt SOS fallback integrated and verified, California official API access requested, CA connector fixed and live data seeded on staging.

**Prior docs:** `11th_June.md` (50-state plan) · `PHASE2_COMPLETION_REPORT.md` · `E2E_LIVE_VERIFICATION_REPORT.md`

**Staging:** Web `http://184.72.123.188:3003` · API `:3001` · Admin `:3002`  
**Branch:** `feature/us-50-state-registry-api` · **PR #2**

---

## 1) Executive summary

| Area | Status (12 Jun) |
|------|-----------------|
| **Cobalt SOS API** | ✅ Integrated, live-tested, working on trial (20 free lookups) |
| **California (`us_ca`)** | ✅ **96 live records** seeded (via Cobalt interim); official CA API connector code ready |
| **CA SOS API access** | ⏳ **Submitted** — subscriptions `finance-platform-prod` + `finance-platform-uat` awaiting approval |
| **BEA** | ✅ Live — 429 records (`BEA_API_USER_ID` active) |
| **Registry total** | **202 records** across 51 jurisdictions |
| **Tests** | **74 passed** (`pytest tests/ -q`) |

---

## 2) What was done today

### 2.1 Cobalt Intelligence — integrated & verified

- Fixed `cobalt_fallback.py` to match live API:
  - Endpoint: `https://apigateway.cobaltintelligence.com/v1/search`
  - Params: `searchQuery`, `state` (full name), `liveData=false` (cached, saves credits)
  - Header: `x-api-key`
- Wired into `scrape_generic.py` for 44 scrape-tier states + DC
- **Live test succeeded:** Georgia entity search returned real SOS data (1/20 trial credits used for verification)
- Trial account: **20 free lookups** — use `COBALT_LIVE_DATA=false` in `.env` for cached pulls during dev

**Signup:** https://app.cobaltintelligence.com/ (paid plans ~$0.60–$1/lookup at volume after trial)

### 2.2 California SOS — official API connector fixed

- Updated `packages/connectors/us/state_registry/api/ca.py`:
  - Production base: `https://calico.sos.ca.gov/cbc/v1/api/`
  - Endpoints: `BusinessEntityKeywordSearch`, `BusinessEntityDetails`, `ServerStatus`
  - Header: `Ocp-Apim-Subscription-Key` (not `X-API-Key`)
- **Cobalt interim fallback** in `ca.py` when `CA_SOS_API_KEY` empty or API returns no rows
- Seeded **92 live CA entities** (Apple-related searches) → **96 total** in `source_record_meta`
- Fixed `scripts/seed-state-registry.sh` upsert URL (`/sources/records` not `/sources/records/upsert`)

### 2.3 California SOS developer portal — API access requested

Account: registered at [calicodev.sos.ca.gov](https://calicodev.sos.ca.gov/) (Abhishek Kulkarni).

| Subscription name | Product | State |
|-------------------|---------|-------|
| `finance-platform-prod` | CBC API Production | **Submitted** (awaiting CA SOS approval) |
| `finance-platform-uat` | CBC API - UAT | **Submitted** |

**When approved:** Profile → Subscriptions → **Primary key** → set `CA_SOS_API_KEY` in `.env` → `pm2 restart finance-api --update-env`. Connector will automatically prefer official CA API over Cobalt.

**Official guide:** [BE Public Search API Guide v1.0.4](https://calicodev.sos.ca.gov/content/California%20SOS%20BE%20Public%20Search%20API%20Guide%20v1.0.4.pdf)

### 2.4 Tests added

- `test_ca_parse_keyword_response_shape` — CA SOS JSON parsing (no network)
- `test_cobalt_parse_response_shape` — Cobalt JSON parsing (no network)

---

## 3) Staging verification (12 Jun)

```bash
# Registry health
curl http://184.72.123.188:3001/registry/health
# → 51 jurisdictions, 202 records

# California live search (Cobalt-sourced interim)
curl "http://184.72.123.188:3001/registry/search?q=apple&state=us_ca&limit=3"
# → 51 matches including APPLE INC., APPLE LLC, etc.

# Cobalt direct (1 credit if liveData=true)
curl -G 'https://apigateway.cobaltintelligence.com/v1/search' \
  --data-urlencode 'searchQuery=Apple' \
  --data-urlencode 'state=California' \
  --data-urlencode 'liveData=false' \
  -H "x-api-key: $COBALT_API_KEY"
```

---

## 4) Keys status

| Key | Status | Notes |
|-----|--------|-------|
| `COBALT_API_KEY` | ✅ SET | Trial — 20 lookups; use cached mode in dev |
| `CA_SOS_API_KEY` | ⏳ Pending | Subscription submitted; key appears when **Active** |
| `BEA_API_USER_ID` | ✅ SET | Live, 429 records |
| 17 federal gov keys | ✅ SET | All working |
| `OIDC_CLIENT_ID/SECRET` | Empty | Optional — staging has no login |

---

## 5) Data strategy (aligned with James)

```
Priority stack (per James: free first, Cobalt third):

1. Tier A/B free bulk/API     → NY, CO, FL, OR, WA, TX (+ CA when key approved)
2. Tier D scrape              → 44 states (Playwright framework in place)
3. Cobalt per-use fallback    → NOW LIVE for scrape states + CA interim
4. Official CA API            → When calicodev subscription approved (free)
```

**Cobalt is not a 100% replacement for CA** for licensing narrative (third-party, per-lookup cost) but **is sufficient for live lookups and demos** until CA SOS approves the free official key.

---

## 6) Remaining / next steps

1. **Wait for CA SOS** subscription approval → add `CA_SOS_API_KEY` → re-seed `us_ca` from official API
2. **Cobalt trial budget** — avoid bulk seeding all 44 states on trial; seed per-state or wait for paid plan
3. **BizFile scrape** (optional) — free official CA path if approval is slow
4. **OIDC** — Google Workspace SSO when James provides credentials
5. **E2E re-run** — `E2E_LIVE_TEST_AGENT_PROMPT.md` after CA key active

---

## 7) Files changed (12 Jun commit)

| File | Change |
|------|--------|
| `packages/connectors/us/state_registry/api/ca.py` | Official CA endpoints + Cobalt fallback |
| `packages/connectors/us/state_registry/cobalt_fallback.py` | Live API URL/params/parsing |
| `packages/connectors/us/state_registry/states/scrape_generic.py` | Cobalt integration |
| `scripts/seed-state-registry.sh` | Fix records upsert endpoint |
| `tests/connectors/test_state_registry.py` | CA + Cobalt parse tests |
| `.env.example` | CA API header/URL docs |
| `README.md`, `PHASE2_COMPLETION_REPORT.md`, `E2E_LIVE_VERIFICATION_REPORT.md` | Status update |

---

*End of 12 June handoff*
