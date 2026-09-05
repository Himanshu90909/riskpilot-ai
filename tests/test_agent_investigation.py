"""Agent investigation tests: structured output schema, real tool execution, LLM-never-scores."""

from conftest import HIGH_RISK_TXN, LOW_RISK_TXN

from server.agent_tools import RiskInvestigationAgent, TOOL_REGISTRY


def make_agent() -> RiskInvestigationAgent:
    return RiskInvestigationAgent()


def test_tool_registry_is_real_and_documented():
    expected = {
        "get_customer_history", "get_transaction_history", "get_device_intelligence",
        "get_location_intelligence", "get_velocity_analysis", "get_merchant_risk",
        "get_account_risk", "calculate_ml_risk_score", "create_risk_case",
        "create_audit_event", "recommend_action",
    }
    assert expected.issubset(set(TOOL_REGISTRY.keys()))


def test_investigation_output_schema():
    agent = make_agent()
    result = agent.run_investigation(dict(HIGH_RISK_TXN))

    # Top-level contract
    for key in ("transaction_id", "steps", "risk_assessment", "recommended_action",
                "total_latency_ms", "profile_update", "audit"):
        assert key in result, f"Missing key: {key}"

    # Structured AI investigation output (requirement 5)
    assessment = result["risk_assessment"]
    for key in ("risk_score", "risk_level", "decision", "reasons", "model_version"):
        assert key in assessment
    assert 0.0 <= assessment["risk_score"] <= 100.0
    assert assessment["decision"] in ("APPROVE", "REVIEW", "BLOCK")
    assert len(assessment["reasons"]) >= 1

    # Evidence-style findings in every step
    assert len(result["steps"]) >= 8
    for step in result["steps"]:
        assert "tool" in step and "latency_ms" in step and "findings" in step
        assert step["latency_ms"] >= 0.0


def test_llm_never_produces_the_score():
    """The numeric score must come from the deterministic engine, never an LLM."""
    agent = make_agent()
    result = agent.run_investigation(dict(HIGH_RISK_TXN))
    assert result["risk_assessment"]["score_source"] == "deterministic_ml_engine"
    engine_scores = [s for s in result["steps"] if s["tool"] == "calculate_ml_risk_score"]
    assert engine_scores, "calculate_ml_risk_score must be an executed step"
    assert engine_scores[0]["findings"]["model_version"] in ("ml_model_v1.0", "rule_engine_v1.0")


def test_investigation_is_deterministic_and_repeatable():
    agent = make_agent()
    r1 = agent.run_investigation(dict(HIGH_RISK_TXN))
    r2 = agent.run_investigation(dict(HIGH_RISK_TXN))
    assert r1["risk_assessment"]["risk_score"] == r2["risk_assessment"]["risk_score"]
    assert r1["risk_assessment"]["decision"] == r2["risk_assessment"]["decision"]


def test_high_risk_opens_a_case_and_audits():
    agent = make_agent()
    result = agent.run_investigation(dict(HIGH_RISK_TXN))
    assert result["risk_assessment"]["decision"] == "BLOCK"
    assert result["risk_case"], "BLOCK must open a risk case for analyst review"
    assert result["audit"]["finding"], "Investigation must be appended to the audit trail"


def test_low_risk_needs_no_case():
    agent = make_agent()
    result = agent.run_investigation(dict(LOW_RISK_TXN))
    assert result["risk_assessment"]["decision"] == "APPROVE"
    assert result["risk_case"] is None


def test_latency_is_measured_not_fabricated():
    agent = make_agent()
    result = agent.run_investigation(dict(HIGH_RISK_TXN))
    # Measured: total >= sum of step latencies (allowing float tolerance)
    step_sum = sum(s["latency_ms"] for s in result["steps"])
    assert result["total_latency_ms"] >= step_sum * 0.9


def test_closed_loop_profile_update_recorded():
    agent = make_agent()
    result = agent.run_investigation(dict(HIGH_RISK_TXN))
    event = result["profile_update"]
    assert event["type"] == "risk_decision"
    assert event["decision"] == "block"
    profile = agent.profiles.get_customer_profile("CUS_TEST")
    assert profile is not None and profile["total_transactions"] >= 1
