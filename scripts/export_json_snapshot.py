#!/usr/bin/env python3
"""Export full database tables to JSON snapshot for serverless fallback."""

import json
from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "siaga.db"
OUTPUT_PATH = BASE_DIR / "data" / "siaga_snapshot.json"

def main():
    if not DB_PATH.exists():
        print(f"Error: {DB_PATH} not found")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # 1. daily_stats
    daily_stats = [dict(r) for r in conn.execute("SELECT * FROM daily_stats ORDER BY date DESC").fetchall()]

    # 2. domain_findings
    domain_findings = [dict(r) for r in conn.execute("SELECT * FROM domain_findings ORDER BY risk_score DESC, id DESC LIMIT 50").fetchall()]

    # 3. collector_runs
    collector_runs = [dict(r) for r in conn.execute("SELECT * FROM collector_runs ORDER BY id DESC LIMIT 20").fetchall()]

    # 4. summary counts
    table_counts = {}
    for t in ["ct_raw", "collector_runs", "domain_findings", "campaigns", "daily_stats"]:
        table_counts[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]

    conn.close()

    snapshot = {
        "generated_at": "2026-09-01T16:50:00+07:00",
        "table_counts": table_counts,
        "daily_stats": daily_stats,
        "domain_findings": domain_findings,
        "collector_runs": collector_runs,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)

    print(f"Snapshot written successfully to {OUTPUT_PATH} ({len(daily_stats)} daily stats, {len(domain_findings)} findings)")

if __name__ == "__main__":
    main()
