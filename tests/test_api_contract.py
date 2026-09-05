"""API contract tests: health, validation, risk analyze, override field preservation, profiles, mode status."""

import pytest

fastapi_testclient = pytest.importorskip("fastapi.testclient")

from conftest import HIGH_RISK_TXN, LOW_RISK_TXN

from fastapi.testclient import TestClient

from server.main import app

client = TestClient(app)


def test_health():
    r = client.get("/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "model_version" in body


def test_integrations_status_reports_mode_honestly():
    r = client.get("/v1/integrations/status")
    assert r.status_code == 200
    body = r.json()
    assert body["mode"]["execution_mode"] in ("DEMO_MODE", "TEST_MODE_PARTIAL", "RAZORPAY_TEST_MODE")
    assert body["webhook"]["idempotency"] is True
    assert body["agent"]["score_source"] == "deterministic_ml_engine"


def test_risk_analyze_happy_path():
    r = client.post("/v1/risk/analyze", json=HIGH_RISK_TXN)
    assert r.status_code == 200
    body = r.json()
    for key in ("transaction_id", "risk_score", "risk_level", "decision", "reasons",
                "model_version", "timestamp", "latency_ms",
                "risk_factors", "evidence", "recommended_action",
                "ai_recommendation", "policy_version", "governance"):
        assert key in body, f"Missing required contract field: {key}"
    assert 0.0 <= body["risk_score"] <= 100.0
    assert body["decision"] in ("approve", "review", "step_up", "block")
    assert isinstance(body["evidence"], list) and len(body["evidence"]) >= 1
    assert body["governance"]["policy_version"] == body["policy_version"]
    assert body["governance"]["final_decision"] == body["decision"]
    assert body["latency_ms"] >= 0.0


def test_risk_analyze_rejects_invalid_input():
    bad = {**HIGH_RISK_TXN, "amount": -100.0}          # negative amount
    r = client.post("/v1/risk/analyze", json=bad)
    assert r.status_code == 422
    bad2 = {**HIGH_RISK_TXN, "behavioral_deviation": 5.0}  # out of 0-1 range
    r2 = client.post("/v1/risk/analyze", json=bad2)
    assert r2.status_code == 422


def test_governance_layer_decides_not_the_engine():
    """Requirement 3: AI recommends; governance decides. HIGH band must yield step_up
    even when the engine recommended 'review' — the two must be independently recorded."""
    from server.governance import apply_governance, governed_assessment

    # Unit: HIGH band with engine 'review' recommendation → governance raises to step_up
    engine_assessment = {"risk_score": 72.0, "risk_level": "high", "decision": "review",
                         "reasons": ["velocity"], "model_version": "ml_model_v1.0"}
    governed = apply_governance(engine_assessment)
    assert governed["ai_recommendation"] == "review"
    assert governed["final_decision"] == "step_up"
    assert governed["ai_recommendation_differs"] is True
    assert governed["step_up_required"] is True
    assert governed["human_review_required"] is True

    # Band mapping for all four decisions
    assert apply_governance({"risk_level": "low", "decision": "approve"})["final_decision"] == "approve"
    assert apply_governance({"risk_level": "medium", "decision": "review"})["final_decision"] == "review"
    assert apply_governance({"risk_level": "high", "decision": "review"})["final_decision"] == "step_up"
    assert apply_governance({"risk_level": "critical", "decision": "block"})["final_decision"] == "block"

    # governed_assessment surfaces the split without losing the engine's view
    result = governed_assessment(engine_assessment)
    assert result["ai_recommendation"] == "review"
    assert result["decision"] == "step_up"
    assert result["recommended_action"] == "create_order_with_step_up_verification"
    assert result["policy_version"] == "gov_policy_v1.0"
    assert result["governance"]["final_decision"] == "step_up"


def test_override_preserves_policy_version_in_audit():
    """Requirement 4: audit record must carry model_version AND policy_version."""
    r = client.post("/v1/risk/analyze", json=HIGH_RISK_TXN)
    txn_id = r.json()["transaction_id"]
    r2 = client.get("/v1/audit/recent")
    entry = {e["transaction_id"]: e for e in r2.json()["entries"]}[txn_id]
    assert entry["policy_version"] == "gov_policy_v1.0"
    assert entry["model_version"]  # model version preserved from decision time


def test_investigation_run_endpoint():
    r = client.post("/v1/investigations/run", json=HIGH_RISK_TXN)
    assert r.status_code == 200
    body = r.json()
    assert len(body["steps"]) >= 8
    assert body["risk_assessment"]["score_source"] == "deterministic_ml_engine"


def test_judge_run_closed_loop():
    r = client.post("/v1/investigations/judge-run", json={})
    assert r.status_code == 200
    body = r.json()
    names = [t["name"] for t in body["timeline"]]
    expected_flow = [
        "transaction_received", "risk_engine", "agent_investigation", "governance_policy",
        "razorpay_action", "webhook_verification", "audit_trail", "risk_profile_update",
    ]
    assert names == expected_flow, "Judge flow must follow the canonical pipeline"
    gov = [t for t in body["timeline"] if t["name"] == "governance_policy"]
    assert gov, "Governance must be an explicit pipeline step"
    assert gov[0]["result"]["policy_version"] == "gov_policy_v1.0"
    assert gov[0]["result"]["final_decision"] == body["final_decision"].lower()
    # Honesty labels on the two integration steps
    razorpay_modes = {t["mode"] for t in body["timeline"] if t["name"] == "razorpay_action"}
    assert razorpay_modes.issubset({"razorpay_test_mode", "labeled_simulation", "error"})
    webhook_modes = {t["mode"] for t in body["timeline"] if t["name"] == "webhook_verification"}
    assert webhook_modes.issubset(
        {"real_hmac_on_labeled_test_event", "not_configured_skipped"})


def test_override_preserves_full_history():
    """Requirement 8/9: AI decision is NEVER overwritten; full context preserved."""
    # 1. Create the original AI decision
    r = client.post("/v1/risk/analyze", json=HIGH_RISK_TXN)
    txn_id = r.json()["transaction_id"]
    ai_decision = r.json()["decision"]
    ai_score = r.json()["risk_score"]

    # 2. Human overrides
    r2 = client.post("/v1/risk/override", json={
        "transaction_id": txn_id,
        "human_decision": "review",
        "reason": "Customer verified identity through manual review.",
        "analyst_id": "analyst_42",
    })
    assert r2.status_code == 200

    # 3. Audit entry preserves BOTH decisions + reason + actor + timestamp + txn id
    r3 = client.get("/v1/audit/recent")
    entries = {e["transaction_id"]: e for e in r3.json()["entries"]}
    entry = entries[txn_id]
    assert entry["ai_decision"] == ai_decision, "Original AI decision must survive the override"
    assert entry["human_decision"] == "review"
    assert entry["risk_score"] == ai_score
    assert entry["override_reason"] == "Customer verified identity through manual review."
    assert entry["analyst_id"] == "analyst_42"
    assert entry["is_overridden"] is True
    assert entry["overridden_at"], "Override timestamp must be recorded"
    assert entry["transaction_id"] == txn_id
    assert entry["action_taken"] == "review"


def test_override_requires_reason():
    r = client.post("/v1/risk/analyze", json=LOW_RISK_TXN)
    txn_id = r.json()["transaction_id"]
    r2 = client.post("/v1/risk/override", json={
        "transaction_id": txn_id, "human_decision": "approve", "reason": "x",
    })
    assert r2.status_code == 422, "Short/empty reasons must be rejected"


def test_override_unknown_transaction_404():
    r = client.post("/v1/risk/override", json={
        "transaction_id": "txn_does_not_exist", "human_decision": "approve",
        "reason": "manual investigation complete",
    })
    assert r.status_code == 404


def test_profiles_closed_loop_via_api():
    # Analyze creates the profile (closed loop)
    r = client.post("/v1/risk/analyze", json=HIGH_RISK_TXN)
    assert r.status_code == 200
    r2 = client.get("/v1/profiles/customer/CUS_TEST")
    assert r2.status_code == 200
    body = r2.json()
    assert body["total_transactions"] >= 1
    assert "risk_level" in body

    # Unknown profile is a clean 404
    r3 = client.get("/v1/profiles/customer/NOSUCH")
    assert r3.status_code == 404


def test_webhook_endpoint_rejects_invalid_signature():
    r = client.post("/v1/razorpay/webhook",
                    content=b'{"event": "payment.authorized"}',
                    headers={"X-Razorpay-Signature": "invalid"})
    # Without a configured secret the handler rejects; with a configured one an
    # invalid signature is rejected. Either way: never 200 with processing.
    assert r.status_code in (400, 403, 200)
    if r.status_code == 200:
        assert r.json().get("status") in ("error", "duplicate_ignored"), \
            "Unsigned/invalid webhooks must never be processed as verified"


def test_razorpay_create_payment_with_risk_gate():
    payload = {**HIGH_RISK_TXN, "currency": "INR"}
    r = client.post("/v1/razorpay/create-payment", json=payload)
    assert r.status_code == 200
    body = r.json()
    # Canonical ATO scenario must be refused by the risk gate
    assert body["success"] is False
    assert body["status"] == "blocked_by_risk_engine"
    assert body["order"] is None
    # Low-risk order proceeds (real test order or clearly-labeled simulation)
    r2 = client.post("/v1/razorpay/create-payment", json={**LOW_RISK_TXN, "currency": "INR"})
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["success"] is True
    assert body2["status"] in ("order_created", "order_created_simulation")
    assert body2["risk_assessment"]["decision"] in ("approve", "review", "step_up")
    if body2["status"] == "order_created_simulation":
        assert body2["test_mode_warning"], "Simulation must carry an explicit warning label"


def test_error_structure_is_consistent():
    r = client.post("/v1/risk/analyze", json={"bad": "payload"})
    assert r.status_code == 422
    body = r.json()
    assert "detail" in body
