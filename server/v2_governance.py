"""RiskPilot v2 governed decision contracts for the original FastAPI service."""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


class AnalystDecision(str, Enum):
    APPROVE = "approve"
    MODIFY = "modify"
    REJECT = "reject"


class RiskContextV2(BaseModel):
    severity: float = Field(ge=0, le=100)
    exploit_likelihood: float = Field(ge=0, le=100)
    asset_criticality: float = Field(ge=0, le=100)
    exposure: float = Field(ge=0, le=100)
    evidence_count: int = Field(default=1, ge=0)
    freshest_evidence_age_hours: float = Field(default=0, ge=0)


class PolicyV2(BaseModel):
    version: str = "RP-2.4"
    weights: Dict[str, float] = {"severity": 0.30, "exploit_likelihood": 0.25, "asset_criticality": 0.25, "exposure": 0.20}
    thresholds: Dict[str, float] = {"critical": 85, "high": 65, "medium": 40}


class ScoreContribution(BaseModel):
    factor: str
    input_value: float
    weight: float
    contribution: float


class DecisionV2(BaseModel):
    score: float
    level: str
    action: str
    confidence: float
    policy_version: str
    contributions: List[ScoreContribution]
    abstained: bool = False
    uncertainty_flags: List[str] = []


class ReviewRequestV2(BaseModel):
    case_id: str = Field(min_length=1)
    decision: AnalystDecision
    rationale: str = Field(min_length=10)

    @model_validator(mode="after")
    def rationale_is_meaningful(self) -> "ReviewRequestV2":
        self.rationale = self.rationale.strip()
        if len(self.rationale) < 10:
            raise ValueError("Analyst rationale must be at least 10 characters")
        return self


class EvidenceV2(BaseModel):
    id: str
    excerpt: str
    reference: str
    confidence: float = Field(ge=0, le=1)
    observed_at: datetime


class SummaryV2(BaseModel):
    summary: str = Field(min_length=1)
    evidence_citations: List[str]
    uncertainty_flags: List[str]
    recommended_action: str
    requires_human_review: bool


class AppendOnlyAudit:
    """Small process-local append-only event store for the original service."""

    def __init__(self) -> None:
        self._events: List[Dict[str, Any]] = []
        self._lock = Lock()

    def append(self, event_type: str, actor: str, payload: Dict[str, Any], case_id: Optional[str] = None) -> Dict[str, Any]:
        event = {"id": uuid4().hex, "event_type": event_type, "actor": actor, "case_id": case_id, "payload": payload, "created_at": datetime.now(timezone.utc).isoformat()}
        with self._lock:
            self._events.append(event)
        return event

    def list(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._events)

    def update(self, *_: Any, **__: Any) -> None:
        raise RuntimeError("AUDIT_EVENTS_APPEND_ONLY: update is forbidden")

    def delete(self, *_: Any, **__: Any) -> None:
        raise RuntimeError("AUDIT_EVENTS_APPEND_ONLY: delete is forbidden")


def should_abstain(context: RiskContextV2) -> bool:
    return context.evidence_count == 0 or context.freshest_evidence_age_hours > 48


def score_v2(context: RiskContextV2, policy: PolicyV2 = PolicyV2()) -> DecisionV2:
    fields = [("severity", context.severity), ("exploit_likelihood", context.exploit_likelihood), ("asset_criticality", context.asset_criticality), ("exposure", context.exposure)]
    contributions = [ScoreContribution(factor=name, input_value=value, weight=policy.weights[name], contribution=round(value * policy.weights[name], 2)) for name, value in fields]
    score = round(sum(item.contribution for item in contributions), 2)
    if score >= policy.thresholds["critical"]:
        level, action = "critical", "block"
    elif score >= policy.thresholds["high"]:
        level, action = "high", "step_up"
    elif score >= policy.thresholds["medium"]:
        level, action = "medium", "review"
    else:
        level, action = "low", "approve"
    abstained = should_abstain(context)
    flags = ["Evidence is missing or stale; human review is required."] if abstained else []
    return DecisionV2(score=score, level=level, action="abstain" if abstained else action, confidence=round(max(0.0, min(1.0, 0.55 + context.evidence_count * 0.1 - context.freshest_evidence_age_hours / 200)), 3), policy_version=policy.version, contributions=contributions, abstained=abstained, uncertainty_flags=flags)


def summarize_v2(decision: DecisionV2, evidence: List[EvidenceV2]) -> SummaryV2:
    if decision.abstained:
        return SummaryV2(summary="RiskPilot abstained because supporting evidence is missing or stale.", evidence_citations=[], uncertainty_flags=decision.uncertainty_flags, recommended_action="abstain", requires_human_review=True)
    return SummaryV2(summary=f"Deterministic policy {decision.policy_version} produced a {decision.level} decision at {decision.score}/100.", evidence_citations=[item.reference for item in evidence], uncertainty_flags=decision.uncertainty_flags, recommended_action=decision.action, requires_human_review=decision.action != "approve")
