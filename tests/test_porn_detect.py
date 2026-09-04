"""Unit tests for Adult Content Domain Detection."""

from datetime import datetime, timezone
import sqlite3
from unittest.mock import patch

import pytest

from lib.db import init_db
from lib.porn_detect import (
    PORN_AMBIGUOUS_KEYWORDS,
    PORN_KEYWORDS,
    check_porn,
    check_porn_ambiguous,
    scan_ct_raw,
)
from lib.llm import LLMBudgetExceeded


# ---------------------------------------------------------------------------
# check_porn
# ---------------------------------------------------------------------------

def test_check_porn_real_match_bokep():
    """'bokep' is unambiguous Indonesian slang specifically for porn video."""
    match = check_porn("bokep.web.id")
    assert match is not None
    assert "bokep" in match.matched_keywords
    assert match.is_hijacked_institution is False


def test_check_porn_real_match_xxx_subdomain():
    match = check_porn("www.xxx.kabulcipta.co.id")
    assert match is not None
    assert "xxx" in match.matched_keywords


def test_check_porn_hijacked_government_domain():
    match = check_porn("bokep-viral.desa-sukamaju.desa.id")
    assert match is not None
    assert match.is_hijacked_institution is True
    assert match.institution_suffix == "desa.id"


def test_check_porn_no_match_returns_none():
    assert check_porn("bankmandiri.co.id") is None
    assert check_porn("example.com") is None


def test_check_porn_body_part_profanity_excluded_from_keyword_list():
    """Genital slang (kontol/toket/memek/ewe) false-positived on a real vulgar
    DDNS prank cluster ('kontol.dnm.web.id' + brand subdomains) in production
    data and must stay excluded -- profanity is not a content descriptor."""
    assert check_porn("kontol.dnm.web.id") is None
    assert check_porn("app.gopay.co.id.kontol.dnm.web.id") is None
    assert check_porn("toket-gede.web.id") is None
    assert check_porn("memek.xyz") is None


def test_check_porn_religious_sensitive_term_excluded():
    """'jilbob' is deliberately excluded regardless of prevalence -- conflating
    religious dress with adult content risks an unacceptable false accusation."""
    assert check_porn("jilbob-viral.xyz") is None


def test_check_porn_malformed_domain_returns_none():
    assert check_porn("") is None
    assert check_porn("not-a-domain") is None


def test_check_porn_matches_keyword_with_digit_suffix():
    match = check_porn("bokep88.web.id")
    assert match is not None
    assert match.matched_keywords == ["bokep"]


def test_check_porn_digit_suffix_does_not_over_match():
    assert check_porn("pornographic.com") is None


def test_check_porn_keyword_list_is_lowercase_and_nonempty():
    assert len(PORN_KEYWORDS) > 0
    assert all(k == k.lower() for k in PORN_KEYWORDS)


def test_jilbob_never_appears_in_either_keyword_tier():
    """Hard ethical exclusion: 'jilbob' must never be a candidate for
    detection, keyword or LLM-gated -- not a precision trade-off to revisit."""
    assert "jilbob" not in PORN_KEYWORDS
    assert "jilbob" not in PORN_AMBIGUOUS_KEYWORDS


# ---------------------------------------------------------------------------
# check_porn_ambiguous (LLM-gated tier)
# ---------------------------------------------------------------------------

def test_check_porn_ambiguous_matches_dropped_strict_keywords():
    assert check_porn_ambiguous("kontol.dnm.web.id") == ["kontol"]


def test_check_porn_ambiguous_no_overlap_with_strict_list():
    assert PORN_AMBIGUOUS_KEYWORDS.isdisjoint(PORN_KEYWORDS)


def test_check_porn_ambiguous_empty_when_no_match():
    assert check_porn_ambiguous("bankmandiri.co.id") == []


def test_check_porn_ambiguous_never_matches_jilbob():
    assert check_porn_ambiguous("jilbob-viral.xyz") == []


# ---------------------------------------------------------------------------
# scan_ct_raw
# ---------------------------------------------------------------------------

@pytest.fixture
def db_with_ct_raw(tmp_path):
    db_file = tmp_path / "porn_test.db"
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
        _insert_ct_raw(conn, "bokep.web.id", now_iso)
        _insert_ct_raw(conn, "kontol.dnm.web.id", now_iso)
        _insert_ct_raw(conn, "bankmandiri.co.id", now_iso)
        conn.commit()

    summary = scan_ct_raw(db_path=db_with_ct_raw)

    assert summary.domains_scanned == 3
    assert summary.domains_flagged == 1
    assert summary.newly_inserted == 1

    with sqlite3.connect(str(db_with_ct_raw)) as conn:
        rows = conn.execute("SELECT domain FROM porn_findings").fetchall()
    assert rows == [("bokep.web.id",)]


def test_scan_ct_raw_idempotent_second_run_zero_new(db_with_ct_raw):
    now_iso = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(str(db_with_ct_raw)) as conn:
        _insert_ct_raw(conn, "bokep.web.id", now_iso)
        conn.commit()

    scan_ct_raw(db_path=db_with_ct_raw)
    second = scan_ct_raw(db_path=db_with_ct_raw)

    assert second.domains_flagged == 1
    assert second.newly_inserted == 0


def test_scan_ct_raw_rebuild_drops_stale_rows_from_direct_db_insert(db_with_ct_raw):
    now_iso = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(str(db_with_ct_raw)) as conn:
        _insert_ct_raw(conn, "kontol.dnm.web.id", now_iso)
        conn.execute(
            """
            INSERT INTO porn_findings
                (domain, first_seen, matched_keywords, is_hijacked_institution, institution_suffix, detected_at)
            VALUES ('kontol.dnm.web.id', ?, 'kontol', 0, NULL, ?)
            """,
            (now_iso, now_iso),
        )
        conn.commit()

    summary = scan_ct_raw(db_path=db_with_ct_raw)

    assert summary.domains_flagged == 0
    with sqlite3.connect(str(db_with_ct_raw)) as conn:
        rows = conn.execute("SELECT domain FROM porn_findings").fetchall()
    assert rows == []


def test_scan_ct_raw_ambiguous_never_flagged_without_allow_llm(db_with_ct_raw):
    now_iso = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(str(db_with_ct_raw)) as conn:
        _insert_ct_raw(conn, "kontol.dnm.web.id", now_iso)
        conn.commit()

    summary = scan_ct_raw(db_path=db_with_ct_raw)

    assert summary.domains_flagged == 0
    assert summary.llm_candidates_checked == 0


def test_scan_ct_raw_llm_rejects_vandalism_cluster(db_with_ct_raw):
    """The real 'kontol.dnm.web.id' + brand-subdomain prank pattern -- an LLM
    given the full domain string should recognize this as vandalism on a free
    DDNS zone, not adult content, and correctly decline to flag it."""
    now_iso = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(str(db_with_ct_raw)) as conn:
        _insert_ct_raw(conn, "app.gopay.co.id.kontol.dnm.web.id", now_iso)
        conn.commit()

    def fake_complete(prompt, schema, system_prompt=None, db_path=None):
        return {
            "is_match": False,
            "reasoning": "Nama domain menempelkan nama brand (gopay.co.id) di subdomain acak pada layanan DDNS gratis -- pola vandalisme, bukan indikasi konten dewasa.",
        }

    with patch("lib.porn_detect.complete", side_effect=fake_complete):
        summary = scan_ct_raw(db_path=db_with_ct_raw, allow_llm=True)

    assert summary.llm_candidates_checked == 1
    assert summary.llm_confirmed == 0
    assert summary.domains_flagged == 0


def test_scan_ct_raw_llm_confirms_ambiguous_match(db_with_ct_raw):
    now_iso = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(str(db_with_ct_raw)) as conn:
        _insert_ct_raw(conn, "kontol-viral-2026.web.id", now_iso)
        conn.commit()

    def fake_complete(prompt, schema, system_prompt=None, db_path=None):
        return {"is_match": True, "reasoning": "Konteks nama domain mengindikasikan konten dewasa."}

    with patch("lib.porn_detect.complete", side_effect=fake_complete):
        summary = scan_ct_raw(db_path=db_with_ct_raw, allow_llm=True)

    assert summary.llm_confirmed == 1
    assert summary.domains_flagged == 1

    with sqlite3.connect(str(db_with_ct_raw)) as conn:
        row = conn.execute(
            "SELECT verification_method, llm_reasoning FROM porn_findings"
        ).fetchone()
    assert row[0] == "llm"
    assert row[1]


def test_scan_ct_raw_llm_budget_exceeded_skips_gracefully(db_with_ct_raw):
    now_iso = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(str(db_with_ct_raw)) as conn:
        _insert_ct_raw(conn, "kontol.dnm.web.id", now_iso)
        conn.commit()

    with patch("lib.porn_detect.complete", side_effect=LLMBudgetExceeded("budget exceeded")):
        summary = scan_ct_raw(db_path=db_with_ct_raw, allow_llm=True)

    assert summary.llm_candidates_checked == 1
    assert summary.llm_confirmed == 0
    assert summary.domains_flagged == 0
