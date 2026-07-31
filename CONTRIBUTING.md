# Contributing to Finance Advanced Research Platform

Thank you for your interest in contributing to the Finance Advanced Research Platform! This document provides guidelines and instructions for contributing.

## Repository Structure

This is a monorepo organized as follows:

```
Finance-Advanced-Research-Platform/
├── apps/              # Deployable applications
│   ├── api/          # FastAPI backend
│   ├── web/          # Next.js frontend
│   ├── admin/        # React admin panel
│   └── worker/       # Background jobs
├── packages/         # Shared libraries
│   ├── finance/      # Financial calculations
│   ├── connectors/   # Data connectors
│   ├── config-*/     # Shared configurations
│   └── shared-types/ # TypeScript types
└── tooling/          # Development tools
```

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+
- pnpm (recommended) or npm
- Redis (for worker processes)

### Local Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and configure
3. Run setup script:

```bash
.\scripts\local-start.ps1
```

See [docs/setup/SETUP.md](docs/setup/SETUP.md) for detailed instructions.

## Development Workflow

### Branching Strategy

- `main` - Production-ready code
- `feature/*` - New features
- `fix/*` - Bug fixes
- `docs/*` - Documentation updates

### Commit Convention

We follow conventional commits:

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Example:
```
feat: add DCF valuation endpoint
fix: resolve yfinance NaN handling
docs: update API integration guide
```

### Code Style

- **JavaScript/TypeScript**: We use ESLint with our shared configs
- **Python**: We follow PEP 8 with Black formatter
- **Line length**: 100 characters max
- **Imports**: Organized alphabetically

### Adding New Features

1. **Create a feature branch**
   ```bash
   git checkout -b feature/my-new-feature
   ```

2. **Develop your feature**
   - Add tests for new functionality
   - Update documentation
   - Follow existing code patterns

3. **Test locally**
   ```bash
   # Backend tests
   cd apps/api
   pytest tests/
   
   # Frontend tests (when available)
   cd apps/web
   npm test
   ```

4. **Create a pull request**
   - Describe what the feature does
   - Include screenshots for UI changes
   - Reference any related issues

## Package Guidelines

### Creating New Packages

New packages go in `packages/`:

```
packages/
└── my-package/
    ├── package.json
    ├── README.md
    ├── src/
    └── tests/
```

Package naming: `@finance-platform/package-name`

### Dependency Rules

- **Apps import from packages** ✅
- **Packages import from other packages** ✅
- **Packages import from apps** ❌ Never!
- **Apps import from other apps** ❌ Extract to package instead

## Testing

- Write tests for all new features
- Maintain existing test coverage
- Run tests before submitting PR

```bash
# Python tests
cd apps/api
pytest

# JavaScript tests
cd apps/web
npm test
```

## Documentation

- Update README.md for significant changes
- Add JSDoc/docstrings for public APIs
- Update relevant docs in `docs/` folder
- Include examples where helpful

## Pull Request Process

1. **Update documentation**
2. **Add tests**
3. **Run linters**: `npm run lint` or `black .`
4. **Test locally**: Ensure all services start correctly
5. **Create PR** with clear description
6. **Address review feedback**
7. **Wait for approval** from maintainers

## Code Review Guidelines

### For Authors
- Keep PRs focused and reasonably sized
- Respond to feedback promptly
- Be open to suggestions

### For Reviewers
- Be respectful and constructive
- Focus on code quality and maintainability
- Approve when satisfied with changes

## Questions?

- Check existing [documentation](docs/)
- Open an issue for bugs or feature requests
- Contact the team for clarification

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing! 🎉
