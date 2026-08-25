"""
RiskPilot AI - Synthetic Transaction Data Generator
Generates realistic payment transaction datasets with fraud labels for training and evaluation.
Simulates realistic fraud patterns: Account Takeover, Card Testing, Velocity Attack, and Friendly Fraud.
"""

import os
import random
import numpy as np
import pandas as pd

# Set random seed for reproducibility
np.random.seed(42)
random.seed(42)


def generate_synthetic_transactions(num_records=100000, fraud_rate=0.05):
    """
    Generates a DataFrame of synthetic payment transactions.
    
    Args:
        num_records (int): Total number of transaction records to generate.
        fraud_rate (float): Target fraction of fraudulent transactions (~0.05).
        
    Returns:
        pd.DataFrame: DataFrame containing generated features and fraud labels.
    """
    num_fraud = int(num_records * fraud_rate)
    num_legit = num_records - num_fraud

    # Partition fraud into 4 distinct patterns:
    # 1. Account Takeover (~30%)
    # 2. Card Testing (~25%)
    # 3. Velocity Attack (~25%)
    # 4. Friendly Fraud (~20%)
    f1_count = int(num_fraud * 0.30)
    f2_count = int(num_fraud * 0.25)
    f3_count = int(num_fraud * 0.25)
    f4_count = num_fraud - (f1_count + f2_count + f3_count)

    records = []

    # ------------------- 1. LEGITIMATE TRANSACTIONS -------------------
    for i in range(num_legit):
        cust_id = f"CUST_{random.randint(10000, 99999)}"
        dev_id = f"DEV_{random.randint(10000, 99999)}"
        merch_id = f"MERCH_{random.randint(100, 999)}"
        location = random.choice(["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Pune", "Kolkata", "Ahmedabad"])

        # Legitimate behavioral distribution
        amount = float(np.random.lognormal(mean=7.5, sigma=1.1)) # ~1,800 INR mean
        amount = np.clip(amount, 10.0, 75000.0)

        # 7% chance of legitimate new device usage (e.g. phone upgrade)
        new_device = int(np.random.rand() < 0.07)

        # 4% chance of legitimate location anomaly (e.g. user traveling)
        location_anomaly = int(np.random.rand() < 0.04)

        # Low velocity for legit users
        velocity = float(np.clip(np.random.exponential(scale=0.8), 0.1, 4.0))

        # Failed attempts mostly 0, rarely 1 or 2
        failed_attempts = int(np.random.choice([0, 1, 2], p=[0.93, 0.05, 0.02]))

        # Account age in days (established accounts)
        account_age_days = int(np.random.randint(15, 1200))

        # Low to moderate merchant risk score
        merchant_risk_score = float(np.random.beta(a=1.5, b=8.0))

        # Behavioral deviation low for normal users
        behavioral_deviation = float(np.random.beta(a=1.5, b=6.0))

        records.append({
            'customer_id': cust_id,
            'device_id': dev_id,
            'new_device': new_device,
            'location': location,
            'location_anomaly': location_anomaly,
            'amount': round(amount, 2),
            'velocity': round(velocity, 2),
            'failed_attempts': failed_attempts,
            'account_age_days': account_age_days,
            'merchant_id': merch_id,
            'merchant_risk_score': round(merchant_risk_score, 4),
            'behavioral_deviation': round(behavioral_deviation, 4),
            'is_fraud': 0
        })

    # ------------------- 2. FRAUD PATTERNS -------------------
    # Fraud Pattern 1: Account Takeover (ATO)
    # Features: new_device=1, location_anomaly=1, high velocity, short account age
    for i in range(f1_count):
        cust_id = f"CUST_{random.randint(10000, 99999)}"
        dev_id = f"DEV_{random.randint(10000, 99999)}"
        merch_id = f"MERCH_{random.randint(100, 999)}"
        location = random.choice(["London", "Lagos", "Bucharest", "Moscow", "Unknown_VPN"])

        amount = float(np.random.uniform(12000.0, 90000.0))
        new_device = int(np.random.rand() < 0.88)
        location_anomaly = int(np.random.rand() < 0.85)
        velocity = float(np.random.uniform(5.0, 18.0))
        failed_attempts = int(np.random.choice([0, 1, 2, 3], p=[0.25, 0.40, 0.25, 0.10]))
        account_age_days = int(np.random.randint(1, 14))
        merchant_risk_score = float(np.random.uniform(0.40, 0.90))
        behavioral_deviation = float(np.random.uniform(0.65, 0.98))

        records.append({
            'customer_id': cust_id,
            'device_id': dev_id,
            'new_device': new_device,
            'location': location,
            'location_anomaly': location_anomaly,
            'amount': round(amount, 2),
            'velocity': round(velocity, 2),
            'failed_attempts': failed_attempts,
            'account_age_days': account_age_days,
            'merchant_id': merch_id,
            'merchant_risk_score': round(merchant_risk_score, 4),
            'behavioral_deviation': round(behavioral_deviation, 4),
            'is_fraud': 1
        })

    # Fraud Pattern 2: Card Testing
    # Features: many failed_attempts, moderate amount, high velocity
    for i in range(f2_count):
        cust_id = f"CUST_{random.randint(10000, 99999)}"
        dev_id = f"DEV_{random.randint(10000, 99999)}"
        merch_id = f"MERCH_{random.randint(100, 999)}"
        location = random.choice(["Mumbai", "Delhi", "Kolkata", "Proxy_Node"])

        amount = float(np.random.uniform(150.0, 3000.0))
        new_device = int(np.random.rand() < 0.70)
        location_anomaly = int(np.random.rand() < 0.50)
        velocity = float(np.random.uniform(10.0, 40.0))
        failed_attempts = int(np.random.randint(3, 12))
        account_age_days = int(np.random.randint(1, 40))
        merchant_risk_score = float(np.random.uniform(0.50, 0.90))
        behavioral_deviation = float(np.random.uniform(0.50, 0.90))

        records.append({
            'customer_id': cust_id,
            'device_id': dev_id,
            'new_device': new_device,
            'location': location,
            'location_anomaly': location_anomaly,
            'amount': round(amount, 2),
            'velocity': round(velocity, 2),
            'failed_attempts': failed_attempts,
            'account_age_days': account_age_days,
            'merchant_id': merch_id,
            'merchant_risk_score': round(merchant_risk_score, 4),
            'behavioral_deviation': round(behavioral_deviation, 4),
            'is_fraud': 1
        })

    # Fraud Pattern 3: Velocity Attack
    # Features: extremely high velocity, multiple failed attempts
    for i in range(f3_count):
        cust_id = f"CUST_{random.randint(10000, 99999)}"
        dev_id = f"DEV_{random.randint(10000, 99999)}"
        merch_id = f"MERCH_{random.randint(100, 999)}"
        location = random.choice(["Bangalore", "Singapore", "Dublin", "Frankfurt"])

        amount = float(np.random.uniform(4000.0, 55000.0))
        new_device = int(np.random.rand() < 0.80)
        location_anomaly = int(np.random.rand() < 0.60)
        velocity = float(np.random.uniform(20.0, 75.0))
        failed_attempts = int(np.random.randint(2, 9))
        account_age_days = int(np.random.randint(1, 50))
        merchant_risk_score = float(np.random.uniform(0.40, 0.85))
        behavioral_deviation = float(np.random.uniform(0.60, 0.92))

        records.append({
            'customer_id': cust_id,
            'device_id': dev_id,
            'new_device': new_device,
            'location': location,
            'location_anomaly': location_anomaly,
            'amount': round(amount, 2),
            'velocity': round(velocity, 2),
            'failed_attempts': failed_attempts,
            'account_age_days': account_age_days,
            'merchant_id': merch_id,
            'merchant_risk_score': round(merchant_risk_score, 4),
            'behavioral_deviation': round(behavioral_deviation, 4),
            'is_fraud': 1
        })

    # Fraud Pattern 4: Friendly Fraud (Chargeback abuse)
    # Features: long account age, normal device, high amount, low merchant risk
    for i in range(f4_count):
        cust_id = f"CUST_{random.randint(10000, 99999)}"
        dev_id = f"DEV_{random.randint(10000, 99999)}"
        merch_id = f"MERCH_{random.randint(100, 999)}"
        location = random.choice(["Mumbai", "Delhi", "Bangalore", "Pune"])

        amount = float(np.random.uniform(25000.0, 85000.0))
        new_device = int(np.random.rand() < 0.12)
        location_anomaly = int(np.random.rand() < 0.08)
        velocity = float(np.random.uniform(0.3, 3.0))
        failed_attempts = int(np.random.choice([0, 1], p=[0.88, 0.12]))
        account_age_days = int(np.random.randint(120, 900))
        merchant_risk_score = float(np.random.uniform(0.05, 0.35))
        behavioral_deviation = float(np.random.uniform(0.35, 0.70))

        records.append({
            'customer_id': cust_id,
            'device_id': dev_id,
            'new_device': new_device,
            'location': location,
            'location_anomaly': location_anomaly,
            'amount': round(amount, 2),
            'velocity': round(velocity, 2),
            'failed_attempts': failed_attempts,
            'account_age_days': account_age_days,
            'merchant_id': merch_id,
            'merchant_risk_score': round(merchant_risk_score, 4),
            'behavioral_deviation': round(behavioral_deviation, 4),
            'is_fraud': 1
        })

    # Convert to DataFrame and shuffle
    df = pd.DataFrame(records)
    df = df.sample(frac=1.0, random_state=42).reset_index(drop=True)

    # ------------------- 3. ADD NOISE FOR REALISTIC MODELING -------------------
    # Flip ~0.6% of labels to introduce realistic noise
    noise_mask = np.random.rand(len(df)) < 0.006
    df.loc[noise_mask, 'is_fraud'] = 1 - df.loc[noise_mask, 'is_fraud']

    return df


def main():
    print("Generating synthetic payment transaction dataset (100,000 records)...")
    df = generate_synthetic_transactions(num_records=100000, fraud_rate=0.05)

    # Split into 80,000 train and 20,000 test
    train_df = df.iloc[:80000].copy()
    test_df = df.iloc[80000:].copy()

    # Create directories if needed
    os.makedirs('ml/data', exist_ok=True)

    train_path = 'ml/data/train.csv'
    test_path = 'ml/data/test.csv'

    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)

    print(f"Data generation complete!")
    print(f" - Train set saved to: {train_path} ({len(train_df)} rows, {train_df['is_fraud'].sum()} fraud)")
    print(f" - Test set saved to:  {test_path} ({len(test_df)} rows, {test_df['is_fraud'].sum()} fraud)")


if __name__ == '__main__':
    main()
