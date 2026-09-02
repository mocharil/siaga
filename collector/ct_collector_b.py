#!/usr/bin/env python3
"""
SIAGA CT Collector — Aliran B: kandidat typosquat lintas TLD global.

Standalone script. No OpenClaw, no LLM.

Kenapa desain ini, bukan "pantau semua TLD global" seperti rencana awal:
ctlogs.dev TIDAK memiliki endpoint untuk "semua sertifikat baru di bawah
TLD X" — hanya exact-domain, subdomains-of-a-domain, org search, serial,
SPKI (diverifikasi lewat request nyata pada 2026-09-02, lihat devlog).
crt.sh (JSON API maupun akses Postgres publik guest@crt.sh:5432) terbukti
tidak stabil untuk beban ini. CertStream publik sudah tidak aktif.

Pendekatan yang dipakai sebagai gantinya (mirip teknik dnstwist): generate
kandidat nama domain typosquat dari watchlist institusi Indonesia (stem
resmi + modifier umpan phishing umum) lintas TLD murah, lalu cek satu per
satu ke endpoint /v1/domain/{hostname} ctlogs.dev yang TERBUKTI berfungsi
(exact-domain lookup). Kandidat yang punya sertifikat nyata masuk ke
ct_raw dengan source="ctlogs_candidate_b" agar tetap melewati pipeline
Tahap 1-3 yang sama seperti Aliran A.

Ini bukan pengawasan pasif murni seperti Aliran A (yang membaca semua
sertifikat baru) — ini pengecekan aktif atas string yang KITA generate.
Tetap mematuhi CLAUDE.md: hanya baca data publik CT log, tidak ada request
ke domain yang diperiksa itu sendiri (HTTP HEAD dilakukan terpisah oleh
Tahap 2 pipeline, bukan di sini).
"""

from __future__ import annotations

import logging
import os
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collector.ct_collector import (  # noqa: E402
    DB_PATH,
    LOG_DIR,
    USER_AGENT,
    _acquire_lock,
    _allow_sleep,
    _prevent_sleep,
    _release_lock,
    init_db,
    record_run,
    setup_logging,
)
from lib.similarity import load_watchlist  # noqa: E402

# ---------------------------------------------------------------------------
# Configuration — tunable candidate space. Kept small deliberately: each
# candidate costs one live HTTP request at REQUEST_DELAY_SECONDS pacing,
# so the product of these three lists directly sets daily runtime.
# 214 stems x 7 (1 exact + 6 modifier) x 2 TLD =~ 3000 req =~ 50 menit.
# ---------------------------------------------------------------------------

CTLOGS_BASE_URL = "https://api.ctlogs.dev"
REQUEST_DELAY_SECONDS = 2.0
REQUEST_TIMEOUT_SECONDS = 15
MIN_STEM_LEN = 4  # selaras dengan SHORT_NAME_MAX_LEN di lib/similarity.py

# Anonymous tier ctlogs.dev ternyata membatasi jauh lebih ketat daripada
# "1 concurrent" yang didokumentasikan -- run nyata 2026-09-02 kena 429
# dalam <1 menit walau dijeda 1 req/detik. Backoff + retry per kandidat,
# dan hentikan seluruh run kalau server terus menolak (bukan menggerus
# ribuan kandidat yang pasti gagal semua).
RATE_LIMIT_BACKOFF_SECONDS = 30.0
RATE_LIMIT_MAX_RETRIES = 2
RATE_LIMIT_ABORT_THRESHOLD = 5  # 429 beruntun -> hentikan run, jangan dipaksa

# Insiden 2026-09-02: laptop kehilangan jaringan ~2 jam di tengah run, dan
# getaddrinfo Windows tidak selalu menghormati timeout urllib saat adapter
# jaringan sedang reconnect -- proses jadi macet diam tanpa error maupun
# progres selama >15 menit, harus di-kill manual. socket.setdefaulttimeout
# adalah lapisan kedua (selain REQUEST_TIMEOUT_SECONDS per-request), dan
# MAX_RUN_SECONDS adalah batas keras seluruh run supaya jaringan yang mati
# berjam-jam menghasilkan status "partial" yang jujur, bukan proses yang
# menggantung selamanya.
MAX_RUN_SECONDS = 110 * 60  # 2688 kandidat @ 2s pacing butuh ~90 menit minimum kalau lancar

CANDIDATE_TLDS = ["xyz", "top"]

# Kata umpan phishing umum di konteks perbankan/institusi Indonesia.
# Dipasang sebagai suffix (pola paling wajar diamati: "bankmandiri-verifikasi.xyz").
CANDIDATE_MODIFIERS = ["login", "verifikasi", "verify", "resmi", "secure", "update"]

LOCK_PATH = Path(__file__).resolve().parent.parent / "data" / ".collector_b.lock"
LOG_PATH = LOG_DIR / "collector_b.log"

logger = logging.getLogger("ct_collector_b")


# ---------------------------------------------------------------------------
# Candidate generation
# ---------------------------------------------------------------------------


def generate_candidates(watchlist_path: Path | str | None = None) -> list[str]:
    """Generate typosquat candidate hostnames from the institutional watchlist.

    One candidate list per official-domain stem (e.g. "bankmandiri" from
    bankmandiri.co.id), deduplicated across brands that share a stem.
    """
    entries = load_watchlist(watchlist_path)
    stems = sorted({e.off_stem for e in entries if len(e.off_stem) >= MIN_STEM_LEN})

    candidates: list[str] = []
    seen: set[str] = set()
    for stem in stems:
        names = [stem] + [f"{stem}-{mod}" for mod in CANDIDATE_MODIFIERS]
        for name in names:
            for tld in CANDIDATE_TLDS:
                host = f"{name}.{tld}"
                if host not in seen:
                    seen.add(host)
                    candidates.append(host)

    return candidates


# ---------------------------------------------------------------------------
# ctlogs.dev exact-domain lookup
# ---------------------------------------------------------------------------


class RateLimited(Exception):
    """Raised when ctlogs.dev returns 429 -- distinct from other failures so
    the caller can back off and retry instead of counting it as a dead end."""


def _check_domain(hostname: str, api_key: str | None) -> tuple[bool, str | None]:
    """Query /v1/domain/{hostname}. Returns (has_cert, earliest_not_before_iso)."""
    import json
    import urllib.error
    import urllib.request

    url = f"{CTLOGS_BASE_URL}/v1/domain/{hostname}"
    headers = {"User-Agent": USER_AGENT}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 400:
            logger.debug("Invalid hostname skipped: %s", hostname)
            return False, None
        if e.code == 429:
            raise RateLimited(f"429 checking {hostname}") from e
        raise RuntimeError(f"HTTP {e.code} checking {hostname}: {e}") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise RuntimeError(f"Network error checking {hostname}: {e}") from e

    rows = data.get("rows", [])
    if not rows:
        return False, None

    earliest = min(r["not_before"] for r in rows if r.get("not_before"))
    return True, earliest


def check_candidates(
    candidates: list[str], api_key: str | None = None
) -> tuple[list[tuple[str, str]], int, int]:
    """Check each candidate hostname for an existing certificate.

    Returns (matches, checked_count, error_count) where matches is a list
    of (hostname, not_before_iso) for candidates that DO have a cert on record.

    A 429 gets RATE_LIMIT_MAX_RETRIES retries with a fixed cooldown before
    the candidate is counted as an error. If RATE_LIMIT_ABORT_THRESHOLD
    consecutive candidates end up rate-limited even after retries, the run
    stops early -- the server is telling us no, and grinding through the
    remaining candidates would just produce more failures without result.

    Also enforces MAX_RUN_SECONDS as a wall-clock ceiling: the 2026-09-02
    incident saw a multi-hour network outage make individual checks hang
    well past REQUEST_TIMEOUT_SECONDS (Windows getaddrinfo does not always
    honor urllib's timeout while an adapter is reconnecting), leaving the
    whole run stuck with no progress and no error until killed manually.
    Remaining candidates are simply left unchecked for this run -- exact-
    domain lookup finds a historical cert whenever it's next checked, so
    a partial pass today is not lost the way a missed Aliran A day is.
    """
    matches: list[tuple[str, str]] = []
    checked = 0
    errors = 0
    consecutive_rate_limited = 0
    start_time = time.monotonic()

    for hostname in candidates:
        if time.monotonic() - start_time > MAX_RUN_SECONDS:
            logger.error(
                "MAX_RUN_SECONDS (%ds) exceeded with %d/%d candidates left unchecked; "
                "stopping instead of risking an indefinite hang.",
                MAX_RUN_SECONDS, len(candidates) - checked - errors, len(candidates),
            )
            break
        for attempt in range(RATE_LIMIT_MAX_RETRIES + 1):
            try:
                has_cert, not_before = _check_domain(hostname, api_key)
                checked += 1
                if has_cert and not_before:
                    matches.append((hostname, not_before))
                consecutive_rate_limited = 0
                break
            except RateLimited:
                if attempt < RATE_LIMIT_MAX_RETRIES:
                    logger.warning(
                        "Rate limited on %s, backing off %.0fs (attempt %d/%d)",
                        hostname, RATE_LIMIT_BACKOFF_SECONDS, attempt + 1,
                        RATE_LIMIT_MAX_RETRIES,
                    )
                    time.sleep(RATE_LIMIT_BACKOFF_SECONDS)
                    continue
                errors += 1
                consecutive_rate_limited += 1
                logger.warning("Still rate limited on %s after retries; giving up on it.", hostname)
            except RuntimeError as e:
                errors += 1
                consecutive_rate_limited = 0
                logger.warning("Check failed for %s: %s", hostname, e)
            break

        if consecutive_rate_limited >= RATE_LIMIT_ABORT_THRESHOLD:
            logger.error(
                "%d consecutive rate-limited candidates even with backoff; "
                "aborting run early instead of grinding through the rest.",
                consecutive_rate_limited,
            )
            break

        time.sleep(REQUEST_DELAY_SECONDS)

    return matches, checked, errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    log_path = Path(os.environ.get("SIAGA_LOG_PATH_B", str(LOG_PATH)))
    setup_logging(log_path)

    lock_path = Path(os.environ.get("SIAGA_COLLECTOR_B_LOCK_PATH", str(LOCK_PATH)))
    if not _acquire_lock(lock_path):
        logger.warning(
            "Another Aliran B instance appears to be running (lock: %s). Skipping.",
            lock_path,
        )
        print("\nSIAGA CT Collector B — SKIPPED (another instance already running)\n")
        sys.exit(0)

    try:
        _run(log_path)
    finally:
        _release_lock(lock_path)


def _run(log_path: Path) -> None:
    _prevent_sleep()
    # Second timeout layer: urllib's per-request timeout doesn't reliably
    # bound getaddrinfo() on Windows while a network adapter is
    # reconnecting (see MAX_RUN_SECONDS docstring). This is process-global,
    # set once here rather than per-request.
    socket.setdefaulttimeout(REQUEST_TIMEOUT_SECONDS)
    try:
        db_path = Path(os.environ.get("SIAGA_DB_PATH", str(DB_PATH)))
        api_key = os.environ.get("CTLOGS_API_KEY") or None

        started_at = datetime.now(timezone.utc)

        logger.info("=" * 60)
        logger.info("SIAGA CT Collector B (Aliran B — kandidat typosquat) — starting")
        logger.info("DB: %s | Log: %s", db_path, log_path)
        logger.info("=" * 60)

        conn = init_db(db_path)

        candidates = generate_candidates()
        logger.info("Generated %d kandidat dari watchlist.", len(candidates))

        fetched = 0
        inserted_new = 0
        status = "failed"
        error_message = None

        try:
            count_before = conn.execute("SELECT COUNT(*) FROM ct_raw").fetchone()[0]

            matches, checked, errors = check_candidates(candidates, api_key)
            fetched = checked

            now_iso = started_at.isoformat()
            for hostname, not_before in matches:
                conn.execute(
                    "INSERT OR IGNORE INTO ct_raw (domain, first_seen, not_before, source) "
                    "VALUES (?, ?, ?, ?)",
                    (hostname, now_iso, not_before, "ctlogs_candidate_b"),
                )
            conn.commit()

            count_after = conn.execute("SELECT COUNT(*) FROM ct_raw").fetchone()[0]
            inserted_new = count_after - count_before

            logger.info(
                "Selesai: %d dicek, %d cocok (punya sertifikat), %d gagal, %d baris baru.",
                checked, len(matches), errors, inserted_new,
            )

            if checked == 0:
                status = "failed"
                error_message = "No candidates checked"
            elif errors == 0:
                status = "ok"
            elif errors < checked:
                status = "partial"
            else:
                status = "failed"
                error_message = f"All {errors} checks failed"

        except Exception as e:
            error_message = str(e)
            status = "failed"
            logger.error("Collector B failed: %s", e, exc_info=True)

        finished_at = datetime.now(timezone.utc)

        try:
            record_run(
                conn, started_at, finished_at, "ctlogs_candidate_b",
                fetched, inserted_new, status, error_message,
            )
        except Exception as e:
            logger.error("Failed to record run: %s", e)

        conn.close()

        print(f"\nSIAGA CT Collector B — {status.upper()}")
        print(f"Kandidat dicek: {fetched} | Cocok baru: {inserted_new}\n")
    finally:
        _allow_sleep()


if __name__ == "__main__":
    main()
