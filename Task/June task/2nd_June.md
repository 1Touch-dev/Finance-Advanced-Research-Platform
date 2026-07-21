# 2nd June Master Plan - Path to 100% Requirements Completion

This document is the implementation master checklist to take the platform from current Phase 1 state to full completion against:
- `Enterprise Intelligence Development Plan.pdf`
- `Enterprise Intelligence Scaling Plan.pdf`
- `INTELIGENCE Platform Credentials.pdf`

It defines:
1) what the system is,  
2) what full requirements are,  
3) current status, and  
4) every major item needed to reach 100%.

---

## 1) What The System Is

The system is an enterprise, multi-tenant, evidence-first intelligence and investment research platform.

Core purpose:
- Accept an input entity (company, ticker, person, fund, agency, bill, regulation, contract, docket, portfolio, etc.).
- Ingest and normalize market data + public records from official sources.
- Build evidence-linked entity/relationship graph and timeline intelligence.
- Run investor and diligence analysis workflows (including finance skills).
- Generate editable reports with claim-level evidence, review, approval, and export.
- Support watchlists and alerts for new events (filings, contracts, lobbying, regulations, legal, sanctions, market events).

---

## 2) Full Requirement Baseline (Target 100%)

The documents define the target as:

### A. Platform and Architecture
- Multi-tenant enterprise workspace with strict tenant isolation.
- Evidence-first architecture with immutable raw storage and EvidenceRefs for claims/relationships.
- Hybrid storage model: operational DB + object store + lake/lakehouse + search + graph + analytics.
- Cost-aware scaling controls, budgets, and workload tiering.

### B. Core Product Capabilities
- Global entity resolution and identifiers (CIK, LEI, ticker, etc.).
- Relationship graph, related-party discovery, and timeline events.
- Investor workflows: stock analysis, valuation, DCF, comps, technicals, catalysts, risks.
- Public records intelligence across priority sources.
- Report engine: templates, claims, citation verification, review workspace, approvals, exports.
- Alerting: watchlists + triggers + delivery channels.

### C. Connectors and Data Sources
- P0/P1 connectors with standard source contracts.
- Official APIs first, with proper raw persistence, normalization, idempotency, quality checks.
- Source-run monitoring, retries, freshness, and error handling.

### D. Finance Skills
- Provider-agnostic finance skills gateway.
- Claude/integrated skill runs + internal fallback.
- SkillRun artifact, versioning, cost logging, review gates.

### E. Security, Compliance, Governance
- SSO/OIDC/SAML, MFA, enterprise auth controls.
- RBAC + ABAC + auditing + export policy gates.
- Restricted-use data enforcement (e.g., FEC/SAM/licensed sources).
- Human review for sensitive outputs.

### F. Reliability and Readiness
- Integration/e2e/security/load tests.
- Launch gates for security, evidence quality, reliability, compliance, and user workflow completion.

---

## 3) Current Status (Reality Check)

### What exists today
- Monorepo with `apps/api`, `apps/web`, `apps/admin`, `apps/worker`, `packages/connectors`, `packages/finance`.
- Broad API route coverage for core modules (search, entities, graph, finance, sources, reports, review, monitor, compliance, skills).
- Basic report/evidence/claims data model and bootstrap flow.
- Connector framework and source contracts structure present.
- Some service clients implemented (OpenAI, Stripe, SendGrid, Twilio, Didit, Twenty).

### Major current gaps
- Many connectors are sample/fallback/stub and not production ETL depth.
- OpenSearch integration is still stub-level.
- Review/verification/approval workflow is baseline, not enterprise-grade.
- SSO/SCIM/MFA and ABAC hardening not complete.
- Testing depth is low (limited integration/e2e/load/security coverage).
- Not all credentials are present/usable; some integrations are implemented in code but not wired end-to-end.

Estimated status against full documents: foundation complete, production depth incomplete.

---

## 4) Credentials and API Completion Matrix (What Must Be True for 100%)

For each integration, 100% means all three are true:
1. Credential present and valid.
2. Real code path is wired into workflows.
3. End-to-end tests and monitoring prove it works.

### Required completion states
- OpenAI/skills provider: fully wired, monitored, budgeted, with fallback strategy.
- Government connectors (Congress, FEC, Regulations, SAM, CourtListener, SEC, etc.): production ingestion, not sample fallback.
- Notifications (SendGrid/Twilio): successful delivery in real workflow.
- Payments/fiscal/KYC/CRM (Stripe, MercadoPago, NFe, FocusNFe, Didit, Twenty): implemented where in scope, tested and monitored.

### Immediate credential governance requirement
- Remove credential leakage risk from repo and documents.
- Rotate exposed keys and move all secrets to secure secret management.
- Ensure no hardcoded secrets in tracked files.

---

## 5) Work Required to Reach 100% (Master Checklist)

## Phase 0 - Security and Secret Hygiene (Blocker)
- [ ] Rotate all potentially exposed API keys/tokens.
- [ ] Remove secrets from repository history and tracked files.
- [ ] Move all runtime secrets to managed secret store.
- [ ] Add pre-commit and CI secret scanning.
- [ ] Add environment-specific secret policy and access controls.

## Phase 1 - Data and Connector Productionization
- [ ] Convert P0 connectors from sample/fallback to real ingestion jobs.
- [ ] Enforce connector contract: discover -> fetch -> raw persist -> normalize -> EvidenceRef link -> publish events.
- [ ] Add idempotency keys, stable source IDs, checkpoint cursors, retries, dead-letter handling.
- [ ] Add source freshness, error-rate, and run metrics dashboards.
- [ ] Add source-specific integration tests with fixture + live-safe checks.

## Phase 2 - Evidence, Claims, and Report Integrity
- [ ] Enforce strict rule: every factual claim must have EvidenceRef (or explicit assumption label).
- [ ] Upgrade citation verifier for contradiction detection and stale-source detection.
- [ ] Implement full claim lifecycle and reviewer gates for high-risk content.
- [ ] Ensure report edits trigger re-verification and state transitions.
- [ ] Add complete evidence appendix generation for exports.

## Phase 3 - Search, Graph, and Retrieval Quality
- [ ] Replace OpenSearch stub with real index/read/write integration.
- [ ] Build hybrid retrieval (lexical + semantic + rerank) for evidence/report search.
- [ ] Improve graph pathfinding quality and confidence scoring.
- [ ] Add timeline completeness and entity-resolution confidence workflows.

## Phase 4 - Finance and Skills Completion
- [ ] Finish provider-agnostic `FinanceSkillsGateway` contract and adapters.
- [ ] Implement/verify core skills: comps, DCF, earnings, initiating coverage.
- [ ] Persist skill input/output artifacts, hashes, cost, review status.
- [ ] Add governance around skill usage, version pinning, and human approval.
- [ ] Add workflow-level regression tests for finance outputs.

## Phase 5 - Enterprise Auth, Compliance, and Governance
- [ ] Implement SSO (OIDC/SAML) and optional SCIM provisioning.
- [ ] Implement MFA/session policies and stronger token lifecycle controls.
- [ ] Complete RBAC + ABAC enforcement across all sensitive actions.
- [ ] Complete export approval policy enforcement and audit trails.
- [ ] Implement restricted-use data controls and source-license constraints.

## Phase 6 - Alerts, Delivery, and Monitoring
- [ ] Upgrade alert scan logic from baseline simulation to real source-change intelligence.
- [ ] Fully implement and test email/SMS/Slack/Teams/webhook channels as in-scope.
- [ ] Add dedupe/throttling/severity logic with policy controls.
- [ ] Add tenant/workspace observability for alert failures and delays.

## Phase 7 - Frontend Completion (Analyst + Reviewer UX)
- [ ] Build full Review Workspace UI (section editing, comments, claim cards, suggestion diff).
- [ ] Add inline evidence sidebar and claim verification feedback in UI.
- [ ] Add workflow UX for approval routing and compliance review.
- [ ] Add robust exports UX (PDF/Word/PPT/Excel/HTML/JSON + evidence appendix).
- [ ] Harden web/admin role-based experience and access boundaries.

## Phase 8 - Infrastructure, Scaling, and Cost Controls
- [ ] Move core operational DB to managed Postgres for production.
- [ ] Implement object storage evidence vault with immutable paths and lifecycle tiers.
- [ ] Add lake/lakehouse strategy for high-volume sources.
- [ ] Add cost attribution and guardrails (API, compute, storage, LLM, search).
- [ ] Add reliability controls: backup/restore drills, SLOs, autoscaling policies.

## Phase 9 - Testing and Launch Gates
- [ ] Build comprehensive unit/integration/e2e test matrix.
- [ ] Add performance/load tests for ingestion, search, report generation, alerts.
- [ ] Add security test suite and tenant-isolation verification.
- [ ] Verify full end-to-end demo scenario from search -> analyze -> report -> review -> approve -> export -> watchlist.
- [ ] Pass launch gates from documents before enterprise launch.

---

## 6) API and Credential-Specific To-Do List

## Must complete (high priority)
- [ ] SEC connector: replace sample path with production ingestion and parsing.
- [ ] FEC connector: production ingestion + restricted-use policy enforcement.
- [ ] LDA, Congress, Federal Register, USAspending, SAM, CourtListener, OFAC/OpenSanctions: full production ETL depth.
- [ ] Regulations, eCFR, RegInfo/OIRA, IRS 990, FARA: complete production integrations.
- [ ] OpenSearch: full indexing and query integration (remove stub behavior).

## Commercial/operational integrations
- [ ] Stripe: confirm end-to-end payment flow routes and webhook handling in active app paths.
- [ ] MercadoPago: complete credential setup and implementation if in product scope.
- [ ] NFe.io and FocusNFe: implement real service adapters if fiscal scope is active.
- [ ] SendGrid and Twilio: harden auth, delivery, retry, and failure observability.
- [ ] Didit: complete webhook and verification lifecycle integration.
- [ ] Twenty CRM: complete full API key setup and real sync workflows.

---

## 7) Definition of Done for "100%"

We are at 100% only when all are true:
- Every required feature in the two plan PDFs is implemented and validated.
- Every in-scope API integration is live, tested, and monitored.
- Every required credential is securely managed, not exposed, and operational.
- Evidence-first and claim-verification governance is enforced everywhere.
- Enterprise security/compliance controls pass validation.
- End-to-end workflows and launch-gate checks pass in CI and staging.

---

## 8) Execution Order Recommendation

Recommended sequence for future work:
1. Security/credential hygiene (Phase 0)  
2. Connector and evidence productionization (Phases 1-2)  
3. Search/graph + finance skill depth (Phases 3-4)  
4. Enterprise governance and review UX (Phases 5-7)  
5. Infra scaling and full test/launch gate completion (Phases 8-9)

This ordering minimizes risk and prevents building on insecure or non-authoritative data flows.
