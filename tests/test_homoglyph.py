"""Unit tests for lib/homoglyph.py (T17).

Verifies punycode IDN decoding, Cyrillic & Greek script spoof normalization,
number lookalikes, digraphs, and ensures legitimate domains are untouched.
"""

import pytest
from lib.homoglyph import (
    HomoglyphResult,
    analyze_homoglyph,
    decode_punycode,
    normalize,
)


def test_decode_punycode_ascii():
    """ASCII domain without punycode prefix returns False."""
    decoded, is_puny = decode_punycode("bca.co.id")
    assert decoded == "bca.co.id"
    assert is_puny is False


def test_decode_punycode_idn():
    """Punycode domain (xn--) decodes to unicode string and returns True."""
    # xn--ba-omc.com -> bсa.com (with Cyrillic 'с')
    puny_domain = "xn--ba-omc.com"
    decoded, is_puny = decode_punycode(puny_domain)
    assert is_puny is True
    assert "b" in decoded and "a.com" in decoded
    assert normalize(puny_domain) == "bca.com"


def test_cyrillic_homoglyphs_real_attack():
    """Detect and normalize real Cyrillic spoof letters targeting Indonesian brands."""
    # 'b' + cyrillic 'с' (\u0441) + cyrillic 'а' (\u0430) + '.com'
    cyrillic_bca = "b\u0441\u0430.com"
    normalized = normalize(cyrillic_bca)
    assert normalized == "bca.com"

    res = analyze_homoglyph(cyrillic_bca)
    assert res.has_homoglyphs is True
    assert "cyrillic_script_spoof" in res.detected_spoofs
    assert res.normalized_domain == "bca.com"


def test_greek_homoglyphs_normalization():
    """Detect and normalize Greek lookalikes."""
    # 'b' + greek alpha (\u03b1) + 'nk.com'
    greek_bank = "b\u03b1nk.com"
    normalized = normalize(greek_bank)
    assert normalized == "bank.com"

    res = analyze_homoglyph(greek_bank)
    assert res.has_homoglyphs is True
    assert "greek_script_spoof" in res.detected_spoofs


def test_leet_digit_normalization():
    """Normalize common visual leet numbers inside words (0->o, 1->l, etc)."""
    assert normalize("t0k0pedia.com") == "tokopedia.com"
    assert normalize("b0a.co.id") == "boa.co.id"
    assert normalize("adakam1.id") == "adakami.id"


def test_digraph_substitution():
    """Normalize common visual digraphs: rn -> m, vv -> w."""
    assert normalize("rnodalku.com") == "modalku.com"
    assert normalize("vvondr.com") == "wondr.com"


def test_legitimate_indonesian_domains_untouched():
    """DoD: Normalization must NOT mutate or break legitimate Indonesian domains."""
    legit_domains = [
        "bca.co.id",
        "bankmandiri.co.id",
        "pajak.go.id",
        "bpjs-kesehatan.go.id",
        "posindonesia.co.id",
        "kemdikbud.go.id",
        "shopee.co.id",
        "tokopedia.com",
        "superbank.id",
    ]

    for dom in legit_domains:
        normalized = normalize(dom)
        assert normalized == dom, f"Legitimate domain '{dom}' was destructively mutated to '{normalized}'"

        res = analyze_homoglyph(dom)
        assert res.is_punycode is False
        assert len(res.detected_spoofs) == 0
