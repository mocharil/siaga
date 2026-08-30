"""Unit tests for Healthcheck and Alerting Module (T26).

Tests all operational health verification rules:
1. Healthy operational state
2. Latest collector status failure ('failed' / 'partial')
3. Stale collector execution (> 26 hours)
4. Missing / failed daily_stats heartbeat_ok
5. Missing or locked database
6. Alert message formatting and Telegram notification trigger
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
from unittest.mock import MagicMock, patch
import pytest

from lib.db import init_db
from scripts.healthcheck import HealthCheckResult, check_health


@pytest.fixture
def sample_db(tmp_path):
    """Set up an isolated database with healthy initial records."""
    db_file = tmp_path / "test_health.db"
    init_db(db_file)

    now_iso = datetime.now(timezone.utc).isoformat()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    with sqlite3.connect(str(db_file)) as conn:
        # Insert healthy collector run
        conn.execute(
            """
            INSERT INTO collector_runs (started_at, finished_at, source, fetched, inserted_new, status)
            VALUES (?, ?, 'ctlogs_id', 100, 10, 'ok')
            """,
            (now_iso, now_iso),
        )
        # Insert healthy daily_stats
        conn.execute(
            """
            INSERT INTO daily_stats (date, domains_scanned, domains_flagged, collector_ok, heartbeat_ok, peak_ram_mb)
            VALUES (?, 100, 2, 1, 1, 45)
            """,
            (today_str,),
        )
        conn.commit()

    return db_file


def test_healthcheck_healthy_state(sample_db):
    """Verify that a freshly updated database evaluates as healthy with 0 issues."""
    result = check_health(db_path=sample_db, max_staleness_hours=26.0)

    assert result.is_healthy is True
    assert len(result.issues) == 0
    assert result.latest_collector_status == "ok"
    assert result.latest_heartbeat_ok is True


def test_healthcheck_missing_database(tmp_path):
    """Verify that a non-existent database file triggers health failure."""
    non_existent = tmp_path / "does_not_exist.db"
    result = check_health(db_path=non_existent)

    assert result.is_healthy is False
    assert any("tidak ditemukan" in issue for issue in result.issues)


def test_healthcheck_collector_latest_failed(sample_db):
    """Verify that a latest collector run with status 'failed' triggers an alert."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(str(sample_db)) as conn:
        conn.execute(
            """
            INSERT INTO collector_runs (started_at, finished_at, source, fetched, inserted_new, status, error_message)
            VALUES (?, ?, 'ctlogs_id', 0, 0, 'failed', 'DNS resolution timeout')
            """,
            (now_iso, now_iso),
        )
        conn.commit()

    result = check_health(db_path=sample_db)

    assert result.is_healthy is False
    assert result.latest_collector_status == "failed"
    assert any("berstatus 'failed'" in issue for issue in result.issues)
    assert any("DNS resolution timeout" in issue for issue in result.issues)


def test_healthcheck_collector_stale_over_26_hours(sample_db):
    """Verify that if no successful collector run happened in >26 hours, health fails."""
    # Set the only collector run to 30 hours ago
    stale_time = (datetime.now(timezone.utc) - timedelta(hours=30)).isoformat()
    with sqlite3.connect(str(sample_db)) as conn:
        conn.execute("DELETE FROM collector_runs")
        conn.execute(
            """
            INSERT INTO collector_runs (started_at, finished_at, source, fetched, inserted_new, status)
            VALUES (?, ?, 'ctlogs_id', 50, 5, 'ok')
            """,
            (stale_time, stale_time),
        )
        conn.commit()

    result = check_health(db_path=sample_db, max_staleness_hours=26.0)

    assert result.is_healthy is False
    assert any("Tidak ada collector sukses dalam" in issue for issue in result.issues)


def test_healthcheck_heartbeat_not_ok(sample_db):
    """Verify that heartbeat_ok == 0 in daily_stats triggers an alert."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with sqlite3.connect(str(sample_db)) as conn:
        conn.execute("UPDATE daily_stats SET heartbeat_ok = 0 WHERE date = ?", (today_str,))
        conn.commit()

    result = check_health(db_path=sample_db)

    assert result.is_healthy is False
    assert result.latest_heartbeat_ok is False
    assert any("heartbeat_ok bernilai 0/false" in issue for issue in result.issues)


def test_healthcheck_alert_message_formatting(sample_db):
    """Verify alert message formatting contains key diagnostic information."""
    result = HealthCheckResult(
        is_healthy=False,
        checked_at="2026-08-30T09:00:00Z",
        issues=["Eksekusi collector terakhir berstatus 'failed'."],
    )
    msg = result.format_alert_message(sample_db)

    assert "[SIAGA HEALTH ALERT]" in msg
    assert "Eksekusi collector terakhir berstatus 'failed'" in msg
    assert str(sample_db) in msg


def test_healthcheck_cli_alert_dispatch(sample_db, monkeypatch):
    """Verify main() CLI dispatches Telegram alert when unhealthy."""
    from scripts.healthcheck import main

    # Force unhealthy database state
    with sqlite3.connect(str(sample_db)) as conn:
        conn.execute("UPDATE daily_stats SET heartbeat_ok = 0")
        conn.commit()

    mock_send = MagicMock()
    with patch("scripts.healthcheck.send_message", mock_send):
        monkeypatch.setattr(
            "sys.argv",
            ["healthcheck.py", "--db-path", str(sample_db), "--chat-id", "12345678"],
        )
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        assert mock_send.called
        assert mock_send.call_args[1]["chat_id"] == "12345678"
        assert "[SIAGA HEALTH ALERT]" in mock_send.call_args[1]["text"]


def test_healthcheck_daily_stats_staleness_wib_timezone(tmp_path):
    """Verify that daily_stats staleness evaluates from 07:00 WIB (00:00 UTC), not 07:00 UTC.

    Why this test is crucial (Lessons from T06 & T26 incident):
    The daily brief cron is scheduled at 07:00 WIB (00:00 UTC). If healthcheck parses
    the daily_stats date as 07:00 UTC (which is 14:00 WIB), the timestamp is falsely
    shifted 7 hours into the future, stretching the 26-hour staleness threshold to 33 hours.
    
    This test verifies that at 27 hours after 07:00 WIB (i.e. next day 10:00 WIB),
    the system correctly flags daily_stats as stale (> 26 hours), preventing silent
    healthcheck delays.
    """
    from zoneinfo import ZoneInfo
    db_file = tmp_path / "test_health_wib.db"
    init_db(db_file)

    WIB = ZoneInfo("Asia/Jakarta")
    # Date in database: 2026-08-28 (completed 2026-08-28 07:00 WIB)
    stat_date = "2026-08-28"

    # Current time for test: 2026-08-29 10:00 WIB (27 hours after 2026-08-28 07:00 WIB)
    now_27h_wib = datetime(2026, 8, 29, 10, 0, 0, tzinfo=WIB)
    collector_run_time = (now_27h_wib - timedelta(hours=2)).isoformat()

    with sqlite3.connect(str(db_file)) as conn:
        conn.execute(
            """
            INSERT INTO collector_runs (started_at, finished_at, source, fetched, inserted_new, status)
            VALUES (?, ?, 'ctlogs_id', 100, 10, 'ok')
            """,
            (collector_run_time, collector_run_time),
        )
        conn.execute(
            """
            INSERT INTO daily_stats (date, domains_scanned, domains_flagged, collector_ok, heartbeat_ok, peak_ram_mb)
            VALUES (?, 100, 2, 1, 1, 45)
            """,
            (stat_date,),
        )
        conn.commit()

    # 27 hours elapsed from 07:00 WIB must trigger stale alert (threshold = 26h)
    result = check_health(db_path=db_file, max_staleness_hours=26.0, now=now_27h_wib)
    assert result.is_healthy is False
    assert any("daily_stats terakhir sudah usang" in issue for issue in result.issues)
    assert any("27.0 jam" in issue for issue in result.issues)

    # Conversely, at 25 hours after 07:00 WIB (next day 08:00 WIB), it must be healthy
    now_25h_wib = datetime(2026, 8, 29, 8, 0, 0, tzinfo=WIB)
    result_fresh = check_health(db_path=db_file, max_staleness_hours=26.0, now=now_25h_wib)
    assert result_fresh.is_healthy is True
    assert len(result_fresh.issues) == 0
