import sqlite3
import pandas as pd

# --- Connect to SQLite (creates the file if it doesn't exist) ---
conn = sqlite3.connect("data/transactions.db")
cursor = conn.cursor()

# --- Create the transactions table ---
cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id      TEXT PRIMARY KEY,
        customer_id         TEXT NOT NULL,
        date                TEXT NOT NULL,
        amount              REAL NOT NULL,
        transaction_type    TEXT NOT NULL,
        destination_country TEXT NOT NULL,
        is_suspicious       INTEGER NOT NULL  -- 0 = False, 1 = True
    )
""")
print("✅ Table created")

# --- Load CSV into DataFrame ---
df = pd.read_csv("data/transactions.csv")

# --- Write DataFrame into SQLite table ---
df.to_sql("transactions", conn, if_exists="replace", index=False)
print(f"✅ Loaded {len(df)} transactions into the database")

# --- Run some SQL queries to verify the data ---

print("\n--- Sample of 5 transactions ---")
sample = pd.read_sql_query("SELECT * FROM transactions LIMIT 5", conn)
print(sample.to_string(index=False))

print("\n--- Transaction type breakdown ---")
breakdown = pd.read_sql_query("""
    SELECT transaction_type,
           COUNT(*) as count,
           ROUND(AVG(amount), 2) as avg_amount
    FROM transactions
    GROUP BY transaction_type
    ORDER BY count DESC
""", conn)
print(breakdown.to_string(index=False))

print("\n--- Suspicious vs Normal ---")
flagged = pd.read_sql_query("""
    SELECT is_suspicious,
           COUNT(*) as count,
           ROUND(AVG(amount), 2) as avg_amount
    FROM transactions
    GROUP BY is_suspicious
""", conn)
print(flagged.to_string(index=False))

# --- Close connection ---
conn.close()
print("\n✅ Database ready → data/transactions.db")