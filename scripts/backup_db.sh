#!/usr/bin/env bash
# ==============================================================================
# SIAGA Database Backup Script (T26)
#
# Daily backup of siaga.db to a dedicated backups/ directory.
# Retains the last 7 daily backups, and saves weekly archives.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

DB_PATH="${SIAGA_DB_PATH:-$PROJECT_ROOT/data/siaga.db}"
BACKUP_ROOT="${SIAGA_BACKUP_DIR:-$PROJECT_ROOT/backups}"
DAILY_DIR="$BACKUP_ROOT/daily"
WEEKLY_DIR="$BACKUP_ROOT/weekly"
RETENTION_DAYS=7

mkdir -p "$DAILY_DIR"
mkdir -p "$WEEKLY_DIR"

TODAY="$(date -u +"%Y-%m-%d")"
DAILY_TARGET="$DAILY_DIR/siaga_${TODAY}.db"
WEEKLY_TARGET="$WEEKLY_DIR/siaga_weekly_${TODAY}.db"

echo "================================================================="
echo "SIAGA Database Backup — $TODAY"
echo "Source DB: $DB_PATH"
echo "Target:    $DAILY_TARGET"
echo "================================================================="

if [ ! -f "$DB_PATH" ]; then
    echo "ERROR: Source database not found at $DB_PATH" >&2
    exit 1
fi

# Prefer python online backup if python3 is available for safe WAL copying
if command -v python3 >/dev/null 2>&1; then
    python3 "$SCRIPT_DIR/backup_db.py" --db-path "$DB_PATH" --backup-dir "$BACKUP_ROOT" --retention-days "$RETENTION_DAYS"
else
    # Fallback to sqlite3 CLI online backup
    echo "Using sqlite3 CLI online backup..."
    sqlite3 "$DB_PATH" ".backup '$DAILY_TARGET'"
    echo "Daily backup saved: $(du -h "$DAILY_TARGET" | cut -f1)"

    # Check if Sunday (weekday 7 / 0) for weekly archive
    DOW="$(date -u +"%u")"
    if [ "$DOW" -eq 7 ] || [ "$DOW" -eq 0 ]; then
        cp -p "$DAILY_TARGET" "$WEEKLY_TARGET"
        echo "Weekly backup saved: $WEEKLY_TARGET"
    fi

    # Prune daily backups older than 7 days
    find "$DAILY_DIR" -type f -name "siaga_*.db" -mtime +"$RETENTION_DAYS" -exec rm -f {} +
    echo "Pruning complete for daily backups older than $RETENTION_DAYS days."
fi

echo "Backup job completed successfully."
