"""RiskPilot AI — Canonical Governance Policy Layer.

SINGLE authoritative governance module. Pipeline position:

    Transaction → Risk Engine → Risk Score → Governance Policy → Final Decision → Audit

The risk engine (and the AI investigation layer) only RECOMMEND. This module
owns the final automated decision. This separation means the AI recommendation
and the governed decision can (and for the HIGH band, deliberately do) differ.

Supported final decisions:
    APPROVE   — score band LOW (0-30)
    REVIEW    — score band MEDIUM (31-60)
    STEP-UP   — score band HIGH (61-80): require additional verification (e.g. 3DS/OTP)
    BLOCK     — score band CRITICAL (81-100)
"""

from typing import Any, Dict, Optional

GOVERNANCE_POLICY_VERSION = "gov_policy_v1.0"
GOVERNANCE_RULES = [
    "0-30 LOW → APPROVE",
    "31-60 MEDIUM → REVIEW (human analyst)",
    "61-80 HIGH → STEP-UP (additional verification required)",
    "81-100 CRITICAL → BLOCK",
]

# Final decision per risk band. The engine recommends; governance decides.
_BAND_DECISIONS = {
    "low": "approve",
    "medium": "review",
    "high": "step_up",
    "critical": "block",
}

# Merchant-facing recommended action per final decision.
_RECOMMENDED_ACTIONS = {
    "approve": "allow_order",
    "review": "hold_for_analyst_review",
    "step_up": "create_order_with_step_up_verification",
    "block": "refuse_order_creation",
}


def apply_governance(assessment: Dict[str, Any]) -> Dict[str, Any]:
    """Apply the governance policy to a risk-engine assessment.

    Returns a governance result dict. Does NOT mutate the input assessment;
    the caller decides how to merge (typically: ai_recommendation = engine
    decision, decision = governed final decision).
    """
    risk_level = str(assessment.get("risk_level", "medium")).lower()
    if risk_level not in _BAND_DECISIONS:
        risk_level = "medium"

    engine_decision = str(assessment.get("decision", "review")).lower()
    final_decision = _BAND_DECISIONS[risk_level]

    human_review_required = final_decision in ("review", "step_up", "block")
    diverged = final_decision != engine_decision

    notes = []
    if diverged:
        notes.append(
            f"Governance raised the engine recommendation '{engine_decision}' to "
            f"'{final_decision}' for band {risk_level.upper()} — band policy governs the final decision."
        )
    if final_decision == "step_up":
        notes.append("Step-up verification (e.g. 3DS/OTP) required before the payment can complete.")
    if human_review_required:
        notes.append("Analyst review path available; any human override is preserved in the audit trail.")

    return {
        "policy_version": GOVERNANCE_POLICY_VERSION,
        "risk_band": risk_level,
        "ai_recommendation": engine_decision,
        "final_decision": final_decision,
        "step_up_required": final_decision == "step_up",
        "human_review_required": human_review_required,
        "ai_recommendation_differs": diverged,
        "rules": list(GOVERNANCE_RULES),
        "notes": notes,
    }


def governed_assessment(assessment: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of the assessment with governance applied and surfaced.

    Adds/overrides:
      - ai_recommendation  : the risk engine's (AI layer's) recommendation
      - decision           : the GOVERNED final decision (approve/review/step_up/block)
      - recommended_action : merchant-facing action
      - policy_version     : governance policy version
      - governance         : full governance result for audit/UI display
    """
    governed = apply_governance(assessment)
    result = dict(assessment)
    result["ai_recommendation"] = governed["ai_recommendation"]
    result["decision"] = governed["final_decision"]
    result["recommended_action"] = _RECOMMENDED_ACTIONS[governed["final_decision"]]
    result["policy_version"] = governed["policy_version"]
    result["governance"] = governed
    return result
