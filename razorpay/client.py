"""
Razorpay API Client (Test-Mode).
Handles authenticated HTTP requests to Razorpay's REST API using httpx.
Includes rate limiting awareness, test-mode warnings, and structured error handling.
"""

import os
import time
import uuid
from typing import Any, Dict, Optional, Tuple
import httpx


class RazorpayClientError(Exception):
    """Custom exception raised for Razorpay API client errors."""
    pass


class RazorpayClient:
    """
    Client for interacting with Razorpay REST API v1 in TEST MODE.
    """

    TEST_MODE_WARNING = (
        "⚠️ TEST MODE ONLY: No real currency or monetary settlement is involved. "
        "RiskPilot AI operates in Razorpay Test Mode."
    )

    def __init__(
        self,
        key_id: Optional[str] = None,
        key_secret: Optional[str] = None,
        base_url: str = "https://api.razorpay.com/v1",
        rate_limit_delay: float = 0.2,
        timeout: float = 10.0,
        mock_mode: bool = False,
    ) -> None:
        """
        Initialize Razorpay API Client.

        :param key_id: Razorpay Key ID (defaults to RAZORPAY_KEY_ID env var)
        :param key_secret: Razorpay Key Secret (defaults to RAZORPAY_KEY_SECRET env var)
        :param base_url: Razorpay REST API base URL
        :param rate_limit_delay: Delay in seconds between HTTP calls for rate limiting awareness
        :param timeout: HTTP request timeout in seconds
        :param mock_mode: Force mock responses if offline or missing API credentials
        """
        self.key_id = key_id or os.getenv("RAZORPAY_KEY_ID")
        self.key_secret = key_secret or os.getenv("RAZORPAY_KEY_SECRET")
        self.base_url = base_url.rstrip("/")
        self.rate_limit_delay = rate_limit_delay
        self.timeout = timeout

        # Enable mock mode if credentials are completely absent or explicitly requested
        self.mock_mode = mock_mode or not (self.key_id and self.key_secret)

    def _get_auth(self) -> Tuple[str, str]:
        if not self.key_id or not self.key_secret:
            raise RazorpayClientError(
                "Razorpay API credentials missing. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET environment variables."
            )
        return (self.key_id, self.key_secret)

    def _apply_rate_limit(self) -> None:
        if self.rate_limit_delay > 0:
            time.sleep(self.rate_limit_delay)

    def _attach_test_warning(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(response_data, dict):
            response_data["_test_mode_warning"] = self.TEST_MODE_WARNING
            response_data["_is_test_mode"] = True
        return response_data

    def _mock_response(
        self,
        method: str,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Provides fallback mock responses for demonstration and offline testing."""
        path_clean = path.lstrip("/")
        now_ts = int(time.time())

        if path_clean == "orders" and method == "POST":
            json_data = json or {}
            order_id = f"order_{uuid.uuid4().hex[:14]}"
            res = {
                "id": order_id,
                "entity": "order",
                "amount": json_data.get("amount", 0),
                "amount_paid": 0,
                "amount_due": json_data.get("amount", 0),
                "currency": json_data.get("currency", "INR"),
                "receipt": json_data.get("receipt", f"rcpt_{uuid.uuid4().hex[:8]}"),
                "status": "created",
                "attempts": 0,
                "notes": json_data.get("notes", {}),
                "created_at": now_ts,
            }

        elif path_clean == "payment_links" and method == "POST":
            json_data = json or {}
            link_id = f"plink_{uuid.uuid4().hex[:14]}"
            res = {
                "id": link_id,
                "entity": "payment_link",
                "amount": json_data.get("amount", 0),
                "currency": json_data.get("currency", "INR"),
                "short_url": f"https://rzp.io/i/{link_id[:8]}",
                "status": "created",
                "description": json_data.get("description", ""),
                "notes": json_data.get("notes", {}),
                "created_at": now_ts,
            }

        elif path_clean.startswith("payments/") and path_clean.endswith("/capture") and method == "POST":
            payment_id = path_clean.split("/")[1]
            json_data = json or {}
            res = {
                "id": payment_id,
                "entity": "payment",
                "amount": json_data.get("amount", 0),
                "currency": json_data.get("currency", "INR"),
                "status": "captured",
                "order_id": f"order_{uuid.uuid4().hex[:14]}",
                "captured": True,
                "created_at": now_ts,
            }

        elif path_clean.startswith("payments/") and method == "GET":
            payment_id = path_clean.split("/")[1]
            res = {
                "id": payment_id,
                "entity": "payment",
                "amount": 500000,
                "currency": "INR",
                "status": "authorized",
                "order_id": f"order_{uuid.uuid4().hex[:14]}",
                "method": "card",
                "email": "customer@example.com",
                "contact": "+919876543210",
                "created_at": now_ts,
                "notes": {"risk_flag": "manual_review_required"},
            }

        elif path_clean == "settlements" and method == "GET":
            res = {
                "entity": "collection",
                "count": 2,
                "items": [
                    {
                        "id": f"setl_{uuid.uuid4().hex[:14]}",
                        "entity": "settlement",
                        "amount": 150000,
                        "status": "processed",
                        "created_at": now_ts - 86400,
                    },
                    {
                        "id": f"setl_{uuid.uuid4().hex[:14]}",
                        "entity": "settlement",
                        "amount": 340000,
                        "status": "processed",
                        "created_at": now_ts - 172800,
                    },
                ],
            }
        else:
            res = {"status": "success", "message": f"Mock response for {method} {path}"}

        return self._attach_test_warning(res)

    def _request(
        self,
        method: str,
        path: str,
        json: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute HTTP request to Razorpay v1 REST API with error handling and rate limits."""
        self._apply_rate_limit()

        if self.mock_mode:
            return self._mock_response(method, path, json, params)

        auth = self._get_auth()
        url = f"{self.base_url}/{path.lstrip('/')}"

        max_retries = 3
        for attempt in range(max_retries):
            try:
                with httpx.Client(timeout=self.timeout) as http_client:
                    res = http_client.request(
                        method=method,
                        url=url,
                        auth=auth,
                        json=json,
                        params=params,
                        headers={"User-Agent": "RiskPilot-AI-Razorpay-Client/1.0"},
                    )

                if res.status_code == 429:
                    retry_after = float(res.headers.get("Retry-After", 1.0))
                    time.sleep(retry_after)
                    continue

                res.raise_for_status()
                data = res.json()
                return self._attach_test_warning(data)

            except httpx.HTTPStatusError as err:
                try:
                    err_json = err.response.json()
                    err_msg = err_json.get("error", {}).get("description", str(err))
                except Exception:
                    err_msg = str(err)
                raise RazorpayClientError(f"Razorpay API HTTP Error [{err.response.status_code}]: {err_msg}") from err
            except httpx.RequestError as err:
                if attempt == max_retries - 1:
                    raise RazorpayClientError(f"Razorpay API Connection Error: {str(err)}") from err
                time.sleep(0.5 * (attempt + 1))

        raise RazorpayClientError("Failed to complete request to Razorpay API after retries.")

    def create_order(
        self,
        amount_paise: int,
        currency: str = "INR",
        receipt: Optional[str] = None,
        notes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a test order via POST /v1/orders.

        :param amount_paise: Amount in smallest currency unit (e.g. 50000 paise = ₹500.00)
        :param currency: 3-letter ISO currency code (default: INR)
        :param receipt: Optional receipt identifier
        :param notes: Key-value metadata notes attached to the order
        :return: Created order response payload with test-mode warning
        """
        payload = {
            "amount": amount_paise,
            "currency": currency,
        }
        if receipt:
            payload["receipt"] = receipt
        if notes:
            payload["notes"] = notes

        return self._request("POST", "orders", json=payload)

    def create_payment_link(
        self,
        amount_paise: int,
        title: str,
        description: str,
        currency: str = "INR",
        customer_details: Optional[Dict[str, Any]] = None,
        notes: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a test payment link via POST /v1/payment_links.

        :param amount_paise: Amount in paise
        :param title: Payment link title / reference
        :param description: Description of transaction
        :param currency: ISO currency code
        :param customer_details: Dict with name, email, contact
        :param notes: Additional notes dict
        :return: Created payment link payload
        """
        payload = {
            "amount": amount_paise,
            "currency": currency,
            "description": f"{title} - {description}",
        }
        if customer_details:
            payload["customer"] = customer_details
        if notes:
            payload["notes"] = notes

        return self._request("POST", "payment_links", json=payload)

    def fetch_payment(self, payment_id: str) -> Dict[str, Any]:
        """
        Fetch payment details via GET /v1/payments/{payment_id}.

        :param payment_id: Razorpay payment ID (e.g., pay_123456)
        :return: Payment details response payload
        """
        if not payment_id:
            raise RazorpayClientError("payment_id cannot be empty.")
        return self._request("GET", f"payments/{payment_id}")

    def fetch_settlements(self, count: int = 10, skip: int = 0) -> Dict[str, Any]:
        """
        Fetch recent settlements via GET /v1/settlements.

        :param count: Number of settlement items to retrieve
        :param skip: Number of settlement items to skip for pagination
        :return: List of settlement items response payload
        """
        params = {"count": count, "skip": skip}
        return self._request("GET", "settlements", params=params)

    def capture_payment(
        self,
        payment_id: str,
        amount_paise: int,
        currency: str = "INR",
    ) -> Dict[str, Any]:
        """
        Capture an authorized payment via POST /v1/payments/{payment_id}/capture.

        :param payment_id: Razorpay payment ID to capture
        :param amount_paise: Amount to capture in paise
        :param currency: Currency code
        :return: Captured payment response payload
        """
        if not payment_id:
            raise RazorpayClientError("payment_id cannot be empty.")
        payload = {
            "amount": amount_paise,
            "currency": currency,
        }
        return self._request("POST", f"payments/{payment_id}/capture", json=payload)
