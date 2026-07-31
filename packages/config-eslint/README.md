# @finance-platform/config-eslint

Shared ESLint configurations for the Finance Advanced Research Platform monorepo.

## Configurations

- **base.js** - Base ESLint config for all packages
- **nextjs.js** - Next.js specific rules (extends base)
- **react.js** - React specific rules (extends base)

## Usage

In your package's `.eslintrc.js` or `eslintConfig` in `package.json`:

### Next.js Apps
```js
module.exports = {
  extends: ['@finance-platform/config-eslint/nextjs'],
};
```

### React Apps
```js
module.exports = {
  extends: ['@finance-platform/config-eslint/react'],
};
```

### Other Packages
```js
module.exports = {
  extends: ['@finance-platform/config-eslint/base'],
};
```
