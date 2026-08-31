> **Built and submitted by Himanshu Suthar**
>
> GitHub owner: [Himanshu90909](https://github.com/Himanshu90909)  
> Live demo: [riskpilot-ai-five.vercel.app/demo]https://riskpilot-ai-five.vercel.app/app
> Pitch walkthrough: [working platform video](https://files.manuscdn.com/user_upload_by_module/session_file/310519663815895274/AxlHmfIynAgdoPel.webm)

# RiskPilot AI

> **Autonomous Risk Intelligence for Digital Payments**

RiskPilot AI is a startup-style fintech SaaS demo for the AI Risk Manager track. It sits between a digital commerce system and the final payment decision, investigating suspicious activity across customer, device, location, velocity, payment, behavior, and merchant signals before recommending **approve**, **review**, or **block**.

The product is intentionally presented as a **DEMO ENVIRONMENT** for fictional customer NovaPay. All metrics and relationships are deterministic synthetic data; no real financial data, billing, or payment infrastructure is connected.

## Product overview

RiskPilot is positioned as an autonomous risk intelligence layer rather than a dashboard that only predicts fraud. Its key product promise is:

> **RiskPilot AI helps businesses decide which transactions to trust.**

The experience supports a 3–5 minute interview or hackathon walkthrough. The new `/demo` route opens a guided command center where the agent reveals each signal in sequence, sweeps the risk score from pending to critical, writes the audit state, and then presents held-out synthetic evaluation evidence. Reviewers can continue into the full console for executive impact, transaction context, human override, simulation, and developer API details.

## What is implemented

| Area | Included in the demo |
|---|---|
| Landing page | Product positioning, platform capabilities, “Detect → Investigate → Decide → Protect” story, and evidence-first case file visual |
| Executive overview | KPI strip, fraud prevention trend, risk distribution chart, priority queue, autonomous agent summary |
| Transaction intelligence | Search, risk-level filter, decision filter, 100 deterministic synthetic transactions, clickable transaction drawer |
| AI investigations | Risk ring, risk factors, investigation timeline, explanation, model/version metadata, human-in-the-loop actions |
| Risk intelligence | Detection vs. exposure trend, risk category breakdown, signal topology, model readout |
| Fraud patterns | Account takeover, card testing, velocity attack, and friendly fraud clusters |
| Customer profiles | 30 synthetic customer profiles with risk score, account age, devices, locations, failed payments, and events |
| Merchant intelligence | 15 synthetic merchants with risk rate, fraud rate, blocked amount, trend bars, and health status |
| Rules | Toggleable risk rules with enable/disable feedback and transparent score bands |
| Simulation Lab | Account takeover, card testing, velocity attack, and friendly fraud scenarios with deterministic results |
| Audit Center | Searchable decision records with AI decision, human decision, action, timestamp, and model version |
| Developer API | Simulated `POST /v1/risk/analyze` request/response with JSON examples |
| Risk Analyst | Local analytical assistant with contextual responses for key demo questions |
| Pricing | Startup-style pricing presentation marked as UI-only; no billing integration |

## Architecture

```text
Digital commerce
      ↓
Transaction context
      ↓
RiskPilot AI risk layer
      ├── Fraud signals
      ├── Behavioral signals
      ├── Device and location signals
      └── Merchant and payment signals
      ↓
Deterministic risk engine (demo mode)
      ↓
Approve / Review / Block
      ↓
Explanation + human override + audit trail
```

## Tech stack

The project uses React 19, TypeScript, Vite, Tailwind CSS 4, Wouter for client-side routing, Recharts for deterministic visualizations, Lucide React for iconography, and shadcn/ui primitives from the provided static web template. It is frontend-only by design so the interview demo starts instantly without a database, credentials, or external API dependency.

## Setup

```bash
pnpm install
pnpm run dev
```

For a production build:

```bash
pnpm run check
pnpm run build
pnpm run start
```

The local demo opens at `http://localhost:3000`.

## Demo access

No login is required. Open the landing page and select **Open demo**. The fictional workspace is **NovaPay** and the demo operator is **Himanshu Suthar · Admin**.

Recommended walkthrough:

1. Open `/demo` first. Let the guided investigation run so the reviewer sees the risk score, evidence trail, decision monitor, and model readout build in real time.
2. Open **Overview** and call out `₹3.82 Cr` potential fraud prevented, `12,481` blocked transactions, and the `42 ms` median decision time.
3. Open the first priority transaction, `TXN-84921`, for Rahul Mehta at Nova Electronics.
4. Open **AI Investigation** and show the `91 / 100 · CRITICAL` score, signal contributions, timeline, and explanation.
5. Use **Keep blocked**, **Approve anyway**, or **Request verification** to demonstrate responsible AI and human accountability.
6. Open **Simulations**, run **Account Takeover**, and show the deterministic `94 / 100 · BLOCK · ₹4.8L` result.
7. Point to the held-out synthetic test set in the guided demo: precision `93.35%`, recall `88.97%`, F1 `91.11%`, and the confusion matrix. Finish in **Developer API** to show how the risk layer can be integrated into a payment flow.

## Track 02 evaluation

The submission is intentionally focused on one loss class: account takeover on digital payment transactions. `evaluation/run.mjs` is the reproducible evaluation entry point. It keeps data generation, detector logic, threshold, cost model, and metrics in code so a reviewer can rerun the result instead of trusting a screenshot. `evaluation/results.json` is the generated artifact used by the guided UI.

The evaluator uses a deterministic synthetic dataset because this is a hackathon demo environment with no real customer data. Every output is labeled as synthetic and should not be read as a production fraud estimate.

## Risk engine

The deterministic engine in `client/src/lib/mockData.ts` accepts transaction amount, device state, location state, velocity, failed attempts, account age, merchant risk, and behavioral deviation. Each input contributes to a transparent score between 0 and 100.

| Score | Level | Default decision |
|---:|---|---|
| 0–30 | LOW | APPROVE |
| 31–60 | MEDIUM | REVIEW |
| 61–80 | HIGH | REVIEW / STEP-UP |
| 81–100 | CRITICAL | BLOCK |

The score is intentionally deterministic so the same interview walkthrough always produces the same evidence. The engine is isolated behind `calculateRiskScore`, making it straightforward to replace with a service or model adapter later.

## AI agent architecture

The interface presents RiskPilot Agent as an agentic investigator. A suspicious transaction moves through customer history, device reputation, geographic behavior, velocity, payment behavior, merchant signals, score calculation, and explanation generation. In the current static demo, those steps are represented with local deterministic data and UI timing. The `assistantReply` function provides a replaceable seam for a future LLM-backed analyst service.

## API demonstration

The simulated endpoint is:

```http
POST /v1/risk/analyze
```

Example response:

```json
{
  "risk_score": 91,
  "risk_level": "critical",
  "decision": "block",
  "reasons": [
    "new_device",
    "location_anomaly",
    "high_velocity"
  ]
}
```

The endpoint is presented as a UI demonstration only. There is no live network request or payment action behind it.

## Project structure

```text
client/
  src/
    pages/Home.tsx       # Landing, app shell, routes, and feature views
    lib/mockData.ts      # Synthetic entities, charts, risk engine, assistant
    index.css            # Editorial Trust Layer design system
    App.tsx              # Route map and global providers
  index.html             # Metadata, fonts, favicon
ideas.md                 # Design exploration and chosen visual direction
README.md                # Product and implementation documentation
```

## Design system

RiskPilot uses the **Editorial Trust Layer** direction: Swiss-inspired hierarchy, deep ink navigation, warm paper surfaces, signal teal `#19C6B1`, IBM Plex data typography, Space Grotesk display typography, and semantic risk colors. The interface intentionally avoids generic purple gradients, excessive rounded cards, and vague AI language.

## Future roadmap

The included Track 02 evaluator is runnable from the repository with `node evaluation/run.mjs`. It generates 100,000 deterministic synthetic records, reserves the final 20,000 records as held-out evaluation data, applies a defense-only weighted signal detector at threshold 24, and writes the exact result to `evaluation/results.json`. The current held-out result is precision `93.35%`, recall `88.97%`, F1 `91.11%`, false-positive rate `3.53%`, and false-positive cost `₹81,540` under the documented synthetic cost assumptions. The confusion matrix is 6,363 true positives, 453 false positives, 789 false negatives, and 12,395 true negatives.

A production version could add a FastAPI decision service, PostgreSQL entities and audit storage, signed webhooks, authenticated workspaces, configurable tenant-level risk policies, model monitoring, analyst feedback loops, policy simulation against historical outcomes, and operational integrations with payment gateways. These are intentionally not included in this interview demo so the core story remains fast, deterministic, defense-only, and easy to evaluate.


## Deployment

The repository includes `vercel.json` with the Vite build command, `dist/public` output directory, and SPA fallback rewrites so `/demo` and `/app` remain reachable on direct refresh. The production Vercel project is connected to the `main` branch.
