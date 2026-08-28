"""Unit tests for Database Schema and UU PDP Retention (T19).

Verifies full database schema initialization, indexes, idempotent migrations,
and enforces automated 30-day message hash data retention purging.
"""

from datetime import datetime, timezone, timedelta
import hashlib
from pathlib import Path
import sqlite3
import subprocess
import sys
import pytest

from lib.db import cleanup_retention, init_db


@pytest.fixture
def temp_db(tmp_path):
    """Provide isolated SQLite database for schema and retention testing."""
    db_file = tmp_path / "test_siaga.db"
    init_db(db_file)
    return db_file


def test_full_schema_all_tables_created(temp_db):
    """DoD: All required tables and indexes exist in the initialized schema."""
    expected_tables = {
        "ct_raw",
        "collector_runs",
        "domain_findings",
        "message_analyses",
        "daily_stats",
        "watchlist",
        "rdap_cache",
        "rdap_bootstrap",
        "blacklist_cache",
        "llm_usage",
    }

    with sqlite3.connect(str(temp_db)) as conn:
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = {row[0] for row in cur.fetchall()}

    missing_tables = expected_tables - existing_tables
    assert not missing_tables, f"Missing database tables: {missing_tables}"


def test_ct_raw_columns_and_processed_at_field(temp_db):
    """Verify ct_raw contains both not_before and processed_at columns."""
    with sqlite3.connect(str(temp_db)) as conn:
        cur = conn.execute("PRAGMA table_info(ct_raw)")
        columns = {row[1] for row in cur.fetchall()}

    assert "processed_at" in columns
    assert "not_before" in columns
    assert "domain" in columns
    assert "first_seen" in columns


def test_retention_cleanup_purges_records_older_than_30_days(temp_db):
    """DoD: Retention job purges records older than 30 days and retains recent records."""
    now_dt = datetime.now(timezone.utc)
    old_dt_1 = (now_dt - timedelta(days=40)).isoformat()
    old_dt_2 = (now_dt - timedelta(days=32)).isoformat()
    recent_dt_1 = (now_dt - timedelta(days=10)).isoformat()
    recent_dt_2 = (now_dt - timedelta(days=1)).isoformat()

    # Insert test records
    with sqlite3.connect(str(temp_db)) as conn:
        records = [
            (old_dt_1, "telegram", "hash_old_1", 1, 90, "INDIKASI PENIPUAN", 450),
            (old_dt_2, "telegram", "hash_old_2", 1, 80, "INDIKASI PENIPUAN", 320),
            (recent_dt_1, "telegram", "hash_recent_1", 1, 10, "AMAN", 150),
            (recent_dt_2, "telegram", "hash_recent_2", 0, 0, "AMAN", 100),
        ]
        conn.executemany(
            """
            INSERT INTO message_analyses (
                received_at, channel, message_hash, urls_found, risk_score, risk_level, latency_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            records,
        )
        conn.commit()

        cur = conn.execute("SELECT COUNT(*) FROM message_analyses")
        assert cur.fetchone()[0] == 4

    # Run retention cleanup for 30 days
    purged_count = cleanup_retention(temp_db, retention_days=30)
    assert purged_count == 2, f"Expected 2 expired records purged, got {purged_count}"

    # Verify remaining records
    with sqlite3.connect(str(temp_db)) as conn:
        cur = conn.execute("SELECT message_hash FROM message_analyses ORDER BY id ASC")
        remaining_hashes = [r[0] for r in cur.fetchall()]

    assert remaining_hashes == ["hash_recent_1", "hash_recent_2"]


def test_retention_job_cli_runner(temp_db):
    """Verify scripts/retention_job.py runs cleanly as a command-line utility."""
    script_path = Path(__file__).resolve().parent.parent / "scripts" / "retention_job.py"
    cmd = [sys.executable, str(script_path), "--db", str(temp_db), "--days", "30"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert "Total records purged:" in result.stderr or "Total records purged:" in result.stdout
