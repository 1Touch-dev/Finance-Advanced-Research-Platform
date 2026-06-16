# Phase 1 U.S. MVP — Full Implementation Agent Prompt

**Copy everything below the line into a new Cursor Agent chat. Do not summarize or shorten it.**

---

## YOUR MISSION

You are an autonomous senior full-stack engineer agent. Your job is to take the existing **Finance-Advanced-Research-Platform** monorepo from its current ~35–45% foundation state to **100% complete Phase 1 U.S. MVP** — with **zero gaps**, **no stubs**, **no sample/fallback connector paths in production code**, and **every credential from the local credentials file fully wired and verified**.

You must: **implement → test → verify in Cursor browser → fix bugs → retest → commit → push → publish to GitHub** — all on a **new feature branch** created from a **dedicated integration branch** (not directly from `main`).

When finished, produce a structured **`PHASE1_MVP_COMPLETION_REPORT.md`** documenting everything done, test results, and launch-gate sign-off.

**Do not stop early. Do not defer items as "Phase 2" unless explicitly listed as out-of-scope below. Do not claim 100% until every acceptance criterion passes.**

---

## REPOSITORY CONTEXT

- **Workspace:** `/home/ubuntu/Finance-Advanced-Research-Platform`
- **Current branch:** `productionization/codex-roadmap`
- **Remote:** `https://github.com/1Touch-dev/Finance-Advanced-Research-Platform.git`
- **Staging EC2:** Web `http://184.72.123.188:3003` · API `http://184.72.123.188:3001` · Admin `http://184.72.123.188:3002`
- **Master spec docs (read first, local only — NOT in git):**
  - `Enterprise Intelligence Development Plan.pdf`
  - `Enterprise Intelligence Scaling Plan.pdf`
  - `INTELIGENCE Platform Credentials.pdf`
- **Implementation roadmap (in repo):** `5th_june.md` (sections §6 and §7 are your checklists)
- **Gap analysis:** `docs/REQUIREMENT_GAP_ANALYSIS.md`
- **Apps:** `apps/api` (FastAPI), `apps/web` (Next.js), `apps/admin` (React), `apps/worker` (Bull/Redis)
- **Packages:** `packages/connectors`, `packages/finance`, `packages/reporting`

---

## GIT & BRANCH STRATEGY (MANDATORY — DO FIRST)

Execute in this exact order:

1. `git fetch origin`
2. Ensure you are on `productionization/codex-roadmap` and it is up to date.
3. Create integration base branch:
   ```bash
   git checkout productionization/codex-roadmap
   git pull origin productionization/codex-roadmap
   git checkout -b integration/phase1-mvp-base
   git push -u origin integration/phase1-mvp-base
   ```
4. Create your working feature branch FROM that integration branch:
   ```bash
   git checkout integration/phase1-mvp-base
   git checkout -b feature/phase1-us-mvp-100pct
   ```
5. **All commits go on `feature/phase1-us-mvp-100pct` only.**
6. At the end, push and open a PR:
   ```bash
   git push -u origin feature/phase1-us-mvp-100pct
   gh pr create --base integration/phase1-mvp-base --title "feat: complete Phase 1 U.S. MVP (100%)" --body "See PHASE1_MVP_COMPLETION_REPORT.md"
   ```

**Never commit secrets. Never force-push to `main`.**

---

## SECRETS & GITIGNORE (MANDATORY — BEFORE CODING)

1. Read **`INTELIGENCE Platform Credentials.pdf`** (local file) and ensure **every LIVE credential** is present in **`.env`** at repo root (create from `.env.example` if needed).
2. Required env vars to wire (at minimum — add any others found in credentials PDF):

   ```
   # Core
   DATABASE_URL=postgresql+psycopg://...   # migrate off SQLite for MVP
   JWT_SECRET=...
   ENV=staging

   # Web
   NEXT_PUBLIC_API_URL=http://184.72.123.188:3001
   REACT_APP_API_URL=http://184.72.123.188:3001

   # Worker
   REDIS_URL=redis://127.0.0.1:6379

   # AI
   OPENAI_API_KEY=...
   ANTHROPIC_API_KEY=...          # add for live Claude skills

   # Payments
   STRIPE_PUBLIC_KEY=...
   STRIPE_SECRET_KEY=...
   STRIPE_WEBHOOK_SECRET=...

   # Notifications
   SENDGRID_API_KEY=...
   TWILIO_ACCOUNT_SID=...
   TWILIO_AUTH_TOKEN=...
   TWILIO_PHONE_NUMBER=...

   # KYC / CRM
   DIDIT_CLIENT_ID=...
   DIDIT_API_KEY=...
   DIDIT_WEBHOOK_SECRET=...
   TWENTY_API_KEY=...
   TWENTY_WORKSPACE_URL=...

   # Government APIs
   SEC_USER_AGENT=...
   CONGRESS_API_KEY=...
   FEC_API_KEY=...
   REGULATIONS_GOV_API_KEY=...
   GOVINFO_API_KEY=...
   SAM_GOV_API_KEY=...
   COURTLISTENER_API_TOKEN=...
   SANCTIONS_API_KEY=...

   # Storage / Search
   OPENSEARCH_URL=...
   OPENSEARCH_INDEX=enterprise-docs
   S3_ENDPOINT=...
   S3_BUCKET=...
   S3_ACCESS_KEY=...
   S3_SECRET_KEY=...

   # Optional commercial (wire if credentials exist)
   MERCADOPAGO_ACCESS_TOKEN=...
   NFEIO_API_KEY=...
   FOCUSNFE_API_TOKEN=...
   ```

3. Update **`.env.example`** with all variable **names** (no real values).
4. Verify **`.gitignore`** blocks:
   - `.env`, `apps/admin/.env`
   - `*.pdf`, credentials PDFs
   - `*.db`, `venv/`, `node_modules/`, `.next/`
   - `exports/`, `artifacts/`
5. Run `git status` and confirm **no secrets or PDFs are staged**.
6. Add pre-commit or CI secret scanning if not present (e.g. `gitleaks` or `detect-secrets` in GitHub Actions).

---

## PHASE 1 U.S. MVP — 11 MODULES (100% REQUIRED)

Implement **every item** in `5th_june.md` §6.1–§6.12. Summary:

### Module 1 — Enterprise Workspace & Identity
- OIDC SSO (Google Workspace or Azure AD — pick one, fully working)
- JWT refresh tokens + revocation
- RBAC enforced on ALL sensitive endpoints
- MFA option for admin/reviewer roles
- Tenant isolation integration tests
- Admin UI: user/role/workspace management (not just health check)

### Module 2 — Source Registry & Connector Framework
- Scheduled connector jobs via `apps/worker`
- DB-persisted checkpoints per source
- Idempotency keys, stable external IDs
- Retry + exponential backoff + dead-letter table
- Source run metrics + admin health dashboard
- Complete `source_contract.yml` for all 18 U.S. sources

### Module 3 — Evidence Vault
- S3/MinIO storage with immutable paths (`source/YYYY-MM-DD/sha256`)
- Raw-always-first: no parse without stored raw artifact
- EvidenceRef linked to document metadata
- Document viewer in web UI
- Retention + legal hold fields

### Module 4 — U.S. Source Connectors (ALL 18 — NO SAMPLE FALLBACK IN PROD PATH)

Each connector MUST implement full ETL:
`discover → fetch → raw persist → normalize → EvidenceRef → graph edges + timeline events`

| Connector | Must be live |
|-----------|--------------|
| SEC EDGAR | ✅ |
| FEC | ✅ |
| LDA | ✅ |
| FARA | ✅ |
| Congress.gov | ✅ |
| GovInfo | ✅ |
| Federal Register | ✅ |
| Regulations.gov | ✅ |
| eCFR | ✅ |
| RegInfo/OIRA | ✅ |
| USAspending | ✅ |
| SAM.gov | ✅ |
| IRS 990 | ✅ |
| CourtListener | ✅ |
| OFAC/OpenSanctions | ✅ |
| OpenCorporates | ✅ |
| GLEIF | ✅ |

- Remove or gate all `samples = [...]` fallback paths behind `ENV=test` only.
- FEC/SAM restricted-use flags enforced in compliance module.
- Integration test per connector (fixture + live-safe smoke).

### Module 5 — Entity Resolution
- Jaro-Winkler fuzzy scoring + identifier boost + graph proximity
- Conflict matrix blocking contradictory CIK/EIN/LEI merges
- Graph-neighborhood candidate suggestions
- Merge review UI (queue, side-by-side, approve/reject)
- Full-fidelity unmerge

### Module 6 — Intelligence Graph
- Weighted pathfinding (edge type, evidence confidence, recency)
- Related-party ranking (strength, recency, frequency, amount, centrality)
- Unified timeline from all active connectors
- Interactive graph UI (Cytoscape.js or React Flow)
- Sub-graph export JSON/PNG

### Module 7 — Investor Intelligence
- End-to-end Analyze Stock using **live** SEC + ≥2 other live sources
- Investor memo template with mandatory evidence sections
- Government exposure score
- Catalyst calendar
- Pluggable market data adapter (implement free-tier adapter; document licensed gaps)

### Module 8 — Claude Finance Skills Gateway
- **Live Anthropic adapter** (replace simulated path entirely)
- Skills: comps, DCF, earnings update, one-pager, IC memo, due diligence
- Artifact persistence with content hash
- Per-run cost logging + workspace budget caps
- Review gate before skill output enters published report
- Regression tests for output structure

### Module 9 — Report Generation & Review
- Enforce: `verified` claims require ≥1 EvidenceRef (API + DB constraint)
- Citation verifier v2: stale source + contradiction detection
- Full review workspace UI: section editor, claim cards, comments, diff
- Approval routing by risk tier
- Re-verify all claims on section edit before export
- Exports: **PDF, Word, PowerPoint** + evidence appendix
- Templates: investor intel, long thesis, short thesis, procurement, lobbying, IC memo

### Module 10 — Alerts & Monitoring
- Alert rules on **real connector delta events** (not simulated thresholds)
- Scan job against fresh ingestion window
- Delivery proven E2E: webhook + **SendGrid email** + **Twilio SMS**
- Dedupe, throttle, severity policies
- Alert inbox UI in web

### Module 11 — Storage / Search / Graph Infrastructure
- **Postgres** (not SQLite) for MVP runtime
- S3 evidence vault wired to API
- **Real OpenSearch** via `opensearch-py` (remove stub client)
- Index pipeline: evidence, entities, report sections
- Hybrid search: SQL + OpenSearch
- PM2 or systemd for api + web + worker on EC2
- Cost logging per search, skill run, connector run
- Backup/restore tested once

### Commercial integrations (credentials exist — must wire)
- **Stripe:** payment routes + webhook handler in active paths
- **SendGrid + Twilio:** alert delivery (above)
- **Didit:** webhook + verification lifecycle
- **Twenty CRM:** real sync workflow (not just client stub)
- **OpenAI:** skills fallback path monitored
- **MercadoPago, NFe.io, Focus NFe:** implement adapters if credentials in `.env`; if CNPJ-blocked, document in report with code ready

---

## EXPLICITLY OUT OF SCOPE (DO NOT BUILD)

- Phase 2 global connectors (U.K., EU, Brazil ICIJ, etc.)
- ClickHouse / Iceberg / Neo4j / Snowflake (post-MVP scaling)
- Licensed premium market data (document limitation; ship free-tier adapter)

Everything else in Phase 1 spec is **IN SCOPE**.

---

## IMPLEMENTATION RULES

1. **Read before writing:** `5th_june.md`, `docs/REQUIREMENT_GAP_ANALYSIS.md`, relevant `apps/api/app/api/*.py`, `packages/connectors/us/*/`.
2. **Match existing conventions:** naming, imports, FastAPI patterns, Next.js page structure.
3. **Minimal scope per PR commit** but complete all modules before declaring done.
4. **No hardcoded secrets** anywhere in tracked files.
5. **No sample data in production connector paths** — test fixtures only in `tests/`.
6. **Every new endpoint:** permission check + audit log entry.
7. **Every connector run:** recorded in `source_runs` with metrics.
8. Update `README.md` and `5th_june.md` checkboxes when items complete.

---

## TESTING REQUIREMENTS (MANDATORY)

### Automated tests (must all pass before final commit)

```bash
# Python
source venv/bin/activate
pip install -e apps/api -e packages/finance -e packages/connectors
pytest tests/ -v --tb=short
# Target: ≥80% of API domains have integration tests; all 18 connectors have contract tests

# Web build
cd apps/web && npm install && npm run build

# Admin build
cd apps/admin && npm install && npm run build

# API lint/type check if configured
```

### Test categories to add/expand
- [ ] Health + all API domain integration tests
- [ ] 18 connector contract tests (fixture + live-safe smoke)
- [ ] Tenant isolation / permission boundary tests
- [ ] EvidenceRef enforcement tests
- [ ] Claim lifecycle + export gate tests
- [ ] Alert scan + delivery tests (mock SendGrid/Twilio in CI; live on staging)
- [ ] Skills gateway artifact + cost tests
- [ ] E2E script for 11-step user flow

### Cursor browser verification (MANDATORY)

Use the **Cursor IDE browser MCP** to manually verify the full analyst workflow on staging:

1. `browser_navigate` → `http://184.72.123.188:3003`
2. Verify home, search, stock, graph, skills pages load (no blank screen, no localhost API errors)
3. Run search for `apple` or `PLTR` — results render
4. Open entity profile `/entities/{id}` — timeline and evidence visible
5. Open graph `/graph` — interactive nodes/edges render
6. Run stock analysis `/stock` — live data indicators present
7. Open review workspace `/review/1` — section editor, claims, comments work
8. Trigger skills run `/skills` — live provider response
9. Open portfolio `/portfolio/1` — exposure data
10. Admin `http://184.72.123.188:3002` — source health dashboard shows live connector status
11. API docs `http://184.72.123.188:3001/docs` — all routes respond

**For each failure:** fix code → redeploy/restart services → retest in browser → repeat until all pass.

### API smoke tests (curl)

```bash
curl -s http://184.72.123.188:3001/health
curl -s -X POST http://184.72.123.188:3001/demo/seed
curl -s "http://184.72.123.188:3001/search/?q=apple"
curl -s "http://184.72.123.188:3001/sources/runs"  # or equivalent
# Run connector for SEC and verify source_run success + evidence created
```

---

## DEPLOYMENT ON EC2 (MANDATORY)

After implementation, ensure staging runs the new code:

1. Set `.env` on EC2 with all credentials and `NEXT_PUBLIC_API_URL=http://184.72.123.188:3001`
2. Migrate to Postgres if not already
3. Start/restart with PM2 or systemd:
   - API: `uvicorn app.main:app --host 0.0.0.0 --port 3001` from `apps/api`
   - Web: `npm run dev` or `npm start` from `apps/web` on port **3003**
   - Worker: from `apps/worker`
4. `POST /bootstrap` and all module bootstrap endpoints
5. Run all 18 connector jobs once; verify `source_runs` success
6. Re-run browser verification on EC2 URLs

---

## LAUNCH GATES — DEFINITION OF DONE (ALL MUST PASS)

From `5th_june.md` §7. **You may not declare 100% until every box is checked.**

### Developer success criteria
- [ ] Every normalized entity and edge has ≥1 EvidenceRef
- [ ] Every connector stores raw before parsing
- [ ] Every report claim has evidence, confidence, review status
- [ ] Every expensive workflow has cost budget + caching
- [ ] User-facing conclusions re-verified before export
- [ ] Financial models expose assumptions + sensitivity

### End-to-end demo gate (staging)
1. [ ] Search U.S. public company by ticker
2. [ ] Evidence-backed entity profile + timeline
3. [ ] Stock analysis with live SEC + ≥2 other live sources
4. [ ] Generate investor intelligence report
5. [ ] Edit section, attach evidence, run Claude skill on financial section
6. [ ] Reviewer approves/rejects claims
7. [ ] Export PDF/Word with evidence appendix
8. [ ] Add to watchlist
9. [ ] Real alert on new filing/contract (not simulated)
10. [ ] Alert received via email or webhook

---

## BUG-FIX LOOP (MANDATORY)

```
implement module → write tests → run pytest → fix failures
       ↓
start services → browser verify → fix UI/API bugs
       ↓
deploy EC2 → browser verify staging → fix deployment issues
       ↓
repeat until ALL launch gates pass
```

Do not skip the retest cycle. Log every bug fixed in the completion report.

---

## COMMIT & PUSH (MANDATORY)

- Commit frequently with clear messages (`feat(connectors): production SEC ETL`, etc.)
- Final commits must include:
  - All implementation code
  - All tests
  - Updated `.env.example`
  - Updated `README.md`
  - `PHASE1_MVP_COMPLETION_REPORT.md`
  - **NOT** `.env`, PDFs, or credentials
- Push: `git push -u origin feature/phase1-us-mvp-100pct`
- Create PR to `integration/phase1-mvp-base` via `gh pr create`

---

## FINAL DELIVERABLE — `PHASE1_MVP_COMPLETION_REPORT.md`

Create this file at repo root before your last commit. Structure:

```markdown
# Phase 1 U.S. MVP — Completion Report
Date: [date]
Branch: feature/phase1-us-mvp-100pct
PR URL: [link]

## Executive summary
[1 paragraph: 100% yes/no with evidence]

## Module completion matrix (11 modules)
| Module | Status | Evidence |
|--------|--------|----------|

## Connector status (18 sources)
| Connector | Live ETL | Tests | Smoke result |

## Integration status (all credentials)
| Service | Wired | E2E verified |

## Test results
- pytest: X passed, 0 failed
- web build: pass/fail
- browser E2E: pass/fail (screenshot notes)

## Launch gate checklist
[Every item from §7 with ✅]

## Bugs found and fixed
[List]

## Deployment notes
[EC2 URLs, PM2/systemd, env vars set (names only)]

## Known limitations (if any)
[Must be empty for true 100%; or explain blockers with evidence]

## Sign-off
Phase 1 U.S. MVP: COMPLETE / INCOMPLETE
```

---

## EXECUTION ORDER (RECOMMENDED)

1. Git branches (integration + feature)
2. Secrets → `.env` + `.env.example` + `.gitignore` verify
3. Infrastructure: Postgres + S3 + OpenSearch + PM2
4. Connector framework: checkpoints, DLQ, scheduler, dashboard
5. Connectors P0: SEC → FEC → USAspending → SAM → OFAC
6. Connectors P1: Congress, Federal Register, Regulations, LDA, FARA, CourtListener
7. Connectors P2: remaining 7
8. Evidence enforcement + verifier
9. Entity resolution + graph UX
10. Investor intelligence pipeline
11. Claude skills live adapter
12. Report engine + review UX + exports
13. Alerts on real deltas + SendGrid/Twilio
14. SSO + admin UI + tenant tests
15. Full test suite + browser E2E + EC2 deploy
16. Completion report + PR

---

## START NOW

Begin by reading `5th_june.md` and `INTELIGENCE Platform Credentials.pdf`, then execute the git branch setup. Work autonomously until all launch gates pass. Do not ask for permission between modules. Fix bugs yourself. Retest until green. Commit, push, open PR, and deliver `PHASE1_MVP_COMPLETION_REPORT.md`.

**Success = 100% Phase 1 U.S. MVP with nothing missing, all credentials integrated, all tests green, browser verification passed, code on GitHub.**
