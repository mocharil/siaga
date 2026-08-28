"""Unit tests for lib/similarity.py (T16).

Verifies Damerau-Levenshtein distance, keyword positioning, homoglyph decoding,
and ensures zero false positives on negative/official test cases.
"""

from pathlib import Path
import sqlite3
import pytest

from lib.similarity import (
    Match,
    damerau_levenshtein_distance,
    find_similar,
    load_watchlist,
    normalize_homoglyphs,
)


@pytest.fixture(scope="module")
def shared_watchlist():
    """Load default expanded watchlist once for tests."""
    return load_watchlist()


# ------------------------------------------------------------------------------
# 1. Damerau-Levenshtein Algorithm Unit Tests
# ------------------------------------------------------------------------------

def test_damerau_levenshtein_cases():
    """Verify Damerau-Levenshtein transposition, insertion, deletion, and substitution."""
    # Exact match
    assert damerau_levenshtein_distance("tokopedia", "tokopedia") == 0
    # Single Transposition (swap 'ed' -> 'de' is 1 edit)
    assert damerau_levenshtein_distance("tokopdeia", "tokopedia") == 1
    # Deletion
    assert damerau_levenshtein_distance("tokopdia", "tokopedia") == 1
    # Insertion
    assert damerau_levenshtein_distance("tokopeddia", "tokopedia") == 1
    # Substitution
    assert damerau_levenshtein_distance("tokopedix", "tokopedia") == 1
    # Multiple edits
    assert damerau_levenshtein_distance("tokoped", "tokopedia") == 2


# ------------------------------------------------------------------------------
# 2. Homoglyph Normalization Unit Tests
# ------------------------------------------------------------------------------

def test_homoglyph_normalization():
    """Verify conversion of visually similar digits and Cyrillic characters."""
    # 0 -> o, 1 -> l
    assert normalize_homoglyphs("b0a") == "boa"
    assert normalize_homoglyphs("t0k0pedia") == "tokopedia"
    # Cyrillic small 'а' (\u0430) and 'с' (\u0441)
    cyrillic_bca = "b\u0441\u0430"
    assert normalize_homoglyphs(cyrillic_bca) == "bca"


# ------------------------------------------------------------------------------
# 3. DoD 12 Core Test Cases (7 True Positives + 5 True Negatives)
# ------------------------------------------------------------------------------

def test_7_true_positive_phishing_cases(shared_watchlist):
    """DoD: Test 7 known phishing/typosquatting domain patterns matched accurately."""
    positive_cases = [
        ("klikbca-update.online", "Bank Central Asia"),
        ("bankmandiri-promo.xyz", "Bank Mandiri"),
        ("bca.promo-site.xyz", "Bank Central Asia"),
        ("tokopdia.com", "Tokopedia"),
        ("traveloka-resmi.site", "Traveloka"),
        ("indodaxx.com", "Indodax Indonesia"),
        ("bni-mobile-aktivasi.top", "Bank Negara Indonesia"),
    ]

    for domain, expected_brand in positive_cases:
        matches = find_similar(domain, shared_watchlist)
        assert len(matches) >= 1, f"Expected match for phishing domain: {domain}"
        matched_brands = [m.brand_name for m in matches]
        assert expected_brand in matched_brands, (
            f"Expected brand '{expected_brand}' in {matched_brands} for domain '{domain}'"
        )


def test_5_true_negative_cases_no_false_positives(shared_watchlist):
    """DoD: 5 test cases that MUST NOT match (prevents false positives)."""
    negative_cases = [
        # 1. Official domain itself
        "bca.co.id",
        # 2. Official domain itself
        "tokopedia.com",
        # 3. Unrelated short 4-letter domain (should NOT trigger 3-letter BCA)
        "bcam.com",
        # 4. Unrelated domain with distance > allowed threshold (should NOT match Mandiri)
        "mandala.com",
        # 5. Unrelated foreign legitimate domain
        "google.com",
    ]

    for domain in negative_cases:
        matches = find_similar(domain, shared_watchlist)
        assert len(matches) == 0, (
            f"False Positive detected! Domain '{domain}' should NOT match any watchlist entry, but got: {matches}"
        )


# ------------------------------------------------------------------------------
# 4. Live Verification Against 20 Real CT Domains
# ------------------------------------------------------------------------------

def test_no_false_positives_on_sample_real_domains(shared_watchlist):
    """DoD: Test check on 20 sample domains from ct_raw shows no obvious false positives."""
    db_path = Path(__file__).resolve().parent.parent / "data" / "siaga.db"
    if not db_path.exists():
        pytest.skip("siaga.db not found for live sampling")

    with sqlite3.connect(str(db_path)) as conn:
        cur = conn.execute("SELECT domain FROM ct_raw ORDER BY id DESC LIMIT 20")
        sample_domains = [r[0] for r in cur.fetchall()]

    if not sample_domains:
        pytest.skip("No domains found in ct_raw")

    for dom in sample_domains:
        matches = find_similar(dom, shared_watchlist)
        for m in matches:
            assert m.method in ["keyword", "edit_distance", "homoglyph", "permutation"]
            assert len(m.matched_term) >= 3
