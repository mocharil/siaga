#!/usr/bin/env python3
"""SIAGA System Healthcheck & Alerting Script (T26).

Checks operational health criteria from siaga.db:
1. Latest collector run status must be 'ok'.
2. A successful collector run must have occurred within the last 26 hours.
3. daily_stats.heartbeat_ok must be updated and active within the last 26 hours.
4. Database read accessibility and integrity.

If any health criteria fail, sends an immediate alert via lib/telegram_notify.py.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import sqlite3
import sys
import time

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure repository root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from lib.telegram_notify import TelegramNotifyError, send_message

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("siaga.healthcheck")

DEFAULT_DB_PATH = BASE_DIR / "data" / "siaga.db"
DEFAULT_MAX_STALENESS_HOURS = 26.0


@dataclass
class HealthCheckResult:
    """Detailed health check outcome."""
    is_healthy: bool
    checked_at: str
    issues: list[str] = field(default_factory=list)
    latest_collector_status: str | None = None
    latest_collector_time: str | None = None
    last_successful_collector_time: str | None = None
    latest_heartbeat_date: str | None = None
    latest_heartbeat_ok: bool | None = None
    staleness_hours: float | None = None

    def format_alert_message(self, db_path: str | Path = DEFAULT_DB_PATH) -> str:
        """Format a human-readable alert message for Telegram."""
        lines = [
            "🚨 [SIAGA HEALTH ALERT] 🚨",
            "Terdeteksi gangguan operasional pada sistem deteksi penipuan SIAGA:\n",
        ]
        for issue in self.issues:
            lines.append(f"• {issue}")

        lines.append(f"\nWaktu Pemeriksaan: {self.checked_at}")
        lines.append(f"Database: {db_path}")
        lines.append("Harap periksa logs dan Task Scheduler / Cron segera.")
        return "\n".join(lines)


def _connect_ro_with_retry(db_path: Path, max_attempts: int = 3, timeout: float = 5.0) -> sqlite3.Connection:
    """Safely open SQLite connection in read-only mode with retries against disk I/O / WAL busy."""
    db_uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    last_err: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            conn = sqlite3.connect(db_uri, uri=True, timeout=timeout)
            # Simple probe query
            conn.execute("SELECT 1").fetchone()
            return conn
        except sqlite3.OperationalError as e:
            last_err = e
            logger.warning("SQLite connection attempt %d failed (%s), retrying...", attempt, e)
            time.sleep(0.5 * attempt)
        except Exception as e:
            # Fallback to standard connection if URI mode fails
            try:
                conn = sqlite3.connect(str(db_path), timeout=timeout)
                conn.execute("SELECT 1").fetchone()
                return conn
            except Exception as fallback_err:
                last_err = fallback_err
                time.sleep(0.5 * attempt)

    raise sqlite3.OperationalError(f"Could not connect to database after {max_attempts} attempts: {last_err}")


def check_health(
    db_path: Path | str = DEFAULT_DB_PATH,
    max_staleness_hours: float = DEFAULT_MAX_STALENESS_HOURS,
    now: datetime | None = None,
) -> HealthCheckResult:
    """Evaluate database state and determine operational health.

    Args:
        db_path: Path to siaga.db SQLite database.
        max_staleness_hours: Maximum allowed hours without successful collector/heartbeat.
        now: Optional reference datetime (defaults to current UTC time).

    Returns:
        HealthCheckResult with healthy boolean and detailed issue descriptions.
    """
    resolved_db = Path(db_path)
    now_dt = now or datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()

    result = HealthCheckResult(
        is_healthy=True,
        checked_at=now_iso,
    )

    if not resolved_db.exists():
        result.is_healthy = False
        result.issues.append(f"Berkas database tidak ditemukan di {resolved_db}")
        return result

    try:
        conn = _connect_ro_with_retry(resolved_db)
    except Exception as e:
        result.is_healthy = False
        result.issues.append(f"Koneksi database gagal (Disk I/O atau lock error): {e}")
        return result

    try:
        # 1. Check latest collector run
        cur = conn.execute(
            """
            SELECT id, started_at, finished_at, status, error_message
            FROM collector_runs
            ORDER BY id DESC
            LIMIT 1
            """
        )
        latest_run = cur.fetchone()

        if not latest_run:
            result.is_healthy = False
            result.issues.append("Belum pernah ada riwayat eksekusi collector tercatat di database.")
        else:
            run_id, started_at, finished_at, status, error_msg = latest_run
            result.latest_collector_status = status
            result.latest_collector_time = finished_at or started_at

            if status != "ok":
                result.is_healthy = False
                err_detail = f": {error_msg}" if error_msg else ""
                result.issues.append(
                    f"Eksekusi collector terakhir (run #{run_id}) berstatus '{status}'{err_detail} pada {result.latest_collector_time}."
                )

        # 2. Check time elapsed since last successful collector run ('ok')
        cur = conn.execute(
            """
            SELECT MAX(COALESCE(finished_at, started_at))
            FROM collector_runs
            WHERE status = 'ok'
            """
        )
        last_ok_row = cur.fetchone()
        last_ok_time_str = last_ok_row[0] if last_ok_row else None
        result.last_successful_collector_time = last_ok_time_str

        if not last_ok_time_str:
            result.is_healthy = False
            if "Belum pernah ada riwayat eksekusi collector" not in str(result.issues):
                result.issues.append("Tidak ditemukan eksekusi collector dengan status 'ok'.")
        else:
            try:
                # Parse ISO timestamp
                clean_ts = last_ok_time_str.replace("Z", "+00:00")
                last_ok_dt = datetime.fromisoformat(clean_ts)
                elapsed_hours = (now_dt - last_ok_dt).total_seconds() / 3600.0
                result.staleness_hours = elapsed_hours

                if elapsed_hours > max_staleness_hours:
                    result.is_healthy = False
                    result.issues.append(
                        f"Tidak ada collector sukses dalam {elapsed_hours:.1f} jam terakhir (Batas toleransi: {max_staleness_hours} jam, Sukses terakhir: {last_ok_time_str})."
                    )
            except Exception as parse_err:
                logger.warning("Could not parse timestamp %s: %s", last_ok_time_str, parse_err)

        # 3. Check daily_stats heartbeat freshness
        cur = conn.execute(
            """
            SELECT date, heartbeat_ok, collector_ok
            FROM daily_stats
            ORDER BY date DESC
            LIMIT 1
            """
        )
        latest_daily = cur.fetchone()

        if not latest_daily:
            result.is_healthy = False
            result.issues.append("Tabel daily_stats kosong — belum pernah ada siklus harian berjalan.")
        else:
            stat_date, hb_ok, col_ok = latest_daily
            result.latest_heartbeat_date = stat_date
            result.latest_heartbeat_ok = bool(hb_ok)

            if not hb_ok:
                result.is_healthy = False
                result.issues.append(
                    f"Status heartbeat_ok bernilai 0/false pada entri harian terakhir ({stat_date})."
                )

            # Check if latest daily_stats date is stale (> 26 hours ago)
            try:
                stat_dt = datetime.strptime(stat_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                # Consider start of day for comparison
                date_diff_hours = (now_dt.date() - stat_dt.date()).days * 24.0
                if date_diff_hours > max_staleness_hours:
                    result.is_healthy = False
                    result.issues.append(
                        f"daily_stats terakhir sudah usang ({stat_date}, selisih ~{date_diff_hours:.0f} jam dari tanggal sekarang)."
                    )
            except Exception as date_err:
                logger.warning("Could not parse daily_stats date %s: %s", stat_date, date_err)

    except Exception as e:
        result.is_healthy = False
        result.issues.append(f"Gagal mengevaluasi kueri kesehatan database: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="SIAGA Operational Healthcheck (T26)")
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DEFAULT_DB_PATH,
        help=f"Path to SQLite database (default: {DEFAULT_DB_PATH})",
    )
    parser.add_argument(
        "--max-staleness-hours",
        type=float,
        default=DEFAULT_MAX_STALENESS_HOURS,
        help=f"Maximum allowed staleness in hours (default: {DEFAULT_MAX_STALENESS_HOURS})",
    )
    parser.add_argument(
        "--chat-id",
        type=str,
        default=os.environ.get("SIAGA_OWNER_CHAT_ID") or os.environ.get("TELEGRAM_CHAT_ID"),
        help="Telegram chat ID to send alerts to",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Check health and print report without sending Telegram notification",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output result in JSON format",
    )

    args = parser.parse_args()

    result = check_health(
        db_path=args.db_path,
        max_staleness_hours=args.max_staleness_hours,
    )

    if args.json:
        print(json.dumps({
            "is_healthy": result.is_healthy,
            "checked_at": result.checked_at,
            "issues": result.issues,
            "latest_collector_status": result.latest_collector_status,
            "latest_collector_time": result.latest_collector_time,
            "last_successful_collector_time": result.last_successful_collector_time,
            "latest_heartbeat_date": result.latest_heartbeat_date,
            "latest_heartbeat_ok": result.latest_heartbeat_ok,
            "staleness_hours": result.staleness_hours,
        }, indent=2))
    else:
        if result.is_healthy:
            logger.info("✅ HEALTHCHECK OK: Sistem SIAGA beroperasi normal.")
            logger.info("Collector status: %s | Sukses terakhir: %s | Heartbeat date: %s (ok=%s)",
                        result.latest_collector_status, result.last_successful_collector_time,
                        result.latest_heartbeat_date, result.latest_heartbeat_ok)
        else:
            logger.error("❌ HEALTHCHECK FAILED: Ditemukan %d masalah operasional:", len(result.issues))
            for i, issue in enumerate(result.issues, 1):
                logger.error("  %d. %s", i, issue)

    # Send Telegram alert if unhealthy and not dry-run
    if not result.is_healthy and not args.dry_run:
        if args.chat_id:
            alert_text = result.format_alert_message(args.db_path)
            try:
                send_message(chat_id=args.chat_id, text=alert_text)
                logger.info("Telegram alert successfully sent to chat_id=%s", args.chat_id)
            except TelegramNotifyError as e:
                logger.error("Failed to send Telegram alert: %s", e)
        else:
            logger.warning("No chat_id configured; skipped Telegram alert delivery.")

    # Exit code: 0 if healthy, 1 if unhealthy
    sys.exit(0 if result.is_healthy else 1)


if __name__ == "__main__":
    main()
