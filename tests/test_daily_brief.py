"""Unit tests for Daily Brief Formatting (T25)."""

import sqlite3
from datetime import datetime

import pytest

from lib.daily_brief import format_daily_brief
from lib.db import init_db


@pytest.fixture
def db_path(tmp_path):
    p = tmp_path / "brief_test.db"
    init_db(p)
    return p


def test_missing_day_returns_explicit_no_data_message(db_path):
    """A day with no daily_stats row must never be silently reported as zero
    activity — the two states must look different to the reader."""
    text = format_daily_brief("2026-09-01", db_path=db_path)
    assert "Tidak ada data pipeline" in text
    assert "2026-09-01" in text


def test_basic_stats_rendered(db_path):
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            INSERT INTO daily_stats (date, domains_scanned, domains_flagged, domains_live, flagged_not_in_blacklist)
            VALUES ('2026-09-05', 18432, 14, 6, 10)
            """
        )
        conn.commit()

    text = format_daily_brief("2026-09-05", db_path=db_path)
    assert "18,432" in text
    assert "14 mencurigakan" in text
    assert "6 sudah aktif" in text
    assert "05 September 2026" in text


def test_top_findings_included_with_reasons(db_path):
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "INSERT INTO daily_stats (date, domains_scanned, domains_flagged, domains_live) VALUES ('2026-09-05', 100, 2, 1)"
        )
        conn.execute(
            """
            INSERT INTO domain_findings (domain, first_seen, matched_brand, match_method, risk_score, risk_level, is_live)
            VALUES ('bca-verif.xyz', '2026-09-05T01:00:00Z', 'Bank Central Asia', 'edit_distance', 87, 'INDIKASI PENIPUAN', 1)
            """
        )
        conn.execute(
            """
            INSERT INTO domain_findings (domain, first_seen, matched_brand, match_method, risk_score, risk_level, is_live)
            VALUES ('mandiri-login.online', '2026-09-05T02:00:00Z', 'Bank Mandiri', 'keyword', 72, 'INDIKASI PENIPUAN', 0)
            """
        )
        conn.commit()

    text = format_daily_brief("2026-09-05", db_path=db_path)
    assert "bca-verif.xyz" in text
    assert "Bank Central Asia" in text
    assert "87" in text
    assert "mandiri-login.online" in text


def test_findings_ordered_by_risk_score_descending(db_path):
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("INSERT INTO daily_stats (date, domains_scanned, domains_flagged) VALUES ('2026-09-05', 10, 2)")
        conn.execute(
            "INSERT INTO domain_findings (domain, first_seen, matched_brand, match_method, risk_score) VALUES ('low.xyz', '2026-09-05T01:00:00Z', 'BRI', 'keyword', 45)"
        )
        conn.execute(
            "INSERT INTO domain_findings (domain, first_seen, matched_brand, match_method, risk_score) VALUES ('high.xyz', '2026-09-05T02:00:00Z', 'BRI', 'keyword', 90)"
        )
        conn.commit()

    text = format_daily_brief("2026-09-05", db_path=db_path)
    assert text.index("high.xyz") < text.index("low.xyz")


def test_campaign_membership_annotated(db_path):
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("INSERT INTO daily_stats (date, domains_scanned, domains_flagged) VALUES ('2026-09-05', 10, 1)")
        conn.execute(
            "INSERT INTO campaigns (cluster_type, cluster_key, member_count, first_detected_at, last_updated_at) VALUES ('nameserver', 'evilhost.top', 3, '2026-09-05T00:00:00Z', '2026-09-05T00:00:00Z')"
        )
        campaign_id = conn.execute("SELECT id FROM campaigns").fetchone()[0]
        conn.execute(
            "INSERT INTO domain_findings (domain, first_seen, matched_brand, match_method, risk_score, campaign_id) VALUES ('bca1.xyz', '2026-09-05T01:00:00Z', 'BCA', 'keyword', 80, ?)",
            (campaign_id,),
        )
        conn.commit()

    text = format_daily_brief("2026-09-05", db_path=db_path)
    assert "infrastruktur sama" in text
    assert "indikasi satu kampanye" in text


def test_trend_insufficient_history_is_honest(db_path):
    """With fewer than 3 prior days, must say so rather than compute a
    misleading percentage off a thin sample."""
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("INSERT INTO daily_stats (date, domains_scanned, domains_flagged) VALUES ('2026-09-05', 10, 3)")
        conn.commit()

    text = format_daily_brief("2026-09-05", db_path=db_path)
    assert "belum cukup data historis" in text


def test_trend_computed_with_enough_history(db_path):
    with sqlite3.connect(str(db_path)) as conn:
        for day, flagged in [("2026-08-29", 10), ("2026-08-30", 10), ("2026-08-31", 10), ("2026-09-01", 20)]:
            conn.execute(
                "INSERT INTO daily_stats (date, domains_scanned, domains_flagged) VALUES (?, 100, ?)",
                (day, flagged),
            )
        conn.commit()

    text = format_daily_brief("2026-09-01", db_path=db_path)
    assert "Tren: naik" in text
    assert "100%" in text  # 20 vs avg(10) = +100%
