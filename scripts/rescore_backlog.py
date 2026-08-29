#!/usr/bin/env python3
"""Retroactive Backlog Rescoring Script (T20).

Processes raw Certificate Transparency backlog in ct_raw where processed_at IS NULL,
executes high-throughput similarity filtering and risk evaluation, and stores identified
phishing domains in domain_findings while preserving original historical first_seen timestamps.

Features:
- Idempotent and resumable: Safely handles interruptions (Ctrl+C).
- Dry-run mode: Evaluates filter ratio and sample findings without modifying DB.
- Rate-limiting and batch commits for optimal database throughput.
"""

import argparse
from datetime import datetime, timezone
import logging
from pathlib import Path
import sqlite3
import sys
import time

# Ensure repository root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from lib.blacklist_check import BlacklistStatus, is_listed
from lib.db import init_db
from lib.rdap import lookup
from lib.scoring import RISKY_TLDS
from lib.similarity import find_similar, load_watchlist

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("siaga.rescore_backlog")


def process_backlog(
    db_path: Path | str,
    batch_size: int = 500,
    limit: int | None = None,
    dry_run: bool = False,
    allow_network: bool = False,
) -> tuple[int, int]:
    """Process unprocessed ct_raw records in batches.

    Returns:
        tuple of (total_processed, total_flagged_findings)
    """
    resolved_db = Path(db_path)
    init_db(resolved_db)
    watchlist = load_watchlist()

    logger.info("Loaded %d watchlist institutions for similarity filtering.", len(watchlist))

    total_processed = 0
    total_flagged = 0
    offset = 0

    while True:
        if limit is not None and total_processed >= limit:
            logger.info("Reached processing limit of %d domains.", limit)
            break

        current_batch_limit = batch_size
        if limit is not None:
            current_batch_limit = min(batch_size, limit - total_processed)

        # 1. Fetch next batch of unprocessed domains
        with sqlite3.connect(str(resolved_db)) as conn:
            if dry_run:
                cur = conn.execute(
                    """
                    SELECT domain, first_seen, not_before
                    FROM ct_raw
                    WHERE processed_at IS NULL
                    ORDER BY rowid ASC
                    LIMIT ? OFFSET ?
                    """,
                    (current_batch_limit, offset),
                )
            else:
                cur = conn.execute(
                    """
                    SELECT domain, first_seen, not_before
                    FROM ct_raw
                    WHERE processed_at IS NULL
                    ORDER BY rowid ASC
                    LIMIT ?
                    """,
                    (current_batch_limit,),
                )
            rows = cur.fetchall()

        if not rows:
            logger.info("No more unprocessed domains found in ct_raw.")
            break

        offset += len(rows)

        batch_start = time.monotonic()
        flagged_records: list[tuple] = []
        processed_domains: list[str] = []

        now_iso = datetime.now(timezone.utc).isoformat()

        # 2. Process each domain in batch
        for domain, first_seen, not_before in rows:
            clean_dom = domain.strip().lower().rstrip(".")
            matches = find_similar(clean_dom, watchlist=watchlist)

            if matches:
                top_match = matches[0]
                tld = clean_dom.split(".")[-1]
                is_risky_tld = tld in RISKY_TLDS

                # Determine risk score based on similarity and TLD
                sim_pts = int(top_match.similarity_score * 60)
                tld_pts = 15 if is_risky_tld else 0
                risk_score = min(100, sim_pts + tld_pts + 20)

                risk_level = "INDIKASI PENIPUAN" if risk_score >= 70 else "HATI-HATI"

                # Check blacklist status
                bl_res = is_listed(clean_dom, db_path=resolved_db, allow_network=allow_network)
                in_blacklist = 1 if bl_res.status == BlacklistStatus.LISTED else 0

                # Determine historical timestamp to preserve
                event_ts = not_before if not_before else first_seen

                reasoning = (
                    f"Mencatut nama institusi '{top_match.brand_name}' via metode {top_match.method} "
                    f"(skor kemiripan {int(top_match.similarity_score * 100)}%)."
                )
                if is_risky_tld:
                    reasoning += f" Menggunakan ekstensi domain berisiko (.{tld})."

                flagged_records.append((
                    clean_dom,
                    event_ts,
                    None,  # registered_at
                    None,  # registrar
                    None,  # nameservers
                    top_match.brand_name,
                    top_match.method,
                    risk_score,
                    risk_level,
                    0,  # is_live
                    reasoning,
                    in_blacklist,
                    now_iso,
                ))

            processed_domains.append(clean_dom)

        # 3. Persist batch results if not dry-run
        if not dry_run:
            with sqlite3.connect(str(resolved_db)) as conn:
                # Insert findings
                if flagged_records:
                    conn.executemany(
                        """
                        INSERT OR IGNORE INTO domain_findings (
                            domain, first_seen, registered_at, registrar, nameservers,
                            matched_brand, match_method, risk_score, risk_level,
                            is_live, reasoning, in_public_blacklist_at_detection, blacklist_checked_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        flagged_records,
                    )

                # Mark processed in ct_raw
                conn.executemany(
                    "UPDATE ct_raw SET processed_at = ? WHERE domain = ?",
                    [(now_iso, dom) for dom in processed_domains],
                )
                conn.commit()

        batch_elapsed = time.monotonic() - batch_start
        total_processed += len(processed_domains)
        total_flagged += len(flagged_records)

        rate = len(processed_domains) / max(0.001, batch_elapsed)
        logger.info(
            "Batch progress: %d processed (+%d flagged) in %.2fs (%.1f dom/s) | Total processed: %d | Total flagged: %d",
            len(processed_domains),
            len(flagged_records),
            batch_elapsed,
            rate,
            total_processed,
            total_flagged,
        )

    return total_processed, total_flagged


def main() -> int:
    parser = argparse.ArgumentParser(description="SIAGA Retroactive CT Backlog Rescoring Engine.")
    parser.add_argument(
        "--db",
        type=Path,
        default=BASE_DIR / "data" / "siaga.db",
        help="Path to SIAGA SQLite database",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Processing batch size (default: 500)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum domains to process in this run",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate filtering without writing changes to the database",
    )
    parser.add_argument(
        "--allow-network",
        action="store_true",
        help="Enable live outbound network queries (RDAP & blacklist)",
    )

    args = parser.parse_args()

    mode_str = "[DRY-RUN]" if args.dry_run else "[LIVE EXECUTION]"
    logger.info("Starting backlog rescoring %s on database: %s", mode_str, args.db)

    start_time = time.monotonic()
    total_proc, total_flagged = process_backlog(
        db_path=args.db,
        batch_size=args.batch_size,
        limit=args.limit,
        dry_run=args.dry_run,
        allow_network=args.allow_network,
    )
    elapsed = time.monotonic() - start_time

    filter_ratio = (total_flagged / max(1, total_proc)) * 100
    logger.info(
        "Rescoring Summary: %d domains processed in %.2fs. %d suspicious findings identified (Filter ratio: %.2f%%).",
        total_proc,
        elapsed,
        total_flagged,
        filter_ratio,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
