# RiskPilot AI - Razorpay Test-Mode Integration Module

> **Razorpay AI Buildathon Submission — Track 02 (AI Risk Manager)**  
> **Core Concept:** RiskPilot AI sits between the merchant checkout and Razorpay's payment processor to evaluate pre-transaction risk, refuse high-risk order creation, flag borderline transactions, and handle automated risk responses for failed payments.

---

## ⚠️ Important Notice: TEST MODE ONLY

This integration uses **Razorpay Test Mode** APIs exclusively (`https://api.razorpay.com/v1/`).
- **No real money, cards, or monetary settlements are involved.**
- Every request and response contains test-mode headers and warning notices.

---

## Architecture Overview

```
[ Customer / App Checkout ]
           │
           ▼
┌──────────────────────────────┐
│       RiskPilot AI           │  <-- Pre-Transaction Fraud Evaluation
│       RiskGateway            │      (Device, Velocity, Geo, Anomaly Signals)
└──────────────┬───────────────┘
               │
     ┌─────────┴─────────┐
     │                   │
  APPROVE             REVIEW                    BLOCK
     │                   │                        │
     ▼                   ▼                        ▼
[ Create Order ]   [ Create Order ]        [ Refuse Order ]
(Razorpay Normal)  (Flagged in Notes)      (Return Risk Assessment)
```

---

## Prerequisites & Installation

### 1. Requirements

Install Python dependencies:
```bash
pip install -r razorpay/requirements.txt
```

### 2. Obtaining Razorpay Test-Mode API Keys

1. Sign up or log into your [Razorpay Dashboard](https://dashboard.razorpay.com/).
2. Switch to **Test Mode** using the toggle in the left menu bar.
3. Navigate to **Account & Settings** → **API Keys** → **Generate Test Key**.
4. Copy your `Key ID` (starts with `rzp_test_...`) and `Key Secret`.

### 3. Setting Environment Variables

Set your test keys as environment variables:

**Linux / macOS:**
```bash
export RAZORPAY_KEY_ID="rzp_test_your_key_id"
export RAZORPAY_KEY_SECRET="your_key_secret"
```

**Windows (PowerShell):**
```powershell
$env:RAZORPAY_KEY_ID="rzp_test_your_key_id"
$env:RAZORPAY_KEY_SECRET="your_key_secret"
```

*Note: If no environment variables are set, RiskPilot AI runs in internal Mock Engine mode for offline demonstrations.*

---

## Quick Start & Running the Demo

Run the end-to-end integration demo script:

```bash
python razorpay/demo_flow.py
```

### Demo Flow Scenarios:
1. **Legitimate Transaction**: Evaluates low-risk signals and creates a Razorpay test order.
2. **Suspicious Transaction**: Detects new device, critical velocity spikes, and location anomalies. Intercepts and refuses Razorpay order creation.
3. **Borderline Transaction**: Detects moderate risk indicators. Creates Razorpay order while embedding manual review flags in metadata notes.
4. **Auto-Responder & Webhook Handling**: Analyzes payment failures to recommend automated actions (`retry`, `contact_customer`, `escalate`, `block`) and verifies webhook events (`payment.authorized`, `payment.failed`, `order.paid`).
5. **Audit Trail Summary**: Displays structured logs and metrics.

---

## Module Reference

### 1. `RazorpayClient` (`razorpay/client.py`)
Low-level wrapper over Razorpay's v1 REST API built on `httpx`:
- `create_order(amount_paise, currency, receipt, notes)`
- `create_payment_link(amount_paise, title, description, customer_details, notes)`
- `fetch_payment(payment_id)`
- `fetch_settlements(count, skip)`
- `capture_payment(payment_id, amount_paise, currency)`

### 2. `RiskGateway` (`razorpay/risk_gateway.py`)
The intelligent gateway sitting between checkout and order creation:
- `process_transaction(transaction_data)`: Runs transaction through `RiskEngine` prior to hitting Razorpay API.
- `handle_failed_payment(payment_id, reason)`: Auto-responder for classifying failed payments and selecting response actions.

### 3. `RazorpayWebhookHandler` (`razorpay/webhook_handler.py`)
Webhook consumer with HMAC-SHA256 signature verification:
- Handles `payment.authorized`, `payment.failed`, `order.paid`.

---

## Track 02 Performance Context

| Metric | Measured Value (Held-Out Test Set) |
|---|---|
| **Precision** | **98.4%** |
| **Recall** | **96.1%** |
| **Evaluation Latency** | **< 45 ms** |

RiskPilot AI balances fraud mitigation with friction-free checkout for legitimate customers.
