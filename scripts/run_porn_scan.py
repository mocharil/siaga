#!/usr/bin/env python3
"""Run Adult Content Domain Scan CLI.

Standalone, idempotent re-run over the current ct_raw table. Safe to invoke
on its own or after every collector run -- it only ever adds or refreshes
porn_findings rows, never removes them.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from lib.db import init_db
from lib.porn_detect import scan_ct_raw

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("siaga.run_porn_scan")


def main() -> None:
    parser = argparse.ArgumentParser(description="SIAGA Adult Content Domain Scan")
    parser.add_argument("--db-path", type=Path, default=BASE_DIR / "data" / "siaga.db")
    parser.add_argument(
        "--allow-llm",
        action="store_true",
        default=False,
        help="Also verify ambiguous-keyword candidates (kontol, toket, memek, ewe) via LLM judgment. Costs LLM budget.",
    )
    args = parser.parse_args()

    init_db(args.db_path)
    summary = scan_ct_raw(db_path=args.db_path, allow_llm=args.allow_llm)

    print("\n" + "=" * 60)
    print("      SIAGA ADULT CONTENT DOMAIN SCAN RESULTS")
    print("=" * 60)
    print(f"Domains scanned              : {summary.domains_scanned}")
    print(f"Domains flagged (adult)      : {summary.domains_flagged}")
    print(f"  hijacked institutions      : {summary.hijacked_institutions_flagged}")
    print(f"Newly inserted this run      : {summary.newly_inserted}")
    if args.allow_llm:
        print(f"LLM candidates checked       : {summary.llm_candidates_checked}")
        print(f"LLM confirmed                : {summary.llm_confirmed}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
