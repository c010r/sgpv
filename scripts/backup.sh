#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/sgpv}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
APP_DIR="${APP_DIR:-/opt/sgpv}"
MEDIA_DIR="${MEDIA_DIR:-$APP_DIR/media}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"

mkdir -p "$BACKUP_DIR"

DB_NAME="${DB_NAME:?DB_NAME is required}"
DB_USER="${DB_USER:?DB_USER is required}"
DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-5432}"
DB_PASSWORD="${DB_PASSWORD:-}"

export PGPASSWORD="$DB_PASSWORD"

SQL_FILE="$BACKUP_DIR/sgpv_db_${TIMESTAMP}.sql.gz"
MEDIA_FILE="$BACKUP_DIR/sgpv_media_${TIMESTAMP}.tar.gz"

pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$DB_NAME" | gzip > "$SQL_FILE"

if [[ -d "$MEDIA_DIR" ]]; then
  tar -czf "$MEDIA_FILE" -C "$MEDIA_DIR" .
else
  echo "[backup] media dir not found: $MEDIA_DIR"
fi

find "$BACKUP_DIR" -type f -name "sgpv_*" -mtime +"$RETENTION_DAYS" -delete

echo "[backup] database backup: $SQL_FILE"
if [[ -f "$MEDIA_FILE" ]]; then
  echo "[backup] media backup: $MEDIA_FILE"
fi
echo "[backup] retention: $RETENTION_DAYS days"
