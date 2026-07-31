# Changelog

All notable changes to the Finance Advanced Research Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Repository restructured to follow 2026 monorepo best practices
- New shared configuration packages: `@finance-platform/config-typescript` and `@finance-platform/config-eslint`
- New `@finance-platform/shared-types` package for common TypeScript types
- pnpm workspace configuration
- Turborepo configuration for build orchestration
- Root-level TypeScript configuration
- `CONTRIBUTING.md` with contribution guidelines
- `tooling/` directory for development scripts and generators
- Comprehensive documentation reorganization

### Changed
- Documentation now organized in structured subdirectories:
  - `docs/setup/` - Setup and installation guides
  - `docs/architecture/` - Architecture decisions and context
  - `docs/features/` - Feature documentation
  - `docs/api/` - API integration guides
  - `docs/deployment/` - Deployment documentation
  - `docs/handoff/` - Team handoff documents
  - `docs/requirements/` - Requirements and specifications
  - `docs/archive/` - Historical logs and reports
- Moved scripts from root to `tooling/scripts/`
- Moved memory bank contents to `docs/architecture/`
- Archived sprint logs to `docs/archive/sprints/`
- Archived verification reports to `docs/archive/verification/`
- Archived agent prompts to `docs/archive/prompts/`

### Removed
- Redundant root-level documentation files (consolidated into docs/)
- Empty `Task/` and `memory/` directories after reorganization

## [2.0.0] - 2026-07-29

### Added
- Trade Alerts (F-03): Big trade detection with email/SMS notifications
- Investment Alerts (F-04): Per-watchlist threshold monitoring
- PM2 automated scanners running every 4 hours
- Alert rules CRUD API
- Watchlist threshold configuration per ticker

### Previous Features
For complete feature history, see:
- [docs/handoff/Finance_Platform_Handoff.md](docs/handoff/Finance_Platform_Handoff.md)
- [docs/archive/sprints/](docs/archive/sprints/)

---

## Version History Notes

This CHANGELOG was created on 2026-07-29 as part of the repository restructure. Previous changes are documented in:
- Sprint logs: `docs/archive/sprints/`
- Completion reports: `docs/archive/verification/`
- Handoff documents: `docs/handoff/`
