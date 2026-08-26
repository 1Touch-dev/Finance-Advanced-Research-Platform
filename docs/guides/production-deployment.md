# Production Deployment Guide

## Quick Checklist

Run the automated pre-flight script:
```bash
# From repo root — set env vars first
export DATABASE_URL=postgresql://user:pass@host:5432/dbname
export JWT_SECRET=your-secret-at-least-32-chars
export REDIS_URL=redis://your-redis-host:6379
export ENV=production

bash docs/scripts/deploy.sh
```

---

## P0 — Mandatory Before First Deploy

### 1. Set production environment variables

```bash
# .env (production server) — NEVER commit this file
DATABASE_URL=postgresql://user:pass@host:5432/finresearch
JWT_SECRET=<generate: python3 -c "import secrets; print(secrets.token_hex(32))">
REDIS_URL=redis://localhost:6379
ENV=production
SEC_USER_AGENT="YourName yourname@email.com"
APP_VERSION=v1.0.0

# Sentry (recommended)
SENTRY_DSN=https://xxx@sentry.io/xxx
NEXT_PUBLIC_SENTRY_DSN=https://xxx@sentry.io/xxx

# API keys (set those you have)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
FINNHUB_API_KEY=...
STRIPE_SECRET_KEY=sk_live_...
SENDGRID_API_KEY=...
```

### 2. Verify Redis

```bash
redis-cli -u $REDIS_URL ping   # expects: PONG
```

### 3. Run Alembic migrations

```bash
cd apps/api
alembic upgrade head
alembic current   # should show (head)
```

### 4. HTTPS/SSL

**Option A — Nginx + Let's Encrypt (recommended for VPS):**
```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location / {
        proxy_pass http://127.0.0.1:3000/;
    }
}
```

```bash
certbot --nginx -d yourdomain.com
```

**Option B — AWS ACM + ALB:** Attach certificate in ACM, attach to ALB target group pointing to EC2/ECS.

---

## Health Endpoints (load balancer probes)

| Endpoint | Purpose | Expected |
|----------|---------|----------|
| `GET /health/live` | Liveness probe — is process alive? | 200 always |
| `GET /health/ready` | Readiness probe — can serve traffic? | 200 when ready, 503 otherwise |
| `GET /health/db` | Database check | 200 with status |
| `GET /health/redis` | Redis check | 200 with status |
| `GET /health/full` | All components | 200 with details |

**AWS ALB / k8s configuration:**
- Liveness: `GET /health/live` every 10s, threshold 3 failures
- Readiness: `GET /health/ready` every 5s, threshold 2 failures, 503 = unhealthy

---

## Database Backups

### Manual backup

```bash
# PostgreSQL
DATABASE_URL=... bash docs/scripts/backup-db.sh

# With S3 upload
DATABASE_URL=... BACKUP_S3_BUCKET=my-backups bash docs/scripts/backup-db.sh
```

### Automated (cron)

```bash
# crontab -e
# Daily backup at 2am, upload to S3, retain 30 days
0 2 * * * DATABASE_URL="$DATABASE_URL" BACKUP_S3_BUCKET="finance-platform-backups" BACKUP_RETENTION_DAYS=30 /path/to/repo/docs/scripts/backup-db.sh >> /var/log/db-backup.log 2>&1
```

---

## Rate Limits

The API enforces two tiers of rate limiting:

| Tier | Read (GET) | Write (POST/PUT/DELETE) |
|------|-----------|------------------------|
| Per IP | 100/min | 20/min |
| Per user (JWT) | 300/min | 60/min |

Health endpoints (`/health/*`) are exempt from rate limiting.

---

## Post-Deploy Verification

```bash
# Liveness
curl https://yourdomain.com/health/live

# Readiness
curl https://yourdomain.com/health/ready

# Full status
curl https://yourdomain.com/health/full | python3 -m json.tool

# API docs
open https://yourdomain.com/docs
```
