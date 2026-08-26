# RiskPilot AI - LLM Risk Analyst Integration
> **Razorpay AI Buildathon Submission — Track 02 (AI Risk Manager)**

This directory contains the LLM-powered **Risk Analyst** integration for **RiskPilot AI**, replacing static canned responses in the legacy `assistantReply` seam with real-time, agentic multi-step fraud investigations and Gemini-powered natural language reasoning.

---

## 🌟 Overview

RiskPilot AI evaluates transaction risk by synthesizing device telemetry, network behavior, geographic anomalies, velocity surges, and user transaction history. The Risk Analyst integration adds an intelligent, defense-only agent layer that:

1. **Simulates an Agentic UI Workflow**: Executes an 8-step investigation pipeline (Customer History, Device Reputation, Geographic Behavior, Velocity, Payment Behavior, Merchant Signal, Risk Score Synthesis, and Explanation Generation).
2. **Generates High-Signal Explanations**: Uses Google's **Gemini 2.0 Flash** (`gemini-2.0-flash`) via the `google-genai` SDK to explain *why* a transaction is safe or suspicious.
3. **Guarantees 100% Reliability**: Includes a robust, deterministic rule-based fallback generator (`ExplanationGenerator`) when the Gemini API is unconfigured or unreachable.
4. **Enforces Defense-Only Safety**: Embedded system prompts prevent any generation of fraud bypass instructions, enforcing strict risk mitigation guardrails.

---

## 📁 File Architecture

```text
llm/
├── __init__.py                # Package exports
├── risk_analyst.py            # Gemini 2.0 Flash LLM Risk Analyst with defense guardrails
├── explanation_generator.py   # Fallback deterministic rule-based explanation engine
├── investigation_agent.py     # 8-step agentic investigation workflow simulating RiskPilot UI
├── requirements.txt           # Python dependencies (google-genai, numpy)
└── README.md                  # Setup & integration guide
```

### Module Descriptions

1. **`llm/risk_analyst.py`**
   - Connects to Google Gemini API using `google-genai` (`gemini-2.5-flash` by default).
   - Accepts current Google AI Studio key formats, including `AQ.` keys, through `GEMINI_API_KEY` or the `RiskAnalyst(api_key=...)` constructor.
   - Accepts flexible transaction context dictionaries containing amount, customer profile, device telemetry, location, velocity, failed attempts, merchant info, risk score, risk level, and AI decision.
   - Outputs structured JSON with:
     - `summary`: Concise 2-3 sentence investigation summary.
     - `risk_factors`: List of key risk factors identified.
     - `recommended_action`: Actionable decision (`BLOCK`, `FLAG_FOR_REVIEW`, `ALLOW`) with reasoning.
     - `reasoning`: Technical breakdown of risk vectors.
     - `follow_up_questions`: 2-4 critical follow-up questions for human analysts.
   - Handles API errors gracefully by invoking the fallback explanation generator.

2. **`llm/explanation_generator.py`**
   - Deterministic rule-based engine that evaluates active risk signals across amount spikes, new account tenure, historical chargebacks, VPN/proxy usage, new hardware fingerprints, geographic shifts, velocity bursts, and failed OTPs.
   - Maps risk indicators directly to structured summaries, risk factors, recommendations, follow-up questions, and an investigation timeline narrative.

3. **`llm/investigation_agent.py`**
   - Orchestrates the 8-step agentic workflow corresponding to the RiskPilot UI:
     - **Step 1**: Customer History Check (*'Querying customer profile and transaction history...'*)
     - **Step 2**: Device Reputation Check (*'Checking device fingerprint against known devices...'*)
     - **Step 3**: Geographic Behavior Check (*'Analyzing location patterns and distance from usual locations...'*)
     - **Step 4**: Velocity Check (*'Measuring transaction frequency against baseline...'*)
     - **Step 5**: Payment Behavior Check (*'Reviewing payment method and failure history...'*)
     - **Step 6**: Merchant Signal Check (*'Evaluating merchant risk profile...'*)
     - **Step 7**: Risk Score Calculation (*'Synthesizing all signals into risk score...'*)
     - **Step 8**: Explanation Generation (*'Generating investigation summary and recommendation...'*)
   - Exposes `assistant_reply(context)` / `assistantReply(context)` as the drop-in replacement for the app's legacy seam.

4. **`llm/requirements.txt`**
   - Contains required Python packages: `google-genai>=0.1.0` and `numpy>=1.20.0`.

---

## 🚀 Setup & Installation

### 1. Install Dependencies
```bash
pip install -r llm/requirements.txt
```

### 2. Get a Google Gemini API Key
1. Visit [Google AI Studio](https://aistudio.google.com/).
2. Sign in with your Google account.
3. Click **Get API key** and create a new key.
4. Export the key in your terminal or environment configuration:
   ```bash
   export GEMINI_API_KEY="your_gemini_api_key_here"  # Supports current AQ. keys and legacy AIza keys
   ```

*Note: If `GEMINI_API_KEY` is not set, RiskPilot AI will automatically operate using the rule-based fallback engine without throwing errors.*

---

## 🔄 Replacing the Legacy `assistantReply` Seam

The existing RiskPilot AI codebase previously used a canned response stub for `assistantReply`. You can replace that seam with a single import call:

### Legacy Canned Implementation (Before)
```python
# Old static seam with hardcoded responses
def assistantReply(context):
    return {
        "reply": "Transaction looks suspicious due to high risk score.",
        "risk_score": context.get("risk_score", 50)
    }
```

### LLM-Powered Implementation (After)
```python
from llm.investigation_agent import assistantReply

# Now calls the 8-step agentic workflow & Gemini 2.0 Flash reasoning
investigation_report = assistantReply(transaction_context)
```

---

## 💻 Example Usage

```python
from llm.investigation_agent import assistant_reply

# Sample transaction context payload
transaction_context = {
    "transaction_id": "tx_987654321",
    "amount": 4999.00,
    "currency": "INR",
    "customer": {
        "id": "cust_88",
        "account_age_days": 3,
        "total_previous_tx_count": 1,
        "historical_chargebacks": 0,
        "avg_tx_amount": 150.00
    },
    "device": {
        "ip": "185.220.101.5",
        "fingerprint": "dev_fp_998877",
        "is_vpn_or_proxy": True,
        "is_new_device": True
    },
    "location": {
        "current_city": "Mumbai",
        "usual_city": "Delhi",
        "distance_from_usual_km": 1150
    },
    "velocity": {
        "tx_count_last_10m": 4,
        "tx_count_last_1h": 7,
        "velocity_score": 88
    },
    "failed_attempts": {
        "failed_otp_last_1h": 3,
        "total_failed_attempts": 3
    },
    "merchant": {
        "name": "CryptoExchange Pro",
        "mcc": "6051",
        "risk_category": "HIGH"
    },
    "risk_score": 87.5,
    "risk_level": "HIGH",
    "ai_decision": "REJECT"
}

# Run multi-step investigation pipeline
report = assistant_reply(transaction_context)

# Inspect LLM output
print("AI Decision:", report["ai_decision"])
print("Summary:", report["summary_analysis"]["summary"])
print("Recommended Action:", report["summary_analysis"]["recommended_action"])
print("Risk Factors:", report["summary_analysis"]["risk_factors"])
print("Follow-up Questions:", report["summary_analysis"]["follow_up_questions"])
```

---

## 🛡️ Safety & Defense-Only Guardrails

RiskPilot AI is designed strictly for financial risk management and fraud detection. The system prompt embedded in `llm/risk_analyst.py` enforces:

- **Strict Defense Positioning**: Operates exclusively to detect, explain, and mitigate transaction fraud.
- **Zero Fraud Facilitation**: Refuses any prompts requesting advice on how to bypass security controls, evade velocity limits, spoof IP/device fingerprints, or commit payment fraud.
- **Concise Analysis**: Ensures output remains structured, professional, and directly useful for fraud operations teams.
