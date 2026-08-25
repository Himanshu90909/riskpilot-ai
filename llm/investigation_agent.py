"""
RiskPilot AI - Investigation Agent Module.

Implements an agentic multi-step investigation pipeline that simulates the 8-step
fraud investigation workflow displayed in the RiskPilot UI:
1. Customer History Check - 'Querying customer profile and transaction history...'
2. Device Reputation Check - 'Checking device fingerprint against known devices...'
3. Geographic Behavior Check - 'Analyzing location patterns and distance from usual locations...'
4. Velocity Check - 'Measuring transaction frequency against baseline...'
5. Payment Behavior Check - 'Reviewing payment method and failure history...'
6. Merchant Signal Check - 'Evaluating merchant risk profile...'
7. Risk Score Calculation - 'Synthesizing all signals into risk score...'
8. Explanation Generation - 'Generating investigation summary and recommendation...'
"""

import datetime
import logging
from typing import Any, Dict, List, Optional

from llm.explanation_generator import extract_context_fields
from llm.risk_analyst import RiskAnalyst

logger = logging.getLogger("RiskPilot.InvestigationAgent")


class InvestigationAgent:
    """
    Multi-step fraud investigation agent simulating the agentic RiskPilot UI workflow.
    """

    def __init__(self, risk_analyst: Optional[RiskAnalyst] = None):
        """
        Initialize InvestigationAgent.

        Args:
            risk_analyst: RiskAnalyst instance (defaults to new RiskAnalyst).
        """
        self.risk_analyst = risk_analyst or RiskAnalyst()

    def run_investigation(self, transaction_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute full 8-step investigation pipeline for transaction context.

        Args:
            transaction_context: Dict containing transaction metrics and signals.

        Returns:
            Dict containing step-by-step logs, overall assessment, investigation timeline,
            and final LLM/fallback analysis.
        """
        fields = extract_context_fields(transaction_context)
        steps: List[Dict[str, Any]] = []

        # Step 1: Customer History Check
        step1 = self._step1_customer_history(fields)
        steps.append(step1)

        # Step 2: Device Reputation Check
        step2 = self._step2_device_reputation(fields)
        steps.append(step2)

        # Step 3: Geographic Behavior Check
        step3 = self._step3_geographic_behavior(fields)
        steps.append(step3)

        # Step 4: Velocity Check
        step4 = self._step4_velocity(fields)
        steps.append(step4)

        # Step 5: Payment Behavior Check
        step5 = self._step5_payment_behavior(fields)
        steps.append(step5)

        # Step 6: Merchant Signal Check
        step6 = self._step6_merchant_signal(fields)
        steps.append(step6)

        # Step 7: Risk Score Calculation
        step7 = self._step7_risk_score_calculation(fields, steps)
        steps.append(step7)

        # Step 8: Explanation Generation (calls LLM Risk Analyst)
        llm_analysis = self.risk_analyst.analyze_transaction(transaction_context)
        step8 = self._step8_explanation_generation(llm_analysis)
        steps.append(step8)

        # Build investigation timeline
        timeline = self._build_timeline(steps, llm_analysis)

        return {
            "transaction_id": fields["transaction_id"],
            "amount": fields["amount"],
            "currency": fields["currency"],
            "overall_risk_score": fields["risk_score"],
            "overall_risk_level": fields["risk_level"],
            "ai_decision": fields["ai_decision"],
            "steps": steps,
            "summary_analysis": llm_analysis,
            "investigation_timeline": timeline,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

    def _step1_customer_history(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        age = fields["account_age_days"]
        chargebacks = fields["historical_chargebacks"]
        prev_tx = fields["total_previous_tx_count"]

        if chargebacks > 0:
            status = "flag"
            finding = f"High-risk account history: Account age {age} days, {prev_tx} prior order(s), {chargebacks} previous chargeback(s)."
        elif age < 7 or prev_tx < 2:
            status = "review"
            finding = f"New customer profile: Account age {age} days with limited transaction history ({prev_tx} prior orders)."
        else:
            status = "pass"
            finding = f"Established customer profile: Account age {age} days, {prev_tx} prior orders, 0 chargebacks."

        return {
            "step_number": 1,
            "name": "Customer History Check",
            "description": "Querying customer profile and transaction history...",
            "status": status,
            "findings": finding,
            "details": {
                "account_age_days": age,
                "total_previous_tx_count": prev_tx,
                "historical_chargebacks": chargebacks,
            },
        }

    def _step2_device_reputation(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        vpn = fields["is_vpn_or_proxy"]
        new_dev = fields["is_new_device"]
        fp = fields["device_fingerprint"]
        ip = fields["ip"]

        if vpn:
            status = "flag"
            finding = f"Suspicious network telemetry: IP {ip} is associated with an anonymizing VPN or proxy network."
        elif new_dev:
            status = "review"
            finding = f"Unrecognized hardware fingerprint ({fp}): First order observed on this device."
        else:
            status = "pass"
            finding = f"Trusted device: Fingerprint ({fp}) matches established customer hardware history."

        return {
            "step_number": 2,
            "name": "Device Reputation Check",
            "description": "Checking device fingerprint against known devices...",
            "status": status,
            "findings": finding,
            "details": {
                "ip": ip,
                "device_fingerprint": fp,
                "is_vpn_or_proxy": vpn,
                "is_new_device": new_dev,
            },
        }

    def _step3_geographic_behavior(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        dist = fields["distance_from_usual_km"]
        current = fields["current_city"]
        usual = fields["usual_city"]
        mismatch = fields["country_mismatch"]

        if mismatch or dist > 500:
            status = "flag"
            finding = f"Geographic anomaly: Transaction IP in {current}, {dist:.0f} km away from habitual region ({usual})."
        elif dist > 100:
            status = "review"
            finding = f"Moderate location variance: Current city {current} is {dist:.0f} km from home location ({usual})."
        else:
            status = "pass"
            finding = f"Location verified: Origin city ({current}) aligns with customer home region ({usual})."

        return {
            "step_number": 3,
            "name": "Geographic Behavior Check",
            "description": "Analyzing location patterns and distance from usual locations...",
            "status": status,
            "findings": finding,
            "details": {
                "current_city": current,
                "usual_city": usual,
                "distance_from_usual_km": dist,
                "country_mismatch": mismatch,
            },
        }

    def _step4_velocity(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        v10 = fields["tx_count_last_10m"]
        v1h = fields["tx_count_last_1h"]
        v_score = fields["velocity_score"]

        if v10 >= 3 or v_score >= 75:
            status = "flag"
            finding = f"Velocity burst detected: {v10} transactions in 10 minutes (Velocity Risk Score: {v_score:.0f}/100)."
        elif v10 >= 2 or v1h >= 4:
            status = "review"
            finding = f"Elevated frequency: {v10} txs in 10m, {v1h} txs in 1 hour."
        else:
            status = "pass"
            finding = f"Velocity normal: {v10} txs in 10m, {v1h} txs in 1 hour within baseline thresholds."

        return {
            "step_number": 4,
            "name": "Velocity Check",
            "description": "Measuring transaction frequency against baseline...",
            "status": status,
            "findings": finding,
            "details": {
                "tx_count_last_10m": v10,
                "tx_count_last_1h": v1h,
                "tx_count_last_24h": fields["tx_count_last_24h"],
                "velocity_score": v_score,
            },
        }

    def _step5_payment_behavior(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        failed = fields["total_failed_attempts"]
        failed_otp = fields["failed_otp"]

        if failed >= 3 or failed_otp >= 2:
            status = "flag"
            finding = f"Authentication failure alert: {failed} failed attempt(s) ({failed_otp} OTP failures) prior to current attempt."
        elif failed > 0:
            status = "review"
            finding = f"Recent auth failure: {failed} failed attempt recorded in recent session."
        else:
            status = "pass"
            finding = "Authentication clear: Zero failed auth/OTP attempts in current session."

        return {
            "step_number": 5,
            "name": "Payment Behavior Check",
            "description": "Reviewing payment method and failure history...",
            "status": status,
            "findings": finding,
            "details": {
                "failed_otp_last_1h": failed_otp,
                "total_failed_attempts": failed,
            },
        }

    def _step6_merchant_signal(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        m_name = fields["merchant_name"]
        mcc = fields["merchant_mcc"]
        cat = fields["merchant_risk_category"].upper()

        if cat in ["HIGH", "CRITICAL"]:
            status = "flag"
            finding = f"High-risk merchant: Target merchant '{m_name}' (MCC {mcc}) classified under High Risk category."
        elif cat == "MEDIUM":
            status = "review"
            finding = f"Moderate merchant risk: Target merchant '{m_name}' (MCC {mcc}) requires standard risk oversight."
        else:
            status = "pass"
            finding = f"Trusted merchant: Target merchant '{m_name}' (MCC {mcc}) classified as Low Risk."

        return {
            "step_number": 6,
            "name": "Merchant Signal Check",
            "description": "Evaluating merchant risk profile...",
            "status": status,
            "findings": finding,
            "details": {
                "merchant_name": m_name,
                "merchant_mcc": mcc,
                "merchant_risk_category": cat,
            },
        }

    def _step7_risk_score_calculation(
        self, fields: Dict[str, Any], prior_steps: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        score = fields["risk_score"]
        level = fields["risk_level"]
        decision = fields["ai_decision"]

        flag_count = sum(1 for s in prior_steps if s["status"] == "flag")
        review_count = sum(1 for s in prior_steps if s["status"] == "review")

        if score >= 75 or flag_count >= 2:
            status = "flag"
            finding = f"Risk Score: {score:.1f}/100 [{level}] -> AI Decision: {decision}. Synthesized {flag_count} critical flags and {review_count} review signals."
        elif score >= 40 or flag_count >= 1 or review_count >= 2:
            status = "review"
            finding = f"Risk Score: {score:.1f}/100 [{level}] -> AI Decision: {decision}. Synthesized {flag_count} flag(s) and {review_count} review signal(s)."
        else:
            status = "pass"
            finding = f"Risk Score: {score:.1f}/100 [{level}] -> AI Decision: {decision}. All telemetry checks clear."

        return {
            "step_number": 7,
            "name": "Risk Score Calculation",
            "description": "Synthesizing all signals into risk score...",
            "status": status,
            "findings": finding,
            "details": {
                "risk_score": score,
                "risk_level": level,
                "ai_decision": decision,
                "flagged_steps_count": flag_count,
                "review_steps_count": review_count,
            },
        }

    def _step8_explanation_generation(self, llm_analysis: Dict[str, Any]) -> Dict[str, Any]:
        action = llm_analysis.get("recommended_action", "").upper()
        if "BLOCK" in action or "REJECT" in action:
            status = "flag"
        elif "REVIEW" in action or "FLAG" in action:
            status = "review"
        else:
            status = "pass"

        engine = llm_analysis.get("engine_used", "unknown")
        summary = llm_analysis.get("summary", "")

        return {
            "step_number": 8,
            "name": "Explanation Generation",
            "description": "Generating investigation summary and recommendation...",
            "status": status,
            "findings": f"Generated reasoning via {engine}: {summary}",
            "details": llm_analysis,
        }

    def _build_timeline(
        self, steps: List[Dict[str, Any]], llm_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        timeline = []
        for s in steps:
            timeline.append({
                "step": s["step_number"],
                "name": s["name"],
                "description": s["description"],
                "status": s["status"],
                "findings": s["findings"],
            })
        return timeline


def assistant_reply(transaction_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Drop-in replacement function for RiskPilot AI's legacy assistantReply seam.
    Executes real-time agentic multi-step investigation and LLM risk analysis.

    Args:
        transaction_context: Dict containing transaction telemetry & risk indicators.

    Returns:
        Structured investigation report with step logs, timeline, and LLM reasoning.
    """
    agent = InvestigationAgent()
    return agent.run_investigation(transaction_context)


# Alias for camelCase callers
assistantReply = assistant_reply
