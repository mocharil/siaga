"""RDAP Lookup and Caching Module (T12).

Provides lookup() for domain registration metadata (registration date, registrar,
nameservers, and status) with IANA RDAP bootstrap routing, rate-limiting,
and SQLite-backed caching.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sqlite3
import ssl
import time
import urllib.error
import urllib.request

logger = logging.getLogger("siaga.rdap")

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "siaga.db"
DEFAULT_TIMEOUT = 5.0
DEFAULT_RATE_LIMIT_DELAY = 1.0  # seconds between outbound network requests
CACHE_TTL_FOUND = 7 * 86400     # 7 days in seconds
CACHE_TTL_NOT_FOUND = 86400     # 24 hours in seconds for 404 responses
BOOTSTRAP_TTL = 30 * 86400      # 30 days in seconds
IANA_BOOTSTRAP_URL = "https://data.iana.org/rdap/dns.json"
USER_AGENT = "SIAGA-FraudDetector/0.1 (+https://github.com/idwebhost-pandi/siaga)"

_last_request_time: float = 0.0


@dataclass
class DomainInfo:
    domain: str
    registration_date: str | None
    registrar: str | None
    nameservers: list[str] = field(default_factory=list)
    status: list[str] = field(default_factory=list)


def _init_rdap_tables(conn: sqlite3.Connection) -> None:
    """Initialize SQLite caching and bootstrap tables if they do not exist."""
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
        );
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_rdap_cache_fetched_at
        ON rdap_cache(fetched_at);
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rdap_bootstrap (
            tld TEXT PRIMARY KEY,
            rdap_url TEXT NOT NULL,
            fetched_at TIMESTAMP NOT NULL
        );
        """
    )
    conn.commit()


def _get_ssl_context() -> ssl.SSLContext:
    """Create default SSL context with full hostname and certificate verification."""
    return ssl.create_default_context()


def _throttle() -> None:
    """Enforce rate limit of at most 1 request per second."""
    global _last_request_time
    now = time.monotonic()
    elapsed = now - _last_request_time
    if elapsed < DEFAULT_RATE_LIMIT_DELAY:
        time.sleep(DEFAULT_RATE_LIMIT_DELAY - elapsed)
    _last_request_time = time.monotonic()


def _fetch_iana_bootstrap(db_path: Path) -> dict[str, str]:
    """Fetch IANA RDAP dns.json and store mapping in database with 30-day TTL."""
    logger.info("Fetching IANA RDAP bootstrap from %s", IANA_BOOTSTRAP_URL)
    _throttle()
    req = urllib.request.Request(
        IANA_BOOTSTRAP_URL,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT, context=_get_ssl_context()) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.warning("Failed to fetch IANA RDAP bootstrap: %s", e)
        return {}

    services = data.get("services", [])
    now_iso = datetime.now(timezone.utc).isoformat()
    mapping: dict[str, str] = {}

    with sqlite3.connect(str(db_path)) as conn:
        _init_rdap_tables(conn)
        for tld_list, url_list in services:
            if not url_list:
                continue
            base_url = url_list[0]
            if not base_url.endswith("/"):
                base_url += "/"
            for tld in tld_list:
                clean_tld = tld.lower().strip(".")
                mapping[clean_tld] = base_url
                conn.execute(
                    """
                    INSERT INTO rdap_bootstrap (tld, rdap_url, fetched_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(tld) DO UPDATE SET
                        rdap_url = excluded.rdap_url,
                        fetched_at = excluded.fetched_at
                    """,
                    (clean_tld, base_url, now_iso),
                )
        conn.commit()

    return mapping


def _resolve_rdap_base_url(tld: str, db_path: Path) -> str:
    """Resolve base RDAP URL for a given TLD via cached bootstrap or fallback."""
    clean_tld = tld.lower().strip(".")
    now_dt = datetime.now(timezone.utc)

    # 1. Check local cache in SQLite
    try:
        with sqlite3.connect(str(db_path)) as conn:
            _init_rdap_tables(conn)
            cur = conn.execute(
                "SELECT rdap_url, fetched_at FROM rdap_bootstrap WHERE tld = ?",
                (clean_tld,),
            )
            row = cur.fetchone()
            if row:
                rdap_url, fetched_at_str = row
                try:
                    fetched_dt = datetime.fromisoformat(fetched_at_str)
                    if (now_dt - fetched_dt).total_seconds() < BOOTSTRAP_TTL:
                        return rdap_url
                except ValueError:
                    pass
    except sqlite3.Error as e:
        logger.warning("Database error reading rdap_bootstrap: %s", e)

    # 2. Refresh bootstrap from IANA
    mapping = _fetch_iana_bootstrap(db_path)
    if clean_tld in mapping:
        return mapping[clean_tld]

    # 3. Universal fallback
    logger.debug("TLD '%s' not found in bootstrap; falling back to rdap.org", clean_tld)
    return "https://rdap.org/"


def _extract_registration_date(events: list[dict]) -> str | None:
    """Extract registration timestamp from RDAP events array."""
    for event in events:
        if isinstance(event, dict) and event.get("eventAction") == "registration":
            return event.get("eventDate")
    return None


def _extract_registrar(entities: list[dict]) -> str | None:
    """Extract registrar organization name from RDAP entities array."""
    for entity in entities:
        if not isinstance(entity, dict):
            continue
        roles = [r.lower() for r in entity.get("roles", []) if isinstance(r, str)]
        if "registrar" in roles:
            # 1. Look in vcardArray
            vcard = entity.get("vcardArray")
            if isinstance(vcard, list) and len(vcard) > 1 and isinstance(vcard[1], list):
                for item in vcard[1]:
                    if isinstance(item, list) and len(item) >= 4 and item[0] == "fn":
                        fn_val = item[3]
                        if isinstance(fn_val, str) and fn_val.strip():
                            return fn_val.strip()

            # 2. Look in handle or publicIds
            handle = entity.get("handle")
            if isinstance(handle, str) and handle.strip():
                return handle.strip()

            public_ids = entity.get("publicIds", [])
            for pid in public_ids:
                if isinstance(pid, dict) and pid.get("identifier"):
                    return str(pid.get("identifier")).strip()

    return None


def _extract_nameservers(nameservers: list[dict]) -> list[str]:
    """Extract and normalize nameservers list."""
    ns_list: list[str] = []
    for ns in nameservers:
        if isinstance(ns, dict):
            name = ns.get("ldhName") or ns.get("handle")
            if name and isinstance(name, str) and name.strip():
                clean_name = name.strip().lower().rstrip(".")
                if clean_name not in ns_list:
                    ns_list.append(clean_name)
    return ns_list


def _extract_status(status_raw: list[str]) -> list[str]:
    """Extract domain status array."""
    if isinstance(status_raw, list):
        return [str(s).strip() for s in status_raw if s]
    return []


def _parse_rdap_json(domain: str, data: dict) -> DomainInfo:
    """Parse RDAP JSON dictionary into structured DomainInfo object."""
    events = data.get("events", [])
    entities = data.get("entities", [])
    nameservers = data.get("nameservers", [])
    status = data.get("status", [])

    return DomainInfo(
        domain=domain.lower(),
        registration_date=_extract_registration_date(events),
        registrar=_extract_registrar(entities),
        nameservers=_extract_nameservers(nameservers),
        status=_extract_status(status),
    )


def lookup(
    domain: str,
    db_path: str | Path | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> DomainInfo | None:
    """Perform RDAP lookup for a domain with caching, bootstrap routing, and error resilience.

    Args:
        domain: Fully-qualified domain name to query (e.g. "google.com", "pandi.id").
        db_path: Optional path to SQLite database for caching. Defaults to data/siaga.db.
        timeout: HTTP request timeout in seconds (default: 5.0).

    Returns:
        DomainInfo if domain registration metadata was found, or None if domain was
        not found (404), query timed out, or rate-limited.
    """
    clean_domain = domain.strip().lower().rstrip(".")
    if not clean_domain or "." not in clean_domain:
        return None

    resolved_db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()

    # 1. Check cache
    try:
        with sqlite3.connect(str(resolved_db_path)) as conn:
            _init_rdap_tables(conn)
            cur = conn.execute(
                """
                SELECT registration_date, registrar, nameservers, status, is_not_found, fetched_at
                FROM rdap_cache WHERE domain = ?
                """,
                (clean_domain,),
            )
            row = cur.fetchone()
            if row:
                reg_date, registrar, ns_json, status_json, is_not_found, fetched_at_str = row
                try:
                    fetched_dt = datetime.fromisoformat(fetched_at_str)
                    age_seconds = (now_dt - fetched_dt).total_seconds()

                    if is_not_found:
                        # Negative cache TTL: 24 hours
                        if age_seconds < CACHE_TTL_NOT_FOUND:
                            logger.debug("Negative cache hit for %s (age: %.0fs)", clean_domain, age_seconds)
                            return None
                    else:
                        # Positive cache TTL: 7 days
                        if age_seconds < CACHE_TTL_FOUND:
                            logger.debug("Positive cache hit for %s (age: %.0fs)", clean_domain, age_seconds)
                            return DomainInfo(
                                domain=clean_domain,
                                registration_date=reg_date,
                                registrar=registrar,
                                nameservers=json.loads(ns_json) if ns_json else [],
                                status=json.loads(status_json) if status_json else [],
                            )
                except (ValueError, json.JSONDecodeError) as e:
                    logger.debug("Error parsing cache row for %s: %s", clean_domain, e)
    except sqlite3.Error as e:
        logger.warning("Database error querying rdap_cache: %s", e)

    # 2. Resolve RDAP query URL via bootstrap
    tld = clean_domain.split(".")[-1]
    base_url = _resolve_rdap_base_url(tld, resolved_db_path)
    query_url = f"{base_url}domain/{clean_domain}" if base_url.endswith("/") else f"{base_url}/domain/{clean_domain}"

    # 3. Perform network request with throttling & error handling
    _throttle()
    req = urllib.request.Request(
        query_url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/rdap+json, application/json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_get_ssl_context()) as resp:
            raw_body = resp.read().decode("utf-8")
            data = json.loads(raw_body)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            logger.info("Domain %s not found (HTTP 404). Caching negative result.", clean_domain)
            try:
                with sqlite3.connect(str(resolved_db_path)) as conn:
                    _init_rdap_tables(conn)
                    conn.execute(
                        """
                        INSERT INTO rdap_cache (domain, is_not_found, fetched_at)
                        VALUES (?, 1, ?)
                        ON CONFLICT(domain) DO UPDATE SET
                            is_not_found = 1,
                            fetched_at = excluded.fetched_at
                        """,
                        (clean_domain, now_iso),
                    )
                    conn.commit()
            except sqlite3.Error as db_err:
                logger.warning("Failed to store negative cache for %s: %s", clean_domain, db_err)
            return None
        elif e.code == 429:
            logger.warning("RDAP rate limit reached (HTTP 429) for %s on %s", clean_domain, query_url)
            return None
        else:
            logger.warning("RDAP HTTP error %s for %s on %s", e.code, clean_domain, query_url)
            return None
    except (urllib.error.URLError, TimeoutError) as e:
        logger.warning("RDAP network/timeout error for %s: %s", clean_domain, e)
        return None
    except Exception as e:
        logger.warning("Unexpected error during RDAP lookup for %s: %s", clean_domain, e)
        return None

    # 4. Parse result
    try:
        domain_info = _parse_rdap_json(clean_domain, data)
    except Exception as e:
        logger.warning("Failed to parse RDAP JSON for %s: %s", clean_domain, e)
        return None

    # 5. Store in positive cache (7 days TTL)
    try:
        with sqlite3.connect(str(resolved_db_path)) as conn:
            _init_rdap_tables(conn)
            conn.execute(
                """
                INSERT INTO rdap_cache (
                    domain, registration_date, registrar, nameservers, status, is_not_found, fetched_at
                )
                VALUES (?, ?, ?, ?, ?, 0, ?)
                ON CONFLICT(domain) DO UPDATE SET
                    registration_date = excluded.registration_date,
                    registrar = excluded.registrar,
                    nameservers = excluded.nameservers,
                    status = excluded.status,
                    is_not_found = 0,
                    fetched_at = excluded.fetched_at
                """,
                (
                    clean_domain,
                    domain_info.registration_date,
                    domain_info.registrar,
                    json.dumps(domain_info.nameservers),
                    json.dumps(domain_info.status),
                    now_iso,
                ),
            )
            conn.commit()
    except sqlite3.Error as db_err:
        logger.warning("Failed to save positive cache for %s: %s", clean_domain, db_err)

    return domain_info
