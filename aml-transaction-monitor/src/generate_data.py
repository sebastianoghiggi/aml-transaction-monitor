import pandas as pd
import random
from faker import Faker
from datetime import datetime, timedelta

fake = Faker()
random.seed(42)  # makes results reproducible

# --- Configuration ---

NUM_TRANSACTIONS = 500
NUM_CUSTOMERS = 50
START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2024, 12, 31)

# --- Helper: random date between two dates ---

def random_date(start, end):
    delta = end - start
    return start + timedelta(days=random.randint(0, delta.days),
                             hours=random.randint(0, 23),
                             minutes=random.randint(0, 59))

# --- Generate customer pool ---

customers = [fake.bothify(text="CUST-####") for _ in range(NUM_CUSTOMERS)]

# --- Transaction types ---

TRANSACTION_TYPES = ["deposit", "withdrawal", "transfer", "wire_transfer"]

# --- Generate normal transactions ---

def generate_normal_transactions(n):
    transactions = []
    for _ in range(n):
        transactions.append({
            "transaction_id": fake.uuid4(),
            "customer_id": random.choice(customers),
            "date": random_date(START_DATE, END_DATE),
            "amount": round(random.uniform(10, 9000), 2),
            "transaction_type": random.choice(TRANSACTION_TYPES),
            "destination_country": random.choice(["US", "US", "US", "UK", "CA"]),
            "is_suspicious": False
        })
    return transactions

# --- Generate suspicious transactions ---

def generate_suspicious_transactions():
    suspicious = []

    # Pattern 1: Large cash deposits (over $10,000 — classic AML red flag)
    for _ in range(10):
        suspicious.append({
            "transaction_id": fake.uuid4(),
            "customer_id": random.choice(customers),
            "date": random_date(START_DATE, END_DATE),
            "amount": round(random.uniform(10001, 50000), 2),
            "transaction_type": "deposit",
            "destination_country": "US",
            "is_suspicious": True
        })

    # Pattern 2: Structuring — multiple transactions just under $10,000
    structuring_customer = random.choice(customers)
    base_date = random_date(START_DATE, END_DATE)
    for i in range(5):
        suspicious.append({
            "transaction_id": fake.uuid4(),
            "customer_id": structuring_customer,
            "date": base_date + timedelta(hours=i * 2),
            "amount": round(random.uniform(8500, 9999), 2),
            "transaction_type": "deposit",
            "destination_country": "US",
            "is_suspicious": True
        })

    # Pattern 3: Wire transfers to high-risk countries
    for _ in range(10):
        suspicious.append({
            "transaction_id": fake.uuid4(),
            "customer_id": random.choice(customers),
            "date": random_date(START_DATE, END_DATE),
            "amount": round(random.uniform(5000, 30000), 2),
            "transaction_type": "wire_transfer",
            "destination_country": random.choice(["IR", "KP", "SY"]),
            "is_suspicious": True
        })

    return suspicious

# --- Combine and shuffle ---
all_transactions = generate_normal_transactions(NUM_TRANSACTIONS)
all_transactions += generate_suspicious_transactions()
random.shuffle(all_transactions)

# --- Convert to DataFrame ---
df = pd.DataFrame(all_transactions)
df = df.sort_values("date").reset_index(drop=True)

# --- Save to CSV ---
df.to_csv("data/transactions.csv", index=False)
print(f"✅ Generated {len(df)} transactions → saved to data/transactions.csv")
print(f"   Suspicious: {df['is_suspicious'].sum()} | Normal: {(~df['is_suspicious']).sum()}")