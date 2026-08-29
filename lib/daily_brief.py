"""Daily Brief Formatting Module (T25).

Formats the Mode B daily brief per plan/02 section 4's template. Purely a
formatter: every number comes from daily_stats/domain_findings, never
generated freehand — this keeps the brief's figures machine-reproducible
and prevents an LLM from paraphrasing (and possibly drifting) the numbers.

Domain names are shown in FULL here, unlike the public dashboard (D2) or
video/article materials (plan/06), because this brief is delivered only
to the project owner via a private Telegram DM (heartbeat target="owner"),
never published. Masking is a rule for public-facing surfaces, not an
operator's own alert channel.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "siaga.db"
TOP_FINDINGS_LIMIT = 5
TREND_WINDOW_DAYS = 7


@dataclass
class DailyStatsRow:
    date: str
    domains_scanned: int
    domains_flagged: int
    domains_live: int
    flagged_not_in_blacklist: int


def _fetch_daily_stats(conn: sqlite3.Connection, target_date: str) -> DailyStatsRow | None:
    row = conn.execute(
        """
        SELECT date, domains_scanned, domains_flagged, domains_live, flagged_not_in_blacklist
        FROM daily_stats WHERE date = ?
        """,
        (target_date,),
    ).fetchone()
    if row is None:
        return None
    return DailyStatsRow(*row)


def _fetch_top_findings(conn: sqlite3.Connection, target_date: str, limit: int) -> list[dict]:
    rows = conn.execute(
        """
        SELECT df.domain, df.matched_brand, df.risk_score, df.is_live, df.reasoning,
               df.campaign_id, c.member_count, c.cluster_type
        FROM domain_findings df
        LEFT JOIN campaigns c ON df.campaign_id = c.id
        WHERE substr(df.first_seen, 1, 10) = ?
        ORDER BY df.risk_score DESC
        LIMIT ?
        """,
        (target_date, limit),
    ).fetchall()
    findings = []
    for domain, brand, score, is_live, reasoning, campaign_id, member_count, cluster_type in rows:
        findings.append({
            "domain": domain,
            "matched_brand": brand,
            "risk_score": score,
            "is_live": bool(is_live),
            "reasoning": reasoning or "",
            "campaign_member_count": member_count,
            "campaign_cluster_type": cluster_type,
        })
    return findings


def _compute_trend(conn: sqlite3.Connection, target_date: str, today_flagged: int) -> str:
    """Compare today's flagged count to the trailing N-day average
    (excluding today). Returns a human-readable Indonesian sentence, or a
    neutral note if there isn't enough history yet — never a fabricated
    percentage on thin data.
    """
    target_dt = datetime.strptime(target_date, "%Y-%m-%d")
    window_start = (target_dt - timedelta(days=TREND_WINDOW_DAYS)).strftime("%Y-%m-%d")

    rows = conn.execute(
        """
        SELECT domains_flagged FROM daily_stats
        WHERE date >= ? AND date < ?
        """,
        (window_start, target_date),
    ).fetchall()

    if len(rows) < 3:
        return "Tren: belum cukup data historis untuk dibandingkan (butuh minimal 3 hari)."

    avg_flagged = sum(r[0] for r in rows) / len(rows)
    if avg_flagged == 0:
        if today_flagged == 0:
            return "Tren: stabil, tidak ada temuan pada hari-hari sebelumnya maupun hari ini."
        return f"Tren: {today_flagged} temuan baru hari ini, dibanding rata-rata 0 pada {len(rows)} hari sebelumnya."

    pct_change = ((today_flagged - avg_flagged) / avg_flagged) * 100
    arah = "naik" if pct_change > 0 else "turun" if pct_change < 0 else "stabil pada"
    return f"Tren: {arah} {abs(pct_change):.0f}% dibanding rata-rata {len(rows)} hari terakhir."


def format_daily_brief(target_date: str, db_path: str | Path | None = None) -> str:
    """Build the Mode B daily brief text for target_date.

    Returns a plain-text message ready to send as-is. If there is no
    daily_stats row for target_date (pipeline has not run for that day),
    returns an explicit "no data" message rather than silently fabricating
    zeros — a missing day and a zero-activity day must never look the same.
    """
    resolved_db = Path(db_path) if db_path else DEFAULT_DB_PATH

    with sqlite3.connect(str(resolved_db)) as conn:
        stats = _fetch_daily_stats(conn, target_date)
        if stats is None:
            return (
                f"⚠️ SIAGA — Brief Harian, {target_date}\n\n"
                f"Tidak ada data pipeline untuk tanggal ini. Pipeline mungkin belum "
                f"dijalankan atau gagal sebelum sempat menulis daily_stats."
            )

        top_findings = _fetch_top_findings(conn, target_date, TOP_FINDINGS_LIMIT)
        trend_line = _compute_trend(conn, target_date, stats.domains_flagged)

    date_display = datetime.strptime(target_date, "%Y-%m-%d").strftime("%d %B %Y")

    lines = [
        f"🔎 SIAGA — Brief Harian, {date_display}",
        "",
        f"Dipindai   : {stats.domains_scanned:,} domain baru (24 jam terakhir)",
        f"Ditandai   : {stats.domains_flagged} mencurigakan",
        f"Prioritas  : {stats.domains_live} sudah aktif merespons (live)",
    ]

    if top_findings:
        lines.append("")
        lines.append("Temuan teratas:")
        for i, f in enumerate(top_findings, start=1):
            detail = f"{i}. {f['domain']} — mencatut '{f['matched_brand']}', skor {f['risk_score']}"
            if f["is_live"]:
                detail += ", aktif"
            if f["campaign_member_count"] and f["campaign_member_count"] > 1:
                kind = "infrastruktur sama" if f["campaign_cluster_type"] == "nameserver" else "pola sama"
                detail += f" → {kind} dengan {f['campaign_member_count'] - 1} temuan lain, indikasi satu kampanye"
            lines.append(detail)

    lines.append("")
    lines.append(trend_line)
    lines.append("Ketik /laporkan <nomor> untuk menyusun draft laporan.")

    return "\n".join(lines)
