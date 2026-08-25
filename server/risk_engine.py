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
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger("risk_pilot.risk_engine")
logging.basicConfig(level=logging.INFO)


def _get_bool(txn: dict, *keys, default=False) -> bool:
    """Check multiple possible key names for a boolean field."""
    for key in keys:
        val = txn.get(key)
        if val is not None:
            return bool(val)
    return default


# Full feature list the ML model was trained on
ML_FEATURE_COLUMNS = [
    "amount", "amount_log", "amount_per_day", "new_device", "location_anomaly",
    "velocity", "failed_attempts", "velocity_failed_ratio", "account_age_days",
    "account_maturity_factor", "merchant_risk_score", "behavioral_deviation",
    "risk_flags_sum", "high_risk_interaction", "merchant_amount_interaction",
    "velocity_flag", "failed_attempts_flag",
]


def engineer_features(txn_data: Dict[str, Any]) -> pd.DataFrame:
    """
    Transform raw transaction dict into the 17 engineered features
    the Gradient Boosting model was trained on.
    """
    amount = float(txn_data.get("amount", 0.0))
    new_device = int(_get_bool(txn_data, "is_new_device", "new_device"))
    location_anomaly = int(_get_bool(txn_data, "is_location_anomaly", "location_anomaly"))
    velocity = float(txn_data.get("velocity_1h", txn_data.get("velocity", 0)))
    failed_attempts = int(txn_data.get("failed_attempts_24h", txn_data.get("failed_attempts", 0)))
    account_age_days = int(txn_data.get("account_age_days", 30))
    merchant_risk_score = float(txn_data.get("merchant_risk_score", 0.1))
    behavioral_deviation = float(txn_data.get("behavioral_deviation", 0.1))

    if behavioral_deviation > 1.0 and behavioral_deviation <= 100.0:
        behavioral_deviation = behavioral_deviation / 100.0
    behavioral_deviation = float(np.clip(behavioral_deviation, 0.0, 1.0))
    merchant_risk_score = float(np.clip(merchant_risk_score, 0.0, 1.0))

    amount_log = float(np.log1p(amount))
    amount_per_day = amount / max(account_age_days, 1)
    velocity_failed_ratio = velocity * (failed_attempts + 1.0)
    account_maturity_factor = 1.0 / (np.log1p(float(account_age_days)) + 1.0)
    risk_flags_sum = (
        new_device + location_anomaly +
        int(velocity > 4.0) + int(failed_attempts >= 2) +
        int(behavioral_deviation > 0.5)
    )
    high_risk_interaction = float(new_device) * float(location_anomaly) * behavioral_deviation
    merchant_amount_interaction = merchant_risk_score * amount_log
    velocity_flag = int(velocity > 5.0)
    failed_attempts_flag = int(failed_attempts >= 3)

    row = {
        "amount": amount,
        "amount_log": amount_log,
        "amount_per_day": amount_per_day,
        "new_device": new_device,
        "location_anomaly": location_anomaly,
        "velocity": velocity,
        "failed_attempts": failed_attempts,
        "velocity_failed_ratio": velocity_failed_ratio,
        "account_age_days": account_age_days,
        "account_maturity_factor": account_maturity_factor,
        "merchant_risk_score": merchant_risk_score,
        "behavioral_deviation": behavioral_deviation,
        "risk_flags_sum": risk_flags_sum,
        "high_risk_interaction": high_risk_interaction,
        "merchant_amount_interaction": merchant_amount_interaction,
        "velocity_flag": velocity_flag,
        "failed_attempts_flag": failed_attempts_flag,
    }

    df = pd.DataFrame([row], columns=ML_FEATURE_COLUMNS)
    return df


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
        self.scaler = None
        self.feature_columns = ML_FEATURE_COLUMNS
        self.model_version = "rule_engine_v1.0"
        self.decision_threshold = 0.3
        self.is_ml_loaded = False
        self._load_model(model_path)

    def _load_model(self, custom_path: Optional[str] = None) -> None:
        """Attempts to load scikit-learn model artifact from several candidate paths."""
        candidate_paths = []
        if custom_path:
            candidate_paths.append(custom_path)
        if os.environ.get("MODEL_PATH"):
            candidate_paths.append(os.environ.get("MODEL_PATH"))

        base_dir = os.path.dirname(os.path.abspath(__file__))

        candidate_paths.extend([
            "ml/model.pkl",
            "../ml/model.pkl",
            os.path.join(base_dir, "..", "ml", "model.pkl"),
            os.path.join(base_dir, "ml", "model.pkl"),
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
                        self.feature_columns = artifact.get("feature_columns", ML_FEATURE_COLUMNS)
                        self.model_version = artifact.get("model_version", "ml_model_v1.0")
                        self.decision_threshold = artifact.get("decision_threshold", 0.3)
                    else:
                        self.model = artifact
                        self.model_version = "ml_model_v1.0"

                    # Try to load scaler
                    scaler_path = abs_path.replace("model.pkl", "scaler.pkl")
                    if os.path.isfile(scaler_path):
                        self.scaler = joblib.load(scaler_path)

                    self.is_ml_loaded = True
                    logger.info(f"Successfully loaded ML model from {abs_path} (Version: {self.model_version})")
                    return
                except Exception as e:
                    logger.warning(f"Failed to load model from {abs_path}: {e}")

        logger.info("No valid ML model file found. Falling back to rule-based risk engine.")
        self.is_ml_loaded = False
        self.model_version = "rule_engine_v1.0"

    def classify_risk_score(self, score: float) -> Tuple[str, str]:
        """Classify numerical risk score into risk_level and decision."""
        score = float(np.clip(score, 0.0, 100.0))
        if score <= 30.0:
            return "LOW", "approve"
        elif score <= 60.0:
            return "MEDIUM", "review"
        elif score <= 80.0:
            return "HIGH", "review"
        else:
            return "CRITICAL", "block"

    def generate_reasons(self, features: Dict[str, Any], raw_txn: Optional[Dict[str, Any]] = None) -> List[str]:
        """Generate human-readable contributing risk factors based on feature signals."""
        reasons = []
        raw_txn = raw_txn or {}

        if _get_bool(raw_txn, "is_new_device", "new_device"):
            reasons.append("Transaction initiated from an unrecognized/new device.")

        if _get_bool(raw_txn, "is_location_anomaly", "location_anomaly"):
            reasons.append("Geographic anomaly: IP location deviates significantly from user history.")

        email = str(raw_txn.get("email", "")).lower()
        if any(email.endswith(f"@{domain}") for domain in self.DISPOSABLE_EMAIL_DOMAINS):
            reasons.append(f"Disposable email domain detected ({email}).")

        if _get_bool(raw_txn, "is_tor_or_vpn", "tor_or_vpn", "vpn"):
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
        """Rule-based risk scoring (0-100). Used as fallback when ML model is unavailable."""
        base_score = 5.0
        raw_txn = raw_txn or {}

        if _get_bool(raw_txn, "is_new_device", "new_device"):
            base_score += 25.0

        if _get_bool(raw_txn, "is_location_anomaly", "location_anomaly"):
            base_score += 30.0

        email = str(raw_txn.get("email", "")).lower()
        if any(email.endswith(f"@{domain}") for domain in self.DISPOSABLE_EMAIL_DOMAINS):
            base_score += 20.0

        if _get_bool(raw_txn, "is_tor_or_vpn", "tor_or_vpn", "vpn"):
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

    def _predict_ml(self, df_features: pd.DataFrame) -> float:
        """Use the trained ML model to predict fraud probability and convert to 0-100 risk score."""
        try:
            if self.scaler is not None:
                # Scaler may expect different feature names — use values
                try:
                    df_scaled = self.scaler.transform(df_features)
                except Exception:
                    df_scaled = self.scaler.transform(df_features.values)
            else:
                df_scaled = df_features

            proba = self.model.predict_proba(df_scaled)[0]
            fraud_prob = proba[1] if len(proba) > 1 else proba[0]
            risk_score = float(np.clip(fraud_prob * 100.0, 0.0, 100.0))
            return risk_score
        except Exception as e:
            logger.warning(f"ML prediction failed, falling back to rules: {e}")
            return -1.0

    def evaluate(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate a transaction and return a comprehensive risk assessment.
        Uses ML model if available, otherwise falls back to rule-based scoring.
        """
        # Build basic feature dict for reasons/rules
        amount = float(transaction_data.get("amount", 0.0))
        velocity = int(transaction_data.get("velocity_1h", transaction_data.get("velocity", 0)))
        failed_attempts = int(transaction_data.get("failed_attempts_24h", transaction_data.get("failed_attempts", 0)))
        account_age_days = int(transaction_data.get("account_age_days", 30))
        merchant_risk_score = float(transaction_data.get("merchant_risk_score", 0.0))
        behavioral_deviation = float(transaction_data.get("behavioral_deviation", 0.0))

        feature_dict = {
            "amount": amount,
            "velocity": velocity,
            "failed_attempts": failed_attempts,
            "account_age_days": account_age_days,
            "merchant_risk_score": merchant_risk_score,
            "behavioral_deviation": behavioral_deviation,
        }

        reasons = self.generate_reasons(feature_dict, raw_txn=transaction_data)

        # Use ML model if available, otherwise rules
        if self.is_ml_loaded and self.model is not None:
            df_features = engineer_features(transaction_data)
            ml_score = self._predict_ml(df_features)
            if ml_score >= 0:
                score = ml_score
            else:
                score = self.evaluate_rules(feature_dict, raw_txn=transaction_data)
        else:
            score = self.evaluate_rules(feature_dict, raw_txn=transaction_data)

        risk_level, decision = self.classify_risk_score(score)

        return {
            "score": round(score, 1),
            "decision": decision,
            "risk_level": risk_level,
            "reasons": reasons,
            "model_version": self.model_version,
            "evaluated_signals": {
                "new_device": _get_bool(transaction_data, "is_new_device", "new_device"),
                "velocity_1h": velocity,
                "location_anomaly": _get_bool(transaction_data, "is_location_anomaly", "location_anomaly"),
                "amount_rupees": amount,
                "failed_attempts": failed_attempts,
                "account_age_days": account_age_days,
                "merchant_risk_score": merchant_risk_score,
                "behavioral_deviation": behavioral_deviation,
            }
        }

    def evaluate_payment_failure(self, payment_data: Dict[str, Any], failure_reason: Optional[str] = None) -> Dict[str, Any]:
        """Analyze a failed payment event to classify if it was fraud-related."""
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
        """Alias method for analyzing transaction data."""
        return self.evaluate(txn_data)
