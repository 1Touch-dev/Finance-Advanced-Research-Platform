# Repository Restructure Plan - 2026 Best Practices

## Executive Summary
Reorganizing the Finance Advanced Research Platform repository to align with 2026 monorepo best practices while maintaining all functionality and improving developer experience.

## Current Issues
1. **Root-level clutter**: 27 files at root (should be ~8)
2. **Scattered documentation**: Docs in root, /docs, /memory, /Task
3. **Unclear organization**: memory/ and Task/ folders lack clear purpose
4. **No shared config packages**: Missing centralized ESLint/TS configs

## Target Structure (2026 Standard)

```
Finance-Advanced-Research-Platform/
├── apps/                          # Deployable applications
│   ├── api/                       # FastAPI backend
│   ├── web/                       # Next.js frontend
│   ├── admin/                     # React admin panel
│   └── worker/                    # Background jobs
│
├── packages/                      # Shared libraries
│   ├── finance/                   # Financial calculations
│   ├── connectors/                # Data connectors (17 federal + 51 state)
│   ├── config-typescript/         # NEW: Shared TS config
│   ├── config-eslint/             # NEW: Shared ESLint config
│   └── shared-types/              # NEW: Shared TypeScript types
│
├── tooling/                       # NEW: Development tools
│   └── scripts/                   # Build/deploy scripts (moved from root)
│
├── docs/                          # All documentation (reorganized)
│   ├── setup/                     # Setup guides
│   ├── architecture/              # Architecture decisions & diagrams
│   ├── features/                  # Feature documentation
│   ├── api/                       # API documentation
│   ├── deployment/                # Deployment guides
│   ├── handoff/                   # Team handoff documents
│   └── archive/                   # Historical logs and reports
│       ├── sprints/               # Daily task logs (from Task/)
│       ├── verification/          # Verification reports
│       └── prompts/               # Agent prompts
│
├── .github/                       # NEW: CI/CD workflows
│   └── workflows/
│
├── README.md                      # Main readme (cleaned up)
├── CONTRIBUTING.md                # NEW: Contribution guidelines
├── CHANGELOG.md                   # NEW: Version history
├── package.json                   # Root workspace config
├── pnpm-workspace.yaml            # NEW: pnpm workspaces
├── turbo.json                     # NEW: Turborepo config
├── tsconfig.json                  # Root TypeScript config
├── .env.example                   # Environment template
├── .gitignore                     # Git ignore
├── docker-compose.yml             # Docker setup
├── ecosystem.config.js            # PM2 config
└── amplify.yml                    # AWS Amplify config
```

## File Reorganization Map

### Root Level - Keep Only Essential Files (8 core files)
**KEEP:**
- README.md (updated with new structure)
- CONTRIBUTING.md (new)
- CHANGELOG.md (new)
- package.json
- .env, .env.example
- .gitignore
- .dockerignore
- docker-compose.yml
- ecosystem.config.js
- amplify.yml
- tsconfig.json (new - root config)
- pnpm-workspace.yaml (new)
- turbo.json (new - optional)

**MOVE:**

1. **Documentation Files → docs/**
   - Finance_Platform_Handoff.md → docs/handoff/Finance_Platform_Handoff.md
   - SETUP.md → docs/setup/SETUP.md
   - james_requirements.md → docs/requirements/james_requirements.md
   - PROJECT_DEEP_ANALYSIS.md → docs/architecture/PROJECT_DEEP_ANALYSIS.md
   - 5th_July.md → docs/archive/sprints/5th_July.md

2. **Verification Reports → docs/archive/verification/**
   - E2E_LIVE_VERIFICATION_REPORT.md
   - JAMES_REQUIREMENTS_VERIFICATION_REPORT.md
   - PHASE1_E2E_VERIFICATION_REPORT.md
   - PHASE1_MVP_COMPLETION_REPORT.md
   - PHASE2_COMPLETION_REPORT.md

3. **Agent Prompts → docs/archive/prompts/**
   - E2E_LIVE_TEST_AGENT_PROMPT.md
   - PHASE1_MVP_AGENT_PROMPT.md
   - PHASE1_MVP_REMAINING_20_PROMPT.md
   - PHASE2_50_STATE_REGISTRY_AGENT_PROMPT.md

4. **Scripts → tooling/scripts/**
   - All files from /scripts directory

5. **Memory → docs/architecture/**
   - memory/architecture.md → docs/architecture/decisions.md
   - memory/project_context.md → docs/architecture/context.md
   - memory/progress.md → docs/architecture/progress.md
   - memory/decisions.md → docs/architecture/technical_decisions.md
   - memory/2nd_June.md → docs/archive/sprints/2nd_June.md

6. **Task Logs → docs/archive/sprints/**
   - Task/June task/*.md → docs/archive/sprints/june/*.md

7. **Word Documents → docs/requirements/**
   - Enterprise Intelligence Platform v2.0 Requirements.docx
   - Jarvis Nexus Dashboard UI Spec (2).docx

8. **Scripts → tooling/scripts/**
   - gen_md.py

### New Directories to Create

1. **packages/config-typescript/**
   - Base TypeScript configurations for all apps

2. **packages/config-eslint/**
   - Shared ESLint rules

3. **packages/shared-types/**
   - Common TypeScript types/interfaces

4. **tooling/**
   - scripts/ (moved from root)
   - generators/ (for future code generation)

5. **.github/workflows/**
   - CI/CD pipeline definitions

## Benefits of New Structure

### 1. Clarity
- Clear separation: deployables vs libraries vs tools vs docs
- Obvious where to find things
- New developers onboard faster

### 2. Scalability
- Easy to add new apps without cluttering root
- Shared packages prevent code duplication
- Tooling isolated from application code

### 3. Modern Standards
- Aligns with Turborepo/Nx best practices
- Follows 2026 monorepo conventions
- Industry-standard naming

### 4. Maintainability
- Documentation organized by purpose
- Historical artifacts archived but accessible
- Clean git history

### 5. Developer Experience
- Less cognitive load navigating repo
- Consistent patterns across packages
- Better IDE support with proper tsconfig paths

## Implementation Steps

### Phase 1: Create New Structure (No Breaking Changes)
1. Create new directories
2. Create new config packages
3. Set up workspace configuration

### Phase 2: Move Documentation
1. Move all .md files to appropriate docs/ subdirectories
2. Move Word docs to docs/requirements/
3. Archive Task/ folder contents

### Phase 3: Move Code Assets
1. Move scripts/ to tooling/scripts/
2. Move memory/ contents to docs/architecture/

### Phase 4: Update References
1. Update README.md with new structure
2. Update import paths if needed
3. Update documentation links
4. Update ecosystem.config.js paths if needed

### Phase 5: Cleanup
1. Remove empty directories
2. Update .gitignore
3. Test all services still work
4. Create CHANGELOG.md documenting restructure

## Breaking Changes: NONE
- All application code stays in apps/ and packages/
- All services continue to run from same locations
- Only documentation and tooling moves
- No import path changes needed

## Migration Safety
- Git preserves file history with moves
- Can revert at any time
- No code logic changes
- Services remain operational throughout

## Post-Restructure Tasks
1. Update team documentation
2. Communicate changes to team members
3. Update CI/CD if it references old paths
4. Update any deployment scripts

## Success Metrics
- Root directory: 27 files → 13 files (52% reduction)
- Clear documentation hierarchy
- All services run without modification
- Team approves new structure
- Faster onboarding for new developers

---

**Status:** Ready for implementation
**Estimated Time:** 30-45 minutes
**Risk Level:** Low (documentation-only changes)
**Rollback Plan:** Git revert
