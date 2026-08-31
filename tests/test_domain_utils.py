"""Unit tests for lib/domain_utils.py — registrable_domain() extraction.

Shared utility moved from lib/campaign.py so that both lib/rdap.py and
lib/campaign.py use the same authoritative implementation.
"""

from __future__ import annotations

import pytest

from lib.domain_utils import registrable_domain


# ==============================================================================
# Basic extraction: generic TLDs (two-label rule)
# ==============================================================================

@pytest.mark.parametrize("hostname, expected", [
    # Plain apex domains — returned as-is
    ("google.com", "google.com"),
    ("tokopedia.com", "tokopedia.com"),
    ("bca.co.id", "bca.co.id"),

    # Single-level subdomains
    ("www.google.com", "google.com"),
    ("ns1.badhost.xyz", "badhost.xyz"),
    ("mail.tokopedia.com", "tokopedia.com"),

    # Deep multi-level subdomains (generic TLD)
    ("login.phishing.sub.google.com", "google.com"),
    ("a.b.c.d.e.example.net", "example.net"),

    # Trailing dot is stripped
    ("www.google.com.", "google.com"),
])
def test_registrable_domain_generic_tld(hostname, expected):
    assert registrable_domain(hostname) == expected


# ==============================================================================
# Indonesian compound SLD: .co.id, .go.id, .ac.id, .or.id, .web.id
# ==============================================================================

@pytest.mark.parametrize("hostname, expected", [
    # Apex compound .id domain
    ("bca.co.id", "bca.co.id"),
    ("pandi.id", "pandi.id"),        # plain .id (NOT in ID_SECOND_LEVEL_TLDS — two-label rule)
    ("kemenkeu.go.id", "kemenkeu.go.id"),
    ("namabank.web.id", "namabank.web.id"),

    # Single subdomain above compound .id
    ("www.bca.co.id", "bca.co.id"),
    ("ns1.provider.co.id", "provider.co.id"),
    ("api.namabank.web.id", "namabank.web.id"),

    # Deep subdomain — the exact SIAGA-typical phishing pattern
    ("login.namabank.brand.web.id", "brand.web.id"),
    ("investors.spotify.com.id2.bumiayuvpn.web.id", "bumiayuvpn.web.id"),
])
def test_registrable_domain_id_compound_sld(hostname, expected):
    assert registrable_domain(hostname) == expected


# ==============================================================================
# Edge cases that must return None
# ==============================================================================

@pytest.mark.parametrize("hostname", [
    "localhost",        # single label
    "",                 # empty
    "   ",              # whitespace only
    "nodot",            # no dot at all
])
def test_registrable_domain_returns_none_for_invalid(hostname):
    assert registrable_domain(hostname) is None


# ==============================================================================
# Case-insensitivity: all inputs must be normalized to lowercase
# ==============================================================================

def test_registrable_domain_lowercases_output():
    assert registrable_domain("NS1.BadHost.XYZ") == "badhost.xyz"
    assert registrable_domain("Login.BANK.Web.ID") == "bank.web.id"
