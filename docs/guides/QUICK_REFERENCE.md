# 🚀 Quick Reference - Finance Advanced Research Platform

## 📁 **Where to Find Things** (Updated 2026 Structure)

### Starting Development
```powershell
# Option 1: Use original scripts (still works)
.\scripts\local-start.ps1

# Option 2: Use new location
.\tooling\scripts\local-start.ps1
```

### Documentation
| What I Need | Where It Is |
|-------------|-------------|
| **Start here (new teammates)** | [docs/handoff/Finance_Platform_Handoff.md](docs/handoff/Finance_Platform_Handoff.md) |
| **Local setup** | [docs/setup/SETUP.md](docs/setup/SETUP.md) |
| **All API integrations** | [docs/api/API_INTEGRATIONS_GUIDE.md](docs/api/API_INTEGRATIONS_GUIDE.md) |
| **Requirements backlog** | [docs/requirements/james_requirements.md](docs/requirements/james_requirements.md) |
| **Trade alerts architecture** | [docs/features/FEATURE_BIG_TRADE_ALERTS_ARCHITECTURE.md](docs/features/FEATURE_BIG_TRADE_ALERTS_ARCHITECTURE.md) |
| **All docs index** | [docs/README_DOCS.md](docs/README_DOCS.md) |
| **Contributing** | [CONTRIBUTING.md](CONTRIBUTING.md) |
| **What changed recently** | [CHANGELOG.md](CHANGELOG.md) |

### Code Locations
| Component | Path |
|-----------|------|
| **FastAPI Backend** | `apps/api/` |
| **Next.js Frontend** | `apps/web/` |
| **Admin Dashboard** | `apps/admin/` |
| **Background Worker** | `apps/worker/` |
| **Financial Logic** | `packages/finance/` |
| **Data Connectors** | `packages/connectors/` |
| **Shared Types** | `packages/shared-types/` |
| **Config (TS/ESLint)** | `packages/config-*/` |
| **Scripts & Tools** | `tooling/scripts/` (or `scripts/` for now) |

## 🌐 **Service URLs**

### Local Development
- **Web UI:** http://localhost:3003
- **API:** http://localhost:3001
- **API Docs:** http://localhost:3001/docs
- **Admin:** http://localhost:3002

### Staging (EC2)
- **Web UI:** http://184.72.123.188:3003
- **API:** http://184.72.123.188:3001
- **API Docs:** http://184.72.123.188:3001/docs
- **Admin:** http://184.72.123.188:3002

## 🔧 **Common Commands**

### Development
```powershell
# Start all services
.\scripts\local-start.ps1

# Stop all services
.\scripts\local-stop.ps1

# Start with Docker
.\scripts\docker-up.ps1

# Bootstrap database
curl.exe -X POST http://localhost:3001/bootstrap

# Seed demo data
curl.exe -X POST http://localhost:3001/demo/seed
```

### PM2 (Production)
```bash
pm2 list                    # List all services
pm2 logs finance-api        # View API logs
pm2 restart finance-api     # Restart API
pm2 restart all             # Restart everything
```

### Package Management
```powershell
# Install dependencies (root)
npm install

# Install for specific app
cd apps/web
npm install

# Install Python deps
cd apps/api
pip install -e .
pip install -e ../../packages/finance
```

## 📦 **Shared Packages**

### Using TypeScript Types
```typescript
// In any app
import { Entity, IntelligenceReport, StockData } from '@finance-platform/shared-types';
```

### Using TypeScript Config
```json
// In app's tsconfig.json
{
  "extends": "@finance-platform/config-typescript/nextjs.json"
}
```

### Using ESLint Config
```javascript
// In app's .eslintrc.js
module.exports = {
  extends: ['@finance-platform/config-eslint/nextjs'],
};
```

## 🎯 **Key Features**

| Feature | Page | API Endpoint |
|---------|------|--------------|
| **Intelligence Reports** | `/intelligence` | `POST /intelligence/generate` |
| **Stock Analysis** | `/stock` | `GET /market/yf/snapshot` |
| **DCF Valuation** | `/valuation` | `GET /market/valuation/dcf` |
| **Crypto Dashboard** | `/crypto` | `GET /market/crypto/dashboard` |
| **Gov Trading** | `/gov-trading` | `GET /market/gov/ptr-filings` |
| **Trade Alerts** | `/tracking` | `POST /tracking/scan/insider-trades` |
| **13F Analysis** | `/institutional` | `GET /market/institutional/holders` |

## 🔐 **Environment Setup**

```powershell
# Copy example env file
cp .env.example .env

# Edit with your API keys
notepad .env
```

Key variables:
- `DATABASE_URL` - Database connection
- `OPENAI_API_KEY` - For AI features
- `APOLLO_API_KEY` - For company enrichment
- `SENDGRID_API_KEY` - For email alerts
- `TWILIO_*` - For SMS alerts

## 🗂️ **Project Structure**

```
Finance-Advanced-Research-Platform/
├── apps/              # Deployable applications
├── packages/          # Shared libraries
├── tooling/           # Dev scripts & tools
├── docs/              # All documentation
├── tests/             # Test suites
└── .github/           # CI/CD (future)
```

**Key Principle:** `apps` consume `packages`, never the reverse!

## 📝 **Git Workflow**

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes, commit
git add .
git commit -m "feat: add awesome feature"

# Push and create PR
git push origin feature/my-feature
```

**Commit Prefixes:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation
- `refactor:` - Code refactoring
- `test:` - Tests
- `chore:` - Maintenance

## 🆘 **Getting Help**

1. **Check docs:** [docs/README_DOCS.md](docs/README_DOCS.md)
2. **API reference:** http://localhost:3001/docs
3. **Handoff document:** [docs/handoff/Finance_Platform_Handoff.md](docs/handoff/Finance_Platform_Handoff.md)
4. **Known issues:** [CHANGELOG.md](CHANGELOG.md)
5. **Ask team:** Contact via your team channel

## 🎓 **New Developer Checklist**

- [ ] Read [README.md](README.md)
- [ ] Read [docs/handoff/Finance_Platform_Handoff.md](docs/handoff/Finance_Platform_Handoff.md)
- [ ] Follow [docs/setup/SETUP.md](docs/setup/SETUP.md)
- [ ] Access EC2 staging server
- [ ] Get `.env` file with API keys
- [ ] Run `.\scripts\local-start.ps1`
- [ ] Open http://localhost:3003
- [ ] Generate test intelligence report
- [ ] Read [CONTRIBUTING.md](CONTRIBUTING.md)
- [ ] Join team communication channels

## 🌟 **Quick Wins**

**Generate Intelligence Report:**
1. Go to http://localhost:3003/intelligence
2. Click "Palantir Technologies" seed
3. Click "Generate Intelligence Report"
4. Wait ~30 seconds
5. Export as PDF/Word/Excel

**Analyze Stock:**
1. Go to http://localhost:3003/stock
2. Click "AAPL" quick button
3. Click "Analyze"
4. View AI consensus + technicals

**View Crypto Dashboard:**
1. Go to http://localhost:3003/crypto
2. See top 14 coins by market cap
3. Check trending coins
4. View whale alerts

---

**Last Updated:** 2026-07-29  
**Structure Version:** 2026 Best Practices  
**Questions?** See [docs/README_DOCS.md](docs/README_DOCS.md)
