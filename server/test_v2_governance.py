from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from server.v2_governance import AppendOnlyAudit, EvidenceV2, PolicyV2, RiskContextV2, ReviewRequestV2, score_v2, summarize_v2


def test_score_is_deterministic_and_versioned():
    context = RiskContextV2(severity=96, exploit_likelihood=89, asset_criticality=96, exposure=100)
    decision = score_v2(context)
    assert decision.policy_version == "RP-2.4"
    assert decision.score == 95.05
    assert decision.action == "block"


def test_stale_evidence_abstains_safely():
    context = RiskContextV2(severity=90, exploit_likelihood=80, asset_criticality=80, exposure=90, evidence_count=1, freshest_evidence_age_hours=72)
    decision = score_v2(context)
    summary = summarize_v2(decision, [])
    assert decision.abstained is True
    assert summary.recommended_action == "abstain"
    assert summary.requires_human_review is True


def test_review_requires_meaningful_rationale():
    with pytest.raises(ValidationError):
        ReviewRequestV2(case_id="RP-1", decision="approve", rationale="short")


def test_audit_update_and_delete_are_rejected():
    audit = AppendOnlyAudit()
    audit.append("RISK_DECISION", "engine", {"score": 80})
    with pytest.raises(RuntimeError):
        audit.update("event")
    with pytest.raises(RuntimeError):
        audit.delete("event")
    assert len(audit.list()) == 1
