"""
RiskPilot AI - Risk Gateway for Razorpay Integrations.
Sits between the merchant checkout / order creation flow and the payment processor.
Evaluates pre-transaction risk, intercepts high-risk transactions, flags borderline ones,
and handles automated responses for failed payments.
"""

from typing import Any, Dict, Optional
from server.risk_engine import RiskEngine
from server.audit_store import AuditStore, default_audit_store
from razorpay.client import RazorpayClient, RazorpayClientError


class RiskGateway:
    """
    Risk Gateway providing pre-transaction decisioning, order creation interception,
    and post-failure automated response intelligence.
    """

    def __init__(
        self,
        razorpay_client: Optional[RazorpayClient] = None,
        risk_engine: Optional[RiskEngine] = None,
        audit_store: Optional[AuditStore] = None,
    ) -> None:
        """
        Initialize the Risk Gateway.

        :param razorpay_client: Optional custom RazorpayClient instance.
        :param risk_engine: Optional custom RiskEngine instance.
        :param audit_store: Optional custom AuditStore instance.
        """
        self.client = razorpay_client or RazorpayClient()
        self.risk_engine = risk_engine or RiskEngine()
        self.audit_store = audit_store or default_audit_store

    def process_transaction(self, transaction_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for payment flow. Evaluates risk BEFORE creating a Razorpay order.

        1. Run transaction through the risk engine.
        2. If decision is 'block' -> refuse to create order, return risk assessment + reason.
        3. If decision is 'review' -> create order but flag for manual review, return order + risk assessment.
        4. If decision is 'approve' -> create order normally, return order + risk assessment.

        :param transaction_data: Payload containing transaction metadata.
        :return: Dict containing execution status, order data, and risk assessment.
        """
        # 1. Evaluate risk using core engine
        risk_assessment = self.risk_engine.evaluate(transaction_data)
        decision = risk_assessment.get("decision", "review")

        amount_paise = transaction_data.get("amount_paise", 0)
        currency = transaction_data.get("currency", "INR")
        receipt = transaction_data.get("receipt")
        base_notes = dict(transaction_data.get("notes", {}) or {})

        # 2. Execute decision-driven order flow
        if decision == "block":
            reason = risk_assessment.get("reasons", ["High fraud risk detected"])[0]
            result = {
                "status": "blocked",
                "order_created": False,
                "message": f"Order creation refused by RiskPilot AI: {reason}",
                "order": None,
                "risk_assessment": risk_assessment,
                "reason": reason,
            }

        elif decision == "review":
            notes = {
                **base_notes,
                "risk_flag": "manual_review_required",
                "risk_score": str(risk_assessment.get("score")),
                "risk_level": risk_assessment.get("risk_level", "MEDIUM"),
            }
            order = self.client.create_order(
                amount_paise=amount_paise,
                currency=currency,
                receipt=receipt,
                notes=notes,
            )
            result = {
                "status": "review",
                "order_created": True,
                "message": "Order created but flagged for manual review due to medium risk indicators.",
                "order": order,
                "risk_assessment": risk_assessment,
            }

        else:  # 'approve'
            notes = {
                **base_notes,
                "risk_flag": "cleared",
                "risk_score": str(risk_assessment.get("score")),
            }
            order = self.client.create_order(
                amount_paise=amount_paise,
                currency=currency,
                receipt=receipt,
                notes=notes,
            )
            result = {
                "status": "approved",
                "order_created": True,
                "message": "Transaction cleared. Razorpay order created successfully.",
                "order": order,
                "risk_assessment": risk_assessment,
            }

        # 3. Log decision to audit store
        self.audit_store.log_decision(
            event_type="transaction_risk_evaluation",
            transaction_data=transaction_data,
            decision_result=result,
            metadata={"decision": decision, "risk_score": risk_assessment.get("score")},
        )

        return result

    def handle_failed_payment(self, payment_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Auto-responder for failed payments that:
        1. Fetches payment details from Razorpay API.
        2. Runs it through the risk engine to check if failure was fraud-related.
        3. Returns recommended action (retry, block, contact_customer, escalate).

        :param payment_id: Razorpay payment ID.
        :param reason: Optional failure reason or error message.
        :return: Dict containing payment analysis and recommended response action.
        """
        try:
            payment_details = self.client.fetch_payment(payment_id)
        except RazorpayClientError as err:
            payment_details = {"id": payment_id, "error": str(err)}

        risk_assessment = self.risk_engine.evaluate_payment_failure(payment_details, failure_reason=reason)
        recommended_action = risk_assessment.get("recommended_action", "contact_customer")

        result = {
            "status": "processed",
            "payment_id": payment_id,
            "payment_details": payment_details,
            "risk_assessment": risk_assessment,
            "recommended_action": recommended_action,
            "action_description": self._get_action_description(recommended_action),
        }

        # Log every auto-responder evaluation to audit store
        self.audit_store.log_decision(
            event_type="failed_payment_auto_responder",
            transaction_data={"payment_id": payment_id, "reason": reason},
            decision_result=result,
            metadata={"recommended_action": recommended_action},
        )

        return result

    def _get_action_description(self, action: str) -> str:
        descriptions = {
            "retry": "Low risk detected. Prompt customer to retry payment or select alternate payment option.",
            "contact_customer": "Medium risk or verification issue. Trigger automated verification link / customer service reachout.",
            "escalate": "High risk pattern suspected. Forward payment record to fraud team for detailed investigation.",
            "block": "Critical fraud indicator detected. Block card token and flag user account against future orders.",
        }
        return descriptions.get(action, "Review transaction manually.")
