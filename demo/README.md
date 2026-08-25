# RiskPilot AI — Demo Guide & 5-Minute Pitch Script

> **Razorpay AI Buildathon 2026** | **Track 02 — AI Risk Manager**  
> *Defense-Only AI Risk Detection with Human-in-the-Loop Override & Transparent Auditability*

---

## 🚀 Quick Execution Guide

Run both interactive terminal scripts directly from the repository root:

```bash
# 1. Run the Explicit Failure-Case & Human Override Demo
python3 demo/failure_case.py

# 2. Run the Full End-to-End 6-Scenario Walkthrough & Honest Metrics Demo
python3 demo/full_walkthrough.py
```

---

## 🎬 5-Minute Pitch Script & Presentation Walkthrough

Use this script during live presentations, video submissions, or judge reviews. Each minute is structured with exact **Speaker Lines**, **Terminal/UI Cues**, and **Key Highlights**.

---

### ⏱️ Minute 1: Introduction & Guided Risk Investigation
**Objective**: Introduce RiskPilot AI, state the defense-only mission, and show how incoming payments trigger guided risk analysis.

* **Speaker Script**:
  > "Hello judges! Welcome to **RiskPilot AI** — an intelligent, defense-only AI Risk Manager designed for Razorpay's payment ecosystem.
  > 
  > In high-throughput payment gateways, automated risk engines must be fast, accurate, and completely transparent. RiskPilot AI evaluates transactions in real-time by combining XGBoost risk scoring with LLM-powered context analysis.
  > 
  > Let's start our demo by launching the full walkthrough script. As you see on the screen, Scenario 1 evaluates a standard ₹1,850 grocery transaction for Rahul Verma. The system evaluates device telemetry, home city location, and spending baseline to yield a **Risk Score of 12/100 (LOW RISK)**, approving it instantly without customer friction."

* **On-Screen Cue**: Run `python3 demo/full_walkthrough.py` — highlight Scenario 1 output.
* **Key Takeaway**: Zero-friction approval for legitimate users; defense-only posture.

---

### ⏱️ Minute 2: Real Fraud Detection in Action (ATO & Bot Attacks)
**Objective**: Demonstrate how the risk engine detects and blocks active threats (Account Takeover, Card Testing, and Velocity Attacks).

* **Speaker Script**:
  > "Now, look at Scenario 2 and Scenario 3. Here, RiskPilot AI steps in to block critical real-world attack vectors.
  > 
  > In **Scenario 2**, an Account Takeover attempt triggers a **Risk Score of 94/100 (CRITICAL)**. The attacker changed the account password 2 minutes ago and tried to transfer ₹1,20,000 to a crypto exchange from a Tor exit node in Kyiv. The system blocks the payment immediately.
  > 
  > In **Scenario 3**, a card-testing botnet launches 15 micro-transactions in 45 seconds. RiskPilot AI detects the automated browser headers and global BIN velocity burst, issuing an instant **BLOCK (Score 96/100)**. Both events generate tamper-proof SHA-256 audit log records."

* **On-Screen Cue**: Point out Scenarios 2, 3, and 4 in `demo/full_walkthrough.py`.
* **Key Takeaway**: Instant defense against ATO, botnets, and high-velocity bursts with cryptographically signed logs.

---

### ⏱️ Minute 3: The Failure Case — Graceful False Positive Recovery
**Objective**: Fulfill the buildathon requirement: *"Show the audit trail and one failure handled gracefully."* Show transparency when the AI is wrong.

* **Speaker Script**:
  > "Now for the most crucial part of our buildathon entry: **Honesty in AI**. AI models make mistakes. The bar for a production risk system is how gracefully it handles its own errors.
  > 
  > Let's switch to `demo/failure_case.py`. Here, **Priya Sharma** — a 3-year VIP customer with 142 completed orders and zero chargebacks — makes a ₹45,000 purchase from an airport store in Bengaluru using a new iPhone.
  > 
  > Our automated AI engine over-flags the new device and location jump, scoring it **85/100 (CRITICAL)** and blocking the transaction. This is a **False Positive**.
  > 
  > But RiskPilot AI doesn't silently discard the user. Because of Priya's high trust tier, the system routes the case to a **Human Analyst (Vikram Malhotra)**. Vikram reviews her travel history, sends an in-app verification prompt, confirms travel, and executes a **Human Override**: *'Approve anyway — verified customer, new device explained by travel'*.
  > 
  > The payment is captured, the override is logged, and the failure pattern is fed back to retrain our model."

* **On-Screen Cue**: Run `python3 demo/failure_case.py` — highlight Steps 2, 4, 5, and 7.
* **Key Takeaway**: AI transparency, Human-in-the-Loop resilience, and active learning feedback loops.

---

### ⏱️ Minute 4: Razorpay Test-Mode Integration & Immutable Audit Trail
**Objective**: Show how RiskPilot AI integrates natively with Razorpay APIs and maintains compliance logs.

* **Speaker Script**:
  > "Under the hood, RiskPilot AI operates seamlessly alongside Razorpay's Checkout and Webhook infrastructure.
  > 
  > When a transaction is blocked or overridden, RiskPilot AI calls Razorpay's payment capture or authorization APIs in real-time.
  > 
  > Furthermore, every decision — whether made by the automated XGBoost engine or a human analyst — produces an **immutable audit record** with cryptographic hashes (`sha256`), actor IDs, initial AI score, override justification, and timestamp.
  > 
  > This guarantees 100% auditability for bank compliance, dispute management, and RBI regulatory oversight."

* **On-Screen Cue**: Scroll through the JSON Audit Log output in `demo/failure_case.py` (Step 6) and Scenario 5 audit entry in `full_walkthrough.py`.
* **Key Takeaway**: Turnkey Razorpay integration with immutable regulatory auditability.

---

### ⏱️ Minute 5: Honest Metrics & Financial Impact Analysis
**Objective**: Highlight the buildathon metric requirement: *"Honest metrics including false-positive cost."*

* **Speaker Script**:
  > "Finally, let's look at our evaluation results from `ml/results.json`. We refuse to report inflated 99% accuracy numbers that hide operational reality.
  > 
  > Across a 20,000-transaction benchmark test set:
  > * **Precision**: **94.2%**
  > * **Recall (Catch Rate)**: **91.8%**
  > * **F1 Score**: **0.930**
  > 
  > More importantly, we explicitly calculate the **False Positive Cost**:
  > Out of ₹48.5 Lakhs in prevented fraud, we recorded **240 false positives** costing **₹1,08,000** — broken down into SMS OTP costs (₹12k), analyst review time (₹48k), and customer friction (₹48k).
  > 
  > Subtracting FP costs yields a **Net Financial Savings of ₹47.42 Lakhs**.
  > 
  > RiskPilot AI is strictly defense-only, 100% transparent, and ready for Razorpay production deployment. Thank you!"

* **On-Screen Cue**: Highlight the terminal summary table and Honest Financial Impact section at the end of `demo/full_walkthrough.py`.
* **Key Takeaway**: True bottom-line financial impact accounting for operational and friction costs.

---

## 📊 Summary of Scenario Outcomes

| Scenario | Description | AI Score | AI Decision | Final Outcome | Human / Step-up Action |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **1** | Legitimate Consumer Purchase | `12/100` | `APPROVED` | **APPROVED** | Automated Pass |
| **2** | Account Takeover (ATO) Fraud | `94/100` | `BLOCKED` | **BLOCKED** | Blocked & Logged (True Positive) |
| **3** | Card Testing Bot Attack | `96/100` | `BLOCKED` | **BLOCKED** | Blocked & Logged (True Positive) |
| **4** | High-Velocity Fraud Burst | `89/100` | `BLOCKED` | **BLOCKED** | Blocked & Logged (True Positive) |
| **5** | False Positive (High-Trust Travel) | `85/100` | `BLOCKED` | **APPROVED** | **Human Override**: *"Verified customer, travel"* |
| **6** | Borderline Moderate Risk | `54/100` | `REVIEW` | **APPROVED** | **Step-Up Auth**: Passed OTP Verification |

---

## 🛡️ Buildathon Compliance Checklist

- [x] **Track 02 — AI Risk Manager**: Full end-to-end payment risk evaluation.
- [x] **Strictly Defense-Only**: No offensive testing capabilities or exploit payloads.
- [x] **Failure Handled Gracefully**: `demo/failure_case.py` demonstrates AI mistake recovery via human override.
- [x] **Audit Trail Included**: Complete cryptographic SHA-256 audit entries for every transaction state change.
- [x] **Honest Metrics**: Includes precision (94.2%), recall (91.8%), and explicit **False Positive Cost** (₹1,08,000) in `ml/results.json`.
