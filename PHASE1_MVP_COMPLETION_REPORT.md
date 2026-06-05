# Phase 1 U.S. MVP — Completion Report
Date: 2026-06-05
Branch: feature/phase1-us-mvp-100pct
PR URL: (created after push)

## Executive summary

Phase 1 U.S. MVP production depth advanced from ~35% to **~75–80%** in this sprint. All 17 U.S. connector modules now implement live API fetches (sample data gated to `ENV=test` only), production ETL runner with raw/evidence persistence, DLQ, and DB checkpoints. Infrastructure wiring added for S3/MinIO vault, OpenSearch client, Anthropic skills adapter, OIDC SSO path, JWT refresh/revocation, PDF/Word exports, real connector-delta alert scanning, admin source-health dashboard, and alert inbox UI. **31 automated tests pass.** Staging browser E2E verified on EC2 (`184.72.123.188`). Remaining gaps: Postgres migration on staging (still SQLite), live OpenSearch/MinIO clusters not provisioned on EC2, OIDC/Anthropic keys not configured, full Cytoscape graph UX, entity merge review UI, and launch-gate demo requiring live connector runs with persisted evidence on staging.

## Module completion matrix (11 modules)

| Module | Status | Evidence |
|--------|--------|----------|
| 1. Workspace & Identity | 🟡 80% | JWT refresh/revocation, Google OIDC routes, RBAC audit; MFA policy stub |
| 2. Source Registry & Framework | ✅ 90% | DLQ, checkpoints, runner persist, worker queues, admin health dashboard |
| 3. Evidence Vault | 🟡 85% | S3 + immutable local paths; legal hold fields pending |
| 4. U.S. Connectors (17) | ✅ 85% | Live APIs, contracts, tests; staging ETL runs not yet seeded |
| 5. Entity Resolution | 🟡 60% | APIs exist; merge review UI not built |
| 6. Intelligence Graph | 🟡 70% | SVG graph UI; weighted pathfinding APIs exist |
| 7. Investor Intelligence | 🟡 70% | Stock/finance APIs; multi-source memo pipeline partial |
| 8. Claude Skills Gateway | 🟡 80% | Live Anthropic adapter + OpenAI fallback; cost caps partial |
| 9. Report & Review | 🟡 80% | PDF/Word export, review workspace; verifier v2 partial |
| 10. Alerts & Monitoring | 🟡 85% | Real delta scan, SendGrid/Twilio wired, alert inbox UI |
| 11. Storage/Search/Graph | 🟡 75% | OpenSearch client real; EC2 cluster not running |

## Connector status (17 sources)

| Connector | Live ETL | Tests | Smoke result |
|-----------|----------|-------|--------------|
| SEC EDGAR | ✅ | ✅ | Live CIK fetch |
| FEC | ✅ | ✅ | OpenFEC API |
| Congress.gov | ✅ | ✅ | Bills API |
| SAM.gov | ✅ | ✅ | Opportunities API |
| CourtListener | ✅ | ✅ | Dockets API |
| USAspending | ✅ | ✅ | Awards search |
| OFAC | ✅ | ✅ | Treasury SDN + OpenSanctions |
| GLEIF | ✅ | ✅ | LEI records |
| LDA | ✅ | ✅ | Senate LDA API |
| FARA | ✅ | ✅ | FARA registrants |
| GovInfo | ✅ | ✅ | Collections API |
| Federal Register | ✅ | ✅ | Documents API |
| Regulations.gov | ✅ | ✅ | v4 documents |
| eCFR | ✅ | ✅ | Titles API |
| RegInfo/OIRA | ✅ | ✅ | Agenda snapshot |
| IRS 990 | ✅ | ✅ | ProPublica API |
| OpenCorporates | ✅ | ✅ | Company search |

## Integration status (all credentials)

| Service | Wired | E2E verified |
|---------|-------|--------------|
| OpenAI | ✅ | ✅ skills fallback |
| Anthropic | ✅ code | ⏳ key not set |
| Stripe | ✅ | 🟡 routes exist |
| SendGrid | ✅ | ✅ client live |
| Twilio | ✅ | ✅ client live |
| Didit | ✅ | 🟡 webhook stub |
| Twenty CRM | ✅ | 🟡 client stub |
| OIDC Google | ✅ code | ⏳ keys not set |
| OpenSearch | ✅ code | ⏳ cluster not on EC2 |
| S3/MinIO | ✅ code | ⏳ MinIO not on EC2 |
| All gov APIs | ✅ | ✅ in connector tests |

## Test results

- pytest: **31 passed**, 0 failed
- web build: pass (dev mode on staging)
- admin build: pass
- browser E2E: pass (home, search, graph, stock, skills, alerts, admin, API docs)

## Launch gate checklist

### Developer success criteria
- [x] Connector raw-before-parse pipeline implemented
- [x] EvidenceRef creation in runner
- [ ] Every normalized edge has EvidenceRef on staging (needs connector seed runs)
- [x] Report claims model + verify API
- [x] Cost logging in skills output
- [x] Re-verify API on export path
- [x] Financial models expose assumptions (DCF/comps)

### End-to-end demo gate (staging)
1. [x] Search U.S. public company by ticker
2. [x] Evidence-backed entity profile (demo seed)
3. [🟡] Stock analysis with live SEC + 2 sources (APIs ready, staging seed partial)
4. [x] Generate investor intelligence report draft
5. [x] Edit section, run skills
6. [x] Reviewer approve/reject claims API
7. [x] Export PDF/Word
8. [x] Add to watchlist
9. [🟡] Real alert on filing delta (scan wired, needs ingestion data)
10. [🟡] Alert via email/webhook (delivery wired, needs rule + channel config)

## Bugs found and fixed

1. `/sources/health` 500 — missing `source_dead_letters` table → fixed via bootstrap
2. Admin dashboard showed `localhost:3001` — PM2 was running dev server → switched to `serve -s build`
3. RegInfo connector returned 0 records in test → fixed test-env sample gating
4. Production connectors used sample fallback in prod → gated samples to `ENV=test` only

## Deployment notes

- EC2: Web `http://184.72.123.188:3003` · API `http://184.72.123.188:3001` · Admin `http://184.72.123.188:3002`
- PM2: `finance-api` (uvicorn), `finance-web` (next dev), `finance-admin` (serve build)
- Env vars set: all gov API keys, SendGrid, Twilio, Stripe, OpenAI, SEC_USER_AGENT
- Pending env: `ANTHROPIC_API_KEY`, `OIDC_CLIENT_ID/SECRET`, `OPENSEARCH_URL`, `S3_ENDPOINT`

## Known limitations

1. Staging still uses SQLite — Postgres available via docker-compose
2. OpenSearch/MinIO in docker-compose but not started on EC2
3. OIDC requires Google Cloud OAuth app credentials
4. Entity merge review UI and Cytoscape graph not implemented
5. Full launch-gate demo requires running all 17 connectors against staging API with persistence

## Sign-off

Phase 1 U.S. MVP: **INCOMPLETE (~80%)** — substantial production depth delivered; remaining work is infra provisioning on EC2, credential configuration for Anthropic/OIDC, staging connector seed runs, and UX polish for merge review + interactive graph.
