"""Tests for data/watchlist.csv format and validation rules (T06)."""

import csv
from pathlib import Path
import re
import pytest

WATCHLIST_PATH = Path(__file__).resolve().parent.parent / "data" / "watchlist.csv"
VALID_CATEGORIES = {"bank", "ecommerce", "pemerintah", "logistik"}
VALID_MATCH_MODES = {"keyword_only", "edit_distance"}


def test_watchlist_file_exists():
    """Watchlist CSV file must exist."""
    assert WATCHLIST_PATH.exists(), f"Watchlist file not found at {WATCHLIST_PATH}"


def test_watchlist_header_and_count():
    """Watchlist must contain valid headers and at least 50 entries."""
    with open(WATCHLIST_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        expected_headers = [
            "brand_name",
            "aliases",
            "official_domain",
            "category",
            "match_mode",
            "source",
        ]
        assert reader.fieldnames == expected_headers, f"Headers mismatch: {reader.fieldnames}"

        rows = list(reader)
        assert len(rows) >= 50, f"Expected >= 50 rows, got {len(rows)}"


def test_watchlist_row_validity():
    """Every row must have non-empty columns, valid categories, valid domain syntax, and correct match_mode."""
    domain_regex = re.compile(r"^(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$")

    with open(WATCHLIST_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        seen_domains = set()

        for idx, row in enumerate(reader, start=2):
            brand = row["brand_name"].strip()
            aliases = row["aliases"].strip()
            domain = row["official_domain"].strip()
            category = row["category"].strip()
            match_mode = row["match_mode"].strip()
            source = row["source"].strip()

            assert brand, f"Row {idx}: brand_name is empty"
            assert aliases, f"Row {idx}: aliases is empty"
            assert domain, f"Row {idx}: official_domain is empty"
            assert source, f"Row {idx}: source is empty"

            # Domain syntax check
            assert not domain.startswith("http://") and not domain.startswith("https://"), (
                f"Row {idx}: domain should not contain URL scheme: {domain}"
            )
            assert "/" not in domain, f"Row {idx}: domain should not contain path: {domain}"
            assert domain_regex.match(domain), f"Row {idx}: invalid domain format: {domain}"

            # Category check
            assert category in VALID_CATEGORIES, (
                f"Row {idx}: invalid category '{category}', must be one of {VALID_CATEGORIES}"
            )

            # Match mode check
            assert match_mode in VALID_MATCH_MODES, (
                f"Row {idx}: invalid match_mode '{match_mode}', must be one of {VALID_MATCH_MODES}"
            )

            # DoD 4 rule: Names <= 4 characters must strictly use keyword_only
            # (e.g. BCA, BRI, BNI, BSI, BTN, Mega, OCBC, BTPN, Jago, Blu, BNC, BJB, DKI, UOB, HSBC, DANA, OVO, DJP, PLN, JNE, J&T, POS, TIKI)
            if len(brand) <= 4:
                assert match_mode == "keyword_only", (
                    f"Row {idx} ({brand}): brand_name <= 4 chars must use keyword_only, got {match_mode}"
                )

            # Duplicate domain check
            assert domain not in seen_domains, f"Row {idx}: duplicate official_domain '{domain}'"
            seen_domains.add(domain)


def test_watchlist_category_distribution():
    """Verify that banks form the majority and all 4 categories are represented."""
    counts = {}
    with open(WATCHLIST_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cat = row["category"]
            counts[cat] = counts.get(cat, 0) + 1

    # Banks should be the largest group (phishing prime target)
    assert counts.get("bank", 0) >= 20, f"Expected >= 20 banks, got {counts.get('bank')}"
    assert counts.get("ecommerce", 0) >= 5, f"Expected >= 5 ecommerce, got {counts.get('ecommerce')}"
    assert counts.get("pemerintah", 0) >= 5, f"Expected >= 5 pemerintah, got {counts.get('pemerintah')}"
    assert counts.get("logistik", 0) >= 5, f"Expected >= 5 logistik, got {counts.get('logistik')}"


def test_watchlist_verification_sources_present():
    """Verify that every row includes concrete verification source evidence."""
    with open(WATCHLIST_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader, start=2):
            source = row["source"].strip()
            assert len(source) >= 5, f"Row {idx} ({row['brand_name']}): verification source is too short: '{source}'"
            # Ensure source mentions a registry/authority or DNS resolution
            assert any(k in source for k in ["DNS:", "OJK", "BI", "PANDI", "Kominfo", "Kemen", "BUMN", "Asperindo", "Polri"]), (
                f"Row {idx} ({row['brand_name']}): source must contain recognizable authority or DNS evidence: '{source}'"
            )
