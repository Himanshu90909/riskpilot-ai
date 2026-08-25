"""
Risk Engine for RiskPilot AI.
Loads scikit-learn ML model from artifact or falls back to rule-based risk scoring.
Implements transparent score bands:
  0-30   LOW      -> approve
  31-60  MEDIUM   -> review
  61-80  HIGH     -> review
  81-100 CRITICAL -> block
"""

import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

logger = logging.getLogger("risk_pilot.risk_engine")
logging.basicConfig(level=logging.INFO)


class RiskEngine:
    """
    Core risk evaluation engine using ML model scoring with rule-based fallback.
    """

    DISPOSABLE_EMAIL_DOMAINS = {
        "tempmail.com", "guerrillamail.com", "10minutemail.com",
        "throwawaymail.com", "mailinator.com", "trashmail.com"
    }

    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.feature_names = [
            "amount",
            "velocity",
            "failed_attempts",
            "account_age_days",
            "merchant_risk_score",
            "behavioral_deviation",
        ]
        self.model_version = "rule_engine_v1.0"
        self.is_ml_loaded = False
        self._load_model(model_path)

    def _load_model(self, custom_path: Optional[str] = None) -> None:
        """
        Attempts to load scikit-learn model artifact from several candidate paths.
        """
        candidate_paths = []
        if custom_path:
            candidate_paths.append(custom_path)
        if os.environ.get("MODEL_PATH"):
            candidate_paths.append(os.environ.get("MODEL_PATH"))

        candidate_paths.extend([
            "ml/model.pkl",
            "../ml/model.pkl",
            "server/ml/model.pkl",
            os.path.join(os.path.dirname(__file__), "..", "ml", "model.pkl"),
            os.path.join(os.path.dirname(__file__), "ml", "model.pkl"),
        ])

        for path in candidate_paths:
            if not path:
                continue
            abs_path = os.path.abspath(path)
            if os.path.isfile(abs_path):
                try:
                    import joblib

                    artifact = joblib.load(abs_path)
                    if isinstance(artifact, dict) and "model" in artifact:
                        self.model = artifact["model"]
                        self.feature_names = artifact.get("feature_names", self.feature_names)
                        self.model_version = artifact.get("model_version", "ml_model_v1.0")
                    else:
                        self.model = artifact
                        self.model_version = "ml_model_v1.0"

                    self.is_ml_loaded = True
                    logger.info(f"Successfully loaded ML model from {abs_path} (Version: {self.model_version})")
                    return
                except Exception as e:
                    logger.warning(f"Failed to load model from {abs_path}: {e}")

        logger.info("No valid ML model file found. Falling back to rule-based risk engine.")
        self.is_ml_loaded = False
        self.model_version = "rule_engine_v1.0"

    def classify_risk_score(self, score: float) -> Tuple[str, str]:
        """
        Classify numerical risk score into risk_level and decision.
        """
        score = float(np.clip(score, 0.0, 100.0))
        if score <= 30.0:
            return "LOW", "approve"
        elif score <= 60.0:
            return "MEDIUM", "review"
        elif score <= 80.0:
            return "HIGH", "review"
        else:
            return "CRITICAL", "block"

    def extract_features(self, txn_data: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Extract numeric feature vector for ML model and parsed parameters.
        """
        # Convert amount_paise to Rupee float if present
        amount_paise = txn_data.get("amount_paise")
        if amount_paise is not None:
            amount = float(amount_paise) / 100.0
        else:
            amount = float(txn_data.get("amount", 0.0))

        velocity = int(txn_data.get("velocity_1h", txn_data.get("velocity", 0)))
        failed_attempts = int(txn_data.get("failed_attempts_24h", txn_data.get("failed_attempts", 0)))
        account_age_days = int(txn_data.get("account_age_days", 30))
        merchant_risk_score = float(txn_data.get("merchant_risk_score", 0.0))
        behavioral_deviation = float(txn_data.get("behavioral_deviation", 0.0))

        if behavioral_deviation > 1.0 and behavioral_deviation <= 100.0:
            behavioral_deviation = behavioral_deviation / 100.0
        behavioral_deviation = float(np.clip(behavioral_deviation, 0.0, 1.0))
        merchant_risk_score = float(np.clip(merchant_risk_score, 0.0, 100.0))

        feature_dict = {
            "amount": amount,
            "velocity": velocity,
            "failed_attempts": failed_attempts,
            "account_age_days": account_age_days,
            "merchant_risk_score": merchant_risk_score,
            "behavioral_deviation": behavioral_deviation,
        }

        df = pd.DataFrame([feature_dict])[self.feature_names]
        return df, feature_dict

    def generate_reasons(self, features: Dict[str, Any], raw_txn: Optional[Dict[str, Any]] = None) -> List[str]:
        """
        Generate human-readable contributing risk factors based on feature signals.
        """
        reasons = []
        raw_txn = raw_txn or {}

        if raw_txn.get("is_new_device", False):
            reasons.append("Transaction initiated from an unrecognized/new device.")

        if raw_txn.get("is_location_anomaly", False):
            reasons.append("Geographic anomaly: IP location deviates significantly from user history.")

        email = str(raw_txn.get("email", "")).lower()
        if any(email.endswith(f"@{domain}") for domain in self.DISPOSABLE_EMAIL_DOMAINS):
            reasons.append(f"Disposable email domain detected ({email}).")

        if raw_txn.get("is_tor_or_vpn", False):
            reasons.append("VPN / Anonymizing proxy connection detected.")

        amount = features["amount"]
        velocity = features["velocity"]
        failed_attempts = features["failed_attempts"]

        if amount >= 50000.0:
            reasons.append(f"High-value transaction amount (₹{amount:,.2f})")

        if velocity >= 10:
            reasons.append(f"Severe velocity spike ({velocity} attempts in past hour)")
        elif velocity >= 4:
            reasons.append(f"Elevated velocity ({velocity} attempts in past hour)")

        if failed_attempts >= 3:
            reasons.append(f"Multiple recent payment failures ({failed_attempts} in 24h)")

        if not reasons:
            reasons.append("Standard transaction profile with low risk indicators.")

        return reasons

    def evaluate_rules(self, features: Dict[str, Any], raw_txn: Optional[Dict[str, Any]] = None) -> float:
        """
        Rule-based risk scoring (0-100).
        """
        base_score = 5.0
        raw_txn = raw_txn or {}

        if raw_txn.get("is_new_device", False):
            base_score += 25.0

        if raw_txn.get("is_location_anomaly", False):
            base_score += 30.0

        email = str(raw_txn.get("email", "")).lower()
        if any(email.endswith(f"@{domain}") for domain in self.DISPOSABLE_EMAIL_DOMAINS):
            base_score += 20.0

        if raw_txn.get("is_tor_or_vpn", False):
            base_score += 20.0

        amount = features["amount"]
        velocity = features["velocity"]
        failed_attempts = features["failed_attempts"]

        if amount >= 50000.0:
            base_score += 15.0

        if velocity >= 10:
            base_score += 40.0
        elif velocity >= 5:
            base_score += 25.0
        elif velocity >= 3:
            base_score += 15.0

        if failed_attempts >= 3:
            base_score += 25.0

        return float(np.clip(base_score, 0.0, 100.0))

    def evaluate(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a transaction and return a comprehensive risk assessment.

        :param transaction_data: Transaction details.
        :return: Dict containing score, decision, risk_level, and reasons.
        """
        df_features, feature_dict = self.extract_features(transaction_data)
        reasons = self.generate_reasons(feature_dict, raw_txn=transaction_data)
        score = self.evaluate_rules(feature_dict, raw_txn=transaction_data)

        risk_level, decision = self.classify_risk_score(score)

        return {
            "score": round(score, 1),
            "decision": decision,
            "risk_level": risk_level,
            "reasons": reasons,
            "evaluated_signals": {
                "new_device": transaction_data.get("is_new_device", False),
                "velocity_1h": feature_dict["velocity"],
                "location_anomaly": transaction_data.get("is_location_anomaly", False),
                "amount_rupees": feature_dict["amount"],
            }
        }

    def evaluate_payment_failure(self, payment_data: Dict[str, Any], failure_reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze a failed payment event to classify if it was fraud-related.
        """
        score = 0.0
        reasons: List[str] = []

        raw_reason = failure_reason or payment_data.get("error_description") or payment_data.get("error_code") or ""
        raw_reason_str = str(raw_reason).lower()

        notes = payment_data.get("notes", {}) or {}
        if not isinstance(notes, dict):
            notes = {}

        if any(kw in raw_reason_str for kw in ["stolen", "lost_card", "fraud", "card_blocked", "security_violation"]):
            score += 90.0
            reasons.append("Payment processor reported security/fraud violation code.")
            action = "block"
        elif any(kw in raw_reason_str for kw in ["incorrect_otp", "max_attempts_exceeded", "invalid_cvv", "authentication_failed"]):
            score += 65.0
            reasons.append("Repeated authentication or CVV failure pattern detected.")
            action = "escalate" if score >= 70 else "contact_customer"
        elif any(kw in raw_reason_str for kw in ["insufficient_funds", "user_cancelled", "expired"]):
            score += 15.0
            reasons.append("Standard non-fraud issue (insufficient funds / user cancellation / expiration).")
            action = "retry"
        else:
            score += 45.0
            reasons.append(f"Payment failure recorded: {raw_reason or 'Unknown error'}.")
            action = "contact_customer"

        if notes.get("risk_flag") == "manual_review_required":
            score += 20.0
            reasons.append("Payment had prior manual review flag.")

        score = min(score, 100.0)
        if action != "block" and score >= 75.0:
            action = "escalate"

        return {
            "is_fraud_suspected": score >= 50.0,
            "fraud_risk_score": round(score, 1),
            "reasons": reasons,
            "recommended_action": action,
            "payment_id": payment_data.get("id"),
            "amount": payment_data.get("amount"),
        }

    def analyze_transaction(self, txn_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Alias method for analyzing transaction data.
        """
        return self.evaluate(txn_data)
