# RiskPilot AI — 3-Minute Judge Presentation Script

> **Razorpay AI Buildathon 2026** | **Track 02 — AI Risk Manager**
> **Repo:** [github.com/Himanshu90909/riskpilot-ai](https://github.com/Himanshu90909/riskpilot-ai)
> **Live app:** [riskpilot-ai-five.vercel.app/demo](https://riskpilot-ai-five.vercel.app/demo)

**One-click full flow:** with the backend running (`pnpm run api:dev`), execute the entire
closed loop in a single request and read the timeline top to bottom:

```bash
curl -X POST http://localhost:8000/v1/investigations/judge-run -H "Content-Type: application/json" -d '{}'
# → transaction → ML risk engine → agent tool calls → governance → Razorpay
#   → HMAC-verified webhook (when secret configured) → audit → risk profile update
```

Every step in the response carries a `mode` label: `real`, `razorpay_test_mode`,
`labeled_simulation`, or `not_configured_skipped`. Nothing is presented as more than it is.

---

## ⏱️ Timeline

### 0:00 — Problem

> "In payment gateways, merchants face a dilemma: block too aggressively and you create
> friction for good customers; block too loosely and account takeovers, card-testing
> botnets, and velocity attacks cost real money.
>
> Most fraud tools are post-transaction dashboards — opaque scores, after the money has moved."

**On screen:** landing page (`/`) — "Detect → Investigate → Decide → Protect", the
pre-checkout intervention point on the architecture diagram.

### 0:20 — RiskPilot Overview

> "RiskPilot AI is agentic payment-risk infrastructure. It sits **before** Razorpay order
> creation, evaluates customer, device, location, velocity, payment, behavior, and merchant
> signals, and decides APPROVE / REVIEW / BLOCK.
>
> Two things make it different: the numeric score is **deterministic** — ML model plus
> transparent rules — and the LLM only investigates, explains, and recommends. The LLM
> never invents the score."

**On screen:** `/app` executive overview. Note the KPI strip is **labeled synthetic demo
data** — the dashboard demonstrates the workflow, not production numbers.

### 0:40 — Live Transaction

> "Customer CUS_1029, ₹4,80,000 purchase. Signals arriving with the payment: first-seen
> device fingerprint, location anomaly, 12 transactions in the past hour, 5 failed
> payment attempts, 2-day-old account."

**On screen:** `/live` — enter the payload and click **Analyze transaction** (real FastAPI
call through the ML engine), or run the one-click judge flow above.

### 1:00 — AI Investigation

> "RiskPilot doesn't return a bare number — it runs a real investigation. The agent
> executes tool calls against live data: customer history, transaction history, device
> intelligence, location, velocity, merchant risk, account risk — then synthesizes the
> score with the deterministic engine and writes the case to the audit trail."

**On screen:** the `timeline` array from `/v1/investigations/run` — each tool call with
its **measured latency** (`risk_pilot.agent_tools`), or the 8-step tracker in `/demo`
(Demo Mode: deterministic, for reproducibility).

### 1:30 — Explainable Risk Score

> "For this transaction the live ML engine returns **99.5 / 100 — CRITICAL → BLOCK**
> (`ml_model_v1.0`, Gradient Boosting on 17 engineered features). The reasons are
> explicit: first-seen device, geographic anomaly, severe velocity spike, repeated
> authentication failures, high-value amount on a 2-day-old account.
>
> The guided demo shows the same decision via additive per-signal contributions
> (device, geo, velocity, failures, amount) — transparent bands: 0–30 LOW → APPROVE,
> 31–60 MEDIUM → REVIEW, 61–80 HIGH → REVIEW/STEP-UP, 81–100 CRITICAL → BLOCK."

**On screen:** decision card + contribution breakdown. Score source is always
`deterministic_ml_engine` — never the LLM.

### 1:50 — Governance & Razorpay Test Mode

> "Governance policy applies the band: CRITICAL → BLOCK, human review required, risk
> case opened with recorded reasons. Then the risk gateway acts on Razorpay:
> APPROVE creates the order, REVIEW creates it with risk notes, **BLOCK refuses order
> creation entirely**. Test Mode only — `rzp_test_*` keys, no real money."

**On screen:** `razorpay/demo_flow.py` terminal output, or the `razorpay_action` step in
the judge-run timeline. With credentials: `razorpay_test_mode`. Without: `labeled_simulation`
— never presented as a real remote payment.

### 2:10 — Webhook Verification

> "Payment events come back as webhooks. Every payload is verified with **HMAC-SHA256**
> using constant-time comparison, and duplicate deliveries are ignored via
> idempotency fingerprints — same event redelivered, no double processing. Verified
> events update the customer risk profile and land in the audit trail."

**On screen:** in the judge-run response, `webhook_verification` shows
`real_hmac_on_labeled_test_event` when `RAZORPAY_WEBHOOK_SECRET` is set (real HMAC check
against a locally generated, clearly labeled test event), or
`not_configured_skipped` — never faked.

### 2:30 — Audit Trail

> "Everything is recorded: risk calculation, agent investigation, Razorpay action, webhook
> verification, profile update, and any human override — AI decision, human decision,
> reason, actor, timestamp, transaction ID. Append-only. A compliance reviewer can
> reconstruct any payment decision end to end."

**On screen:** `GET /v1/audit/recent` in `/live` (Load audit), or the Audit Center in `/demo`.

### 2:45 — Business Impact

> "Our evaluation is honest and reproducible. On a 20,000-record held-out **synthetic**
> set: the Track 02 ATO detector hits 93.35% precision / 88.97% recall / 91.11% F1
> (`node evaluation/run.mjs`); the Gradient Boosting model hits 90.82% / 89.08% / 89.94%
> with a 0.52% false-positive rate (`python ml/run_evaluation.py`). A public-dataset
> benchmark against real Kaggle credit-card data is included for external validity
> (`ml/benchmark_public.py`). Synthetic results are labeled synthetic — they demonstrate
> the approach, not production fraud rates."

### 3:00 — Closing

> **"RiskPilot doesn't just detect risky payments. It investigates them, explains why
> they're risky, takes controlled action, and creates a complete auditable trail around
> the payment lifecycle."**

---

## Reproduce-everything commands

```bash
pip install -r server/requirements.txt && pnpm install
pnpm run api:dev                          # FastAPI backend (localhost:8000)
pnpm run dev                             # React frontend (localhost:3000)
pytest tests/ -v                         # full test suite (risk engine, webhook security, agent schema, API contract)
python razorpay/demo_flow.py             # 4-scenario Razorpay Test Mode gateway + webhook + audit
node evaluation/run.mjs                  # ATO detector benchmark (93.35 / 88.97 / 91.11)
python ml/run_evaluation.py              # ML model benchmark (90.82 / 89.08 / 89.94)
```
