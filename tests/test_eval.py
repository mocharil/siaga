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


def test_saved_eval_results_meets_dod_metric_targets():
    """DoD: Verify that full evaluation results meet Precision >= 85% and Recall >= 80%."""
    eval_file = BASE_DIR / "data" / "eval_results.json"
    assert eval_file.exists(), f"Evaluation results file missing at {eval_file}"

    with open(eval_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    summary = data.get("summary", {})
    metrics = summary.get("metrics", {})

    precision = metrics.get("precision", 0.0)
    recall = metrics.get("recall", 0.0)
    f1_score = metrics.get("f1_score", 0.0)
    fpr = metrics.get("false_positive_rate", 1.0)

    assert precision >= 0.85, f"Precision {precision:.4f} is below target 0.85"
    assert recall >= 0.80, f"Recall {recall:.4f} is below target 0.80"
    assert fpr <= 0.10, f"FPR {fpr:.4f} exceeds threshold 0.10"
    assert f1_score >= 0.82, f"F1 {f1_score:.4f} is below target 0.82"


def test_run_eval_on_smoke_subset(tmp_path):
    """Verify run_eval execution pipeline on a sample subset."""
    subset_file = tmp_path / "subset.jsonl"
    sample_data = [
        {"id": "s1", "type": "domain", "content": "bca-update-tarif.online", "label": "scam", "category": "phishing", "source": "sintetis"},
        {"id": "s2", "type": "domain", "content": "bca.co.id", "label": "legit", "category": "resmi", "source": "publik_resmi"},
    ]
    with open(subset_file, "w", encoding="utf-8") as f:
        for s in sample_data:
            f.write(json.dumps(s) + "\n")

    metrics = run_evaluation(
        testset_path=subset_file,
        db_path=DB_PATH,
        out_prefix="smoke_eval",
    )
    assert metrics["total_samples"] == 2
    assert metrics["metrics"]["accuracy"] == 1.0
