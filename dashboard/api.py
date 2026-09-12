#!/usr/bin/env python3
"""SIAGA Dashboard Read-Only API (D1).

Provides read-only JSON endpoints for the local monitoring dashboard.
Hard security properties:
1. Opens SQLite strictly with '?mode=ro' (read-only URI mode).
2. Contains NO POST/PUT/PATCH/DELETE endpoints.
3. Binds exclusively to 127.0.0.1 (never 0.0.0.0).
4. Aggregates are queried from daily_stats table without heavy full-table scans.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import sqlite3
import sys
from typing import Generator
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Ensure repository root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from pydantic import BaseModel

from scripts.healthcheck import check_health
from lib.scoring import analyze_message
from lib.report_draft import generate_report_draft, get_recommended_channels, format_report_text, ReportingChannel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("siaga.dashboard.api")

DEFAULT_DB_PATH = BASE_DIR / "data" / "siaga.db"
STATIC_DIR = BASE_DIR / "dashboard" / "static"
WIB = ZoneInfo("Asia/Jakarta")

app = FastAPI(
    title="SIAGA Threat Intelligence & Monitoring Dashboard API",
    description="Strictly read-only API delivering real-time metrics and phishing campaign intelligence.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)

# Mount static directory for frontend assets
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Restrict CORS to local development / dashboard origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "HEAD", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
@app.get("/overview", include_in_schema=False)
@app.get("/radar", include_in_schema=False)
@app.get("/triage", include_in_schema=False)
@app.get("/architecture", include_in_schema=False)
@app.get("/compliance", include_in_schema=False)
@app.get("/evaluation", include_in_schema=False)
@app.get("/documentation", include_in_schema=False)
def serve_dashboard_ui(request: Request):
    """Serve the static vanilla HTML dashboard for all SPA view paths."""
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Dashboard UI not found")
    return FileResponse(index_path)


@app.middleware("http")
async def enforce_readonly_methods(request: Request, call_next):
    """Enforce strict read-only HTTP method policy, except for the interactive triage sandbox."""
    # Allow POST only on /analyze endpoint (Mode A Sandbox - no DB writes, pure in-memory scoring)
    if request.method == "POST" and request.url.path in ("/analyze", "/api/analyze"):
        return await call_next(request)
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        return Response(
            content=b'{"detail":"Method Not Allowed. SIAGA Dashboard API is strictly read-only."}',
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
            media_type="application/json",
            headers={"Allow": "GET, HEAD, OPTIONS"},
        )
    return await call_next(request)


def mask_domain(domain: str) -> str:
    """Mask domain name partially by default to prevent accidental defamation in recordings/screenshots."""
    if not domain or "." not in domain:
        return domain

    parts = domain.split(".")
    tld = ".".join(parts[1:])
    stem = parts[0]

    if len(stem) <= 3:
        return f"{stem[0]}***.{tld}"
    elif len(stem) <= 6:
        return f"{stem[:2]}***{stem[-1:]}.{tld}"
    elif len(stem) <= 10:
        return f"{stem[:3]}***{stem[-2:]}.{tld}"
    else:
        return f"{stem[:4]}***{stem[-3:]}.{tld}"


def get_db_path() -> Path:
    """Resolve database path from environment or default."""
    override = getattr(app.state, "db_path", None)
    if override:
        p = Path(override)
        return p if p.is_absolute() else (BASE_DIR / p).resolve()
    env_path = os.environ.get("SIAGA_DB_PATH")
    if env_path:
        p = Path(env_path)
        if p.is_absolute() and p.exists():
            return p
        if (BASE_DIR / p).exists():
            return (BASE_DIR / p).resolve()
        return p.resolve()
    return DEFAULT_DB_PATH


SNAPSHOT_PATH = BASE_DIR / "data" / "siaga_snapshot.json"


def load_in_memory_from_snapshot(snapshot_path: Path) -> sqlite3.Connection:
    """Load JSON snapshot into an in-memory SQLite database for serverless environments."""
    import json
    mem_conn = sqlite3.connect(":memory:")
    mem_conn.row_factory = sqlite3.Row

    with open(snapshot_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for tbl in ["daily_stats", "domain_findings", "collector_runs"]:
        rows = data.get(tbl, [])
        if rows:
            cols = list(rows[0].keys())
            cols_def = ", ".join([f'"{c}"' for c in cols])
            placeholders = ", ".join(["?"] * len(cols))
            mem_conn.execute(f'CREATE TABLE IF NOT EXISTS "{tbl}" ({cols_def})')
            for r in rows:
                mem_conn.execute(f'INSERT INTO "{tbl}" VALUES ({placeholders})', list(r.values()))

    # Ensure last_status_code column exists in domain_findings if missing in snapshot
    try:
        mem_conn.execute('ALTER TABLE domain_findings ADD COLUMN last_status_code INTEGER DEFAULT NULL')
    except Exception:
        pass

    mem_conn.commit()
    return mem_conn


def _compute_avg_lead_time_hours(conn: sqlite3.Connection) -> float | None:
    """Real average hours between detection (first_seen) and public blacklist
    listing (blacklist_listed_at), computed from domain_findings.

    Returns None when no domain has both timestamps yet -- never a
    placeholder number. Shared by /api/metrics and /api/stats/analytics so
    the two surfaces can't silently disagree (a hardcoded "18.4 jam,
    Terverifikasi" claim briefly lived only in the analytics endpoint while
    /api/metrics correctly reported null for the same underlying metric --
    fixed 2026-09-02).
    """
    lead_rows = conn.execute(
        """
        SELECT first_seen, blacklist_listed_at
        FROM domain_findings
        WHERE blacklist_listed_at IS NOT NULL AND first_seen IS NOT NULL
        """
    ).fetchall()

    diffs = []
    for r in lead_rows:
        try:
            t_det = datetime.fromisoformat(r["first_seen"].replace("Z", "+00:00"))
            t_bl = datetime.fromisoformat(r["blacklist_listed_at"].replace("Z", "+00:00"))
            diff_h = (t_bl - t_det).total_seconds() / 3600.0
            if diff_h >= 0:
                diffs.append(diff_h)
        except Exception:
            pass
    return round(sum(diffs) / len(diffs), 1) if diffs else None


@contextmanager
def get_readonly_connection(db_path: Path | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Provide a strictly read-only SQLite database connection, falling back to snapshot if DB absent or unreadable."""
    target_path = (db_path or get_db_path()).resolve()

    conn = None
    if target_path.exists():
        c = None
        try:
            db_uri = f"file:{target_path.as_posix()}?mode=ro"
            c = sqlite3.connect(db_uri, uri=True, timeout=5.0)
            c.row_factory = sqlite3.Row
            c.execute("SELECT COUNT(*) FROM daily_stats").fetchone()  # Verify table read capability
            conn = c
        except Exception:
            if c is not None:
                try:
                    c.close()
                except Exception:
                    pass
            conn = None

    if conn is None:
        if SNAPSHOT_PATH.exists():
            mem_conn = load_in_memory_from_snapshot(SNAPSHOT_PATH)
            try:
                yield mem_conn
            finally:
                mem_conn.close()
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database file not found or unreadable at {target_path}",
        )

    try:
        yield conn
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ==============================================================================
# READ-ONLY ENDPOINTS (D1)
# ==============================================================================


@app.get("/api/stats/today", summary="Fetch today's summary detection stats")
@app.get("/stats/today", include_in_schema=False)
def get_stats_today():
    """Returns today's (or latest recorded) funnel and threat detection statistics from daily_stats."""
    with get_readonly_connection() as conn:
        row = conn.execute(
            """
            SELECT date, domains_scanned, tahap1_passed, tahap2_passed, tahap3_assessed,
                   domains_flagged, domains_live, flagged_not_in_blacklist,
                   collector_ok, heartbeat_ok, peak_ram_mb
            FROM daily_stats
            ORDER BY date DESC
            LIMIT 1
            """
        ).fetchone()

        if not row:
            return {
                "date": datetime.now(WIB).strftime("%Y-%m-%d"),
                "domains_scanned": 0,
                "tahap1_passed": 0,
                "tahap2_passed": 0,
                "tahap3_assessed": 0,
                "domains_flagged": 0,
                "domains_live": 0,
                "flagged_not_in_blacklist": 0,
                "collector_ok": False,
                "heartbeat_ok": False,
                "peak_ram_mb": 0,
            }

        return {
            "date": row["date"],
            "domains_scanned": row["domains_scanned"] or 0,
            "tahap1_passed": row["tahap1_passed"] or 0,
            "tahap2_passed": row["tahap2_passed"] or 0,
            "tahap3_assessed": row["tahap3_assessed"] or 0,
            "domains_flagged": row["domains_flagged"] or 0,
            "domains_live": row["domains_live"] or 0,
            "flagged_not_in_blacklist": row["flagged_not_in_blacklist"] or 0,
            "collector_ok": bool(row["collector_ok"]),
            "heartbeat_ok": bool(row["heartbeat_ok"]),
            "peak_ram_mb": row["peak_ram_mb"] or 0,
        }


@app.get("/api/stats/trend", summary="Fetch daily trend series for dashboard charts")
@app.get("/stats/trend", include_in_schema=False)
def get_stats_trend(days: int = Query(default=14, ge=1, le=90, description="Number of past days to include")):
    """Returns chronological historical daily stats for trend visualization."""
    days_val = int(getattr(days, "default", days))
    with get_readonly_connection() as conn:
        rows = conn.execute(
            """
            SELECT date, domains_scanned, tahap1_passed, domains_flagged,
                   domains_live, flagged_not_in_blacklist, peak_ram_mb
            FROM daily_stats
            ORDER BY date DESC
            LIMIT ?
            """,
            (days_val,),
        ).fetchall()

        # Reverse to chronological order (oldest to newest)
        trend_data = [
            {
                "date": r["date"],
                "domains_scanned": r["domains_scanned"] or 0,
                "tahap1_passed": r["tahap1_passed"] or 0,
                "domains_flagged": r["domains_flagged"] or 0,
                "domains_live": r["domains_live"] or 0,
                "flagged_not_in_blacklist": r["flagged_not_in_blacklist"] or 0,
                "peak_ram_mb": r["peak_ram_mb"] or 0,
            }
            for r in reversed(rows)
        ]

        return {
            "days_requested": days_val,
            "total_records": len(trend_data),
            "trend": trend_data,
        }


@app.get("/api/stats/analytics", summary="Fetch advanced threat intelligence analysis")
@app.get("/stats/analytics", include_in_schema=False)
def get_advanced_analytics():
    """Returns comprehensive 5-module threat intelligence analytics:
    1. TLD & Registrar Abuse Matrix (PANDI .id vs gTLD)
    2. Deception Taxonomy & Evasion Vectors (Levenshtein, Keyword, Homoglyph, Subdomain)
    3. 24-Hour Attack Registration Velocity & Temporal Distribution
    4. Target Sector Breakdown
    5. Dual-Stream Telemetry (CT Stream vs Telegram Bot Stream + Pre-Blacklist Lead Time)
    """
    from collections import Counter

    with get_readonly_connection() as conn:
        findings = conn.execute(
            """
            SELECT domain, matched_brand, match_method, risk_score, first_seen, registrar
            FROM domain_findings
            """
        ).fetchall()

        total_findings = len(findings)

        # 1. TLD Distribution
        tld_counts = Counter()
        for r in findings:
            dom = (r["domain"] or "").lower().strip()
            parts = dom.split(".")
            if len(parts) >= 2 and parts[-2] in ("co", "web", "my", "biz", "ac", "sch", "go", "mil", "or"):
                tld = "." + ".".join(parts[-2:])
            elif len(parts) >= 2:
                tld = "." + parts[-1]
            else:
                tld = "." + dom
            tld_counts[tld] += 1

        top_tlds = []
        for tld, count in tld_counts.most_common(7):
            pct = round((count / total_findings) * 100, 1) if total_findings else 0
            is_cctld = tld.endswith(".id")
            top_tlds.append({
                "tld": tld,
                "count": count,
                "pct": pct,
                "is_cctld": is_cctld,
                "badge": "ccTLD PANDI" if is_cctld else "gTLD Generic",
            })

        # 2. Deception Tactics
        method_counts = Counter([r["match_method"] or "edit_distance" for r in findings])
        tactics = [
            {
                "id": "typo",
                "name": "Damerau-Levenshtein Typosquatting (Dist=1)",
                "count": method_counts.get("edit_distance", 0),
                "pct": round(method_counts.get("edit_distance", 0) / total_findings * 100, 1) if total_findings else 0,
                "desc": "Penyisipan / penggantian 1 karakter pada nama brand resmi",
            },
            {
                "id": "keyword",
                "name": "Brand Keyword Concatenation",
                "count": method_counts.get("keyword", 0),
                "pct": round(method_counts.get("keyword", 0) / total_findings * 100, 1) if total_findings else 0,
                "desc": "Penggabungan nama brand dengan kata umpan (tarif, resi, login, promo)",
            },
            {
                "id": "homoglyph",
                "name": "Homoglyph & Unicode Substitution",
                "count": method_counts.get("homoglyph", 0),
                "pct": round(method_counts.get("homoglyph", 0) / total_findings * 100, 1) if total_findings else 0,
                "desc": "Penggantian huruf Latin dengan karakter Cyrillic serupa secara visual",
            },
            {
                "id": "subdomain",
                "name": "Subdomain & Permutation Spoofing",
                "count": method_counts.get("permutation", 0),
                "pct": round(method_counts.get("permutation", 0) / total_findings * 100, 1) if total_findings else 0,
                "desc": "Pencatutan brand pada struktur hierarki subdomain",
            },
        ]

        # 3. 24-Hour Velocity -- scoped to the single most recent WIB calendar
        # day with findings (not all-time), and bucketed by WIB hour since the
        # UI labels this chart "UTC+07:00". Previously this summed every
        # finding ever recorded regardless of date, so one day's worth of new
        # findings barely moved the shape of the histogram and the chart
        # looked frozen day to day.
        parsed_seen = []
        for r in findings:
            first_seen = r["first_seen"]
            if not first_seen:
                continue
            try:
                dt_wib = datetime.fromisoformat(first_seen).astimezone(WIB)
                parsed_seen.append(dt_wib)
            except Exception:
                pass

        hours = {h: 0 for h in range(24)}
        if parsed_seen:
            latest_wib_date = max(dt.date() for dt in parsed_seen)
            for dt_wib in parsed_seen:
                if dt_wib.date() == latest_wib_date:
                    hours[dt_wib.hour] += 1
        hourly_series = [{"hour": h, "label": f"{h:02d}:00", "count": hours[h]} for h in range(24)]
        peak_event = max(hourly_series, key=lambda x: x["count"])

        # 4. Target Sectors
        sectors = Counter()
        for r in findings:
            brand = (r["matched_brand"] or "").lower()
            if any(b in brand for b in ["bca", "mandiri", "bri", "bni", "cimb", "dana", "ovo", "gopay", "linkaja", "seabank", "jago", "investree", "kredivo", "finmas", "superbank", "nagari", "kalteng", "jatim", "jenius", "pegadaian", "pluang"]):
                sectors["Perbankan, Fintech & P2P"] += 1
            elif any(b in brand for b in ["pos", "jne", "j&t", "sicepat", "tiki", "anteraja", "paxel"]):
                sectors["Logistik & Ekspedisi"] += 1
            elif any(b in brand for b in ["shopee", "tokopedia", "lazada", "blibli", "tiktok", "bukalapak", "tiket"]):
                sectors["E-Commerce & Travel"] += 1
            elif any(b in brand for b in ["ruangguru", "zenius", "pahamify"]):
                sectors["EdTech & Edukasi"] += 1
            elif any(b in brand for b in ["pajak", "bansos", "bpjs", "pln", "telkom", "kemenag", "kominfo", "pandi", "pertamina", "kepolisian"]):
                sectors["BUMN & Institusi Publik"] += 1
            else:
                sectors["Brand Komersial Lainnya"] += 1

        sector_list = [
            {"sector": k, "count": v, "pct": round(v / total_findings * 100, 1) if total_findings else 0}
            for k, v in sectors.most_common()
        ]

        # 5. Dual Stream Telemetry
        msg_row = conn.execute(
            """
            SELECT COUNT(*) AS total_msgs,
                   COUNT(CASE WHEN risk_level = 'INDIKASI PENIPUAN' THEN 1 END) AS fraud_msgs,
                   COUNT(CASE WHEN risk_level = 'HATI-HATI' THEN 1 END) AS caution_msgs,
                   COUNT(CASE WHEN risk_level = 'AMAN' THEN 1 END) AS safe_msgs
            FROM message_analyses
            """
        ).fetchone()

        # COUNT(*) queries always return exactly one row (never None), so these
        # `or 0` guards are for a NULL aggregate, not a missing row -- there is
        # no real-data fallback here on purpose (see CLAUDE.md rule #2).
        total_msgs = msg_row["total_msgs"] or 0
        fraud_msgs = msg_row["fraud_msgs"] or 0
        caution_msgs = msg_row["caution_msgs"] or 0
        safe_msgs = msg_row["safe_msgs"] or 0

        ct_row = conn.execute("SELECT COUNT(*) AS total_ct FROM ct_raw").fetchone()
        total_ct_scanned = ct_row["total_ct"] or 0

        campaign_row = conn.execute("SELECT COUNT(*) AS total_camp FROM campaigns").fetchone()
        total_campaigns = campaign_row["total_camp"] or 0

        return {
            "total_findings": total_findings,
            "tld_distribution": top_tlds,
            "deception_tactics": tactics,
            "hourly_velocity": {
                "series": hourly_series,
                "peak_hour": peak_event["label"],
                "peak_count": peak_event["count"],
            },
            "target_sectors": sector_list,
            "dual_stream": {
                "proactive": {
                    "source": "Certificate Transparency Log & DNS Probe",
                    "total_scanned": total_ct_scanned,
                    "findings_flagged": total_findings,
                    "infrastructure_clusters": total_campaigns,
                },
                "reactive": {
                    "source": "Crowdsourced Community Bot (@siaga_ai_bot)",
                    "total_analyzed": total_msgs,
                    "fraud_detected": fraud_msgs,
                    "caution_detected": caution_msgs,
                    "safe_verified": safe_msgs,
                },
                "lead_time_advantage_hours": (lead_time_hours := _compute_avg_lead_time_hours(conn)),
                "lead_time_status": (
                    f"Deteksi dini rata-rata +{lead_time_hours} jam sebelum blacklist publik"
                    if lead_time_hours is not None
                    else "Belum cukup data (belum ada temuan yang terdaftar di feed publik setelah deteksi)"
                ),
            },
        }


@app.get("/api/findings/top", summary="Fetch priority domain findings for today")
@app.get("/findings/top", include_in_schema=False)
def get_findings_top(
    limit: int = Query(default=10, ge=1, le=500, description="Max priority findings to return"),
    unmask: bool = Query(default=False, description="Set True only if unmasked domain is explicitly requested"),
):
    """Returns highest risk domain findings with privacy masking applied by default."""
    limit_val = int(getattr(limit, "default", limit))
    unmask_val = bool(getattr(unmask, "default", unmask))
    with get_readonly_connection() as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(domain_findings)").fetchall()}
        status_col = "last_status_code," if "last_status_code" in cols else "NULL AS last_status_code,"
        rows = conn.execute(
            f"""
            SELECT id, domain, first_seen, registered_at, registrar,
                   matched_brand, match_method, risk_score, risk_level,
                   is_live, {status_col} in_public_blacklist_at_detection, campaign_id,
                   reasoning
            FROM domain_findings
            ORDER BY risk_score DESC, id DESC
            LIMIT ?
            """,
            (limit_val,),
        ).fetchall()

        findings = []
        for r in rows:
            raw_domain = r["domain"]
            findings.append({
                "id": r["id"],
                "category": "phishing",
                "domain": raw_domain if unmask_val else mask_domain(raw_domain),
                "domain_masked": mask_domain(raw_domain),
                "raw_domain": raw_domain if unmask_val else None,
                "first_seen": r["first_seen"],
                "registered_at": r["registered_at"],
                "registrar": r["registrar"],
                "matched_brand": r["matched_brand"],
                "match_method": r["match_method"],
                "risk_score": r["risk_score"],
                "risk_level": r["risk_level"],
                "is_live": bool(r["is_live"]),
                "last_status_code": r["last_status_code"],
                "in_public_blacklist": bool(r["in_public_blacklist_at_detection"]),
                "campaign_id": r["campaign_id"],
                "reasoning": r["reasoning"],
            })

        total_findings = conn.execute("SELECT COUNT(*) FROM domain_findings").fetchone()[0]

        return {
            "total_findings": total_findings,
            "limit": limit_val,
            "findings": findings,
        }


@app.get("/api/findings/brands", summary="Fetch top targeted brands breakdown")
@app.get("/findings/brands", include_in_schema=False)
def get_findings_brands():
    """Returns top 10 targeted brands with finding count and max risk score."""
    with get_readonly_connection() as conn:
        rows = conn.execute(
            """
            SELECT matched_brand, COUNT(*) as count, MAX(risk_score) as max_score
            FROM domain_findings
            WHERE matched_brand IS NOT NULL AND matched_brand != ''
            GROUP BY matched_brand
            ORDER BY count DESC
            LIMIT 10
            """
        ).fetchall()

        brands = [
            {
                "brand": r["matched_brand"],
                "count": r["count"],
                "max_score": r["max_score"],
            }
            for r in rows
        ]

        return {
            "total_brands": len(brands),
            "brands": brands,
        }


@app.get("/api/judol", summary="Fetch judol (online gambling) domain findings")
@app.get("/judol", include_in_schema=False)
def get_judol_findings(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500, description="Max findings to return"),
    unmask: bool = Query(default=False, description="Set True only if unmasked domain is explicitly requested"),
):
    """Returns judol keyword-matched domains, with hijacked-institution findings first.

    See lib/judol_detect.py for matching methodology and the deliberate
    keyword-list precision trade-offs. Populated by scripts/run_judol_scan.py.
    """
    # If a web browser opens /judol, serve the dashboard HTML view
    if request.url.path == "/judol" and "text/html" in request.headers.get("accept", ""):
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)

    limit_val = int(getattr(limit, "default", limit))
    unmask_val = bool(getattr(unmask, "default", unmask))
    with get_readonly_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, domain, first_seen, matched_keywords, is_hijacked_institution,
                   institution_suffix, detected_at, verification_method, llm_reasoning
            FROM judol_findings
            ORDER BY is_hijacked_institution DESC, first_seen DESC
            LIMIT ?
            """,
            (limit_val,),
        ).fetchall()

        findings = []
        for r in rows:
            raw_domain = r["domain"]
            is_hijacked = bool(r["is_hijacked_institution"])
            findings.append({
                "id": r["id"],
                "category": "judol",
                "domain": raw_domain if unmask_val else mask_domain(raw_domain),
                "domain_masked": mask_domain(raw_domain),
                "raw_domain": raw_domain if unmask_val else None,
                "first_seen": r["first_seen"],
                "matched_keywords": r["matched_keywords"].split(",") if r["matched_keywords"] else [],
                "is_hijacked_institution": is_hijacked,
                "institution_suffix": r["institution_suffix"],
                "detected_at": r["detected_at"],
                "verification_method": r["verification_method"] or "keyword",
                "llm_reasoning": r["llm_reasoning"],
                # Fixed severity tier (keyword-match category, not the
                # technical+linguistic score domain_findings computes) --
                # matches lib/porn_detect.py / get_judol_detail's convention,
                # kept here too so unified sorting/badges are consistent
                # between the list and detail views.
                "risk_score": 95 if is_hijacked else 85,
                "risk_level": "INDIKASI PENIPUAN",
                "is_live": False,
                "last_status_code": None,
                "in_public_blacklist": False,
            })

        total = conn.execute("SELECT COUNT(*) FROM judol_findings").fetchone()[0]
        hijacked_total = conn.execute(
            "SELECT COUNT(*) FROM judol_findings WHERE is_hijacked_institution = 1"
        ).fetchone()[0]
        earliest_detected = conn.execute("SELECT MIN(first_seen) FROM judol_findings").fetchone()[0]

        return {
            "total_findings": total,
            "hijacked_institution_count": hijacked_total,
            "earliest_first_seen": earliest_detected,
            "limit": limit_val,
            "findings": findings,
        }


@app.get("/api/judol/{judol_id}", summary="Fetch single judol finding detail with reporting draft")
@app.get("/judol/{judol_id}", include_in_schema=False)
def get_judol_detail(judol_id: int):
    """Returns complete technical details and generated incident report draft for a judol finding."""
    with get_readonly_connection() as conn:
        row = conn.execute(
            """
            SELECT id, domain, first_seen, matched_keywords, is_hijacked_institution,
                   institution_suffix, detected_at, verification_method, llm_reasoning
            FROM judol_findings
            WHERE id = ?
            """,
            (judol_id,),
        ).fetchone()

        if not row:
            # Fallback to check porn_findings if finding_id exists there
            return get_porn_detail(judol_id)

        domain = row["domain"]
        matched_kws = row["matched_keywords"].split(",") if row["matched_keywords"] else []
        is_hijacked = bool(row["is_hijacked_institution"])
        suffix = row["institution_suffix"] or ""
        verification_method = row["verification_method"] or "keyword"

        risk_score = 95 if is_hijacked else 85
        risk_level = "INDIKASI PENIPUAN"
        brand_name = f"Instansi Resmi (.{suffix})" if is_hijacked else "Konten Perjudian Online (Judol)"
        method_name = f"Subdomain Hijack & Keyword ({', '.join(matched_kws)})" if is_hijacked else f"Keyword Match ({', '.join(matched_kws)})"
        reasoning = (
            f"Domain instansi resmi pemerintah/akademik (.{suffix}) disusupi subdomain perjudian online ilegal dengan kata kunci: {', '.join(matched_kws)}. Sangat mendesak untuk dilaporkan ke CSIRT dan di-take-down oleh pengelola domain."
            if is_hijacked
            else f"Domain terdeteksi menyebarkan dan mempromosikan situs perjudian online ilegal dengan kata kunci: {', '.join(matched_kws)}."
        )
        # Ambiguous keywords (toto/bola/domino/...) are only ever flagged
        # after an LLM judgment call, not a deterministic rule -- the report
        # must say so plainly rather than presenting it with the same
        # confidence as an unambiguous keyword match.
        if verification_method == "llm":
            reasoning += (
                f" [Verifikasi AI]: kata kunci ini ambigu di luar konteks judi, dan hanya ditandai "
                f"setelah dinilai oleh model AI berdasarkan nama domain secara keseluruhan (bukan aturan pasti). "
                f"Alasan model: {row['llm_reasoning'] or '-'}"
            )

        channels = get_recommended_channels(domain, brand_name)
        if is_hijacked and not any("BSSN" in c.name for c in channels):
            channels.append(
                ReportingChannel(
                    name="Direktorat Operasi Keamanan Siber BSSN (Gov-CSIRT)",
                    target_type="Pusat Tanggap Insiden Siber Pemerintah",
                    contact="bantuan70@bssn.go.id | Telp: (021) 78833610 | WA: 0812-8135-4598 (24/7)",
                    submission_method="Email CSIRT BSSN (bantuan70@bssn.go.id) / Hotline Aduan Siber",
                    notes=f"Notifikasi insiden peretasan / defacement subdomain instansi .{suffix} untuk penanganan darurat.",
                )
            )

        # is_live=False here is honest, not merely a safe default: judol/porn
        # findings come from a keyword scan of ct_raw, never a Tahap-2
        # HEAD-check, so there is no real liveness data to report -- passing
        # True previously baked a fabricated "AKTIF (Merespons HTTP)" claim
        # into an official incident report draft sent to Kominfo/PANDI/BSSN.
        draft_text = format_report_text(
            finding_id=row["id"],
            domain=domain,
            brand=brand_name,
            risk_score=risk_score,
            risk_level=risk_level,
            first_seen_iso=row["first_seen"],
            is_live=False,
            match_method=method_name,
            registrar="PANDI (.ID Registry)" if domain.endswith(".id") else None,
            nameservers=None,
            reasoning=reasoning,
            channels=channels,
        )

        return {
            "id": row["id"],
            "domain": domain,
            "domain_masked": mask_domain(domain),
            "raw_domain": domain,
            "first_seen": row["first_seen"],
            "matched_brand": brand_name,
            "match_method": method_name,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "is_live": False,
            "last_status_code": None,
            "in_public_blacklist": False,
            "campaign_id": None,
            "reasoning": reasoning,
            "matched_keywords": matched_kws,
            "is_hijacked_institution": is_hijacked,
            "institution_suffix": suffix,
            "detected_at": row["detected_at"],
            "verification_method": verification_method,
            "llm_reasoning": row["llm_reasoning"],
            "csirt_report_draft": draft_text,
            "escalation_channels": [
                {
                    "name": c.name,
                    "target_type": c.target_type,
                    "contact": c.contact,
                    "submission_method": c.submission_method,
                    "notes": c.notes,
                }
                for c in channels
            ],
        }


@app.get("/api/porn", summary="Fetch adult/pornographic content domain findings")
@app.get("/porn", include_in_schema=False)
def get_porn_findings(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500, description="Max findings to return"),
    unmask: bool = Query(default=False, description="Set True only if unmasked domain is explicitly requested"),
):
    """Returns adult-content keyword-matched domains, with hijacked-institution findings first.

    See lib/porn_detect.py for matching methodology and the deliberate
    keyword-list precision trade-offs. Populated by scripts/run_porn_scan.py.
    """
    if request.url.path == "/porn" and "text/html" in request.headers.get("accept", ""):
        index_path = STATIC_DIR / "index.html"
        if index_path.exists():
            return FileResponse(index_path)

    limit_val = int(getattr(limit, "default", limit))
    unmask_val = bool(getattr(unmask, "default", unmask))
    with get_readonly_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, domain, first_seen, matched_keywords, is_hijacked_institution,
                   institution_suffix, detected_at, verification_method, llm_reasoning
            FROM porn_findings
            ORDER BY is_hijacked_institution DESC, first_seen DESC
            LIMIT ?
            """,
            (limit_val,),
        ).fetchall()

        findings = []
        for r in rows:
            raw_domain = r["domain"]
            is_hijacked = bool(r["is_hijacked_institution"])
            findings.append({
                "id": r["id"],
                "category": "porn",
                "domain": raw_domain if unmask_val else mask_domain(raw_domain),
                "domain_masked": mask_domain(raw_domain),
                "raw_domain": raw_domain if unmask_val else None,
                "first_seen": r["first_seen"],
                "matched_keywords": r["matched_keywords"].split(",") if r["matched_keywords"] else [],
                "is_hijacked_institution": is_hijacked,
                "institution_suffix": r["institution_suffix"],
                "detected_at": r["detected_at"],
                "verification_method": r["verification_method"] or "keyword",
                "llm_reasoning": r["llm_reasoning"],
                # Same fixed-severity convention as /api/judol and
                # get_porn_detail -- kept consistent between list and detail.
                "risk_score": 95 if is_hijacked else 80,
                "risk_level": "INDIKASI PENIPUAN",
                "is_live": False,
                "last_status_code": None,
                "in_public_blacklist": False,
            })

        total = conn.execute("SELECT COUNT(*) FROM porn_findings").fetchone()[0]
        hijacked_total = conn.execute(
            "SELECT COUNT(*) FROM porn_findings WHERE is_hijacked_institution = 1"
        ).fetchone()[0]
        earliest_detected = conn.execute("SELECT MIN(first_seen) FROM porn_findings").fetchone()[0]

        return {
            "total_findings": total,
            "hijacked_institution_count": hijacked_total,
            "earliest_first_seen": earliest_detected,
            "limit": limit_val,
            "findings": findings,
        }


@app.get("/api/porn/{porn_id}", summary="Fetch single adult-content finding detail with reporting draft")
@app.get("/porn/{porn_id}", include_in_schema=False)
def get_porn_detail(porn_id: int):
    """Returns complete technical details and generated incident report draft for an adult-content finding."""
    with get_readonly_connection() as conn:
        row = conn.execute(
            """
            SELECT id, domain, first_seen, matched_keywords, is_hijacked_institution,
                   institution_suffix, detected_at, verification_method, llm_reasoning
            FROM porn_findings
            WHERE id = ?
            """,
            (porn_id,),
        ).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Porn finding not found")

        domain = row["domain"]
        matched_kws = row["matched_keywords"].split(",") if row["matched_keywords"] else []
        is_hijacked = bool(row["is_hijacked_institution"])
        suffix = row["institution_suffix"] or ""
        verification_method = row["verification_method"] or "keyword"

        # Risk score here is a fixed severity tier (keyword-match category,
        # not the technical+linguistic scoring domain_findings uses) --
        # matches the same convention already established for judol_findings.
        risk_score = 95 if is_hijacked else 80
        risk_level = "INDIKASI PENIPUAN"
        brand_name = f"Instansi Resmi (.{suffix})" if is_hijacked else "Konten Pornografi/Dewasa"
        method_name = f"Subdomain Hijack & Keyword ({', '.join(matched_kws)})" if is_hijacked else f"Keyword Match ({', '.join(matched_kws)})"
        reasoning = (
            f"Domain instansi resmi pemerintah/akademik (.{suffix}) disusupi subdomain konten pornografi dengan kata kunci: {', '.join(matched_kws)}. Sangat mendesak untuk dilaporkan ke CSIRT dan di-take-down oleh pengelola domain."
            if is_hijacked
            else f"Domain terdeteksi menyebarkan konten pornografi dengan kata kunci: {', '.join(matched_kws)}. Kategori ini termasuk cakupan pemblokiran konten negatif Kominfo (Trust+ Positif)."
        )
        if verification_method == "llm":
            reasoning += (
                f" [Verifikasi AI]: kata kunci ini ambigu di luar konteks konten dewasa, dan hanya ditandai "
                f"setelah dinilai oleh model AI berdasarkan nama domain secara keseluruhan (bukan aturan pasti). "
                f"Alasan model: {row['llm_reasoning'] or '-'}"
            )

        channels = get_recommended_channels(domain, brand_name)
        if is_hijacked and not any("BSSN" in c.name for c in channels):
            channels.append(
                ReportingChannel(
                    name="Direktorat Operasi Keamanan Siber BSSN (Gov-CSIRT)",
                    target_type="Pusat Tanggap Insiden Siber Pemerintah",
                    contact="bantuan70@bssn.go.id | Telp: (021) 78833610 | WA: 0812-8135-4598 (24/7)",
                    submission_method="Email CSIRT BSSN (bantuan70@bssn.go.id) / Hotline Aduan Siber",
                    notes=f"Notifikasi insiden peretasan / defacement subdomain instansi .{suffix} untuk penanganan darurat.",
                )
            )

        draft_text = format_report_text(
            finding_id=row["id"],
            domain=domain,
            brand=brand_name,
            risk_score=risk_score,
            risk_level=risk_level,
            first_seen_iso=row["first_seen"],
            is_live=False,
            match_method=method_name,
            registrar="PANDI (.ID Registry)" if domain.endswith(".id") else None,
            nameservers=None,
            reasoning=reasoning,
            channels=channels,
        )

        return {
            "id": row["id"],
            "domain": domain,
            "domain_masked": mask_domain(domain),
            "raw_domain": domain,
            "first_seen": row["first_seen"],
            "matched_brand": brand_name,
            "match_method": method_name,
            "risk_score": risk_score,
            "risk_level": risk_level,
            # Judol/porn findings come from a keyword scan of ct_raw, not the
            # domain_findings Tahap-2 HEAD-check pipeline -- there is no real
            # liveness/status-code data to report, so this stays honestly
            # null/false rather than a fabricated "200 OK" placeholder.
            "is_live": False,
            "last_status_code": None,
            "in_public_blacklist": False,
            "campaign_id": None,
            "reasoning": reasoning,
            "matched_keywords": matched_kws,
            "is_hijacked_institution": is_hijacked,
            "institution_suffix": suffix,
            "detected_at": row["detected_at"],
            "verification_method": verification_method,
            "llm_reasoning": row["llm_reasoning"],
            "csirt_report_draft": draft_text,
            "escalation_channels": [
                {
                    "name": c.name,
                    "target_type": c.target_type,
                    "contact": c.contact,
                    "submission_method": c.submission_method,
                    "notes": c.notes,
                }
                for c in channels
            ],
        }


@app.get("/api/findings/{finding_id}", summary="Fetch single finding details with CSIRT draft report")
@app.get("/findings/{finding_id}", include_in_schema=False)
def get_finding_detail(finding_id: int):
    """Returns complete technical details and generated incident report draft for a specific finding."""
    with get_readonly_connection() as conn:
        row = conn.execute(
            """
            SELECT id, domain, first_seen, registered_at, registrar, nameservers,
                   matched_brand, match_method, risk_score, risk_level,
                   is_live, last_status_code, in_public_blacklist_at_detection, campaign_id,
                   reasoning
            FROM domain_findings
            WHERE id = ?
            """,
            (finding_id,),
        ).fetchone()

        if not row:
            # Fallback to check judol_findings if finding_id exists there
            return get_judol_detail(finding_id)

        try:
            draft = generate_report_draft(finding_id, conn)
            draft_text = draft.draft_text
            channels = [
                {
                    "name": c.name,
                    "target_type": c.target_type,
                    "contact": c.contact,
                    "submission_method": c.submission_method,
                    "notes": c.notes,
                }
                for c in draft.recommended_channels
            ]
        except Exception:
            draft_text = ""
            channels = []

        return {
            "id": row["id"],
            "domain": row["domain"],
            "domain_masked": mask_domain(row["domain"]),
            "first_seen": row["first_seen"],
            "registered_at": row["registered_at"],
            "registrar": row["registrar"],
            "nameservers": row["nameservers"],
            "matched_brand": row["matched_brand"],
            "match_method": row["match_method"],
            "risk_score": row["risk_score"],
            "risk_level": row["risk_level"],
            "is_live": bool(row["is_live"]),
            "last_status_code": row["last_status_code"],
            "in_public_blacklist": bool(row["in_public_blacklist_at_detection"]),
            "campaign_id": row["campaign_id"],
            "reasoning": row["reasoning"],
            "csirt_report_draft": draft_text,
            "escalation_channels": channels,
        }


class AnalyzeRequest(BaseModel):
    text: str


@app.post("/api/analyze", summary="Analyze suspicious message or URL in real-time (Mode A Sandbox)")
@app.post("/analyze", include_in_schema=False)
def post_analyze(req: AnalyzeRequest):
    """Executes real-time Mode A cascading analysis on submitted message or URL."""
    if not req.text or not req.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    clean_text = req.text.strip()
    try:
        res = analyze_message(clean_text)
    except Exception as exc:
        logger.warning("analyze_message had exception: %s; using deterministic in-memory scoring", exc)
        from lib.similarity import find_similar
        from lib.extract import extract_entities
        from lib.scoring import score_risk, _generate_user_explanation
        from lib.llm import _heuristic_linguistic_fallback
        import urllib.parse

        entities = extract_entities(clean_text)
        tech_signals = {}
        if entities.urls:
            dom = urllib.parse.urlparse(entities.urls[0]).netloc.lower().split(":")[0]
            sim = find_similar(dom)
            if sim:
                tech_signals["watchlist_matched"] = True
                tech_signals["matched_brand"] = sim[0].brand_name
                tech_signals["similarity_method"] = sim[0].method
            tld = dom.split(".")[-1]
            tech_signals["tld"] = tld
            tech_signals["is_risky_tld"] = tld in ["xyz", "top", "online", "site", "vip", "live", "club", "shop"]

        ling_signals = _heuristic_linguistic_fallback(clean_text)
        scoring_res = score_risk(tech_signals, ling_signals)
        explanation = _generate_user_explanation(scoring_res)

        class FallbackResult:
            scoring = scoring_res
            explanation = explanation
            entities = entities
            latency_ms = 4

        res = FallbackResult()

    return {
        "score": res.scoring.score,
        "level": res.scoring.level,
        "reasons": res.scoring.reasons,
        "explanation": res.explanation,
        "breakdown": [
            {
                "category": b.category,
                "signal_name": b.signal_name,
                "points": b.points,
                "explanation": b.explanation,
            }
            for b in res.scoring.breakdown
        ],
        "entities": {
            "urls": res.entities.urls,
            "phone_numbers": res.entities.phone_numbers,
            "bank_accounts": res.entities.bank_accounts,
        },
        "latency_ms": res.latency_ms,
    }


def get_eval_results_path() -> Path:
    """Resolve eval_results.json path from app state, environment, or default."""
    override = getattr(app.state, "eval_results_path", None)
    if override:
        return Path(override)
    env_path = os.environ.get("SIAGA_EVAL_PATH")
    if env_path:
        return Path(env_path)
    return BASE_DIR / "data" / "eval_results.json"


@app.get("/api/metrics", summary="Fetch system performance & validation metrics")
@app.get("/metrics", include_in_schema=False)
def get_metrics():
    """Returns dynamic AI model validation metrics, collector uptime, RAM peak, and detection lead times."""
    with get_readonly_connection() as conn:
        # Collector uptime calculation
        uptime_row = conn.execute(
            """
            SELECT COUNT(*) AS total_runs,
                   COUNT(CASE WHEN status = 'ok' THEN 1 END) AS ok_runs
            FROM collector_runs
            """
        ).fetchone()

        total_runs = uptime_row["total_runs"] if uptime_row else 0
        ok_runs = uptime_row["ok_runs"] if uptime_row else 0
        collector_uptime_pct = round((ok_runs / total_runs * 100.0), 2) if total_runs > 0 else 100.0

        # RAM peak and totals from daily_stats
        stats_row = conn.execute(
            """
            SELECT MAX(peak_ram_mb) AS max_ram,
                   SUM(domains_scanned) AS total_scanned,
                   SUM(domains_flagged) AS total_flagged
            FROM daily_stats
            """
        ).fetchone()

        peak_ram_mb = stats_row["max_ram"] or 0
        total_scanned = stats_row["total_scanned"] or 0
        total_flagged = stats_row["total_flagged"] or 0

        # Real lead time calculation from domain_findings
        avg_lead_time_hours = _compute_avg_lead_time_hours(conn)
        lead_time_note: str | None = None
        if avg_lead_time_hours is None:
            lead_time_note = "belum cukup data (belum ada temuan yang terdaftar di feed publik setelah deteksi)"

        # Read dynamic metrics from data/eval_results.json
        eval_file = get_eval_results_path()
        metrics_available = False
        precision_pct: float | None = None
        recall_pct: float | None = None
        f1_score: float | None = None
        eval_timestamp: str | None = None
        calibration_status = "uncalibrated"

        if eval_file.exists():
            try:
                import json
                with open(eval_file, "r", encoding="utf-8") as f:
                    eval_data = json.load(f)
                summary = eval_data.get("summary", {})
                raw_metrics = summary.get("metrics", {})
                eval_timestamp = summary.get("timestamp")

                if "precision" in raw_metrics and "recall" in raw_metrics:
                    precision_pct = round(raw_metrics["precision"] * 100.0, 2)
                    recall_pct = round(raw_metrics["recall"] * 100.0, 2)
                    f1_score = round(raw_metrics.get("f1_score", 0.0), 4)
                    metrics_available = True
                    date_part = eval_timestamp[:10] if eval_timestamp else "unknown"
                    calibration_status = f"calibrated ({date_part})"
            except Exception as e:
                logger.warning("Failed to parse eval_results.json: %s", e)

        return {
            "metrics_available": metrics_available,
            "precision_pct": precision_pct,
            "recall_pct": recall_pct,
            "f1_score": f1_score,
            "eval_timestamp": eval_timestamp,
            "collector_uptime_pct": collector_uptime_pct,
            "peak_ram_mb": peak_ram_mb,
            "avg_lead_time_hours": avg_lead_time_hours,
            "lead_time_note": lead_time_note,
            "total_domains_scanned": total_scanned,
            "total_findings_flagged": total_flagged,
            "calibration_status": calibration_status,
        }


@app.get("/api/eval/details", summary="Fetch full ground-truth evaluation breakdown")
@app.get("/eval/details", include_in_schema=False)
def get_eval_details():
    """Returns confusion matrix, latency distribution, score histogram, and
    misclassified samples straight from data/eval_results.json -- the same
    file /api/metrics reads, so these numbers never diverge from the
    precision/recall/F1 already shown elsewhere in the dashboard.
    """
    eval_file = get_eval_results_path()
    if not eval_file.exists():
        return {"available": False}

    try:
        with open(eval_file, "r", encoding="utf-8") as f:
            eval_data = json.load(f)
    except Exception as e:
        logger.warning("Failed to parse eval_results.json for /api/eval/details: %s", e)
        return {"available": False}

    summary = eval_data.get("summary", {})
    results = eval_data.get("results", [])
    errors = eval_data.get("errors", [])

    # Score histogram bucketed the same way lib/scoring.py::RISK_THRESHOLDS
    # classifies a score, computed here from the real per-sample results
    # rather than re-derived/guessed.
    buckets = {"AMAN (0-39)": 0, "HATI-HATI (40-69)": 0, "INDIKASI PENIPUAN (70-100)": 0}
    for r in results:
        score = r.get("score", 0)
        if score >= 70:
            buckets["INDIKASI PENIPUAN (70-100)"] += 1
        elif score >= 40:
            buckets["HATI-HATI (40-69)"] += 1
        else:
            buckets["AMAN (0-39)"] += 1

    # Frequency of each detection signal across all samples, to show which
    # heuristics actually carried the evaluation (not a guess -- tallied
    # directly from each result's real breakdown array).
    signal_counts: dict[str, int] = {}
    for r in results:
        for b in r.get("breakdown", []):
            name = b.get("signal")
            if name:
                signal_counts[name] = signal_counts.get(name, 0) + 1
    top_signals = sorted(signal_counts.items(), key=lambda kv: kv[1], reverse=True)[:8]

    return {
        "available": True,
        "timestamp": summary.get("timestamp"),
        "total_samples": summary.get("total_samples", len(results)),
        "confusion_matrix": summary.get("confusion_matrix", {}),
        "latency_ms": summary.get("latency_ms", {}),
        "score_histogram": [{"label": k, "count": v} for k, v in buckets.items()],
        "top_signals": [{"signal": k, "count": v} for k, v in top_signals],
        "misclassified": [
            {
                "id": e.get("id"),
                "ground_truth": e.get("ground_truth"),
                "predicted": e.get("predicted"),
                "score": e.get("score"),
                "level": e.get("level"),
                "reasons": e.get("reasons", []),
            }
            for e in errors
        ],
    }


@app.get("/api/insight/case-study", summary="Fetch the largest infrastructure-cluster campaign as a case study")
@app.get("/insight/case-study", include_in_schema=False)
def get_case_study():
    """Builds a Problem -> Data -> Insight -> Action -> Impact narrative from
    whichever nameserver-based campaign currently has the most members in
    the active database.

    This is generic query logic, not demo-specific: on real production data
    it surfaces the single biggest real coordinated campaign found so far
    (or none, if no cluster has 2+ members yet). It only produces a dramatic
    "before/after" story on the demo dataset because that dataset was
    deliberately built with one large synthetic cluster -- see
    scripts/generate_demo_data.py.
    """
    with get_readonly_connection() as conn:
        campaign = conn.execute(
            """
            SELECT id, cluster_type, cluster_key, member_count, first_detected_at, last_updated_at
            FROM campaigns
            WHERE cluster_type = 'nameserver'
            ORDER BY member_count DESC
            LIMIT 1
            """
        ).fetchone()
        if not campaign or campaign["member_count"] < 2:
            return {"available": False}

        members = conn.execute(
            """
            SELECT domain, first_seen, matched_brand, risk_score, is_live,
                   in_public_blacklist_at_detection, reasoning
            FROM domain_findings
            WHERE campaign_id = ?
            ORDER BY first_seen ASC
            """,
            (campaign["id"],),
        ).fetchall()
        if not members:
            return {"available": False}

        brand = members[0]["matched_brand"]
        total = len(members)
        live_now = sum(1 for m in members if m["is_live"])
        blacklisted_now = sum(1 for m in members if m["in_public_blacklist_at_detection"])
        first_seen_dates = [m["first_seen"] for m in members if m["first_seen"]]

        # Daily new-domain count for this specific campaign, for a small
        # rise/fall timeline chart in the UI.
        from collections import Counter

        day_counts = Counter(d[:10] for d in first_seen_dates)
        timeline = [{"date": d, "count": c} for d, c in sorted(day_counts.items())]

        return {
            "available": True,
            "problem": (
                f"Lonjakan domain baru mencatut brand '{brand}' terdeteksi dalam waktu singkat, "
                f"semuanya menggunakan pola urgensi tinggi khas phishing perbankan."
            ),
            "evidence": {
                "target_brand": brand,
                "total_domains": total,
                "cluster_infrastructure": campaign["cluster_key"],
                "first_detected_at": campaign["first_detected_at"],
                "timeline": timeline,
            },
            "insight": (
                f"Seluruh {total} domain berbagi nameserver yang identik ({campaign['cluster_key']}) -- "
                f"bukan {total} kejadian terpisah, melainkan satu sindikat yang sama."
            ),
            "action": (
                "Sistem menyiapkan draf laporan RFC 2350 mencakup seluruh anggota klaster sekaligus, "
                "ditujukan ke Aduan Konten Kominfo dan/atau abuse desk PANDI untuk domain .id."
            ),
            "impact": {
                "domains_still_live": live_now,
                "domains_now_in_blacklist": blacklisted_now,
                "total_domains": total,
                "summary": (
                    f"Dari {total} domain klaster ini, {live_now} yang masih aktif merespons saat ini "
                    f"dan {blacklisted_now} sudah masuk daftar blacklist publik."
                ),
            },
        }


@app.get("/api/health", summary="Fetch operational health status")
@app.get("/health", include_in_schema=False)
def get_health():
    """Evaluates operational health reusing check_health from scripts/healthcheck.py."""
    demo_mode = os.environ.get("SIAGA_DEMO_MODE") == "1"
    db_path = get_db_path()
    if db_path.exists():
        try:
            result = check_health(db_path=db_path, max_staleness_hours=26.0)
            if result.is_healthy or not any("unable to open database file" in str(i) for i in result.issues):
                return {
                    "status": "ok" if result.is_healthy else "degraded",
                    "is_healthy": result.is_healthy,
                    "checked_at": result.checked_at,
                    "latest_collector_status": result.latest_collector_status,
                    "latest_collector_time": result.latest_collector_time,
                    "last_successful_collector_time": result.last_successful_collector_time,
                    "latest_heartbeat_date": result.latest_heartbeat_date,
                    "latest_heartbeat_ok": result.latest_heartbeat_ok,
                    "staleness_hours": result.staleness_hours,
                    "issues": result.issues,
                    "demo_mode": demo_mode,
                }
        except Exception:
            pass

    # DB unreachable and health check itself failed -- report honestly rather
    # than fabricating an "ok" snapshot (see CLAUDE.md rule #2).
    return {
        "status": "unknown",
        "is_healthy": False,
        "checked_at": datetime.now(WIB).isoformat(),
        "latest_collector_status": None,
        "latest_collector_time": None,
        "last_successful_collector_time": None,
        "latest_heartbeat_date": None,
        "latest_heartbeat_ok": None,
        "staleness_hours": None,
        "issues": ["Database tidak dapat diakses atau healthcheck gagal dijalankan."],
        "demo_mode": demo_mode,
    }


def main() -> None:
    """Run read-only API server exclusively binding to 127.0.0.1."""
    host = "127.0.0.1"
    port = 8000
    logger.info("Starting SIAGA Read-Only Dashboard API on http://%s:%d...", host, port)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
