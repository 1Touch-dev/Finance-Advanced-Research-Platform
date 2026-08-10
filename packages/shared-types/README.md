# @finance-platform/shared-types

Shared TypeScript types and interfaces for the Finance Advanced Research Platform monorepo.

## Purpose

This package provides common type definitions used across all applications and packages in the monorepo, ensuring type consistency and reducing duplication.

## Usage

```typescript
import { Entity, IntelligenceReport, StockData } from '@finance-platform/shared-types';

// Use the types in your code
const entity: Entity = {
  id: '1',
  name: 'Palantir Technologies',
  type: 'organization',
};
```

## Organization

- `index.ts` - Main export file with core types
- `api.ts` - API-specific types (responses, pagination, errors)
- `entities.ts` - Entity and relationship types

## Adding New Types

1. Add your type definition to the appropriate file
2. Export it from that file
3. Re-export from `index.ts` if it should be part of the main export

## Type Categories

- **API Types**: Request/response formats, pagination
- **Entity Types**: Core domain entities (people, organizations, agencies)
- **Report Types**: Intelligence reports, claims, sections
- **Market Types**: Stock data, crypto data
- **User Types**: Authentication, authorization
- **Alert Types**: Notifications, watchlist alerts
