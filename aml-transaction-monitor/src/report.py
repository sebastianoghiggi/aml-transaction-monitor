import sqlite3
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # no display needed, we're saving to file
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import base64
import io
from datetime import datetime

# --- Connect and load data ---
conn = sqlite3.connect("data/transactions.db")
alerts = pd.read_sql_query("SELECT * FROM alerts", conn)
transactions = pd.read_sql_query("SELECT * FROM transactions", conn)
conn.close()

alerts["date"] = pd.to_datetime(alerts["date"])
transactions["date"] = pd.to_datetime(transactions["date"])

# --- Helper: convert matplotlib figure to base64 image ---
def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return encoded

# --- Color palette ---
SEVERITY_COLORS = {"CRITICAL": "#e63946", "HIGH": "#f4a261", "MEDIUM": "#457b9d"}

# -------------------------------------------------------
# CHART 1: Alerts by severity (bar chart)
# -------------------------------------------------------
severity_counts = alerts["severity"].value_counts().reindex(["CRITICAL", "HIGH", "MEDIUM"]).fillna(0)
fig1, ax1 = plt.subplots(figsize=(6, 4))
bars = ax1.bar(severity_counts.index, severity_counts.values,
               color=[SEVERITY_COLORS[s] for s in severity_counts.index], edgecolor="white", width=0.5)
ax1.set_title("Alerts by Severity", fontsize=14, fontweight="bold", pad=15)
ax1.set_xlabel("Severity Level")
ax1.set_ylabel("Number of Alerts")
ax1.set_ylim(0, severity_counts.max() + 3)
for bar, val in zip(bars, severity_counts.values):
    ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
             str(int(val)), ha="center", fontsize=11, fontweight="bold")
ax1.spines[["top", "right"]].set_visible(False)
chart1 = fig_to_base64(fig1)

# -------------------------------------------------------
# CHART 2: Alerts by type (horizontal bar)
# -------------------------------------------------------
type_counts = alerts["alert_type"].value_counts()
fig2, ax2 = plt.subplots(figsize=(6, 4))
bars2 = ax2.barh(type_counts.index, type_counts.values, color="#2a9d8f", edgecolor="white")
ax2.set_title("Alerts by Type", fontsize=14, fontweight="bold", pad=15)
ax2.set_xlabel("Number of Alerts")
ax2.invert_yaxis()
for bar, val in zip(bars2, type_counts.values):
    ax2.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
             str(int(val)), va="center", fontsize=10, fontweight="bold")
ax2.spines[["top", "right"]].set_visible(False)
chart2 = fig_to_base64(fig2)

# -------------------------------------------------------
# CHART 3: Alert amounts vs normal (box plot)
# -------------------------------------------------------
transactions["category"] = transactions["is_suspicious"].map({0: "Normal", 1: "Flagged"})
fig3, ax3 = plt.subplots(figsize=(6, 4))
sns.boxplot(data=transactions, x="category", y="amount",
            palette={"Normal": "#a8dadc", "Flagged": "#e63946"}, ax=ax3)
ax3.set_title("Transaction Amount: Normal vs Flagged", fontsize=14, fontweight="bold", pad=15)
ax3.set_xlabel("")
ax3.set_ylabel("Amount (USD)")
ax3.spines[["top", "right"]].set_visible(False)
chart3 = fig_to_base64(fig3)

# -------------------------------------------------------
# CHART 4: Alerts over time (monthly)
# -------------------------------------------------------
alerts["month"] = alerts["date"].dt.to_period("M")
monthly = alerts.groupby(["month", "severity"]).size().unstack(fill_value=0)
monthly.index = monthly.index.astype(str)
fig4, ax4 = plt.subplots(figsize=(10, 4))
bottom = pd.Series([0] * len(monthly), index=monthly.index)
for severity in ["CRITICAL", "HIGH", "MEDIUM"]:
    if severity in monthly.columns:
        ax4.bar(monthly.index, monthly[severity], bottom=bottom,
                label=severity, color=SEVERITY_COLORS[severity], edgecolor="white")
        bottom += monthly[severity]
ax4.set_title("Alerts Over Time (Monthly)", fontsize=14, fontweight="bold", pad=15)
ax4.set_xlabel("Month")
ax4.set_ylabel("Number of Alerts")
ax4.legend(title="Severity")
plt.xticks(rotation=45, ha="right")
ax4.spines[["top", "right"]].set_visible(False)
chart4 = fig_to_base64(fig4)

print("✅ Charts generated")

# -------------------------------------------------------
# BUILD HTML REPORT
# -------------------------------------------------------
generated_on = datetime.now().strftime("%B %d, %Y at %H:%M")

# Top 10 alerts table
top_alerts = alerts[["transaction_id", "customer_id", "date", "amount",
                      "alert_type", "severity", "destination_country"]].head(10)
top_alerts["date"] = top_alerts["date"].dt.strftime("%Y-%m-%d %H:%M")
top_alerts["amount"] = top_alerts["amount"].apply(lambda x: f"${x:,.2f}")

def severity_badge(s):
    colors = {"CRITICAL": "#e63946", "HIGH": "#f4a261", "MEDIUM": "#457b9d"}
    return f'<span style="background:{colors[s]};color:white;padding:3px 10px;border-radius:12px;font-size:12px;font-weight:bold">{s}</span>'

top_alerts["severity"] = top_alerts["severity"].apply(severity_badge)

table_html = top_alerts.to_html(index=False, escape=False, classes="alert-table",
                                 border=0, justify="left")

html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>AML Transaction Monitoring Report</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Segoe UI', sans-serif; background: #f0f2f5; color: #1d1d1d; }}
    header {{
      background: linear-gradient(135deg, #1d3557, #457b9d);
      color: white; padding: 40px;
      display: flex; justify-content: space-between; align-items: center;
    }}
    header h1 {{ font-size: 28px; letter-spacing: 1px; }}
    header p {{ font-size: 13px; opacity: 0.8; margin-top: 6px; }}
    .badge {{ background: rgba(255,255,255,0.2); padding: 6px 14px;
              border-radius: 20px; font-size: 13px; }}
    .container {{ max-width: 1100px; margin: 40px auto; padding: 0 20px; }}
    .kpi-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 32px; }}
    .kpi {{ background: white; border-radius: 12px; padding: 24px;
             text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.07); }}
    .kpi .value {{ font-size: 36px; font-weight: 800; }}
    .kpi .label {{ font-size: 13px; color: #666; margin-top: 6px; }}
    .kpi.critical .value {{ color: #e63946; }}
    .kpi.high .value {{ color: #f4a261; }}
    .kpi.medium .value {{ color: #457b9d; }}
    .kpi.total .value {{ color: #1d3557; }}
    .section-title {{ font-size: 18px; font-weight: 700; margin: 32px 0 16px;
                      color: #1d3557; border-left: 4px solid #457b9d; padding-left: 12px; }}
    .charts-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 32px; }}
    .chart-box {{ background: white; border-radius: 12px; padding: 20px;
                  box-shadow: 0 2px 8px rgba(0,0,0,0.07); }}
    .chart-box img {{ width: 100%; }}
    .chart-full {{ background: white; border-radius: 12px; padding: 20px;
                   box-shadow: 0 2px 8px rgba(0,0,0,0.07); margin-bottom: 32px; }}
    .chart-full img {{ width: 100%; }}
    .alert-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    .alert-table th {{ background: #1d3557; color: white; padding: 12px 14px; text-align: left; }}
    .alert-table td {{ padding: 11px 14px; border-bottom: 1px solid #eee; }}
    .alert-table tr:hover td {{ background: #f8f9fa; }}
    .table-wrap {{ background: white; border-radius: 12px; overflow: hidden;
                   box-shadow: 0 2px 8px rgba(0,0,0,0.07); margin-bottom: 40px; }}
    footer {{ text-align: center; padding: 24px; font-size: 12px; color: #999; }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>🛡️ AML Transaction Monitoring Report</h1>
      <p>Generated on {generated_on} · Fiscal Year 2024</p>
    </div>
    <div class="badge">CONFIDENTIAL</div>
  </header>

  <div class="container">

    <div class="kpi-row">
      <div class="kpi total">
        <div class="value">{len(alerts)}</div>
        <div class="label">Total Alerts</div>
      </div>
      <div class="kpi critical">
        <div class="value">{len(alerts[alerts['severity']=='CRITICAL'])}</div>
        <div class="label">Critical</div>
      </div>
      <div class="kpi high">
        <div class="value">{len(alerts[alerts['severity']=='HIGH'])}</div>
        <div class="label">High</div>
      </div>
      <div class="kpi medium">
        <div class="value">{len(alerts[alerts['severity']=='MEDIUM'])}</div>
        <div class="label">Medium</div>
      </div>
    </div>

    <div class="section-title">Alert Breakdown</div>
    <div class="charts-grid">
      <div class="chart-box"><img src="data:image/png;base64,{chart1}"></div>
      <div class="chart-box"><img src="data:image/png;base64,{chart2}"></div>
    </div>

    <div class="section-title">Amount Distribution</div>
    <div class="charts-grid">
      <div class="chart-box"><img src="data:image/png;base64,{chart3}"></div>
    </div>

    <div class="section-title">Alerts Over Time</div>
    <div class="chart-full"><img src="data:image/png;base64,{chart4}"></div>

    <div class="section-title">Top 10 Alerts</div>
    <div class="table-wrap">{table_html}</div>

  </div>
  <footer>AML Monitoring System · Synthetic Data · For Portfolio Use Only</footer>
</body>
</html>
"""

with open("data/aml_report.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ Report saved → data/aml_report.html")
print("   Open it in your browser to view the dashboard!")