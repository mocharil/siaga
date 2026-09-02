"""Unit tests for lib/blacklist_check.py (T18).

Verifies read-only public blacklist checking, URLhaus query parser,
status reporting (listed/not_listed/unknown), and SQLite caching resilience.
"""

import json
from pathlib import Path
import sqlite3
from unittest.mock import MagicMock, patch
import urllib.error
import pytest

from lib.blacklist_check import (
    BlacklistResult,
    BlacklistStatus,
    is_listed,
)


@pytest.fixture
def temp_db(tmp_path):
    """Provide isolated SQLite database for blacklist caching tests."""
    db_file = tmp_path / "test_siaga.db"
    return db_file


def test_blacklist_listed_domain_success(temp_db, monkeypatch):
    """DoD: Known phishing/malware domain is recognized as LISTED."""
    monkeypatch.setenv("URLHAUS_AUTH_KEY", "test-key-123")
    mock_response_data = {
        "query_status": "ok",
        "id": "123456",
        "url_count": "2",
        "urls": [
            {"url": "http://evil-phish.xyz/login", "url_status": "online"},
            {"url": "http://evil-phish.xyz/payload.exe", "url_status": "offline"},
        ],
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_response_data).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        result = is_listed("evil-phish.xyz", db_path=temp_db)
        assert result.status == BlacklistStatus.LISTED
        assert result.source == "URLhaus"
        assert "2 reported payloads" in result.details
        assert mock_urlopen.called


def test_blacklist_not_listed_official_domain(temp_db, monkeypatch):
    """DoD: Official/clean domain is recognized as NOT_LISTED."""
    monkeypatch.setenv("URLHAUS_AUTH_KEY", "test-key-123")
    mock_response_data = {
        "query_status": "no_results",
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_response_data).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        result = is_listed("bca.co.id", db_path=temp_db)
        assert result.status == BlacklistStatus.NOT_LISTED
        assert result.source == "URLhaus"
        assert "Clean" in result.details


def test_blacklist_offline_or_network_error_returns_unknown(temp_db, monkeypatch):
    """DoD: Network errors or offline mode return UNKNOWN without crashing and without returning NOT_LISTED."""
    monkeypatch.setenv("URLHAUS_AUTH_KEY", "test-key-123")

    # 1. With allow_network=False
    result_offline = is_listed("test-domain.xyz", db_path=temp_db, allow_network=False)
    assert result_offline.status == BlacklistStatus.UNKNOWN
    assert result_offline.status != BlacklistStatus.NOT_LISTED

    # 2. With URLError exception simulated
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Network is unreachable")):
        result_error = is_listed("test-network-fail.xyz", db_path=temp_db, allow_network=True)
        assert result_error.status == BlacklistStatus.UNKNOWN
        assert result_error.status != BlacklistStatus.NOT_LISTED
        assert "network_error" in result_error.source or "error" in result_error.source


def test_blacklist_no_auth_key_skips_network_call(temp_db, monkeypatch):
    """Regression (2026-09-02): abuse.ch made Auth-Key mandatory -- every
    URLhaus request without it 401s. Without a key configured, is_listed()
    must report UNKNOWN honestly ("tidak dapat diperiksa") without ever
    attempting the doomed request, so 100s of domains don't each log a
    401 warning."""
    monkeypatch.delenv("URLHAUS_AUTH_KEY", raising=False)

    with patch("urllib.request.urlopen") as mock_urlopen:
        result = is_listed("no-key-configured.xyz", db_path=temp_db)
        assert result.status == BlacklistStatus.UNKNOWN
        assert result.source == "no_auth_key"
        assert "auth.abuse.ch" in result.details
        assert not mock_urlopen.called


def test_blacklist_invalid_auth_key_reported_distinctly(temp_db, monkeypatch):
    """A configured-but-rejected key (401 despite sending Auth-Key) must be
    distinguishable from "no key configured" or a generic network error --
    otherwise a typo'd key looks identical to abuse.ch being down."""
    monkeypatch.setenv("URLHAUS_AUTH_KEY", "wrong-or-expired-key")

    err = urllib.error.HTTPError(url="x", code=401, msg="Unauthorized", hdrs=None, fp=None)
    with patch("urllib.request.urlopen", side_effect=err):
        result = is_listed("some-domain.xyz", db_path=temp_db)
        assert result.status == BlacklistStatus.UNKNOWN
        assert result.source == "invalid_auth_key"


def test_blacklist_sqlite_caching_hit(temp_db, monkeypatch):
    """DoD: Repeated queries hit local SQLite cache and avoid redundant network round-trips."""
    monkeypatch.setenv("URLHAUS_AUTH_KEY", "test-key-123")
    mock_response_data = {"query_status": "ok", "urls": [{"url": "http://cached-phish.xyz"}]}
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_response_data).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        # First query -> fetches from network
        res1 = is_listed("cached-phish.xyz", db_path=temp_db)
        assert res1.status == BlacklistStatus.LISTED
        assert mock_urlopen.call_count == 1

        # Second query -> hits SQLite cache without network call
        res2 = is_listed("cached-phish.xyz", db_path=temp_db)
        assert res2.status == BlacklistStatus.LISTED
        assert mock_urlopen.call_count == 1  # Still 1, no second call


def test_blacklist_read_only_and_privacy_payload(temp_db, monkeypatch):
    """Verify that only the domain is transmitted and no sensitive user data is exposed."""
    monkeypatch.setenv("URLHAUS_AUTH_KEY", "test-key-123")
    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps({"query_status": "no_results"}).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
        is_listed("target-domain.com", db_path=temp_db)
        called_req = mock_urlopen.call_args[0][0]
        # Verify request body contains only host=target-domain.com
        assert called_req.data == b"host=target-domain.com"
        assert called_req.get_method() == "POST"
        assert called_req.get_header("Auth-key") == "test-key-123"
