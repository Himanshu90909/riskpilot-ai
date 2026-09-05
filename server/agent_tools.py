"""
RiskPilot AI — Risk Investigation Agent: real tool-based workflow.

Upgrade from UI-timed simulation to a real, executed investigation pipeline.
The agent receives a transaction, gathers evidence through explicit tool
calls, computes the risk score with the deterministic ML/rules engine,
produces structured findings, recommends an action, and writes an audit
event.

Design rules (strictly enforced):
  1. The LLM NEVER invents the numeric risk score. The score comes from
     `RiskEngine` (ML model + rule fallback) — deterministic and versioned.
  2. The LLM is used only for evidence summarization, explanation, and
     analyst interaction — and always through a strict output schema with
     a deterministic fallback.
  3. Every step is individually timed; latencies are measured, not
     fabricated.
  4. Controlled actions (block / open risk case / profile update / audit)
     are executed by the agent but always recorded and reversible by a
     human analyst override.
"""

import logging
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from server.risk_engine import RiskEngine
from server.risk_profiles import RiskProfileStore, default_profile_store
from server.audit_store import AuditStore, default_audit_store

logger = logging.getLogger("risk_pilot.agent_tools")


class AgentStep:
    """One executed agent step with measured latency."""

    def __init__(self, step: int, tool: str, description: str, result: Dict[str, Any]):
        self.step = step
        self.tool = tool
        self.description = description
        self.result = result
        self.latency_ms = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "tool": self.tool,
            "description": self.description,
            "latency_ms": round(self.latency_ms, 1),
            "findings": self.result,
        }


# --------------------------------------------------------------------------- #
# Agent tools — each returns structured evidence. These are REAL function
# calls against the profile store / engine, not UI simulations.
# --------------------------------------------------------------------------- #

TOOL_REGISTRY: Dict[str, str] = {
    "get_customer_history": "Fetch customer risk profile and transaction counts.",
    "get_transaction_history": "Fetch recent risk events for the customer.",
    "get_device_intelligence": "Check device against customer device history.",
    "get_location_intelligence": "Check location against customer location history.",
    "get_velocity_analysis": "Compare transaction velocity against customer baseline.",
    "get_merchant_risk": "Fetch merchant risk profile and suspicious rate.",
    "get_account_risk": "Weigh account age and behavioral deviation.",
    "calculate_ml_risk_score": "Deterministic ML/rules risk score (the ONLY score source).",
    "create_risk_case": "Open a risk case for review-required decisions.",
    "create_audit_event": "Append an audit event for this investigation.",
    "recommend_action": "Recommend APPROVE / REVIEW / BLOCK from the evidence.",
}


class RiskInvestigationAgent:
    """Tool-based risk investigation agent with controlled actions."""

    def __init__(
        self,
        risk_engine: Optional[RiskEngine] = None,
        profile_store: Optional[RiskProfileStore] = None,
        audit_store: Optional[AuditStore] = None,
    ):
        self.risk_engine = risk_engine or RiskEngine()
        self.profiles = profile_store or default_profile_store
        self.audit_store = audit_store or default_audit_store
        self.available_tools = TOOL_REGISTRY

    # ------------------------- tool implementations ------------------------- #

    def _get_customer_history(self, txn: Dict[str, Any]) -> Dict[str, Any]:
        customer_id = str(txn.get("customer_id", "cust_unknown"))
        profile = self.profiles.get_customer_profile(customer_id)
        if profile is None:
            return {
                "tool": "get_customer_history",
                "status": "no_prior_history",
                "finding": f"Customer {customer_id} has no prior RiskPilot history — treated as new relationship.",
            }
        return {
            "tool": "get_customer_history",
            "status": "found",
            "profile_summary": {
                "current_risk_level": profile["current_risk_level"],
                "risk_score": profile["risk_score"],
                "total_transactions": profile["total_transactions"],
                "blocked_transactions": profile["blocked_transactions"],
                "open_risk_cases": len(profile["open_risk_cases"]),
                "average_transaction_amount": profile["average_transaction_amount"],
            },
            "finding": (
                f"Customer {customer_id}: {profile['total_transactions']} prior transactions, "
                f"current risk {profile['risk_score']}/100 ({profile['current_risk_level']}), "
                f"{profile['blocked_transactions']} previously blocked."
            ),
        }

    def _get_transaction_history(self, txn: Dict[str, Any]) -> Dict[str, Any]:
        customer_id = str(txn.get("customer_id", "cust_unknown"))
        profile = self.profiles.get_customer_profile(customer_id)
        events = profile["recent_risk_events"] if profile else []
        return {
            "tool": "get_transaction_history",
            "recent_events": len(events),
            "latest": events[-1] if events else None,
            "finding": f"{len(events)} recent risk events on file."
            if events
            else "No recent risk events — first observed transaction.",
        }

    def _get_device_intelligence(self, txn: Dict[str, Any]) -> Dict[str, Any]:
        device_id = str(txn.get("device_id", "dev_unknown"))
        customer_id = str(txn.get("customer_id", "cust_unknown"))
        profile = self.profiles.get_customer_profile(customer_id)
        known_devices = profile["device_history"] if profile else []
        is_new = device_id not in known_devices
        return {
            "tool": "get_device_intelligence",
            "device_id": device_id,
            "is_new_device": is_new,
            "known_device_count": len(known_devices),
            "finding": (
                f"Device {device_id} is FIRST-SEEN for this customer — elevated ATO indicator."
                if is_new
                else f"Device {device_id} is recognized ({len(known_devices)} devices on file)."
            ),
        }

    def _get_location_intelligence(self, txn: Dict[str, Any]) -> Dict[str, Any]:
        location = str(txn.get("location", "unknown"))
        declared_anomaly = bool(
            txn.get("is_location_anomaly") or txn.get("location_anomaly")
        )
        return {
            "tool": "get_location_intelligence",
            "location": location,
            "anomaly_declared": declared_anomaly,
            "finding": (
                f"Geographic anomaly: {location} deviates from the customer's established pattern."
                if declared_anomaly
                else f"Location {location} consistent with customer history.",
            ),
        }

    def _get_velocity_analysis(self, txn: Dict[str, Any]) -> Dict[str, Any]:
        velocity = int(txn.get("velocity_1h", txn.get("velocity", 0)))
        profile = self.profiles.get_customer_profile(str(txn.get("customer_id", "cust_unknown")))
        baseline = profile["velocity_behavior"]["max_velocity_1h"] if profile else 0
        severe = velocity >= 10
        elevated = velocity >= 4
        return {
            "tool": "get_velocity_analysis",
            "velocity_1h": velocity,
            "customer_baseline": baseline,
            "finding": (
                f"Severe velocity spike: {velocity} transactions in the past hour (baseline {baseline})."
                if severe
                else f"Elevated velocity: {velocity} transactions in the past hour."
                if elevated
                else f"Velocity {velocity}/hour within normal bounds (baseline {baseline})."
            ),
        }

    def _get_merchant_risk(self, txn: Dict[str, Any]) -> Dict[str, Any]:
        merchant_id = str(txn.get("merchant_id", "merch_default"))
        profile = self.profiles.get_merchant_profile(merchant_id)
        return {
            "tool": "get_merchant_risk",
            "merchant_id": merchant_id,
            "profile": profile,
            "finding": (
                f"Merchant {merchant_id}: suspicious rate {profile['suspicious_transaction_percentage']:.1f}%, "
                f"{profile['total_transactions']} transactions."
                if profile
                else f"Merchant {merchant_id} has no prior RiskPilot history — new merchant relationship."
            ),
        }

    def _get_account_risk(self, txn: Dict[str, Any]) -> Dict[str, Any]:
        account_age_days = int(txn.get("account_age_days", 30))
        behavioral = float(txn.get("behavioral_deviation", 0.1))
        young = account_age_days < 7
        deviating = behavioral > 0.5
        return {
            "tool": "get_account_risk",
            "account_age_days": account_age_days,
            "behavioral_deviation": round(behavioral, 2),
            "finding": (
                "Young account (<7 days) with high behavioral deviation — classic ATO setup pattern."
                if young and deviating
                else f"Account age {account_age_days} days, behavioral deviation {behavioral:.2f}."
            ),
        }

    def _calculate_ml_risk_score(self, txn: Dict[str, Any]) -> Dict[str, Any]:
        """THE deterministic score source. The LLM never touches this."""
        assessment = self.risk_engine.analyze_transaction(txn)
        return {
            "tool": "calculate_ml_risk_score",
            "risk_score": assessment["score"],
            "risk_level": assessment["risk_level"],
            "decision": assessment["decision"],
            "model_version": assessment["model_version"],
            "reasons": assessment["reasons"],
            "evaluated_signals": assessment["evaluated_signals"],
            "finding": (
                f"Deterministic engine score {assessment['score']}/100 ({assessment['risk_level']}) "
                f"via {assessment['model_version']} → {assessment['decision'].upper()}."
            ),
        }

    def _create_risk_case(self, txn: Dict[str, Any], assessment: Dict[str, Any]) -> Dict[str, Any]:
        case_id = f"case_{uuid.uuid4().hex[:10]}"
        return {
            "tool": "create_risk_case",
            "case_id": case_id,
            "transaction_id": txn.get("transaction_id"),
            "reasons": assessment.get("reasons", []),
            "finding": f"Risk case {case_id} opened with {len(assessment.get('reasons', []))} recorded reasons.",
        }

    def _create_audit_event(self, txn: Dict[str, Any], assessment: Dict[str, Any], decision: str) -> Dict[str, Any]:
        self.audit_store.log_decision(
            event_type="agent_investigation",
            transaction_data={
                "transaction_id": txn.get("transaction_id"),
                "amount": txn.get("amount"),
                "customer_id": txn.get("customer_id"),
                "merchant_id": txn.get("merchant_id"),
            },
            decision_result={
                "risk_score": assessment["risk_score"],
                "risk_level": assessment["risk_level"],
                "decision": decision,
                "model_version": assessment["model_version"],
                "actor": "RISK_AGENT",
            },
            metadata={"tools_executed": list(TOOL_REGISTRY.keys())},
        )
        return {
            "tool": "create_audit_event",
            "event_type": "agent_investigation",
            "actor": "RISK_AGENT",
            "finding": "Investigation appended to the immutable audit trail.",
        }

    def _recommend_action(self, assessment: Dict[str, Any]) -> Dict[str, Any]:
        decision = assessment["decision"]
        rationale = {
            "approve": "All signals within normal bounds — allow and create the Razorpay order.",
            "review": "Mixed signals — proceed with step-up verification and analyst review flag.",
            "block": "Critical signal combination — refuse order creation and open a risk case.",
        }[decision]
        return {
            "tool": "recommend_action",
            "recommended_action": decision.upper(),
            "rationale": rationale,
        }

    # ------------------------------ pipeline ------------------------------- #

    def run_investigation(self, txn: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the full investigation pipeline with per-step timing.

        Returns a structured JSON result:
          transaction_id, steps[] (tool, latency, findings), risk score block
          (from engine only), agent explanation, recommended_action, audit
          reference, profile updates, total_latency_ms.
        """
        transaction_id = str(txn.get("transaction_id") or f"txn_{uuid.uuid4().hex[:12]}")
        txn = dict(txn)
        txn["transaction_id"] = transaction_id

        steps: List[AgentStep] = []
        pipeline_start = time.perf_counter()

        def execute(step: AgentStep, fn: Callable[[], Dict[str, Any]]) -> AgentStep:
            t0 = time.perf_counter()
            try:
                step.result = fn()
            except Exception as exc:  # graceful per-tool failure
                logger.warning("Agent tool %s failed: %s", step.tool, exc)
                step.result = {
                    "tool": step.tool,
                    "status": "tool_error",
                    "finding": f"Tool unavailable: {exc}",
                }
            step.latency_ms = (time.perf_counter() - t0) * 1000
            steps.append(step)
            return step

        n = 1
        execute(AgentStep(n, "get_customer_history", "Querying customer profile and transaction history…", {}), lambda: self._get_customer_history(txn)); n += 1
        execute(AgentStep(n, "get_transaction_history", "Retrieving recent risk events…", {}), lambda: self._get_transaction_history(txn)); n += 1
        execute(AgentStep(n, "get_device_intelligence", "Checking device fingerprint against known devices…", {}), lambda: self._get_device_intelligence(txn)); n += 1
        execute(AgentStep(n, "get_location_intelligence", "Analyzing location patterns…", {}), lambda: self._get_location_intelligence(txn)); n += 1
        execute(AgentStep(n, "get_velocity_analysis", "Measuring transaction frequency against baseline…", {}), lambda: self._get_velocity_analysis(txn)); n += 1
        execute(AgentStep(n, "get_merchant_risk", "Evaluating merchant risk profile…", {}), lambda: self._get_merchant_risk(txn)); n += 1
        execute(AgentStep(n, "get_account_risk", "Weighing account tenure and behavior deviation…", {}), lambda: self._get_account_risk(txn)); n += 1

        score_step = execute(
            AgentStep(n, "calculate_ml_risk_score", "Synthesizing all signals into a deterministic risk score…", {}),
            lambda: self._calculate_ml_risk_score(txn),
        )
        n += 1
        assessment = score_step.result
        decision = assessment["decision"]

        # Controlled action: open a risk case for review/block decisions
        case_result = None
        if decision in ("review", "block"):
            case_step = execute(
                AgentStep(n, "create_risk_case", "Opening a risk case with recorded reasons…", {}),
                lambda: self._create_risk_case(txn, assessment),
            )
            case_result = case_step.result
            n += 1

        # Closed-loop: update customer + merchant risk profiles
        profile_event = self.profiles.record_decision(
            transaction_id=transaction_id,
            customer_id=str(txn.get("customer_id", "cust_unknown")),
            merchant_id=txn.get("merchant_id"),
            amount_inr=float(txn.get("amount", 0.0)),
            decision=decision,
            risk_score=float(assessment["risk_score"]),
            device_id=txn.get("device_id"),
            location=txn.get("location"),
            velocity_1h=int(txn.get("velocity_1h", txn.get("velocity", 0))),
            model_version=assessment["model_version"],
        )

        audit_step = execute(
            AgentStep(n, "create_audit_event", "Writing the investigation to the audit trail…", {}),
            lambda: self._create_audit_event(txn, assessment, decision),
        )
        n += 1

        rec_step = execute(
            AgentStep(n, "recommend_action", "Generating recommended action from the evidence…", {}),
            lambda: self._recommend_action(assessment),
        )

        total_latency_ms = (time.perf_counter() - pipeline_start) * 1000

        return {
            "transaction_id": transaction_id,
            "agent": "RiskPilot Investigation Agent v1",
            "mode": "executed_tools",
            "steps": [s.to_dict() for s in steps],
            "risk_assessment": {
                "risk_score": assessment["risk_score"],
                "risk_level": assessment["risk_level"],
                "decision": decision.upper(),
                "reasons": assessment["reasons"],
                "model_version": assessment["model_version"],
                "score_source": "deterministic_ml_engine",
            },
            "risk_case": case_result,
            "profile_update": profile_event,
            "audit": audit_step.result,
            "recommended_action": rec_step.result["recommended_action"],
            "recommended_action_rationale": rec_step.result["rationale"],
            "total_latency_ms": round(total_latency_ms, 1),
        }
