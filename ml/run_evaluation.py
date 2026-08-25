#!/usr/bin/env python3
"""
Reproducible evaluation pipeline for RiskPilot AI.
Runs the full cycle: generate data → train model → evaluate → save results.

Usage:
    python ml/run_evaluation.py
"""

import json
import subprocess
import sys
from pathlib import Path

def main():
    print("=" * 60)
    print("  RiskPilot AI — Reproducible Evaluation Pipeline")
    print("  Track 02: AI Risk Manager — Razorpay Buildathon")
    print("=" * 60)
    print()

    # Step 1: Generate synthetic data
    print("[1/3] Generating synthetic transaction data...")
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "generate_data.py")],
        capture_output=False
    )
    if result.returncode != 0:
        print("✗ Data generation failed!")
        sys.exit(1)
    print("✓ Data generated: ml/data/train.csv, ml/data/test.csv")
    print()

    # Step 2: Train model
    print("[2/3] Training fraud detection model...")
    result = subprocess.run(
        [sys.executable, str(Path(__file__).parent / "train_model.py")],
        capture_output=False
    )
    if result.returncode != 0:
        print("✗ Model training failed!")
        sys.exit(1)
    print("✓ Model trained: ml/model.pkl, ml/scaler.pkl")
    print()

    # Step 3: Load and display results
    print("[3/3] Loading evaluation results...")
    results_path = Path(__file__).parent / "results.json"
    with open(results_path) as f:
        results = json.load(f)

    print()
    print("=" * 60)
    print("  EVALUATION RESULTS (Held-out test set, n=20,000)")
    print("=" * 60)
    print()

    gb = results["gradient_boosting"]
    print(f"  Primary Model: Gradient Boosting Classifier")
    print(f"  Decision Threshold: {gb['decision_threshold']}")
    print()
    print(f"  Precision:     {gb['precision']:.4f}  ({gb['precision']*100:.2f}%)")
    print(f"  Recall:        {gb['recall']:.4f}  ({gb['recall']*100:.2f}%)")
    print(f"  F1 Score:      {gb['f1']:.4f}  ({gb['f1']*100:.2f}%)")
    print(f"  FPR:           {gb['fpr']:.6f}  ({gb['fpr']*100:.4f}%)")
    print(f"  FP Cost:       ₹{gb['fp_cost']:,.0f}")
    print()
    cm = gb["confusion_matrix"]
    print(f"  Confusion Matrix:")
    print(f"    True Positives:   {cm['tp']:>6}")
    print(f"    True Negatives:   {cm['tn']:>6}")
    print(f"    False Positives:  {cm['fp']:>6}")
    print(f"    False Negatives:  {cm['fn']:>6}")
    print()

    if "logistic_regression" in results:
        lr = results["logistic_regression"]
        print(f"  Comparison: Logistic Regression")
        print(f"    Precision: {lr['precision']:.4f} | Recall: {lr['recall']:.4f} | F1: {lr['f1']:.4f}")
        print(f"    FPR: {lr['fpr']:.6f} | FP Cost: ₹{lr['fp_cost']:,.0f}")
        print()

    print("=" * 60)
    print("  ✅ Evaluation complete. Results saved to ml/results.json")
    print("  ⚠️  All data is synthetic. Not a production fraud estimate.")
    print("=" * 60)


if __name__ == "__main__":
    main()
