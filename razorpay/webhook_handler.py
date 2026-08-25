"""
Razorpay Webhook Handler Module.
Processes inbound HTTP webhook events from Razorpay (payment.authorized, payment.failed, order.paid).
Verifies HMAC-SHA256 signatures and integrates with RiskEngine and AuditStore.
"""

import hashlib
import hmac
import json
from typing import Any, Dict, Optional, Tuple, Union
from server.risk_engine import RiskEngine
from server.audit_store import AuditStore, default_audit_store


class WebhookVerificationError(Exception):
    """Raised when webhook signature verification fails."""
    pass


class RazorpayWebhookHandler:
    """
    Webhook handler for validating and processing Razorpay webhooks.
    """

    def __init__(
        self,
        webhook_secret: Optional[str] = None,
        risk_engine: Optional[RiskEngine] = None,
        audit_store: Optional[AuditStore] = None,
    ) -> None:
        """
        Initialize Razorpay webhook handler.

        :param webhook_secret: Secret string configured in Razorpay Webhook Dashboard
        :param risk_engine: Custom RiskEngine instance
        :param audit_store: Custom AuditStore instance
        """
        self.webhook_secret = webhook_secret
        self.risk_engine = risk_engine or RiskEngine()
        self.audit_store = audit_store or default_audit_store

    def verify_signature(
        self,
        raw_body: Union[str, bytes],
        signature: str,
        secret: Optional[str] = None,
    ) -> bool:
        """
        Verify Razorpay HMAC-SHA256 webhook signature.

        :param raw_body: Raw request body string or bytes
        :param signature: X-Razorpay-Signature header value
        :param secret: Optional secret override (or defaults to instance secret)
        :return: True if signature is valid, False otherwise
        """
        sec = secret or self.webhook_secret
        if not sec:
            raise WebhookVerificationError("Webhook secret is not configured.")

        if isinstance(raw_body, str):
            body_bytes = raw_body.encode("utf-8")
        else:
            body_bytes = raw_body

        expected_sig = hmac.new(
            sec.encode("utf-8"),
            body_bytes,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected_sig, signature)

    def process_webhook(
        self,
        payload: Union[str, bytes, Dict[str, Any]],
        signature: Optional[str] = None,
        secret: Optional[str] = None,
        skip_signature_verification: bool = False,
    ) -> Tuple[Dict[str, Any], int]:
        """
        Process incoming Razorpay webhook event.

        :param payload: Webhook payload string/bytes or parsed dict.
        :param signature: Value of X-Razorpay-Signature header.
        :param secret: Webhook secret.
        :param skip_signature_verification: Set True only for internal testing without secret.
        :return: Tuple of (response_body_dict, http_status_code).
        """
        # 1. Signature verification
        if not skip_signature_verification:
            if not signature:
                return {"status": "error", "message": "Missing X-Razorpay-Signature header"}, 400

            raw_body = payload if isinstance(payload, (str, bytes)) else json.dumps(payload)
            try:
                if not self.verify_signature(raw_body, signature, secret):
                    return {"status": "error", "message": "Invalid webhook signature"}, 400
            except WebhookVerificationError as err:
                return {"status": "error", "message": str(err)}, 400

        # Parse JSON payload
        if isinstance(payload, (str, bytes)):
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                return {"status": "error", "message": "Invalid JSON payload"}, 400
        else:
            data = payload

        event = data.get("event", "")
        event_payload = data.get("payload", {})

        # Handle supported event types
        if event == "payment.failed":
            return self._handle_payment_failed(data, event_payload)
        elif event == "payment.authorized":
            return self._handle_payment_authorized(data, event_payload)
        elif event == "order.paid":
            return self._handle_order_paid(data, event_payload)
        else:
            res = {
                "status": "ignored",
                "event": event,
                "message": f"Event '{event}' received but no special risk handling required.",
            }
            return res, 200

    def _handle_payment_failed(
        self,
        full_event: Dict[str, Any],
        event_payload: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], int]:
        payment_entity = event_payload.get("payment", {}).get("entity", {})
        payment_id = payment_entity.get("id", "unknown_payment")
        error_desc = payment_entity.get("error_description") or payment_entity.get("error_code")

        # Run failure through RiskEngine
        risk_assessment = self.risk_engine.evaluate_payment_failure(payment_entity, failure_reason=error_desc)
        recommended_action = risk_assessment.get("recommended_action", "contact_customer")

        result = {
            "status": "processed",
            "event": "payment.failed",
            "payment_id": payment_id,
            "risk_assessment": risk_assessment,
            "recommended_action": recommended_action,
            "message": f"Failed payment evaluated. Recommended action: {recommended_action}.",
        }

        self.audit_store.log_decision(
            event_type="webhook_payment_failed",
            transaction_data={"payment_id": payment_id, "event": "payment.failed"},
            decision_result=result,
            metadata={"payment_entity": payment_entity},
        )

        return result, 200

    def _handle_payment_authorized(
        self,
        full_event: Dict[str, Any],
        event_payload: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], int]:
        payment_entity = event_payload.get("payment", {}).get("entity", {})
        payment_id = payment_entity.get("id", "unknown_payment")
        amount = payment_entity.get("amount", 0)

        # Confirm risk status
        notes = payment_entity.get("notes", {}) or {}
        risk_flag = notes.get("risk_flag", "cleared") if isinstance(notes, dict) else "cleared"

        confirmation = {
            "status": "confirmed",
            "event": "payment.authorized",
            "payment_id": payment_id,
            "amount": amount,
            "risk_flag": risk_flag,
            "risk_decision_confirmed": True,
            "message": f"Payment {payment_id} authorized and confirmed under risk status '{risk_flag}'.",
        }

        self.audit_store.log_decision(
            event_type="webhook_payment_authorized",
            transaction_data={"payment_id": payment_id, "event": "payment.authorized"},
            decision_result=confirmation,
            metadata={"payment_entity": payment_entity},
        )

        return confirmation, 200

    def _handle_order_paid(
        self,
        full_event: Dict[str, Any],
        event_payload: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], int]:
        order_entity = event_payload.get("order", {}).get("entity", {})
        order_id = order_entity.get("id", "unknown_order")
        amount_paid = order_entity.get("amount_paid", 0)

        res = {
            "status": "processed",
            "event": "order.paid",
            "order_id": order_id,
            "amount_paid": amount_paid,
            "message": f"Order {order_id} marked paid.",
        }

        self.audit_store.log_decision(
            event_type="webhook_order_paid",
            transaction_data={"order_id": order_id, "event": "order.paid"},
            decision_result=res,
            metadata={"order_entity": order_entity},
        )

        return res, 200
