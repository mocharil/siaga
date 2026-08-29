"""Tiered Funnel Detection Pipeline Module (T22).

Processes raw Certificate Transparency domains from ct_raw in a 3-tier cascade:
  Tahap 1 — Saringan Kasar (Pure CPU, 0 Network, 0 LLM):
            Watchlist similarity matching (Damerau-Levenshtein, homoglyph, permutation).
  Tahap 2 — Verifikasi Teknis (HEAD-only HTTP, RDAP cache, Blacklist check, 0 LLM):
            Domain age, registrar, nameservers, live host check (HEAD-only), URLhaus status.
  Tahap 3 — Penilaian LLM (Contextual Synthesis & Risk Scoring):
            LLM contextual reasoning, final risk scoring, and storage in domain_findings.

Ratios are tracked at every stage and recorded in daily_stats.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import os
from pathlib import Path
import sqlite3
import sys
import time

import psutil

# Ensure repository root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from lib.blacklist_check import BlacklistStatus, is_listed
from lib.db import init_db
from lib.llm import LLMBudgetExceeded, LLMSchemaError, complete
from lib.rdap import DomainInfo, lookup
from lib.redirect import trace
from lib.scoring import RISK_THRESHOLDS, RISKY_TLDS, score_risk
from lib.similarity import Match, find_similar, load_watchlist

logger = logging.getLogger("siaga.pipeline")

# Windows sleep prevention flags
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


def _get_peak_ram_mb() -> int:
    """Get current resident set size memory usage in MB."""
    try:
        return int(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024))
    except Exception:
        return 50


def _prevent_sleep() -> None:
    """Request Windows OS to stay awake during pipeline execution."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED
            )
            logger.debug("Windows sleep prevention activated (ES_SYSTEM_REQUIRED)")
        except Exception as e:
            logger.warning("Could not set Windows thread execution state: %s", e)


def _allow_sleep() -> None:
    """Release Windows sleep prevention lock."""
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
            logger.debug("Windows sleep prevention released (ES_CONTINUOUS)")
        except Exception as e:
            logger.warning("Could not reset Windows thread execution state: %s", e)


@dataclass
class TieredCandidate:
    """Candidate domain progressing through the funnel."""
    domain: str
    first_seen: str
    not_before: str | None = None
    # Tahap 1 results
    matched_brand: str = ""
    match_method: str = ""
    similarity_score: float = 0.0
    # Tahap 2 results
    is_live: bool = False
    domain_age_days: int | None = None
    registered_at: str | None = None
    registrar: str | None = None
    nameservers: str | None = None
    in_blacklist: bool = False
    # Tahap 3 results
    risk_score: int = 0
    risk_level: str = "AMAN"
    reasoning: str = ""
    llm_call_succeeded: bool = False


@dataclass
class PipelineMetrics:
    """Metrics and stage counts for a pipeline run."""
    date: str
    domains_scanned: int = 0
    tahap1_passed: int = 0
    tahap2_passed: int = 0
    tahap3_assessed: int = 0
    domains_flagged: int = 0
    domains_live: int = 0
    flagged_not_in_blacklist: int = 0
    llm_calls_succeeded: int = 0
    llm_budget_capped_count: int = 0
    peak_ram_mb: int = 0
    duration_seconds: float = 0.0

    def summary_ratio(self) -> str:
        return (
            f"{self.domains_scanned:,} (scanned) -> "
            f"{self.tahap1_passed:,} (Tahap 1 similarity) -> "
            f"{self.tahap2_passed:,} (Tahap 2 technical) -> "
            f"{self.tahap3_assessed:,} (Tahap 3 LLM assessed) -> "
            f"{self.domains_flagged:,} flagged findings"
        )


def run_tiered_pipeline(
    target_date: str,
    db_path: Path | str = BASE_DIR / "data" / "siaga.db",
    watchlist_path: Path | str = BASE_DIR / "data" / "watchlist.csv",
    limit: int | None = None,
    allow_network: bool = False,
    allow_llm: bool = True,
    dry_run: bool = False,
) -> PipelineMetrics:
    """Execute 3-tier funnel pipeline on ct_raw domains for a specific date.

    Args:
        target_date: Date string 'YYYY-MM-DD' to filter ct_raw (by first_seen).
        db_path: Path to SIAGA SQLite database.
        watchlist_path: Path to institutional watchlist CSV.
        limit: Optional limit on ct_raw domains to scan.
        allow_network: Whether to permit live network calls in Tahap 2.
        allow_llm: Whether to invoke LLM in Tahap 3.
        dry_run: If True, skips database writes and only computes metrics.

    Returns:
        PipelineMetrics with counts and ratio details.
    """
    resolved_db = Path(db_path)
    init_db(resolved_db)

    _prevent_sleep()
    t0 = time.monotonic()

    metrics = PipelineMetrics(date=target_date)

    try:
        # Load watchlist institutions
        watchlist = load_watchlist(watchlist_path)
        logger.info("Loaded %d watchlist institutions for Tahap 1.", len(watchlist))

        # Fetch ct_raw domains for target_date
        with sqlite3.connect(str(resolved_db)) as conn:
            query = """
                SELECT domain, first_seen, not_before
                FROM ct_raw
                WHERE substr(first_seen, 1, 10) = ?
                ORDER BY rowid ASC
            """
            params: list = [target_date]
            if limit is not None:
                query += " LIMIT ?"
                params.append(limit)

            cur = conn.execute(query, params)
            raw_rows = cur.fetchall()

        metrics.domains_scanned = len(raw_rows)
        logger.info("Tahap 0: Fetched %d domains for %s from ct_raw.", metrics.domains_scanned, target_date)

        if metrics.domains_scanned == 0:
            logger.warning("No ct_raw records found for date %s.", target_date)
            return metrics

        # ===================================================================
        # TAHAP 1 — Saringan Kasar (Pure Local CPU, 0 Network, 0 LLM)
        # ===================================================================
        stage1_candidates: list[TieredCandidate] = []
        for dom, f_seen, not_bef in raw_rows:
            clean_dom = dom.strip().lower().rstrip(".")
            matches = find_similar(clean_dom, watchlist=watchlist)
            if matches:
                top = matches[0]
                stage1_candidates.append(
                    TieredCandidate(
                        domain=clean_dom,
                        first_seen=f_seen,
                        not_before=not_bef,
                        matched_brand=top.brand_name,
                        match_method=top.method,
                        similarity_score=top.similarity_score,
                    )
                )

        metrics.tahap1_passed = len(stage1_candidates)
        logger.info(
            "Tahap 1 Complete: %d / %d passed brand similarity filter (%.2f%%).",
            metrics.tahap1_passed,
            metrics.domains_scanned,
            (metrics.tahap1_passed / metrics.domains_scanned * 100) if metrics.domains_scanned else 0,
        )

        # ===================================================================
        # TAHAP 2 — Verifikasi Teknis (HEAD-only HTTP, RDAP cache, Blacklist)
        # ===================================================================
        stage2_candidates: list[TieredCandidate] = []
        for cand in stage1_candidates:
            clean_dom = cand.domain
            tld = clean_dom.split(".")[-1]
            is_risky_tld = tld in RISKY_TLDS

            # 1. Live status check (HEAD-only, 0 GET download)
            is_live = False
            if allow_network:
                try:
                    trace_res = trace(f"http://{clean_dom}", max_hops=1, timeout=1.5)
                    if trace_res.hops and trace_res.hops[-1].status_code < 400:
                        is_live = True
                except Exception:
                    is_live = False
            cand.is_live = is_live

            # 2. RDAP lookup (cached in SQLite)
            try:
                rdap_res = lookup(clean_dom, db_path=resolved_db, allow_network=allow_network)
                if rdap_res and rdap_res.registration_date:
                    cand.registered_at = rdap_res.registration_date
                    cand.registrar = rdap_res.registrar
                    if rdap_res.nameservers:
                        cand.nameservers = ";".join(rdap_res.nameservers)
                    try:
                        clean_iso = rdap_res.registration_date.replace("Z", "+00:00")
                        reg_dt = datetime.fromisoformat(clean_iso)
                        cand.domain_age_days = max(0, (datetime.now(timezone.utc) - reg_dt).days)
                    except Exception:
                        cand.domain_age_days = None
            except Exception as e:
                logger.debug("RDAP lookup skipped for %s: %s", clean_dom, e)

            # 3. Blacklist check (URLhaus read-only cache)
            try:
                bl_res = is_listed(clean_dom, db_path=resolved_db, allow_network=allow_network)
                cand.in_blacklist = (bl_res.status == BlacklistStatus.LISTED)
            except Exception as e:
                logger.debug("Blacklist check skipped for %s: %s", clean_dom, e)

            # Stage 2 escalation rule:
            # Escalate to Tahap 3 if:
            # - Site is live, OR
            # - Similarity score is high (>= 0.80), OR
            # - Risky TLD / young domain (age < 30 days or unknown age), OR
            # - Already listed in public blacklist
            # Drops: dead domains with old age (> 90 days) and low similarity.
            is_established_dead = (
                not cand.is_live
                and cand.domain_age_days is not None
                and cand.domain_age_days > 90
                and cand.similarity_score < 0.80
            )

            if not is_established_dead:
                stage2_candidates.append(cand)

        metrics.tahap2_passed = len(stage2_candidates)
        logger.info(
            "Tahap 2 Complete: %d / %d passed technical verification filter.",
            metrics.tahap2_passed,
            metrics.tahap1_passed,
        )

        # ===================================================================
        # TAHAP 3 — Penilaian LLM & Scoring Akhir
        # ===================================================================
        findings_to_save: list[tuple] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        DOMAIN_SUMMARY_SCHEMA = {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
            },
            "required": ["summary"],
        }

        for cand in stage2_candidates:
            clean_dom = cand.domain
            tld = clean_dom.split(".")[-1]
            is_risky_tld = tld in RISKY_TLDS
            metrics.tahap3_assessed += 1

            # Calibrated scoring — reuse the SAME engine and weights that T21
            # calibrated (lib/scoring.score_risk). Mode B has no message text,
            # so linguistic_signals is empty; every branch in score_risk()
            # reads it via .get() with defaults, so an empty dict is safe.
            technical_signals = {
                "domain_age_days": cand.domain_age_days,
                "watchlist_matched": bool(cand.matched_brand),
                "matched_brand": cand.matched_brand,
                "is_risky_tld": is_risky_tld,
                "tld": tld,
            }
            # URLhaus listing is a stronger, independent confirmation signal
            # than anything score_risk's technical dict currently models;
            # fold it in as a flat addition on top of the calibrated score
            # rather than silently dropping the information.
            scoring_result = score_risk(technical_signals, {})
            cand.risk_score = min(100, scoring_result.score + (20 if cand.in_blacklist else 0))
            if cand.risk_score >= RISK_THRESHOLDS["fraud_min"]:
                cand.risk_level = "INDIKASI PENIPUAN"
            elif cand.risk_score > RISK_THRESHOLDS["safe_max"]:
                cand.risk_level = "HATI-HATI"
            else:
                cand.risk_level = "AMAN"

            # Rule-based reasoning from the calibrated engine — always available,
            # never depends on the LLM being reachable.
            reasoning_parts = list(scoring_result.reasons)
            if cand.is_live:
                reasoning_parts.append("Domain terdeteksi aktif merespons (live).")
            if cand.in_blacklist:
                reasoning_parts.append("Terdaftar dalam blacklist publik URLhaus.")
            reasoning = " ".join(reasoning_parts)

            # Optional LLM synthesis: a one-sentence plain-language summary for
            # high-priority candidates, appended to (not replacing) the
            # rule-based reasons above. If this fails or the budget is
            # exhausted, the rule-based reasoning still stands on its own.
            if allow_llm and cand.risk_score >= 60:
                llm_prompt = (
                    f"Domain '{clean_dom}' mencatut institusi '{cand.matched_brand}' "
                    f"lewat metode {cand.match_method}. TLD berisiko: {is_risky_tld}. "
                    f"Status aktif: {cand.is_live}. Terdaftar di blacklist publik: "
                    f"{cand.in_blacklist}. Tulis satu kalimat ringkasan ancaman dalam "
                    f"bahasa Indonesia awam."
                )
                try:
                    llm_result = complete(llm_prompt, DOMAIN_SUMMARY_SCHEMA, db_path=resolved_db)
                    summary = llm_result.get("summary", "").strip()
                    if summary:
                        reasoning = f"{reasoning} {summary}".strip()
                    cand.llm_call_succeeded = True
                    metrics.llm_calls_succeeded += 1
                except LLMBudgetExceeded:
                    metrics.llm_budget_capped_count += 1
                    logger.warning("LLM daily budget exceeded at domain %s — using rule synthesis only.", clean_dom)
                except LLMSchemaError as e:
                    logger.warning("LLM schema validation failed for %s: %s — using rule synthesis only.", clean_dom, e)
                except Exception as e:
                    logger.warning("LLM call failed for %s: %s — using rule synthesis only.", clean_dom, e)

            cand.reasoning = reasoning

            # Record if risk score indicates fraud or caution
            if cand.risk_score >= 40:
                event_ts = cand.not_before if cand.not_before else cand.first_seen
                findings_to_save.append((
                    cand.domain,
                    event_ts,
                    cand.registered_at,
                    cand.registrar,
                    cand.nameservers,
                    cand.matched_brand,
                    cand.match_method,
                    cand.risk_score,
                    cand.risk_level,
                    1 if cand.is_live else 0,
                    cand.reasoning,
                    1 if cand.in_blacklist else 0,
                    now_iso,
                ))

                if cand.is_live:
                    metrics.domains_live += 1
                if not cand.in_blacklist:
                    metrics.flagged_not_in_blacklist += 1

        metrics.domains_flagged = len(findings_to_save)
        logger.info(
            "Tahap 3 Complete: %d domains flagged as suspicious (score >= 40).",
            metrics.domains_flagged,
        )

        # ===================================================================
        # Persist Findings and Daily Stats (if not dry_run)
        #
        # NOTE: daily_stats must be written even when findings_to_save is
        # empty — a day with zero flags is a legitimate, informative result,
        # not an error. Skipping the write here would silently create a gap
        # in daily_stats and undercount "total domain dipindai" in plan/05.
        # ===================================================================
        if not dry_run:
            with sqlite3.connect(str(resolved_db)) as conn:
                if findings_to_save:
                    conn.executemany(
                        """
                        INSERT INTO domain_findings (
                            domain, first_seen, registered_at, registrar, nameservers,
                            matched_brand, match_method, risk_score, risk_level,
                            is_live, reasoning, in_public_blacklist_at_detection, blacklist_checked_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(domain) DO UPDATE SET
                            risk_score = excluded.risk_score,
                            risk_level = excluded.risk_level,
                            is_live = excluded.is_live,
                            reasoning = excluded.reasoning
                        """,
                        findings_to_save,
                    )

                # Record aggregated daily stats
                metrics.peak_ram_mb = _get_peak_ram_mb()

                conn.execute(
                    """
                    INSERT INTO daily_stats (
                        date, domains_scanned, domains_flagged, domains_live,
                        flagged_not_in_blacklist, collector_ok, heartbeat_ok,
                        peak_ram_mb, tahap1_passed, tahap2_passed, tahap3_assessed
                    )
                    VALUES (?, ?, ?, ?, ?, 1, 1, ?, ?, ?, ?)
                    ON CONFLICT(date) DO UPDATE SET
                        domains_scanned = excluded.domains_scanned,
                        domains_flagged = excluded.domains_flagged,
                        domains_live = excluded.domains_live,
                        flagged_not_in_blacklist = excluded.flagged_not_in_blacklist,
                        peak_ram_mb = excluded.peak_ram_mb,
                        tahap1_passed = excluded.tahap1_passed,
                        tahap2_passed = excluded.tahap2_passed,
                        tahap3_assessed = excluded.tahap3_assessed
                    """,
                    (
                        target_date,
                        metrics.domains_scanned,
                        metrics.domains_flagged,
                        metrics.domains_live,
                        metrics.flagged_not_in_blacklist,
                        metrics.peak_ram_mb,
                        metrics.tahap1_passed,
                        metrics.tahap2_passed,
                        metrics.tahap3_assessed,
                    ),
                )
                conn.commit()

        metrics.duration_seconds = time.monotonic() - t0
        logger.info("Pipeline completed in %.2fs. Summary: %s", metrics.duration_seconds, metrics.summary_ratio())
        return metrics

    finally:
        _allow_sleep()
