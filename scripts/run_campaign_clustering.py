#!/usr/bin/env python3
"""Run Campaign Clustering CLI (T23).

Standalone, idempotent re-run over the current domain_findings table.
Safe to invoke on its own (e.g. after backlog rescoring) or after every
pipeline run — it only ever adds or refreshes campaign_id labels, never
removes findings.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from lib.campaign import apply_campaign_labels
from lib.db import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("siaga.run_campaign_clustering")


def main() -> None:
    parser = argparse.ArgumentParser(description="SIAGA Campaign Clustering (T23)")
    parser.add_argument("--db-path", type=Path, default=BASE_DIR / "data" / "siaga.db")
    args = parser.parse_args()

    init_db(args.db_path)
    summary = apply_campaign_labels(db_path=args.db_path)

    print("\n" + "=" * 60)
    print("      SIAGA CAMPAIGN CLUSTERING RESULTS (T23)")
    print("=" * 60)
    print(f"Nameserver clusters found  : {summary.nameserver_clusters_found}")
    print(f"  domains labeled          : {summary.nameserver_domains_labeled}")
    print(f"Brand-pattern clusters found: {summary.brand_pattern_clusters_found}")
    print(f"  domains labeled          : {summary.brand_pattern_domains_labeled}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
