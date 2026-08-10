# @finance-platform/config-typescript

Shared TypeScript configurations for the Finance Advanced Research Platform monorepo.

## Configurations

- **base.json** - Base TypeScript config for all packages
- **nextjs.json** - Next.js specific configuration (extends base)
- **react.json** - React specific configuration (extends base)

## Usage

In your package's `tsconfig.json`:

```json
{
  "extends": "@finance-platform/config-typescript/nextjs.json",
  "compilerOptions": {
    // Your package-specific overrides
  }
}
```

## Available Configs

### Next.js Apps
```json
{
  "extends": "@finance-platform/config-typescript/nextjs.json"
}
```

### React Apps (CRA, Admin)
```json
{
  "extends": "@finance-platform/config-typescript/react.json"
}
```

### Library Packages
```json
{
  "extends": "@finance-platform/config-typescript/base.json"
}
```
