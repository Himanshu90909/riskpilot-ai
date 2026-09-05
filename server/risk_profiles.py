"""
RiskPilot AI — Customer & Merchant Risk Profiles.

Closed-loop risk state: every risk decision, override, and verified webhook
event updates the customer and merchant risk profile. This is the
"Risk Profile Update" step of the closed loop:

    Payment → Risk Decision → Payment Action → Webhook → Event Processing
           → Risk Profile Update → Audit Trail

In-memory store (hackathon scope). A production deployment would back this
with PostgreSQL; the interface is intentionally storage-agnostic.
"""

import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CustomerRiskProfile:
    """Mutable customer risk state updated by decisions and webhook events."""

    def __init__(self, customer_id: str):
        self.customer_id = customer_id
        self.created_at = _now_iso()
        self.updated_at = self.created_at
        self.risk_score: float = 5.0           # current rolling risk score (0-100)
        self.risk_level: str = "LOW"
        self.total_transactions = 0
        self.successful_transactions = 0
        self.failed_transactions = 0
        self.blocked_transactions = 0
        self.reviewed_transactions = 0
        self.total_amount_inr: float = 0.0
        self.average_amount_inr: float = 0.0
        self.largest_transaction_inr: float = 0.0
        self.devices_seen: List[str] = []
        self.locations_seen: List[str] = []
        self.max_velocity_1h: int = 0
        self.recent_risk_events: List[Dict[str, Any]] = []
        self.open_risk_cases: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "customer_id": self.customer_id,
            "risk_score": round(self.risk_score, 1),
            "risk_level": self.risk_level,
            "current_risk_level": self.risk_level,
            "total_transactions": self.total_transactions,
            "successful_transactions": self.successful_transactions,
            "failed_transactions": self.failed_transactions,
            "blocked_transactions": self.blocked_transactions,
            "reviewed_transactions": self.reviewed_transactions,
            "average_transaction_amount": round(self.average_amount_inr, 2),
            "largest_transaction": round(self.largest_transaction_inr, 2),
            "device_history": list(self.devices_seen),
            "location_history": list(self.locations_seen),
            "velocity_behavior": {"max_velocity_1h": self.max_velocity_1h},
            "recent_risk_events": list(self.recent_risk_events[-10:]),
            "open_risk_cases": list(self.open_risk_cases),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class MerchantRiskProfile:
    """Mutable merchant risk state updated by decisions and webhook events."""

    def __init__(self, merchant_id: str):
        self.merchant_id = merchant_id
        self.created_at = _now_iso()
        self.updated_at = self.created_at
        self.risk_score: float = 5.0
        self.total_transactions = 0
        self.blocked_transactions = 0
        self.reviewed_transactions = 0
        self.suspicious_percentage: float = 0.0
        self.total_volume_inr: float = 0.0
        self.recent_investigations: List[Dict[str, Any]] = []
        self.risk_trend: List[Dict[str, Any]] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "merchant_id": self.merchant_id,
            "risk_score": round(self.risk_score, 1),
            "total_transactions": self.total_transactions,
            "blocked_transactions": self.blocked_transactions,
            "reviewed_transactions": self.reviewed_transactions,
            "suspicious_transaction_percentage": round(self.suspicious_percentage, 2),
            "total_transaction_volume_inr": round(self.total_volume_inr, 2),
            "recent_investigations": list(self.recent_investigations[-10:]),
            "risk_trend": list(self.risk_trend[-20:]),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class RiskProfileStore:
    """Thread-safe in-memory profile store with decision/webhook update hooks."""

    def __init__(self) -> None:
        self._customers: Dict[str, CustomerRiskProfile] = {}
        self._merchants: Dict[str, MerchantRiskProfile] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # Lookup helpers used as agent tools
    # ------------------------------------------------------------------ #

    def get_customer_profile(self, customer_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            profile = self._customers.get(customer_id)
            return profile.to_dict() if profile else None

    def get_merchant_profile(self, merchant_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            profile = self._merchants.get(merchant_id)
            return profile.to_dict() if profile else None

    def _customer(self, customer_id: str) -> CustomerRiskProfile:
        if customer_id not in self._customers:
            self._customers[customer_id] = CustomerRiskProfile(customer_id)
        return self._customers[customer_id]

    def _merchant(self, merchant_id: str) -> MerchantRiskProfile:
        if merchant_id not in self._merchants:
            self._merchants[merchant_id] = MerchantRiskProfile(merchant_id)
        return self._merchants[merchant_id]

    # ------------------------------------------------------------------ #
    # Closed-loop updates
    # ------------------------------------------------------------------ #

    def record_decision(
        self,
        transaction_id: str,
        customer_id: str,
        merchant_id: Optional[str],
        amount_inr: float,
        decision: str,
        risk_score: float,
        device_id: Optional[str] = None,
        location: Optional[str] = None,
        velocity_1h: int = 0,
        model_version: str = "unknown",
    ) -> Dict[str, Any]:
        """Update profiles after a risk decision. Returns the profile snapshot delta."""
        decision = str(decision).lower()
        event = {
            "event_id": f"evt_{uuid.uuid4().hex[:12]}",
            "transaction_id": transaction_id,
            "type": "risk_decision",
            "decision": decision,
            "risk_score": round(float(risk_score), 1),
            "amount_inr": float(amount_inr),
            "timestamp": _now_iso(),
        }

        with self._lock:
            cust = self._customer(customer_id)
            cust.total_transactions += 1
            cust.total_amount_inr += amount_inr
            cust.average_amount_inr = cust.total_amount_inr / max(cust.total_transactions, 1)
            cust.largest_transaction_inr = max(cust.largest_transaction_inr, amount_inr)
            if device_id and device_id not in cust.devices_seen:
                cust.devices_seen.append(device_id)
            if location and location not in cust.locations_seen:
                cust.locations_seen.append(location)
            cust.max_velocity_1h = max(cust.max_velocity_1h, int(velocity_1h))

            if decision == "approve":
                cust.successful_transactions += 1
                # approvals decay risk slightly (good history)
                cust.risk_score = max(0.0, cust.risk_score * 0.95)
            elif decision == "review":
                cust.reviewed_transactions += 1
            elif decision == "step_up":
                # Governance step-up: payment held pending additional verification
                cust.reviewed_transactions += 1
                cust.risk_score = min(100.0, cust.risk_score + 8.0)
            elif decision == "block":
                cust.blocked_transactions += 1
                # blocks raise risk sharply
                cust.risk_score = min(100.0, cust.risk_score + 25.0)
                cust.open_risk_cases.append(transaction_id)

            cust.risk_level = self._level_for(cust.risk_score)
            cust.recent_risk_events.append(event)
            cust.updated_at = _now_iso()

            if merchant_id:
                merch = self._merchant(merchant_id)
                merch.total_transactions += 1
                merch.total_volume_inr += amount_inr
                if decision == "block":
                    merch.blocked_transactions += 1
                    merch.risk_score = min(100.0, merch.risk_score + 5.0)
                elif decision in ("review", "step_up"):
                    merch.reviewed_transactions += 1
                flagged = merch.blocked_transactions + merch.reviewed_transactions
                merch.suspicious_percentage = (
                    100.0 * flagged / max(merch.total_transactions, 1)
                )
                merch.risk_trend.append({
                    "timestamp": _now_iso(),
                    "risk_score": round(merch.risk_score, 1),
                    "decision": decision,
                })
                merch.recent_investigations.append({
                    "transaction_id": transaction_id,
                    "decision": decision,
                    "risk_score": round(float(risk_score), 1),
                    "model_version": model_version,
                    "timestamp": _now_iso(),
                })
                merch.updated_at = _now_iso()

        return event

    def record_webhook_event(
        self,
        event_type: str,
        entity_id: str,
        customer_id: Optional[str] = None,
        merchant_id: Optional[str] = None,
        outcome: str = "processed",
    ) -> Dict[str, Any]:
        """Update profiles after a signature-verified webhook event."""
        event = {
            "event_id": f"evt_{uuid.uuid4().hex[:12]}",
            "entity_id": entity_id,
            "type": f"webhook_{event_type}",
            "outcome": outcome,
            "timestamp": _now_iso(),
        }
        with self._lock:
            if customer_id and customer_id in self._customers:
                cust = self._customers[customer_id]
                if event_type == "payment.failed":
                    cust.failed_transactions += 1
                    cust.risk_score = min(100.0, cust.risk_score + 10.0)
                elif event_type == "payment.authorized":
                    cust.successful_transactions += 1
                    cust.risk_score = max(0.0, cust.risk_score * 0.9)
                cust.risk_level = self._level_for(cust.risk_score)
                cust.recent_risk_events.append(event)
                cust.updated_at = _now_iso()

            if merchant_id and merchant_id in self._merchants:
                merch = self._merchants[merchant_id]
                merch.recent_investigations.append({
                    "webhook_event": event_type,
                    "entity_id": entity_id,
                    "outcome": outcome,
                    "timestamp": _now_iso(),
                })
                merch.updated_at = _now_iso()
        return event

    def close_risk_case(self, transaction_id: str, customer_id: Optional[str] = None) -> bool:
        """Close an open risk case after analyst review."""
        with self._lock:
            if customer_id:
                cust = self._customers.get(customer_id)
                if cust and transaction_id in cust.open_risk_cases:
                    cust.open_risk_cases.remove(transaction_id)
                    cust.updated_at = _now_iso()
                    return True
            # Fall back: remove from any customer holding the case
            for cust in self._customers.values():
                if transaction_id in cust.open_risk_cases:
                    cust.open_risk_cases.remove(transaction_id)
                    cust.updated_at = _now_iso()
                    return True
            return False

    def list_customers(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [p.to_dict() for p in self._customers.values()]

    @staticmethod
    def _level_for(score: float) -> str:
        if score <= 30.0:
            return "LOW"
        if score <= 60.0:
            return "MEDIUM"
        if score <= 80.0:
            return "HIGH"
        return "CRITICAL"


# Module-level default store (single instance per process)
default_profile_store = RiskProfileStore()
