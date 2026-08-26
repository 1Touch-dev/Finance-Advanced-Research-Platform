#!/usr/bin/env bash
# ============================================================
# Database Backup Script — Finance Research Platform
# Supports: PostgreSQL (pg_dump) and SQLite
# Usage:
#   bash docs/scripts/backup-db.sh              # backup to ./backups/
#   BACKUP_DIR=/mnt/backups bash docs/scripts/backup-db.sh
#   BACKUP_S3_BUCKET=my-bucket bash docs/scripts/backup-db.sh
# ============================================================
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DATABASE_URL="${DATABASE_URL:-sqlite:///./local.db}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting database backup..."
echo "  URL: ${DATABASE_URL%%@*}@***"  # mask password

# ── Detect DB type ────────────────────────────────────────────────────────────
if [[ "$DATABASE_URL" == postgresql* ]]; then
  DB_TYPE="postgresql"
elif [[ "$DATABASE_URL" == sqlite* ]]; then
  DB_TYPE="sqlite"
else
  echo "ERROR: Unsupported DATABASE_URL scheme: $DATABASE_URL"
  exit 1
fi

# ── PostgreSQL backup ─────────────────────────────────────────────────────────
if [ "$DB_TYPE" = "postgresql" ]; then
  if ! command -v pg_dump &>/dev/null; then
    echo "ERROR: pg_dump not found — install postgresql-client"
    exit 1
  fi
  
  BACKUP_FILE="$BACKUP_DIR/postgres_${TIMESTAMP}.sql.gz"
  
  echo "  Type: PostgreSQL → $BACKUP_FILE"
  pg_dump "$DATABASE_URL" | gzip > "$BACKUP_FILE"
  
  SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
  echo "  Size: $SIZE"
fi

# ── SQLite backup ─────────────────────────────────────────────────────────────
if [ "$DB_TYPE" = "sqlite" ]; then
  # Extract file path from sqlite:///./local.db or sqlite:////absolute/path.db
  SQLITE_PATH=$(echo "$DATABASE_URL" | sed 's|sqlite:///||')
  
  if [ ! -f "$SQLITE_PATH" ]; then
    echo "ERROR: SQLite file not found: $SQLITE_PATH"
    exit 1
  fi
  
  BACKUP_FILE="$BACKUP_DIR/sqlite_${TIMESTAMP}.db.gz"
  echo "  Type: SQLite ($SQLITE_PATH) → $BACKUP_FILE"
  
  # Use SQLite online backup (safe for live DBs)
  if command -v sqlite3 &>/dev/null; then
    sqlite3 "$SQLITE_PATH" ".backup /tmp/backup_${TIMESTAMP}.db"
    gzip -c "/tmp/backup_${TIMESTAMP}.db" > "$BACKUP_FILE"
    rm -f "/tmp/backup_${TIMESTAMP}.db"
  else
    cp "$SQLITE_PATH" "/tmp/backup_${TIMESTAMP}.db"
    gzip -c "/tmp/backup_${TIMESTAMP}.db" > "$BACKUP_FILE"
    rm -f "/tmp/backup_${TIMESTAMP}.db"
  fi
  
  SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
  echo "  Size: $SIZE"
fi

# ── Upload to S3 (optional) ───────────────────────────────────────────────────
if [ -n "${BACKUP_S3_BUCKET:-}" ]; then
  if command -v aws &>/dev/null; then
    S3_KEY="db-backups/$(basename "$BACKUP_FILE")"
    echo "  Uploading to s3://$BACKUP_S3_BUCKET/$S3_KEY..."
    aws s3 cp "$BACKUP_FILE" "s3://$BACKUP_S3_BUCKET/$S3_KEY" --storage-class STANDARD_IA
    echo "  S3 upload: complete"
  else
    echo "  WARNING: BACKUP_S3_BUCKET set but aws CLI not found — skipping S3 upload"
  fi
fi

# ── Prune old local backups ───────────────────────────────────────────────────
echo "  Pruning backups older than ${RETENTION_DAYS} days..."
find "$BACKUP_DIR" -name "*.gz" -mtime +${RETENTION_DAYS} -delete 2>/dev/null || true
REMAINING=$(ls "$BACKUP_DIR"/*.gz 2>/dev/null | wc -l)
echo "  Remaining backups: $REMAINING"

echo "[$(date)] Backup complete: $BACKUP_FILE"
