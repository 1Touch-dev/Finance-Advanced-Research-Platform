# Program Documentation — Finance Intelligence Platform

Created 19 Aug 2026 from `JAMES_ASKS.txt` (60 CEO messages, 21 Jul → 18 Aug) reconciled against the
actual codebase. Six documents, each with one job.

| # | Document | Audience | Read it when |
|:--:|---|---|---|
| 01 | [CEO One-Pager](01-CEO-ONE-PAGER.md) | **James** | Send as-is. Nothing else goes to him. |
| 02 | [Program Plan](02-PROGRAM-PLAN.md) | TL + devs | Daily execution. Sprints, lanes, hours, gates. |
| 03 | [CEO Operating Manual](03-CEO-OPERATING-MANUAL.md) | **TL only** | Before replying to James. **Never send.** |
| 04 | [Verification & Audit Playbook](04-VERIFICATION-AUDIT-PLAYBOOK.md) | TL + devs | Before shipping anything a customer reads. |
| 05 | [Source Depth Register](05-SOURCE-DEPTH-REGISTER.md) | Dev-1 | Sprint 1 primary work item. |
| 06 | [Decision Log & Risks](06-DECISION-LOG.md) | TL + James | When blocked, or when scope is contested. |

---

## The thesis in five lines

```
   FOLLOW    the money, people and entities
   DEEPEN    recurse into every entity discovered      ← needs a graph. We have none.
   CORRELATE find what no single database shows        ← needs base-rate correction
   PROVE     evidence + date + confidence on every claim  ← the insert. The moat.
   SHOW      a picture he can forward
```

## The three findings that shaped the plan

1. **`MASTER_TASK_STATUS.md` says 78/72 features done (108%). 40 of 89 services contain mock or
   synthetic data paths.** Feature-rich, evidence-poor. That metric is
   [retired](06-DECISION-LOG.md#d5).
2. **Nine services describe a relationship graph. None of them store one.** `correlation_service`,
   `cooccurrence_service`, `coinvestment_network_service`, `recursive_entity_service`,
   `founder_correlations_service`, `entity_network_connector` and three more each build ad-hoc
   adjacency in memory and discard it. This is why depth cannot increase — there is nothing to
   recurse into. Sprint 3 builds it.
3. **The top 10 sources extract under a third of their available fields.** DEF 14A Item 404 —
   legally-mandated related-party disclosure — answers a question James has asked four times, and we
   do not parse it. Full triage in the [register](05-SOURCE-DEPTH-REGISTER.md).

## Start here

- **Today's actions:** [plan §9](02-PROGRAM-PLAN.md#9-do-this-today-wed-19-aug)
- **What to send James:** [01](01-CEO-ONE-PAGER.md), plus the four decisions with dates
- **Before you reply to any of his messages:** [manual §9 pocket card](03-CEO-OPERATING-MANUAL.md#9-pocket-card)

## Cleanup suggested

Root and `docs/` have accumulated overlapping status files. Recommend consolidating:

| File | Action |
|---|---|
| `MASTER_TASK_STATUS.md` (root, 977 lines) | Add correction banner re: the 108% claim, then supersede with `02-PROGRAM-PLAN.md`. Keep as historical record. |
| `JAMES_ASKS.txt` (root, 1058 lines) | Move to `docs/program/` — it is the source corpus for these docs and should not sit in the repo root. |
| `docs/reports/PHASE1_*`, `PHASE2_*` (8 files) | Archive to `docs/reports/archive/` — superseded. |
| `docs/architecture/RESTRUCTURE_*`, `BEFORE_AFTER_COMPARISON.md` | Archive — completed work. |
| `docs/tasks/16th_July_Status_and_Scope.md` | Archive — superseded. |
| `docs/US Government Officials — Stock Trading Rankings.xlsx` | Keep. Active input to sprint 1. |
