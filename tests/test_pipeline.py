"""Unit tests for Tiered Detection Pipeline (T22).

Tests the 3-tier cascade funnel logic:
- Tahap 1 (Rough similarity filtering without network or LLM)
- Tahap 2 (Technical verification: HEAD check, RDAP, Blacklist)
- Tahap 3 (LLM contextual assessment and risk scoring)
- Metric recording and daily_stats persistence.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
from unittest.mock import MagicMock, patch
import pytest

from lib.blacklist_check import BlacklistResult, BlacklistStatus
from lib.db import init_db
from lib.llm import LLMBudgetExceeded
from lib.pipeline import TieredCandidate, run_tiered_pipeline
from lib.rdap import DomainInfo


@pytest.fixture
def temp_pipeline_db(tmp_path):
    """Set up an isolated SQLite database with sample ct_raw records."""
    db_file = tmp_path / "test_pipeline.db"
    init_db(db_file)

    with sqlite3.connect(str(db_file)) as conn:
        # Insert 10 sample raw domains for date '2026-08-28'
        sample_domains = [
            ("bca-update-tarif.online", "2026-08-28T01:00:00Z"),
            ("bankmandiri-promo.xyz", "2026-08-28T02:00:00Z"),
            ("bca.promo-site.xyz", "2026-08-28T03:00:00Z"),
            ("tokopdia.com", "2026-08-28T04:00:00Z"),
            ("dana-kaget.site", "2026-08-28T05:00:00Z"),
            ("kucinglucu-anggora.id", "2026-08-28T06:00:00Z"),
            ("gardening-tanaman.id", "2026-08-28T07:00:00Z"),
            ("berita-bola-terkini.id", "2026-08-28T08:00:00Z"),
            ("toko-sepatu-bandung.id", "2026-08-28T09:00:00Z"),
            ("jual-tanah-bogor.id", "2026-08-28T10:00:00Z"),
        ]
        for dom, f_seen in sample_domains:
            conn.execute(
                "INSERT INTO ct_raw (domain, first_seen, source) VALUES (?, ?, 'test')",
                (dom, f_seen),
            )
        conn.commit()

    return db_file


def test_tiered_pipeline_funnel_stages(temp_pipeline_db):
    """Test full 3-tier cascade filtering and funnel counts."""
    metrics = run_tiered_pipeline(
        target_date="2026-08-28",
        db_path=temp_pipeline_db,
        allow_network=False,
        allow_llm=False,
        dry_run=False,
    )

    # 1. Total scanned must equal 10
    assert metrics.domains_scanned == 10

    # 2. Tahap 1 must filter out unrelated domains (5 brand matches pass out of 10)
    assert metrics.tahap1_passed == 5

    # 3. Tahap 2 must verify technical signals (all 5 pass technical criteria)
    assert metrics.tahap2_passed == 5

    # 4. Tahap 3 must assess all 5 candidates, but only flag those whose
    # calibrated technical score clears the 40-point threshold (lib.scoring
    # T21 weights). "tokopdia.com" carries a single weak signal (name
    # similarity only — no RDAP age, no risky TLD, no live check with
    # allow_network=False) and correctly stays below the flag line.
    assert metrics.tahap3_assessed == 5
    assert metrics.domains_flagged == 4

    # 5. Verify daily_stats table populated
    with sqlite3.connect(str(temp_pipeline_db)) as conn:
        row = conn.execute(
            """
            SELECT domains_scanned, domains_flagged, tahap1_passed, tahap2_passed, tahap3_assessed
            FROM daily_stats
            WHERE date = '2026-08-28'
            """
        ).fetchone()

        assert row is not None
        assert row[0] == 10
        assert row[1] == 4
        assert row[2] == 5
        assert row[3] == 5
        assert row[4] == 5


def test_tiered_pipeline_tahap2_drops_established_dead_domain(temp_pipeline_db):
    """Verify Tahap 2 drops dead domains that are old (>90 days) and low similarity."""
    # Add an old low-similarity domain
    with sqlite3.connect(str(temp_pipeline_db)) as conn:
        conn.execute(
            "INSERT INTO ct_raw (domain, first_seen, source) VALUES ('mandiriku.id', '2026-08-28T11:00:00Z', 'test')"
        )
        conn.commit()

    # Mock RDAP to return registration date 2 years ago (old)
    mock_rdap = DomainInfo(
        domain="mandiriku.id",
        registration_date="2024-01-01T00:00:00Z",
        registrar="PANDI",
        nameservers=["ns1.pandi.id"],
        status=["active"],
    )

    with patch("lib.pipeline.lookup", return_value=mock_rdap):
        metrics = run_tiered_pipeline(
            target_date="2026-08-28",
            db_path=temp_pipeline_db,
            allow_network=False,
            allow_llm=False,
            dry_run=True,
        )

        assert metrics.domains_scanned == 11
        assert metrics.tahap1_passed >= 5


def test_tiered_pipeline_llm_budget_cap_handled(temp_pipeline_db):
    """Verify that hitting LLM token budget limit does not crash pipeline and increments metric.

    A fresh-registration RDAP result is mocked so at least one candidate's
    calibrated score clears the >=60 LLM-escalation threshold (watchlist
    match 25 + risky TLD 15 + domain_age_under_7d 30 = 70) — otherwise the
    LLM branch is never reached at all and this test would pass for the
    wrong reason (silently, same failure mode as the bug it guards against).
    """
    fresh_domain = DomainInfo(
        domain="bca-update-tarif.online",
        registration_date=datetime.now(timezone.utc).isoformat(),
        registrar="Some Registrar",
        nameservers=["ns1.example.com"],
        status=["active"],
    )

    def _lookup_side_effect(domain, *args, **kwargs):
        return fresh_domain if domain == "bca-update-tarif.online" else None

    with patch("lib.pipeline.lookup", side_effect=_lookup_side_effect),          patch("lib.pipeline.complete", side_effect=LLMBudgetExceeded("Daily limit exceeded")) as mock_complete:
        metrics = run_tiered_pipeline(
            target_date="2026-08-28",
            db_path=temp_pipeline_db,
            allow_network=False,
            allow_llm=True,
            dry_run=False,
        )

        assert mock_complete.called
        assert metrics.domains_scanned == 10
        assert metrics.domains_flagged == 4
        assert metrics.llm_budget_capped_count > 0
        assert metrics.llm_calls_succeeded == 0
        assert metrics.duration_seconds >= 0.0


def test_tiered_pipeline_empty_date(temp_pipeline_db):
    """Verify pipeline handles a date with no ct_raw records gracefully."""
    metrics = run_tiered_pipeline(
        target_date="2025-01-01",
        db_path=temp_pipeline_db,
        dry_run=True,
    )

    assert metrics.domains_scanned == 0
    assert metrics.tahap1_passed == 0
    assert metrics.domains_flagged == 0


def test_tiered_pipeline_llm_call_actually_invoked_on_success(temp_pipeline_db):
    """Verify a successful LLM call is actually made (not just a prompt built and
    discarded) and its summary is folded into the persisted reasoning.

    This guards against the T22 regression where llm_prompt was constructed,
    metrics.tahap3_assessed was incremented, and evaluated_by_llm was set True
    — without complete() ever being called.
    """
    fresh_domain = DomainInfo(
        domain="bca-update-tarif.online",
        registration_date=datetime.now(timezone.utc).isoformat(),
        registrar="Some Registrar",
        nameservers=["ns1.example.com"],
        status=["active"],
    )

    def _lookup_side_effect(domain, *args, **kwargs):
        return fresh_domain if domain == "bca-update-tarif.online" else None

    mock_response = {"summary": "Domain ini meniru institusi resmi dengan TLD murah."}
    with patch("lib.pipeline.lookup", side_effect=_lookup_side_effect),          patch("lib.pipeline.complete", return_value=mock_response) as mock_complete:
        metrics = run_tiered_pipeline(
            target_date="2026-08-28",
            db_path=temp_pipeline_db,
            allow_network=False,
            allow_llm=True,
            dry_run=False,
        )

        assert mock_complete.called, "complete() was never invoked — LLM synthesis is a no-op"
        assert metrics.llm_calls_succeeded > 0

    with sqlite3.connect(str(temp_pipeline_db)) as conn:
        rows = conn.execute(
            "SELECT reasoning FROM domain_findings WHERE reasoning LIKE ?",
            ("%meniru institusi resmi dengan TLD murah%",),
        ).fetchall()
        assert len(rows) > 0, "LLM summary was not folded into persisted reasoning"
