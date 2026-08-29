"""Database Schema Management and UU PDP Data Retention Module (T19).

Defines complete database schema for SIAGA, ensures idempotent migrations,
and enforces a 30-day strict privacy retention policy (UU PDP) on message audit hashes.
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
import logging
from pathlib import Path
import sqlite3

logger = logging.getLogger("siaga.db")

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "siaga.db"
DEFAULT_RETENTION_DAYS = 30


def init_db(db_path: Path | str | None = None) -> None:
    """Initialize complete SIAGA SQLite database schema idempotently."""
    resolved_path = Path(db_path) if db_path else DEFAULT_DB_PATH
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(str(resolved_path)) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")

        # 1. CT Collector Raw Logs
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ct_raw (
                domain TEXT PRIMARY KEY,
                first_seen TIMESTAMP NOT NULL,
                not_before TIMESTAMP,
                tld TEXT,
                source TEXT DEFAULT 'certstream',
                processed_at TIMESTAMP
            )
            """
        )
        # Migration check: Ensure processed_at column exists in ct_raw
        cur = conn.execute("PRAGMA table_info(ct_raw)")
        columns = [row[1] for row in cur.fetchall()]
        if "processed_at" not in columns:
            conn.execute("ALTER TABLE ct_raw ADD COLUMN processed_at TIMESTAMP")
        if "not_before" not in columns:
            conn.execute("ALTER TABLE ct_raw ADD COLUMN not_before TIMESTAMP")

        # 2. Collector Runs Log
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS collector_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TIMESTAMP,
                finished_at TIMESTAMP,
                run_at TIMESTAMP,
                source TEXT,
                fetched INTEGER DEFAULT 0,
                inserted_new INTEGER DEFAULT 0,
                domains_found INTEGER,
                domains_new INTEGER,
                status TEXT,
                error_message TEXT
            )
            """
        )
        cur = conn.execute("PRAGMA table_info(collector_runs)")
        cr_cols = [row[1] for row in cur.fetchall()]
        for col_name, col_type in [
            ("started_at", "TIMESTAMP"),
            ("finished_at", "TIMESTAMP"),
            ("run_at", "TIMESTAMP"),
            ("source", "TEXT"),
            ("fetched", "INTEGER DEFAULT 0"),
            ("inserted_new", "INTEGER DEFAULT 0"),
            ("domains_found", "INTEGER"),
            ("domains_new", "INTEGER"),
        ]:
            if col_name not in cr_cols:
                try:
                    conn.execute(f"ALTER TABLE collector_runs ADD COLUMN {col_name} {col_type}")
                except Exception:
                    pass

        # 3. Domain Findings (Mode B2 / Backlog rescoring)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS domain_findings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL UNIQUE,
                first_seen TIMESTAMP NOT NULL,
                registered_at TIMESTAMP,
                registrar TEXT,
                nameservers TEXT,
                matched_brand TEXT,
                match_method TEXT,
                risk_score INTEGER,
                risk_level TEXT,
                is_live BOOLEAN DEFAULT 0,
                reasoning TEXT,
                reviewed_by_human BOOLEAN DEFAULT 0,
                human_verdict TEXT,
                in_public_blacklist_at_detection BOOLEAN,
                blacklist_checked_at TIMESTAMP,
                blacklist_listed_at TIMESTAMP
            )
            """
        )

        # 4. Message Analyses (Mode A) - UU PDP Compliant: Hash only
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS message_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                received_at TIMESTAMP NOT NULL,
                channel TEXT,
                message_hash TEXT NOT NULL,
                urls_found INTEGER,
                risk_score INTEGER,
                risk_level TEXT,
                latency_ms INTEGER,
                report_drafted BOOLEAN DEFAULT 0
            )
            """
        )

        # 5. Daily Aggregated Statistics
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_stats (
                date DATE PRIMARY KEY,
                domains_scanned INTEGER DEFAULT 0,
                domains_flagged INTEGER DEFAULT 0,
                domains_live INTEGER DEFAULT 0,
                messages_analyzed INTEGER DEFAULT 0,
                reports_drafted INTEGER DEFAULT 0,
                flagged_not_in_blacklist INTEGER DEFAULT 0,
                collector_ok BOOLEAN DEFAULT 0,
                heartbeat_ok BOOLEAN DEFAULT 0,
                peak_ram_mb INTEGER DEFAULT 0,
                tahap1_passed INTEGER DEFAULT 0,
                tahap2_passed INTEGER DEFAULT 0,
                tahap3_assessed INTEGER DEFAULT 0
            )
            """
        )
        cur = conn.execute("PRAGMA table_info(daily_stats)")
        ds_cols = [row[1] for row in cur.fetchall()]
        for col_name in ["tahap1_passed", "tahap2_passed", "tahap3_assessed"]:
            if col_name not in ds_cols:
                try:
                    conn.execute(f"ALTER TABLE daily_stats ADD COLUMN {col_name} INTEGER DEFAULT 0")
                except Exception:
                    pass

        # 6. Monitored Watchlist Table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                brand_name TEXT NOT NULL,
                official_domain TEXT NOT NULL,
                category TEXT,
                added_at TIMESTAMP
            )
            """
        )

        # 7. RDAP Lookup Cache
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rdap_cache (
                domain TEXT PRIMARY KEY,
                registration_date TEXT,
                registrar TEXT,
                nameservers TEXT,
                status TEXT,
                is_not_found INTEGER DEFAULT 0,
                fetched_at TIMESTAMP NOT NULL
            )
            """
        )

        # 8. RDAP IANA Bootstrap Cache
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rdap_bootstrap (
                tld TEXT PRIMARY KEY,
                rdap_url TEXT NOT NULL,
                fetched_at TIMESTAMP NOT NULL
            )
            """
        )

        # 9. Public Threat Intelligence Blacklist Cache
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS blacklist_cache (
                domain TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                source TEXT NOT NULL,
                details TEXT,
                checked_at TEXT NOT NULL
            )
            """
        )

        # 10. LLM Token Usage Accounting Table
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS llm_usage (
                date TEXT PRIMARY KEY,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                call_count INTEGER DEFAULT 0
            )
            """
        )

        # Indexes for query performance
        conn.execute("CREATE INDEX IF NOT EXISTS idx_domain_findings_first_seen ON domain_findings (first_seen);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_message_analyses_received_at ON message_analyses (received_at);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ct_raw_processed_at ON ct_raw (processed_at);")

        conn.commit()
        logger.info("Complete SIAGA database schema initialized successfully at %s", resolved_path)


def cleanup_retention(
    db_path: Path | str | None = None,
    retention_days: int = DEFAULT_RETENTION_DAYS,
) -> int:
    """Purge message hash records older than retention_days under UU PDP mandate.

    Args:
        db_path: Path to SQLite database.
        retention_days: Max age in days (default: 30 days).

    Returns:
        Number of purged records.
    """
    resolved_path = Path(db_path) if db_path else DEFAULT_DB_PATH
    if not resolved_path.exists():
        return 0

    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=retention_days)).isoformat()

    try:
        with sqlite3.connect(str(resolved_path)) as conn:
            # Check if table exists
            cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='message_analyses'")
            if not cur.fetchone():
                return 0

            # Delete records older than cutoff
            cur = conn.execute(
                "DELETE FROM message_analyses WHERE received_at < ?",
                (cutoff_date,),
            )
            purged_count = cur.rowcount
            conn.commit()

            if purged_count > 0:
                logger.info(
                    "UU PDP Retention Job: Purged %d expired message analysis records older than %d days (%s)",
                    purged_count,
                    retention_days,
                    cutoff_date,
                )
            return max(0, purged_count)
    except sqlite3.Error as e:
        logger.error("Error executing retention cleanup: %s", e)
        return 0
