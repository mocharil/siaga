"""Tests for collector/ct_collector.py — parsing, normalization, and DB idempotency."""

from __future__ import annotations

import sqlite3
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Adjust path so we can import the collector
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collector.ct_collector import (
    normalize_domain,
    extract_domains_from_name_value,
    init_db,
    record_run,
    _fetch_from_ctlogs,
    fetch_recent_domains,
)


# ---------------------------------------------------------------------------
# normalize_domain
# ---------------------------------------------------------------------------


class TestNormalizeDomain:
    def test_plain(self):
        assert normalize_domain("Example.COM") == "example.com"

    def test_wildcard(self):
        assert normalize_domain("*.bank.co.id") == "bank.co.id"

    def test_trailing_dot(self):
        assert normalize_domain("bank.co.id.") == "bank.co.id"

    def test_wildcard_and_trailing_dot(self):
        assert normalize_domain("*.Bank.CO.ID.") == "bank.co.id"

    def test_whitespace(self):
        assert normalize_domain("  bank.co.id  ") == "bank.co.id"

    def test_already_clean(self):
        assert normalize_domain("clean.go.id") == "clean.go.id"

    def test_empty_after_strip(self):
        assert normalize_domain("*.") == ""

    def test_just_whitespace(self):
        assert normalize_domain("   ") == ""


# ---------------------------------------------------------------------------
# extract_domains_from_name_value (crt.sh format)
# ---------------------------------------------------------------------------


class TestExtractDomainsFromNameValue:
    def test_single_domain(self):
        assert extract_domains_from_name_value("example.com") == ["example.com"]

    def test_multiline_with_wildcard(self):
        result = extract_domains_from_name_value("*.example.com\nexample.com")
        assert set(result) == {"example.com"}  # wildcard stripped = same

    def test_mixed(self):
        nv = "*.bank.co.id\nbank.co.id\nwww.bank.co.id"
        result = extract_domains_from_name_value(nv)
        assert "bank.co.id" in result
        assert "www.bank.co.id" in result

    def test_empty(self):
        assert extract_domains_from_name_value("") == []

    def test_only_whitespace(self):
        assert extract_domains_from_name_value("   \n  \n  ") == []


# ---------------------------------------------------------------------------
# ctlogs.dev response parsing (mocked)
# ---------------------------------------------------------------------------

MOCK_CTLOGS_RESPONSE_PAGE1 = {
    "rows": [
        {
            "id": "00000111",
            "match": "*.mandiri-login.co.id",
            "not_before": "2026-08-28T06:00:00Z",
            "not_after": "2026-11-28T06:00:00Z",
            "serial_hex": "abcd1234",
            "issuer": "Let's Encrypt",
            "key_algo": "ECDSA P-256",
            "san_count": 2,
        },
        {
            "id": "00000222",
            "match": "bankbca-online.co.id",
            "not_before": "2026-08-28T05:00:00Z",
            "not_after": "2026-11-28T05:00:00Z",
            "serial_hex": "efgh5678",
            "issuer": "Let's Encrypt",
            "key_algo": "RSA 2048",
            "san_count": 1,
        },
        {
            "id": "00000333",
            "match": "legit-company.co.id",
            "not_before": "2026-08-27T01:00:00Z",  # older than 24h → cutoff
            "not_after": "2026-11-27T01:00:00Z",
            "serial_hex": "ijkl9012",
            "issuer": "DigiCert",
            "key_algo": "RSA 2048",
            "san_count": 3,
        },
    ],
    "has_next": False,
    "next_cursor": None,
    "duration_ms": 42,
}


class TestCtlogsResponseParsing:
    """Verify that ctlogs.dev responses are parsed correctly with mock data."""

    @patch("collector.ct_collector._ctlogs_fetch_page")
    def test_domains_extracted_and_cutoff_respected(self, mock_fetch):
        mock_fetch.return_value = MOCK_CTLOGS_RESPONSE_PAGE1
        since = datetime(2026, 8, 27, 6, 0, 0, tzinfo=timezone.utc)

        records, ok, partial, fail = _fetch_from_ctlogs(since, ["co.id"])
        domains = [d for d, _ in records]
        domain_dict = dict(records)

        # Only the two domains newer than `since` should appear.
        # The third (2026-08-27T01:00:00Z) is before cutoff.
        assert "mandiri-login.co.id" in domains  # wildcard stripped
        assert "bankbca-online.co.id" in domains
        assert "legit-company.co.id" not in domains
        assert domain_dict["mandiri-login.co.id"] == datetime(2026, 8, 28, 6, 0, 0, tzinfo=timezone.utc)
        assert domain_dict["bankbca-online.co.id"] == datetime(2026, 8, 28, 5, 0, 0, tzinfo=timezone.utc)
        assert ok == 1
        assert partial == 0
        assert fail == 0

    @patch("collector.ct_collector._ctlogs_fetch_page")
    def test_pagination(self, mock_fetch):
        """Verify multi-page fetching works."""
        page1 = {
            "rows": [
                {
                    "id": "p1",
                    "match": "page1.co.id",
                    "not_before": "2026-08-28T06:00:00Z",
                    "not_after": "2026-11-28T06:00:00Z",
                    "serial_hex": "aa",
                    "issuer": "LE",
                    "key_algo": "ECDSA P-256",
                    "san_count": 1,
                }
            ],
            "has_next": True,
            "next_cursor": "CURSOR_ABC",
            "duration_ms": 10,
        }
        page2 = {
            "rows": [
                {
                    "id": "p2",
                    "match": "page2.co.id",
                    "not_before": "2026-08-28T05:00:00Z",
                    "not_after": "2026-11-28T05:00:00Z",
                    "serial_hex": "bb",
                    "issuer": "LE",
                    "key_algo": "ECDSA P-256",
                    "san_count": 1,
                }
            ],
            "has_next": False,
            "next_cursor": None,
            "duration_ms": 8,
        }
        mock_fetch.side_effect = [page1, page2]
        since = datetime(2026, 8, 27, 6, 0, 0, tzinfo=timezone.utc)

        records, ok, partial, fail = _fetch_from_ctlogs(since, ["co.id"])
        domains = [d for d, _ in records]

        assert "page1.co.id" in domains
        assert "page2.co.id" in domains
        assert mock_fetch.call_count == 2
        assert ok == 1
        assert partial == 0
        assert fail == 0

    @patch("collector.ct_collector._ctlogs_fetch_page")
    def test_tld_failure_recorded(self, mock_fetch):
        """If a TLD fails completely, it's counted as failed."""
        mock_fetch.return_value = None  # both attempts fail
        since = datetime(2026, 8, 27, 6, 0, 0, tzinfo=timezone.utc)

        records, ok, partial, fail = _fetch_from_ctlogs(since, ["co.id"])

        assert records == []
        assert ok == 0
        assert partial == 0
        assert fail == 1

    @patch("collector.ct_collector._ctlogs_fetch_page")
    def test_tld_partial_failure_recorded(self, mock_fetch):
        """If a TLD fetches some pages but fails midway, it's counted as partial."""
        page1 = {
            "rows": [
                {
                    "id": "p1",
                    "match": "partial-domain.co.id",
                    "not_before": "2026-08-28T06:00:00Z",
                    "not_after": "2026-11-28T06:00:00Z",
                    "serial_hex": "aa",
                    "issuer": "LE",
                    "key_algo": "ECDSA P-256",
                    "san_count": 1,
                }
            ],
            "has_next": True,
            "next_cursor": "CURSOR_NEXT",
            "duration_ms": 10,
        }
        # page 1 succeeds, page 2 fails (returns None on first try and on retry)
        mock_fetch.side_effect = [page1, None, None]
        since = datetime(2026, 8, 27, 6, 0, 0, tzinfo=timezone.utc)

        records, ok, partial, fail = _fetch_from_ctlogs(since, ["co.id"])
        domains = [d for d, _ in records]

        assert "partial-domain.co.id" in domains
        assert ok == 0
        assert partial == 1
        assert fail == 0

    @patch("collector.ct_collector._fetch_from_ctlogs")
    def test_fetch_recent_domains_partial_status(self, mock_fetch):
        """fetch_recent_domains must return 'partial' status when a TLD is partial."""
        since = datetime(2026, 8, 27, 6, 0, 0, tzinfo=timezone.utc)
        mock_fetch.return_value = (
            [("partial.co.id", datetime.now(timezone.utc))],
            1,  # ok_tlds
            1,  # partial_tlds
            0,  # fail_tlds
        )
        _, status = fetch_recent_domains(since, "ctlogs_id")
        assert status == "partial"

    @patch("collector.ct_collector._ctlogs_fetch_page")
    def test_deduplication_across_tlds(self, mock_fetch):
        """Same domain in different TLD queries is deduplicated."""
        resp = {
            "rows": [
                {
                    "id": "x",
                    "match": "shared.co.id",
                    "not_before": "2026-08-28T06:00:00Z",
                    "not_after": "2026-11-28T06:00:00Z",
                    "serial_hex": "cc",
                    "issuer": "LE",
                    "key_algo": "ECDSA P-256",
                    "san_count": 1,
                }
            ],
            "has_next": False,
        }
        mock_fetch.return_value = resp
        since = datetime(2026, 8, 27, 6, 0, 0, tzinfo=timezone.utc)

        # Query two TLDs that both return the same domain
        records, ok, partial, fail = _fetch_from_ctlogs(since, ["co.id", "or.id"])
        domains = [d for d, _ in records]

        assert domains.count("shared.co.id") == 1
        assert ok == 2
        assert partial == 0
        assert fail == 0

    @patch("collector.ct_collector._ctlogs_fetch_page")
    def test_earliest_not_before_retained_on_duplicate_domain(self, mock_fetch):
        """When the same domain appears multiple times with different not_before, the earliest is retained."""
        resp = {
            "rows": [
                {
                    "id": "cert-new",
                    "match": "duplicate.co.id",
                    "not_before": "2026-08-28T08:00:00Z",  # newer
                    "not_after": "2026-11-28T08:00:00Z",
                    "serial_hex": "1111",
                    "issuer": "LE",
                    "key_algo": "ECDSA P-256",
                    "san_count": 1,
                },
                {
                    "id": "cert-old",
                    "match": "duplicate.co.id",
                    "not_before": "2026-08-28T02:00:00Z",  # earlier
                    "not_after": "2026-11-28T02:00:00Z",
                    "serial_hex": "2222",
                    "issuer": "LE",
                    "key_algo": "ECDSA P-256",
                    "san_count": 1,
                },
            ],
            "has_next": False,
        }
        mock_fetch.return_value = resp
        since = datetime(2026, 8, 27, 6, 0, 0, tzinfo=timezone.utc)

        records, ok, partial, fail = _fetch_from_ctlogs(since, ["co.id"])
        domain_dict = dict(records)

        assert "duplicate.co.id" in domain_dict
        assert domain_dict["duplicate.co.id"] == datetime(2026, 8, 28, 2, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Database: init + idempotency + migration
# ---------------------------------------------------------------------------


class TestDatabase:
    @pytest.fixture
    def db(self, tmp_path):
        db_path = tmp_path / "test.db"
        conn = init_db(db_path)
        yield conn
        conn.close()

    def test_tables_created(self, db):
        tables = {
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "ct_raw" in tables
        assert "collector_runs" in tables
        columns = [r[1] for r in db.execute("PRAGMA table_info(ct_raw)").fetchall()]
        assert "not_before" in columns

    def test_not_before_stored_and_retrieved(self, db):
        """not_before is stored and retrieved correctly."""
        now = "2026-08-28T12:00:00+00:00"
        nb = "2026-08-28T04:30:00+00:00"
        db.execute(
            "INSERT OR IGNORE INTO ct_raw (domain, first_seen, not_before, source) "
            "VALUES (?, ?, ?, ?)",
            ("sample.co.id", now, nb, "ctlogs_id"),
        )
        db.commit()
        row = db.execute(
            "SELECT domain, first_seen, not_before, source FROM ct_raw WHERE domain='sample.co.id'"
        ).fetchone()
        assert row[0] == "sample.co.id"
        assert row[1] == now
        assert row[2] == nb
        assert row[3] == "ctlogs_id"

    def test_migration_alter_table_idempotent(self, tmp_path):
        """init_db on a legacy DB without not_before column migrates it cleanly, and running again is safe."""
        db_path = tmp_path / "legacy.db"
        conn = sqlite3.connect(str(db_path))
        # Create legacy table without not_before
        conn.execute("""
        CREATE TABLE ct_raw (
            id INTEGER PRIMARY KEY,
            domain TEXT NOT NULL,
            first_seen TIMESTAMP NOT NULL,
            source TEXT,
            processed_at TIMESTAMP,
            UNIQUE(domain)
        );
        """)
        conn.execute("INSERT INTO ct_raw (domain, first_seen, source) VALUES ('legacy.id', '2026-08-28T00:00:00', 'ctlogs_id')")
        conn.commit()
        conn.close()

        # First run of init_db migrates
        conn1 = init_db(db_path)
        cols1 = [r[1] for r in conn1.execute("PRAGMA table_info(ct_raw)").fetchall()]
        assert "not_before" in cols1
        # Check existing row preserved with not_before = NULL
        legacy_row = conn1.execute("SELECT domain, not_before FROM ct_raw WHERE domain='legacy.id'").fetchone()
        assert legacy_row[0] == "legacy.id"
        assert legacy_row[1] is None
        conn1.close()

        # Second run of init_db is safe
        conn2 = init_db(db_path)
        cols2 = [r[1] for r in conn2.execute("PRAGMA table_info(ct_raw)").fetchall()]
        assert cols2.count("not_before") == 1
        conn2.close()

    def test_insert_idempotent(self, db):
        """INSERT OR IGNORE must not duplicate domains."""
        now = datetime.now(timezone.utc).isoformat()
        nb = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        db.execute(
            "INSERT OR IGNORE INTO ct_raw (domain, first_seen, not_before, source) VALUES (?, ?, ?, ?)",
            ("test.co.id", now, nb, "ctlogs_id"),
        )
        db.execute(
            "INSERT OR IGNORE INTO ct_raw (domain, first_seen, not_before, source) VALUES (?, ?, ?, ?)",
            ("test.co.id", now, nb, "ctlogs_id"),
        )
        db.commit()
        count = db.execute("SELECT COUNT(*) FROM ct_raw WHERE domain='test.co.id'").fetchone()[0]
        assert count == 1

    def test_first_seen_preserved(self, db):
        """Second insert for same domain must NOT update first_seen."""
        early = "2026-08-28T01:00:00+00:00"
        late = "2026-08-28T12:00:00+00:00"
        nb = "2026-08-27T23:00:00+00:00"
        db.execute(
            "INSERT OR IGNORE INTO ct_raw (domain, first_seen, not_before, source) VALUES (?, ?, ?, ?)",
            ("preserve.co.id", early, nb, "ctlogs_id"),
        )
        db.execute(
            "INSERT OR IGNORE INTO ct_raw (domain, first_seen, not_before, source) VALUES (?, ?, ?, ?)",
            ("preserve.co.id", late, nb, "ctlogs_id"),
        )
        db.commit()
        stored = db.execute(
            "SELECT first_seen FROM ct_raw WHERE domain='preserve.co.id'"
        ).fetchone()[0]
        assert stored == early

    def test_record_run(self, db):
        now = datetime.now(timezone.utc)
        record_run(db, now, now, "ctlogs_id", 100, 42, "ok")
        row = db.execute("SELECT * FROM collector_runs ORDER BY id DESC LIMIT 1").fetchone()
        assert row is not None
        assert row[5] == 42   # inserted_new
        assert row[6] == "ok" # status

    def test_record_run_failed(self, db):
        now = datetime.now(timezone.utc)
        record_run(db, now, now, "ctlogs_id", 0, 0, "failed", "connection timeout")
        row = db.execute("SELECT * FROM collector_runs ORDER BY id DESC LIMIT 1").fetchone()
        assert row[6] == "failed"
        assert row[7] == "connection timeout"


# ---------------------------------------------------------------------------
# Negative cases
# ---------------------------------------------------------------------------


class TestNegativeCases:
    def test_normalize_handles_garbage(self):
        """Non-domain strings should still not crash."""
        assert normalize_domain("") == ""
        assert normalize_domain("*.") == ""
        assert normalize_domain(".") == ""

    @patch("collector.ct_collector._ctlogs_fetch_page")
    def test_empty_rows(self, mock_fetch):
        """Empty rows list should not crash."""
        mock_fetch.return_value = {"rows": [], "has_next": False}
        since = datetime(2026, 8, 27, 6, 0, 0, tzinfo=timezone.utc)
        records, ok, partial, fail = _fetch_from_ctlogs(since, ["co.id"])
        assert records == []
        assert ok == 1  # successful but empty is ok, not failed
        assert partial == 0
        assert fail == 0

    @patch("collector.ct_collector._ctlogs_fetch_page")
    def test_malformed_not_before(self, mock_fetch):
        """Rows with unparseable not_before should be skipped, not crash."""
        mock_fetch.return_value = {
            "rows": [
                {
                    "id": "bad",
                    "match": "bad.co.id",
                    "not_before": "not-a-date",
                    "not_after": "2026-11-28T06:00:00Z",
                    "serial_hex": "ff",
                    "issuer": "LE",
                    "key_algo": "ECDSA P-256",
                    "san_count": 1,
                }
            ],
            "has_next": False,
        }
        since = datetime(2026, 8, 27, 6, 0, 0, tzinfo=timezone.utc)
        records, ok, partial, fail = _fetch_from_ctlogs(since, ["co.id"])
        # bad date → skipped, not crash
        domains = [d for d, _ in records]
        assert "bad.co.id" not in domains
        assert ok == 1
        assert partial == 0
        assert fail == 0
