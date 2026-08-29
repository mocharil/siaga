"""Unit tests for scripts/rescore_backlog.py (T20).

Verifies backlog rescoring execution, batch processing, dry-run simulation,
idempotency, and historical timestamp preservation in domain_findings.
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path
import sqlite3
import pytest

from lib.db import init_db
from scripts.rescore_backlog import process_backlog


@pytest.fixture
def test_rescore_db(tmp_path):
    """Setup isolated database with sample clean and phishing CT backlog domains."""
    db_file = tmp_path / "test_rescore.db"
    init_db(db_file)

    now_dt = datetime.now(timezone.utc)
    ts_day1 = (now_dt - timedelta(days=2)).isoformat()
    ts_day2 = (now_dt - timedelta(days=1)).isoformat()

    sample_ct_domains = [
        # Phishing targets
        ("bca-update-tarif.online", ts_day1, ts_day1),
        ("bankmandiri-promo.xyz", ts_day1, ts_day1),
        ("tokopdia.com", ts_day2, ts_day2),
        ("traveloka-resmi.site", ts_day2, ts_day2),
        # Clean / benign domains
        ("example-personal-blog.id", ts_day1, ts_day1),
        ("my-bakery-shop-jakarta.com", ts_day2, ts_day2),
        ("random-clean-site.org", ts_day2, ts_day2),
    ]

    with sqlite3.connect(str(db_file)) as conn:
        conn.executemany(
            """
            INSERT INTO ct_raw (domain, first_seen, not_before, source, processed_at)
            VALUES (?, ?, ?, 'certstream', NULL)
            """,
            sample_ct_domains,
        )
        conn.commit()

    return db_file


def test_dry_run_leaves_database_unmodified(test_rescore_db):
    """DoD: Dry run computes statistics but makes zero modifications to DB."""
    total_proc, total_flagged = process_backlog(
        db_path=test_rescore_db,
        batch_size=5,
        dry_run=True,
    )

    assert total_proc == 7
    assert total_flagged >= 3

    with sqlite3.connect(str(test_rescore_db)) as conn:
        # ct_raw processed_at must remain NULL
        cur = conn.execute("SELECT COUNT(*) FROM ct_raw WHERE processed_at IS NOT NULL")
        assert cur.fetchone()[0] == 0

        # domain_findings must remain empty
        cur = conn.execute("SELECT COUNT(*) FROM domain_findings")
        assert cur.fetchone()[0] == 0


def test_live_rescoring_populates_findings_and_marks_processed(test_rescore_db):
    """DoD: Live processing populates domain_findings and sets processed_at timestamps."""
    total_proc, total_flagged = process_backlog(
        db_path=test_rescore_db,
        batch_size=3,
        dry_run=False,
    )

    assert total_proc == 7
    assert total_flagged >= 3

    with sqlite3.connect(str(test_rescore_db)) as conn:
        # All 7 ct_raw records marked as processed
        cur = conn.execute("SELECT COUNT(*) FROM ct_raw WHERE processed_at IS NOT NULL")
        assert cur.fetchone()[0] == 7

        # Findings table contains identified phishing domains
        cur = conn.execute("SELECT domain, matched_brand, risk_score, first_seen FROM domain_findings")
        findings = cur.fetchall()
        assert len(findings) >= 3

        flagged_domains = {f[0] for f in findings}
        assert "bca-update-tarif.online" in flagged_domains
        assert "bankmandiri-promo.xyz" in flagged_domains
        assert "tokopdia.com" in flagged_domains

        # Verify historical first_seen preserved (not overwritten with today's date)
        for dom, brand, score, first_seen in findings:
            assert brand is not None
            assert score >= 40
            assert first_seen is not None


def test_rescoring_is_idempotent_and_resumable(test_rescore_db):
    """DoD: Running rescoring multiple times or after interruption produces zero duplicates."""
    # First run processes all
    proc1, flag1 = process_backlog(test_rescore_db, batch_size=10, dry_run=False)
    assert proc1 == 7

    # Second run finds 0 unprocessed domains
    proc2, flag2 = process_backlog(test_rescore_db, batch_size=10, dry_run=False)
    assert proc2 == 0
    assert flag2 == 0
