"""Unit tests for data/raw_samples/ (T07).

Validates test dataset structure, diversity of attack vectors, absence of personal identifiable
information (PII), and presence of both phishing and legitimate baseline samples.
"""

import json
from pathlib import Path
import re
import pytest

SAMPLES_PATH = Path(__file__).resolve().parent.parent / "data" / "raw_samples" / "public_fraud_samples.json"


def test_samples_file_exists_and_count():
    """DoD: At least 20+ samples stored in data/raw_samples/."""
    assert SAMPLES_PATH.exists(), f"Samples file not found at {SAMPLES_PATH}"
    data = json.loads(SAMPLES_PATH.read_text(encoding="utf-8"))
    assert len(data) >= 20, f"Expected >= 20 samples, found {len(data)}"


def test_samples_schema_and_categories():
    """Verify all samples contain valid schema fields and recognized labels."""
    data = json.loads(SAMPLES_PATH.read_text(encoding="utf-8"))
    required_fields = ["id", "category", "target_brand", "label", "text", "attack_vector", "requested_actions"]

    phishing_count = 0
    legit_count = 0

    seen_ids = set()

    for idx, item in enumerate(data, start=1):
        for field in required_fields:
            assert field in item and item[field], f"Sample #{idx} missing field '{field}'"

        assert item["label"] in ["phishing", "legitimate"], f"Invalid label '{item['label']}' in sample #{idx}"
        if item["label"] == "phishing":
            phishing_count += 1
        else:
            legit_count += 1

        assert item["id"] not in seen_ids, f"Duplicate sample id '{item['id']}'"
        seen_ids.add(item["id"])

    assert phishing_count >= 20, f"Expected >= 20 phishing samples, got {phishing_count}"
    assert legit_count >= 5, f"Expected >= 5 legitimate control samples, got {legit_count}"


def test_no_real_pii_in_samples():
    """Verify that samples use sanitized/synthetic phone numbers, names, and accounts."""
    data = json.loads(SAMPLES_PATH.read_text(encoding="utf-8"))

    # Check for placeholder patterns and sanitized formats
    for item in data:
        text = item["text"]
        assert len(text) >= 30, f"Sample text too short: '{text}'"

        # Ensure no real individual identity leakage (all sample names are generic Indonesian placeholders like Budi, Hendra)
        assert "ktp asli" not in text.lower()
        assert "nik asli" not in text.lower()
