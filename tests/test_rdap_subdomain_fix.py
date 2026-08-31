"""Additional regression tests for lib/rdap.py — subdomain input handling.

Bug fix: lookup() now extracts registrable domain BEFORE cache and query,
so subdomains like 'investors.spotify.com.id2.bumiayuvpn.web.id' correctly
query for 'bumiayuvpn.web.id' rather than returning None on a 404.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from lib.rdap import lookup


@pytest.fixture
def temp_db_sub(tmp_path: Path) -> Path:
    return tmp_path / "test_rdap_sub.db"


@pytest.fixture
def mock_iana_bootstrap() -> dict:
    return {
        "version": "1.0",
        "services": [
            [["com", "net"], ["https://rdap.verisign.com/com/v1/"]],
            [["id"], ["https://rdap.pandi.id/rdap/"]],
        ],
    }


@pytest.fixture
def mock_com_rdap() -> dict:
    return {
        "handle": "2138514_DOMAIN_COM-VRSN",
        "ldhName": "GOOGLE.COM",
        "status": ["client delete prohibited"],
        "events": [{"eventAction": "registration", "eventDate": "1997-09-15T04:00:00Z"}],
        "nameservers": [{"ldhName": "NS1.GOOGLE.COM"}, {"ldhName": "NS2.GOOGLE.COM"}],
        "entities": [
            {
                "roles": ["registrar"],
                "vcardArray": ["vcard", [["fn", {}, "text", "MarkMonitor Inc."]]],
            }
        ],
    }


def test_lookup_subdomain_gives_same_result_as_registrable_domain(
    temp_db_sub, mock_com_rdap, mock_iana_bootstrap
):
    """lookup() on a subdomain must produce the same result as lookup() on the
    registrable domain.  Key invariant: lookup('sub.google.com') == lookup('google.com').

    Before the fix, the full subdomain was passed to the RDAP URL which always
    returned HTTP 404 (registries only store apex records).
    """
    with patch("urllib.request.urlopen") as mock_urlopen:
        resp_bootstrap = MagicMock()
        resp_bootstrap.read.return_value = json.dumps(mock_iana_bootstrap).encode("utf-8")
        resp_bootstrap.__enter__.return_value = resp_bootstrap

        resp_domain = MagicMock()
        resp_domain.read.return_value = json.dumps(mock_com_rdap).encode("utf-8")
        resp_domain.__enter__.return_value = resp_domain

        mock_urlopen.side_effect = [resp_bootstrap, resp_domain]

        result = lookup("login.phishing.sub.google.com", db_path=temp_db_sub)

        assert result is not None, "lookup() on subdomain returned None — registrable domain extraction failed"
        assert result.domain == "google.com"
        assert result.registrar == "MarkMonitor Inc."
        # RDAP query URL must contain only the registrable domain
        domain_call_url = mock_urlopen.call_args_list[1][0][0].full_url
        assert "google.com" in domain_call_url
        assert "login.phishing.sub" not in domain_call_url


def test_lookup_subdomain_uses_shared_cache_with_registrable_domain(
    temp_db_sub, mock_com_rdap, mock_iana_bootstrap
):
    """After lookup('google.com') populates cache, lookup('sub.google.com') must
    return a cache hit without an additional network request.

    Verifies cache key consolidation: previously each distinct subdomain was cached
    separately, meaning every unique subdomain caused its own 404 and polluted
    the negative cache independently.
    """
    with patch("urllib.request.urlopen") as mock_urlopen:
        resp_bootstrap = MagicMock()
        resp_bootstrap.read.return_value = json.dumps(mock_iana_bootstrap).encode("utf-8")
        resp_bootstrap.__enter__.return_value = resp_bootstrap

        resp_domain = MagicMock()
        resp_domain.read.return_value = json.dumps(mock_com_rdap).encode("utf-8")
        resp_domain.__enter__.return_value = resp_domain

        mock_urlopen.side_effect = [resp_bootstrap, resp_domain]

        result1 = lookup("google.com", db_path=temp_db_sub)
        assert result1 is not None

        # Reset so any further network call would be detectable
        mock_urlopen.reset_mock()
        mock_urlopen.side_effect = None

        result2 = lookup("phishing.sub.google.com", db_path=temp_db_sub)

        assert result2 is not None, "Subdomain lookup should hit cache from registrable domain entry"
        assert result2.domain == "google.com"
        assert mock_urlopen.call_count == 0, (
            "Network was called again even though registrable domain was already cached — "
            "subdomain is not sharing the same cache key"
        )


def test_lookup_long_indonesian_subdomain_extracts_web_id_apex(
    temp_db_sub, mock_iana_bootstrap
):
    """Regression: exact example from the bug report.

    'investors.spotify.com.id2.bumiayuvpn.web.id' must resolve to registrable
    domain 'bumiayuvpn.web.id' (.id compound SLD), NOT return None.

    Before the fix this returned None because the full subdomain string hit
    HTTP 404 from rdap.pandi.id (only apex .id domains are registered there).
    """
    mock_web_id_response = {
        "handle": "BUMIAYUVPN_WEB_ID",
        "ldhName": "bumiayuvpn.web.id",
        "status": ["active"],
        "events": [{"eventAction": "registration", "eventDate": "2026-07-01T00:00:00Z"}],
        "nameservers": [
            {"ldhName": "ns1.hostingprovider.com"},
            {"ldhName": "ns2.hostingprovider.com"},
        ],
        "entities": [
            {
                "roles": ["registrar"],
                "vcardArray": ["vcard", [["fn", {}, "text", "Rumahweb Indonesia"]]],
            }
        ],
    }

    with patch("urllib.request.urlopen") as mock_urlopen:
        resp_bootstrap = MagicMock()
        resp_bootstrap.read.return_value = json.dumps(mock_iana_bootstrap).encode("utf-8")
        resp_bootstrap.__enter__.return_value = resp_bootstrap

        resp_domain = MagicMock()
        resp_domain.read.return_value = json.dumps(mock_web_id_response).encode("utf-8")
        resp_domain.__enter__.return_value = resp_domain

        mock_urlopen.side_effect = [resp_bootstrap, resp_domain]

        result = lookup(
            "investors.spotify.com.id2.bumiayuvpn.web.id",
            db_path=temp_db_sub,
        )

        assert result is not None, (
            "lookup() on the exact bug-report subdomain returned None — "
            "registrable domain extraction for .web.id compound SLD failed"
        )
        assert result.domain == "bumiayuvpn.web.id"
        assert result.registrar == "Rumahweb Indonesia"
        assert result.nameservers == ["ns1.hostingprovider.com", "ns2.hostingprovider.com"]

        domain_call_url = mock_urlopen.call_args_list[1][0][0].full_url
        assert "bumiayuvpn.web.id" in domain_call_url
        assert "investors.spotify.com.id2" not in domain_call_url
