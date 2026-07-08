#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/srv/qbtracker}"
ENV_FILE="${ENV_FILE:-$APP_DIR/.env}"
BACKUP_DIR="${BACKUP_DIR:-/srv/backups/qbtracker}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
TIMESTAMP="$(date -u +"%Y%m%d_%H%M%S")"

umask 077
mkdir -p "$BACKUP_DIR"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: env file not found: $ENV_FILE" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: DATABASE_URL is missing in $ENV_FILE" >&2
  exit 1
fi

if ! command -v pg_dump >/dev/null 2>&1; then
  echo "ERROR: pg_dump is not installed or not available in PATH" >&2
  exit 1
fi

DB_BACKUP="$BACKUP_DIR/qbtracker_db_$TIMESTAMP.sql.gz"
FILES_BACKUP="$BACKUP_DIR/qbtracker_files_$TIMESTAMP.tar.gz"
MANIFEST="$BACKUP_DIR/qbtracker_manifest_$TIMESTAMP.txt"

echo "Creating database backup..."
pg_dump --no-owner --no-privileges "$DATABASE_URL" | gzip -9 > "$DB_BACKUP"

echo "Creating file backup..."
tar_items=()
[[ -f "$APP_DIR/.env" ]] && tar_items+=(".env")
[[ -d "$APP_DIR/uploads" ]] && tar_items+=("uploads")
[[ -f "$APP_DIR/requirements.txt" ]] && tar_items+=("requirements.txt")
[[ -f "$APP_DIR/deploy.sh" ]] && tar_items+=("deploy.sh")

if [[ "${#tar_items[@]}" -gt 0 ]]; then
  (cd "$APP_DIR" && tar -czf "$FILES_BACKUP" "${tar_items[@]}")
else
  echo "WARNING: no app files found to archive" >&2
  : > "$FILES_BACKUP"
fi

{
  echo "QB Tracker backup manifest"
  echo "Created UTC: $(date -u +"%Y-%m-%d %H:%M:%S")"
  echo "Host: $(hostname)"
  echo "App dir: $APP_DIR"
  echo "Env file: $ENV_FILE"
  echo "Database backup: $(basename "$DB_BACKUP")"
  echo "Files backup: $(basename "$FILES_BACKUP")"
  echo
  du -h "$DB_BACKUP" "$FILES_BACKUP"
} > "$MANIFEST"

find "$BACKUP_DIR" -type f -name "qbtracker_*" -mtime +"$RETENTION_DAYS" -delete

echo "Backup complete:"
echo "  $DB_BACKUP"
echo "  $FILES_BACKUP"
echo "  $MANIFEST"
