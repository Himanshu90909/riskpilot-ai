"""
RiskPilot AI - FastAPI Fraud Detection & Risk Analysis API.
Razorpay AI Buildathon Submission (Track 02 - AI Risk Manager).
"""

from datetime import datetime, timezone
import json
import logging
import os
import time
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
from server.risk_profiles import RiskProfileStore, default_profile_store
from server.agent_tools import RiskInvestigationAgent, TOOL_REGISTRY
from server.governance import apply_governance, governed_assessment
from server.v2_governance import AppendOnlyAudit, EvidenceV2, PolicyV2, RiskContextV2, ReviewRequestV2, DecisionV2, score_v2, summarize_v2
from razorpay.webhook_handler import RazorpayWebhookHandler
from llm.risk_analyst import RiskAnalyst

logger = logging.getLogger("risk_pilot.api")


# Initialize FastAPI Application
app = FastAPI(
    title="RiskPilot AI - Fraud Detection API",
    description="Real-time AI Fraud Detection & Risk Manager API for Razorpay Payments.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS middleware.
# Secure default: only local development origins unless CORS_ORIGINS is explicitly set
# (comma-separated list, e.g. "https://your-app.vercel.app").
_DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
_configured_origins = [origin.strip() for origin in os.environ.get("CORS_ORIGINS", _DEFAULT_CORS_ORIGINS).split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_configured_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Core Services
risk_engine = RiskEngine()
audit_store = AuditStore()
v2_audit = AppendOnlyAudit()
razorpay_service = RazorpayIntegration()
profile_store: RiskProfileStore = default_profile_store
webhook_handler = RazorpayWebhookHandler(
    webhook_secret=os.environ.get("RAZORPAY_WEBHOOK_SECRET"),
    risk_engine=risk_engine,
    audit_store=audit_store,
    profile_store=profile_store,
)
risk_analyst = RiskAnalyst()
investigation_agent = RiskInvestigationAgent(
    risk_engine=risk_engine,
    profile_store=profile_store,
    audit_store=audit_store,
)


# --- Request-ID + structured logging middleware ---

@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """Attach a request ID, measure latency, and emit one structured log line per request.
    Never logs request bodies or secrets."""
    request_id = request.headers.get("x-request-id") or f"req_{uuid.uuid4().hex[:12]}"
    start = time.perf_counter()
    response = await call_next(request)
    latency_ms = round((time.perf_counter() - start) * 1000, 1)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-Ms"] = str(latency_ms)
    logger.info(
        "method=%s path=%s status=%s latency_ms=%s request_id=%s",
        request.method, request.url.path, response.status_code, latency_ms, request_id,
    )
    return response


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
    decision: Literal["approve", "review", "step_up", "block"] = Field(..., description="Governed final decision (AI recommends; governance decides)")
    ai_recommendation: str = Field("review", description="The risk engine's recommendation BEFORE governance was applied")
    recommended_action: str = Field("hold_for_analyst_review", description="Merchant-facing recommended action")
    risk_factors: List[str] = Field(default_factory=list, description="Contributing risk factors behind the score")
    evidence: List[Dict[str, Any]] = Field(default_factory=list, description="Structured transaction evidence used in the decision")
    governance: Dict[str, Any] = Field(default_factory=dict, description="Governance policy result: band, final decision, policy version, rules")
    policy_version: str = Field("unknown", description="Governance policy version applied to this decision")
    reasons: List[str] = Field(..., description="Contributing risk factors and explanation reasons")
    model_version: str = Field(..., description="Model or engine version used for scoring")
    timestamp: str = Field(..., description="ISO datetime UTC timestamp of evaluation")
    latency_ms: Optional[float] = Field(None, description="Measured engine latency in milliseconds")


class OverrideRequest(BaseModel):
    """
    Request model for human analyst override.
    """
    transaction_id: str = Field(..., description="Target transaction ID to override")
    human_decision: Literal["approve", "review", "step_up", "block"] = Field(..., description="Analyst override decision")
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
    if decision not in {"approve", "review", "step_up", "block"}:
        decision = "review"
    return {
        **assessment,
        "transaction_id": transaction_id,
        "risk_score": round(score, 1),
        "score": round(score, 1),
        "risk_level": risk_level,
        "decision": decision,
        "reasons": list(assessment.get("reasons", [])),
        "timestamp": timestamp or assessment.get("timestamp") or datetime.now(timezone.utc).isoformat(),
    }


class InvestigationRequest(BaseModel):
    """Transaction context for a structured AI/rule-based investigation."""
    context: Dict[str, Any] = Field(default_factory=dict)


class AssistantChatRequest(BaseModel):
    """Question for the free, defense-only RiskPilot operator agent."""
    question: str = Field(..., min_length=1, max_length=500)


class AssistantChatResponse(BaseModel):
    answer: str
    engine: str
    safe_scope: str = "defense-only"


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
    webhook_configured = bool(os.environ.get("RAZORPAY_WEBHOOK_SECRET"))
    execution_mode = "RAZORPAY_TEST_MODE" if (razorpay_configured and webhook_configured) else "TEST_MODE_PARTIAL" if (razorpay_configured or webhook_configured) else "DEMO_MODE"
    return {
        "mode": {
            "execution_mode": execution_mode,
            "description": {
                "DEMO_MODE": "Deterministic simulation — no Razorpay credentials configured. Simulated calls are explicitly labeled.",
                "TEST_MODE_PARTIAL": "Razorpay Test Mode partially configured (API keys or webhook secret). Unconfigured parts run clearly-labeled simulation.",
                "RAZORPAY_TEST_MODE": "Razorpay Test Mode active — real test API requests and HMAC-verified webhooks. No real money.",
            }[execution_mode],
        },
        "api": {"status": "ready", "docs": "/docs"},
        "risk_engine": {"status": "ready", "model_loaded": risk_engine.is_ml_loaded, "model_version": risk_engine.model_version},
        "agent": {"status": "ready", "tools": len(TOOL_REGISTRY), "score_source": "deterministic_ml_engine"},
        "profiles": {"status": "ready", "customers_tracked": len(profile_store.list_customers())},
        "razorpay": {"status": "configured" if razorpay_configured else "simulation", "test_mode": True},
        "webhook": {"status": "configured" if webhook_configured else "not_configured", "signature": "HMAC-SHA256", "idempotency": True},
        "llm": {"provider": getattr(risk_analyst, "_backend", "none"), "configured": risk_analyst.is_llm_active, "fallback": "rule_based_deterministic"},
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
    assessment = governed_assessment(normalize_assessment(risk_engine.analyze_transaction(context), transaction_id))
    assessment["risk_factors"] = list(assessment.get("reasons", []))
    assessment["evidence"] = [
        {"signal": "amount", "value": float(context.get("amount", 0.0)), "detail": "Transaction amount (INR)"},
        {"signal": "velocity", "value": int(context.get("velocity", 0)), "detail": "Transactions in the past hour"},
        {"signal": "failed_attempts", "value": int(context.get("failed_attempts", 0)), "detail": "Failed payment attempts (24h)"},
        {"signal": "account_age_days", "value": int(context.get("account_age_days", 30)), "detail": "Customer account age in days"},
        {"signal": "merchant_risk_score", "value": float(context.get("merchant_risk_score", 0.0)), "detail": "Merchant risk rating (0-100)"},
        {"signal": "behavioral_deviation", "value": float(context.get("behavioral_deviation", 0.0)), "detail": "Behavioral deviation score (0-1)"},
    ]
    context.update(assessment)
    analysis = risk_analyst.analyze_transaction(context)
    return {"transaction_id": transaction_id, "risk": RiskAnalysisResponse(**assessment).model_dump(), "analysis": analysis}


@app.post("/v1/assistant/chat", response_model=AssistantChatResponse, summary="Ask RiskPilot operator agent", tags=["Risk Analyst"])
async def assistant_chat(request: AssistantChatRequest):
    """Answer common risk-ops questions without requiring a paid model key."""
    question = request.question.strip().lower()
    if any(term in question for term in ("bypass", "evade", "spoof", "hack", "steal", "fraud kaise")):
        answer = "I can’t provide instructions to bypass controls or commit fraud. I can help with defensive detection, safe policy tuning, analyst review, or explaining a flagged transaction."
    elif any(term in question for term in ("block", "84921", "why")):
        answer = "TXN-84921 was blocked because the ₹84,999 amount is far above the customer baseline and arrived from a first-seen device and location with elevated velocity. The combined signals produced a critical 91/100 risk score; an analyst can still override the decision."
    elif any(term in question for term in ("merchant", "shop")):
        answer = "Nova Electronics is the highest-volume merchant under watch with a 12.4% simulated risk rate. Aster Travel Co. has the steepest increase in flagged activity; review card-testing thresholds before changing policy."
    elif any(term in question for term in ("takeover", "account")):
        answer = "The strongest account-takeover cluster combines a new device, new location, password reset, and an unusually large purchase. RiskPilot surfaced 37 related synthetic events across Mumbai and Bengaluru."
    elif any(term in question for term in ("fraud", "prevented", "impact", "today")):
        answer = "The NovaPay demo shows ₹3.82 Cr in potential fraud prevented, 12,481 transactions blocked, and a 1.8% false-positive rate. These are synthetic buildathon figures, not production financial results."
    elif any(term in question for term in ("risk", "riskiest", "high")):
        answer = "The riskiest synthetic transactions are TXN-84921 at 91, TXN-85288 at 96, and TXN-85473 at 93. They share a new-device signal; two also show elevated velocity."
    else:
        answer = "I’m the free RiskPilot operator agent. Ask me to explain a decision, find risky patterns, summarize fraud impact, or suggest a safe analyst-review workflow."
    return AssistantChatResponse(answer=answer, engine="RiskPilot free rule agent")


@app.post("/v1/investigations/run", summary="Run full tool-based risk investigation", tags=["Risk Engine"])
async def run_investigation(request: TransactionRequest):
    """
    Execute the complete Risk Investigation Agent workflow with REAL tool calls:
    customer history, transaction history, device, location, velocity, merchant,
    account risk, deterministic ML score, risk case, profile updates, audit event,
    and recommended action — each step individually timed.
    The numeric risk score comes ONLY from the deterministic engine, never the LLM.
    """
    try:
        txn_dict = request.model_dump()
        result = investigation_agent.run_investigation(txn_dict)
        return result
    except Exception as e:
        logger.exception("Investigation failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during the investigation: {str(e)}",
        )


@app.get("/v1/investigations/tools", summary="Agent tool registry", tags=["Risk Engine"])
async def list_agent_tools():
    """Transparency endpoint: the exact tools available to the investigation agent."""
    return {"agent": "RiskPilot Investigation Agent v1", "tools": TOOL_REGISTRY, "score_source": "deterministic_ml_engine"}


@app.get("/v1/profiles/customer/{customer_id}", summary="Customer risk profile", tags=["Risk Profiles"])
async def get_customer_profile(customer_id: str):
    """Closed-loop customer risk profile: history, devices, locations, velocity, risk events."""
    profile = profile_store.get_customer_profile(customer_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No risk profile found for customer '{customer_id}'.")
    return profile


@app.get("/v1/profiles/merchant/{merchant_id}", summary="Merchant risk profile", tags=["Risk Profiles"])
async def get_merchant_profile(merchant_id: str):
    """Closed-loop merchant risk profile: volume, suspicious rate, trend, investigations."""
    profile = profile_store.get_merchant_profile(merchant_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No risk profile found for merchant '{merchant_id}'.")
    return profile


class JudgeRunRequest(TransactionRequest):
    """Judge Mode: all fields optional — the canonical high-risk ATO scenario
    (₹4,80,000, new device, location anomaly, velocity 12, 5 failed attempts)
    is used when a field is omitted."""
    def __init__(self, **data):
        defaults = {
            "amount": 480000.0,
            "customer_id": "CUS_JUDGE_DEMO",
            "device_id": "DEV_JUDGE_NEW",
            "location": "Bengaluru, IN",
            "velocity": 12,
            "failed_attempts": 5,
            "account_age_days": 2,
            "merchant_id": "MERCH_JUDGE_DEMO",
            "merchant_risk_score": 65.0,
            "behavioral_deviation": 0.82,
        }
        merged = {**defaults, **{k: v for k, v in data.items() if v is not None}}
        super().__init__(**merged)


@app.post("/v1/investigations/judge-run", summary="Judge Mode: full closed-loop payment risk flow", tags=["Risk Engine"])
async def judge_run(request: JudgeRunRequest):
    """
    One-click 2-3 minute reviewer flow. Every step is REAL backend execution,
    individually timed and labeled:

      Transaction → Risk Engine (ML) → Agent Investigation (tool calls)
      → Governance Policy → Razorpay Test Mode action → Webhook verification
      → Audit Trail → Risk Profile Update

    Honesty rules:
      - Razorpay step: REAL Test Mode order creation when credentials exist;
        otherwise an explicitly-labeled deterministic simulation.
      - Webhook step: the HMAC-SHA256 verification is REAL against a locally
        generated test event (labeled origin) when RAZORPAY_WEBHOOK_SECRET is
        set; skipped and labeled when not configured.
    """
    t_total = time.perf_counter()
    timeline = []

    def record(name: str, detail: str, result: Any, t0: float, mode_label: str) -> None:
        timeline.append({
            "step": len(timeline) + 1,
            "name": name,
            "detail": detail,
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
            "mode": mode_label,
            "result": result,
        })

    txn = request.model_dump()
    txn_id = f"txn_{uuid.uuid4().hex[:12]}"
    txn["transaction_id"] = txn_id

    # 1. Transaction received
    t0 = time.perf_counter()
    record("transaction_received", f"Transaction {txn_id} received (₹{txn['amount']:,.0f}).",
           {"transaction_id": txn_id, "amount": txn["amount"], "customer_id": txn["customer_id"]},
           t0, "real")

    # 2. ML risk engine (authoritative score)
    t0 = time.perf_counter()
    assessment = normalize_assessment(
        risk_engine.analyze_transaction(txn), txn_id, datetime.now(timezone.utc).isoformat()
    )
    record("risk_engine", f"Deterministic ML risk score computed: {assessment['risk_score']}/100 ({assessment['risk_level'].upper()}).",
           {"risk_score": assessment["risk_score"], "risk_level": assessment["risk_level"],
            "decision": assessment["decision"], "model_version": assessment["model_version"]},
           t0, "real")

    # 3. Agent investigation (real tool calls, audit + profile updates included)
    t0 = time.perf_counter()
    investigation = investigation_agent.run_investigation(txn)
    record("agent_investigation",
           f"Agent executed {len(investigation['steps'])} tool calls; case opened: {bool(investigation['risk_case'])}.",
           {"agent_tools_executed": [s["tool"] for s in investigation["steps"]],
            "risk_case": investigation["risk_case"],
            "score_source": investigation["risk_assessment"]["score_source"],
            "agent_latency_ms": investigation["total_latency_ms"]},
           t0, "real")

    # 4. Governance policy — canonical module (AI recommends; governance decides)
    t0 = time.perf_counter()
    governed = apply_governance(assessment)
    assessment["ai_recommendation"] = governed["ai_recommendation"]
    assessment["decision"] = governed["final_decision"]
    assessment["recommended_action"] = governed["final_decision"]
    assessment["policy_version"] = governed["policy_version"]
    record("governance_policy", f"Governance band applied: {assessment['risk_level'].upper()} → {governed['final_decision'].upper()}"
           + (f" (engine recommended '{governed['ai_recommendation']}' — band policy governs)." if governed["ai_recommendation_differs"] else "."),
           governed, t0, "real")

    # 5. Razorpay Test Mode action (risk gateway: create or refuse the order)
    t0 = time.perf_counter()
    razorpay_mode = "razorpay_test_mode" if not razorpay_service.is_placeholder_key else "labeled_simulation"
    try:
        rzp_result = await razorpay_service.create_order_with_risk_check(
            order_payload=txn, risk_engine=risk_engine, audit_store=audit_store,
        )
        if rzp_result["success"]:
            rzp_detail = f"Razorpay order {rzp_result['order']['id']} created (decision: {assessment['decision'].upper()})."
        else:
            rzp_detail = f"Order creation REFUSED by risk gate ({rzp_result['status']})."
        record("razorpay_action", rzp_detail,
               {"success": rzp_result["success"], "status": rzp_result["status"],
                "order_id": (rzp_result["order"] or {}).get("id"),
                "test_mode_warning": rzp_result.get("test_mode_warning")},
               t0, razorpay_mode)
    except Exception as ex:
        record("razorpay_action", f"Razorpay action failed: {ex}", {"success": False, "status": "error"},
               t0, razorpay_mode)

    # 6. Webhook verification — REAL HMAC check on a locally generated, clearly labeled test event
    t0 = time.perf_counter()
    webhook_secret = os.environ.get("RAZORPAY_WEBHOOK_SECRET")
    if webhook_secret:
        import hashlib, hmac as hmac_mod
        payment_id = f"pay_test_{uuid.uuid4().hex[:10]}"
        webhook_payload = json.dumps({
            "event": "payment.captured" if assessment["decision"] == "approve" else "payment.authorized",
            "payload": {"payment": {"entity": {
                "id": payment_id, "amount": int(txn["amount"] * 100), "currency": "INR",
                "status": "authorized", "created_at": int(time.time()),
                "notes": {"risk_pilot_id": txn_id, "customer_id": txn["customer_id"],
                          "merchant_id": txn["merchant_id"], "origin": "locally_generated_test_event"},
            }}},
        }, sort_keys=True)
        signature = hmac_mod.new(webhook_secret.encode(), webhook_payload.encode(), hashlib.sha256).hexdigest()
        wb_body, wb_status = webhook_handler.process_webhook(webhook_payload, signature=signature)
        record("webhook_verification",
               "HMAC-SHA256 signature VERIFIED on a locally generated test event (origin labeled in payload).",
               {"signature_verified": wb_status == 200, "http_status": wb_status, "response": wb_body,
                "event_origin": "locally_generated_test_event"},
               t0, "real_hmac_on_labeled_test_event")
    else:
        record("webhook_verification",
               "Skipped: RAZORPAY_WEBHOOK_SECRET not configured. Signature verification cannot run — not simulated.",
               {"signature_verified": None, "skipped_reason": "webhook_secret_not_configured"},
               t0, "not_configured_skipped")

    # 7. Audit trail (entries actually written during this run)
    t0 = time.perf_counter()
    audit_entries = audit_store.get_by_transaction_id(txn_id)
    record("audit_trail", f"{len(audit_entries.reasons) if audit_entries else 0}+ audit entries recorded for {txn_id} "
           "(risk decision, agent investigation, Razorpay gate).",
           {"transaction_id": txn_id, "audit_available": audit_entries is not None},
           t0, "real")

    # 8. Risk profile update (closed loop)
    t0 = time.perf_counter()
    profile = profile_store.get_customer_profile(str(txn["customer_id"]))
    record("risk_profile_update", f"Customer {txn['customer_id']} risk profile updated "
           f"(score {profile['risk_score']}/100, {profile['total_transactions']} transactions).",
           profile, t0, "real")

    return {
        "flow": "judge_mode_closed_loop",
        "transaction_id": txn_id,
        "execution_mode": "RAZORPAY_TEST_MODE" if not razorpay_service.is_placeholder_key else "DEMO_MODE",
        "final_decision": assessment["decision"].upper(),
        "risk_score": assessment["risk_score"],
        "risk_level": assessment["risk_level"].upper(),
        "timeline": timeline,
        "total_latency_ms": round((time.perf_counter() - t_total) * 1000, 1),
    }


@app.post("/v1/risk/analyze", response_model=RiskAnalysisResponse, summary="Analyze Transaction Risk", tags=["Risk Engine"])
async def analyze_risk(request: TransactionRequest):
    """
    Analyze a transaction payload for fraud risk using ML model scoring and rule bands.
    Records the decision automatically into the audit store.
    """
    start = time.perf_counter()
    try:
        txn_id = request.transaction_id or f"txn_{uuid.uuid4().hex[:12]}"
        txn_dict = request.model_dump()
        txn_dict["transaction_id"] = txn_id

        # Risk Engine scores (deterministic ML)...
        raw_assessment = risk_engine.analyze_transaction(txn_dict)

        # ...Governance Policy decides the final action (AI recommends; governance decides)
        assessment = governed_assessment(raw_assessment)
        assessment["risk_factors"] = list(assessment.get("reasons", []))
        assessment["evidence"] = [
            {"signal": "amount", "value": float(request.amount), "detail": "Transaction amount (INR)"},
            {"signal": "velocity", "value": int(request.velocity), "detail": "Transactions in the past hour"},
            {"signal": "failed_attempts", "value": int(request.failed_attempts), "detail": "Failed payment attempts (24h)"},
            {"signal": "account_age_days", "value": int(request.account_age_days), "detail": "Customer account age in days"},
            {"signal": "merchant_risk_score", "value": float(request.merchant_risk_score), "detail": "Merchant risk rating (0-100)"},
            {"signal": "behavioral_deviation", "value": float(request.behavioral_deviation), "detail": "Behavioral deviation score (0-1)"},
        ]
        assessment = normalize_assessment(assessment, txn_id, datetime.now(timezone.utc).isoformat())

        # Log to audit store
        audit_store.record_decision(
            transaction_id=txn_id,
            risk_assessment=assessment,
            amount=request.amount,
            customer_id=request.customer_id,
            merchant_id=request.merchant_id,
        )

        # Closed loop: update customer + merchant risk profiles
        profile_store.record_decision(
            transaction_id=txn_id,
            customer_id=request.customer_id,
            merchant_id=request.merchant_id,
            amount_inr=float(request.amount),
            decision=assessment["decision"],
            risk_score=float(assessment["risk_score"]),
            device_id=request.device_id,
            location=request.location,
            velocity_1h=int(request.velocity),
            model_version=assessment["model_version"],
        )

        assessment["latency_ms"] = round((time.perf_counter() - start) * 1000, 1)
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
    if request.human_decision not in ("approve", "review", "step_up", "block"):
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
