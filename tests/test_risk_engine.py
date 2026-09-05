"""Risk engine tests: determinism, score bands, reasons, and closed-loop profile updates."""

from conftest import HIGH_RISK_TXN, LOW_RISK_TXN

from server.risk_engine import RiskEngine
from server.risk_profiles import RiskProfileStore


def make_engine() -> RiskEngine:
    return RiskEngine()


def test_engine_loads_or_falls_back():
    engine = make_engine()
    # Either ML model loaded or rule fallback active — both must be a valid version string
    assert engine.model_version in ("ml_model_v1.0", "rule_engine_v1.0")
    assert isinstance(engine.is_ml_loaded, bool)


def test_score_is_deterministic():
    engine = make_engine()
    r1 = engine.analyze_transaction(dict(HIGH_RISK_TXN))
    r2 = engine.analyze_transaction(dict(HIGH_RISK_TXN))
    assert r1["score"] == r2["score"], "Same input must always produce the same score"
    assert r1["decision"] == r2["decision"]


def test_score_bands():
    engine = make_engine()
    assert engine.classify_risk_score(0.0) == ("LOW", "approve")
    assert engine.classify_risk_score(15.0) == ("LOW", "approve")
    assert engine.classify_risk_score(30.0) == ("LOW", "approve")
    assert engine.classify_risk_score(31.0) == ("MEDIUM", "review")
    assert engine.classify_risk_score(60.0) == ("MEDIUM", "review")
    assert engine.classify_risk_score(61.0) == ("HIGH", "review")
    assert engine.classify_risk_score(80.0) == ("HIGH", "review")
    assert engine.classify_risk_score(81.0) == ("CRITICAL", "block")
    assert engine.classify_risk_score(100.0) == ("CRITICAL", "block")
    # out-of-range inputs are clipped
    assert engine.classify_risk_score(150.0)[0] == "CRITICAL"
    assert engine.classify_risk_score(-5.0)[0] == "LOW"


def test_high_risk_transaction_blocks():
    engine = make_engine()
    result = engine.analyze_transaction(dict(HIGH_RISK_TXN))
    assert 0.0 <= result["score"] <= 100.0
    # The canonical ATO scenario must be blocked by either ML or rule engine
    assert result["decision"] == "block"
    assert result["risk_level"] == "CRITICAL"
    reasons = " ".join(result["reasons"]).lower()
    assert "velocity" in reasons or "device" in reasons or "failure" in reasons


def test_low_risk_transaction_approves():
    engine = make_engine()
    result = engine.analyze_transaction(dict(LOW_RISK_TXN))
    assert result["decision"] == "approve"
    assert result["risk_level"] in ("LOW", "MEDIUM")


def test_reasons_explain_the_decision():
    engine = make_engine()
    result = engine.analyze_transaction(dict(HIGH_RISK_TXN))
    assert len(result["reasons"]) >= 1
    assert all(isinstance(r, str) and len(r) > 5 for r in result["reasons"])


def test_signal_features_engineered():
    from server.risk_engine import engineer_features
    df = engineer_features(dict(HIGH_RISK_TXN))
    assert df.shape == (1, 17), "Model expects exactly 17 engineered features"
    assert df["new_device"].iloc[0] in (0, 1)


def test_profile_store_closed_loop():
    store = RiskProfileStore()
    # Blocked decision raises customer risk and opens a case
    store.record_decision("txn_1", "CUS_A", "MERCH_A", 480000.0, "block", 94.0,
                          device_id="DEV_X", location="Mumbai", velocity_1h=12,
                          model_version="test")
    cust = store.get_customer_profile("CUS_A")
    assert cust["blocked_transactions"] == 1
    assert cust["total_transactions"] == 1
    assert cust["largest_transaction"] == 480000.0
    assert "txn_1" in cust["open_risk_cases"]
    assert cust["risk_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    merch = store.get_merchant_profile("MERCH_A")
    assert merch["blocked_transactions"] == 1
    assert merch["suspicious_transaction_percentage"] == 100.0

    # Approved decision decays risk; case stays open until an analyst closes it
    store.record_decision("txn_2", "CUS_A", "MERCH_A", 100.0, "approve", 8.0,
                          device_id="DEV_X", location="Mumbai", velocity_1h=1,
                          model_version="test")
    cust = store.get_customer_profile("CUS_A")
    assert cust["successful_transactions"] == 1
    assert "txn_1" in cust["open_risk_cases"], "Closed cases require explicit analyst action"

    # Webhook events feed the loop
    store.record_webhook_event("payment.failed", "pay_1", customer_id="CUS_A",
                               merchant_id="MERCH_A")
    cust = store.get_customer_profile("CUS_A")
    assert cust["failed_transactions"] == 1

    # Analyst closes the case
    assert store.close_risk_case("txn_1", "CUS_A") is True
    assert "txn_1" not in store.get_customer_profile("CUS_A")["open_risk_cases"]


def test_unknown_profile_is_none():
    store = RiskProfileStore()
    assert store.get_customer_profile("NOPE") is None
    assert store.get_merchant_profile("NOPE") is None
