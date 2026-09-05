"""Webhook security tests: HMAC signature verification, duplicate protection, malformed payloads."""

import json

from conftest import make_webhook_payload, sign

from razorpay.webhook_handler import RazorpayWebhookHandler

SECRET = "test_webhook_secret_123"


def make_handler() -> RazorpayWebhookHandler:
    return RazorpayWebhookHandler(webhook_secret=SECRET)


def test_valid_signature_accepted_and_processed():
    handler = make_handler()
    payload = make_webhook_payload()
    response, status = handler.process_webhook(payload, signature=sign(payload, SECRET))
    assert status == 200
    assert response["status"] == "confirmed"
    assert response["event"] == "payment.authorized"


def test_invalid_signature_rejected():
    handler = make_handler()
    payload = make_webhook_payload()
    response, status = handler.process_webhook(payload, signature="deadbeef" * 8)
    assert status == 400
    assert response["status"] == "error"
    assert "signature" in response["message"].lower()


def test_missing_signature_rejected():
    handler = make_handler()
    payload = make_webhook_payload()
    response, status = handler.process_webhook(payload, signature=None)
    assert status == 400


def test_duplicate_webhook_ignored():
    """Razorpay redelivers events — duplicates must never process twice."""
    handler = make_handler()
    payload = make_webhook_payload()
    signature = sign(payload, SECRET)

    first, s1 = handler.process_webhook(payload, signature=signature)
    assert s1 == 200 and first["status"] == "confirmed"

    second, s2 = handler.process_webhook(payload, signature=signature)
    assert s2 == 200
    assert second["status"] == "duplicate_ignored"


def test_malformed_json_rejected_safely():
    handler = make_handler()
    response, status = handler.process_webhook("not json {", signature=sign("not json {", SECRET))
    assert status == 400
    assert response["status"] == "error"


def test_unknown_event_type_handled():
    handler = make_handler()
    payload = json.dumps({"event": "refund.processed", "payload": {"refund": {"entity": {
        "id": "rfnd_1", "amount": 100, "created_at": 1690000000}}}}, sort_keys=True)
    response, status = handler.process_webhook(payload, signature=sign(payload, SECRET))
    # Unknown events must not crash — acknowledged or explicitly unsupported, never 500
    assert status in (200, 202, 400)


def test_missing_fields_do_not_crash():
    handler = make_handler()
    payload = json.dumps({"event": "payment.authorized"}, sort_keys=True)
    response, status = handler.process_webhook(payload, signature=sign(payload, SECRET))
    assert status in (200, 400)
    assert "status" in response


def test_no_secret_configured_rejects_everything():
    """Without a configured secret, verification cannot succeed — nothing is accepted unsigned."""
    handler = RazorpayWebhookHandler(webhook_secret=None)
    payload = make_webhook_payload()
    response, status = handler.process_webhook(payload, signature="anything")
    assert status == 400


def test_signature_comparison_is_constant_time():
    """Handler must use hmac.compare_digest (timing-attack resistant)."""
    import inspect
    from razorpay import webhook_handler as module
    source = inspect.getsource(module)
    assert "compare_digest" in source, "Signature comparison must be constant-time"


def test_error_responses_never_leak_secret():
    handler = make_handler()
    payload = make_webhook_payload()
    response, status = handler.process_webhook(payload, signature="wrong")
    blob = json.dumps(response)
    assert SECRET not in blob
