#!/usr/bin/env bash
# ============================================================
# Finance Advanced Research Platform — Production Deployment
# Checklist + Automated Pre-flight Script
# Run from repo root: bash docs/scripts/deploy.sh
# ============================================================
set -euo pipefail

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
PASS=0; FAIL=0; WARN=0

ok()   { echo -e "  ${GREEN}✓${NC} $1"; ((PASS++)); }
fail() { echo -e "  ${RED}✗${NC} $1"; ((FAIL++)); }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; ((WARN++)); }

echo ""
echo "══════════════════════════════════════════════════════"
echo "  Finance Research Platform — Production Pre-flight"
echo "══════════════════════════════════════════════════════"
echo ""

# ── P0: Critical requirements ─────────────────────────────────────────────────
echo "P0 — Critical"
echo "─────────────"

# 1. ENV variables
check_env() {
  local var="$1" required="${2:-true}"
  if [ -n "${!var:-}" ]; then
    ok "$var is set"
  elif [ "$required" = "true" ]; then
    fail "$var is NOT set (required)"
  else
    warn "$var is not set (recommended)"
  fi
}

check_env DATABASE_URL
check_env JWT_SECRET
check_env REDIS_URL
check_env SEC_USER_AGENT
check_env ENV

# JWT secret length
if [ -n "${JWT_SECRET:-}" ] && [ ${#JWT_SECRET} -ge 32 ]; then
  ok "JWT_SECRET is ≥32 chars (${#JWT_SECRET} chars)"
else
  fail "JWT_SECRET must be at least 32 characters"
fi

# ENV must be 'production' for prod
if [ "${ENV:-}" = "production" ]; then
  ok "ENV=production"
else
  warn "ENV=${ENV:-unset} (should be 'production')"
fi

echo ""
echo "P0 — Database"
echo "─────────────"

# 2. Database connectivity + migration
if command -v python3 &>/dev/null; then
  DB_STATUS=$(cd apps/api && python3 -c "
from app.db.session import check_db_health
r = check_db_health()
print(r.get('status','error'))
" 2>/dev/null || echo "error")
  
  if [ "$DB_STATUS" = "ok" ]; then
    ok "Database connectivity: $DB_STATUS"
  else
    fail "Database connectivity: $DB_STATUS"
  fi

  # Check alembic head
  ALEMBIC_CURRENT=$(cd apps/api && python3 -m alembic current 2>/dev/null | grep -v INFO | tail -1 || echo "unknown")
  ALEMBIC_HEAD=$(cd apps/api && python3 -m alembic heads 2>/dev/null | grep -v INFO | head -1 || echo "unknown")
  
  if echo "$ALEMBIC_CURRENT" | grep -q "(head)"; then
    ok "Alembic: at head revision"
  else
    fail "Alembic: NOT at head — run: cd apps/api && alembic upgrade head"
    echo "     Current: $ALEMBIC_CURRENT"
    echo "     Head:    $ALEMBIC_HEAD"
  fi
else
  warn "python3 not found — skipping DB checks"
fi

echo ""
echo "P0 — Redis"
echo "──────────"

if command -v redis-cli &>/dev/null && [ -n "${REDIS_URL:-}" ]; then
  if redis-cli -u "$REDIS_URL" ping 2>/dev/null | grep -q PONG; then
    ok "Redis: reachable at $REDIS_URL"
  else
    fail "Redis: NOT reachable at $REDIS_URL"
  fi
elif [ -n "${REDIS_URL:-}" ]; then
  warn "redis-cli not found — verify Redis manually: redis-cli -u $REDIS_URL ping"
else
  fail "REDIS_URL not set — caching and rate limiting will use in-memory only"
fi

echo ""
echo "P0 — HTTPS/SSL"
echo "──────────────"

if [ -n "${DOMAIN:-}" ]; then
  if curl -s --head "https://$DOMAIN/health/live" | grep -q "200"; then
    ok "HTTPS: $DOMAIN responds on 443"
  else
    fail "HTTPS: $DOMAIN not responding — configure SSL certificate"
  fi
else
  warn "DOMAIN not set — verify HTTPS/SSL manually"
  warn "Recommended: use Nginx + Let's Encrypt (certbot) or AWS ACM"
fi

echo ""
echo "P1 — Observability"
echo "──────────────────"

check_env SENTRY_DSN false
check_env NEXT_PUBLIC_SENTRY_DSN false
check_env APP_VERSION false

echo ""
echo "P1 — API Keys (data sources)"
echo "──────────────────────────────"

check_env FINNHUB_API_KEY false
check_env FRED_API_KEY false
check_env FEC_API_KEY false
check_env OPENAI_API_KEY false

echo ""
echo "══════════════════════════════════════════════════════"
printf "  Result: ${GREEN}%d passed${NC}  ${RED}%d failed${NC}  ${YELLOW}%d warnings${NC}\n" $PASS $FAIL $WARN
echo "══════════════════════════════════════════════════════"
echo ""

if [ $FAIL -gt 0 ]; then
  echo -e "  ${RED}❌ DEPLOYMENT BLOCKED — fix failures above before deploying${NC}"
  exit 1
elif [ $WARN -gt 0 ]; then
  echo -e "  ${YELLOW}⚠  Deployment allowed but review warnings above${NC}"
  exit 0
else
  echo -e "  ${GREEN}✅ All checks passed — safe to deploy${NC}"
  exit 0
fi
