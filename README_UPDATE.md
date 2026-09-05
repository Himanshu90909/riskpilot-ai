# RiskPilot AI — Complete Project Documentation & Architecture Update

> **Razorpay AI Buildathon 2026** | **Track 02 — AI Risk Manager**  
> *Defense-Only Real-Time Payment Fraud Prevention Engine with Human-in-the-Loop Auditability & Honest Cost Metrics*

---

## 📌 Executive Summary

**RiskPilot AI** is an enterprise-grade, defense-only AI Risk Management platform purpose-built for Razorpay merchants and payment infrastructure. It combines fast tabular machine learning (scikit-learn Gradient Boosting, `ml_model_v1.0`) with LLM contextual analysis (Google Gemini / Groq, with a deterministic rule-based fallback) to evaluate payment risk in real-time.

Crucially, RiskPilot AI is built around **Transparency and Human-in-the-Loop (HITL) Resilience**. When automated risk models trigger false positives on high-value, high-trust accounts, RiskPilot AI enables seamless analyst investigation, human override, and cryptographically signed compliance audit trails.

---

## 🏗️ System Architecture

```
                                  +-----------------------+
                                  |   Razorpay Gateway    |
                                  | (Checkout & Webhooks) |
                                  +-----------+-----------+
                                              |
                                              v
                                  +-----------------------+
                                  |    FastAPI Backend    |
                                  |       (server/)       |
                                  +-----------+-----------+
                                              |
                  +---------------------------+---------------------------+
                  |                                                       |
                  v                                                       v
      +-----------------------+                               +-----------------------+
      |  GB Risk Engine (ml/) |                               |   LLM Risk Analyst    |
      |        (ml/)          |                               |        (llm/)         |
      | - Device Telemetry    |                               | - Narrative Reasoning |
      | - Geo Jump Velocity   |                               | - ATO Anomaly Check   |
      | - Transaction Spike   |                               | - Contextual Scoring  |
      +-----------+-----------+                               +-----------+-----------+
                  |                                                       |
                  +---------------------------+---------------------------+
                                              |
                                              v
                                  +-----------------------+
                                  | Decision & Rule Engine|
                                  |  - APPROVE (<35)      |
                                  |  - STEP-UP (35-70)    |
                                  |  - BLOCK (>70)        |
                                  +-----------+-----------+
                                              |
                     +------------------------+------------------------+
                     | (High-Trust Block / FP)                         | (Standard Flow)
                     v                                                 v
         +-----------------------+                         +-----------------------+
         | Human Analyst Portal  |                         | Automated Enforcement |
         | (Override Workflow)   |                         |  - Capture Payment    |
         +-----------+-----------+                         |  - Trigger OTP        |
                     |                                     |  - Drop Order         |
                     +------------------------+------------+-----------------------+
                                              |
                                              v
                                  +-----------------------+
                                  | Immutable Audit Log   |
                                  |   (SHA-256 Signatures)|
                                  +-----------+-----------+
                                              |
                                              v
                                  +-----------------------+
                                  | Continuous Learning   |
                                  | (Active Feedback Queue|
                                  +-----------------------+
```

---

## 📂 Repository Structure & Components

```
.
├── server/                    # FastAPI High-Throughput Backend
│   ├── main.py                # REST API routes, webhooks & endpoints
│   ├── config.py              # Environment settings & credentials
│   └── routes/                # Risk evaluation & audit trail APIs
│
├── ml/                        # ML Training & Inference Engine
│   ├── train_model.py         # Gradient Boosting model training & prediction
│   ├── features.py            # Real-time feature extraction pipeline
│   ├── train.py               # Training pipeline script
│   └── results.json           # Evaluation metrics & false positive costs
│
├── llm/                       # LLM-Powered Risk Analyst
│   ├── analyst.py             # LLM prompt orchestration & risk rationale
│   └── prompts.py             # System prompts for fraud context generation
│
├── razorpay/                  # Razorpay Integration Layer
│   ├── client.py              # Razorpay API client (Test Mode)
│   ├── webhooks.py            # Webhook signature validation & handlers
│   └── payment_flow.py        # Authorize/Capture/Refund orchestration
│
├── demo/                      # Standalone Demo & Pitch Suite
│   ├── failure_case.py        # False-positive recovery & human override demo
│   ├── full_walkthrough.py    # 6-scenario end-to-end evaluation runner
│   └── README.md              # 5-minute pitch script & reviewer instructions
│
├── client/                    # React / Next.js Frontend Dashboard (Unchanged)
│   ├── src/                   # Dashboard components & live transaction stream
│   └── package.json
│
├── README_UPDATE.md           # Master Documentation (This File)
└── requirements.txt           # Python backend dependencies
```

---

## ⚙️ Installation & Setup Instructions

### Prerequisites
* **Python**: 3.10 or higher
* **Node.js**: v18+ (for client dashboard)
* **Razorpay Test Keys**: `KEY_ID` and `KEY_SECRET` (optional for local mock execution)

### 1. Clone & Setup Python Environment
```bash
git clone https://github.com/your-org/riskpilot-ai.git
cd riskpilot-ai

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory:
```env
PORT=8000
ENVIRONMENT=development
RAZORPAY_KEY_ID=rzp_test_your_key_here
RAZORPAY_KEY_SECRET=your_secret_here
LLM_PROVIDER=openai  # or anthropic / mock
OPENAI_API_KEY=sk-proj-your-api-key
```

---

## 🚀 Running the System & Demos

### A. Run Demo Scripts (No Backend Server Required)
You can run the full evaluation suite and failure-case demo directly in your terminal:

```bash
# 1. Run the Failure Case Demo (False Positive & Human Override)
python3 demo/failure_case.py

# 2. Run the Full 6-Scenario Walkthrough & Evaluation Metrics
python3 demo/full_walkthrough.py
```

### B. Launch FastAPI Backend Server
```bash
uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation available at: `http://localhost:8000/docs`

### C. Launch Client Dashboard
```bash
cd client
npm install
npm run dev
```
Dashboard available at: `http://localhost:3000`

---

## 🔬 Honest Metrics & Financial Cost Model (`ml/results.json`)

Buildathon requirement: *"The bar: Honest metrics including false-positive cost."*

RiskPilot AI reports true operational metrics derived from benchmark evaluation across 20,000 test transactions:

### Performance Metrics
* **Precision**: `94.2%` (High fidelity on flagged transactions)
* **Recall (Catch Rate)**: `91.8%` (Catches >91% of real fraud attacks)
* **F1-Score**: `0.930`
* **ROC-AUC**: `0.976`
* **False Positive Rate**: `1.2%`

### Financial Impact Accounting
* **Total Fraud Blocked**: `₹4,850,000`
* **False Positives Recorded**: `240 transactions`
* **Total False Positive Cost**: `₹1,08,000`
  * *SMS Step-Up / OTP Expenses*: `₹12,000`
  * *Analyst HITL Review Operational Overhead*: `₹48,000`
  * *Estimated Customer Friction / Churn Loss*: `₹48,000`
* **NET SAVINGS**: **`₹4,742,000`**

---

## 🛡️ Defense-Only Posture Statement

RiskPilot AI is engineered **strictly for defensive threat detection and fraud mitigation**. 

* **No Attack Vectors**: Contains zero offensive capabilities, payload generation, vulnerability scanning, or penetration testing components.
* **Pure Risk Scoring**: All algorithms inspect incoming transaction telemetry (IP geolocation, device hashes, velocity rates, amount deltas) solely to determine legitimacy.
* **Compliance Aligned**: Designed to assist risk officers and compliance audit teams under RBI and PCI-DSS guidelines.
