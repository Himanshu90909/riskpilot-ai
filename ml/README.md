# RiskPilot AI — ML Model Training Pipeline

## Overview

This module trains a fraud detection model on synthetic payment transaction data. The model predicts whether a transaction is fraudulent based on features like transaction amount, device state, location, velocity, failed attempts, account age, and merchant risk.

## Architecture

- **Data Generation**: `generate_data.py` creates 100,000 synthetic transactions (80K train / 20K held-out test) with 4 fraud patterns
- **Model Training**: `train_model.py` trains both a Logistic Regression (baseline) and Gradient Boosting Classifier (primary)
- **Inference**: `predict.py` provides a clean API for loading the model and making predictions
- **Evaluation**: `run_evaluation.py` runs the full pipeline end-to-end

## Fraud Patterns Simulated

1. **Account Takeover** — new device, location anomaly, high velocity, short account age
2. **Card Testing** — many failed attempts, moderate amount, high velocity
3. **Velocity Attack** — extremely high velocity, multiple failed attempts
4. **Friendly Fraud** — long account age, normal device, high amount, low merchant risk

## Results (Held-out Test Set, n=20,000)

| Metric | Gradient Boosting | Logistic Regression |
|---|---|---|
| Precision | 90.82% | 86.76% |
| Recall | 89.08% | 89.44% |
| F1 Score | 89.94% | 88.08% |
| FPR | 0.52% | 0.79% |
| FP Cost | ₹49,500 | ₹75,000 |

## Usage

```bash
# Full pipeline: generate → train → evaluate
python ml/run_evaluation.py

# Or run individual steps
python ml/generate_data.py    # Generate synthetic data
python ml/train_model.py       # Train and evaluate models
```

## Inference (used by the backend)

```python
from ml.predict import load_model, predict_single

model, scaler = load_model()
result = predict_single({
    "amount": 45000,
    "new_device": True,
    "location_anomaly": True,
    "velocity": 8,
    "failed_attempts": 0,
    "account_age_days": 1095,
    "merchant_risk_score": 0.2,
    "behavioral_deviation": 0.8
})
# result = {"risk_score": 85, "is_fraud": True, "confidence": 0.87}
```

## Defense-Only

This model is strictly defense-only. It detects fraud; it does not facilitate it. Any offense-capable use is explicitly disallowed per the Razorpay Buildathon Track 02 rules.

## Disclaimer

All data is synthetic. Metrics are not production fraud estimates. The model is trained on deterministic synthetic data for hackathon demonstration purposes.

## Public-Dataset Benchmark (Real Data)

`benchmark_public.py` validates the detection approach against the **Kaggle Credit Card Fraud Detection** dataset — 284,807 real card transactions with a 0.172% fraud rate. Unlike the synthetic data above, this measures real-world class imbalance.

```bash
# 1. Download creditcard.csv from https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud
# 2. Place it at ml/data/creditcard.csv
python ml/benchmark_public.py
# → writes ml/public_benchmark.json
```

Real-data metrics are reported honestly alongside synthetic ones: the synthetic set powers reproducible demo scenarios; the public set provides external validity.
