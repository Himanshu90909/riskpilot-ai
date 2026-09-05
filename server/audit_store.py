"""
Audit Store for RiskPilot AI.
In-memory thread-safe store for transaction risk decisions and human analyst overrides.
"""

from datetime import datetime, timezone
import threading
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AuditEntry(BaseModel):
    """
    Schema for a single audit log entry.
    """
    transaction_id: str
    timestamp: str
    ai_decision: str
    human_decision: Optional[str] = None
    action_taken: str
    risk_score: float
    risk_level: str
    model_version: str
    reasons: List[str] = Field(default_factory=list)
    confidence: Optional[float] = None
    is_overridden: bool = False
    override_reason: Optional[str] = None
    analyst_id: Optional[str] = None
    overridden_at: Optional[str] = None
    amount: Optional[float] = None
    customer_id: Optional[str] = None
    merchant_id: Optional[str] = None


class AuditStore:
    """
    In-memory thread-safe store for audit trail management.
    """

    def __init__(self, max_entries: int = 1000):
        self._entries: Dict[str, AuditEntry] = {}
        self._order: List[str] = []
        self._raw_logs: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._max_entries = max_entries

    def log_decision(
        self,
        event_type: str,
        transaction_data: Dict[str, Any],
        decision_result: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Record a risk decision, webhook event, or auto-response in the audit store.
        """
        now_str = datetime.now(timezone.utc).isoformat()
        tx_id = (
            transaction_data.get("receipt")
            or transaction_data.get("payment_id")
            or transaction_data.get("order_id")
            or f"TXN-{len(self._raw_logs) + 1:05d}"
        )

        risk_info = decision_result.get("risk_assessment", {})
        score = risk_info.get("score", risk_info.get("fraud_risk_score", 0.0))
        decision = (
            decision_result.get("status")
            or decision_result.get("recommended_action")
            or "review"
        )

        entry_dict = {
            "entry_id": f"AUDIT-{len(self._raw_logs) + 1:05d}",
            "transaction_id": tx_id,
            "timestamp": now_str,
            "event_type": event_type,
            "transaction_data": transaction_data,
            "decision_result": decision_result,
            "metadata": metadata or {},
        }

        with self._lock:
            self._raw_logs.append(entry_dict)

            # Also create Pydantic AuditEntry for legacy compatibility
            audit_entry = AuditEntry(
                transaction_id=str(tx_id),
                timestamp=now_str,
                ai_decision=str(decision),
                action_taken=str(decision),
                risk_score=float(score) if isinstance(score, (int, float)) else 0.0,
                risk_level=str(risk_info.get("risk_level", "MEDIUM")),
                model_version="RiskPilot_v1.0",
                reasons=risk_info.get("reasons", []),
                amount=float(transaction_data.get("amount_paise", 0)) / 100.0,
                customer_id=transaction_data.get("user_id"),
            )
            self._entries[str(tx_id)] = audit_entry
            if str(tx_id) not in self._order:
                self._order.append(str(tx_id))

        return entry_dict

    def record_decision(
        self,
        transaction_id: str,
        risk_assessment: Dict[str, Any],
        amount: Optional[float] = None,
        customer_id: Optional[str] = None,
        merchant_id: Optional[str] = None,
    ) -> AuditEntry:
        """
        Record an AI risk analysis decision in the audit trail.
        """
        now_str = datetime.now(timezone.utc).isoformat()
        ai_decision = risk_assessment.get("decision", "review")

        entry = AuditEntry(
            transaction_id=transaction_id,
            timestamp=now_str,
            ai_decision=ai_decision,
            human_decision=None,
            action_taken=ai_decision,
            risk_score=float(risk_assessment.get("score", risk_assessment.get("risk_score", 0.0))),
            risk_level=risk_assessment.get("risk_level", "medium"),
            model_version=risk_assessment.get("model_version", "unknown"),
            reasons=risk_assessment.get("reasons", []),
            confidence=risk_assessment.get("confidence"),
            is_overridden=False,
            amount=amount,
            customer_id=customer_id,
            merchant_id=merchant_id,
        )

        with self._lock:
            if transaction_id in self._entries:
                self._order.remove(transaction_id)
            
            self._entries[transaction_id] = entry
            self._order.append(transaction_id)

            while len(self._order) > self._max_entries:
                oldest_id = self._order.pop(0)
                self._entries.pop(oldest_id, None)

        return entry

    def override_decision(
        self,
        transaction_id: str,
        human_decision: str,
        reason: str,
        analyst_id: Optional[str] = "analyst_default",
    ) -> Optional[AuditEntry]:
        """
        Record human analyst override for a transaction decision.
        """
        now_str = datetime.now(timezone.utc).isoformat()
        
        with self._lock:
            entry = self._entries.get(transaction_id)
            if not entry:
                # Data integrity: a human override must reference an existing AI decision.
                # Overriding a transaction that was never evaluated would fabricate an
                # audit record, so we refuse and let the API return 404.
                return None

            entry.human_decision = human_decision
            entry.action_taken = human_decision
            entry.is_overridden = True
            entry.override_reason = reason
            entry.analyst_id = analyst_id
            entry.overridden_at = now_str
            # Original AI decision, risk score, and timestamp are intentionally preserved.
            return entry

    def get_logs(self) -> List[Dict[str, Any]]:
        """Return all logged raw audit entries."""
        with self._lock:
            return list(self._raw_logs)

    def get_recent_entries(self, limit: int = 50) -> List[AuditEntry]:
        """
        Return recent audit entries sorted by timestamp descending (newest first).
        """
        with self._lock:
            recent_ids = list(reversed(self._order[-limit:]))
            return [self._entries[tid] for tid in recent_ids if tid in self._entries]

    def get_by_transaction_id(self, transaction_id: str) -> Optional[AuditEntry]:
        """
        Lookup audit entry by transaction_id.
        """
        with self._lock:
            return self._entries.get(transaction_id)

    def clear(self) -> None:
        """
        Clear all stored audit entries.
        """
        with self._lock:
            self._entries.clear()
            self._order.clear()
            self._raw_logs.clear()

    def format_audit_trail(self) -> str:
        """Return a formatted string representation of the audit trail."""
        with self._lock:
            if not self._raw_logs and not self._entries:
                return "Audit Trail: [Empty]"

            lines = ["=" * 75, "               RISKPILOT AI - AUDIT TRAIL LOGS", "=" * 75]
            
            for log in self._raw_logs:
                lines.append(f"Entry ID   : {log['entry_id']}")
                lines.append(f"Timestamp  : {log['timestamp']}")
                lines.append(f"Event Type : {log['event_type']}")
                decision = log['decision_result'].get('status') or log['decision_result'].get('recommended_action') or 'N/A'
                lines.append(f"Decision   : {decision}")
                risk_info = log['decision_result'].get('risk_assessment', {})
                score = risk_info.get('score', risk_info.get('fraud_risk_score', 'N/A'))
                lines.append(f"Risk Score : {score}")
                lines.append("-" * 75)
            
            return "\n".join(lines)


# Default singleton instance
default_audit_store = AuditStore()
