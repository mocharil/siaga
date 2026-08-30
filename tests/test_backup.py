"""Unit tests for Database Backup Job and Retention (T26).

Tests:
1. Online database backup creation in daily/ directory.
2. Weekly archive creation when forced or on Sunday.
3. Retention pruning of daily backups older than 7 days.
4. Database integrity and table structure verification of backup.
"""

from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import time
import pytest

from lib.db import init_db
from scripts.backup_db import perform_backup


@pytest.fixture
def sample_source_db(tmp_path):
    """Create a sample database with tables and sample data."""
    db_file = tmp_path / "source_siaga.db"
    init_db(db_file)

    with sqlite3.connect(str(db_file)) as conn:
        conn.execute(
            "INSERT INTO ct_raw (domain, first_seen, source) VALUES ('test-backup.id', '2026-08-30T00:00:00Z', 'test')"
        )
        conn.commit()

    return db_file


def test_perform_backup_daily_and_integrity(sample_source_db, tmp_path):
    """Verify daily backup creates a valid SQLite database with matching tables and rows."""
    backup_root = tmp_path / "backups"

    daily_path, weekly_path = perform_backup(
        db_path=sample_source_db,
        backup_root=backup_root,
        retention_days=7,
        force_weekly=False,
    )

    assert daily_path.exists()
    assert daily_path.stat().st_size > 0

    # Verify backup database integrity
    with sqlite3.connect(str(daily_path)) as conn:
        cur = conn.cursor()
        count = cur.execute("SELECT COUNT(*) FROM ct_raw").fetchone()[0]
        assert count == 1
        row = cur.execute("SELECT domain FROM ct_raw").fetchone()[0]
        assert row == "test-backup.id"


def test_perform_backup_force_weekly(sample_source_db, tmp_path):
    """Verify weekly archive copy is generated when force_weekly=True."""
    backup_root = tmp_path / "backups"

    daily_path, weekly_path = perform_backup(
        db_path=sample_source_db,
        backup_root=backup_root,
        force_weekly=True,
    )

    assert weekly_path is not None
    assert weekly_path.exists()
    assert weekly_path.parent.name == "weekly"
    assert weekly_path.stat().st_size == daily_path.stat().st_size


def test_perform_backup_sunday_wib_triggers_weekly_backup(sample_source_db, tmp_path):
    """Verify that Sunday morning in WIB (Asia/Jakarta) correctly triggers weekly backup.

    Why this test is crucial (Lessons from T06 incident):
    If the backup job executes at 06:30 WIB on Sunday morning (2026-08-30 06:30+07:00),
    the equivalent UTC timestamp is Saturday night (2026-08-29 23:30Z, weekday()=5).
    Using UTC caused `is_sunday` to evaluate to False, silently skipping weekly backups.
    This test verifies that timezone conversion to Asia/Jakarta correctly evaluates
    weekday() == 6 (Sunday) and creates the weekly backup file without --force-weekly.
    """
    from zoneinfo import ZoneInfo
    backup_root = tmp_path / "backups"

    # Sunday 06:30 WIB = Saturday 23:30 UTC
    sunday_morning_wib = datetime(2026, 8, 30, 6, 30, 0, tzinfo=ZoneInfo("Asia/Jakarta"))

    daily_path, weekly_path = perform_backup(
        db_path=sample_source_db,
        backup_root=backup_root,
        force_weekly=False,
        now=sunday_morning_wib,
    )

    assert daily_path.exists()
    assert weekly_path is not None
    assert weekly_path.exists()
    assert weekly_path.name == "siaga_weekly_2026-08-30.db"


def test_perform_backup_non_sunday_wib_skips_weekly_backup(sample_source_db, tmp_path):
    """Verify that non-Sunday runs in WIB do not create weekly backup unless forced."""
    from zoneinfo import ZoneInfo
    backup_root = tmp_path / "backups"

    # Monday 06:30 WIB
    monday_morning_wib = datetime(2026, 8, 31, 6, 30, 0, tzinfo=ZoneInfo("Asia/Jakarta"))

    daily_path, weekly_path = perform_backup(
        db_path=sample_source_db,
        backup_root=backup_root,
        force_weekly=False,
        now=monday_morning_wib,
    )

    assert daily_path.exists()
    assert weekly_path is None


def test_perform_backup_retention_pruning(sample_source_db, tmp_path):
    """Verify daily backups older than 7 days are automatically pruned."""
    backup_root = tmp_path / "backups"
    daily_dir = backup_root / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)

    # Create dummy old daily backup files
    old_file_10d = daily_dir / "siaga_2026-08-20.db"
    old_file_10d.write_text("dummy old db")
    # Set modification time to 10 days ago
    ten_days_ago = time.time() - (10 * 86400)
    os.utime(str(old_file_10d), (ten_days_ago, ten_days_ago))

    recent_file_3d = daily_dir / "siaga_2026-08-27.db"
    recent_file_3d.write_text("dummy recent db")
    three_days_ago = time.time() - (3 * 86400)
    os.utime(str(recent_file_3d), (three_days_ago, three_days_ago))

    assert old_file_10d.exists()
    assert recent_file_3d.exists()

    daily_path, _ = perform_backup(
        db_path=sample_source_db,
        backup_root=backup_root,
        retention_days=7,
    )

    # Old backup (>7 days) must be deleted
    assert not old_file_10d.exists()
    # Recent backup (3 days) must be preserved
    assert recent_file_3d.exists()
    # Today's backup must exist
    assert daily_path.exists()
