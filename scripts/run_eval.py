#!/usr/bin/env python3
"""Evaluation Runner and Metrics Calibration Engine (T21).

Runs automated evaluation over the 120-sample test set (data/testset.jsonl),
computes confusion matrix, precision, recall, F1, FPR, and response latency (p50/p95),
and dumps misclassifications to eval_errors_YYYY-MM-DD.json for human calibration.

Hard Rules:
- NEVER fabricate numbers. All metrics MUST come from actual code execution.
- False positive minimization prioritized: precision >= 85%, recall >= 80%.
"""

import argparse
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import statistics
import sys
import time

# Ensure repository root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from lib.db import init_db
from lib.scoring import analyze_message
from lib.similarity import find_similar, load_watchlist

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("siaga.run_eval")

DEFAULT_TESTSET_PATH = BASE_DIR / "data" / "testset.jsonl"
DEFAULT_DB_PATH = BASE_DIR / "data" / "siaga.db"


def run_evaluation(
    testset_path: Path | str = DEFAULT_TESTSET_PATH,
    db_path: Path | str = DEFAULT_DB_PATH,
    out_prefix: str = "eval_results",
) -> dict:
    """Execute evaluation against test set and compute metrics."""
    testset_file = Path(testset_path)
    if not testset_file.exists():
        raise FileNotFoundError(f"Testset file not found at {testset_file}")

    resolved_db = Path(db_path)
    init_db(resolved_db)
    watchlist = load_watchlist()

    samples = []
    with open(testset_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))

    logger.info("Loaded %d evaluation samples from %s", len(samples), testset_file)

    tp, fp, tn, fn = 0, 0, 0, 0
    latencies_ms: list[float] = []
    errors: list[dict] = []
    detailed_results: list[dict] = []

    for idx, item in enumerate(samples, 1):
        item_id = item["id"]
        item_type = item["type"]
        content = item["content"]
        ground_truth = item["label"]  # "scam" | "legit"

        t_start = time.perf_counter()

        if item_type == "message":
            res = analyze_message(content, db_path=resolved_db)
            score = res.scoring.score
            level = res.scoring.level
            reasons = res.scoring.reasons
            # Classification threshold: score >= 40 (HATI-HATI or INDIKASI PENIPUAN) is flagged as scam
            predicted = "scam" if score >= 40 else "legit"
            breakdown = [{"signal": b.signal_name, "points": b.points} for b in res.scoring.breakdown]
        else:  # item_type == "domain"
            matches = find_similar(content, watchlist=watchlist)
            if matches:
                score = int(matches[0].similarity_score * 100)
                level = "INDIKASI PENIPUAN" if score >= 70 else "HATI-HATI"
                predicted = "scam"
                reasons = [f"Kemiripan domain dengan {matches[0].brand_name} ({matches[0].method})"]
                breakdown = [{"signal": matches[0].method, "points": score}]
            else:
                score = 0
                level = "AMAN"
                predicted = "legit"
                reasons = ["Domain resmi / tidak mencatut institusi."]
                breakdown = []

        elapsed_ms = (time.perf_counter() - t_start) * 1000.0
        latencies_ms.append(elapsed_ms)

        # Confusion Matrix
        is_correct = (predicted == ground_truth)
        if ground_truth == "scam":
            if predicted == "scam":
                tp += 1
            else:
                fn += 1
        else:  # ground_truth == "legit"
            if predicted == "legit":
                tn += 1
            else:
                fp += 1

        record = {
            "id": item_id,
            "type": item_type,
            "ground_truth": ground_truth,
            "predicted": predicted,
            "is_correct": is_correct,
            "score": score,
            "level": level,
            "reasons": reasons,
            "breakdown": breakdown,
            "latency_ms": round(elapsed_ms, 2),
            "content": content[:120] + "..." if len(content) > 120 else content,
        }
        detailed_results.append(record)

        if not is_correct:
            errors.append(record)

    # Compute Final Performance Metrics
    total = len(samples)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    accuracy = (tp + tn) / total if total > 0 else 0.0

    p50_latency = statistics.median(latencies_ms) if latencies_ms else 0.0
    p95_latency = statistics.quantiles(latencies_ms, n=20)[18] if len(latencies_ms) >= 20 else max(latencies_ms)

    metrics = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_samples": total,
        "confusion_matrix": {
            "true_positives": tp,
            "false_positives": fp,
            "true_negatives": tn,
            "false_negatives": fn,
        },
        "metrics": {
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "false_positive_rate": round(fpr, 4),
        },
        "latency_ms": {
            "p50": round(p50_latency, 2),
            "p95": round(p95_latency, 2),
            "min": round(min(latencies_ms), 2),
            "max": round(max(latencies_ms), 2),
        },
        "error_count": len(errors),
    }

    # Save Misclassification Dump
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    error_file = BASE_DIR / "data" / f"eval_errors_{today_str}.json"
    with open(error_file, "w", encoding="utf-8") as f:
        json.dump(errors, f, indent=2, ensure_ascii=False)

    # Save Output Summary
    results_file = BASE_DIR / "data" / f"{out_prefix}.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump({"summary": metrics, "errors": errors, "results": detailed_results}, f, indent=2, ensure_ascii=False)

    logger.info("Saved evaluation summary to %s", results_file)
    logger.info("Saved %d errors to %s", len(errors), error_file)

    return metrics


def print_metrics_table(m: dict) -> None:
    """Print formatted terminal report of evaluation results."""
    c = m["confusion_matrix"]
    met = m["metrics"]
    lat = m["latency_ms"]

    print("\n" + "=" * 65)
    print("      SIAGA PHISHING DETECTION EVALUATION REPORT (T21)")
    print("=" * 65)
    print(f"Total Samples Evaluated: {m['total_samples']}")
    print(f"Evaluation Timestamp   : {m['timestamp']}")
    print("-" * 65)
    print("CONFUSION MATRIX:")
    print(f"  True Positives (TP) : {c['true_positives']:>4}  (Scam correctly flagged)")
    print(f"  False Positives (FP): {c['false_positives']:>4}  (Legit mistakenly flagged)")
    print(f"  True Negatives (TN) : {c['true_negatives']:>4}  (Legit correctly cleared)")
    print(f"  False Negatives (FN): {c['false_negatives']:>4}  (Scam missed)")
    print("-" * 65)
    print("CALIBRATED PERFORMANCE METRICS:")
    print(f"  Accuracy            : {met['accuracy'] * 100:>6.2f}%")
    print(f"  Precision           : {met['precision'] * 100:>6.2f}%  (Target: >= 85.0%)")
    print(f"  Recall              : {met['recall'] * 100:>6.2f}%  (Target: >= 80.0%)")
    print(f"  F1 Score            : {met['f1_score']:>6.4f}  (Target: >= 0.820)")
    print(f"  False Positive Rate : {met['false_positive_rate'] * 100:>6.2f}%  (Target: <= 10.0%)")
    print("-" * 65)
    print("SYSTEM LATENCY PROFILE:")
    print(f"  p50 Latency         : {lat['p50']:>6.2f} ms")
    print(f"  p95 Latency         : {lat['p95']:>6.2f} ms")
    print(f"  Max Latency         : {lat['max']:>6.2f} ms")
    print("=" * 65 + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run SIAGA evaluation over 120-sample test set.")
    parser.add_argument(
        "--testset",
        type=Path,
        default=DEFAULT_TESTSET_PATH,
        help="Path to testset JSONL file",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to SQLite database",
    )
    parser.add_argument(
        "--out-prefix",
        type=str,
        default="eval_results",
        help="Prefix for output summary JSON",
    )
    args = parser.parse_args()

    metrics = run_evaluation(
        testset_path=args.testset,
        db_path=args.db,
        out_prefix=args.out_prefix,
    )
    print_metrics_table(metrics)
    return 0


if __name__ == "__main__":
    sys.exit(main())
