# Phase 1 Readiness

## Setup
- Docker Compose with Postgres, Redis, MinIO, API, Web, Admin, Worker
- Env vars: OPENSEARCH_URL, OPENSEARCH_INDEX, SKILL_ARTIFACT_DIR, EXPORT_DIR

## Architecture
- API services for identity, sources, evidence, entities, search, graph, finance, skills, reports, review, monitor, compliance
- OpenSearch client stub + hybrid DB fallback

## Operator Guide
- Bootstrap endpoints (reports/review/monitor/skills/compliance)
- Index docs: /searchos/index/doc?doc_id=...
- Exports via /review/export/...

## Source Contracts
- See source_contract.yml templates under packages/connectors/us/*

## Release Checklist
- [ ] Run docker compose up --build
- [ ] POST all /bootstrap endpoints
- [ ] Create sample report and run review/export
- [ ] Create watchlist/portfolio, add rules, run scan+deliver
- [ ] Verify /search and /searchos endpoints

## Deferred Items (Phase 2)
- Real OpenSearch integration and ingestion pipeline
- SSO/SAML/OIDC hooks, SCIM provisioning, MFA policies
- Slack/Teams/Email delivery implementations
- Full technical suite and market data providers
- Advanced ranking, contradiction detection, and evidence similarity
- Load/security/tenant isolation test suites
