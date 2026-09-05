"""
RiskPilot AI - Fallback Rule-Based Explanation Generator Module.

Provides deterministic, rule-based fraud explanations, risk signal extractions,
recommendations, follow-up questions, and investigation timeline narratives
when LLM services (Google Gemini API) are unreachable or unconfigured.
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger("RiskPilot.ExplanationGenerator")


def extract_context_fields(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts standardized telemetry and risk attributes from a flexible transaction context dict.
    Supports both nested objects (customer, device, location, etc.) and flat dictionary keys.
    """
    # Customer history
    customer = context.get("customer") or context.get("customer_history") or {}
    if not isinstance(customer, dict):
        customer = {}

    # Device info
    device = context.get("device") or context.get("device_info") or {}
    if not isinstance(device, dict):
        device = {}

    # Location info
    location = context.get("location") or {}
    if not isinstance(location, dict):
        location = {}

    # Velocity info
    velocity = context.get("velocity") or {}
    if not isinstance(velocity, dict):
        velocity = {}

    # Failed attempts
    failed = context.get("failed_attempts") or {}
    if not isinstance(failed, dict):
        failed = {}

    # Merchant info
    merchant = context.get("merchant") or context.get("merchant_info") or {}
    if not isinstance(merchant, dict):
        merchant = {}

    # Amount & Currency
    amount = float(context.get("amount", 0.0))
    currency = str(context.get("currency", "INR"))

    # Extracted values with fallbacks
    account_age_days = int(
        customer.get("account_age_days", context.get("account_age_days", 30))
    )
    total_previous_tx_count = int(
        customer.get("total_previous_tx_count", context.get("total_previous_tx_count", 10))
    )
    historical_chargebacks = int(
        customer.get("historical_chargebacks", context.get("historical_chargebacks", 0))
    )
    avg_tx_amount = float(
        customer.get("avg_tx_amount", context.get("avg_tx_amount", amount))
    )

    ip = str(device.get("ip", context.get("ip", "unknown")))
    is_vpn_or_proxy = bool(
        device.get(
            "is_vpn_or_proxy",
            context.get("is_vpn_or_proxy", device.get("is_proxy", False)),
        )
    )
    is_new_device = bool(
        device.get("is_new_device", context.get("is_new_device", False))
    )
    device_fingerprint = str(
        device.get("fingerprint", context.get("device_fingerprint", "fp_unknown"))
    )

    current_city = str(
        location.get("current_city", context.get("current_city", "Unknown"))
    )
    usual_city = str(
        location.get("usual_city", context.get("usual_city", "Unknown"))
    )
    distance_from_usual_km = float(
        location.get(
            "distance_from_usual_km", context.get("distance_from_usual_km", 0.0)
        )
    )
    country_mismatch = bool(
        location.get("country_mismatch", context.get("country_mismatch", False))
    )

    tx_count_last_10m = int(
        velocity.get("tx_count_last_10m", context.get("tx_count_last_10m", 0))
    )
    tx_count_last_1h = int(
        velocity.get("tx_count_last_1h", context.get("tx_count_last_1h", 0))
    )
    tx_count_last_24h = int(
        velocity.get("tx_count_last_24h", context.get("tx_count_last_24h", 0))
    )
    velocity_score = float(
        velocity.get("velocity_score", context.get("velocity_score", 0.0))
    )

    failed_otp = int(
        failed.get("failed_otp_last_1h", context.get("failed_otp_last_1h", 0))
    )
    failed_pin = int(
        failed.get("failed_pin_last_1h", context.get("failed_pin_last_1h", 0))
    )
    total_failed_attempts = int(
        failed.get(
            "total_failed_attempts",
            context.get("total_failed_attempts", failed_otp + failed_pin),
        )
    )

    merchant_name = str(
        merchant.get("name", context.get("merchant_name", "Merchant"))
    )
    merchant_mcc = str(
        merchant.get("mcc", context.get("merchant_mcc", "0000"))
    )
    merchant_risk_category = str(
        merchant.get("risk_category", context.get("merchant_risk_category", "LOW"))
    )

    risk_score = float(context.get("risk_score", 0.0))
    risk_level = str(context.get("risk_level", "LOW")).upper()
    raw_decision = context.get("ai_decision") or context.get("decision") or "APPROVE"
    decision_map = {
        "approve": "APPROVE", "allow": "APPROVE", "cleared": "APPROVE",
        "review": "REVIEW", "flag_for_review": "REVIEW", "flag": "REVIEW",
        "step_up": "REVIEW", "stepup": "REVIEW", "verify": "REVIEW",
        "block": "BLOCK", "blocked": "BLOCK", "reject": "BLOCK", "refuse": "BLOCK", "denied": "BLOCK",
    }
    ai_decision = decision_map.get(str(raw_decision).strip().lower(), "APPROVE")
    transaction_id = str(context.get("transaction_id", "tx_unknown"))

    return {
        "transaction_id": transaction_id,
        "amount": amount,
        "currency": currency,
        "account_age_days": account_age_days,
        "total_previous_tx_count": total_previous_tx_count,
        "historical_chargebacks": historical_chargebacks,
        "avg_tx_amount": avg_tx_amount,
        "ip": ip,
        "is_vpn_or_proxy": is_vpn_or_proxy,
        "is_new_device": is_new_device,
        "device_fingerprint": device_fingerprint,
        "current_city": current_city,
        "usual_city": usual_city,
        "distance_from_usual_km": distance_from_usual_km,
        "country_mismatch": country_mismatch,
        "tx_count_last_10m": tx_count_last_10m,
        "tx_count_last_1h": tx_count_last_1h,
        "tx_count_last_24h": tx_count_last_24h,
        "velocity_score": velocity_score,
        "failed_otp": failed_otp,
        "failed_pin": failed_pin,
        "total_failed_attempts": total_failed_attempts,
        "merchant_name": merchant_name,
        "merchant_mcc": merchant_mcc,
        "merchant_risk_category": merchant_risk_category,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "ai_decision": ai_decision,
    }


class ExplanationGenerator:
    """
    Rule-based deterministic risk explanation generator.
    Acts as the reliable fallback mechanism when LLM inference is disabled or unavailable.
    """

    def generate_explanation(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generates a structured risk explanation from raw transaction context.

        Args:
            context: Raw transaction context dict.

        Returns:
            Dict containing summary, risk_factors, recommended_action, reasoning,
            follow_up_questions, timeline_narrative, is_fallback, and engine_used.
        """
        fields = extract_context_fields(context)
        risk_factors: List[str] = []
        follow_up_questions: List[str] = []
        timeline_narrative: List[str] = []

        # 1. Amount Spike Check
        amount = fields["amount"]
        avg_amt = fields["avg_tx_amount"]
        curr = fields["currency"]
        if avg_amt > 0 and amount > 2.5 * avg_amt:
            multiplier = amount / avg_amt
            risk_factors.append(
                f"Amount Anomaly: Transaction value ({curr} {amount:,.2f}) is {multiplier:.1f}x higher than baseline average ({curr} {avg_amt:,.2f})."
            )
            follow_up_questions.append(
                "Has the account holder completed transactions of comparable size in previous billing cycles?"
            )
            timeline_narrative.append(
                f"Amount evaluation flagged high transaction size ({curr} {amount:,.2f} vs avg {curr} {avg_amt:,.2f})."
            )

        # 2. Customer Profile / History Check
        age = fields["account_age_days"]
        prev_tx = fields["total_previous_tx_count"]
        chargebacks = fields["historical_chargebacks"]

        if age < 7 or prev_tx == 0:
            risk_factors.append(
                f"New Profile Risk: Account created recently ({age} days ago) with minimal transaction history ({prev_tx} prior orders)."
            )
            follow_up_questions.append(
                "Can identity proof (e.g. KYC documentation, verified phone/email) be verified for this new account?"
            )
            timeline_narrative.append(
                f"Customer profile check noted new user status ({age} days old)."
            )

        if chargebacks > 0:
            risk_factors.append(
                f"Historical Chargebacks: Profile has {chargebacks} previous chargeback(s) recorded."
            )
            follow_up_questions.append(
                "What were the exact resolution notes and merchant categories for prior chargebacks on this account?"
            )
            timeline_narrative.append(
                f"Historical audit identified {chargebacks} previous chargeback record(s)."
            )

        # 3. Device & Network Telemetry
        if fields["is_vpn_or_proxy"]:
            risk_factors.append(
                "Anonymized Network: Transaction IP address is flagged as a commercial VPN, TOR exit node, or proxy."
            )
            follow_up_questions.append(
                "Is the user connecting through a legitimate corporate VPN or an anonymizing proxy?"
            )
            timeline_narrative.append(
                "Device analysis detected active VPN/proxy masking true origin IP."
            )

        if fields["is_new_device"]:
            risk_factors.append(
                f"Unrecognized Hardware: Device fingerprint '{fields['device_fingerprint']}' is new for this account."
            )
            follow_up_questions.append(
                "Was 2FA or device authorization completed during login on this new hardware?"
            )
            timeline_narrative.append(
                "Fingerprint scan confirmed unrecognized device."
            )

        # 4. Geographic Telemetry
        dist = fields["distance_from_usual_km"]
        current_city = fields["current_city"]
        usual_city = fields["usual_city"]
        if dist > 300 or fields["country_mismatch"]:
            risk_factors.append(
                f"Geographic Distance Anomaly: Transaction IP in {current_city} is {dist:.0f} km away from usual location in {usual_city}."
            )
            follow_up_questions.append(
                "Does the physical distance between recent activity indicate impossible travel velocity?"
            )
            timeline_narrative.append(
                f"Geographic check registered location shift to {current_city} ({dist:.0f} km away)."
            )

        # 5. Velocity Telemetry
        v10 = fields["tx_count_last_10m"]
        v_score = fields["velocity_score"]
        if v10 >= 3 or v_score >= 70:
            risk_factors.append(
                f"Velocity Spike: Detected {v10} transactions within a 10-minute window (Velocity Risk Score: {v_score:.0f}/100)."
            )
            follow_up_questions.append(
                "Are multiple orders being placed sequentially with identical cart items or cards?"
            )
            timeline_narrative.append(
                f"Velocity monitor detected burst activity ({v10} attempts in 10 mins)."
            )

        # 6. Payment & Authentication Failures
        failed_attempts = fields["total_failed_attempts"]
        failed_otp = fields["failed_otp"]
        if failed_attempts > 0:
            risk_factors.append(
                f"Authentication Failures: {failed_attempts} total failed payment/OTP attempt(s) recorded in recent session."
            )
            follow_up_questions.append(
                "Were the failed authentication attempts due to incorrect PIN/OTP entry or card decline codes?"
            )
            timeline_narrative.append(
                f"Payment security check recorded {failed_attempts} prior failed attempt(s)."
            )

        # 7. Merchant Risk Category
        m_cat = fields["merchant_risk_category"].upper()
        m_name = fields["merchant_name"]
        if m_cat in ["HIGH", "CRITICAL"]:
            risk_factors.append(
                f"High-Risk Merchant Category: Destination merchant '{m_name}' (MCC {fields['merchant_mcc']}) is classified as High Risk."
            )
            follow_up_questions.append(
                "Is this high-risk merchant purchase consistent with the user's historical spending profile?"
            )
            timeline_narrative.append(
                f"Merchant evaluation flagged target '{m_name}' as High Risk."
            )

        # Fallback if no specific risk factors triggered
        if not risk_factors:
            risk_factors.append(
                "Standard Behavioral Pattern: Telemetry metrics reflect normal user baseline parameters."
            )
            follow_up_questions.append(
                "Are there any external notification flags or support tickets attached to this customer ID?"
            )
            timeline_narrative.append(
                "Baseline security audit completed: All behavioral signals clear."
            )

        # Determine Recommendation & Reasoning
        score = fields["risk_score"]
        decision = fields["ai_decision"]

        if score >= 75 or decision in ["REJECT", "BLOCK"]:
            recommended_action = "BLOCK"
            reasoning = (
                f"Transaction cumulative risk score ({score:.1f}/100) exceeds block threshold. "
                f"Multiple critical risk signals triggered ({len(risk_factors)} factors active). "
                "Decline order immediately to prevent financial loss."
            )
        elif score >= 40 or decision in ["FLAG_FOR_REVIEW", "REVIEW"]:
            recommended_action = "FLAG_FOR_REVIEW"
            reasoning = (
                f"Transaction risk score ({score:.1f}/100) reflects moderate anomaly concentration. "
                "Manual analyst review is required to verify legitimacy before settlement."
            )
        else:
            recommended_action = "ALLOW"
            reasoning = (
                f"Transaction risk score ({score:.1f}/100) is low. "
                "All telemetry signals fall within acceptable operational bounds."
            )

        # Synthesize Investigation Summary
        tx_id = fields["transaction_id"]
        if recommended_action == "BLOCK":
            summary = (
                f"Transaction {tx_id} for {curr} {amount:,.2f} at {m_name} was flagged as HIGH RISK "
                f"(Score: {score:.1f}/100, Decision: {decision}). Key drivers include "
                f"{risk_factors[0].split(':')[0].lower()} and {risk_factors[1].split(':')[0].lower() if len(risk_factors) > 1 else 'suspicious telemetry'}. "
                "Immediate decline is recommended to prevent potential fraud exposure."
            )
        elif recommended_action == "FLAG_FOR_REVIEW":
            summary = (
                f"Transaction {tx_id} for {curr} {amount:,.2f} at {m_name} exhibits MODERATE RISK "
                f"(Score: {score:.1f}/100, Decision: {decision}). Primary concerns involve "
                f"{risk_factors[0].split(':')[0].lower()}. Human analyst review is recommended."
            )
        else:
            summary = (
                f"Transaction {tx_id} for {curr} {amount:,.2f} at {m_name} is evaluated as LOW RISK "
                f"(Score: {score:.1f}/100, Decision: {decision}). All risk checks passed within standard limits."
            )

        timeline_narrative.append(
            f"Final Risk Score synthesized: {score:.1f}/100 [{fields['risk_level']}] -> Action: {recommended_action}."
        )

        return {
            "summary": summary,
            "risk_factors": risk_factors,
            "recommended_action": recommended_action,
            "reasoning": reasoning,
            "follow_up_questions": follow_up_questions,
            "timeline_narrative": timeline_narrative,
            "is_fallback": True,
            "engine_used": "rule-based-fallback",
        }
