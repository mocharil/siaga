"""Unit tests for lib/redirect.py (T13).

Verifies strictly HEAD-only redirect tracing, hop chains, loop detection, timeout, and max hops.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import urllib.error
import urllib.response

import pytest

from lib.redirect import RedirectTrace, trace


def test_no_requests_get_in_source_code():
    """DoD: Ensure zero instances of requests.get in both lib/extract.py and lib/redirect.py."""
    lib_dir = Path(__file__).resolve().parent.parent / "lib"
    for filename in ["extract.py", "redirect.py"]:
        code = (lib_dir / filename).read_text(encoding="utf-8")
        assert "requests.get" not in code, f"Found requests.get in {filename}"
        assert 'method="GET"' not in code and "method='GET'" not in code, f"Found GET method in {filename}"
        assert "import requests" not in code, f"Found requests import in {filename}"


def test_no_insecure_ssl_in_redirect_module():
    """Ensure strict TLS verification is maintained in lib/redirect.py."""
    code = (Path(__file__).resolve().parent.parent / "lib" / "redirect.py").read_text(encoding="utf-8")
    assert "CERT_NONE" not in code
    assert "check_hostname=False" not in code
    assert "check_hostname = False" not in code


def test_trace_single_hop_success():
    """Test URL that directly responds with 200 OK (1 hop)."""
    with patch("urllib.request.OpenerDirector.open") as mock_open:
        resp = MagicMock()
        resp.status = 200
        resp.headers = {}
        mock_open.return_value = resp

        result = trace("https://example.com/login")
        assert result.status == "ok"
        assert result.final_url == "https://example.com/login"
        assert len(result.hops) == 1
        assert result.hops[0].status_code == 200

        # Assert HEAD method was used
        req = mock_open.call_args[0][0]
        assert req.get_method() == "HEAD"


def test_trace_multi_hop_redirect_chain():
    """Test 2-hop redirect chain: 301 -> 302 -> 200."""
    with patch("urllib.request.OpenerDirector.open") as mock_open:
        # Hop 1: bit.ly -> 301 Location: https://promo.com
        resp1 = MagicMock()
        resp1.status = 301
        resp1.headers = {"Location": "https://promo.com/auth"}

        # Hop 2: promo.com -> 302 Location: https://phishing.xyz/bca
        resp2 = MagicMock()
        resp2.status = 302
        resp2.headers = {"Location": "https://phishing.xyz/bca"}

        # Hop 3: phishing.xyz -> 200 OK
        resp3 = MagicMock()
        resp3.status = 200
        resp3.headers = {}

        mock_open.side_effect = [resp1, resp2, resp3]

        result = trace("https://bit.ly/test321")
        assert result.status == "ok"
        assert result.final_url == "https://phishing.xyz/bca"
        assert len(result.hops) == 3
        assert result.hops[0].status_code == 301
        assert result.hops[1].status_code == 302
        assert result.hops[2].status_code == 200

        # Verify all calls used HEAD
        for call_item in mock_open.call_args_list:
            req = call_item[0][0]
            assert req.get_method() == "HEAD"


def test_trace_redirect_loop():
    """Test redirect loop: A -> B -> A detected and terminated cleanly."""
    with patch("urllib.request.OpenerDirector.open") as mock_open:
        resp_a = MagicMock()
        resp_a.status = 302
        resp_a.headers = {"Location": "https://site-b.com/step"}

        resp_b = MagicMock()
        resp_b.status = 302
        resp_b.headers = {"Location": "https://site-a.com/start"}

        mock_open.side_effect = [resp_a, resp_b]

        result = trace("https://site-a.com/start")
        assert result.status == "loop_detected"
        assert result.error_message == "Redirect loop detected"
        assert len(result.hops) == 2


def test_trace_max_hops_exceeded():
    """Test chain exceeding max_hops (e.g. 5) terminates with status max_hops_exceeded."""
    with patch("urllib.request.OpenerDirector.open") as mock_open:
        def make_redirect_resp(hop_num):
            resp = MagicMock()
            resp.status = 302
            resp.headers = {"Location": f"https://example.com/step_{hop_num}"}
            return resp

        mock_open.side_effect = [make_redirect_resp(i) for i in range(1, 10)]

        result = trace("https://example.com/step_0", max_hops=3)
        assert result.status == "max_hops_exceeded"
        assert len(result.hops) == 3


def test_trace_unreachable_network_error():
    """Test network failure or unreachable domain handled gracefully without exception."""
    with patch("urllib.request.OpenerDirector.open") as mock_open:
        mock_open.side_effect = urllib.error.URLError("Connection refused")

        result = trace("https://unreachable-host-xyz.com")
        assert result.status == "unreachable"
        assert len(result.hops) == 1
        assert result.hops[0].status_code == 0
