"""Unit tests for Judol (Online Gambling) Domain Detection."""

from datetime import datetime, timezone
import sqlite3
from unittest.mock import patch

import pytest

from lib.db import init_db
from lib.domain_utils import extract_domain_labels
from lib.judol_detect import (
    JUDOL_AMBIGUOUS_KEYWORDS,
    JUDOL_KEYWORDS,
    check_judol,
    check_judol_ambiguous,
    scan_ct_raw,
)
from lib.llm import LLMBudgetExceeded


# ---------------------------------------------------------------------------
# extract_domain_labels (moved from lib/similarity.py to lib/domain_utils.py)
# ---------------------------------------------------------------------------

def test_extract_domain_labels_splits_hyphens():
    assert extract_domain_labels("slot-gacor.xyz") == ["slot-gacor", "slot", "gacor"]


def test_extract_domain_labels_strips_id_second_level_tld():
    assert extract_domain_labels("slot-gacor.selumakab.go.id") == [
        "slot-gacor", "slot", "gacor", "selumakab",
    ]


def test_extract_domain_labels_no_hyphen_single_token():
    assert extract_domain_labels("bandarlampungkota.go.id") == ["bandarlampungkota"]


# ---------------------------------------------------------------------------
# check_judol
# ---------------------------------------------------------------------------

def test_check_judol_real_hijacked_government_domain():
    match = check_judol("slot-gacor.selumakab.go.id")
    assert match is not None
    assert "slot" in match.matched_keywords
    assert "gacor" in match.matched_keywords
    assert match.is_hijacked_institution is True
    assert match.institution_suffix == "go.id"


def test_check_judol_real_hijacked_education_domain():
    match = check_judol("www.slot-thailand.disdag.tapinkab.go.id")
    assert match is not None
    assert match.is_hijacked_institution is True


def test_check_judol_non_institutional_match_not_flagged_hijacked():
    match = check_judol("gacor88.xyz")
    assert match is not None
    assert match.is_hijacked_institution is False
    assert match.institution_suffix is None


def test_check_judol_no_match_returns_none():
    assert check_judol("bankmandiri.co.id") is None
    assert check_judol("example.com") is None


def test_check_judol_false_positive_city_name_not_matched():
    """'bandar' substring-matches the city name but is not a whole label."""
    assert check_judol("bandarlampungkota.go.id") is None


def test_check_judol_ambiguous_generic_words_excluded_from_keyword_list():
    """Generic words that false-positived on real ct_raw data must stay excluded."""
    assert check_judol("pt-rtp.co.id") is None
    assert check_judol("domino-printer.co.id") is None
    assert check_judol("bola-staging.samitech.co.id") is None
    assert check_judol("joker.uho.ac.id") is None
    assert check_judol("toto-industries.co.id") is None


def test_check_judol_malformed_domain_returns_none():
    assert check_judol("") is None
    assert check_judol("not-a-domain") is None


def test_check_judol_matches_keyword_with_digit_suffix():
    """Real judol domains overwhelmingly append digits: gacor88, slot777, toto's togel-4d convention."""
    match = check_judol("gacor88.web.id")
    assert match is not None
    assert match.matched_keywords == ["gacor"]


def test_check_judol_matches_keyword_with_4d_suffix():
    match = check_judol("togel-4d.web.id")
    assert match is not None
    assert "togel" in match.matched_keywords


def test_check_judol_digit_suffix_does_not_over_match():
    """A keyword embedded with trailing letters (not just digits/d) must not match."""
    assert check_judol("slotmachine.com") is None


def test_check_judol_keyword_list_is_lowercase_and_nonempty():
    assert len(JUDOL_KEYWORDS) > 0
    assert all(k == k.lower() for k in JUDOL_KEYWORDS)


# ---------------------------------------------------------------------------
# check_judol_ambiguous (LLM-gated tier)
# ---------------------------------------------------------------------------

def test_check_judol_ambiguous_matches_dropped_strict_keywords():
    assert check_judol_ambiguous("toto-macau-2026.web.id") == ["toto"]
    assert check_judol_ambiguous("pt-rtp.co.id") == ["rtp"]


def test_check_judol_ambiguous_no_overlap_with_strict_list():
    """Ambiguous and strict keyword sets must never overlap -- a domain
    should never be double-counted by both tiers."""
    assert JUDOL_AMBIGUOUS_KEYWORDS.isdisjoint(JUDOL_KEYWORDS)


def test_check_judol_ambiguous_empty_when_no_match():
    assert check_judol_ambiguous("bankmandiri.co.id") == []


# ---------------------------------------------------------------------------
# scan_ct_raw
# ---------------------------------------------------------------------------

@pytest.fixture
def db_with_ct_raw(tmp_path):
    db_file = tmp_path / "judol_test.db"
    init_db(db_file)
    return db_file


def _insert_ct_raw(conn, domain, first_seen):
    conn.execute(
        "INSERT OR IGNORE INTO ct_raw (domain, first_seen, source) VALUES (?, ?, 'test')",
        (domain, first_seen),
    )


def test_scan_ct_raw_flags_real_and_skips_clean_domains(db_with_ct_raw):
    now_iso = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(str(db_with_ct_raw)) as conn:
        _insert_ct_raw(conn, "slot-gacor.selumakab.go.id", now_iso)
        _insert_ct_raw(conn, "bandarlampungkota.go.id", now_iso)
        _insert_ct_raw(conn, "bankmandiri.co.id", now_iso)
        conn.commit()

    summary = scan_ct_raw(db_path=db_with_ct_raw)

    assert summary.domains_scanned == 3
    assert summary.domains_flagged == 1
    assert summary.hijacked_institutions_flagged == 1
    assert summary.newly_inserted == 1

    with sqlite3.connect(str(db_with_ct_raw)) as conn:
        rows = conn.execute("SELECT domain FROM judol_findings").fetchall()
    assert rows == [("slot-gacor.selumakab.go.id",)]


def test_scan_ct_raw_idempotent_second_run_zero_new(db_with_ct_raw):
    now_iso = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(str(db_with_ct_raw)) as conn:
        _insert_ct_raw(conn, "slot-gacor.selumakab.go.id", now_iso)
        conn.commit()

    scan_ct_raw(db_path=db_with_ct_raw)
    second = scan_ct_raw(db_path=db_with_ct_raw)

    assert second.domains_flagged == 1
    assert second.newly_inserted == 0


def test_scan_ct_raw_rebuild_drops_stale_rows_from_direct_db_insert(db_with_ct_raw):
    """A stale judol_findings row (e.g. from a retired keyword) must be dropped on rebuild."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(str(db_with_ct_raw)) as conn:
        _insert_ct_raw(conn, "bandarlampungkota.go.id", now_iso)
        conn.execute(
            """
            INSERT INTO judol_findings
                (domain, first_seen, matched_keywords, is_hijacked_institution, institution_suffix, detected_at)
            VALUES ('bandarlampungkota.go.id', ?, 'bandar', 0, NULL, ?)
            """,
            (now_iso, now_iso),
        )
        conn.commit()

    summary = scan_ct_raw(db_path=db_with_ct_raw)

    assert summary.domains_flagged == 0
    with sqlite3.connect(str(db_with_ct_raw)) as conn:
        rows = conn.execute("SELECT domain FROM judol_findings").fetchall()
    assert rows == []


def test_scan_ct_raw_ambiguous_never_flagged_without_allow_llm(db_with_ct_raw):
    """Default (allow_llm=False) must never auto-flag an ambiguous-only match."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(str(db_with_ct_raw)) as conn:
        _insert_ct_raw(conn, "toto-macau-2026.web.id", now_iso)
        conn.commit()

    summary = scan_ct_raw(db_path=db_with_ct_raw)

    assert summary.domains_flagged == 0
    assert summary.llm_candidates_checked == 0


def test_scan_ct_raw_llm_confirms_ambiguous_match(db_with_ct_raw):
    now_iso = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(str(db_with_ct_raw)) as conn:
        _insert_ct_raw(conn, "toto-macau-2026.web.id", now_iso)
        _insert_ct_raw(conn, "domino-printer.co.id", now_iso)
        conn.commit()

    def fake_complete(prompt, schema, system_prompt=None, db_path=None):
        if "toto-macau-2026" in prompt:
            return {"is_match": True, "reasoning": "Nama domain menyebut 'macau', istilah umum judi online."}
        return {"is_match": False, "reasoning": "Nama domain menunjukkan bisnis percetakan, bukan judi."}

    with patch("lib.judol_detect.complete", side_effect=fake_complete):
        summary = scan_ct_raw(db_path=db_with_ct_raw, allow_llm=True)

    assert summary.llm_candidates_checked == 2
    assert summary.llm_confirmed == 1
    assert summary.domains_flagged == 1

    with sqlite3.connect(str(db_with_ct_raw)) as conn:
        row = conn.execute(
            "SELECT domain, verification_method, llm_reasoning FROM judol_findings"
        ).fetchone()
    assert row[0] == "toto-macau-2026.web.id"
    assert row[1] == "llm"
    assert "macau" in row[2]


def test_scan_ct_raw_llm_budget_exceeded_skips_gracefully(db_with_ct_raw):
    """A budget-exceeded LLM call must never fall back to auto-flagging."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(str(db_with_ct_raw)) as conn:
        _insert_ct_raw(conn, "toto-macau-2026.web.id", now_iso)
        conn.commit()

    with patch("lib.judol_detect.complete", side_effect=LLMBudgetExceeded("budget exceeded")):
        summary = scan_ct_raw(db_path=db_with_ct_raw, allow_llm=True)

    assert summary.llm_candidates_checked == 1
    assert summary.llm_confirmed == 0
    assert summary.domains_flagged == 0
