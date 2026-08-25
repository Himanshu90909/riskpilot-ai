"""
RiskPilot AI - Single Transaction Fraud Predictor & Inference Module
Provides realtime fraud prediction, risk scoring (0-100), confidence level, feature importances,
and automatic rule-based fallback if ML model artifacts are missing.
"""

import os
import joblib
import numpy as np
import pandas as pd

# Path resolution for model artifacts
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODEL_PATH = os.path.join(BASE_DIR, 'model.pkl')
DEFAULT_SCALER_PATH = os.path.join(BASE_DIR, 'scaler.pkl')

_MODEL = None
_SCALER = None
_FEATURE_COLUMNS = None
_THRESHOLD = 0.30
_MODEL_LOADED = False

DEFAULT_FEATURE_COLUMNS = [
    'amount', 'amount_log', 'amount_per_day', 'new_device', 'location_anomaly',
    'velocity', 'failed_attempts', 'velocity_failed_ratio', 'account_age_days',
    'account_maturity_factor', 'merchant_risk_score', 'behavioral_deviation',
    'risk_flags_sum', 'high_risk_interaction', 'merchant_amount_interaction',
    'velocity_flag', 'failed_attempts_flag'
]


def engineer_single_features(tx_dict):
    """
    Transforms a single raw transaction dictionary into engineered DataFrame features.
    
    Args:
        tx_dict (dict): Raw transaction fields.
        
    Returns:
        pd.DataFrame: Engineered feature DataFrame matching model training columns.
    """
    df = pd.DataFrame([tx_dict])

    defaults = {
        'amount': 1000.0,
        'new_device': 0,
        'location_anomaly': 0,
        'velocity': 1.0,
        'failed_attempts': 0,
        'account_age_days': 30,
        'merchant_risk_score': 0.1,
        'behavioral_deviation': 0.1
    }
    for key, val in defaults.items():
        if key not in df.columns or pd.isna(df.loc[0, key]):
            df[key] = val

    df['new_device'] = df['new_device'].astype(int)
    df['location_anomaly'] = df['location_anomaly'].astype(int)

    df['amount_per_day'] = df['amount'].astype(float) / np.maximum(df['account_age_days'].astype(float), 1.0)
    df['amount_log'] = np.log1p(df['amount'].astype(float))
    df['velocity_failed_ratio'] = df['velocity'].astype(float) * (df['failed_attempts'].astype(float) + 1.0)
    df['account_maturity_factor'] = 1.0 / (np.log1p(df['account_age_days'].astype(float)) + 1.0)

    df['risk_flags_sum'] = (
        df['new_device'] +
        df['location_anomaly'] +
        (df['velocity'] > 4.0).astype(int) +
        (df['failed_attempts'] >= 2).astype(int) +
        (df['behavioral_deviation'] > 0.5).astype(int)
    )

    df['high_risk_interaction'] = (
        df['new_device'].astype(float) *
        df['location_anomaly'].astype(float) *
        df['behavioral_deviation'].astype(float)
    )

    df['merchant_amount_interaction'] = df['merchant_risk_score'].astype(float) * df['amount_log']
    df['velocity_flag'] = (df['velocity'] > 5.0).astype(int)
    df['failed_attempts_flag'] = (df['failed_attempts'] >= 3).astype(int)

    return df[DEFAULT_FEATURE_COLUMNS]


def load_model(model_path=None, scaler_path=None):
    """
    Loads model.pkl and scaler.pkl into global memory.
    
    Returns:
        bool: True if model loaded successfully, False otherwise.
    """
    global _MODEL, _SCALER, _FEATURE_COLUMNS, _THRESHOLD, _MODEL_LOADED

    m_path = model_path or DEFAULT_MODEL_PATH
    s_path = scaler_path or DEFAULT_SCALER_PATH

    # Search fallback paths if not found directly
    candidate_m_paths = [m_path, 'ml/model.pkl', 'model.pkl']
    candidate_s_paths = [s_path, 'ml/scaler.pkl', 'scaler.pkl']

    found_m = next((p for p in candidate_m_paths if os.path.exists(p)), None)
    found_s = next((p for p in candidate_s_paths if os.path.exists(p)), None)

    if found_m and found_s:
        try:
            artifact = joblib.load(found_m)
            _SCALER = joblib.load(found_s)

            if isinstance(artifact, dict) and 'model' in artifact:
                _MODEL = artifact['model']
                _FEATURE_COLUMNS = artifact.get('feature_columns', DEFAULT_FEATURE_COLUMNS)
                _THRESHOLD = artifact.get('decision_threshold', 0.30)
            else:
                _MODEL = artifact
                _FEATURE_COLUMNS = DEFAULT_FEATURE_COLUMNS
                _THRESHOLD = 0.30

            _MODEL_LOADED = True
            return True
        except Exception as e:
            print(f"[RiskPilot ML Warning] Model loading failed ({e}). Falling back to rule engine.")
            _MODEL_LOADED = False
            return False
    else:
        _MODEL_LOADED = False
        return False


def rule_based_predict(tx_dict):
    """
    Rule-based scoring engine for fallback when model files are not available.
    """
    score = 5.0  # Base risk level
    amount = float(tx_dict.get('amount', 0))
    new_dev = bool(tx_dict.get('new_device', False))
    loc_anom = bool(tx_dict.get('location_anomaly', False))
    vel = float(tx_dict.get('velocity', 0))
    failed = int(tx_dict.get('failed_attempts', 0))
    age = int(tx_dict.get('account_age_days', 100))
    merch_risk = float(tx_dict.get('merchant_risk_score', 0))
    beh_dev = float(tx_dict.get('behavioral_deviation', 0))

    if new_dev:
        score += 22.0
    if loc_anom:
        score += 25.0
    if vel > 5.0:
        score += min(30.0, vel * 1.5)
    if failed >= 3:
        score += min(25.0, failed * 5.0)
    if age < 7:
        score += 15.0
    if amount > 50000:
        score += 12.0
    score += beh_dev * 25.0
    score += merch_risk * 18.0

    risk_score = round(float(np.clip(score, 0.0, 100.0)), 2)
    is_fraud = risk_score >= 50.0
    confidence = 0.80

    top_features = []
    if loc_anom:
        top_features.append({"feature": "location_anomaly", "importance": 0.25})
    if new_dev:
        top_features.append({"feature": "new_device", "importance": 0.22})
    if vel > 5.0:
        top_features.append({"feature": "velocity", "importance": 0.20})
    if failed >= 3:
        top_features.append({"feature": "failed_attempts", "importance": 0.18})
    if age < 7:
        top_features.append({"feature": "account_age_days", "importance": 0.15})

    if not top_features:
        top_features.append({"feature": "normal_behavioral_baseline", "importance": 0.90})

    return {
        "risk_score": risk_score,
        "is_fraud": is_fraud,
        "confidence": confidence,
        "mode": "rule_based_fallback",
        "top_features": top_features
    }


def predict_single(tx_dict):
    """
    Takes a transaction dictionary and predicts fraud risk score (0-100), label, and confidence.
    
    Args:
        tx_dict (dict): Raw transaction inputs.
        
    Returns:
        dict: Prediction results including risk_score, is_fraud, confidence, mode, and top_features.
    """
    global _MODEL_LOADED, _MODEL, _SCALER, _THRESHOLD

    if not _MODEL_LOADED or _MODEL is None or _SCALER is None:
        if not load_model():
            return rule_based_predict(tx_dict)

    try:
        X_df = engineer_single_features(tx_dict)
        X_scaled = _SCALER.transform(X_df)
        probas = _MODEL.predict_proba(X_scaled)[0]
        p_fraud = probas[1]

        risk_score = round(float(p_fraud * 100.0), 2)
        is_fraud = bool(p_fraud >= _THRESHOLD)
        confidence = round(float(max(p_fraud, 1.0 - p_fraud)), 4)

        top_features = get_feature_importance(tx_dict)

        return {
            "risk_score": risk_score,
            "is_fraud": is_fraud,
            "confidence": confidence,
            "mode": "ml_gradient_boosting",
            "fraud_probability": round(float(p_fraud), 4),
            "top_features": top_features
        }
    except Exception as e:
        print(f"[RiskPilot ML Error] Single prediction failed ({e}). Using rule fallback.")
        return rule_based_predict(tx_dict)


def get_feature_importance(tx_dict=None, top_n=5):
    """
    Returns global top feature importances from trained model or local driver importances.
    
    Args:
        tx_dict (dict, optional): Specific transaction context.
        top_n (int): Number of top features to return.
        
    Returns:
        list of dicts: List of {"feature": name, "importance": score}.
    """
    global _MODEL_LOADED, _MODEL, _FEATURE_COLUMNS

    if not _MODEL_LOADED or _MODEL is None:
        load_model()

    if _MODEL_LOADED and hasattr(_MODEL, 'feature_importances_'):
        feat_names = _FEATURE_COLUMNS or DEFAULT_FEATURE_COLUMNS
        importances = _MODEL.feature_importances_
        sorted_pairs = sorted(zip(feat_names, importances), key=lambda x: x[1], reverse=True)
        return [{"feature": name, "importance": round(float(imp), 4)} for name, imp in sorted_pairs[:top_n]]

    return [
        {"feature": "location_anomaly", "importance": 0.22},
        {"feature": "new_device", "importance": 0.19},
        {"feature": "velocity", "importance": 0.18},
        {"feature": "failed_attempts", "importance": 0.15},
        {"feature": "behavioral_deviation", "importance": 0.14}
    ]


if __name__ == '__main__':
    # Test sample legit transaction
    legit_tx = {
        'customer_id': 'CUST_10001',
        'device_id': 'DEV_10001',
        'amount': 1500.0,
        'new_device': 0,
        'location_anomaly': 0,
        'velocity': 1.2,
        'failed_attempts': 0,
        'account_age_days': 350,
        'merchant_risk_score': 0.12,
        'behavioral_deviation': 0.08
    }

    # Test sample fraud transaction (Account Takeover)
    fraud_tx = {
        'customer_id': 'CUST_99999',
        'device_id': 'DEV_99999',
        'amount': 45000.0,
        'new_device': 1,
        'location_anomaly': 1,
        'velocity': 12.5,
        'failed_attempts': 2,
        'account_age_days': 4,
        'merchant_risk_score': 0.85,
        'behavioral_deviation': 0.92
    }

    print("Testing ML Predictor module...")
    load_model()

    res_legit = predict_single(legit_tx)
    res_fraud = predict_single(fraud_tx)

    print("\n--- Legit Transaction Prediction ---")
    print(res_legit)

    print("\n--- Fraud Transaction Prediction ---")
    print(res_fraud)

    print("\n--- Top Model Feature Importances ---")
    print(get_feature_importance())
