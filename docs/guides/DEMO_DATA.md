# Demo Data

Use this to quickly populate local data and preview UI/API behavior.

## Seed

```powershell
curl.exe -X POST http://127.0.0.1:3001/demo/seed
```

The endpoint is idempotent (safe to run multiple times).

## What gets created

- demo organization/workspace/project/case
- entities: Apple, Microsoft, DoD, Tim Cook
- relationships with evidence refs
- one stock analysis report with sections, claim, and evidence bundle
- one watchlist with items
- one portfolio with positions and alert rule

## Quick check URLs

- `http://127.0.0.1:3001/search?q=apple`
- `http://127.0.0.1:3001/search/entities/1`
- `http://127.0.0.1:3001/graph/export?entity_id=1&depth=2`
- `http://127.0.0.1:3001/monitor/portfolios/1/exposure`
- `http://127.0.0.1:3001/reports/1`

## UI pages to inspect

- Web home: `http://localhost:3000`
- Search: `http://localhost:3000/search`
- Graph: `http://localhost:3000/graph` (use entity id `1`)
- Entity profile: `http://localhost:3000/entities/1`
- Portfolio: `http://localhost:3000/portfolio/1`
- Review workspace: `http://localhost:3000/review/1`
- Admin: `http://localhost:3002`

