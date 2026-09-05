> **Built and submitted by Himanshu Suthar**
>
> GitHub owner: [Himanshu90909](https://github.com/Himanshu90909)  
> Live demo: [riskpilot-ai-five.vercel.app/demo](https://riskpilot-ai-five.vercel.app/app)
>
> Pitch walkthrough: [working platform video](https://files.manuscdn.com/user_upload_by_module/session_file/310519663815895274/AxlHmfIynAgdoPel.webm)

# RiskPilot AI

> **Agentic Payment-Risk Infrastructure for Digital Payments**

RiskPilot AI is a startup-style fintech SaaS for the AI Risk Manager track. It sits between a digital commerce system and the payment decision, investigating suspicious activity across customer, device, location, velocity, payment, behavior, and merchant signals before deciding **approve**, **review**, or **block** — then executing a controlled action and maintaining an auditable risk trail.

RiskPilot is **not** a dashboard that only predicts fraud. It is a decision layer that runs *before* a Razorpay order is created, refuses or flags the order based on risk, receives the payment webhook, and closes the loop with an append-only audit trail.

## Two execution modes

RiskPilot runs in **two clearly separated modes**:

```text
DEMO MODE (default, zero-setup)
→ Deterministic synthetic data
→ No credentials or backend required
→ Same walkthrough every time — reproducible judging

LIVE TEST MODE (FastAPI backend)
→ Real FastAPI service (`server/`)
→ ML risk engine (`ml/`) loaded at boot
→ LLM investigation agent (`llm/`) — Gemini/Groq, deterministic fallback
→ Razorpay Test Mode APIs (`razorpay/`) — real requests, test keys, no real money
→ HMAC-SHA256 webhook verification → risk profile update → audit trail
```

Demo Mode powers the guided `/demo` walkthrough so the judge experience starts instantly and is fully deterministic. Live Test Mode proves the same decisions run through a real API service — the `/live` page exercises it end-to-end. **Both modes use the same risk engine logic; Demo Mode embeds it client-side for reproducibility, Live Test Mode serves it over FastAPI with the ML model.**

## What is implemented

| Area | Included |
|---|---|
| Landing page | Product positioning, "Detect → Investigate → Decide → Protect" story, evidence-first case file visual |
| Executive overview | KPI strip, fraud prevention trend, risk distribution chart, priority queue, agent summary |
| Transaction intelligence | Search, risk-level filter, decision filter, 100 deterministic transactions, clickable drawer |
| AI investigations | Risk ring, per-signal contributions, investigation timeline, explanation, model/version metadata, human-in-the-loop actions |
| Risk intelligence | Detection vs. exposure trend, risk category breakdown, signal topology, model readout |
| Fraud patterns | Account takeover, card testing, velocity attack, and friendly fraud clusters |
| Customer profiles | 30 profiles with risk score, account age, devices, locations, failed payments, events |
| Merchant intelligence | 15 merchants with risk rate, fraud rate, blocked amount, trend bars, health status |
| Rules | Toggleable risk rules with enable/disable feedback and transparent score bands |
| Simulation Lab | Account takeover, card testing, velocity attack, friendly fraud scenarios |
| Audit Center | Searchable decision records with AI decision, human decision, action, timestamp, model version |
| Developer API | **Live** `POST /v1/risk/analyze` via FastAPI (Live Test Mode), with simulated JSON in Demo Mode |
| Risk Analyst | LLM-backed investigation agent (Live Test Mode) with deterministic fallback (Demo Mode) |
| Razorpay integration | Test Mode order creation, payment links, webhook handling, HMAC-SHA256 verification |
| Pricing | UI-only pricing presentation; no billing integration |

## Architecture

```text
Customer checkout
      ↓
Transaction context
      ↓
┌─────────────────────────────────────────┐
│  RISKPILOT AGENT (8-step investigation) │
│  1. Customer history                     │
│  2. Device reputation                    │
│  3. Geographic behavior                  │
│  4. Velocity analysis                    │
│  5. Payment behavior                     │
│  6. Merchant signals                     │
│  7. ML risk score synthesis              │
│  8. LLM investigation + explanation      │
└───────────────┬─────────────────────────┘
                ↓
        ML RISK ENGINE (deterministic, versioned)
                ↓
   ┌────────────┼────────────┐
   LOW        MEDIUM       HIGH/CRITICAL
   ↓            ↓               ↓
APPROVE      REVIEW/         BLOCK
(Razorpay    step-up        (refuse order,
order        verify          open risk case,
created)     flow            alert analyst)
   ↓            ↓               ↓
┌─────────────────────────────────────────┐
│  CONTROLLED AGENT ACTIONS                │
│  Block · open case · record evidence ·   │
│  alert analyst · request verification · │
│  update customer risk state              │
└───────────────┬─────────────────────────┘
                ↓
        Razorpay Test Mode API
                ↓
        Razorpay webhook
                ↓
HMAC-SHA256 signature verification
                ↓
Risk event processor → update risk profile
                ↓
        Append-only audit trail
                ↓
  Agent learns new signal (closed loop)
```

**Key design rule:** the LLM never decides the numeric risk score. **ML/rules produce the score and evidence; the LLM produces the investigation narrative, explanation, and recommended action.** This keeps decisions deterministic, explainable, and defensible — the LLM augments, it doesn't govern.

## Tech stack

- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS 4, Wouter, Recharts, shadcn/ui primitives
- **Backend:** FastAPI (Python), HMAC-SHA256 webhook verification, append-only audit store
- **ML:** scikit-learn Gradient Boosting (trained on 100K synthetic transactions), deterministic weighted-signal engine
- **LLM:** Google Gemini / Groq (auto-detected) with a rule-based deterministic fallback — always available, no key required

The frontend starts instantly with no backend required (Demo Mode). The full stack runs with `pnpm run api:dev` (Live Test Mode).

## Setup

### Demo Mode (frontend only, zero setup)

```bash
pnpm install
pnpm run dev
```

Open `http://localhost:3000`.

### Live Test Mode (full stack)

```bash
pnpm install
pip install -r server/requirements.txt
pnpm run api:dev     # FastAPI on :8000
pnpm run dev         # Vite on :3000
```

Open `http://localhost:3000/live`. Set `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, and `RAZORPAY_WEBHOOK_SECRET` to use real Razorpay Test Mode APIs. Without credentials the Razorpay endpoints explicitly report deterministic simulation — they never present a fake remote payment as real.

For a production build:

```bash
pnpm run check
pnpm run build
pnpm run start
```

## Demo access

No login is required. Open the landing page and select **Open demo**. The fictional workspace is **NovaPay** and the demo operator is **Himanshu Suthar · Admin**.

Recommended walkthrough:

1. Open `/demo` first. Let the guided investigation run so the reviewer sees the risk score, evidence trail, decision monitor, and model readout build in real time.
2. Open **Overview** and call out `₹3.82 Cr` potential fraud prevented, `12,481` blocked transactions, and the `42 ms` median decision time.
3. Open the first priority transaction, `TXN-84921`, for Rahul Mehta at Nova Electronics.
4. Open **AI Investigation** and show the `91 / 100 · CRITICAL` score, per-signal contributions, timeline, and explanation.
5. Use **Keep blocked**, **Approve anyway**, or **Request verification** to demonstrate responsible AI and human accountability.
6. Open **Simulations**, run **Account Takeover**, and show the deterministic `94 / 100 · BLOCK · ₹4.8L` result.
7. Point to the held-out evaluation evidence in the guided demo (see the unified evaluation table below).
8. Finish in **Developer API** — and if running Live Test Mode, execute a real `POST /v1/risk/analyze` request from `/live` and show the result.

## Live API demonstration

The endpoint is **live** in Live Test Mode:

```http
POST /v1/risk/analyze
```

Example request:

```json
{
  "amount": 480000,
  "customer_id": "CUS_1029",
  "device_id": "DEV_8821",
  "velocity": 12,
  "failed_attempts": 5,
  "account_age_days": 2,
  "merchant_risk_score": 65,
  "behavioral_deviation": 0.82
}
```

Real response (from the running FastAPI service):

```json
{
  "transaction_id": "txn_53515ca5ce18",
  "risk_score": 99.5,
  "risk_level": "critical",
  "decision": "block",
  "reasons": [
    "High-value transaction amount (₹480,000.00)",
    "Severe velocity spike (12 attempts in past hour)",
    "Multiple recent payment failures (5 in 24h)"
  ],
  "model_version": "ml_model_v1.0"
}
```

The `/live` page exercises the full loop: health check → risk analyze → Razorpay order creation (Test Mode) → webhook with HMAC verification → audit retrieval.

## Evaluation — one table, one methodology per metric

All evaluation results are reproducible from the repository. **Each number below comes from exactly one evaluation, clearly labeled.** Synthetic data is used for demo reproducibility; the public-dataset benchmark grounds the model against real-world fraud data.

| # | Evaluation | Dataset | Model | Precision | Recall | F1 | Reproduce |
|---|---|---|---|---:|---:|---:|---|
| 1 | Track 02 ATO detector (`evaluation/run.mjs`) | 100K synthetic, 20K held out | Weighted-signal detector, threshold 24 | 93.35% | 88.97% | 91.11% | `node evaluation/run.mjs` |
| 2 | ML model, held-out (`ml/`) | 100K synthetic, 20K held out | Gradient Boosting (primary) | 90.82% | 89.08% | 89.94% | `python ml/run_evaluation.py` |
| 2b | ML baseline (`ml/`) | Same | Logistic Regression | 86.76% | 89.44% | 88.08% | `python ml/run_evaluation.py` |
| 3 | Public-dataset benchmark (`ml/benchmark_public.py`) | Kaggle Credit Card Fraud (real) | Same Gradient Boosting | see `ml/public_benchmark.json` | | | see below |

- **Evaluation 1** measures the deterministic weighted-signal detector that backs the guided demo and the score-band policy.
- **Evaluation 2** measures the scikit-learn Gradient Boosting model that powers the Live Test Mode risk engine (`ml_model_v1.0`).
- **Evaluation 3** validates the same model against a real, publicly available fraud dataset so results aren't only synthetic. Download `creditcard.csv` from the Kaggle Credit Card Fraud Detection dataset, place it in `ml/data/`, then run:

```bash
python ml/benchmark_public.py
```

### Track 02 ATO detector detail (Evaluation 1)

`evaluation/run.mjs` is the reproducible evaluation entry point. It keeps data generation, detector logic, threshold, cost model, and metrics in code so a reviewer can rerun the result instead of trusting a screenshot. `evaluation/results.json` is the generated artifact used by the guided UI.

- Held-out set: 20,000 records (of 100,000 generated; seed-locked deterministic generator)
- Precision **93.35%**, recall **88.97%**, F1 **91.11%**, false-positive rate **3.53%**
- Confusion matrix: 6,363 TP · 453 FP · 789 FN · 12,395 TN
- False-positive cost ₹81,540, missed-loss ₹9,46,800 under documented synthetic cost assumptions (FP ₹180 / FN ₹1,200)

Every synthetic-data result is labeled as such and should not be read as a production fraud estimate.

## Risk engine & explainability

The engine accepts transaction amount, device state, location state, velocity, failed attempts, account age, merchant risk, and behavioral deviation. Each input contributes a **visible, additive weight** — a judge can always see exactly why a transaction scored what it did:

```text
91 / 100 · CRITICAL

Risk contribution
Transaction amount        +22   (₹84,999 vs customer baseline)
New device                +18   (first-seen fingerprint)
Location anomaly          +16   (Mumbai → new geo)
Velocity                  +12   (5+ txns in window)
Failed attempts           +15   (3 consecutive failures)
Account age                +4
Merchant risk             +12
Behavioral deviation       +4
─────────────────────────────
TOTAL                     91    → BLOCK
```

| Score | Level | Default decision |
|---:|---|---|
| 0–30 | LOW | APPROVE |
| 31–60 | MEDIUM | REVIEW |
| 61–80 | HIGH | REVIEW / STEP-UP |
| 81–100 | CRITICAL | BLOCK |

The score is deterministic so the same walkthrough always produces the same evidence. In Live Test Mode the identical logic runs server-side behind `POST /v1/risk/analyze`, backed by `ml_model_v1.0`.

## AI agent architecture

The RiskPilot Agent is an agentic investigator. A suspicious transaction moves through an 8-step pipeline — customer history, device reputation, geographic behavior, velocity, payment behavior, merchant signals, score synthesis, and explanation generation — then **executes controlled actions**: block transaction, create risk case, record evidence, alert analyst, request step-up verification, and update the customer risk state.

- **Demo Mode** represents the steps with deterministic data and UI timing so judging is reproducible.
- **Live Test Mode** runs the real implementation: `llm/investigation_agent.py` orchestrates the 8-step pipeline, `llm/risk_analyst.py` calls Gemini or Groq for the investigation narrative (with a deterministic rule-based fallback that requires no API key), and `llm/explanation_generator.py` guarantees an explanation is always produced.

The LLM never sets the numeric score — ML/rules produce evidence, the LLM produces investigation, explanation, and recommended action. The agent is defense-only: embedded system prompts refuse any bypass/fraud-assistance requests.

## Razorpay integration (Test Mode)

`razorpay/` is a real Razorpay Test Mode integration module:

- **Order creation, payment links, payment fetching, settlements, capture** — `razorpay/client.py` (auto-detects credentials; explicit mock mode when absent)
- **Risk Gateway** — `razorpay/risk_gateway.py` runs the risk engine *before* order creation: APPROVE → create order, REVIEW → create order with risk notes, BLOCK → refuse order and return the risk assessment
- **Webhook handler** — `razorpay/webhook_handler.py` verifies HMAC-SHA256 signatures for `payment.authorized`, `payment.failed`, `order.paid`, then updates risk profiles and writes the audit trail

```bash
pip install -r razorpay/requirements.txt
python razorpay/demo_flow.py     # end-to-end: 4 scenarios + webhook + audit trail
```

Razorpay Test Mode is used exclusively — no real money, cards, or settlements. Run `razorpay/demo_flow.py` to see the full closed loop: transaction → risk decision → order creation/refusal → webhook → HMAC verification → audit trail.

## Project structure

```text
client/                  # React 19 + Vite frontend (Demo Mode)
  src/pages/Home.tsx     # Landing, app shell, routes, feature views
  src/lib/mockData.ts    # Synthetic entities, charts, risk engine, guided demo
server/                  # FastAPI service (Live Test Mode)
  main.py                # /v1/risk/analyze, Razorpay, webhook, audit, LLM endpoints
  risk_engine.py         # ML-backed risk scoring
  v2_governance.py       # Append-only audit, evidence, human override
ml/                      # Model training + evaluation + public benchmark
llm/                     # Gemini/Groq investigation agent + deterministic fallback
razorpay/                # Razorpay Test Mode client, risk gateway, webhook handler
evaluation/              # Track 02 reproducible evaluator (node evaluation/run.mjs)
demo/                    # Terminal demo scripts + 5-minute pitch script
api/index.py             # Vercel entrypoint for the FastAPI service
```

## Design system

RiskPilot uses the **Editorial Trust Layer** direction: Swiss-inspired hierarchy, deep ink navigation, warm paper surfaces, signal teal `#19C6B1`, IBM Plex data typography, Space Grotesk display typography, and semantic risk colors. The interface intentionally avoids generic purple gradients, excessive rounded cards, and vague AI language.

## Future roadmap

A production version could add PostgreSQL persistence, authenticated multi-tenant workspaces, tenant-level risk policies, model monitoring, analyst feedback loops, and policy simulation against historical outcomes. These are intentionally out of scope for this buildathon submission so the core story remains fast, deterministic, defense-only, and easy to evaluate.

## Deployment

The repository includes `vercel.json` with the Vite build command, `dist/public` output directory, and SPA fallback rewrites so `/demo` and `/app` remain reachable on direct refresh. The Vercel entrypoint `api/index.py` serves the FastAPI service, with the API rewrite placed before the SPA fallback. The production Vercel project is connected to the `main` branch.

## Live integration path

The reviewer-facing live API lab is available at `/live`. It exercises the FastAPI service instead of only rendering mock data.

### Local run

```bash
pnpm install
pnpm run api:dev
pnpm run dev
```

Open http://localhost:3000/live. The page calls:

- `GET /v1/health` and `GET /v1/integrations/status`
- `POST /v1/risk/analyze`
- `POST /v1/razorpay/create-payment`
- `POST /v1/razorpay/webhook` with HMAC signature verification
- `GET /v1/audit/recent`

Set `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, and `RAZORPAY_WEBHOOK_SECRET` to use Razorpay Test Mode. Without credentials, the order endpoint explicitly reports deterministic simulation; it never presents a fake remote payment as real. Set `VITE_API_BASE_URL` when the FastAPI service is deployed separately. Set `GEMINI_API_KEY` or `GROQ_API_KEY` to activate the LLM investigation agent; without a key the deterministic fallback generator is used.

The Vercel entrypoint is `api/index.py` and the API rewrite is placed before the SPA fallback. Secrets are read from environment variables and are not committed.
