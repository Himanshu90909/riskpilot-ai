"""
RiskPilot AI — Public-Dataset Fraud Benchmark.

Validates the RiskPilot fraud-detection approach against a REAL, publicly
available fraud dataset (not synthetic) so evaluation results are grounded
in real-world class imbalance and feature noise.

Dataset: Kaggle "Credit Card Fraud Detection"
  https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud
  - 284,807 real European card transactions (Sept 2013)
  - 492 frauds (0.172% positive rate — genuine real-world imbalance)
  - Features: PCA-anonymized V1..V28 + Time + Amount

Usage:
  1. Download creditcard.csv from Kaggle (link above)
  2. Place it at ml/data/creditcard.csv
  3. Run:  python ml/benchmark_public.py

Outputs ml/public_benchmark.json with precision, recall, F1, PR-AUC,
confusion matrix, and timing. Real-data results are expected to be LOWER
than the synthetic benchmark — that gap is reported honestly, because
real-world fraud is far more imbalanced and noisier than simulation.
"""

import json
import os
import time
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data" / "creditcard.csv"
OUT_PATH = Path(__file__).parent / "public_benchmark.json"

TRAIN_FRACTION = 0.8
RANDOM_STATE = 42


def ensure_dataset() -> None:
    if DATA_PATH.exists():
        return
    print("=" * 70)
    print("REAL PUBLIC DATASET NOT FOUND")
    print("=" * 70)
    print(f"Expected dataset at: {DATA_PATH}")
    print()
    print("Download 'creditcard.csv' from Kaggle:")
    print("  https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud")
    print()
    print("Then place it at ml/data/creditcard.csv and rerun this script.")
    print("This keeps the ~150MB real dataset out of git while letting")
    print("reviewers reproduce the benchmark in under two minutes.")
    raise SystemExit(1)


def run_benchmark() -> dict:
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import (
        average_precision_score,
        confusion_matrix,
        f1_score,
        precision_recall_fscore_support,
        precision_score,
        recall_score,
    )
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler

    print("Loading real public fraud dataset (284,807 transactions)...")
    df = pd.read_csv(DATA_PATH)

    feature_cols = [c for c in df.columns if c not in ("Class", "Time")]
    X = df[feature_cols].values.astype("float64")
    y = df["Class"].values.astype(int)
    print(f"  Transactions: {len(df):,} | Fraud: {y.sum()} ({y.sum()/len(y)*100:.3f}%)")

    # Temporal split (dataset is time-ordered): train on first 80%, test on last 20%
    split = int(len(df) * TRAIN_FRACTION)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    print(f"  Train: {split:,} ({y_train.sum()} fraud) | Test: {len(df)-split:,} ({y_test.sum()} fraud)")

    scaler = StandardScaler().fit(X_train)
    X_train_s = scaler.transform(X_train)
    X_test_s = scaler.transform(X_test)

    results = {
        "dataset": {
            "name": "Kaggle Credit Card Fraud Detection (real transactions)",
            "source": "https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud",
            "total_transactions": int(len(df)),
            "total_fraud": int(y.sum()),
            "positive_rate": float(y.sum() / len(y)),
            "split": "temporal 80/20 (train first 80%, test last 20%)",
            "note": "REAL transaction data, PCA-anonymized features. Unlike the synthetic "
                    "benchmark, this reflects genuine class imbalance.",
        },
        "models": {},
    }

    for name, model in [
        ("logistic_regression", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=RANDOM_STATE)),
        ("gradient_boosting", GradientBoostingClassifier(random_state=RANDOM_STATE)),
    ]:
        print(f"\nTraining {name} on real data...")
        t0 = time.time()
        model.fit(X_train_s, y_train)
        train_time = time.time() - t0

        t0 = time.time()
        y_pred = model.predict(X_test_s)
        infer_time_ms = (time.time() - t0) / len(X_test) * 1000

        precision, recall, f1, _ = precision_recall_fscore_support(
            y_test, y_pred, average="binary", zero_division=0
        )
        tn, fp, fn, tp = confusion_matrix(y_test, y_pred, labels=[0, 1]).ravel()
        try:
            pr_auc = float(average_precision_score(y_test, model.predict_proba(X_test_s)[:, 1]))
        except AttributeError:
            pr_auc = None

        results["models"][name] = {
            "precision": round(float(precision), 4),
            "recall": round(float(recall), 4),
            "f1": round(float(f1), 4),
            "pr_auc": round(pr_auc, 4) if pr_auc else None,
            "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
            "train_seconds": round(train_time, 2),
            "inference_ms_per_txn": round(infer_time_ms, 4),
        }
        print(f"  Precision {precision*100:.2f}% | Recall {recall*100:.2f}% | F1 {f1*100:.2f}%"
              + (f" | PR-AUC {pr_auc:.4f}" if pr_auc else ""))
        print(f"  TP {tp} | FP {fp} | FN {fn} | TN {tn}")

    results["interpretation"] = (
        "Real-data metrics are expected to differ from the synthetic benchmark: real fraud "
        "is ~0.17% of transactions (vs ~5% in simulation), so precision/recall trade-offs are "
        "harsher. Both numbers are reported honestly — synthetic for reproducible demo "
        "scenarios, real-data for external validity of the detection approach."
    )

    OUT_PATH.write_text(json.dumps(results, indent=2))
    print(f"\nResults written to {OUT_PATH}")
    return results


if __name__ == "__main__":
    ensure_dataset()
    run_benchmark()
