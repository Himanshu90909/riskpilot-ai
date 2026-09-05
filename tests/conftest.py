"""RiskPilot AI test suite.

Run:  pytest tests/ -v
Covers: risk engine bands/determinism, webhook security (HMAC valid/invalid/
missing/duplicate/no-secret), agent investigation schema, API contract
(validation, override field preservation, profiles, mode status).
"""

import hashlib
import hmac
import json
import os
import sys
from pathlib import Path

# Ensure repo root is importable regardless of where pytest is invoked
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def make_webhook_payload(payment_id: str = "pay_test_abc123", amount: int = 48000000,
                         customer_id: str = "CUS_1029") -> str:
    """Build a Razorpay-shaped webhook payload (canonical JSON for signing)."""
    return json.dumps({
        "event": "payment.authorized",
        "payload": {"payment": {"entity": {
            "id": payment_id, "amount": amount, "currency": "INR",
            "status": "authorized", "created_at": 1690000000,
            "notes": {"customer_id": customer_id, "merchant_id": "MERCH_NOVA"},
        }}},
    }, sort_keys=True)


def sign(payload: str, secret: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


HIGH_RISK_TXN = {
    "amount": 480000.0, "customer_id": "CUS_TEST", "device_id": "DEV_TEST_NEW",
    "location": "Mumbai, IN", "velocity": 12, "failed_attempts": 5,
    "account_age_days": 2, "merchant_id": "MERCH_TEST", "merchant_risk_score": 65.0,
    "behavioral_deviation": 0.82,
}

LOW_RISK_TXN = {
    "amount": 250.0, "customer_id": "CUS_SAFE", "device_id": "DEV_KNOWN_1",
    "location": "Mumbai, IN", "velocity": 1, "failed_attempts": 0,
    "account_age_days": 1095, "merchant_id": "MERCH_TRUSTED", "merchant_risk_score": 5.0,
    "behavioral_deviation": 0.05,
}
