#!/usr/bin/env python3
"""Automated Database Backup Job (T26).

Creates daily transactional backups of siaga.db using SQLite's online backup API,
retains the last 7 days of daily backups, and stores a weekly archive copy.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import time

# Ensure repository root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("siaga.backup_db")

DEFAULT_DB_PATH = BASE_DIR / "data" / "siaga.db"
DEFAULT_BACKUP_DIR = BASE_DIR / "backups"
DEFAULT_RETENTION_DAYS = 7


def perform_backup(
    db_path: Path | str = DEFAULT_DB_PATH,
    backup_root: Path | str = DEFAULT_BACKUP_DIR,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    force_weekly: bool = False,
) -> tuple[Path, Path | None]:
    """Execute consistent SQLite online backup and purge stale daily backups.

    Args:
        db_path: Path to live siaga.db.
        backup_root: Directory to store backup archives.
        retention_days: Days of daily backups to preserve (default: 7).
        force_weekly: If True, always creates a copy in backups/weekly.

    Returns:
        tuple of (daily_backup_path, weekly_backup_path_or_none)
    """
    resolved_db = Path(db_path)
    resolved_root = Path(backup_root)

    daily_dir = resolved_root / "daily"
    weekly_dir = resolved_root / "weekly"

    daily_dir.mkdir(parents=True, exist_ok=True)
    weekly_dir.mkdir(parents=True, exist_ok=True)

    if not resolved_db.exists():
        raise FileNotFoundError(f"Source database not found at {resolved_db}")

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    daily_target = daily_dir / f"siaga_{today_str}.db"

    logger.info("Starting online backup from %s to %s...", resolved_db, daily_target)
    t0 = time.monotonic()

    # Perform online transactional backup via sqlite3 backup API
    with sqlite3.connect(str(resolved_db)) as src_conn:
        # Destination connection (fresh file)
        if daily_target.exists():
            daily_target.unlink()

        with sqlite3.connect(str(daily_target)) as dst_conn:
            src_conn.backup(dst_conn, pages=100, sleep=0.01)

    elapsed = time.monotonic() - t0
    backup_size_mb = daily_target.stat().st_size / (1024 * 1024)
    logger.info("Daily backup completed successfully: %.2f MB in %.2fs", backup_size_mb, elapsed)

    # Determine if weekly copy should be created (Sunday is weekday 6)
    is_sunday = datetime.now(timezone.utc).weekday() == 6
    weekly_target: Path | None = None

    if is_sunday or force_weekly:
        weekly_target = weekly_dir / f"siaga_weekly_{today_str}.db"
        shutil.copy2(daily_target, weekly_target)
        logger.info("Weekly backup archived at %s (%.2f MB)", weekly_target, backup_size_mb)

    # Purge daily backups older than retention_days
    cutoff_time = time.time() - (retention_days * 86400)
    purged_count = 0

    for item in daily_dir.glob("siaga_*.db"):
        if item.is_file() and item != daily_target:
            try:
                # Check modification time
                if item.stat().st_mtime < cutoff_time:
                    item.unlink()
                    purged_count += 1
                    logger.info("Pruned expired daily backup: %s", item.name)
            except Exception as e:
                logger.warning("Could not check/delete %s: %s", item, e)

    logger.info("Retention maintenance complete: %d expired daily backups purged.", purged_count)
    return daily_target, weekly_target


def main() -> None:
    parser = argparse.ArgumentParser(description="SIAGA Database Backup Runner (T26)")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Path to live SQLite database (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=DEFAULT_BACKUP_DIR,
        help=f"Destination directory for backups (default: {DEFAULT_BACKUP_DIR})",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=DEFAULT_RETENTION_DAYS,
        help=f"Number of daily backups to keep (default: {DEFAULT_RETENTION_DAYS})",
    )
    parser.add_argument(
        "--force-weekly",
        action="store_true",
        default=False,
        help="Force creation of a weekly backup archive",
    )

    args = parser.parse_args()

    try:
        daily_path, weekly_path = perform_backup(
            db_path=args.db_path,
            backup_root=args.backup_dir,
            retention_days=args.retention_days,
            force_weekly=args.force_weekly,
        )
        print(f"SUCCESS: Daily backup at {daily_path}")
        if weekly_path:
            print(f"SUCCESS: Weekly backup at {weekly_path}")
    except Exception as e:
        logger.error("Backup failed: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
