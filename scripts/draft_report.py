#!/usr/bin/env python3
"""SIAGA Official Report Draft CLI Runner (T27).

Usage:
  python scripts/draft_report.py <finding_id_or_domain> [--output-file path]

Examples:
  python scripts/draft_report.py 529
  python scripts/draft_report.py bankbca-update.top --output-file report_529.txt
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure UTF-8 stdout
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from lib.report_draft import generate_report_draft, DEFAULT_DB_PATH


def main() -> None:
    parser = argparse.ArgumentParser(description="SIAGA Official Abuse Report Drafter (T27)")
    parser.add_argument("target", help="Finding ID (number) or domain name to draft report for")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH, help="Path to siaga SQLite database")
    parser.add_argument("--output-file", type=Path, default=None, help="Optional text file path to write draft output to")

    args = parser.parse_args()

    try:
        draft = generate_report_draft(args.target, db_path=args.db_path)
        print(draft.draft_text)

        if args.output_file:
            args.output_file.write_text(draft.draft_text, encoding="utf-8")
            print(f"\n[INFO] Draft saved successfully to {args.output_file}", file=sys.stderr)

    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
