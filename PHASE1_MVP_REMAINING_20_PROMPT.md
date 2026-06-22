# Phase 1 U.S. MVP — Remaining 20% Completion Agent Prompt

**Copy everything below the line into a new Cursor Agent chat. Do not summarize or shorten it.**

---

## YOUR MISSION

You are an autonomous senior full-stack engineer agent. Phase 1 U.S. MVP is **~80% complete** on branch `feature/phase1-us-mvp-100pct` (PR #1 open). Your job is to close the **remaining ~20%** and deliver **100% Phase 1 launch-gate sign-off** — not new features from scratch, but **finish what is already wired**.

Read first: `PHASE1_MVP_COMPLETION_REPORT.md` and `5th_june.md` §7 (launch gates).

You must: **provision infra → configure credentials → migrate DB → seed all connectors on staging → build missing UX → prove launch gates in browser → fix bugs → retest → commit → push → update PR**.

**Do not recreate branches.** Work on the existing feature branch. **Do not claim 100% until every unchecked launch-gate item in the completion report is ✅ with staging evidence.**

---

## CURRENT STATE (DO NOT RE-IMPLEMENT)

### Already done (~80%) — verify, do not rewrite
- 17 U.S. connectors with live API fetches; samples gated to `ENV=test` only
- Production ETL runner: `packages/connectors/runner/run_connector.py`, CLI: `python -m runner.cli`
- DLQ, DB checkpoints, source contracts, admin source-health dashboard
- S3/MinIO vault code, real OpenSearch client (`apps/api/app/services/opensearch_client.py`)
- Anthropic adapter (`anthropic_client.py`), OIDC routes (`auth/oidc.py`), JWT refresh/revocation
- PDF/Word exports, connector-delta alert scan, `/alerts` inbox UI
- **31 pytest tests passing** — must stay green (expand, not break)
- EC2 staging live: Web `:3003`, API `:3001`, Admin `:3002`
- PM2: `finance-api`, `finance-web`, `finance-admin`

### Explicit gaps to close (your work)
| # | Gap | Done when |
|---|-----|-----------|
| 1 | SQLite on staging | API uses Postgres; data migrated; PM2 restarted |
| 2 | MinIO not on EC2 | MinIO running; evidence files in S3 bucket; API reads/writes verified |
| 3 | OpenSearch not on EC2 | OpenSearch running; index pipeline works; `/searchos` returns real hits |
| 4 | `ANTHROPIC_API_KEY` unset | Live Claude skill run succeeds on staging `/skills` |
| 5 | OIDC not configured | Google OAuth login flow works end-to-end |
| 6 | No staging connector seed | All 17 connectors run via runner; `source_runs` success; evidence in DB |
| 7 | Entity merge review UI missing | Web page for `/entities/merge` or queue with approve/reject |
| 8 | Cytoscape/React Flow graph missing | Replace SVG stub in `apps/web/pages/graph.js` with interactive graph |
| 9 | Launch gate 3 partial | Stock analysis uses live SEC + ≥2 other live sources on staging |
| 10 | Launch gates 9–10 partial | Real alert on filing delta + email or webhook delivery proven |
| 11 | MFA policy stub | MFA toggle for admin/reviewer roles (TOTP minimum) |
| 12 | Verifier v2 partial | Stale-source + contradiction detection enforced before export |
| 13 | Legal hold fields pending | Evidence vault retention/legal_hold columns + API |
| 14 | Investor memo pipeline partial | Analyze Stock wires multi-source live data into memo output |
| 15 | Cost caps partial | Workspace skill budget enforced and logged |

---

## REPOSITORY CONTEXT

- **Workspace:** `/home/ubuntu/Finance-Advanced-Research-Platform`
- **Branch (use this):** `feature/phase1-us-mvp-100pct`
- **Base branch for PR:** `integration/phase1-mvp-base`
- **PR:** https://github.com/1Touch-dev/Finance-Advanced-Research-Platform/pull/1
- **Remote:** `https://github.com/1Touch-dev/Finance-Advanced-Research-Platform.git`
- **Staging EC2:** `184.72.123.188` — Web `:3003`, API `:3001`, Admin `:3002`
- **Credentials:** read local `INTELIGENCE Platform Credentials.pdf` + existing `.env` (gitignored)
- **Docker compose:** `docker-compose.yml` has postgres, redis, minio, opensearch services

### Git rules
```bash
git checkout feature/phase1-us-mvp-100pct
git pull origin feature/phase1-us-mvp-100pct
# all commits on this branch; push updates to PR #1
git push origin feature/phase1-us-mvp-100pct
```
**Never commit `.env`, PDFs, or secrets. Never force-push `main`.**

---

## STEP 1 — INFRA ON EC2 (MANDATORY FIRST)

Provision on the EC2 host (not just locally):

```bash
cd /home/ubuntu/Finance-Advanced-Research-Platform
docker compose up -d postgres redis minio opensearch
docker compose ps   # all healthy
```

Update **`.env`** (local file only) with staging values:
```
DATABASE_URL=postgresql+psycopg://user:password@127.0.0.1:5432/mydb
OPENSEARCH_URL=http://127.0.0.1:9200
OPENSEARCH_INDEX=enterprise-docs
S3_ENDPOINT=http://127.0.0.1:9000
S3_BUCKET=enterprise-evidence
S3_ACCESS_KEY=minio
S3_SECRET_KEY=minio123
ENV=staging
NEXT_PUBLIC_API_URL=http://184.72.123.188:3001
REACT_APP_API_URL=http://184.72.123.188:3001
API_URL=http://127.0.0.1:3001
```

Then:
1. Create MinIO bucket `enterprise-evidence` (mc client or API)
2. Bootstrap Postgres: `POST http://127.0.0.1:3001/bootstrap` + all module bootstraps
3. Verify OpenSearch: `curl http://127.0.0.1:9200/_cluster/health`
4. Restart API via PM2 with new env: `pm2 restart finance-api --update-env`
5. Confirm API health: `curl http://184.72.123.188:3001/health`
6. Run migration script if needed (SQLite → Postgres data export) or re-seed demo + connectors

**Done when:** `DATABASE_URL` in running API points to Postgres (verify via logs or `/sources/health`), not SQLite.

---

## STEP 2 — CREDENTIALS (MANDATORY)

From `INTELIGENCE Platform Credentials.pdf`, ensure these are in `.env` and **working on staging**:

| Variable | Verify with |
|----------|-------------|
| `ANTHROPIC_API_KEY` | `POST /skills/run` with `provider=anthropic` → real response |
| `OIDC_CLIENT_ID` + `OIDC_CLIENT_SECRET` | Google Cloud OAuth app; redirect `http://184.72.123.188:3001/auth/oidc/callback` |
| `OPENSEARCH_URL` | Index doc + search returns hits |
| `S3_*` | Upload via `POST /evidence/raw` → file in MinIO bucket |
| All gov API keys | Already set; re-smoke if needed |

If Anthropic or OIDC keys are missing from PDF, document blocker in report — but **attempt** to use keys already in `.env` first.

---

## STEP 3 — STAGING CONNECTOR SEED (ALL 17)

Run every connector against staging API with persistence. Use existing CLI:

```bash
cd packages/connectors
source ../../venv/bin/activate
export API_URL=http://127.0.0.1:3001

# For each connector: register source if needed, create run, execute CLI
CONNECTORS="sec_edgar fec congress_gov sam_gov courtlistener usaspending ofac gleif lda_gov fara govinfo federal_register regulations_gov ecfr reginfo_oira irs_990 opencorporates"

for c in $CONNECTORS; do
  # 1. POST /sources/ to register (or use existing source_id)
  # 2. POST /sources/{id}/runs
  # 3. python -m runner.cli --connector $c --source-id ID --run-id RUN_ID
done
```

**Better:** create `scripts/seed-all-connectors.sh` that automates the above and commit it.

**Done when:**
- 17 `source_runs` with `status=success` in Postgres
- `source_record_meta` rows exist
- `evidence` / `raw_documents` rows exist from runner persist
- Admin dashboard at `:3002` shows all sources green

---

## STEP 4 — OPENSEARCH INDEX PIPELINE

1. Replace any remaining stub behavior in `search_os.py`
2. On connector seed completion, index evidence docs + entity profiles
3. Verify: `GET /searchos?q=apple` returns hits from indexed data
4. Hybrid: SQL `/search/` + OpenSearch `/searchos` both work

---

## STEP 5 — UX GAPS (FRONTEND)

### 5a. Entity merge review UI
- New page: `apps/web/pages/entities/merge.js` (or extend queue)
- Fetch `GET /entities/queue`
- Side-by-side entity comparison, approve/reject merge proposals
- Wire `POST /entities/merge/approve` and reject flow
- Link from Layout nav

### 5b. Interactive graph (Cytoscape.js or React Flow)
- Replace SVG radial layout in `apps/web/pages/graph.js`
- Expand-on-click, zoom/pan, edge labels, evidence tooltips
- Export sub-graph PNG/JSON button

### 5c. Investor memo pipeline
- `/stock` page: after analysis, show sections fed by live SEC + FEC + USAspending (or similar) with EvidenceRef links
- Government exposure score visible on entity profile

---

## STEP 6 — GOVERNANCE COMPLETION

### MFA (Module 1)
- TOTP MFA enrollment for admin/reviewer roles
- Login flow checks MFA when enabled
- API: `POST /auth/mfa/enroll`, `POST /auth/mfa/verify`

### Verifier v2 (Module 9)
- Stale source detection (configurable max age per source type)
- Contradiction flags when two EvidenceRefs conflict
- Block export if unverified high-risk claims remain

### Legal hold (Module 3)
- Add `legal_hold` boolean + `retention_until` on raw documents
- API to set/release hold; block delete when held

### Cost caps (Module 8)
- Workspace-level `skill_budget_usd` setting
- Reject skill runs over budget; log cost per run in DB

---

## STEP 7 — LAUNCH GATES (ALL MUST PASS)

From `PHASE1_MVP_COMPLETION_REPORT.md` — flip every 🟡 and `[ ]` to ✅:

### Developer success criteria
- [ ] Every normalized edge on staging has ≥1 EvidenceRef (after connector seed)
- [ ] (already done items — re-verify after Postgres migration)

### End-to-end demo on staging (prove in browser + curl)

| Step | Action | Pass criteria |
|------|--------|---------------|
| 1 | Search `PLTR` or `apple` | Live results |
| 2 | Entity profile | Timeline shows connector-sourced events, not demo-only |
| 3 | Analyze Stock | Response cites live SEC + ≥2 other sources |
| 4 | Generate investor report | Draft with evidence refs |
| 5 | Edit section + Anthropic skill | Live Claude response in report section |
| 6 | Reviewer approve/reject claim | State transitions in UI |
| 7 | Export PDF + Word | Files download with evidence appendix |
| 8 | Add to watchlist | Persists in Postgres |
| 9 | Trigger real alert | New SEC filing delta detected after connector run |
| 10 | Alert delivery | Email via SendGrid OR webhook POST received |

### OIDC bonus (required for Module 1 100%)
- [ ] Login with Google → JWT issued → web session works

---

## STEP 8 — TESTING (MANDATORY)

```bash
source venv/bin/activate
pytest tests/ -v          # must be ≥31 passed, 0 failed; add new tests for gaps closed
cd apps/web && npm run build
cd apps/admin && npm run build
```

Add tests for:
- Postgres connectivity (integration)
- OpenSearch index/search (mock or live)
- MFA enroll/verify
- Verifier v2 stale/contradiction
- Connector seed script (dry-run mode)

### Cursor browser verification (MANDATORY)

Use Cursor IDE browser MCP on staging:

1. `http://184.72.123.188:3003` — home, search, stock, graph (interactive), skills (Anthropic), alerts, entity merge UI
2. `http://184.72.123.188:3002` — all 17 sources green in health dashboard
3. `http://184.72.123.188:3001/docs` — all routes healthy
4. OIDC login flow if configured

**Fix → redeploy → retest until all pass.**

---

## STEP 9 — DEPLOYMENT HARDENING

1. PM2 ecosystem file with all env vars documented (names only in git)
2. `finance-web`: prefer `npm run build && npm start` on port 3003 for staging stability (or document why dev mode)
3. Worker running connector schedule (cron or Bull repeatable job every N hours)
4. Document backup: `pg_dump` + MinIO bucket sync command in `docs/DEPLOYMENT.md`

---

## STEP 10 — COMMIT, PUSH, UPDATE PR

```bash
git add -A
git status   # confirm NO .env, NO pdf staged
git commit -m "feat: close Phase 1 MVP remaining 20% — infra, seed, UX, launch gates"
git push origin feature/phase1-us-mvp-100pct
```

Update PR #1 description with link to final report.

---

## FINAL DELIVERABLE — UPDATE `PHASE1_MVP_COMPLETION_REPORT.md`

Overwrite/update the report. Change sign-off to:

```markdown
## Sign-off
Phase 1 U.S. MVP: **COMPLETE (100%)**
```

Only if **every** launch gate is ✅ with staging evidence. Include:

- Before/after module matrix (all modules ≥95%)
- Connector seed run IDs and record counts
- OpenSearch index doc count
- MinIO object count
- Postgres table row counts (sources, runs, evidence)
- pytest count (≥31 passed)
- Browser E2E checklist (all ✅)
- OIDC + Anthropic smoke results
- Screenshots notes from browser verification
- Remaining limitations: **must be empty** for true 100%

---

## EXECUTION ORDER

1. `git pull` on `feature/phase1-us-mvp-100pct`
2. Docker: postgres + minio + opensearch on EC2
3. `.env` update + PM2 restart
4. Postgres bootstrap + demo seed
5. `scripts/seed-all-connectors.sh` — run all 17
6. OpenSearch index pipeline
7. Entity merge UI + Cytoscape graph
8. MFA + verifier v2 + legal hold + cost caps
9. Anthropic + OIDC credential verify
10. Launch-gate E2E in browser
11. Tests + fix loop
12. Update completion report → COMPLETE (100%)
13. Commit, push, update PR #1

---

## OUT OF SCOPE (DO NOT BUILD)

- Phase 2 global connectors
- ClickHouse / Iceberg / Neo4j / Snowflake
- MercadoPago / Focus NFe (unless already in `.env` and trivial to wire)
- Licensed premium market data feeds

---

## START NOW

```bash
git checkout feature/phase1-us-mvp-100pct
git pull origin feature/phase1-us-mvp-100pct
cat PHASE1_MVP_COMPLETION_REPORT.md
docker compose up -d postgres minio opensearch
```

Work autonomously until sign-off is **COMPLETE (100%)**. Fix bugs yourself. Retest until green. Do not ask for permission between steps.

**Success = all launch gates ✅, 31+ tests green, staging runs on Postgres+MinIO+OpenSearch, 17 connectors seeded, browser E2E passed, PR #1 updated.**
