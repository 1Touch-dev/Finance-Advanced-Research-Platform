# Setup Guide

Run the platform **without Docker** (recommended on Windows) or with Docker.

## Prerequisites

| Tool | Version | Notes |
|------|---------|--------|
| Node.js | 18+ | Web, admin, worker |
| Python | 3.11+ | API |
| Redis | Optional | Only for the worker (port 6379) |

No PostgreSQL required for local dev — the API uses **SQLite** (`apps/api/local.db`) by default.

---

## Option A — Local, no Docker (recommended)

From the repo root:

```powershell
.\scripts\local-start.ps1
```

This will:

1. Create `.env` from `.env.example` if missing
2. Install Python/Node dependencies
3. Start API (SQLite), Web, Admin, and Worker (if Redis is running)
4. Call `POST /bootstrap` to create tables

Stop everything:

```powershell
.\scripts\local-stop.ps1
```

### URLs

| Service | URL |
|---------|-----|
| Web | http://localhost:3000 |
| API | http://localhost:3001 |
| Admin | http://localhost:3002 |

### Manual start (same stack)

See **Option B** below if you prefer separate terminals.

---

## Option B — Docker (one command stack)

From the repo root (`Finance-Advanced-Research-Platform`):

```powershell
docker compose up --build -d
```

Wait ~30–60 seconds for Postgres, then initialize the database:

```powershell
curl.exe -X POST http://localhost:3001/bootstrap
```

### URLs

| Service | URL |
|---------|-----|
| Web | http://localhost:3000 |
| API | http://localhost:3001 |
| API health | http://localhost:3001/health |
| Admin | http://localhost:3002 |

### Useful commands

```powershell
docker compose ps
docker compose logs -f api
docker compose down
docker compose down -v   # also removes Postgres volume
```

Or use the helper script:

```powershell
.\scripts\docker-up.ps1
```

---

## Option C — Local development (manual, separate terminals)

### 1. Postgres + Redis

**With Docker (DB only):**

```powershell
docker compose up -d postgres redis
```

**Without Docker:** install PostgreSQL and Redis locally; create database `mydb` with user `user` / password `password`.

### 2. API

```powershell
cd apps\api
pip install -e .
pip install -e "..\..\packages\finance"
$env:DATABASE_URL = "postgresql+psycopg://user:password@localhost:5432/mydb"
uvicorn app.main:app --host 127.0.0.1 --port 3001
```

In another terminal (once API is up):

```powershell
curl.exe -X POST http://localhost:3001/bootstrap
```

### 3. Web

```powershell
cd apps\web
npm install
$env:NEXT_PUBLIC_API_URL = "http://localhost:3001"
npm start
```

### 4. Admin

```powershell
cd apps\admin
npm install
$env:PORT = "3002"
npm start
```

### 5. Worker (optional)

```powershell
cd apps\worker
npm install
npm start
```

Requires Redis on `127.0.0.1:6379` (or set `REDIS_URL`).

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `docker` not found | Install and start Docker Desktop; reopen the terminal |
| API crashes on import | `pip install python-multipart` and `pip install -e ../../packages/finance` |
| `POST /bootstrap` hangs | Postgres not running — start `docker compose up -d postgres` |
| Web build: missing `swr` | `cd apps\web` → `npm install` |
| Admin: missing `index.html` | Ensure `apps/admin/public/index.html` exists |
| Root `npm install` fails on Windows | Install per app (`apps\web`, `apps\admin`, `apps\worker`) instead |
| Port already in use | Stop the process on 3000/3001/3002 or change ports in `docker-compose.yml` |

Copy `.env.example` to `.env` in the repo root if you use env files with your tooling.

---

## Project layout

- `apps/api` — FastAPI backend
- `apps/web` — Next.js UI
- `apps/admin` — React admin dashboard
- `apps/worker` — Bull queue worker
- `packages/finance` — DCF, comps, technicals (Python)
- `packages/connectors` — US public-data connectors
