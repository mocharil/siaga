#!/usr/bin/env python3
"""Run Tiered Funnel Pipeline CLI (T22).

Executes the daily 3-tier cascade pipeline for ct_raw domains and prints
the exact funnel filter ratio to standard output.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import logging
from pathlib import Path
import sys

# Ensure repository root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from lib.campaign import apply_campaign_labels
from lib.db import init_db
from lib.pipeline import run_tiered_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("siaga.run_pipeline")


def main() -> None:
    parser = argparse.ArgumentParser(description="SIAGA Tiered Funnel Detection Pipeline (T22)")
    parser.add_argument(
        "--date",
        type=str,
        default="2026-08-28",
        help="Target date in 'YYYY-MM-DD' format (default: '2026-08-28')",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=BASE_DIR / "data" / "siaga.db",
        help="Path to SIAGA SQLite database",
    )
    parser.add_argument(
        "--watchlist",
        type=Path,
        default=BASE_DIR / "data" / "watchlist.csv",
        help="Path to watchlist CSV file",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of ct_raw records to process (for testing/smoke runs)",
    )
    parser.add_argument(
        "--allow-network",
        action="store_true",
        default=False,
        help="Allow live network calls for HEAD checks and RDAP/Blacklist",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        default=False,
        help="Disable LLM synthesis in Tahap 3",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Run filtering without persisting to domain_findings or daily_stats",
    )

    args = parser.parse_args()

    logger.info("=" * 65)
    logger.info("SIAGA TIERED DETECTION PIPELINE (T22)")
    logger.info("Target Date   : %s", args.date)
    logger.info("Database      : %s", args.db_path)
    logger.info("Network Mode  : %s", "Enabled" if args.allow_network else "Disabled (Offline/Cached)")
    logger.info("LLM Synthesis : %s", "Disabled" if args.no_llm else "Enabled")
    logger.info("Dry Run Mode  : %s", "YES" if args.dry_run else "NO")
    logger.info("=" * 65)

    metrics = run_tiered_pipeline(
        target_date=args.date,
        db_path=args.db_path,
        watchlist_path=args.watchlist,
        limit=args.limit,
        allow_network=args.allow_network,
        allow_llm=not args.no_llm,
        dry_run=args.dry_run,
    )

    # Print exact ratio to stdout
    print("\n" + "=" * 65)
    print("      SIAGA TIERED FUNNEL EXECUTION RESULTS (T22)")
    print("=" * 65)
    print(f"Target Date             : {metrics.date}")
    print(f"Total Domains Scanned   : {metrics.domains_scanned:,}")
    print(f"Tahap 1 Passed (Brand)  : {metrics.tahap1_passed:,} ({metrics.tahap1_passed / max(1, metrics.domains_scanned) * 100:.2f}%)")
    print(f"Tahap 2 Passed (Tech)   : {metrics.tahap2_passed:,} ({metrics.tahap2_passed / max(1, metrics.tahap1_passed) * 100:.2f}%)")
    print(f"Tahap 3 Assessed        : {metrics.tahap3_assessed:,}")
    print(f"  of which LLM succeeded: {metrics.llm_calls_succeeded:,}")
    print(f"Domains Flagged (>=40)  : {metrics.domains_flagged:,}")
    print(f"Domains Active (Live)   : {metrics.domains_live:,}")
    print(f"Flagged (NotInBlacklist): {metrics.flagged_not_in_blacklist:,}")
    print(f"LLM Budget Capped Count : {metrics.llm_budget_capped_count:,}")
    print(f"Peak RAM Usage          : {metrics.peak_ram_mb} MB")
    print(f"Total Processing Time   : {metrics.duration_seconds:.2f} s")
    print("-" * 65)
    print("EXACT FUNNEL RATIO:")
    print(f"  {metrics.summary_ratio()}")
    print("=" * 65 + "\n")

    # T23 — cluster findings into campaigns (nameserver reuse, then brand
    # pattern) after this run's findings have been persisted. Idempotent
    # over the whole domain_findings table, not just today's batch, so a
    # campaign spanning multiple days is still caught.
    if not args.dry_run:
        campaign_summary = apply_campaign_labels(db_path=args.db_path)
        print("=" * 65)
        print("      SIAGA CAMPAIGN CLUSTERING (T23)")
        print("=" * 65)
        print(f"Nameserver clusters         : {campaign_summary.nameserver_clusters_found}")
        print(f"  domains labeled           : {campaign_summary.nameserver_domains_labeled}")
        print(f"Brand-pattern clusters      : {campaign_summary.brand_pattern_clusters_found}")
        print(f"  domains labeled           : {campaign_summary.brand_pattern_domains_labeled}")
        print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
