#!/usr/bin/env python3
"""Daily Cycle Orchestrator (T24/T25).

Single command the heartbeat invokes: run the tiered pipeline for today,
cluster findings into campaigns, format the daily brief, and send it to
the project owner on Telegram. Every step is deterministic Python; the
only place an LLM is involved is inside run_tiered_pipeline's Tahap 3
(per-candidate synthesis), never in composing the brief itself.

Sets daily_stats.heartbeat_ok = 1 only if the brief was actually
delivered — a pipeline success with a failed Telegram send is NOT
reported as a healthy day, since T26's healthcheck reads this column.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import sqlite3
import sys

# The brief (lib/daily_brief.py) intentionally includes emoji (matches
# plan/02's template). Windows' console defaults to cp1252, which cannot
# encode them -- crashing print() after everything else already succeeded
# and was persisted. Force UTF-8 stdout/stderr; harmless on Linux (VPS),
# where UTF-8 is already the default.
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from lib.campaign import apply_campaign_labels
from lib.daily_brief import format_daily_brief
from lib.db import init_db
from lib.pipeline import run_tiered_pipeline
from lib.telegram_notify import TelegramNotifyError, send_message

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("siaga.run_daily_cycle")


def _mark_heartbeat_ok(db_path: Path, target_date: str, ok: bool) -> None:
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "UPDATE daily_stats SET heartbeat_ok = ? WHERE date = ?",
            (1 if ok else 0, target_date),
        )
        conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="SIAGA Daily Cycle Orchestrator (T24/T25)")
    parser.add_argument("--date", type=str, default=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    parser.add_argument("--db-path", type=Path, default=BASE_DIR / "data" / "siaga.db")
    parser.add_argument("--watchlist", type=Path, default=BASE_DIR / "data" / "watchlist.csv")
    parser.add_argument("--allow-network", action="store_true", default=True)
    parser.add_argument("--no-network", dest="allow_network", action="store_false")
    parser.add_argument("--no-llm", action="store_true", default=False)
    parser.add_argument("--chat-id", type=str, default=os.environ.get("SIAGA_OWNER_CHAT_ID"))
    parser.add_argument("--skip-send", action="store_true", default=False,
                         help="Compute and print the brief but do not send to Telegram (for testing).")
    args = parser.parse_args()

    init_db(args.db_path)

    logger.info("=== SIAGA daily cycle: %s ===", args.date)

    logger.info("Step 1/3: running tiered pipeline...")
    metrics = run_tiered_pipeline(
        target_date=args.date,
        db_path=args.db_path,
        watchlist_path=args.watchlist,
        allow_network=args.allow_network,
        allow_llm=not args.no_llm,
        dry_run=False,
    )
    logger.info("Pipeline done: %s", metrics.summary_ratio())

    logger.info("Step 2/3: clustering campaigns...")
    campaign_summary = apply_campaign_labels(db_path=args.db_path)
    logger.info(
        "Clustering done: %d nameserver / %d brand_pattern cluster(s)",
        campaign_summary.nameserver_clusters_found,
        campaign_summary.brand_pattern_clusters_found,
    )

    logger.info("Step 3/3: formatting and sending daily brief...")
    brief_text = format_daily_brief(args.date, db_path=args.db_path)
    print("\n" + "=" * 60)
    print(brief_text)
    print("=" * 60 + "\n")

    if args.skip_send:
        logger.info("--skip-send set: brief computed but not sent.")
        return

    if not args.chat_id:
        logger.error(
            "No chat ID available (pass --chat-id or set SIAGA_OWNER_CHAT_ID). "
            "Brief was computed but NOT sent."
        )
        _mark_heartbeat_ok(args.db_path, args.date, ok=False)
        sys.exit(1)

    try:
        send_message(chat_id=args.chat_id, text=brief_text)
        logger.info("Daily brief sent to Telegram.")
        _mark_heartbeat_ok(args.db_path, args.date, ok=True)
    except TelegramNotifyError as e:
        logger.error("Failed to send daily brief: %s", e)
        _mark_heartbeat_ok(args.db_path, args.date, ok=False)
        sys.exit(1)


if __name__ == "__main__":
    main()
