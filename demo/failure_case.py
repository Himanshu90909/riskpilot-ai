#!/usr/bin/env python3
"""
RiskPilot AI - Explicit Failure Case Demo
Razorpay AI Buildathon (Track 02 - AI Risk Manager)

Demonstrates how RiskPilot AI gracefully handles a False Positive:
1. AI Risk Engine over-flags a legitimate transaction from a high-trust customer.
2. System flags transaction for Human-in-the-Loop (HITL) review rather than silent loss.
3. Analyst reviews customer profile, transaction context, and travel signals.
4. Analyst executes human override: 'Approve anyway - verified customer, new device explained by travel'.
5. Event is recorded in the immutable audit trail.
6. Feedback loop captures failure pattern to improve future ML model iterations.
"""

import time
import json
import datetime

# ANSI Color Codes for Rich Terminal Output
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"
BG_RED = "\033[41m"
BG_GREEN = "\033[42m"
BG_YELLOW = "\033[43m"
BG_BLUE = "\033[44m"

def print_banner(title):
    width = 76
    print("\n" + CYAN + "=" * width + RESET)
    print(BOLD + CYAN + f"  {title.center(width - 4)}" + RESET)
    print(CYAN + "=" * width + RESET + "\n")

def print_section(title, color=BLUE):
    width = 76
    print("\n" + color + BOLD + f"--- [ {title} ] " + "-" * (width - 10 - len(title)) + RESET + "\n")

def print_box(content, title=None, color=WHITE):
    lines = content.strip().split("\n")
    max_len = max(len(line) for line in lines)
    width = max(max_len + 4, 72)
    
    border_top = color + "┌" + "─" * (width - 2) + "┐" + RESET
    border_bot = color + "└" + "─" * (width - 2) + "┘" + RESET
    
    print(border_top)
    if title:
        header = f" │ {BOLD}{title}{RESET}"
        pad = width - 1 - len(title) - 4
        print(color + header + " " * max(0, pad) + color + "│" + RESET)
        print(color + "├" + "─" * (width - 2) + "┤" + RESET)
        
    for line in lines:
        padding = width - 4 - len(line)
        print(color + "│ " + RESET + line + " " * max(0, padding) + color + " │" + RESET)
    print(border_bot)

def run_failure_case_demo():
    print_banner("RISKPILOT AI - EXPLICIT FAILURE CASE & HUMAN-IN-THE-LOOP DEMO")
    print(BOLD + WHITE + "Track 02: AI Risk Manager | Razorpay AI Buildathon 2026" + RESET)
    print(DIM + "Demonstrating system resilience, audit transparency, and false-positive recovery.\n" + RESET)

    # -------------------------------------------------------------------------
    # STEP 1: Incoming Transaction
    # -------------------------------------------------------------------------
    print_section("STEP 1: INCOMING TRANSACTION SUBMISSION", CYAN)
    
    txn_details = {
        "transaction_id": "TXN_20260825_FP8849",
        "timestamp": "2026-08-25T19:42:10Z",
        "customer": {
            "id": "CUST_99321",
            "name": "Priya Sharma",
            "email": "priya.sharma@example.com",
            "home_city": "Mumbai, MH"
        },
        "payment_context": {
            "amount": "₹45,000.00",
            "merchant": "TechWorld Premium Store",
            "location": "Bengaluru, KA (Travel Location)",
            "device": "Apple iPhone 15 Pro (Unrecognized Device ID)",
            "ip_address": "182.73.18.99 (Airtel Broadband - Bengaluru)",
            "payment_method": "Razorpay UPI (priya@okicici)"
        }
    }
    
    print(f"{BOLD}Transaction ID:{RESET} {txn_details['transaction_id']}")
    print(f"{BOLD}Customer:{RESET}       {txn_details['customer']['name']} ({txn_details['customer']['id']})")
    print(f"{BOLD}Amount:{RESET}         {BOLD}{YELLOW}{txn_details['payment_context']['amount']}{RESET}")
    print(f"{BOLD}Merchant:{RESET}       {txn_details['payment_context']['merchant']}")
    print(f"{BOLD}Location:{RESET}       {txn_details['payment_context']['location']}")
    print(f"{BOLD}Device:{RESET}         {txn_details['payment_context']['device']}")

    # -------------------------------------------------------------------------
    # STEP 2: Risk Engine Automated Evaluation (The False Positive)
    # -------------------------------------------------------------------------
    print_section("STEP 2: RISK ENGINE EVALUATION (AUTOMATED AI DECISION)", RED)
    
    risk_assessment = {
        "risk_score": 85,
        "risk_level": "CRITICAL",
        "ai_decision": "BLOCKED",
        "rules_triggered": [
            {"rule": "NEW_DEVICE_DETECTED", "score_impact": "+30", "detail": "First seen hardware footprint"},
            {"rule": "LOCATION_ANOMALY", "score_impact": "+30", "detail": "Transaction origin Bengaluru is >800km from home city Mumbai"},
            {"rule": "HIGH_AMOUNT_DEV", "score_impact": "+25", "detail": "Amount ₹45,000 is 3.8x average single purchase value"}
        ],
        "ml_model_confidence": "91.4%",
        "reasoning": "High confidence score driven by simultaneous appearance of brand-new device hardware fingerprint, geolocational jump from home city, and transaction value spike."
    }

    print(f"{BOLD}Risk Score:{RESET}    [{BG_RED}{WHITE}{BOLD} 85 / 100 {RESET}] ({RED}{BOLD}CRITICAL RISK{RESET})")
    print(f"{BOLD}AI Decision:{RESET}   {RED}{BOLD}🛑 BLOCKED (FALSE POSITIVE){RESET}")
    print(f"{BOLD}Model Confidence:{RESET} {risk_assessment['ml_model_confidence']}")
    print("\n" + BOLD + "Triggered Risk Signals:" + RESET)
    for rule in risk_assessment["rules_triggered"]:
        print(f"  • {RED}{rule['rule']}{RESET} ({rule['score_impact']}): {rule['detail']}")
    
    print("\n" + RED + "❌ AI ENGINE ERROR:" + RESET + " System categorized legitimate customer purchase as fraudulent account takeover due to rigid feature weighting on new device + location jump.")

    # -------------------------------------------------------------------------
    # STEP 3: Customer Profile & History Lookup (Context Retrieval)
    # -------------------------------------------------------------------------
    print_section("STEP 3: DEEP CUSTOMER PROFILE & HISTORY LOOKUP", MAGENTA)
    
    print("Pulling historical telemetry and loyalty metrics from feature store...\n")
    
    history_box = f"""Customer Name:       Priya Sharma (ID: CUST_99321)
Account Age:         36 Months (3 Years) - Tier 1 VIP Customer
Total Transactions:  142 Completed Orders
Lifetime Volume:     ₹1,25,000.00
Fraud History:       0 Chargebacks | 0 Disputed Payments | 0 Flags
Recent Activity:     Card used at CSMI Airport Mumbai 4 hours prior (Travel Indicator)
Risk Category:       LOW HISTORICAL RISK (Trust Score: 98/100)"""

    print_box(history_box, title="CUSTOMER HISTORICAL METRICS", color=MAGENTA)

    # -------------------------------------------------------------------------
    # STEP 4: Human Analyst Investigation
    # -------------------------------------------------------------------------
    print_section("STEP 4: HUMAN ANALYST CASE REVIEW (HITL WORKFLOW)", YELLOW)
    
    print(f"{BOLD}Assigned Risk Analyst:{RESET} Vikram Malhotra (ID: ANALYST_402)")
    print(f"{BOLD}Review Queue Status:{RESET}   Urgent Priority (Escalated High-Value Customer Block)\n")
    
    print(BOLD + "Analyst Findings & Verification:" + RESET)
    print("  1. Checked airport lounge merchant swipe 4h prior -> Confirms active domestic travel.")
    print("  2. Performed push-notification step-up verification -> Customer confirmed purchase in-app.")
    print("  3. Item being purchased (laptop at airport electronics hub) matches travel context.")
    print("  4. Zero risk flags in 3-year history across 142 completed orders.")

    # -------------------------------------------------------------------------
    # STEP 5: Human Override Execution
    # -------------------------------------------------------------------------
    print_section("STEP 5: HUMAN OVERRIDE EXECUTION", GREEN)
    
    override_data = {
        "action": "OVERRIDE_APPROVE",
        "previous_status": "BLOCKED",
        "new_status": "APPROVED_BY_HUMAN",
        "analyst_id": "ANALYST_402 (Vikram Malhotra)",
        "override_reason": "Approve anyway - verified customer, new device explained by travel",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "customer_notified": True,
        "razorpay_payment_status": "CAPTURED"
    }
    
    override_box = f"""Analyst Action:     {GREEN}{BOLD}OVERRIDE_APPROVE{RESET}
Previous Status:    {RED}BLOCKED{RESET}
Updated Status:     {GREEN}{BOLD}APPROVED (HUMAN OVERRIDE){RESET}
Override Reason:    "{override_data['override_reason']}"
Razorpay Status:    Captured (Payment Authorized)
Analyst ID:         ANALYST_402"""

    print_box(override_box, title="HUMAN OVERRIDE ACTION RECORD", color=GREEN)

    # -------------------------------------------------------------------------
    # STEP 6: Immutable Audit Trail Entry
    # -------------------------------------------------------------------------
    print_section("STEP 6: IMMUTABLE AUDIT TRAIL LOGGING", CYAN)
    
    audit_entry = {
        "audit_id": "AUD_20260825_99382",
        "transaction_id": txn_details["transaction_id"],
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "event_type": "HUMAN_OVERRIDE",
        "actor": {
            "type": "HUMAN_ANALYST",
            "id": "ANALYST_402",
            "name": "Vikram Malhotra"
        },
        "initial_ai_state": {
            "score": 85,
            "decision": "BLOCKED",
            "top_factor": "LOCATION_ANOMALY"
        },
        "final_state": {
            "decision": "APPROVED",
            "resolution": "FALSE_POSITIVE_OVERRIDDEN"
        },
        "justification": "Approve anyway - verified customer, new device explained by travel",
        "cryptographic_hash": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    }

    print(json.dumps(audit_entry, indent=2))
    print(f"\n{GREEN}✔ Audit entry appended to immutable compliance log.{RESET}")

    # -------------------------------------------------------------------------
    # STEP 7: Failure Summary & Feedback Loop
    # -------------------------------------------------------------------------
    print_section("STEP 7: POST-MORTEM & CONTINUOUS MODEL LEARNING", MAGENTA)
    
    summary_text = f"""1. WHAT WENT WRONG?
   • AI risk model assigned excessive weight (+30) to location jump and new device.
   • Model failed to correlate airport velocity signal with location anomaly.

2. HOW WAS IT HANDLED?
   • High-trust VIP profile prevented auto-hard-drop, routing to Priority HITL Review.
   • Human analyst caught the mistake within 45 seconds and issued an override.
   • Customer purchase was completed smoothly without financial loss.

3. LESSON LEARNED & MODEL IMPROVEMENT:
   • Failure case tagged as FALSE_POSITIVE and pushed to active learning dataset.
   • Retraining Rule: Boost weight of 'Account Age > 24m' & add 'Travel Corridor' signal.
   • Future Similar Txns: Risk score will adjust from 85 -> 42 (Pass with Step-Up Auth)."""

    print_box(summary_text, title="SYSTEM TRANSPARENCY & LEARNING SUMMARY", color=CYAN)
    
    print("\n" + BOLD + GREEN + "✔ DEMO COMPLETE: Failure case gracefully resolved with 100% audit transparency." + RESET + "\n")

if __name__ == "__main__":
    run_failure_case_demo()
