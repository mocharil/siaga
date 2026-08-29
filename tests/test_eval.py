"""Unit tests for Evaluation Runner and Calibration DoD (T21).

Verifies the 120-sample test set integrity, metrics computation,
and asserts that calibrated precision >= 85% and recall >= 80%.
"""

import json
from pathlib import Path
import pytest

from scripts.run_eval import run_evaluation

BASE_DIR = Path(__file__).resolve().parent.parent
TESTSET_PATH = BASE_DIR / "data" / "testset.jsonl"
DB_PATH = BASE_DIR / "data" / "siaga.db"


def test_testset_sample_count_and_structure():
    """DoD: Test set must contain exactly 120 validated labeled samples."""
    assert TESTSET_PATH.exists(), f"Testset file missing at {TESTSET_PATH}"

    samples = []
    with open(TESTSET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))

    assert len(samples) == 120, f"Expected 120 samples, found {len(samples)}"

    # Check required fields
    for s in samples:
        assert "id" in s
        assert "type" in s
        assert "content" in s
        assert "label" in s
        assert s["label"] in ["scam", "legit"]
        assert s["type"] in ["message", "domain"]


def test_run_eval_meets_dod_metric_targets():
    """DoD: Calibrated evaluation must achieve Precision >= 85% and Recall >= 80%."""
    metrics = run_evaluation(
        testset_path=TESTSET_PATH,
        db_path=DB_PATH,
        out_prefix="test_eval_output",
    )

    precision = metrics["metrics"]["precision"]
    recall = metrics["metrics"]["recall"]
    f1_score = metrics["metrics"]["f1_score"]
    fpr = metrics["metrics"]["false_positive_rate"]

    assert precision >= 0.85, f"Precision {precision:.4f} is below target 0.85"
    assert recall >= 0.80, f"Recall {recall:.4f} is below target 0.80"
    assert fpr <= 0.10, f"FPR {fpr:.4f} exceeds threshold 0.10"
    assert f1_score >= 0.82, f"F1 {f1_score:.4f} is below target 0.82"
