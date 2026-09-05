"""
Razorpay Integration for RiskPilot AI.
Handles Razorpay test-mode order creation after pre-screening via RiskEngine.
"""

import os
from datetime import datetime, timezone
import uuid
import logging
from typing import Any, Dict, Optional, Tuple

import httpx
from server.risk_engine import RiskEngine
from server.audit_store import AuditStore

logger = logging.getLogger("risk_pilot.razorpay_integration")

RAZORPAY_API_URL = "https://api.razorpay.com/v1/orders"


class RazorpayIntegration:
    """
    Razorpay Test Mode Payment Order Service with inline fraud risk assessment.
    """

    def __init__(self, key_id: Optional[str] = None, key_secret: Optional[str] = None):
        self.key_id = key_id or os.environ.get("RAZORPAY_KEY_ID", "rzp_test_dummy_key_id")
        self.key_secret = key_secret or os.environ.get("RAZORPAY_KEY_SECRET", "rzp_test_dummy_key_secret")
        self.is_placeholder_key = self.key_id.startswith("rzp_test_dummy") or "dummy" in self.key_id.lower()

    async def create_order_with_risk_check(
        self,
        order_payload: Dict[str, Any],
        risk_engine: RiskEngine,
        audit_store: AuditStore,
    ) -> Dict[str, Any]:
        """
        Pre-screen transaction through RiskEngine.
        - If decision is 'block': Refuse Razorpay order creation.
        - If decision is 'approve' or 'review': Call Razorpay API to create test order.
        """
        amount_inr = float(order_payload.get("amount", 0.0))
        customer_id = str(order_payload.get("customer_id", "cust_unknown"))
        device_id = str(order_payload.get("device_id", "dev_unknown"))
        location = str(order_payload.get("location", "unknown"))
        velocity = int(order_payload.get("velocity", 1))
        failed_attempts = int(order_payload.get("failed_attempts", 0))
        account_age_days = int(order_payload.get("account_age_days", 30))
        merchant_id = str(order_payload.get("merchant_id", "merch_default"))
        merchant_risk_score = float(order_payload.get("merchant_risk_score", 10.0))
        behavioral_deviation = float(order_payload.get("behavioral_deviation", 0.1))
        currency = str(order_payload.get("currency", "INR")).upper()
        receipt = order_payload.get("receipt") or f"rcpt_{uuid.uuid4().hex[:8]}"

        txn_id = f"txn_{uuid.uuid4().hex[:12]}"

        # 1. Evaluate Risk
        txn_risk_input = {
            "transaction_id": txn_id,
            "amount": amount_inr,
            "customer_id": customer_id,
            "device_id": device_id,
            "location": location,
            "velocity": velocity,
            "failed_attempts": failed_attempts,
            "account_age_days": account_age_days,
            "merchant_id": merchant_id,
            "merchant_risk_score": merchant_risk_score,
            "behavioral_deviation": behavioral_deviation,
        }

        raw_assessment = risk_engine.analyze_transaction(txn_risk_input)
        # Governance policy decides the final action (AI recommends; governance decides)
        from server.governance import governed_assessment as _governed
        risk_assessment = _governed(raw_assessment)
        risk_assessment["transaction_id"] = txn_id

        # 2. Record in Audit Store
        audit_store.record_decision(
            transaction_id=txn_id,
            risk_assessment=risk_assessment,
            amount=amount_inr,
            customer_id=customer_id,
            merchant_id=merchant_id,
        )

        decision = risk_assessment.get("decision", "review")
        risk_score = risk_assessment.get("risk_score", risk_assessment.get("score", 0.0))
        risk_level = str(risk_assessment.get("risk_level", "medium")).lower()

        test_warning = None
        if self.is_placeholder_key:
            test_warning = (
                "Running with dummy/placeholder Razorpay API credentials. "
                "Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET environment variables for live Razorpay Test Mode API calls."
            )

        # 3. Handle 'block' Decision
        if decision == "block":
            logger.warning(f"Payment order blocked for txn {txn_id} (Score: {risk_score}, Level: {risk_level})")
            return {
                "success": False,
                "status": "blocked_by_risk_engine",
                "message": f"Payment order creation refused by RiskPilot AI. Transaction risk score ({risk_score}) exceeds critical threshold.",
                "transaction_id": txn_id,
                "order": None,
                "risk_assessment": risk_assessment,
                "test_mode_warning": test_warning,
            }

        # 4. Handle 'approve', 'review', or 'step_up' Decision -> Create Razorpay Order
        #    (step_up creates the order but marks it as requiring additional verification,
        #     e.g. 3DS/OTP, before the payment can complete.)
        amount_paise = int(round(amount_inr * 100))
        user_notes = order_payload.get("notes") or {}
        
        # Inject RiskPilot AI tags into Razorpay Order notes
        rzp_notes = {
            **user_notes,
            "risk_pilot_id": txn_id,
            "risk_score": str(risk_score),
            "risk_level": risk_level,
            "risk_decision": decision,
            "ai_recommendation": str(risk_assessment.get("ai_recommendation", "review")),
            "policy_version": str(risk_assessment.get("policy_version", "gov_policy_v1.0")),
        }
        if decision == "step_up":
            rzp_notes["requires_step_up_verification"] = "true"

        rzp_payload = {
            "amount": amount_paise,
            "currency": currency,
            "receipt": receipt,
            "notes": rzp_notes,
        }

        # Call Razorpay REST API
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    RAZORPAY_API_URL,
                    auth=(self.key_id, self.key_secret),
                    json=rzp_payload,
                )

            if response.status_code == 200:
                order_data = response.json()
                logger.info(f"Successfully created Razorpay order {order_data.get('id')} for txn {txn_id}")
                return {
                    "success": True,
                    "status": "order_created",
                    "message": f"Razorpay order successfully created with risk decision '{decision.upper()}'.",
                    "transaction_id": txn_id,
                    "order": order_data,
                    "risk_assessment": risk_assessment,
                    "test_mode_warning": test_warning,
                }
            else:
                error_body = response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text
                logger.error(f"Razorpay API Error ({response.status_code}): {error_body}")

                # If test key is dummy / unauthorized, return mock test order with test warning
                if response.status_code in (401, 400) and self.is_placeholder_key:
                    mock_order_id = f"order_test_{uuid.uuid4().hex[:14]}"
                    mock_order = {
                        "id": mock_order_id,
                        "entity": "order",
                        "amount": amount_paise,
                        "amount_paid": 0,
                        "amount_due": amount_paise,
                        "currency": currency,
                        "receipt": receipt,
                        "status": "created",
                        "attempts": 0,
                        "notes": rzp_notes,
                        "created_at": int(datetime.now(timezone.utc).timestamp()),
                        "mode": "test_simulation",
                    }
                    return {
                        "success": True,
                        "status": "order_created_simulation",
                        "message": f"Simulated Razorpay order created successfully (Test Mode). Risk decision: '{decision.upper()}'.",
                        "transaction_id": txn_id,
                        "order": mock_order,
                        "risk_assessment": risk_assessment,
                        "test_mode_warning": (
                            test_warning or f"Razorpay API returned {response.status_code}. Mock test order generated for buildathon demonstration."
                        ),
                    }

                return {
                    "success": False,
                    "status": "razorpay_api_error",
                    "message": f"Razorpay API error ({response.status_code}): {error_body}",
                    "transaction_id": txn_id,
                    "order": None,
                    "risk_assessment": risk_assessment,
                    "test_mode_warning": test_warning,
                }

        except Exception as ex:
            logger.error(f"Network / client exception during Razorpay API call: {ex}")
            # If network error occurs with placeholder keys, return fallback test order
            if self.is_placeholder_key:
                mock_order_id = f"order_test_{uuid.uuid4().hex[:14]}"
                mock_order = {
                    "id": mock_order_id,
                    "entity": "order",
                    "amount": amount_paise,
                    "amount_paid": 0,
                    "amount_due": amount_paise,
                    "currency": currency,
                    "receipt": receipt,
                    "status": "created",
                    "attempts": 0,
                    "notes": rzp_notes,
                    "mode": "test_simulation",
                }
                return {
                    "success": True,
                    "status": "order_created_simulation",
                    "message": f"Simulated Razorpay order created. Risk decision: '{decision.upper()}'.",
                    "transaction_id": txn_id,
                    "order": mock_order,
                    "risk_assessment": risk_assessment,
                    "test_mode_warning": f"{test_warning} (Client error: {str(ex)})",
                }

            return {
                "success": False,
                "status": "connection_error",
                "message": f"Failed to connect to Razorpay API: {str(ex)}",
                "transaction_id": txn_id,
                "order": None,
                "risk_assessment": risk_assessment,
                "test_mode_warning": test_warning,
            }
