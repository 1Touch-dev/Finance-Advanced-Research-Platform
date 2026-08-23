# Independent Re-Verification — 2026-08-23

Method: all claims re-checked by booting the app, executing endpoints, running AST
analysis, and doing register→login→write E2E against an isolated DB copy. Documentation
and commit messages were not treated as evidence.

## Part 1 — Previously claimed fixes, re-verified

| # | Claim | Verdict | Evidence |
|---|---|---|---|
| 1 | `load_dotenv(override=False)` | CONFIRMED | `main.py:2` |
| 2 | 266 → 0 blocking async handlers | CONFIRMED | AST: 0. Measured: `/brokerage/brokers` @conc6 **23,843ms → 10.7ms**; `/health/full` 11.2ms; `/legal/types/case-statuses` 147ms |
| 3 | Duplicate `/auth/*` removed from `routes.py` | CONFIRMED | JSON body → **201 + access_token** (was 422) |
| 4 | `/revisions` restored | CONFIRMED (overstated) | **10** paths live, not 12 |
| 5 | NaN coercion in politician search | CONFIRMED | `politician_leaderboard_service.py:244` |
| 6 | `random.uniform` uptime removed | CONFIRMED | zero fabrication in `status.py` |
| 7 | `ticker` param on `/insider/transactions` | CONFIRMED | |
| 8 | Tests collect | CONFIRMED | **1,032** (was 0) |
| 9 | Routers load | CONFIRMED | **0** `router_load_failed` |
| 10 | Real risk metrics | CONFIRMED | `var_95_daily: 39.02` from yfinance; hardcoded `base_vol = 0.18` gone |
| 11 | `/dashboard?user_id=admin` closed | CONFIRMED | now 401 |
| 12 | 5xx cleanup | CONFIRMED | ~23 → 7, of which 2 are honest `501 OIDC not configured` → **5 real** |
| 13 | Frontend auth | CONFIRMED | `login.js` + `lib/auth.js`; **25** files on `apiFetch` |
| 14 | pytest in CI | CONFIRMED | plus `ops > 800` router assertion |

Decisive E2E: `register 201 → login 200 → /auth/me 200 → POST /portfolio 200 →
POST position 200 → GET risk 200 (real VaR)`, persisted
(`users 1, portfolios 1, positions 1, alert_rules 1, audit_logs 1`).
Unauthenticated writes correctly 401. The "persistence is broken" inference was wrong;
"add a login page" was the correct diagnosis and it worked.

Also confirmed the event loop is genuinely unblocked: a 24.5s networked endpoint now runs
alongside trivial ones that stay at 8–10ms.

## Part 2 — New defects found during re-verification, and fixed

### P0-1 — A second duplicate-router shadowing bug (same class as the auth one)

`routes.py:122` registered `POST /workspaces`, shadowing `workspaces.py`. Its dependency
chain reached `rbac/permissions.py:18`:

```python
async def get_current_user(authorization: Optional[str] = None) -> Current:
```

A bare `str` default makes FastAPI declare `authorization` as a **query parameter**. The
header was never read. Measured before the fix:

- `Authorization: Bearer <token>` header → **401 "Missing token"**
- `?authorization=Bearer%20<token>` → **403 "Missing permission"** (i.e. it got through)

OpenAPI confirmed `name='authorization' in='query'`. Two consequences: 6 endpoints
(`/orgs`, `/workspaces`, `/members`, `/projects`, `/cases`, `/audit`) were unreachable via
correct auth, and the only way in put **bearer tokens in URLs**, where every proxy and
access log records them.

Fix: `rbac/permissions.py` now delegates to the canonical header-reading
`app/auth/security.get_current_user` instead of re-implementing it, and the RBAC endpoints
moved to `/rbac/*` so they cannot shadow the service router.

Verified after: `POST /rbac/orgs` with header → 403 (auth read, no grant); without header →
401 `Missing authentication token`; **tokens-in-URL params remaining: 0**.

### P0-2 — Authorization was decorative on 111 endpoints

- 89 took `user_id` with no auth dependency at all
- 22 had `Depends(get_current_user)` but passed the **spoofable query param** to the
  service instead of the token identity

Any logged-in user could act as any other. Fixed by forcing token identity
(`user_id = str(current_user["user_id"])`) on all 22, and adding auth to the **33
unauthenticated mutations** (`pwa_advanced` 10, `comments` 5, `mobile_pwa` 4,
`portfolio_analytics` 3, `billing` 3, `cost_basis` 2, `documents` 2, plus RBAC).

This also fixed a usability bug: `user_id` was `Query(...)` (required), so a correct
authenticated client that omitted it got a 422 — which is exactly what `/alerts` did.

Verified by attacker/victim test: attacker (id=1) posting `?user_id=2` produced a record
owned by **`user_id: "1"`** — token identity wins. Static re-scan:

```
user_id endpoints with no auth dep:  54  (of which MUTATIONS: 0)
auth present but identity from query param:  0
```

The 54 remaining are all reads, left deliberately so this pass could not break the
public/demo surface.

### P0-3 — The third safety net was still broken; CI was green on failure

`ci.yml` ended the pytest step in `| tail -30`, so the step's exit code was **tail's**.
177 failures shipped green. Fixed with `set -o pipefail`.

Separately, the `import random` guard used non-recursive globs
(`app/services/*.py app/api/*.py`) — the same blind spot that let `status.py` ship
fabricated uptime. Now recursive across `services`, `api`, and `connectors`, with
`app/quality/synthetic.py` explicitly excluded (offline training-data generator,
unreachable from any router — verified).

Also removed an unused `import random` from `app/api/experiments.py` that was tripping the
guard.

## Part 3 — Post-fix state

```
router_load_failed:            0
paths / operations:            817 / 860
blocking async handlers:       0
tokens-in-URL params:          0
unauthenticated mutations:     0
identity-from-query-param:     0
tests collected:               1,032
CI random guard:               PASSES
frontend build:                81/81 pages
E2E register→login→write→read: PASS (real VaR from yfinance)
```

## Part 4 — Verified completion

```
                       AUDIT    CLAIMED    VERIFIED (post-P0)
Frontend               ~35%      ~58%       ~50%
Backend                ~55%      ~72%       ~72%
FE↔BE wiring           ~30%      ~60%       ~55%
Core functionality     ~50%      ~68%       ~68%
Production readiness   ~12%      ~50%       ~52%
────────────────────────────────────────────────────
OVERALL                ~38%      ~62-65%    ~62%
```

Backend and production readiness rose because the three P0s were the specific items
holding them down. Frontend stays at ~50%: 25 of ~72 pages use `apiFetch`; the rest still
call `fetch` with no auth header.

## Part 5 — Remaining work

### P1
1. **43 pages still raw-`fetch` with no auth header** — migrate to `apiFetch`. Largest
   single remaining gap and the reason Frontend sits at ~50%.
2. **177 test failures** — now that collection works and CI can no longer hide them, these
   fail the build. Triage: real assertion mismatches vs. network-dependent.
3. **5 real 5xx** — `/ontology/*` (4) and `/searchos/` (1). Note `app/api/searchos.py`
   does not exist; the route is registered from somewhere else and needs tracing.
4. **No Alembic** — schema still via `Base.metadata.create_all`, unversioned.

### P2
5. **16 endpoints >25s** — 60s cases are stacked 30s timeouts with no aggregate budget on
   ontology/filings/litigation fan-out.
6. **FMP 402 / Finnhub 403 fallback unverified** — SEC EDGAR fallback exists but was never
   confirmed to return income statements under real network.
7. **54 reads still accept `user_id`** — no privilege escalation via mutation, but they
   leak per-user data to unauthenticated callers.

### P3
8. `no_data_response` spread overwrites `"reason"` at 72 sites — cosmetic only, since
   `details=` carries the same text. Lower severity than the earlier audit assigned.

## Caveats on these numbers

- The 627-endpoint sweep ran **sandboxed with no external network**, so `EMPTY (253)` and
  `404 (50)` are inflated. 5xx from code bugs are network-independent, so that count holds.
- Provider classifications reflect today's credential state. OpenCorporates, ALEPH,
  OpenSecrets and Senate LDA are **unverified, not broken**.
- **All of this work is uncommitted** across ~85 files. One bad `git checkout` loses it.
