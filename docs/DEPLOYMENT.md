# Staging Deployment (EC2)

## Services

| Service | Port | PM2 name |
|---------|------|----------|
| API | 3001 | finance-api |
| Web | 3003 | finance-web |
| Admin | 3002 | finance-admin |
| Worker | — | finance-worker |

## Infrastructure (Docker)

```bash
docker compose up -d postgres minio opensearch
```

- Postgres: `127.0.0.1:5433` (user/password/mydb)
- MinIO: `127.0.0.1:9000` (minio/minio123)
- OpenSearch: `127.0.0.1:9200`

## Environment (names only — set in `.env`)

- `DATABASE_URL`, `OPENSEARCH_URL`, `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`
- `ANTHROPIC_API_KEY`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`
- `NEXT_PUBLIC_API_URL`, `API_URL`, `ENV=staging`

## Start / restart

```bash
pm2 start ecosystem.config.js
pm2 restart finance-api --update-env
```

## Bootstrap + seed

```bash
curl -X POST http://127.0.0.1:3001/bootstrap
bash scripts/setup-minio-bucket.sh
bash scripts/seed-all-connectors.sh
curl -X POST http://127.0.0.1:3001/searchos/index/rebuild
```

## Backup

```bash
pg_dump -h 127.0.0.1 -p 5433 -U user mydb > backup.sql
# MinIO: use mc mirror or boto3 sync on enterprise-evidence bucket
```
