import sqlite3
import pandas as pd
from datetime import datetime

# --- Connect to database ---
conn = sqlite3.connect("data/transactions.db")

alerts = []  # we'll collect all alerts here

# -------------------------------------------------------
# RULE 1: Large cash transactions (over $10,000)
# -------------------------------------------------------
rule1 = pd.read_sql_query("""
    SELECT
        transaction_id,
        customer_id,
        date,
        amount,
        transaction_type,
        destination_country,
        'Large Cash Transaction' AS alert_type,
        'HIGH' AS severity
    FROM transactions
    WHERE amount > 10000
""", conn)

alerts.append(rule1)
print(f"🔴 Rule 1 - Large Cash Transactions:       {len(rule1)} alerts")

# -------------------------------------------------------
# RULE 2: Structuring — 3+ transactions in 24hrs
#         by same customer, each between $8,000-$9,999
# -------------------------------------------------------
rule2_raw = pd.read_sql_query("""
    SELECT
        transaction_id,
        customer_id,
        date,
        amount,
        transaction_type,
        destination_country
    FROM transactions
    WHERE amount BETWEEN 8000 AND 9999
    ORDER BY customer_id, date
""", conn)

# Group by customer and check if 3+ transactions happen within 24 hours
structuring_alerts = []
rule2_raw["date"] = pd.to_datetime(rule2_raw["date"])

for customer, group in rule2_raw.groupby("customer_id"):
    group = group.sort_values("date").reset_index(drop=True)
    for i in range(len(group)):
        window = group[
            (group["date"] >= group.loc[i, "date"]) &
            (group["date"] <= group.loc[i, "date"] + pd.Timedelta(hours=24))
        ]
        if len(window) >= 3:
            structuring_alerts.append(group.loc[i].to_dict())

if structuring_alerts:
    rule2 = pd.DataFrame(structuring_alerts).drop_duplicates("transaction_id")
    rule2["alert_type"] = "Structuring"
    rule2["severity"] = "HIGH"
    alerts.append(rule2)
    print(f"🔴 Rule 2 - Structuring:                   {len(rule2)} alerts")
else:
    print("🟢 Rule 2 - Structuring:                   0 alerts")

# -------------------------------------------------------
# RULE 3: Wire transfers to high-risk countries
# -------------------------------------------------------
HIGH_RISK_COUNTRIES = ("IR", "KP", "SY")

rule3 = pd.read_sql_query(f"""
    SELECT
        transaction_id,
        customer_id,
        date,
        amount,
        transaction_type,
        destination_country,
        'High-Risk Country Wire' AS alert_type,
        'CRITICAL' AS severity
    FROM transactions
    WHERE transaction_type = 'wire_transfer'
    AND destination_country IN {HIGH_RISK_COUNTRIES}
""", conn)

alerts.append(rule3)
print(f"🚨 Rule 3 - High-Risk Country Wires:       {len(rule3)} alerts")

# -------------------------------------------------------
# RULE 4: Rapid movement — customer makes 5+ transactions
#         of any kind within a single day
# -------------------------------------------------------
rule4_raw = pd.read_sql_query("""
    SELECT
        transaction_id,
        customer_id,
        DATE(date) AS day,
        date,
        amount,
        transaction_type,
        destination_country
    FROM transactions
""", conn)

rule4_raw["date"] = pd.to_datetime(rule4_raw["date"])

rapid_alerts = []
daily_counts = rule4_raw.groupby(["customer_id", "day"])

for (customer, day), group in daily_counts:
    if len(group) >= 5:
        for _, row in group.iterrows():
            rapid_alerts.append(row.to_dict())

if rapid_alerts:
    rule4 = pd.DataFrame(rapid_alerts).drop_duplicates("transaction_id")
    rule4["alert_type"] = "Rapid Movement"
    rule4["severity"] = "MEDIUM"
    rule4 = rule4.drop(columns=["day"])
    alerts.append(rule4)
    print(f"🟡 Rule 4 - Rapid Movement:                {len(rule4)} alerts")
else:
    print("🟢 Rule 4 - Rapid Movement:                0 alerts")

# -------------------------------------------------------
# Combine all alerts
# -------------------------------------------------------
all_alerts = pd.concat(alerts, ignore_index=True)
all_alerts = all_alerts.drop_duplicates("transaction_id")
all_alerts = all_alerts.sort_values("severity", 
                key=lambda x: x.map({"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}))

# Convert date back to string so SQLite can store it
all_alerts["date"] = all_alerts["date"].astype(str)

# --- Save alerts to database ---
all_alerts.to_sql("alerts", conn, if_exists="replace", index=False)

# --- Save alerts to CSV as backup ---
all_alerts.to_csv("data/alerts.csv", index=False)

print(f"\n✅ Total unique alerts generated: {len(all_alerts)}")
print(f"   CRITICAL : {len(all_alerts[all_alerts['severity'] == 'CRITICAL'])}")
print(f"   HIGH     : {len(all_alerts[all_alerts['severity'] == 'HIGH'])}")
print(f"   MEDIUM   : {len(all_alerts[all_alerts['severity'] == 'MEDIUM'])}")
print("\n✅ Alerts saved → data/alerts.csv + database table 'alerts'")

conn.close()