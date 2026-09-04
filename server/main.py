"""
RiskPilot AI - FastAPI Fraud Detection & Risk Analysis API.
Razorpay AI Buildathon Submission (Track 02 - AI Risk Manager).
"""

from datetime import datetime, timezone
import os
import uuid
from typing import Any, Dict, List, Optional, Literal

import uvicorn
from fastapi import FastAPI, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict

from server.risk_engine import RiskEngine
from server.audit_store import AuditStore, AuditEntry
from server.razorpay_integration import RazorpayIntegration
from server.v2_governance import AppendOnlyAudit, EvidenceV2, PolicyV2, RiskContextV2, ReviewRequestV2, DecisionV2, score_v2, summarize_v2
from razorpay.webhook_handler import RazorpayWebhookHandler
from llm.risk_analyst import RiskAnalyst


# Initialize FastAPI Application
app = FastAPI(
    title="RiskPilot AI - Fraud Detection API",
    description="Real-time AI Fraud Detection & Risk Manager API for Razorpay Payments.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.environ.get("CORS_ORIGINS", "*").split(",") if origin.strip()],
    allow_credentials=os.environ.get("CORS_ORIGINS", "*").strip() != "*",
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Core Services
risk_engine = RiskEngine()
audit_store = AuditStore()
v2_audit = AppendOnlyAudit()
razorpay_service = RazorpayIntegration()
webhook_handler = RazorpayWebhookHandler(
    webhook_secret=os.environ.get("RAZORPAY_WEBHOOK_SECRET"),
    risk_engine=risk_engine,
    audit_store=audit_store,
)
risk_analyst = RiskAnalyst()


# --- Pydantic Request & Response Models ---

class TransactionRequest(BaseModel):
    """
    Transaction data model for risk evaluation.
    """
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "transaction_id": "txn_987654321",
            "amount": 75000.0,
            "customer_id": "cust_88219",
            "device_id": "dev_macbook_pro_99",
            "location": "Mumbai, IN",
            "velocity": 6,
            "failed_attempts": 3,
            "account_age_days": 2,
            "merchant_id": "merch_fintech_01",
            "merchant_risk_score": 65.0,
            "behavioral_deviation": 0.82
        }
    })

    amount: float = Field(..., description="Transaction amount in INR", ge=0.0)
    customer_id: str = Field(..., description="Unique customer identifier")
    device_id: str = Field(..., description="Device fingerprint / ID")
    location: str = Field(..., description="Geographic location string (e.g., City, Country)")
    velocity: int = Field(..., description="Number of transactions in short window (e.g., 1 hour)", ge=0)
    failed_attempts: int = Field(..., description="Number of recent failed payment attempts", ge=0)
    account_age_days: int = Field(..., description="Age of customer account in days", ge=0)
    merchant_id: str = Field(..., description="Unique merchant identifier")
    merchant_risk_score: float = Field(..., description="Merchant risk rating (0-100)", ge=0.0, le=100.0)
    behavioral_deviation: float = Field(..., description="Deviation score from baseline user behavior (0.0 to 1.0)", ge=0.0, le=1.0)
    transaction_id: Optional[str] = Field(None, description="Optional custom transaction ID. Auto-generated if omitted.")


class RiskAnalysisResponse(BaseModel):
    """
    Risk analysis response model.
    """
    transaction_id: str
    risk_score: float = Field(..., description="Calculated risk score from 0.0 (safest) to 100.0 (highest risk)")
    risk_level: Literal["low", "medium", "high", "critical"] = Field(..., description="Categorical risk band")
    decision: Literal["approve", "review", "block"] = Field(..., description="Automated decision")
    reasons: List[str] = Field(..., description="Contributing risk factors and explanation reasons")
    confidence: Optional[float] = Field(None, description="Calibrated model confidence when available (0.0 - 1.0)")
    model_version: str = Field(..., description="Model or engine version used for scoring")
    timestamp: str = Field(..., description="ISO datetime UTC timestamp of evaluation")


class OverrideRequest(BaseModel):
    """
    Request model for human analyst override.
    """
    transaction_id: str = Field(..., description="Target transaction ID to override")
    human_decision: Literal["approve", "review", "block"] = Field(..., description="Analyst override decision")
    reason: str = Field(..., description="Explanation for human analyst override", min_length=3)
    analyst_id: Optional[str] = Field("analyst_001", description="Identifier of human analyst")


class OverrideResponse(BaseModel):
    """
    Response model for human analyst override action.
    """
    success: bool
    message: str
    audit_entry: AuditEntry


class RecentAuditResponse(BaseModel):
    """
    Response model for recent audit log entries.
    """
    total: int
    entries: List[AuditEntry]


class RazorpayOrderRequest(BaseModel):
    """
    Request model for creating a Razorpay test mode payment order with inline risk check.
    """
    amount: float = Field(..., description="Payment order amount in INR", ge=1.0)
    currency: str = Field("INR", description="Currency code (e.g. INR)")
    receipt: Optional[str] = Field(None, description="Receipt identifier")
    customer_id: str = Field(..., description="Customer ID")
    device_id: str = Field(..., description="Device fingerprint")
    location: str = Field(..., description="User location")
    velocity: int = Field(1, description="Transaction velocity in window", ge=0)
    failed_attempts: int = Field(0, description="Recent failed payment attempts", ge=0)
    account_age_days: int = Field(30, description="Customer account age in days", ge=0)
    merchant_id: str = Field("merch_123", description="Merchant ID")
    merchant_risk_score: float = Field(10.0, description="Merchant risk score (0-100)", ge=0.0, le=100.0)
    behavioral_deviation: float = Field(0.10, description="Behavioral deviation score (0.0 to 1.0)", ge=0.0, le=1.0)
    notes: Optional[Dict[str, str]] = Field(None, description="Custom metadata notes")


class RazorpayOrderResponse(BaseModel):
    """
    Response model for Razorpay payment order creation.
    """
    success: bool
    status: str
    message: str
    transaction_id: str
    order: Optional[Dict[str, Any]] = None
    risk_assessment: RiskAnalysisResponse
    test_mode_warning: Optional[str] = None


def normalize_assessment(assessment: Dict[str, Any], transaction_id: str, timestamp: Optional[str] = None) -> Dict[str, Any]:
    """Adapt the engine's internal score contract to the public API contract."""
    score = float(assessment.get("risk_score", assessment.get("score", assessment.get("fraud_risk_score", 0.0))))
    risk_level = str(assessment.get("risk_level", "medium")).lower()
    if risk_level not in {"low", "medium", "high", "critical"}:
        risk_level = "medium"
    decision = str(assessment.get("decision", assessment.get("recommended_action", "review"))).lower()
    if decision not in {"approve", "review", "block"}:
        decision = "review"
    return {
        **assessment,
        "transaction_id": transaction_id,
        "risk_score": round(score, 1),
        "score": round(score, 1),
        "risk_level": risk_level,
        "decision": decision,
        "reasons": list(assessment.get("reasons", [])),
        "confidence": assessment.get("confidence"),
        "timestamp": timestamp or assessment.get("timestamp") or datetime.now(timezone.utc).isoformat(),
    }


class InvestigationRequest(BaseModel):
    """Transaction context for a structured AI/rule-based investigation."""
    context: Dict[str, Any] = Field(default_factory=dict)


# --- Endpoints ---

@app.get("/v1/health", summary="Health Check Endpoint", tags=["System"])
async def health_check():
    """
    Health check endpoint for RiskPilot AI service monitoring.
    """
    return {
        "status": "ok",
        "service": "RiskPilot AI",
        "model_loaded": risk_engine.is_ml_loaded,
        "model_version": risk_engine.model_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/v1/integrations/status", summary="Integration configuration status", tags=["System"])
async def integration_status():
    """Return safe, non-secret readiness information for the live demo."""
    razorpay_configured = not razorpay_service.is_placeholder_key
    return {
        "api": {"status": "ready", "docs": "/docs"},
        "risk_engine": {"status": "ready", "model_loaded": risk_engine.is_ml_loaded, "model_version": risk_engine.model_version},
        "razorpay": {"status": "configured" if razorpay_configured else "simulation", "test_mode": True},
        "webhook": {"status": "configured" if bool(os.environ.get("RAZORPAY_WEBHOOK_SECRET")) else "not_configured", "signature": "HMAC-SHA256"},
        "llm": {"provider": getattr(risk_analyst, "_backend", "none"), "configured": risk_analyst.is_llm_active},
    }


@app.post("/v1/razorpay/webhook", summary="Verify and process Razorpay webhook", tags=["Razorpay Integration"])
async def razorpay_webhook(request: Request, x_razorpay_signature: Optional[str] = Header(default=None)):
    """Process only signature-verified Razorpay events and append them to the audit store."""
    raw_body = await request.body()
    response_body, response_status = webhook_handler.process_webhook(raw_body, signature=x_razorpay_signature)
    return JSONResponse(status_code=response_status, content=response_body)


@app.post("/v1/investigations/explain", summary="Generate structured investigation explanation", tags=["Risk Engine"])
async def explain_investigation(request: InvestigationRequest):
    """Run the configured LLM adapter with a deterministic defense-only fallback."""
    context = dict(request.context)
    transaction_id = str(context.get("transaction_id") or f"txn_{uuid.uuid4().hex[:12]}")
    context["transaction_id"] = transaction_id
    assessment = normalize_assessment(risk_engine.analyze_transaction(context), transaction_id)
    context.update(assessment)
    analysis = risk_analyst.analyze_transaction(context)
    return {"transaction_id": transaction_id, "risk": RiskAnalysisResponse(**assessment).model_dump(), "analysis": analysis}


@app.post("/v1/risk/analyze", response_model=RiskAnalysisResponse, summary="Analyze Transaction Risk", tags=["Risk Engine"])
async def analyze_risk(request: TransactionRequest):
    """
    Analyze a transaction payload for fraud risk using ML model scoring and rule bands.
    Records the decision automatically into the audit store.
    """
    try:
        txn_id = request.transaction_id or f"txn_{uuid.uuid4().hex[:12]}"
        txn_dict = request.model_dump()
        txn_dict["transaction_id"] = txn_id

        # Analyze transaction
        assessment = normalize_assessment(
            risk_engine.analyze_transaction(txn_dict),
            txn_id,
            datetime.now(timezone.utc).isoformat(),
        )

        # Log to audit store
        audit_store.record_decision(
            transaction_id=txn_id,
            risk_assessment=assessment,
            amount=request.amount,
            customer_id=request.customer_id,
            merchant_id=request.merchant_id,
        )

        return RiskAnalysisResponse(**assessment)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during risk analysis: {str(e)}"
        )


@app.post("/v1/risk/override", response_model=OverrideResponse, summary="Human Analyst Risk Override", tags=["Audit & Governance"])
async def override_risk(request: OverrideRequest):
    """
    Record a human analyst override for an AI risk decision.
    Updates the audit trail with analyst justification and timestamp.
    """
    if request.human_decision not in ("approve", "review", "block"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="human_decision must be one of: 'approve', 'review', 'block'."
        )

    updated_entry = audit_store.override_decision(
        transaction_id=request.transaction_id,
        human_decision=request.human_decision,
        reason=request.reason,
        analyst_id=request.analyst_id or "analyst_001",
    )

    if not updated_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction ID {request.transaction_id} not found in audit store."
        )

    return OverrideResponse(
        success=True,
        message=f"Decision for transaction {request.transaction_id} successfully overridden to '{request.human_decision.upper()}'.",
        audit_entry=updated_entry,
    )


@app.get("/v1/audit/recent", response_model=RecentAuditResponse, summary="Get Recent Audit Trail Entries", tags=["Audit & Governance"])
async def get_recent_audit(limit: int = Query(50, ge=1, le=500, description="Number of recent records to retrieve")):
    """
    Retrieves recent transaction audit trail entries (up to 500 max, default 50).
    Sorted with most recent decisions first.
    """
    entries = audit_store.get_recent_entries(limit=limit)
    return RecentAuditResponse(
        total=len(entries),
        entries=entries,
    )


@app.post("/v1/razorpay/create-payment", response_model=RazorpayOrderResponse, summary="Create Razorpay Order with Risk Pre-Screening", tags=["Razorpay Integration"])
async def create_razorpay_payment(request: RazorpayOrderRequest):
    """
    Runs transaction risk analysis before calling Razorpay test-mode API to create a payment order.
    Refuses order creation if AI decision is 'block'.
    """
    try:
        payload = request.model_dump()
        result = await razorpay_service.create_order_with_risk_check(
            order_payload=payload,
            risk_engine=risk_engine,
            audit_store=audit_store,
        )

        risk_assessment_data = normalize_assessment(
            result["risk_assessment"],
            result["transaction_id"],
            datetime.now(timezone.utc).isoformat(),
        )

        risk_response = RiskAnalysisResponse(**risk_assessment_data)

        # If order was blocked, set 403 Forbidden or 400 Bad Request status if requested or return structured payload
        return RazorpayOrderResponse(
            success=result["success"],
            status=result["status"],
            message=result["message"],
            transaction_id=result["transaction_id"],
            order=result["order"],
            risk_assessment=risk_response,
            test_mode_warning=result.get("test_mode_warning"),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process Razorpay payment order: {str(e)}"
        )


@app.post("/v2/risk/analyze", response_model=DecisionV2, summary="Governed explainable V2 risk decision", tags=["RiskPilot v2"])
async def analyze_risk_v2(request: RiskContextV2):
    decision = score_v2(request)
    v2_audit.append("RISK_DECISION", "risk_engine", decision.model_dump())
    return decision


@app.post("/v2/investigations/summary", response_model=dict, summary="Evidence-cited V2 investigation summary", tags=["RiskPilot v2"])
async def investigation_summary_v2(decision: DecisionV2, evidence: List[EvidenceV2] = []):
    return summarize_v2(decision, evidence).model_dump()


@app.post("/v2/governance/review", response_model=dict, summary="Rationale-required analyst review", tags=["RiskPilot v2"])
async def review_v2(request: ReviewRequestV2):
    event = v2_audit.append("ANALYST_REVIEW", request.case_id, request.model_dump(), request.case_id)
    return {"ok": True, "audit_event": event}


@app.get("/v2/audit", response_model=List[dict], summary="Append-only V2 audit events", tags=["RiskPilot v2"])
async def audit_v2():
    return v2_audit.list()


if __name__ == "__main__":
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)
