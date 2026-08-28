"""Public Blacklist Checker Module (T18).

Provides read-only status checking against public threat intelligence feeds (URLhaus / OpenPhish)
with SQLite caching and graceful failure handling.

CRITICAL RULES:
- Read-only: never submits, reports, or registers domains.
- Privacy: only passes domain name (never raw user messages or IPs).
- Network resilience: returns BlacklistStatus.UNKNOWN on network error/offline (never crashes).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
import json
import logging
from pathlib import Path
import sqlite3
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger("siaga.blacklist")

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "siaga.db"
URLHAUS_HOST_API = "https://urlhaus-api.abuse.ch/v1/host/"
REQUEST_TIMEOUT_SEC = 3.0

CACHE_TTL_LISTED_HOURS = 12
CACHE_TTL_NOT_LISTED_HOURS = 6


class BlacklistStatus(str, Enum):
    LISTED = "listed"
    NOT_LISTED = "not_listed"
    UNKNOWN = "unknown"


@dataclass
class BlacklistResult:
    domain: str
    status: BlacklistStatus
    source: str
    checked_at: str
    details: str | None = None


def _init_blacklist_cache(conn: sqlite3.Connection) -> None:
    """Ensure blacklist_cache table exists in SQLite database."""
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
    conn.commit()


def _get_cached_status(domain: str, db_path: Path | str) -> BlacklistResult | None:
    """Retrieve unexpired cached blacklist check from SQLite."""
    try:
        with sqlite3.connect(str(db_path)) as conn:
            _init_blacklist_cache(conn)
            cur = conn.execute(
                "SELECT domain, status, source, details, checked_at FROM blacklist_cache WHERE domain = ?",
                (domain.lower(),),
            )
            row = cur.fetchone()
            if not row:
                return None

            dom, status_str, source, details, checked_at = row
            checked_dt = datetime.fromisoformat(checked_at)
            now_dt = datetime.now(timezone.utc)

            ttl_hours = CACHE_TTL_LISTED_HOURS if status_str == BlacklistStatus.LISTED.value else CACHE_TTL_NOT_LISTED_HOURS
            if now_dt - checked_dt < timedelta(hours=ttl_hours):
                return BlacklistResult(
                    domain=dom,
                    status=BlacklistStatus(status_str),
                    source=source,
                    checked_at=checked_at,
                    details=details,
                )
    except sqlite3.Error as e:
        logger.debug("Database read error for blacklist cache: %s", e)
    return None


def _save_cached_status(result: BlacklistResult, db_path: Path | str) -> None:
    """Persist blacklist status result to SQLite cache."""
    try:
        with sqlite3.connect(str(db_path)) as conn:
            _init_blacklist_cache(conn)
            conn.execute(
                """
                INSERT OR REPLACE INTO blacklist_cache (domain, status, source, details, checked_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    result.domain.lower(),
                    result.status.value,
                    result.source,
                    result.details,
                    result.checked_at,
                ),
            )
            conn.commit()
    except sqlite3.Error as e:
        logger.debug("Database write error for blacklist cache: %s", e)


def is_listed(
    domain: str,
    db_path: Path | str | None = None,
    timeout: float = REQUEST_TIMEOUT_SEC,
    allow_network: bool = True,
) -> BlacklistResult:
    """Check if target domain is listed in public malware/phishing blacklists.

    Args:
        domain: Domain name to verify.
        db_path: Path to siaga SQLite database.
        timeout: HTTP request timeout in seconds.
        allow_network: Set False to simulate offline mode or disable outbound requests.

    Returns:
        BlacklistResult with status ('listed', 'not_listed', or 'unknown').
    """
    clean_domain = domain.strip().lower().rstrip(".")
    now_iso = datetime.now(timezone.utc).isoformat()
    resolved_db = Path(db_path) if db_path else DEFAULT_DB_PATH

    # Check cache first
    cached = _get_cached_status(clean_domain, resolved_db)
    if cached:
        return cached

    if not allow_network:
        return BlacklistResult(
            domain=clean_domain,
            status=BlacklistStatus.UNKNOWN,
            source="network_disabled",
            checked_at=now_iso,
            details="Network check disabled or offline",
        )

    # Query URLhaus Host API via POST (standard read-only API method for URLhaus)
    try:
        req_data = urllib.parse.urlencode({"host": clean_domain}).encode("utf-8")
        req = urllib.request.Request(
            URLHAUS_HOST_API,
            data=req_data,
            headers={
                "User-Agent": "SIAGA-AI-Phishing-Detector/1.0 (HackFest2026; ReadOnlyCheck)",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            query_status = data.get("query_status", "")

            if query_status == "ok":
                # Domain is found in URLhaus threat feed
                urls = data.get("urls", [])
                threat_count = len(urls)
                res = BlacklistResult(
                    domain=clean_domain,
                    status=BlacklistStatus.LISTED,
                    source="URLhaus",
                    checked_at=now_iso,
                    details=f"Listed in URLhaus with {threat_count} reported payloads",
                )
            elif query_status == "no_results":
                res = BlacklistResult(
                    domain=clean_domain,
                    status=BlacklistStatus.NOT_LISTED,
                    source="URLhaus",
                    checked_at=now_iso,
                    details="Clean in URLhaus database",
                )
            else:
                res = BlacklistResult(
                    domain=clean_domain,
                    status=BlacklistStatus.UNKNOWN,
                    source="URLhaus",
                    checked_at=now_iso,
                    details=f"URLhaus unexpected query status: {query_status}",
                )

            _save_cached_status(res, resolved_db)
            return res

    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as e:
        logger.warning("Blacklist check failed for domain %s: %s", clean_domain, e)
        # MUST return UNKNOWN on network failure; NEVER crash, NEVER assume not_listed
        return BlacklistResult(
            domain=clean_domain,
            status=BlacklistStatus.UNKNOWN,
            source="network_error",
            checked_at=now_iso,
            details=f"Network query error: {e}",
        )
    except Exception as e:
        logger.warning("Unexpected error checking blacklist for %s: %s", clean_domain, e)
        return BlacklistResult(
            domain=clean_domain,
            status=BlacklistStatus.UNKNOWN,
            source="error",
            checked_at=now_iso,
            details=str(e),
        )
