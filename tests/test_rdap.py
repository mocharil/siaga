"""Unit tests for lib/rdap.py (T12).

Verifies RDAP lookup, parsing for .com and .id structures, IANA bootstrap routing,
negative caching (404), rate limit / timeout resilience, and SQLite caching.
"""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
from unittest.mock import MagicMock, patch
import urllib.error

import pytest

from lib.rdap import (
    BOOTSTRAP_TTL,
    CACHE_TTL_FOUND,
    CACHE_TTL_NOT_FOUND,
    DomainInfo,
    _extract_nameservers,
    _extract_registrar,
    _extract_registration_date,
    _parse_rdap_json,
    lookup,
)


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    """Create a temporary SQLite database path for isolated testing."""
    return tmp_path / "test_rdap.db"


@pytest.fixture
def mock_com_rdap_response() -> dict:
    """Sample Verisign .com RDAP JSON."""
    return {
        "handle": "2138514_DOMAIN_COM-VRSN",
        "ldhName": "GOOGLE.COM",
        "status": ["client delete prohibited", "server delete prohibited"],
        "events": [
            {"eventAction": "registration", "eventDate": "1997-09-15T04:00:00Z"},
            {"eventAction": "expiration", "eventDate": "2028-09-14T04:00:00Z"},
        ],
        "nameservers": [
            {"ldhName": "NS1.GOOGLE.COM"},
            {"ldhName": "NS2.GOOGLE.COM"},
        ],
        "entities": [
            {
                "roles": ["registrar"],
                "handle": "292",
                "vcardArray": [
                    "vcard",
                    [
                        ["version", {}, "text", "4.0"],
                        ["fn", {}, "text", "MarkMonitor Inc."],
                    ],
                ],
            }
        ],
    }


@pytest.fixture
def mock_id_rdap_response() -> dict:
    """Sample PANDI .id RDAP JSON."""
    return {
        "handle": "281096_DOMAIN_ID-ID",
        "ldhName": "PANDI.ID",
        "status": ["server delete prohibited"],
        "events": [
            {"eventAction": "registration", "eventDate": "2013-04-14T07:27:32Z"},
            {"eventAction": "expiration", "eventDate": "2027-04-14T23:59:59Z"},
        ],
        "nameservers": [
            {"ldhName": "bagendit.pandi.id"},
            {"ldhName": "sentani.pandi.id"},
        ],
        "entities": [
            {
                "roles": ["registrar"],
                "handle": "1",
                "vcardArray": [
                    "vcard",
                    [
                        ["version", {}, "text", "4.0"],
                        ["fn", {}, "text", "PANDI Registrar"],
                    ],
                ],
            }
        ],
    }


@pytest.fixture
def mock_iana_bootstrap_response() -> dict:
    """Sample IANA RDAP dns.json."""
    return {
        "version": "1.0",
        "publication": "2026-08-28T00:00:00Z",
        "services": [
            [["com", "net"], ["https://rdap.verisign.com/com/v1/"]],
            [["id"], ["https://rdap.pandi.id/rdap/"]],
            [["xyz"], ["https://rdap.centralnic.com/xyz/"]],
        ],
    }


def test_parse_rdap_json_com_structure(mock_com_rdap_response):
    """Test parsing .com response structure."""
    info = _parse_rdap_json("google.com", mock_com_rdap_response)
    assert info.domain == "google.com"
    assert info.registration_date == "1997-09-15T04:00:00Z"
    assert info.registrar == "MarkMonitor Inc."
    assert info.nameservers == ["ns1.google.com", "ns2.google.com"]
    assert "client delete prohibited" in info.status


def test_parse_rdap_json_id_structure(mock_id_rdap_response):
    """Test parsing .id response structure."""
    info = _parse_rdap_json("pandi.id", mock_id_rdap_response)
    assert info.domain == "pandi.id"
    assert info.registration_date == "2013-04-14T07:27:32Z"
    assert info.registrar == "PANDI Registrar"
    assert info.nameservers == ["bagendit.pandi.id", "sentani.pandi.id"]
    assert "server delete prohibited" in info.status


def test_lookup_com_success(temp_db, mock_com_rdap_response, mock_iana_bootstrap_response):
    """lookup('google.com') fetches and returns DomainInfo."""
    with patch("urllib.request.urlopen") as mock_urlopen:
        # 1st call for bootstrap, 2nd call for domain
        resp_bootstrap = MagicMock()
        resp_bootstrap.read.return_value = json.dumps(mock_iana_bootstrap_response).encode("utf-8")
        resp_bootstrap.__enter__.return_value = resp_bootstrap

        resp_domain = MagicMock()
        resp_domain.read.return_value = json.dumps(mock_com_rdap_response).encode("utf-8")
        resp_domain.__enter__.return_value = resp_domain

        mock_urlopen.side_effect = [resp_bootstrap, resp_domain]

        result = lookup("google.com", db_path=temp_db)
        assert result is not None
        assert result.domain == "google.com"
        assert result.registration_date == "1997-09-15T04:00:00Z"
        assert result.registrar == "MarkMonitor Inc."


def test_lookup_id_success(temp_db, mock_id_rdap_response, mock_iana_bootstrap_response):
    """lookup('pandi.id') fetches and returns DomainInfo with PANDI parser."""
    with patch("urllib.request.urlopen") as mock_urlopen:
        resp_bootstrap = MagicMock()
        resp_bootstrap.read.return_value = json.dumps(mock_iana_bootstrap_response).encode("utf-8")
        resp_bootstrap.__enter__.return_value = resp_bootstrap

        resp_domain = MagicMock()
        resp_domain.read.return_value = json.dumps(mock_id_rdap_response).encode("utf-8")
        resp_domain.__enter__.return_value = resp_domain

        mock_urlopen.side_effect = [resp_bootstrap, resp_domain]

        result = lookup("pandi.id", db_path=temp_db)
        assert result is not None
        assert result.domain == "pandi.id"
        assert result.registration_date == "2013-04-14T07:27:32Z"
        assert result.registrar == "PANDI Registrar"


def test_lookup_bootstrap_routing_xyz(temp_db, mock_iana_bootstrap_response):
    """lookup for .xyz queries centralnic bootstrap base URL."""
    xyz_response = {
        "ldhName": "NIC.XYZ",
        "events": [{"eventAction": "registration", "eventDate": "2013-09-11T11:58:06Z"}],
        "entities": [{"roles": ["registrar"], "handle": "CentralNic"}],
        "nameservers": [{"ldhName": "x.nic.xyz"}],
        "status": ["active"],
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        resp_bootstrap = MagicMock()
        resp_bootstrap.read.return_value = json.dumps(mock_iana_bootstrap_response).encode("utf-8")
        resp_bootstrap.__enter__.return_value = resp_bootstrap

        resp_domain = MagicMock()
        resp_domain.read.return_value = json.dumps(xyz_response).encode("utf-8")
        resp_domain.__enter__.return_value = resp_domain

        mock_urlopen.side_effect = [resp_bootstrap, resp_domain]

        result = lookup("nic.xyz", db_path=temp_db)
        assert result is not None
        assert result.domain == "nic.xyz"
        assert result.registration_date == "2013-09-11T11:58:06Z"

        # Verify bootstrap was queried
        req_args = mock_urlopen.call_args_list[1][0][0]
        assert "centralnic.com/xyz/domain/nic.xyz" in req_args.full_url


def test_lookup_404_negative_caching(temp_db, mock_iana_bootstrap_response):
    """404 response returns None and caches negative result with 24h TTL."""
    with patch("urllib.request.urlopen") as mock_urlopen:
        resp_bootstrap = MagicMock()
        resp_bootstrap.read.return_value = json.dumps(mock_iana_bootstrap_response).encode("utf-8")
        resp_bootstrap.__enter__.return_value = resp_bootstrap

        err_404 = urllib.error.HTTPError(
            url="https://rdap.verisign.com/com/v1/domain/not-found-xyz123.com",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=None,
        )

        mock_urlopen.side_effect = [resp_bootstrap, err_404]

        result = lookup("not-found-xyz123.com", db_path=temp_db)
        assert result is None

        # Verify negative cache row was created in SQLite
        with sqlite3.connect(str(temp_db)) as conn:
            cur = conn.execute("SELECT is_not_found FROM rdap_cache WHERE domain = 'not-found-xyz123.com'")
            row = cur.fetchone()
            assert row is not None
            assert row[0] == 1

        # Second call within 24h should hit negative cache without network request
        mock_urlopen.reset_mock()
        second_result = lookup("not-found-xyz123.com", db_path=temp_db)
        assert second_result is None
        assert mock_urlopen.call_count == 0


def test_lookup_cache_hit_positive(temp_db, mock_com_rdap_response, mock_iana_bootstrap_response):
    """Second call for positive result returns cached DomainInfo without calling network."""
    with patch("urllib.request.urlopen") as mock_urlopen:
        resp_bootstrap = MagicMock()
        resp_bootstrap.read.return_value = json.dumps(mock_iana_bootstrap_response).encode("utf-8")
        resp_bootstrap.__enter__.return_value = resp_bootstrap

        resp_domain = MagicMock()
        resp_domain.read.return_value = json.dumps(mock_com_rdap_response).encode("utf-8")
        resp_domain.__enter__.return_value = resp_domain

        mock_urlopen.side_effect = [resp_bootstrap, resp_domain]

        # 1st call -> network
        res1 = lookup("google.com", db_path=temp_db)
        assert res1 is not None
        assert mock_urlopen.call_count == 2

        # 2nd call -> cache hit
        mock_urlopen.reset_mock()
        res2 = lookup("google.com", db_path=temp_db)
        assert res2 is not None
        assert res2.domain == "google.com"
        assert res2.registration_date == "1997-09-15T04:00:00Z"
        assert mock_urlopen.call_count == 0


def test_lookup_cache_expiry_triggers_fresh_fetch(temp_db, mock_com_rdap_response, mock_iana_bootstrap_response):
    """Expired cache entry (> 7 days) triggers a fresh outbound lookup."""
    # Seed expired positive cache (8 days ago)
    old_time = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    with sqlite3.connect(str(temp_db)) as conn:
        from lib.rdap import _init_rdap_tables
        _init_rdap_tables(conn)
        conn.execute(
            """
            INSERT INTO rdap_cache (domain, registration_date, registrar, nameservers, status, is_not_found, fetched_at)
            VALUES ('google.com', '1997-09-15T04:00:00Z', 'Old Registrar', '[]', '[]', 0, ?)
            """,
            (old_time,),
        )
        conn.execute(
            """
            INSERT INTO rdap_bootstrap (tld, rdap_url, fetched_at)
            VALUES ('com', 'https://rdap.verisign.com/com/v1/', ?)
            """,
            (datetime.now(timezone.utc).isoformat(),),
        )
        conn.commit()

    with patch("urllib.request.urlopen") as mock_urlopen:
        resp_domain = MagicMock()
        resp_domain.read.return_value = json.dumps(mock_com_rdap_response).encode("utf-8")
        resp_domain.__enter__.return_value = resp_domain
        mock_urlopen.return_value = resp_domain

        result = lookup("google.com", db_path=temp_db)
        assert result is not None
        assert result.registrar == "MarkMonitor Inc."  # updated from network
        assert mock_urlopen.call_count == 1


def test_lookup_429_rate_limit_handled(temp_db, mock_iana_bootstrap_response):
    """429 Rate Limit returns None without raising exception."""
    with patch("urllib.request.urlopen") as mock_urlopen:
        resp_bootstrap = MagicMock()
        resp_bootstrap.read.return_value = json.dumps(mock_iana_bootstrap_response).encode("utf-8")
        resp_bootstrap.__enter__.return_value = resp_bootstrap

        err_429 = urllib.error.HTTPError(
            url="https://rdap.verisign.com/com/v1/domain/test.com",
            code=429,
            msg="Too Many Requests",
            hdrs={},
            fp=None,
        )
        mock_urlopen.side_effect = [resp_bootstrap, err_429]

        result = lookup("test.com", db_path=temp_db)
        assert result is None


def test_lookup_timeout_handled(temp_db, mock_iana_bootstrap_response):
    """Network timeout returns None without crashing."""
    with patch("urllib.request.urlopen") as mock_urlopen:
        resp_bootstrap = MagicMock()
        resp_bootstrap.read.return_value = json.dumps(mock_iana_bootstrap_response).encode("utf-8")
        resp_bootstrap.__enter__.return_value = resp_bootstrap

        mock_urlopen.side_effect = [resp_bootstrap, TimeoutError("Connection timed out")]

        result = lookup("test.com", db_path=temp_db)
        assert result is None


def test_lookup_fallback_when_tld_not_in_bootstrap(temp_db, mock_iana_bootstrap_response):
    """Fallback to rdap.org when TLD is unknown in IANA bootstrap."""
    unknown_response = {
        "ldhName": "TEST.UNKNOWN",
        "events": [{"eventAction": "registration", "eventDate": "2020-01-01T00:00:00Z"}],
    }
    with patch("urllib.request.urlopen") as mock_urlopen:
        resp_bootstrap = MagicMock()
        resp_bootstrap.read.return_value = json.dumps(mock_iana_bootstrap_response).encode("utf-8")
        resp_bootstrap.__enter__.return_value = resp_bootstrap

        resp_domain = MagicMock()
        resp_domain.read.return_value = json.dumps(unknown_response).encode("utf-8")
        resp_domain.__enter__.return_value = resp_domain

        mock_urlopen.side_effect = [resp_bootstrap, resp_domain]

        result = lookup("test.unknown", db_path=temp_db)
        assert result is not None
        req_args = mock_urlopen.call_args_list[1][0][0]
        assert "rdap.org/domain/test.unknown" in req_args.full_url


def test_no_insecure_ssl_in_module():
    """Verify that lib/rdap.py does not contain CERT_NONE or check_hostname=False."""
    module_path = Path(__file__).resolve().parent.parent / "lib" / "rdap.py"
    content = module_path.read_text(encoding="utf-8")
    assert "CERT_NONE" not in content, "Found insecure CERT_NONE in lib/rdap.py"
    assert "check_hostname=False" not in content, "Found check_hostname=False in lib/rdap.py"
    assert "check_hostname = False" not in content, "Found check_hostname = False in lib/rdap.py"
