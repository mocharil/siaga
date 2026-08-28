#!/usr/bin/env python3
"""
SIAGA CT Collector — Aliran A: .id family TLDs.

Standalone script. No OpenClaw, no LLM.
Fetches recent certificates from CT logs and stores domains in SQLite.
Designed to run daily via cron at 06:30 WIB.

Sources:
  ctlogs_id  — ctlogs.dev API, .id family TLDs (primary)
  crtsh_id   — crt.sh, .id family TLDs (fallback, reserved)
"""

from __future__ import annotations

import json
import logging
from logging.handlers import RotatingFileHandler
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CTLOGS_BASE_URL = "https://api.ctlogs.dev"
CTLOGS_ID_TLDS = ["co.id", "go.id", "ac.id", "or.id", "web.id"]
# ctlogs.dev rejects bare TLD queries (/v1/subdomains/id → 400).
# These five second-level TLDs cover the .id namespace comprehensively.
# Direct .id registrations (e.g. google.id) are rare; add a targeted
# query approach later if needed.

REQUEST_DELAY_SECONDS = 1.0
REQUEST_TIMEOUT_SECONDS = 30
MAX_PAGES_PER_TLD = 200  # Safety: 200 pages * 100 rows = 20k per TLD
USER_AGENT = "SIAGA-CT-Collector/0.1 (security research)"

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "siaga.db"
LOG_DIR = BASE_DIR / "logs"
LOG_PATH = LOG_DIR / "collector.log"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger("ct_collector")


def setup_logging(log_path: Path) -> logging.Logger:
    """Configure root logger to write to both stdout and a rotating log file."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console / stdout handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Rotating file handler: 5MB per file, max 5 backup files (mode='a')
    file_handler = RotatingFileHandler(
        str(log_path),
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
        mode="a",
    )
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    return logging.getLogger("ct_collector")

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS ct_raw (
    id              INTEGER PRIMARY KEY,
    domain          TEXT NOT NULL,
    first_seen      TIMESTAMP NOT NULL,
    not_before      TIMESTAMP,
    source          TEXT,
    processed_at    TIMESTAMP,
    UNIQUE(domain)
);
CREATE INDEX IF NOT EXISTS idx_ct_raw_unprocessed
    ON ct_raw(processed_at) WHERE processed_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_ct_raw_seen
    ON ct_raw(first_seen);

CREATE TABLE IF NOT EXISTS collector_runs (
    id              INTEGER PRIMARY KEY,
    started_at      TIMESTAMP NOT NULL,
    finished_at     TIMESTAMP,
    source          TEXT NOT NULL,
    fetched         INTEGER DEFAULT 0,
    inserted_new    INTEGER DEFAULT 0,
    status          TEXT NOT NULL CHECK(status IN ('ok', 'partial', 'failed')),
    error_message   TEXT
);
"""


def init_db(db_path: Path) -> sqlite3.Connection:
    """Create database and tables if they don't exist, and migrate schema if needed."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA_SQL)

    # In-place migration: ensure `not_before` column exists in `ct_raw`
    cursor = conn.execute("PRAGMA table_info(ct_raw)")
    columns = [row[1] for row in cursor.fetchall()]
    if "not_before" not in columns:
        conn.execute("ALTER TABLE ct_raw ADD COLUMN not_before TIMESTAMP")
        logger.info("Migrated ct_raw: added not_before column")

    conn.commit()
    return conn


def record_run(
    conn: sqlite3.Connection,
    started_at: datetime,
    finished_at: datetime,
    source: str,
    fetched: int,
    inserted_new: int,
    status: str,
    error_message: Optional[str] = None,
) -> None:
    """Record a collector run to collector_runs table."""
    conn.execute(
        """INSERT INTO collector_runs
           (started_at, finished_at, source, fetched, inserted_new, status, error_message)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            started_at.isoformat(),
            finished_at.isoformat(),
            source,
            fetched,
            inserted_new,
            status,
            error_message,
        ),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Domain normalization
# ---------------------------------------------------------------------------


def normalize_domain(raw: str) -> str:
    """Normalize a domain: lowercase, strip wildcard prefix, strip trailing dot."""
    domain = raw.strip().lower()
    if domain.startswith("*."):
        domain = domain[2:]
    if domain.endswith("."):
        domain = domain[:-1]
    return domain


def extract_domains_from_name_value(name_value: str) -> list[str]:
    """
    Extract and normalize domains from crt.sh name_value field.

    crt.sh returns SAN entries newline-separated in the name_value field,
    possibly with wildcards.  This function is used when crt.sh is the source.
    """
    domains: list[str] = []
    for line in name_value.split("\n"):
        line = line.strip()
        if line:
            normalized = normalize_domain(line)
            if normalized:
                domains.append(normalized)
    return domains


# ---------------------------------------------------------------------------
# ctlogs.dev fetcher
# ---------------------------------------------------------------------------


def _ctlogs_fetch_page(
    url: str, api_key: Optional[str] = None
) -> Optional[dict]:
    """Fetch one page from ctlogs.dev.  Returns parsed JSON or None on error."""
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 429:
            logger.warning("Rate limited (429) on %s — backing off 10s", url)
            time.sleep(10)
        else:
            logger.warning("HTTP %d from %s", e.code, url)
        return None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        logger.warning("Network error fetching %s: %s", url, e)
        return None


def _fetch_from_ctlogs(
    since: datetime,
    tlds: list[str],
    api_key: Optional[str] = None,
) -> tuple[list[tuple[str, datetime]], int, int, int]:
    """
    Fetch domains and their not_before timestamps from ctlogs.dev for the given TLDs.

    Returns (domains_with_nb, successful_tlds, partial_tlds, failed_tlds).
    """
    all_domains: dict[str, datetime] = {}
    successful_tlds = 0
    partial_tlds = 0
    failed_tlds = 0

    for tld in tlds:
        tld_domains: dict[str, datetime] = {}
        url = f"{CTLOGS_BASE_URL}/v1/subdomains/{tld}"
        page_num = 0
        reached_cutoff = False
        tld_failed = False

        while page_num < MAX_PAGES_PER_TLD:
            logger.info("Fetching .%s page %d …", tld, page_num)
            data = _ctlogs_fetch_page(url, api_key)

            if data is None:
                # Retry once after a short delay
                logger.info("Retrying .%s page %d after 5 s …", tld, page_num)
                time.sleep(5)
                data = _ctlogs_fetch_page(url, api_key)
                if data is None:
                    logger.warning(
                        "Failed .%s page %d after retry — moving on", tld, page_num
                    )
                    tld_failed = True
                    break

            rows = data.get("rows", [])
            if not rows:
                break

            for row in rows:
                not_before_str = row.get("not_before", "")
                try:
                    not_before = datetime.fromisoformat(
                        not_before_str.replace("Z", "+00:00")
                    )
                except (ValueError, AttributeError):
                    continue

                if not_before < since:
                    reached_cutoff = True
                    break

                match_domain = row.get("match", "")
                if match_domain:
                    normalized = normalize_domain(match_domain)
                    if normalized:
                        if (
                            normalized not in tld_domains
                            or not_before < tld_domains[normalized]
                        ):
                            tld_domains[normalized] = not_before

            if reached_cutoff:
                logger.info(
                    "Reached cutoff for .%s: %d domains in %d page(s)",
                    tld,
                    len(tld_domains),
                    page_num + 1,
                )
                break

            if not data.get("has_next"):
                logger.info(
                    "No more pages for .%s: %d domains in %d page(s)",
                    tld,
                    len(tld_domains),
                    page_num + 1,
                )
                break

            next_cursor = data.get("next_cursor")
            if not next_cursor:
                break

            url = f"{CTLOGS_BASE_URL}/v1/subdomains/{tld}?after={next_cursor}"
            page_num += 1
            time.sleep(REQUEST_DELAY_SECONDS)

        if tld_failed:
            if tld_domains:
                partial_tlds += 1
            else:
                failed_tlds += 1
        else:
            successful_tlds += 1

        for d, nb in tld_domains.items():
            if d not in all_domains or nb < all_domains[d]:
                all_domains[d] = nb

        time.sleep(REQUEST_DELAY_SECONDS)

    result = [(d, nb) for d, nb in all_domains.items()]
    return result, successful_tlds, partial_tlds, failed_tlds


# ---------------------------------------------------------------------------
# crt.sh fetcher (fallback — reserved slot)
# ---------------------------------------------------------------------------


def _fetch_from_crtsh(
    since: datetime,
) -> tuple[list[tuple[str, datetime]], str]:
    """Fallback: fetch from crt.sh.  Not yet implemented."""
    raise NotImplementedError("crt.sh fallback not yet implemented")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_recent_domains(
    since: datetime, source: str = "ctlogs_id"
) -> tuple[list[tuple[str, datetime]], str]:
    """
    Fetch domains and their not_before timestamps from CT logs issued since *since*.

    Args:
        since:  Only include certificates with not_before >= since.
        source: Backend selector **and** ct_raw.source tag.
                "ctlogs_id" — ctlogs.dev, .id family TLDs (Aliran A)
                "crtsh_id"  — crt.sh fallback (reserved)

    Returns:
        (domain_records, status) where status is "ok" | "partial" | "failed".
    """
    api_key = os.environ.get("CTLOGS_API_KEY")

    if source == "ctlogs_id":
        records, ok_tlds, partial_tlds, fail_tlds = _fetch_from_ctlogs(
            since, CTLOGS_ID_TLDS, api_key
        )
        if ok_tlds > 0 and partial_tlds == 0 and fail_tlds == 0:
            return records, "ok"
        elif ok_tlds > 0 or partial_tlds > 0:
            return records, "partial"
        else:
            return records, "failed"

    elif source == "crtsh_id":
        return _fetch_from_crtsh(since)

    else:
        raise ValueError(f"Unknown source: {source}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    log_path = Path(os.environ.get("SIAGA_LOG_PATH", str(LOG_PATH)))
    setup_logging(log_path)

    source = os.environ.get("CT_SOURCE", "ctlogs_id")
    db_path = Path(os.environ.get("SIAGA_DB_PATH", str(DB_PATH)))

    started_at = datetime.now(timezone.utc)
    since = started_at - timedelta(hours=24)

    logger.info("=" * 60)
    logger.info("SIAGA CT Collector — starting")
    logger.info("Source: %s | DB: %s | Log: %s", source, db_path, log_path)
    logger.info("Window: %s → %s", since.isoformat(), started_at.isoformat())
    logger.info("=" * 60)

    conn = init_db(db_path)

    fetched = 0
    inserted_new = 0
    status = "failed"
    error_message = None

    try:
        count_before = conn.execute("SELECT COUNT(*) FROM ct_raw").fetchone()[0]

        records, fetch_status = fetch_recent_domains(since, source)
        fetched = len(records)
        status = fetch_status

        now_iso = started_at.isoformat()
        for domain, not_before in records:
            nb_iso = (
                not_before.isoformat()
                if isinstance(not_before, datetime)
                else not_before
            )
            conn.execute(
                "INSERT OR IGNORE INTO ct_raw (domain, first_seen, not_before, source) "
                "VALUES (?, ?, ?, ?)",
                (domain, now_iso, nb_iso, source),
            )
        conn.commit()

        count_after = conn.execute("SELECT COUNT(*) FROM ct_raw").fetchone()[0]
        inserted_new = count_after - count_before

    except NotImplementedError as e:
        error_message = str(e)
        status = "failed"
        logger.error("Source not implemented: %s", e)
    except Exception as e:
        error_message = str(e)
        status = "failed"
        logger.error("Collector failed: %s", e, exc_info=True)

    finished_at = datetime.now(timezone.utc)

    try:
        record_run(
            conn, started_at, finished_at, source,
            fetched, inserted_new, status, error_message,
        )
    except Exception as e:
        logger.error("Failed to record run: %s", e)

    conn.close()

    # --- Print and log summary ---
    duration = (finished_at - started_at).total_seconds()
    duplicates = fetched - inserted_new

    # Structured summary line written to log file and console
    logger.info(
        "SUMMARY: timestamp=%s source=%s fetched=%d inserted_new=%d duplicates=%d status=%s duration=%.1fs",
        finished_at.isoformat(),
        source,
        fetched,
        inserted_new,
        duplicates,
        status,
        duration,
    )

    print()
    print("=" * 50)
    print(f"  SIAGA CT Collector — {status.upper()}")
    print("=" * 50)
    print(f"  Source     : {source}")
    print(f"  Duration   : {duration:.1f}s")
    print(f"  Fetched    : {fetched}")
    print(f"  New inserts: {inserted_new}")
    print(f"  Duplicates : {duplicates}")
    if error_message:
        print(f"  Error      : {error_message}")
    print("=" * 50)
    print()

    if status == "failed":
        logger.warning("Collector finished with status FAILED")
    elif status == "partial":
        logger.warning("Collector finished with status PARTIAL — some TLDs failed")
    else:
        logger.info("Collector finished successfully")

    # Always exit 0 — cron-safe.  Status is recorded in collector_runs.
    sys.exit(0)


if __name__ == "__main__":
    main()
