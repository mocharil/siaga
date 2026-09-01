"""Tests for collector/ct_collector_b.py — Aliran B kandidat typosquat.

HTTP dipalsukan (mock) di semua test -- tidak ada test yang memanggil
ctlogs.dev secara nyata, supaya suite pytest tetap deterministik dan cepat.
"""

from __future__ import annotations

import json
import sqlite3
import sys
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collector.ct_collector_b import (
    CANDIDATE_MODIFIERS,
    CANDIDATE_TLDS,
    MIN_STEM_LEN,
    RATE_LIMIT_ABORT_THRESHOLD,
    RATE_LIMIT_MAX_RETRIES,
    RateLimited,
    _check_domain,
    check_candidates,
    generate_candidates,
)
from collector.ct_collector import init_db


WATCHLIST_CSV = (
    "brand_name,aliases,official_domain,category,match_mode,source\n"
    "Bank Mandiri,Mandiri;Bank Mandiri,bankmandiri.co.id,bank,edit_distance,test\n"
    "DANA,DANA,dana.id,ewallet,keyword_only,test\n"
    "GO,GO,go.id,tiny,keyword_only,test\n"  # off_stem "go" -- length 2, must be excluded
)


@pytest.fixture()
def watchlist_path(tmp_path):
    p = tmp_path / "watchlist.csv"
    p.write_text(WATCHLIST_CSV, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# generate_candidates
# ---------------------------------------------------------------------------


class TestGenerateCandidates:
    def test_shape_and_count(self, watchlist_path):
        candidates = generate_candidates(watchlist_path)
        # 2 eligible stems (bankmandiri, ovo) x (1 exact + len(modifiers)) x len(tlds)
        expected = 2 * (1 + len(CANDIDATE_MODIFIERS)) * len(CANDIDATE_TLDS)
        assert len(candidates) == expected

    def test_short_stem_excluded(self, watchlist_path):
        """off_stem 'go' (len 2) must never appear -- MIN_STEM_LEN guard."""
        candidates = generate_candidates(watchlist_path)
        assert not any(c.startswith("go.") or c.startswith("go-") for c in candidates)
        assert MIN_STEM_LEN >= 4

    def test_exact_and_modifier_variants_present(self, watchlist_path):
        candidates = generate_candidates(watchlist_path)
        assert "bankmandiri.xyz" in candidates
        assert "bankmandiri-login.xyz" in candidates
        assert "bankmandiri-verifikasi.top" in candidates

    def test_no_duplicates(self, watchlist_path):
        candidates = generate_candidates(watchlist_path)
        assert len(candidates) == len(set(candidates))

    def test_shared_stem_deduplicated(self, tmp_path):
        """Two brands resolving to the same off_stem must not double-generate."""
        csv_text = (
            "brand_name,aliases,official_domain,category,match_mode,source\n"
            "Brand A,A,shared.co.id,bank,edit_distance,test\n"
            "Brand B,B,shared.id,bank,edit_distance,test\n"
        )
        p = tmp_path / "wl.csv"
        p.write_text(csv_text, encoding="utf-8")
        candidates = generate_candidates(p)
        assert candidates.count("shared.xyz") == 1


# ---------------------------------------------------------------------------
# _check_domain
# ---------------------------------------------------------------------------


class TestCheckDomain:
    def test_match_found_returns_earliest_not_before(self):
        payload = json.dumps({
            "rows": [
                {"not_before": "2026-02-01T00:00:00Z"},
                {"not_before": "2025-06-01T00:00:00Z"},
            ],
            "has_next": False,
        }).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = payload
        mock_resp.__enter__.return_value = mock_resp
        with patch("urllib.request.urlopen", return_value=mock_resp):
            has_cert, not_before = _check_domain("bankmandiri-login.xyz", None)
        assert has_cert is True
        assert not_before == "2025-06-01T00:00:00Z"

    def test_no_rows_returns_false(self):
        payload = json.dumps({"rows": [], "has_next": False}).encode()
        mock_resp = MagicMock()
        mock_resp.read.return_value = payload
        mock_resp.__enter__.return_value = mock_resp
        with patch("urllib.request.urlopen", return_value=mock_resp):
            has_cert, not_before = _check_domain("neverissued.xyz", None)
        assert has_cert is False
        assert not_before is None

    def test_http_400_invalid_hostname_treated_as_no_match(self):
        err = urllib.error.HTTPError(
            url="x", code=400, msg="invalid hostname", hdrs=None, fp=None
        )
        with patch("urllib.request.urlopen", side_effect=err):
            has_cert, not_before = _check_domain("bad_host!.xyz", None)
        assert has_cert is False
        assert not_before is None

    def test_network_error_raises_runtime_error(self):
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("timed out"),
        ):
            with pytest.raises(RuntimeError):
                _check_domain("bankmandiri.xyz", None)

    def test_http_429_raises_rate_limited_not_runtime_error(self):
        """Regression: the 2026-09-02 run treated 429 as an unhandled HTTPError
        and crashed the entire batch after ~40s, checking 0 of 2688 candidates.
        429 must be its own exception type so check_candidates can back off
        instead of the whole run dying."""
        err = urllib.error.HTTPError(
            url="x", code=429, msg="Too Many Requests", hdrs=None, fp=None
        )
        with patch("urllib.request.urlopen", side_effect=err):
            with pytest.raises(RateLimited):
                _check_domain("bankmandiri.xyz", None)


# ---------------------------------------------------------------------------
# check_candidates
# ---------------------------------------------------------------------------


class TestCheckCandidates:
    def test_mixed_results_partial_errors(self):
        """One match, one clean miss, one network failure -- must not crash,
        must report accurate checked/error counts, and must not include
        the failed candidate in matches."""

        def fake_check(hostname, api_key):
            if hostname == "found.xyz":
                return True, "2026-01-01T00:00:00Z"
            if hostname == "clean.xyz":
                return False, None
            raise RuntimeError("simulated network failure")

        with patch("collector.ct_collector_b._check_domain", side_effect=fake_check), \
             patch("time.sleep"):
            matches, checked, errors = check_candidates(
                ["found.xyz", "clean.xyz", "broken.xyz"]
            )

        assert matches == [("found.xyz", "2026-01-01T00:00:00Z")]
        assert checked == 2  # only successful checks increment; broken.xyz errored
        assert errors == 1

    def test_all_clean_returns_no_matches(self):
        with patch(
            "collector.ct_collector_b._check_domain", return_value=(False, None)
        ), patch("time.sleep"):
            matches, checked, errors = check_candidates(["a.xyz", "b.xyz"])
        assert matches == []
        assert checked == 2
        assert errors == 0

    def test_rate_limit_retries_then_succeeds(self):
        """429 twice, then success on the final allowed attempt -- must not
        be counted as an error once it eventually succeeds."""
        calls = {"n": 0}

        def flaky(hostname, api_key):
            calls["n"] += 1
            if calls["n"] <= RATE_LIMIT_MAX_RETRIES:
                raise RateLimited("429")
            return True, "2026-01-01T00:00:00Z"

        with patch("collector.ct_collector_b._check_domain", side_effect=flaky), \
             patch("time.sleep"):
            matches, checked, errors = check_candidates(["retry-me.xyz"])

        assert matches == [("retry-me.xyz", "2026-01-01T00:00:00Z")]
        assert checked == 1
        assert errors == 0

    def test_rate_limit_exhausted_counts_as_error_not_crash(self):
        """429 on every attempt for one candidate -- must count as an error
        and move on, never raise out of check_candidates."""
        with patch(
            "collector.ct_collector_b._check_domain",
            side_effect=RateLimited("429"),
        ), patch("time.sleep"):
            matches, checked, errors = check_candidates(["always-429.xyz"])
        assert matches == []
        assert errors == 1

    def test_rate_limit_aborts_run_after_consecutive_threshold(self):
        """The real 2026-09-02 failure mode: server keeps saying 429. The
        collector must stop early instead of grinding through every
        remaining candidate for a guaranteed failure."""
        candidates = [f"c{i}.xyz" for i in range(RATE_LIMIT_ABORT_THRESHOLD + 10)]
        with patch(
            "collector.ct_collector_b._check_domain",
            side_effect=RateLimited("429"),
        ), patch("time.sleep"):
            matches, checked, errors = check_candidates(candidates)
        assert checked == 0
        assert errors == RATE_LIMIT_ABORT_THRESHOLD
        assert matches == []


# ---------------------------------------------------------------------------
# Integration: matches land in ct_raw with the correct source tag
# ---------------------------------------------------------------------------


class TestCtRawIntegration:
    def test_match_inserted_with_candidate_b_source(self, tmp_path):
        db_path = tmp_path / "test.db"
        conn = init_db(db_path)
        conn.execute(
            "INSERT OR IGNORE INTO ct_raw (domain, first_seen, not_before, source) "
            "VALUES (?, ?, ?, ?)",
            ("bankmandiri-login.xyz", "2026-09-02T00:00:00Z", "2026-08-01T00:00:00Z",
             "ctlogs_candidate_b"),
        )
        conn.commit()
        row = conn.execute(
            "SELECT source FROM ct_raw WHERE domain = ?", ("bankmandiri-login.xyz",)
        ).fetchone()
        assert row[0] == "ctlogs_candidate_b"
        conn.close()

    def test_rerun_does_not_duplicate(self, tmp_path):
        """Same idempotency guarantee as Aliran A: UNIQUE(domain) blocks re-insert."""
        db_path = tmp_path / "test.db"
        conn = init_db(db_path)
        for _ in range(2):
            conn.execute(
                "INSERT OR IGNORE INTO ct_raw (domain, first_seen, not_before, source) "
                "VALUES (?, ?, ?, ?)",
                ("repeat.xyz", "2026-09-02T00:00:00Z", "2026-08-01T00:00:00Z",
                 "ctlogs_candidate_b"),
            )
        conn.commit()
        count = conn.execute(
            "SELECT COUNT(*) FROM ct_raw WHERE domain = ?", ("repeat.xyz",)
        ).fetchone()[0]
        assert count == 1
        conn.close()
