#!/usr/bin/env python3
"""UU PDP Data Retention Enforcement Script.

Executes scheduled cleanup of message analysis records older than 30 days.
Can be executed via cron or heartbeat scheduler.
"""

import argparse
import logging
from pathlib import Path
import sys

# Ensure repository root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from lib.db import cleanup_retention, init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("siaga.retention_job")


def main() -> int:
    parser = argparse.ArgumentParser(description="Enforce UU PDP 30-day message hash retention.")
    parser.add_argument(
        "--db",
        type=Path,
        default=BASE_DIR / "data" / "siaga.db",
        help="Path to SIAGA SQLite database",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Retention limit in days (default: 30)",
    )
    args = parser.parse_args()

    init_db(args.db)
    logger.info("Running UU PDP data retention cleanup job (retention limit: %d days)...", args.days)
    purged = cleanup_retention(args.db, retention_days=args.days)
    logger.info("Job completed successfully. Total records purged: %d", purged)
    return 0


if __name__ == "__main__":
    sys.exit(main())
