# Requirement vs Repo Gap Analysis

## Context
This document compares your target specification ("Enterprise Intelligence & Investment Research Platform") against the current implementation in this repository.

Assessment date: 2026-05-28  
Scope reviewed: `apps/api`, `apps/web`, `apps/admin`, `apps/worker`, `packages/connectors`, `packages/finance`, `tests`, `docs`.

---

## Current Standing (High Level)

The repo is a **working Phase-1 foundation** with core scaffolding in place:

- monorepo app structure is present and runnable
- many API domains exist (identity, evidence, entities, graph, search, reports, review, compliance, monitor, skills, finance)
- connectors package exists with source contracts and connector skeletons
- basic web/admin UIs are available
- monitoring/watchlist/portfolio endpoints exist

But the project is still **early implementation**, not yet a full enterprise-grade research platform.

Main reason: many critical modules are implemented as stubs/skeletons, and enterprise-grade controls, data quality, verification depth, and end-to-end production workflows are still incomplete.

---

## Module-by-Module Status

Legend:
- `Done (Foundation)` = basic functionality exists
- `Partial` = meaningful implementation exists but not production-complete
- `Not Started` = no real implementation yet

### 1) Enterprise Workspace & Identity
Status: `Partial`

What exists:
- org/workspace/user/auth basics (`/auth/register`, `/auth/login`, `/orgs`, `/workspaces`)
- role and permission seed logic
- project/case creation
- audit log endpoint

Gaps:
- no SSO/OIDC/SAML
- no SCIM provisioning
- no MFA policy
- no robust tenant isolation verification tests
- no hardened session/token lifecycle (rotation, revocation, etc.)

### 2) Source Registry & Connector Framework
Status: `Partial`

What exists:
- source registry APIs (`/sources/*`)
- source runs and status tracking
- source contract model + sample YAML contracts
- connector SDK (rate limit, retry, checkpoint primitives)

Gaps:
- connector execution path is mostly placeholder
- limited real ingestion with durable checkpoints
- no robust retry/dead-letter/ops dashboard
- weak data quality metrics and SLA observability

### 3) Evidence Vault
Status: `Done (Foundation) / Partial`

What exists:
- raw upload endpoint (`/evidence/raw`)
- hash + storage path persistence
- EvidenceRef creation and retrieval

Gaps:
- no document viewer with span highlighting
- no immutable retention/legal-hold controls
- no deep citation quality checks across report sections
- no full provenance chain enforcement per claim

### 4) U.S. Source Connectors
Status: `Partial`

What exists:
- connector modules for many U.S. domains (SEC, OFAC, FARA, GLEIF, CourtListener, etc.)
- basic tests for connector skeleton behavior

Gaps:
- many connectors are fixture/sample based, not full production ETL
- missing robust normalization mappings per source
- missing end-to-end "discover -> fetch -> raw persist -> normalize -> evidence refs -> relationships" at production depth

### 5) Entity Resolution
Status: `Partial`

What exists:
- entity, alias, identifier models/APIs
- deterministic identifier match
- fuzzy name resolution
- merge proposal/approve/unmerge endpoints
- resolution queue

Gaps:
- simplistic scoring and merge safety logic
- no advanced conflict policies (cross-id contradiction matrices)
- no analyst-grade merge review UX
- weak reversal fidelity (unmerge is currently naive)

### 6) Intelligence Graph
Status: `Partial`

What exists:
- graph expand/path/related endpoints
- relationship evidence linking endpoint

Gaps:
- graph queries are still basic
- no robust timeline semantics
- no mature graph visualization UX
- no weighted traversal/trust-aware scoring pipeline

### 7) Investor Intelligence
Status: `Partial`

What exists:
- finance APIs: analyze stock, DCF, reverse DCF, comps, fundamentals
- finance package with core computations

Gaps:
- no full investor memo pipeline with complete sectioning and evidence traceability
- no complete market data provider abstraction layer with production adapters
- limited advanced analytics coverage

### 8) Finance Skills Gateway
Status: `Partial`

What exists:
- skills registry and run APIs
- provider field with "anthropic/internal" routing concept
- artifact storage for runs

Gaps:
- anthropic path is simulated, not live provider integration
- no strict provider-agnostic contract enforcement across adapters
- no strong cost accounting/quotas/policies per run

### 9) Report Generation & Review
Status: `Partial`

What exists:
- report/section/bundle/claim models and APIs
- claim-evidence linking
- basic claim verification states
- comments/suggestions/version diff
- export stubs (markdown/html/json/csv)

Gaps:
- verifier is still simplistic
- no rich editor workflow in frontend
- no robust contradiction analysis
- no full approval gates + policy routing for sensitive outputs

### 10) Alerts, Monitoring, Portfolios
Status: `Partial`

What exists:
- watchlists CRUD basics
- portfolio positions + CSV import + exposure endpoint
- alert rules/channels
- scan/deliver flow (with webhook + stubs)

Gaps:
- alerting logic mostly simulated thresholds
- delivery channels (email/slack/teams) are stubs
- no advanced portfolio risk/factor/regulatory exposure engine

### 11) Compliance & Governance
Status: `Partial (early)`

What exists:
- policy records
- export approval request/approve endpoints

Gaps:
- no field-level restriction enforcement pipeline
- no legal hold/retention enforcement
- no full reviewer policy workflow by risk tier

### 12) Search & Retrieval
Status: `Partial`

What exists:
- SQL-based search endpoints
- OpenSearch endpoint stubs (`/searchos`)

Gaps:
- limited ranking quality and hybrid retrieval sophistication
- no robust indexing pipeline + relevance tuning
- no vector/hybrid evidence ranking

### 13) Frontend UX (Web + Admin)
Status: `Partial`

What exists:
- web routes exist (`/search`, `/graph`, `/stock`, `/skills`, etc.)
- admin shell exists with API health check

Gaps:
- still mostly thin pages; no full analyst workbench
- no complete review workspace UX
- no complete case/project collaboration UX

### 14) Testing & Reliability
Status: `Partial (low maturity)`

What exists:
- minimal test scaffolding + some connector tests

Gaps:
- very limited integration/E2E coverage
- no serious load/security/permission boundary testing
- no migration strategy hardening and data lifecycle tests

---

## Where We Stand Against Your 15-Issue Plan

Approximate progress:

- **Foundation + module scaffolding:** largely done
- **Production-depth implementation:** not done yet

Practical estimate: **~35-45% complete** against the full product intent in your handbook.

Reason for this estimate:
- breadth of modules is good
- depth, hardening, and enterprise-grade controls are still pending

---

## Highest Priority Next Work (Recommended Order)

1. **Harden evidence and claims pipeline**
   - strict claim-evidence requirements
   - stronger verifier + contradiction logic
   - provenance integrity checks

2. **Upgrade entity resolution and merge safety**
   - better confidence model
   - conflict blocking rules
   - reversible merge history with full fidelity

3. **Productionize top connectors (P0 first)**
   - SEC, FEC, LDA, Congress, Federal Register, USAspending, OpenCorporates, GLEIF, OFAC/OpenSanctions
   - real checkpointed ingestion + quality metrics

4. **Implement real review workspace UX**
   - section editing, claim status overlays, reviewer queues, approvals

5. **Strengthen compliance/export policy enforcement**
   - risk-tiered approvals
   - export policy checks
   - audit completeness

6. **Search and graph quality pass**
   - ranking improvements
   - graph relevance scoring
   - better timeline and relationship evidence UX

7. **Testing hardening**
   - API integration suite
   - permission boundary tests
   - connector contract tests
   - E2E user workflows

---

## Suggested Immediate Sprint Plan (Next 2-3 Sprints)

### Sprint A (Evidence + Claims + Review Core)
- enhance claim verifier
- enforce evidence-required state transitions
- add review gate checks before export
- add integration tests for claim lifecycle

### Sprint B (Connector Depth + Entity Resolution)
- productionize 2-3 highest-value connectors (SEC, USAspending, OFAC)
- improve deterministic + fuzzy resolution scoring
- implement safe merge conflict rules + full unmerge restore logic

### Sprint C (Analyst UX + Compliance)
- build review workspace pages in web/admin
- add export approval UI and compliance checks
- ship end-to-end report flow with evidence appendix

---

## Bottom Line

You already have a strong base architecture and broad module coverage.  
To match the full handbook vision, the next phase is about **depth and hardening**:

- make ingestion real
- make evidence/claims rigorous
- make review/compliance enforceable
- make workflows complete end-to-end
- add serious test coverage

That is the path from "good prototype foundation" to "enterprise-ready intelligence platform."

