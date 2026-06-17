# Project Context

This document provides the context for the Enterprise Intelligence and Investment Research Platform.

## Overview

The platform provides **evidence-first** public-record intelligence, investor research, relationship graphs, report generation, and monitoring. It is not a stock screener or generic LLM tool — it combines market/financial analysis with U.S. public records (SEC, lobbying, procurement, litigation, sanctions, state registries, and more).

## Goals

- Multi-tenant enterprise workspace with RBAC and audit
- Evidence-first architecture — every claim traceable to sources
- **Layer 1 Entity Network Intelligence Reports** — cited dossiers from live federal sources + AI narrative
- U.S. 50-state company registry (51 jurisdictions)
- Relationship graph intelligence
- Investor workflows (DCF, comps, stock analysis)
- Watchlists, portfolios, alerts

## Stakeholders

- James Thunder Marketing (client)
- Investors, analysts, enterprise clients

## Current State (17 June 2026)

| Phase | Status |
|-------|--------|
| **Phase 1 U.S. MVP** | ~95% — core platform operational on staging |
| **Phase 2 Registry** | Complete — 51 jurisdictions, BEA, BizFile CA scrape |
| **Phase 3 Layer 1** | **v1.1 shipped** — 9-section dossiers, LDA fix, PayPal Mafia, deep narrative |

**Staging:** http://184.72.123.188:3003 · Intelligence: http://184.72.123.188:3003/intelligence

**Active workstream:** Layer 1 v2 — multi-node PayPal Mafia graph, PDF export, PitchBook/PDL integration (pending James), ownership trees

**Deferred:** CA SOS API key, Cobalt upgrade (per client direction)

**Branch:** `feature/us-50-state-registry-api` · PR #2

**Latest handoff:** [17th_June.md](../17th_June.md)
